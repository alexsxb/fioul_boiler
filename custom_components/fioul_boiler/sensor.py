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


# -------------------------------------------------------------
# Basisklasse für alle Sensoren
# -------------------------------------------------------------

class BaseFioulSensor(SensorEntity):
    _attr_should_poll = False

    def __init__(self, coordinator, entry):
        self.coordinator = coordinator
        self.entry = entry

    # Wird als verfügbar behandelt, solange der Coordinator läuft
    @property
    def available(self):
        return True

    # WICHTIG: Damit die Entitäten der Integration zugeordnet werden
    @property
    def device_info(self):
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": "Fioul Boiler",
            "manufacturer": "Custom Integration",
            "model": "Fioul Burner Monitor",
        }

    # WICHTIG: unique_id → HA speichert Werte korrekt
    @property
    def unique_id(self):
        return f"{self.entry.entry_id}_{self.__class__.__name__}"

    @property
    def extra_state_attributes(self):
        return {}


# -------------------------------------------------------------
# Einzelne Sensoren
# -------------------------------------------------------------

class FioulBoilerPowerSensor(BaseFioulSensor):
    _attr_name = "Elektrische Leistung"
    _attr_icon = "mdi:flash"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = "W"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data.get("power", 0.0)


class FioulBoilerStateSensor(BaseFioulSensor):
    _attr_name = "Kesselzustand"
    _attr_icon = "mdi:eye"

    @property
    def native_value(self):
        return self.coordinator.data.get("state_filtered", "unknown")


class FioulBoilerBurnerActiveSensor(BaseFioulSensor):
    _attr_name = "Brenner aktiv"
    _attr_icon = "mdi:fire"

    @property
    def native_value(self):
        running = self.coordinator.data.get("burner_running", False)
        return "An" if running else "Aus"


class FioulBoilerFlowSensor(BaseFioulSensor):
    _attr_name = "Durchfluss"
    _attr_icon = "mdi:pipe-valve"
    _attr_native_unit_of_measurement = "L/h"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data.get("flow_lph", 0.0)


class FioulBoilerThermalPowerSensor(BaseFioulSensor):
    _attr_name = "Thermische Leistung"
    _attr_icon = "mdi:heat-wave"
    _attr_native_unit_of_measurement = "kW"
    _attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def native_value(self):
        return self.coordinator.data.get("thermal_power", 0.0)


class FioulBoilerDeltaLitersSensor(BaseFioulSensor):
    _attr_name = "Brennerphase – Liter"
    _attr_icon = "mdi:water"
    _attr_native_unit_of_measurement = "L"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        return self.coordinator.data.get("delta_liters", 0.0)


class FioulBoilerDeltaEnergySensor(BaseFioulSensor):
    _attr_name = "Brennerphase – Energie"
    _attr_icon = "mdi:lightning-bolt"
    _attr_native_unit_of_measurement = "kWh"
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    @property
    def native_value(self):
        return self.coordinator.data.get("delta_energy_kwh", 0.0)


class FioulBoilerErrorPHCSensor(BaseFioulSensor):
    _attr_name = "PHC-Fehler"
    _attr_icon = "mdi:alert-circle"

    @property
    def native_value(self):
        return "Problem" if self.coordinator.data.get("error_phc") else "OK"


class FioulBoilerErrorAbsenceSensor(BaseFioulSensor):
    _attr_name = "Abwesenheitsfehler"
    _attr_icon = "mdi:alert"

    @property
    def native_value(self):
        return "Problem" if self.coordinator.data.get("error_absence") else "OK"


class FioulBoilerErrorGlobalSensor(BaseFioulSensor):
    _attr_name = "Globaler Fehler"
    _attr_icon = "mdi:alert"

    @property
    def native_value(self):
        return "Problem" if self.coordinator.data.get("error_global") else "OK"
