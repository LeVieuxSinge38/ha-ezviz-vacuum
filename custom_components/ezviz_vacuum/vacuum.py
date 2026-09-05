"""L'entité aspirateur."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from homeassistant.components.vacuum import (
    StateVacuumEntity,
    VacuumActivity,
    VacuumEntityFeature,
)

from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import EzvizVacuumConfigEntry
from .const import (
    CLEANING_STATES,
    PAUSED_STATES,
    RETURNING_STATES,
    SILENCE_BLOQUE,
    STATE_DRYING_MOP,
)
from .entity import EzvizVacuumBaseEntity

_LOGGER = logging.getLogger(__name__)


def _supported_features() -> VacuumEntityFeature:
    """Uniquement ce qui atteint réellement le robot.

    Ni `FAN_SPEED` ni `CLEAN_AREA` : ils reposeraient sur des écritures de
    propriété, qui n'arrivent jamais jusqu'à l'appareil (voir le README).
    `STATE` a été retiré de certaines versions, d'où le test.
    """
    features = (
        VacuumEntityFeature.START
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
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

    def __init__(self, coordinator, serial: str) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = serial
        #: `taskState` retombe brièvement à vide pendant un nettoyage continu.
        #: On mémorise la dernière activité franche pour ne pas clignoter.
        self._last_activity: VacuumActivity | None = None
        #: Depuis quand le robot se tait. C'est ici que la durée du silence
        #: se mesure, et pas dans une carte : l'horloge de Home Assistant ne
        #: se fait pas geler, celle d'un navigateur de tablette murale si.
        self._silence_depuis: datetime | None = None

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

        # Le robot parle : on repart de zéro. Il se tait : on date le début
        # du silence, pour savoir plus bas s'il dure trop.
        if state:
            self._silence_depuis = None
        elif self._silence_depuis is None:
            self._silence_depuis = dt_util.utcnow()

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
        elif (
            self._last_activity
            in (
                VacuumActivity.CLEANING,
                VacuumActivity.PAUSED,
                VacuumActivity.RETURNING,
            )
            and dt_util.utcnow() - self._silence_depuis < SILENCE_BLOQUE
        ):
            # État vide alors que le robot est hors base : c'est le
            # clignotement connu de taskState, on garde l'activité précédente.
            #
            # Mais pas indéfiniment. Un robot coincé se tait pour de bon, et
            # sans cette borne l'entité restait « en nettoyage » des heures
            # durant — mesuré : roue soulevée, elle ne bascule jamais.
            pass
        else:
            self._last_activity = VacuumActivity.IDLE

        return self._last_activity

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
