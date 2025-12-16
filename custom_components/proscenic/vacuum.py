from __future__ import annotations

import asyncio
from enum import Enum, IntFlag
from typing import Any, Optional

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    MANUFACTURER,
    DP_CLEANING_MODE,
    DP_DIRECTION_CONTROL,
    DP_FAN_SPEED,
    REMEMBER_FAN_SPEED_DELAY,
)
from .coordinator import ProscenicCoordinator, ProscenicState


class Fault(IntFlag):
    NO_ERROR = 0
    SIDE_BRUSH = 1
    ROLLER_BRUSH = 2
    LEFT_WHEEL = 4
    RIGHT_WHEEL = 8
    DUST_BIN = 16
    OFF_GROUND = 32
    COLLISION_SENSOR = 64
    WATER_TANK = 128
    VIRTUAL_WALL = 256
    TRAPPED = 512
    UNKNOWN = 1024


class CurrentState(Enum):
    STAND_BY = 0
    CLEAN_SMART = 1
    MOPPING = 2
    CLEAN_WALL_FOLLOW = 3
    GOING_CHARGING = 4
    CHARGING = 5
    PAUSE = 7
    CLEAN_SINGLE = 8

    @staticmethod
    def to_activity(value: Optional[int]) -> Optional[VacuumActivity]:
        if value is None:
            return None
        try:
            st = CurrentState(value)
        except Exception:
            return None

        if st in (
            CurrentState.CLEAN_SMART,
            CurrentState.MOPPING,
            CurrentState.CLEAN_WALL_FOLLOW,
            CurrentState.CLEAN_SINGLE,
        ):
            return VacuumActivity.CLEANING
        if st == CurrentState.GOING_CHARGING:
            return VacuumActivity.RETURNING
        if st == CurrentState.CHARGING:
            return VacuumActivity.DOCKED
        if st == CurrentState.PAUSE:
            return VacuumActivity.PAUSED
        if st == CurrentState.STAND_BY:
            return VacuumActivity.IDLE
        return None

    @staticmethod
    def is_mopping(value: Optional[int]) -> bool:
        return value == CurrentState.MOPPING.value


class CleaningMode(Enum):
    SMART = "smart"
    WALL_FOLLOW = "wallfollow"
    MOP = "mop"
    CHARGE_GO = "chargego"
    SPRIAL = "sprial"
    SINGLE = "single"


class DirectionControl(Enum):
    STOP = "stop"


class FanSpeed(Enum):
    ECO = "ECO"
    NORMAL = "normal"
    STRONG = "strong"


