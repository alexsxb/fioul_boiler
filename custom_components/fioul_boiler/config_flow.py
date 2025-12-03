from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_POWER_SENSOR,
    CONF_LPH_RUN,
    CONF_DEBOUNCE,
    CONF_KWH_PER_LITER,
    DEFAULT_LPH_RUN,
    DEFAULT_DEBOUNCE,
    DEFAULT_KWH_PER_LITER,
)


class FioulBoilerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            return self.async_create_entry(title="Fioul Boiler", data=user_input)

        schema = vol.Schema(
            {
                vol.Required(CONF_POWER_SENSOR): str,
                vol.Optional(CONF_LPH_RUN, default=DEFAULT_LPH_RUN): vol.Coerce(float),
                vol.Optional(CONF_DEBOUNCE, default=DEFAULT_DEBOUNCE): vol.Coerce(int),
                vol.Optional(CONF_KWH_PER_LITER, default=DEFAULT_KWH_PER_LITER): vol.Coerce(float),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)



class FioulBoilerOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        data = self.config_entry.options

        schema = vol.Schema(
            {
                vol.Optional(CONF_LPH_RUN, default=data.get(CONF_LPH_RUN, DEFAULT_LPH_RUN)): vol.Coerce(float),
                vol.Optional(CONF_DEBOUNCE, default=data.get(CONF_DEBOUNCE, DEFAULT_DEBOUNCE)): vol.Coerce(int),
                vol.Optional(CONF_KWH_PER_LITER, default=data.get(CONF_KWH_PER_LITER, DEFAULT_KWH_PER_LITER)): vol.Coerce(float),
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)
