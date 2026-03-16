from __future__ import annotations

from typing import Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN, DP_CLEANING_MODE, DP_WATER_SPEED
from .coordinator import ProscenicCoordinator
from .entity import ProscenicEntity

WATER_SPEED_OPTIONS = ["small", "medium", "Big"]

CLEANING_MODE_OPTION_TO_DP = {
    "none": "NONE",
    "return_to_base": "chargego",
    "auto": "smart",
    "edge": "wallfollow",
    "spot": "sprial",
}

CLEANING_MODE_DP_TO_OPTION = {v: k for k, v in CLEANING_MODE_OPTION_TO_DP.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ProscenicCoordinator = data["coordinator"]
    device_id: str = entry.data["device_id"]

    async_add_entities(
        [
            ProscenicWaterSpeed(coordinator, device_id),
            ProscenicCleaningMode(coordinator, device_id),
        ],
        update_before_add=False,
    )


class ProscenicWaterSpeed(ProscenicEntity, SelectEntity):
    """Water speed selector."""

    _attr_translation_key = "water_speed"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = WATER_SPEED_OPTIONS
    _attr_icon = "mdi:water-percent"

    def __init__(self, coordinator: ProscenicCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_water_speed"

    @property
    def current_option(self) -> Optional[str]:
        st = self.coordinator.data
        return st.water_speed if st else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ValueError(option)
        await self.coordinator.api.set_dp(DP_WATER_SPEED, option)
        await self.coordinator.async_request_refresh()


class ProscenicCleaningMode(ProscenicEntity, SelectEntity):
    """Cleaning mode selector."""

    _attr_translation_key = "cleaning_mode"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(CLEANING_MODE_OPTION_TO_DP.keys())
    _attr_icon = "mdi:robot-vacuum"

    def __init__(self, coordinator: ProscenicCoordinator, device_id: str) -> None:
        super().__init__(coordinator, device_id)
        self._attr_unique_id = f"{device_id}_cleaning_mode"

    @property
    def current_option(self) -> Optional[str]:
        st = self.coordinator.data
        if not st or not st.cleaning_mode:
            return None
        return CLEANING_MODE_DP_TO_OPTION.get(st.cleaning_mode, st.cleaning_mode)

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ValueError(option)

        dp_value = CLEANING_MODE_OPTION_TO_DP[option]
        await self.coordinator.api.set_dp(DP_CLEANING_MODE, dp_value)
        await self.coordinator.async_request_refresh()