"""The Enedis Consumption integration (consumption-only, via MyElectricalData)."""
from __future__ import annotations

from datetime import datetime

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

from .const import (
    CONF_PRICE_BASE,
    CONF_PRICE_BLUE_HC,
    CONF_PRICE_BLUE_HP,
    CONF_PRICE_HC,
    CONF_PRICE_HP,
    CONF_PRICE_RED_HC,
    CONF_PRICE_RED_HP,
    CONF_PRICE_WHITE_HC,
    CONF_PRICE_WHITE_HP,
    CONF_PRM,
    CONF_TOKEN,
    DOMAIN,
)
from .coordinator import EnedisConsoCoordinator
from .statistics_backfill import async_backfill_statistics

PLATFORMS: list[Platform] = [Platform.SENSOR]

SERVICE_BACKFILL = "backfill_statistics"
ATTR_DAYS = "days"
_BACKFILL_DONE = "backfill_done"

_PRICE_KEYS = (
    CONF_PRICE_BASE, CONF_PRICE_HP, CONF_PRICE_HC,
    CONF_PRICE_BLUE_HP, CONF_PRICE_BLUE_HC,
    CONF_PRICE_WHITE_HP, CONF_PRICE_WHITE_HC,
    CONF_PRICE_RED_HP, CONF_PRICE_RED_HC,
)


def _prices(entry: ConfigEntry) -> dict:
    merged = {**entry.data, **entry.options}
    return {k: merged.get(k) for k in _PRICE_KEYS}


def _daily_entity_id(hass: HomeAssistant, entry: ConfigEntry) -> str | None:
    """Resolve the daily_consumption sensor's entity_id for stats backfill."""
    reg = er.async_get(hass)
    return reg.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_daily_consumption")


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Enedis Consumption from a config entry."""
    coordinator = EnedisConsoCoordinator(
        hass,
        prm=entry.data[CONF_PRM],
        token=entry.data[CONF_TOKEN],
        prices=_prices(entry),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    _async_register_services(hass)

    # Auto-backfill daily consumption history once (non-blocking) so the Energy
    # dashboard has data immediately.
    if not entry.data.get(_BACKFILL_DONE):

        async def _initial_backfill() -> None:
            try:
                eid = _daily_entity_id(hass, entry)
                if eid:
                    await async_backfill_statistics(hass, coordinator, eid, days=365)
                    hass.config_entries.async_update_entry(
                        entry, data={**entry.data, _BACKFILL_DONE: True}
                    )
            except Exception:  # noqa: BLE001
                pass

        entry.async_create_background_task(
            hass, _initial_backfill(), "enedis_conso_backfill"
        )

    return True


def _async_register_services(hass: HomeAssistant) -> None:
    if hass.services.has_service(DOMAIN, SERVICE_BACKFILL):
        return

    async def _handle_backfill(call: ServiceCall) -> None:
        days = int(call.data.get(ATTR_DAYS, 365))
        for entry in hass.config_entries.async_entries(DOMAIN):
            coordinator = hass.data[DOMAIN].get(entry.entry_id)
            eid = _daily_entity_id(hass, entry)
            if coordinator and eid:
                await async_backfill_statistics(hass, coordinator, eid, days=days)

    hass.services.async_register(
        DOMAIN,
        SERVICE_BACKFILL,
        _handle_backfill,
        schema=vol.Schema(
            {vol.Optional(ATTR_DAYS): vol.All(vol.Coerce(int), vol.Range(min=1, max=1095))}
        ),
    )


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
        if not hass.data[DOMAIN]:
            hass.services.async_remove(DOMAIN, SERVICE_BACKFILL)
    return unload_ok


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
