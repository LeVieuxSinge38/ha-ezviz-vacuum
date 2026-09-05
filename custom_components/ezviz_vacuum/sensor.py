"""Capteurs : batterie, usure des consommables, panne en cours."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzvizVacuumConfigEntry
from .const import CONSUMABLES, FAN_SPEEDS
from .entity import EzvizVacuumBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzvizVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SensorEntity] = []
    for serial in coordinator.devices:
        entities.append(EzvizVacuumBattery(coordinator, serial))
        entities.append(EzvizVacuumError(coordinator, serial))
        entities.append(EzvizVacuumFanMode(coordinator, serial))
        entities.extend(
            EzvizVacuumConsumable(coordinator, serial, key, label)
            for key, label in CONSUMABLES.values()
        )
    async_add_entities(entities)


class EzvizVacuumBattery(EzvizVacuumBaseEntity, SensorEntity):
    """Niveau de batterie.

    Entité séparée, et non attribut de l'aspirateur : depuis Home Assistant
    2025.8, la batterie portée par l'entité vacuum est dépréciée.
    """

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_name = "Batterie"

    def __init__(self, coordinator, serial: str) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_battery"

    @property
    def native_value(self) -> int | None:
        value = self._data.get("battery")
        return value if isinstance(value, int) else None


class EzvizVacuumError(EzvizVacuumBaseEntity, SensorEntity):
    """Code de panne remonté par le robot, ou « ok »."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Panne"

    def __init__(self, coordinator, serial: str) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_error"

    @property
    def native_value(self) -> str | None:
        if not self._task:
            return None
        return self._task.get("exception") or "ok"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"description": self._task.get("exceptionDesc") or ""}


class EzvizVacuumFanMode(EzvizVacuumBaseEntity, SensorEntity):
    """Puissance d'aspiration configurée sur le robot.

    Doublon assumé du `fan_speed` de l'entité aspirateur, qui lui se règle.
    Ce capteur est conservé parce qu'il existait avant, et qu'on ne casse pas
    les tableaux de bord qui le citent déjà.
    """

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_name = "Aspiration"

    def __init__(self, coordinator, serial: str) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_fan_mode"

    @property
    def native_value(self) -> str | None:
        mode = self._std_clean.get("fanMode")
        return FAN_SPEEDS.get(mode, mode)


class EzvizVacuumConsumable(EzvizVacuumBaseEntity, SensorEntity):
    """Heures restantes avant remplacement d'un consommable."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTime.HOURS
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, serial: str, key: str, label: str) -> None:
        super().__init__(coordinator, serial)
        self._key = key
        self._attr_name = label
        self._attr_unique_id = f"{serial}_consumable_{key}"

    @property
    def native_value(self) -> int | None:
        consumables = self._data.get("consumables") or {}
        entry = consumables.get(self._key)
        if not isinstance(entry, dict):
            return None
        value = entry.get("rest")
        return value if isinstance(value, int) else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        consumables = self._data.get("consumables") or {}
        entry = consumables.get(self._key) or {}
        return {"hours_used": entry.get("used")}