SUPPORTED = (
    VacuumEntityFeature.STATE
    | VacuumEntityFeature.START
    | VacuumEntityFeature.PAUSE
    | VacuumEntityFeature.STOP
    | VacuumEntityFeature.RETURN_HOME
    | VacuumEntityFeature.FAN_SPEED
    | VacuumEntityFeature.CLEAN_SPOT
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ProscenicCoordinator = data["coordinator"]
    async_add_entities([ProscenicVacuum(coordinator, entry)], update_before_add=False)


class ProscenicVacuum(CoordinatorEntity[ProscenicCoordinator], StateVacuumEntity):
    _attr_supported_features = SUPPORTED

    def __init__(self, coordinator: ProscenicCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._device_id: str = entry.data["device_id"]
        self._name: str = entry.title

        self._cmd_lock = asyncio.Lock()

        self._last_cleaning_mode: Optional[str] = None
        self._stored_fan_speed: Optional[str] = None

        self._attr_name = self._name
        self._attr_unique_id = self._device_id

    @property
    def device_info(self) -> dict[str, Any]:
        st: ProscenicState = self.coordinator.data
        model = st.device_model if st and st.device_model else "Proscenic"
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "manufacturer": MANUFACTURER,
            "name": self._name,
            "model": model,
        }

    @property
    def activity(self) -> Optional[VacuumActivity]:
        st: ProscenicState = self.coordinator.data
        if not st:
            return None

        if st.fault is not None and st.fault != Fault.NO_ERROR:
            return VacuumActivity.ERROR

        return CurrentState.to_activity(st.current_state)

    @property
    def battery_level(self) -> Optional[int]:
        st: ProscenicState = self.coordinator.data
        return st.battery if st else None

    @property
    def fan_speed(self) -> Optional[str]:
        st: ProscenicState = self.coordinator.data
        return st.fan_speed if st else None

    @property
    def fan_speed_list(self) -> list[str]:
        return [f.value for f in FanSpeed]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        st: ProscenicState = self.coordinator.data
        if not st:
            return {}

        attrs: dict[str, Any] = {}

        if st.fault is not None and st.fault != Fault.NO_ERROR:
            try:
                attrs["error"] = Fault(st.fault).name
            except Exception:
                attrs["error"] = str(st.fault)

        if CurrentState.is_mopping(st.current_state):
            attrs["mode"] = "mopping"

        if st.clean_area is not None:
            attrs["cleaned_area"] = st.clean_area
        if st.clean_time is not None:
            attrs["cleaning_time"] = st.clean_time
        if st.mop_equipped is not None:
            attrs["mop_equipped"] = st.mop_equipped

        # Health values (diagnostic but useful)
        if st.sensor_health is not None:
            attrs["sensor_health"] = st.sensor_health
        if st.filter_health is not None:
            attrs["filter_health"] = st.filter_health
        if st.side_brush_health is not None:
            attrs["side_brush_health"] = st.side_brush_health
        if st.brush_health is not None:
            attrs["brush_health"] = st.brush_health
        if st.reset_filter is not None:
            attrs["reset_filter"] = st.reset_filter

        # Raw DPS only if option enabled
        domain_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        if domain_data.get("show_raw_dps", False):
            attrs["raw_dps"] = st.raw_dps

        return attrs

    async def async_start(self) -> None:
        async with self._cmd_lock:
            st: ProscenicState = self.coordinator.data
            if st and st.current_state == CurrentState.PAUSE.value and self._last_cleaning_mode:
                mode = self._last_cleaning_mode
            else:
                mode = CleaningMode.SMART.value
                self._last_cleaning_mode = mode

            await self.coordinator.api.set_dp(DP_CLEANING_MODE, mode)
            await self._maybe_restore_fan_speed_after_mode_change()
            await self.coordinator.async_request_refresh()

    async def async_pause(self) -> None:
        # Per la tua logica originale: “pause” reinvia la modalità per togglare
        async with self._cmd_lock:
            if self._last_cleaning_mode:
                await self.coordinator.api.set_dp(DP_CLEANING_MODE, self._last_cleaning_mode)
                await self.coordinator.async_request_refresh()

    async def async_stop(self, **kwargs) -> None:
        async with self._cmd_lock:
            await self.coordinator.api.set_dp(DP_DIRECTION_CONTROL, DirectionControl.STOP.value)
            self._last_cleaning_mode = None
            await self.coordinator.async_request_refresh()

    async def async_return_to_base(self, **kwargs) -> None:
        async with self._cmd_lock:
            self._last_cleaning_mode = CleaningMode.CHARGE_GO.value
            await self.coordinator.api.set_dp(DP_CLEANING_MODE, self._last_cleaning_mode)
            await self._maybe_restore_fan_speed_after_mode_change()
            await self.coordinator.async_request_refresh()

    async def async_clean_spot(self, **kwargs) -> None:
        async with self._cmd_lock:
            self._last_cleaning_mode = CleaningMode.SPRIAL.value
            await self.coordinator.api.set_dp(DP_CLEANING_MODE, self._last_cleaning_mode)
            await self._maybe_restore_fan_speed_after_mode_change()
            await self.coordinator.async_request_refresh()

    async def async_set_fan_speed(self, fan_speed: str, **kwargs) -> None:
        async with self._cmd_lock:
            # validate
            try:
                _ = FanSpeed(fan_speed)
            except Exception:
                raise ValueError(f"Fan speed non valida: {fan_speed}")

            await self.coordinator.api.set_dp(DP_FAN_SPEED, fan_speed)
            self._stored_fan_speed = fan_speed
            await self.coordinator.async_request_refresh()

    async def _maybe_restore_fan_speed_after_mode_change(self) -> None:
        domain_data = self.hass.data.get(DOMAIN, {}).get(self._entry.entry_id, {})
        remember = bool(domain_data.get("remember_fan_speed", False))
        if not remember or not self._stored_fan_speed:
            return

        async def _job():
            await asyncio.sleep(REMEMBER_FAN_SPEED_DELAY)
            await self.coordinator.api.set_dp(DP_FAN_SPEED, self._stored_fan_speed)

        self.hass.async_create_task(_job())