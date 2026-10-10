"""Sensors for Enedis Consumption (consumption-only, via MyElectricalData)."""
from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfPower,
    UnitOfApparentPower,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, CONF_NAME, DEFAULT_NAME, DOMAIN
from .coordinator import EnedisConsoCoordinator


@dataclass(frozen=True, kw_only=True)
class EnedisSensorDescription(SensorEntityDescription):
    """Describes an Enedis sensor and how to read it from coordinator data."""
    value: Callable[[dict], object] = lambda d: None


SENSORS: tuple[EnedisSensorDescription, ...] = (
    EnedisSensorDescription(
        key="daily_consumption",
        name="Daily Consumption",
        icon="mdi:lightning-bolt",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value=lambda d: d.get("daily_consumption"),
    ),
    EnedisSensorDescription(
        key="month_consumption",
        name="Month Consumption",
        icon="mdi:calendar-month",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value=lambda d: d.get("month_consumption"),
    ),
    EnedisSensorDescription(
        key="hp_consumption",
        name="Peak (HP) Consumption",
        icon="mdi:weather-sunny",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value=lambda d: d.get("hp_consumption"),
    ),
    EnedisSensorDescription(
        key="hc_consumption",
        name="Off-Peak (HC) Consumption",
        icon="mdi:weather-night",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        value=lambda d: d.get("hc_consumption"),
    ),
    EnedisSensorDescription(
        key="last_power",
        name="Last Power",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: d.get("last_power"),
    ),
    EnedisSensorDescription(
        key="daily_max_power",
        name="Daily Max Power",
        icon="mdi:gauge-full",
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        device_class=SensorDeviceClass.APPARENT_POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value=lambda d: d.get("daily_max_power"),
    ),
    EnedisSensorDescription(
        key="daily_cost",
        name="Daily Cost",
        icon="mdi:cash",
        native_unit_of_measurement="€",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value=lambda d: d.get("daily_cost"),
    ),
    EnedisSensorDescription(
        key="month_cost",
        name="Month Cost",
        icon="mdi:cash-multiple",
        native_unit_of_measurement="€",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        value=lambda d: d.get("month_cost"),
    ),
    EnedisSensorDescription(
        key="subscribed_power",
        name="Subscribed Power",
        icon="mdi:transmission-tower",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("subscribed_power"),
    ),
    EnedisSensorDescription(
        key="tariff",
        name="Tariff",
        icon="mdi:file-document-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("tariff"),
    ),
    EnedisSensorDescription(
        key="tempo_today",
        name="Tempo Today",
        icon="mdi:palette",
        value=lambda d: d.get("tempo_today"),
    ),
    EnedisSensorDescription(
        key="tempo_tomorrow",
        name="Tempo Tomorrow",
        icon="mdi:palette-outline",
        value=lambda d: d.get("tempo_tomorrow"),
    ),
    EnedisSensorDescription(
        key="address",
        name="Delivery Address",
        icon="mdi:map-marker",
        entity_category=EntityCategory.DIAGNOSTIC,
        value=lambda d: d.get("address"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Enedis sensors from a config entry."""
    coordinator: EnedisConsoCoordinator = hass.data[DOMAIN][entry.entry_id]
    name = entry.data.get(CONF_NAME, DEFAULT_NAME)
    async_add_entities(
        EnedisConsoSensor(coordinator, entry, name, desc) for desc in SENSORS
    )


class EnedisConsoSensor(CoordinatorEntity[EnedisConsoCoordinator], SensorEntity):
    """A single Enedis consumption sensor."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: EnedisSensorDescription

    def __init__(
        self,
        coordinator: EnedisConsoCoordinator,
        entry: ConfigEntry,
        name: str,
        description: EnedisSensorDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=name,
            manufacturer="Enedis",
            model="Linky (MyElectricalData)",
            configuration_url="https://www.myelectricaldata.fr",
        )

    @property
    def native_value(self):
        return self.entity_description.value(self.coordinator.data or {})
