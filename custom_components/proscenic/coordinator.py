from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ProscenicApi, discover_ip_by_device_id
from .const import (
    DP_BATTERY,
    DP_BRUSH_HEALTH,
    DP_CLEAN_AREA,
    DP_CLEAN_TIME,
    DP_CURRENT_STATE,
    DP_DEVICE_MODEL,
    DP_FAULT,
    DP_FAN_SPEED,
    DP_FILTER_HEALTH,
    DP_RESET_FILTER,
    DP_SENSOR_HEALTH,
    DP_SIDE_BRUSH_HEALTH,
    DP_SWEEP_OR_MOP,
    DP_WATER_SPEED,
)

_LOGGER = logging.getLogger(__name__)


@dataclass
class ProscenicState:
    raw_dps: dict[str, Any]
    battery: Optional[int] = None
    fault: Optional[int] = None
    current_state: Optional[int] = None
    fan_speed: Optional[str] = None
    water_speed: Optional[str] = None
    clean_area: Optional[float] = None
    clean_time: Optional[int] = None
    mop_equipped: Optional[bool] = None
    device_model: Optional[str] = None
    sensor_health: Optional[int] = None
    filter_health: Optional[int] = None
    side_brush_health: Optional[int] = None
    brush_health: Optional[int] = None
    reset_filter: Optional[Any] = None


class ProscenicCoordinator(DataUpdateCoordinator[ProscenicState]):
    def __init__(self, hass: HomeAssistant, api: ProscenicApi) -> None:
        super().__init__(hass=hass, logger=_LOGGER, name="proscenic")
        self.api = api
        self.auto_discover_ip: bool = True

    async def _async_update_data(self) -> ProscenicState:
        try:
            return await self._fetch_once()
        except Exception as exc:
            # Enterprise: se abilitato, prova rediscovery IP e ritenta una volta
            if self.auto_discover_ip:
                new_ip = await discover_ip_by_device_id(self.api.device_id, timeout_s=6)
                if new_ip and new_ip != self.api.host:
                    _LOGGER.warning(
                        "Proscenic: IP cambiato %s -> %s, ricostruisco il device e ritento",
                        self.api.host,
                        new_ip,
                    )
                    self.api.update_host(new_ip)
                    try:
                        return await self._fetch_once()
                    except Exception as exc2:
                        raise UpdateFailed(str(exc2)) from exc2

            raise UpdateFailed(str(exc)) from exc

    async def _fetch_once(self) -> ProscenicState:
        payload = await self.api.status()
        dps = (payload or {}).get("dps", {}) or {}

        def get(dp: int) -> Any:
            return dps.get(str(dp))

        st = ProscenicState(raw_dps=dps)

        v = get(DP_BATTERY)
        if v is not None:
            st.battery = int(v)

        v = get(DP_FAULT)
        if v is not None:
            st.fault = int(v)

        v = get(DP_CURRENT_STATE)
        if v is not None:
            st.current_state = int(v)

        v = get(DP_FAN_SPEED)
        if v is not None:
            st.fan_speed = str(v)

        v = get(DP_WATER_SPEED)
        if v is not None:
            st.water_speed = str(v)

        v = get(DP_CLEAN_AREA)
        if v is not None:
            try:
                st.clean_area = float(v)
            except Exception:
                st.clean_area = None

        v = get(DP_CLEAN_TIME)
        if v is not None:
            st.clean_time = int(v)

        v = get(DP_SWEEP_OR_MOP)
        if v is not None:
            st.mop_equipped = (str(v) != "sweep")

        v = get(DP_DEVICE_MODEL)
        if v is not None:
            st.device_model = str(v)

        v = get(DP_SENSOR_HEALTH)
        if v is not None:
            st.sensor_health = int(v)

        v = get(DP_FILTER_HEALTH)
        if v is not None:
            st.filter_health = int(v)

        v = get(DP_SIDE_BRUSH_HEALTH)
        if v is not None:
            st.side_brush_health = int(v)

        v = get(DP_BRUSH_HEALTH)
        if v is not None:
            st.brush_health = int(v)

        v = get(DP_RESET_FILTER)
        if v is not None:
            st.reset_filter = v

        return st