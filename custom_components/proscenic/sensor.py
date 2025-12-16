from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfArea, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import ProscenicCoordinator, ProscenicState


@dataclass(frozen=True)
class ProscenicSensorSpec:
    desc: SensorEntityDescription
    value_fn: Callable[[ProscenicState], Any]


SPECS: tuple[ProscenicSensorSpec, ...] = (
    ProscenicSensorSpec(
        SensorEntityDescription(
            key="battery",
            translation_key="battery",
            device_class=SensorDeviceClass.BATTERY,
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
        ),
        lambda st: st.battery,
    ),
    ProscenicSensorSpec(
        SensorEntityDescription(
            key="cleaned_area",
            translation_key="cleaned_area",
            native_unit_of_measurement=UnitOfArea.SQUARE_METERS,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=1,
        ),
        lambda st: st.clean_area,
    ),
    ProscenicSensorSpec(
        SensorEntityDescription(
            key="cleaning_time",
            translation_key="cleaning_time",
            native_unit_of_measurement=UnitOfTime.SECONDS,
            state_class=SensorStateClass.MEASUREMENT,
            suggested_display_precision=0,
        ),
        lambda st: (st.clean_time // 60) if st.clean_time is not None else None,
    ),
    ProscenicSensorSpec(
        SensorEntityDescription(
            key="filter_health",
            translation_key="filter_health",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        lambda st: st.filter_health,
    ),
    ProscenicSensorSpec(
        SensorEntityDescription(
            key="side_brush_health",
            translation_key="side_brush_health",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        lambda st: st.side_brush_health,
    ),
    ProscenicSensorSpec(
        SensorEntityDescription(
            key="brush_health",
            translation_key="brush_health",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        lambda st: st.brush_health,
    ),
    ProscenicSensorSpec(
        SensorEntityDescription(
            key="sensor_health",
            translation_key="sensor_health",
            native_unit_of_measurement=PERCENTAGE,
            state_class=SensorStateClass.MEASUREMENT,
            entity_category=EntityCategory.DIAGNOSTIC,
        ),
        lambda st: st.sensor_health,
    ),
)

RAW_DESC = SensorEntityDescription(
    key="raw_dps",
    translation_key="raw_dps",
    entity_category=EntityCategory.DIAGNOSTIC,
)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator: ProscenicCoordinator = data["coordinator"]
    show_raw: bool = bool(data.get("show_raw_dps", False))

    entities: list[SensorEntity] = [ProscenicSensor(entry, coordinator, spec) for spec in SPECS]
    if show_raw:
        entities.append(ProscenicRawDps(entry, coordinator))

    async_add_entities(entities, update_before_add=False)


class ProscenicBase(CoordinatorEntity[ProscenicCoordinator]):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, coordinator: ProscenicCoordinator) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._device_id = entry.data["device_id"]

    @property
    def device_info(self) -> dict[str, Any]:
        model = self.coordinator.data.device_model if self.coordinator.data else None
        return {
            "identifiers": {(DOMAIN, self._device_id)},
            "manufacturer": MANUFACTURER,
            "model": model or "Proscenic",
        }


class ProscenicSensor(ProscenicBase, SensorEntity):
    def __init__(self, entry: ConfigEntry, coordinator: ProscenicCoordinator, spec: ProscenicSensorSpec) -> None:
        super().__init__(entry, coordinator)
        self.entity_description = spec.desc
        self._spec = spec
        self._attr_unique_id = f"{self._device_id}_{spec.desc.key}"

    @property
    def native_value(self) -> Any:
        st: ProscenicState = self.coordinator.data
        if not st:
            return None
        return self._spec.value_fn(st)


class ProscenicRawDps(ProscenicBase, SensorEntity):
    entity_description = RAW_DESC
    _attr_icon = "mdi:code-json"

    def __init__(self, entry: ConfigEntry, coordinator: ProscenicCoordinator) -> None:
        super().__init__(entry, coordinator)
        self._attr_unique_id = f"{self._device_id}_raw_dps"

    @property
    def native_value(self) -> str | None:
        st = self.coordinator.data
        return "ok" if st and st.raw_dps else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        st = self.coordinator.data
        return {"dps": st.raw_dps} if st else {}