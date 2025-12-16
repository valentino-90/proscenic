from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, CONF_LOCAL_KEY


TO_REDACT = {CONF_LOCAL_KEY}


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id, {})
    coordinator = data.get("coordinator")

    diag: dict[str, Any] = {
        "entry": {
            "title": entry.title,
            "data": dict(entry.data),
            "options": dict(entry.options),
        },
        "state": None,
    }

    if coordinator and coordinator.data:
        diag["state"] = {
            "host": coordinator.api.host,
            "device_id": coordinator.api.device_id,
            "parsed": coordinator.data.__dict__,
            "raw_dps": coordinator.data.raw_dps,
        }

    return async_redact_data(diag, TO_REDACT)