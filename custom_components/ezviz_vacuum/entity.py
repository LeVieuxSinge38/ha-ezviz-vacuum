"""Socle commun aux entités : rattachement à l'appareil Home Assistant."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EzvizVacuumCoordinator


class EzvizVacuumBaseEntity(CoordinatorEntity[EzvizVacuumCoordinator]):
    """Entité rattachée à un aspirateur donné."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: EzvizVacuumCoordinator, serial: str) -> None:
        super().__init__(coordinator)
        self._serial = serial
        infos = coordinator.devices.get(serial, {})
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer="EZVIZ",
            model=infos.get("deviceType"),
            name=infos.get("name") or f"Aspirateur {serial}",
            sw_version=infos.get("version"),
            serial_number=serial,
        )

    @property
    def _data(self) -> dict[str, Any]:
        return (self.coordinator.data or {}).get(self._serial, {})

    @property
    def _task(self) -> dict[str, Any]:
        task = self._data.get("task")
        return task if isinstance(task, dict) else {}

    @property
    def available(self) -> bool:
        return super().available and self._serial in (self.coordinator.data or {})
