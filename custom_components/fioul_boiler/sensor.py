from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.const import STATE_UNKNOWN, STATE_UNAVAILABLE
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

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

        # Persistent accumulation sensors
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


# ---------------------------------------------------------------------------
# BASE CLASSES
# ---------------------------------------------------------------------------

class FioulBoilerBaseSensor(CoordinatorEntity[FioulBoilerCoordinator], SensorEntity):
    """Base class for read-only coordinator values."""

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
    def native_value(self) -> str | None:
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


# ---------------------------------------------------------------------------
# PERSISTENT ACCUMULATION BASE CLASS
# ---------------------------------------------------------------------------

class FioulBoilerAccumBase(FioulBoilerBaseSensor, RestoreEntity):
    """Base class for persistent sensors with delta accumulation."""

    _attr_native_value: float | None = None

    def __init__(self, coordinator: FioulBoilerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._last_update: datetime | None = None

    async def async_added_to_hass(self) -> None:
        """Restore last state from DB."""
        await super().async_added_to_hass()

        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            try:
                self._attr_native_value = float(last_state.state)
            except Exception:
                self._attr_native_value = 0.0
        else:
            self._attr_native_value = 0.0

        self._last_update = None

    # Default behavior: child classes override this
    @callback
    def _handle_coordinator_update(self) -> None:
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# LITER SENSORS
# ---------------------------------------------------------------------------

class FioulBoilerLitersTotalSensor(FioulBoilerAccumBase):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "L"

    @property
    def translation_key(self) -> str:
        return "liters_total"

    @callback
    def _handle_coordinator_update(self) -> None:
        delta = self.coordinator.data.get("delta_liters") or 0.0
        current = float(self._attr_native_value or 0.0)
        self._attr_native_value = round(current + float(delta), 3)
        self.async_write_ha_state()


class FioulBoilerLitersDailySensor(FioulBoilerAccumBase):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "L"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._last_day = None

    @property
    def translation_key(self) -> str:
        return "liters_daily"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        now = dt_util.now()
        self._last_day = now.day

    @callback
    def _handle_coordinator_update(self) -> None:
        delta = self.coordinator.data.get("delta_liters") or 0.0
        now = dt_util.now()

        if self._last_day is None or now.day != self._last_day:
            current = 0.0
            self._last_day = now.day
        else:
            current = float(self._attr_native_value or 0.0)

        self._attr_native_value = round(current + float(delta), 3)
        self.async_write_ha_state()


class FioulBoilerLitersMonthlySensor(FioulBoilerAccumBase):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "L"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._last_month = None

    @property
    def translation_key(self) -> str:
        return "liters_monthly"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        now = dt_util.now()
        self._last_month = now.month

    @callback
    def _handle_coordinator_update(self) -> None:
        delta = self.coordinator.data.get("delta_liters") or 0.0
        now = dt_util.now()

        if self._last_month is None or now.month != self._last_month:
            current = 0.0
            self._last_month = now.month
        else:
            current = float(self._attr_native_value or 0.0)

        self._attr_native_value = round(current + float(delta), 3)
        self.async_write_ha_state()


class FioulBoilerLitersYearlySensor(FioulBoilerAccumBase):
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "L"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._last_year = None

    @property
    def translation_key(self) -> str:
        return "liters_yearly"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        now = dt_util.now()
        self._last_year = now.year

    @callback
    def _handle_coordinator_update(self) -> None:
        delta = self.coordinator.data.get("delta_liters") or 0.0
        now = dt_util.now()

        if self._last_year is None or now.year != self._last_year:
            current = 0.0
            self._last_year = now.year
        else:
            current = float(self._attr_native_value or 0.0)

        self._attr_native_value = round(current + float(delta), 3)
        self.async_write_ha_state()


# ---------------------------------------------------------------------------
# ENERGY SENSORS
# ---------------------------------------------------------------------------

class FioulBoilerEnergyTotalSensor(FioulBoilerAccumBase):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    @property
    def translation_key(self) -> str:
        return "energy_total_kwh"

    @callback
    def _handle_coordinator_update(self) -> None:
        delta = self.coordinator.data.get("delta_energy_kwh") or 0.0
        current = float(self._attr_native_value or 0.0)
        self._attr_native_value = round(current + float(delta), 4)
        self.async_write_ha_state()


class FioulBoilerEnergyDailySensor(FioulBoilerAccumBase):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._last_day = None

    @property
    def translation_key(self) -> str:
        return "energy_daily_kwh"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._last_day = dt_util.now().day

    @callback
    def _handle_coordinator_update(self) -> None:
        delta = self.coordinator.data.get("delta_energy_kwh") or 0.0
        now = dt_util.now()

        if self._last_day is None or now.day != self._last_day:
            current = 0.0
            self._last_day = now.day
        else:
            current = float(self._attr_native_value or 0.0)

        self._attr_native_value = round(current + float(delta), 4)
        self.async_write_ha_state()


class FioulBoilerEnergyMonthlySensor(FioulBoilerAccumBase):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._last_month = None

    @property
    def translation_key(self) -> str:
        return "energy_monthly_kwh"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._last_month = dt_util.now().month

    @callback
    def _handle_coordinator_update(self) -> None:
        delta = self.coordinator.data.get("delta_energy_kwh") or 0.0
        now = dt_util.now()

        if self._last_month is None or now.month != self._last_month:
            current = 0.0
            self._last_month = now.month
        else:
            current = float(self._attr_native_value or 0.0)

        self._attr_native_value = round(current + float(delta), 4)
        self.async_write_ha_state()


class FioulBoilerEnergyYearlySensor(FioulBoilerAccumBase):
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = "kWh"

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry)
        self._last_year = None

    @property
    def translation_key(self) -> str:
        return "energy_yearly_kwh"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._last_year = dt_util.now().year

    @callback
    def _handle_coordinator_update(self) -> None:
        delta = self.coordinator.data.get("delta_energy_kwh") or 0.0
        now = dt_util.now()

        if self._last_year is None or now.year != self._last_year:
            current = 0.0
            self._last_year = now.year
        else:
            current = float(self._attr_native_value or 0.0)

        self._attr_native_value = round(current + float(delta), 4)
        self.async_write_ha_state()
