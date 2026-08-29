"""L'entité aspirateur."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzvizVacuumConfigEntry
from .const import (
    CLEANING_STATES,
    FAN_SPEEDS,
    PAUSED_STATES,
    RETURNING_STATES,
    STATE_DRYING_MOP,
)
from .entity import EzvizVacuumBaseEntity

_LOGGER = logging.getLogger(__name__)


def _supported_features() -> VacuumEntityFeature:
    """`STATE` a été retiré de certaines versions : on ne l'ajoute que s'il existe."""
    features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.SEND_COMMAND
    )
    if hasattr(VacuumEntityFeature, "STATE"):
        features |= VacuumEntityFeature.STATE
    return features


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzvizVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        EzvizVacuum(coordinator, serial) for serial in coordinator.devices
    )


class EzvizVacuum(EzvizVacuumBaseEntity, StateVacuumEntity):
    """Un robot aspirateur EZVIZ."""

    _attr_name = None
    _attr_supported_features = _supported_features()
    _attr_fan_speed_list = list(FAN_SPEEDS.values())

    def __init__(self, coordinator, serial: str) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = serial
        #: `taskState` retombe brièvement à vide pendant un nettoyage continu.
        #: On mémorise la dernière activité franche pour ne pas clignoter.
        self._last_activity: VacuumActivity | None = None

    # ------------------------------------------------------------------
    # État
    # ------------------------------------------------------------------
    @property
    def activity(self) -> VacuumActivity | None:
        task = self._task
        if not task:
            return None

        if task.get("exception"):
            return VacuumActivity.ERROR

        state = task.get("taskState") or ""
        charging = bool(task.get("inCharging"))

        if state in CLEANING_STATES:
            self._last_activity = VacuumActivity.CLEANING
        elif state in PAUSED_STATES:
            self._last_activity = VacuumActivity.PAUSED
        elif state in RETURNING_STATES:
            self._last_activity = VacuumActivity.RETURNING
        elif state == STATE_DRYING_MOP or charging:
            self._last_activity = VacuumActivity.DOCKED
        elif state:
            self._last_activity = VacuumActivity.IDLE
        elif self._last_activity in (
            VacuumActivity.CLEANING,
            VacuumActivity.PAUSED,
            VacuumActivity.RETURNING,
        ):
            # État vide alors que le robot est hors base : c'est le
            # clignotement connu de taskState, on garde l'activité précédente.
            pass
        else:
            self._last_activity = VacuumActivity.IDLE

        return self._last_activity

    @property
    def fan_speed(self) -> str | None:
        std_clean = self._data.get("std_clean")
        if not isinstance(std_clean, list) or not std_clean:
            return None
        first = std_clean[0]
        if not isinstance(first, dict):
            return None
        return FAN_SPEEDS.get(first.get("fanMode"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        task = self._task
        attributes: dict[str, Any] = {
            "task_state": task.get("taskState"),
            "in_charging": bool(task.get("inCharging")),
        }
        if error := task.get("exception"):
            attributes["error_code"] = error

        maps = self._data.get("maps")
        if isinstance(maps, list):
            attributes["maps"] = [
                {"id": m.get("mapID"), "name": m.get("mapName"),
                 "in_use": bool(m.get("inUse"))}
                for m in maps
            ]

        rooms = self._data.get("rooms")
        if isinstance(rooms, list):
            attributes["rooms"] = [
                {"map_id": entry.get("mapID"),
                 "id": room.get("roomID"),
                 "name": room.get("roomName")}
                for entry in rooms
                for room in entry.get("room", [])
            ]
        return attributes

    # ------------------------------------------------------------------
    # Commandes
    # ------------------------------------------------------------------
    async def async_start(self) -> None:
        """Démarre, ou reprend si le robot était en pause."""
        action = "resume" if self.activity == VacuumActivity.PAUSED else "start"
        await self.coordinator.async_send(
            self.coordinator.api.clean, self._serial, action
        )

    async def async_pause(self) -> None:
        await self.coordinator.async_send(
            self.coordinator.api.clean, self._serial, "pause"
        )

    async def async_stop(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(
            self.coordinator.api.clean, self._serial, "stop"
        )

    async def async_return_to_base(self, **kwargs: Any) -> None:
        await self.coordinator.async_send(
            self.coordinator.api.recharge, self._serial, "start"
        )

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        mode = next(
            (key for key, label in FAN_SPEEDS.items() if label == fan_speed),
            fan_speed,
        )
        if mode not in FAN_SPEEDS:
            raise ValueError(f"Puissance d'aspiration inconnue : {fan_speed}")
        await self.coordinator.async_send(
            self.coordinator.api.set_fan_mode,
            self._serial,
            mode,
            self._data.get("std_clean"),
        )

    async def async_send_command(
        self,
        command: str,
        params: dict[str, Any] | list[Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Passe une commande brute, pour ce que l'entité n'expose pas.

        `clean` accepte start, pause, resume, stop ;
        `recharge` accepte start et stop.
        """
        if command == "clean":
            action = (params or {}).get("action", "start")
            await self.coordinator.async_send(
                self.coordinator.api.clean, self._serial, action
            )
        elif command == "recharge":
            action = (params or {}).get("action", "start")
            await self.coordinator.async_send(
                self.coordinator.api.recharge, self._serial, action
            )
        else:
            raise ValueError(f"Commande inconnue : {command}")
