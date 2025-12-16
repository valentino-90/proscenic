from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .api import ProscenicApi, ProscenicConfig
from .coordinator import ProscenicCoordinator
from .const import (
    DOMAIN,
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

PLATFORMS: list[str] = ["vacuum", "sensor", "select"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    cfg = ProscenicConfig(
        device_id=entry.data[CONF_DEVICE_ID],
        local_key=entry.data[CONF_LOCAL_KEY],
        host=entry.data[CONF_HOST],
    )
    api = ProscenicApi(cfg)
    coordinator = ProscenicCoordinator(hass, api)

    opts = entry.options
    scan_s = int(opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))
    coordinator.update_interval = timedelta(seconds=scan_s)
    coordinator.auto_discover_ip = bool(opts.get(CONF_AUTO_DISCOVER_IP, DEFAULT_AUTO_DISCOVER_IP))

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "coordinator": coordinator,
        "remember_fan_speed": bool(opts.get(CONF_REMEMBER_FAN_SPEED, DEFAULT_REMEMBER_FAN_SPEED)),
        "show_raw_dps": bool(opts.get(CONF_SHOW_RAW_DPS, DEFAULT_SHOW_RAW_DPS)),
        "auto_discover_ip": bool(opts.get(CONF_AUTO_DISCOVER_IP, DEFAULT_AUTO_DISCOVER_IP)),
    }

    entry.async_on_unload(entry.add_update_listener(_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ProscenicCoordinator = data["coordinator"]

    opts = entry.options
    scan_s = int(opts.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_SECONDS))
    coordinator.update_interval = timedelta(seconds=scan_s)

    coordinator.auto_discover_ip = bool(opts.get(CONF_AUTO_DISCOVER_IP, DEFAULT_AUTO_DISCOVER_IP))

    data["remember_fan_speed"] = bool(opts.get(CONF_REMEMBER_FAN_SPEED, DEFAULT_REMEMBER_FAN_SPEED))
    data["show_raw_dps"] = bool(opts.get(CONF_SHOW_RAW_DPS, DEFAULT_SHOW_RAW_DPS))
    data["auto_discover_ip"] = bool(opts.get(CONF_AUTO_DISCOVER_IP, DEFAULT_AUTO_DISCOVER_IP))

    await coordinator.async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok