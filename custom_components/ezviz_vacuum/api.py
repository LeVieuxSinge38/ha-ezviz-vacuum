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
    PROP_STD_CLEAN,
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
        """Ce qui bouge lentement : consommables, cartes, mode de nettoyage."""
        consumables: dict[str, Any] = {}
        for prop, (key, _label) in CONSUMABLES.items():
            value = self._read(serial, DOMAIN_CONSUMABLE, prop)
            if isinstance(value, dict):
                consumables[key] = value

        return {
            "consumables": consumables,
            "std_clean": self._read(serial, DOMAIN_MAP, PROP_STD_CLEAN),
            "maps": self._read(serial, DOMAIN_MAP, PROP_MAP_BASIC),
            "rooms": self._read(serial, DOMAIN_MAP, PROP_ROOM_BASIC),
        }

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
