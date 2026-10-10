"""DataUpdateCoordinator for Enedis Consumption (via MyElectricalData).

Pulls the full CONSUMPTION-side surface for one PDL (PRM):
  * daily consumption (kWh) — yesterday + rolling window
  * 30-min load curve (W) — latest point + daily peak from the curve
  * daily max power (VA)
  * contract (subscribed power kVA, tariff formula)
  * delivery address
  * Tempo day colors (today / tomorrow)
Then derives HP/HC split and € cost from the configured prices.

NO production data is fetched (consumption-only integration).
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    API_BASE,
    DEFAULT_HC_END,
    DEFAULT_HC_START,
    EP_ADDRESSES,
    EP_CONTRACTS,
    EP_DAILY,
    EP_LOAD_CURVE,
    EP_MAX_POWER,
    EP_TEMPO,
    UPDATE_INTERVAL_HOURS,
)

_LOGGER = logging.getLogger(__name__)


class EnedisConsoCoordinator(DataUpdateCoordinator):
    """Poll MyElectricalData for one PDL's consumption data."""

    def __init__(
        self,
        hass: HomeAssistant,
        prm: str,
        token: str,
        prices: dict,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="enedis_conso",
            update_interval=timedelta(hours=UPDATE_INTERVAL_HOURS),
        )
        self._prm = prm
        self._token = token
        self._prices = prices
        self._session = async_get_clientsession(hass)

    @property
    def prm(self) -> str:
        return self._prm

    async def _get(self, url: str) -> dict | None:
        """GET a MyElectricalData endpoint with the user's token."""
        headers = {"Authorization": self._token, "Content-Type": "application/json"}
        try:
            async with async_timeout.timeout(30):
                resp = await self._session.get(url, headers=headers)
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                return await resp.json()
        except Exception as err:  # noqa: BLE001
            _LOGGER.debug("Enedis: request failed %s (%s)", url, err)
            return None

    @staticmethod
    def _iso(d: date) -> str:
        return d.isoformat()

    def _price_for(self, color: str | None, is_peak: bool) -> float:
        """Resolve €/kWh given Tempo color (or None) and peak/off-peak."""
        p = self._prices
        if color in ("blue", "white", "red"):
            key = f"price_{color}_{'hp' if is_peak else 'hc'}"
            return float(p.get(key, 0) or 0)
        # HP/HC contract (no Tempo): use hp/hc if present, else base.
        if p.get("price_hp") or p.get("price_hc"):
            return float((p.get("price_hp") if is_peak else p.get("price_hc")) or 0)
        return float(p.get("price_base", 0) or 0)

    async def _async_update_data(self) -> dict:
        today = date.today()
        start = today - timedelta(days=35)       # ~5 weeks window
        yesterday = today - timedelta(days=1)
        base = API_BASE

        data: dict = {"prm": self._prm}

        # ---- Contract (subscribed power + tariff formula) -------------------
        contracts = await self._get(EP_CONTRACTS.format(base=base, prm=self._prm))
        subscribed_kva = None
        tariff = None
        if contracts:
            try:
                usage_points = contracts.get("customer", {}).get("usage_points", [])
                if usage_points:
                    c = usage_points[0].get("contracts", {})
                    subscribed_kva = c.get("subscribed_power")  # e.g. "9 kVA"
                    tariff = c.get("offpeak_hours") and "HP/HC" or c.get("distribution_tariff")
                    data["offpeak_hours_raw"] = c.get("offpeak_hours")
            except (AttributeError, IndexError, TypeError):
                pass
        data["subscribed_power"] = subscribed_kva
        data["tariff"] = tariff

        # ---- Address --------------------------------------------------------
        addr = await self._get(EP_ADDRESSES.format(base=base, prm=self._prm))
        if addr:
            try:
                up = addr.get("customer", {}).get("usage_points", [{}])[0].get("usage_point", {})
                a = up.get("usage_point_addresses", {})
                data["address"] = ", ".join(
                    x for x in [a.get("street"), a.get("postal_code"), a.get("city")] if x
                )
            except (AttributeError, IndexError, TypeError):
                data["address"] = None

        # ---- Tempo colors (today / tomorrow) --------------------------------
        tempo = await self._get(
            EP_TEMPO.format(base=base, start=self._iso(today), end=self._iso(today + timedelta(days=2)))
        )
        color_today = color_tomorrow = None
        if isinstance(tempo, dict):
            # MyElectricalData returns {"YYYY-MM-DD": "BLUE"|"WHITE"|"RED", ...}
            cmap = {"BLUE": "blue", "WHITE": "white", "RED": "red"}
            color_today = cmap.get(str(tempo.get(self._iso(today), "")).upper())
            color_tomorrow = cmap.get(str(tempo.get(self._iso(today + timedelta(days=1)), "")).upper())
        data["tempo_today"] = color_today
        data["tempo_tomorrow"] = color_tomorrow

        # ---- Daily consumption ---------------------------------------------
        daily = await self._get(
            EP_DAILY.format(base=base, prm=self._prm, start=self._iso(start), end=self._iso(today))
        )
        daily_points = self._extract_readings(daily)
        data["daily_points"] = daily_points  # [(date, Wh)]
        # Yesterday kWh.
        y_wh = next((v for (d, v) in daily_points if d == yesterday), None)
        data["daily_consumption"] = round(y_wh / 1000.0, 2) if y_wh is not None else None
        # This-month total (kWh).
        month_wh = sum(v for (d, v) in daily_points if d.month == today.month and d.year == today.year)
        data["month_consumption"] = round(month_wh / 1000.0, 2) if month_wh else None

        # ---- Max power per day ---------------------------------------------
        maxp = await self._get(
            EP_MAX_POWER.format(base=base, prm=self._prm, start=self._iso(start), end=self._iso(today))
        )
        maxp_points = self._extract_readings(maxp)
        y_max = next((v for (d, v) in maxp_points if d == yesterday), None)
        data["daily_max_power"] = round(y_max, 0) if y_max is not None else None
        data["max_power_points"] = maxp_points

        # ---- Load curve (30-min power) -------------------------------------
        curve = await self._get(
            EP_LOAD_CURVE.format(base=base, prm=self._prm,
                                 start=self._iso(yesterday), end=self._iso(today))
        )
        curve_points = self._extract_curve(curve)
        data["load_curve_points"] = curve_points  # [(datetime, W)]
        data["last_power"] = round(curve_points[-1][1], 0) if curve_points else None

        # ---- HP/HC split of yesterday's load curve + € cost ----------------
        hp_wh = hc_wh = 0.0
        for (dt, w) in curve_points:
            # 30-min slots -> Wh = W * 0.5h
            wh = w * 0.5
            is_peak = not (dt.hour >= DEFAULT_HC_START or dt.hour < DEFAULT_HC_END)
            if is_peak:
                hp_wh += wh
            else:
                hc_wh += wh
        data["hp_consumption"] = round(hp_wh / 1000.0, 2) if hp_wh else None
        data["hc_consumption"] = round(hc_wh / 1000.0, 2) if hc_wh else None

        # € cost of yesterday (color-aware).
        cost = (
            (hp_wh / 1000.0) * self._price_for(color_today, True)
            + (hc_wh / 1000.0) * self._price_for(color_today, False)
        )
        # If no curve (HP/HC unknown), fall back to daily kWh * base/flat price.
        if not curve_points and data["daily_consumption"] is not None:
            cost = data["daily_consumption"] * self._price_for(color_today, True)
        data["daily_cost"] = round(cost, 2) if cost else None

        # Rough monthly cost = month kWh * representative price.
        if data["month_consumption"]:
            data["month_cost"] = round(
                data["month_consumption"] * self._price_for(color_today, True), 2
            )

        return data

    # ---- payload parsers (MyElectricalData / Enedis shapes) -----------------
    @staticmethod
    def _extract_readings(payload: dict | None) -> list[tuple[date, float]]:
        """Daily/max-power payload -> [(date, value)]. Enedis shape:
        meter_reading.interval_reading[] = {value, date}."""
        out: list[tuple[date, float]] = []
        if not payload:
            return out
        try:
            readings = payload.get("meter_reading", {}).get("interval_reading", [])
            for r in readings:
                try:
                    d = datetime.strptime(r["date"][:10], "%Y-%m-%d").date()
                    out.append((d, float(r["value"])))
                except (KeyError, ValueError, TypeError):
                    continue
        except AttributeError:
            pass
        return out

    @staticmethod
    def _extract_curve(payload: dict | None) -> list[tuple[datetime, float]]:
        """Load-curve payload -> [(datetime, W)]."""
        out: list[tuple[datetime, float]] = []
        if not payload:
            return out
        try:
            readings = payload.get("meter_reading", {}).get("interval_reading", [])
            for r in readings:
                try:
                    dt = datetime.strptime(r["date"][:19], "%Y-%m-%d %H:%M:%S")
                    out.append((dt, float(r["value"])))
                except (KeyError, ValueError, TypeError):
                    continue
        except AttributeError:
            pass
        out.sort(key=lambda x: x[0])
        return out
