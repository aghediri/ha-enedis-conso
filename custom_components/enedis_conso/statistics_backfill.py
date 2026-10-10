"""Backfill daily consumption history into HA long-term statistics.

Enedis exposes up to ~3 years of daily consumption. We import it INTO the
daily_consumption sensor's own statistics (statistic_id = entity_id, source
"recorder") so the Energy dashboard + statistics-graph cards show history
immediately, as one continuous series the live sensor keeps extending.

``async_import_statistics`` upserts by start time -> idempotent re-runs.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone

from homeassistant.components.recorder.models import (
    StatisticData,
    StatisticMetaData,
)
from homeassistant.components.recorder.statistics import async_import_statistics
from homeassistant.const import UnitOfEnergy
from homeassistant.core import HomeAssistant

from .const import API_BASE, EP_DAILY
from .coordinator import EnedisConsoCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_backfill_statistics(
    hass: HomeAssistant,
    coordinator: EnedisConsoCoordinator,
    entity_id: str,
    days: int = 365,
) -> int:
    """Fetch `days` of daily consumption and import as a cumulative sum series.

    Energy dashboard needs a *sum* (increasing total) with state_class TOTAL.
    We build a running cumulative sum of daily kWh so the dashboard can diff it
    into per-day/-month usage.
    """
    today = date.today()
    start = today - timedelta(days=days)

    url = EP_DAILY.format(
        base=API_BASE, prm=coordinator.prm, start=start.isoformat(), end=today.isoformat()
    )
    payload = await coordinator._get(url)  # noqa: SLF001 (same package)
    points = EnedisConsoCoordinator._extract_readings(payload)  # noqa: SLF001
    if not points:
        _LOGGER.info("Enedis: no daily history to backfill")
        return 0

    points.sort(key=lambda x: x[0])
    metadata = StatisticMetaData(
        has_mean=False,
        has_sum=True,
        name=None,
        source="recorder",
        statistic_id=entity_id,
        unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    )
    stats: list[StatisticData] = []
    running = 0.0
    for d, wh in points:
        running += wh / 1000.0  # Wh -> kWh
        start_dt = datetime(d.year, d.month, d.day, 0, 0, tzinfo=timezone.utc)
        stats.append(StatisticData(start=start_dt, sum=round(running, 3), state=round(wh / 1000.0, 3)))

    if stats:
        async_import_statistics(hass, metadata, stats)
        _LOGGER.info("Enedis: imported %d daily history points", len(stats))
    return len(stats)
