from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import ProscenicCoordinator


class ProscenicEntity(CoordinatorEntity[ProscenicCoordinator]):
    """Base entity for Proscenic."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ProscenicCoordinator, device_id: str) -> None:
        super().__init__(coordinator)
        self._device_id = device_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information for the registry."""
        model = self.coordinator.data.device_model if self.coordinator.data else None
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer=MANUFACTURER,
            model=model or "Proscenic",
        )