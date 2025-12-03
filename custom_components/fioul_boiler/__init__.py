from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    hass.data.setdefault(DOMAIN, {})
    from .coordinator import FioulBoilerCoordinator

    coordinator = FioulBoilerCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    # Neue API (Mehrzahl)
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    # Alte API (Einzahl!)
    await hass.config_entries.async_forward_entry_unload(entry, "sensor")

    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True
