from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector

from .const import (
    DOMAIN,
    CONF_POWER_SENSOR,
    CONF_LPH_RUN,
    CONF_DEBOUNCE,
    CONF_KWH_PER_LITER,
    DEFAULT_LPH_RUN,
    DEFAULT_DEBOUNCE,
    DEFAULT_KWH_PER_LITER,
    DEFAULT_THRESHOLDS,
)


class FioulBoilerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the fioul boiler."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        errors: dict[str, str] = {}

        if user_input is not None:
            if user_input[CONF_LPH_RUN] <= 0:
                errors[CONF_LPH_RUN] = "invalid_lph"
            if user_input[CONF_DEBOUNCE] < 0:
                errors[CONF_DEBOUNCE] = "invalid_debounce"

            if not errors:
                await self.async_set_unique_id(f"fioul_boiler_{user_input[CONF_POWER_SENSOR]}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="Fioul Boiler", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_POWER_SENSOR): selector(
                    {
                        "entity": {
                            "domain": "sensor",
                            "device_class": "power",
                        }
                    }
                ),
                vol.Optional(CONF_LPH_RUN, default=DEFAULT_LPH_RUN): vol.Coerce(float),
                vol.Optional(CONF_DEBOUNCE, default=DEFAULT_DEBOUNCE): vol.Coerce(int),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return FioulBoilerOptionsFlowHandler(config_entry)


class FioulBoilerOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for fioul boiler thresholds and parameters."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            thresholds = {
                "arret": float(user_input["arret"]),
                "nuit": float(user_input["nuit"]),
                "pompe": float(user_input["pompe"]),
                "prechauffage": float(user_input["prechauffage"]),
                "postcirc": float(user_input["postcirc"]),
                "burn_max": float(user_input["burn_max"]),
            }
            options: dict[str, Any] = {
                CONF_LPH_RUN: float(user_input[CONF_LPH_RUN]),
                CONF_DEBOUNCE: int(user_input[CONF_DEBOUNCE]),
                CONF_KWH_PER_LITER: float(user_input[CONF_KWH_PER_LITER]),
                "thresholds": thresholds,
            }
            return self.async_create_entry(title="", data=options)

        data = self._entry.options or {}
        thresholds = {**DEFAULT_THRESHOLDS, **data.get("thresholds", {})}

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_LPH_RUN,
                    default=data.get(CONF_LPH_RUN, self._entry.data.get(CONF_LPH_RUN, DEFAULT_LPH_RUN)),
                ): vol.Coerce(float),
                vol.Optional(
                    CONF_DEBOUNCE,
                    default=data.get(CONF_DEBOUNCE, self._entry.data.get(CONF_DEBOUNCE, DEFAULT_DEBOUNCE)),
                ): vol.Coerce(int),
                vol.Optional(
                    CONF_KWH_PER_LITER,
                    default=data.get(CONF_KWH_PER_LITER, DEFAULT_KWH_PER_LITER),
                ): vol.Coerce(float),
                vol.Optional("arret", default=thresholds["arret"]): vol.Coerce(float),
                vol.Optional("nuit", default=thresholds["nuit"]): vol.Coerce(float),
                vol.Optional("pompe", default=thresholds["pompe"]): vol.Coerce(float),
                vol.Optional("prechauffage", default=thresholds["prechauffage"]): vol.Coerce(float),
                vol.Optional("postcirc", default=thresholds["postcirc"]): vol.Coerce(float),
                vol.Optional("burn_max", default=thresholds["burn_max"]): vol.Coerce(float),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
