from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FioulBoilerCoordinator


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    """Set up Fioul boiler binary sensors from a config entry."""
    coordinator: FioulBoilerCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = [
        FioulBoilerGlobalErrorBinarySensor(coordinator, entry),
        FioulBoilerPhcErrorBinarySensor(coordinator, entry),
        FioulBoilerAbsenceErrorBinarySensor(coordinator, entry),
        FioulBoilerBurnerRunningBinarySensor(coordinator, entry),
    ]

    async_add_entities(entities)


class FioulBoilerBaseBinarySensor(
    CoordinatorEntity[FioulBoilerCoordinator], BinarySensorEntity
):
    """Base class for Fioul boiler binary sensors."""

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


class FioulBoilerGlobalErrorBinarySensor(FioulBoilerBaseBinarySensor):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def translation_key(self) -> str:
        return "error_global"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("error_global"))


class FioulBoilerPhcErrorBinarySensor(FioulBoilerBaseBinarySensor):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def translation_key(self) -> str:
        return "error_phc"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("error_phc"))


class FioulBoilerAbsenceErrorBinarySensor(FioulBoilerBaseBinarySensor):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def translation_key(self) -> str:
        return "error_absence"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("error_absence"))


class FioulBoilerBurnerRunningBinarySensor(FioulBoilerBaseBinarySensor):
    _attr_device_class = BinarySensorDeviceClass.POWER

    @property
    def translation_key(self) -> str:
        return "burner_running"

    @property
    def is_on(self) -> bool:
        return bool(self.coordinator.data.get("burner_running"))
