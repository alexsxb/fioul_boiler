from __future__ import annotations

from typing import Any
from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FioulBoilerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Fioul boiler sensors from a config entry."""
    coordinator: FioulBoilerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        FioulBoilerStateSensor(coordinator, entry),
        FioulBoilerPowerSensor(coordinator, entry),
        FioulBoilerThermalPowerSensor(coordinator, entry),
        FioulBoilerFlowSensor(coordinator, entry),
        FioulBoilerFlowFilteredSensor(coordinator, entry),
        FioulBoilerLitersTotalSensor(coordinator, entry),
        FioulBoilerLitersDailySensor(coordinator, entry),
        FioulBoilerLitersMonthlySensor(coordinator, entry),
        FioulBoilerLitersYearlySensor(coordinator, entry),
        FioulBoilerEnergyTotalSensor(coordinator, entry),
        FioulBoilerEnergyDailySensor(coordinator, entry),
        FioulBoilerEnergyMonthlySensor(coordinator, entry),
        FioulBoilerEnergyYearlySensor(coordinator, entry),
    ]

    async_add_entities(entities)


class FioulBoilerBaseSensor(CoordinatorEntity[FioulBoilerCoordinator], SensorEntity):
    """Base class for all Fioul boiler sensors."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FioulBoilerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_{self.translation_key}"

    @property
    def device_info(self) -> dict[str, Any]:
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Fioul boiler",
        }


class FioulBoilerStateSensor(FioulBoilerBaseSensor):
    @property
    def translation_key(self) -> str:
        return "state"

    @property
    def native_value(self) -> str:
        return self.coordinator.data.get("state_filtered")


class FioulBoilerPowerSensor(FioulBoilerBaseSensor):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "W"

    @property
    def translation_key(self) -> str:
        return "power"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("power")
        return round(val, 1) if isinstance(val, (int, float)) else None


class FioulBoilerThermalPowerSensor(FioulBoilerBaseSensor):
    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "kW"

    @property
    def translation_key(self) -> str:
        return "thermal_kw"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("thermal_kw")
        return round(val, 2) if isinstance(val, (int, float)) else None


class FioulBoilerFlowSensor(FioulBoilerBaseSensor):
    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "L/h"

    @property
    def translation_key(self) -> str:
        return "flow_lph"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("flow_lph")
        return round(val, 2) if isinstance(val, (int, float)) else None


class FioulBoilerFlowFilteredSensor(FioulBoilerBaseSensor):
    _attr_device_class = SensorDeviceClass.VOLUME_FLOW_RATE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "L/h"

    @property
    def translation_key(self) -> str:
        return "flow_filtered"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("flow_filtered")
        return round(val, 2) if isinstance(val, (int, float)) else None


class FioulBoilerLitersTotalSensor(FioulBoilerBaseSensor):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "L"

    @property
    def translation_key(self) -> str:
        return "liters_total"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("liters_total")
        return round(val, 2) if isinstance(val, (int, float)) else None


class FioulBoilerLitersDailySensor(FioulBoilerBaseSensor):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "L"

    @property
    def translation_key(self) -> str:
        return "liters_daily"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("liters_daily")
        return round(val, 2) if isinstance(val, (int, float)) else None


class FioulBoilerLitersMonthlySensor(FioulBoilerBaseSensor):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "L"

    @property
    def translation_key(self) -> str:
        return "liters_monthly"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("liters_monthly")
        return round(val, 2) if isinstance(val, (int, float)) else None


class FioulBoilerLitersYearlySensor(FioulBoilerBaseSensor):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "L"

    @property
    def translation_key(self) -> str:
        return "liters_yearly"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("liters_yearly")
        return round(val, 2) if isinstance(val, (int, float)) else None


class FioulBoilerEnergyTotalSensor(FioulBoilerBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    @property
    def translation_key(self) -> str:
        return "energy_total_kwh"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("energy_total_kwh")
        return round(val, 3) if isinstance(val, (int, float)) else None


class FioulBoilerEnergyDailySensor(FioulBoilerBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    @property
    def translation_key(self) -> str:
        return "energy_daily_kwh"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("energy_daily_kwh")
        return round(val, 3) if isinstance(val, (int, float)) else None


class FioulBoilerEnergyMonthlySensor(FioulBoilerBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    @property
    def translation_key(self) -> str:
        return "energy_monthly_kwh"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("energy_monthly_kwh")
        return round(val, 3) if isinstance(val, (int, float)) else None


class FioulBoilerEnergyYearlySensor(FioulBoilerBaseSensor):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    @property
    def translation_key(self) -> str:
        return "energy_yearly_kwh"

    @property
    def native_value(self) -> float | None:
        val = self.coordinator.data.get("energy_yearly_kwh")
        return round(val, 3) if isinstance(val, (int, float)) else None
