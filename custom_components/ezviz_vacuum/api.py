"""Accès bas niveau au robot, isolé du reste de l'intégration.

Tous les appels de ce module sont bloquants : ils sont systématiquement
exécutés dans un thread par le coordinateur.
"""

from __future__ import annotations

import logging
from typing import Any

from pyezvizapi import EzvizClient

from .const import (
    ACTION_CLEAN,
    ACTION_RECHARGE,
    CONSUMABLES,
    DEVICE_CATEGORY,
    DOMAIN_CLEAN_TASK,
    DOMAIN_CONSUMABLE,
    DOMAIN_MAP,
    DOMAIN_POWER,
    DOMAIN_TASK,
    LOCAL_INDEX,
    PROP_BATTERY,
    PROP_CURRENT_TASK,
    PROP_MAP_BASIC,
    PROP_ROOM_BASIC,
    PROP_ROOM_CUSTOM,
    PROP_STD_CLEAN,
    CLEAN_CUSTOM,
    ORDER_EXCLUDED,
    RESOURCE,
    SOURCE_MOBILE,
)

_LOGGER = logging.getLogger(__name__)


class EzvizVacuumApi:
    """Enveloppe orientée aspirateur autour de `pyezvizapi`."""

    def __init__(self, client: EzvizClient) -> None:
        self._client = client

    # ------------------------------------------------------------------
    # Découverte
    # ------------------------------------------------------------------
    def discover(self) -> dict[str, dict[str, Any]]:
        """Renvoie les aspirateurs du compte, indexés par numéro de série."""
        found: dict[str, dict[str, Any]] = {}
        for serial, device in self._client.get_device_infos().items():
            infos = device.get("deviceInfos") or {}
            if infos.get("deviceCategory") == DEVICE_CATEGORY:
                found[serial] = infos
        return found

    # ------------------------------------------------------------------
    # Lecture
    # ------------------------------------------------------------------
    def _read(self, serial: str, domain: str, prop: str) -> Any:
        """Lit une propriété, ou None si l'appareil ne la gère pas.

        L'API répond systématiquement HTTP 200 : c'est le code interne qui
        distingue une valeur d'un refus.
        """
        try:
            response = self._client.get_device_feature_value(
                serial, RESOURCE, domain, prop, local_index=LOCAL_INDEX
            )
        except Exception as err:  # noqa: BLE001 - la lib lève large
            _LOGGER.debug("Lecture %s.%s impossible : %s", domain, prop, err)
            return None

        if (response.get("meta") or {}).get("code") != 200:
            _LOGGER.debug("Lecture %s.%s refusée : %s", domain, prop, response)
            return None
        return response.get("data")

    def fetch_live(self, serial: str) -> dict[str, Any]:
        """Les données qui changent vite : tâche en cours et batterie."""
        return {
            "task": self._read(serial, DOMAIN_TASK, PROP_CURRENT_TASK) or {},
            "battery": self._read(serial, DOMAIN_POWER, PROP_BATTERY),
        }

    def fetch_slow(self, serial: str) -> dict[str, Any]:
        """Ce qui bouge lentement : consommables, cartes, pièces, mode."""
        consumables: dict[str, Any] = {}
        for prop, (key, _label) in CONSUMABLES.items():
            value = self._read(serial, DOMAIN_CONSUMABLE, prop)
            if isinstance(value, dict):
                consumables[key] = value

        slow = {
            "consumables": consumables,
            "std_clean": self._read(serial, DOMAIN_MAP, PROP_STD_CLEAN),
            "maps": self._read(serial, DOMAIN_MAP, PROP_MAP_BASIC),
            "rooms": self._read(serial, DOMAIN_MAP, PROP_ROOM_BASIC),
            "room_cfg": self._read(serial, DOMAIN_MAP, PROP_ROOM_CUSTOM),
        }
        # RoomBasicProperty ne renvoie pas toujours le tableau attendu : on
        # trace sa forme réelle pour pouvoir s'y adapter.
        _LOGGER.debug(
            "Formes lues - maps=%s rooms=%s room_cfg=%s std_clean=%s",
            type(slow["maps"]).__name__,
            repr(slow["rooms"])[:400],
            type(slow["room_cfg"]).__name__,
            type(slow["std_clean"]).__name__,
        )
        return slow

    # ------------------------------------------------------------------
    # Écriture
    # ------------------------------------------------------------------
    def _action(self, serial: str, domain: str, action: str, value: Any) -> None:
        """Envoie une commande et vérifie que l'appareil l'a bien reçue.

        Un `200` seul ne prouve rien : il peut n'émaner que du cloud. Seul le
        bloc `deviceMeta` atteste que le robot a répondu.
        """
        response = self._client.set_iot_action(
            serial, RESOURCE, LOCAL_INDEX, domain, action, value
        )
        meta = response.get("meta") or {}
        device_meta = (meta.get("moreInfo") or {}).get("deviceMeta")
        if device_meta is None:
            _LOGGER.warning(
                "%s.%s : le cloud a répondu mais le robot n'a pas accusé "
                "réception (%s)",
                domain,
                action,
                response,
            )
        elif device_meta.get("errorMsg") != "success":
            raise RuntimeError(f"Le robot a refusé {domain}.{action} : {device_meta}")

    def clean(self, serial: str, action: str) -> None:
        """`action` vaut start, pause, resume ou stop."""
        self._action(
            serial,
            DOMAIN_CLEAN_TASK,
            ACTION_CLEAN,
            {"action": action, "source": SOURCE_MOBILE},
        )

    def recharge(self, serial: str, action: str = "start") -> None:
        """Renvoie le robot à sa base, ou interrompt ce retour avec `stop`."""
        self._action(
            serial,
            DOMAIN_TASK,
            ACTION_RECHARGE,
            {"action": action, "source": SOURCE_MOBILE},
        )

    def clean_rooms(
        self,
        serial: str,
        room_ids: set[tuple[int, int]],
        room_cfg: Any,
        std_clean: Any,
        map_id: int,
    ) -> None:
        """Lance un nettoyage limité aux pièces demandées.

        Le robot n'a pas de commande « nettoie telle pièce » : la sélection est
        un réglage. On donne un ordre de passage positif aux pièces voulues et
        `-1` aux autres, on bascule la carte en mode `custom`, puis on lance un
        nettoyage normal.
        """
        if not isinstance(room_cfg, list) or not isinstance(std_clean, list):
            raise RuntimeError(
                "Configuration des pièces illisible : nettoyage par zone "
                "impossible."
            )

        # 1. Ordre de passage : positif pour les pièces retenues, -1 sinon.
        cfg_payload = []
        rank = 0
        for map_entry in room_cfg:
            entry = dict(map_entry)
            entry_map = entry.get("mapID")
            rooms = []
            for room in entry.get("room", []):
                room = dict(room)
                if (entry_map, room.get("roomID")) in room_ids:
                    rank += 1
                    room["order"] = rank
                else:
                    room["order"] = ORDER_EXCLUDED
                rooms.append(room)
            entry["room"] = rooms
            cfg_payload.append(entry)

        self._client.set_iot_feature(
            serial, RESOURCE, LOCAL_INDEX, DOMAIN_MAP, PROP_ROOM_CUSTOM, cfg_payload
        )

        # 2. La carte doit être en mode « personnalisé par pièce ».
        std_payload = []
        for entry in std_clean:
            entry = dict(entry)
            if entry.get("mapID") == map_id:
                entry["cleanConfigType"] = CLEAN_CUSTOM
            std_payload.append(entry)

        self._client.set_iot_feature(
            serial, RESOURCE, LOCAL_INDEX, DOMAIN_MAP, PROP_STD_CLEAN, std_payload
        )

        # 3. Le démarrage est la commande habituelle.
        self.clean(serial, "start")

    def set_fan_mode(self, serial: str, fan_mode: str, std_clean: Any) -> None:
        """Écrit `fanMode` sur toutes les cartes du robot.

        `StdCleanCfg` est un tableau — une entrée par carte — et l'écriture
        remplace la valeur entière : il faut donc renvoyer le tableau complet.
        """
        if not isinstance(std_clean, list) or not std_clean:
            raise RuntimeError(
                "Configuration de nettoyage illisible : impossible de régler "
                "la puissance d'aspiration."
            )
        payload = [dict(entry) for entry in std_clean]
        for entry in payload:
            entry["fanMode"] = fan_mode
        self._client.set_iot_feature(
            serial, RESOURCE, LOCAL_INDEX, DOMAIN_MAP, PROP_STD_CLEAN, payload
        )
