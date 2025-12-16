from __future__ import annotations

from typing import Any, Optional

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, DP_WATER_SPEED
from .coordinator import ProscenicCoordinator


WATER_SPEED_OPTIONS = ["small", "medium", "Big"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ProscenicCoordinator = data["coordinator"]
    async_add_entities([ProscenicWaterSpeed(entry, coordinator)], update_before_add=False)


class ProscenicWaterSpeed(CoordinatorEntity[ProscenicCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "water_speed"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = WATER_SPEED_OPTIONS
    _attr_icon = "mdi:water-percent"

    def __init__(self, entry: ConfigEntry, coordinator: ProscenicCoordinator) -> None:
        super().__init__(coordinator)
        self._device_id = entry.data["device_id"]
        self._attr_unique_id = f"{self._device_id}_water_speed"

    @property
    def current_option(self) -> Optional[str]:
        st = self.coordinator.data
        return st.water_speed if st else None

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            raise ValueError(option)
        await self.coordinator.api.set_dp(DP_WATER_SPEED, option)
        await self.coordinator.async_request_refresh()

    @property
    def device_info(self) -> dict[str, Any]:
        model = self.coordinator.data.device_model if self.coordinator.data else None
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "manufacturer": MANUFACTURER,
            "model": model or "Proscenic",
        }