from __future__ import annotations

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):

    coordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        FioulBoilerPowerSensor(coordinator, entry),
        FioulBoilerStateSensor(coordinator, entry),
        FioulBoilerBurnerActiveSensor(coordinator, entry),
        FioulBoilerFlowSensor(coordinator, entry),
        FioulBoilerThermalPowerSensor(coordinator, entry),
        FioulBoilerDeltaLitersSensor(coordinator, entry),
        FioulBoilerDeltaEnergySensor(coordinator, entry),
        FioulBoilerErrorPHCSensor(coordinator, entry),
        FioulBoilerErrorAbsenceSensor(coordinator, entry),
        FioulBoilerErrorGlobalSensor(coordinator, entry),
    ]

    async_add_entities(entities)


class BaseFioulSensor(SensorEntity):
    _attr_should_poll = False

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry

    @property
    def available(self):
        return True

    @property
    def extra_state_attributes(self):
        return {}


class FioulBoilerPowerSensor(BaseFioulSensor):
    _attr_name = "Elektrische Leistung"
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data.get("power")


class FioulBoilerStateSensor(BaseFioulSensor):
    _attr_name = "Kesselzustand"

    @property
    def icon(self):
        return "mdi:eye"

    @property
    def native_value(self):
        return self.coordinator.data.get("state_filtered")


class FioulBoilerBurnerActiveSensor(BaseFioulSensor):
    _attr_name = "Brenner aktiv"
    _attr_icon = "mdi:fire"

    @property
    def native_value(self):
        val = self.coordinator.data.get("burner_running")
        return "An" if val else "Aus"


class FioulBoilerFlowSensor(BaseFioulSensor):
    _attr_name = "Durchfluss"
    _attr_icon = "mdi:pipe-valve"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "L/h"

    @property
    def native_value(self):
        return self.coordinator.data.get("flow_lph")


class FioulBoilerThermalPowerSensor(BaseFioulSensor):
    _attr_name = "Thermische Leistung"
    _attr_icon = "mdi:heat-wave"
    _attr_native_unit_of_measurement = "kW"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data.get("thermal_power")


class FioulBoilerDeltaLitersSensor(BaseFioulSensor):
    _attr_name = "Brennerphase – Liter"
    _attr_icon = "mdi:water"
    _attr_native_unit_of_measurement = "L"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        return self.coordinator.data.get("delta_liters")


class FioulBoilerDeltaEnergySensor(BaseFioulSensor):
    _attr_name = "Brennerphase – Energie"
    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = "kWh"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        return self.coordinator.data.get("delta_energy_kwh")


class FioulBoilerErrorPHCSensor(BaseFioulSensor):
    _attr_name = "PHC-Fehler"
    _attr_icon = "mdi:alert-circle"

    @property
    def native_value(self):
        return "OK" if not self.coordinator.data.get("error_phc") else "Problem"


class FioulBoilerErrorAbsenceSensor(BaseFioulSensor):
    _attr_name = "Abwesenheitsfehler"
    _attr_icon = "mdi:alert"

    @property
    def native_value(self):
        return "OK" if not self.coordinator.data.get("error_absence") else "Problem"


class FioulBoilerErrorGlobalSensor(BaseFioulSensor):
    _attr_name = "Globaler Fehler"
    _attr_icon = "mdi:alert"

    @property
    def native_value(self):
        return "OK" if not self.coordinator.data.get("error_global") else "Problem"
