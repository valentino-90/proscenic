from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from .api import discover_ip_by_device_id
from .const import (
    DOMAIN,
    DEFAULT_NAME,
    CONF_DEVICE_ID,
    CONF_LOCAL_KEY,
    CONF_HOST,
    CONF_SCAN_INTERVAL,
    CONF_REMEMBER_FAN_SPEED,
    CONF_SHOW_RAW_DPS,
    CONF_AUTO_DISCOVER_IP,
    DEFAULT_SCAN_INTERVAL_SECONDS,
    DEFAULT_REMEMBER_FAN_SPEED,
    DEFAULT_SHOW_RAW_DPS,
    DEFAULT_AUTO_DISCOVER_IP,
)


class ProscenicConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            device_id = user_input[CONF_DEVICE_ID]
            host = user_input.get(CONF_HOST)

            # Best-effort discovery
            if not host:
                host = await discover_ip_by_device_id(device_id)
                if not host:
                    errors["base"] = "cannot_discover_ip"
                else:
                    user_input[CONF_HOST] = host

            if not errors:
                await self.async_set_unique_id(device_id)
                self._abort_if_unique_id_configured()

                title = user_input.get(CONF_NAME, DEFAULT_NAME)
                data = {
                    CONF_DEVICE_ID: user_input[CONF_DEVICE_ID],
                    CONF_LOCAL_KEY: user_input[CONF_LOCAL_KEY],
                    CONF_HOST: user_input[CONF_HOST],
                    CONF_NAME: title,
                }
                return self.async_create_entry(title=title, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_DEVICE_ID): str,
                vol.Required(CONF_LOCAL_KEY): str,
                vol.Optional(CONF_HOST): str,  # optional (discovery)
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return ProscenicOptionsFlowHandler(config_entry)


class ProscenicOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, entry: config_entries.ConfigEntry) -> None:
        self.entry = entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        opts = self.entry.options
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=60)),
                vol.Optional(
                    CONF_REMEMBER_FAN_SPEED,
                    default=opts.get(CONF_REMEMBER_FAN_SPEED, DEFAULT_REMEMBER_FAN_SPEED),
                ): bool,
                vol.Optional(
                    CONF_SHOW_RAW_DPS,
                    default=opts.get(CONF_SHOW_RAW_DPS, DEFAULT_SHOW_RAW_DPS),
                ): bool,
                vol.Optional(
                    CONF_AUTO_DISCOVER_IP,
                    default=opts.get(CONF_AUTO_DISCOVER_IP, DEFAULT_AUTO_DISCOVER_IP),
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)