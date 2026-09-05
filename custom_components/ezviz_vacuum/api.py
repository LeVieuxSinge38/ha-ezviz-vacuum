"""Accès bas niveau au robot, isolé du reste de l'intégration.

Tous les appels de ce module sont bloquants : ils sont systématiquement
exécutés dans un thread par le coordinateur.
"""

from __future__ import annotations

import logging
from copy import deepcopy
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

    def _write(self, serial: str, domain: str, prop: str, value: Any) -> None:
        """Écrit une propriété.

        Contrairement aux actions, une écriture de propriété n'obtient jamais
        de `deviceMeta` : le cloud répond seul. Le `200` n'atteste donc que la
        réception côté serveur — c'est une relecture, quelques secondes plus
        tard, qui dit si l'appareil a adopté la valeur.
        """
        response = self._client.set_iot_feature(
            serial, RESOURCE, LOCAL_INDEX, domain, prop, value
        )
        if (response.get("meta") or {}).get("code") != 200:
            raise RuntimeError(f"Le cloud a refusé {domain}.{prop} : {response}")

    def _set_std_clean(self, serial: str, key: str, value: Any) -> None:
        """Change un réglage global : aspiration, eau ou nombre de passages.

        Le tableau est relu puis réécrit ENTIER. C'est tout le secret : une
        écriture partielle remplace l'objet par ce qu'on envoie, et le robot
        rejette silencieusement un `StdCleanCfg` amputé — d'où la conclusion,
        longtemps tenue pour acquise, que ces réglages n'étaient pas
        pilotables.

        La relecture précède chaque écriture pour ne pas réimposer des valeurs
        périmées si le réglage a bougé depuis l'application EZVIZ.
        """
        current = self._read(serial, DOMAIN_MAP, PROP_STD_CLEAN)
        if not isinstance(current, list) or not current:
            raise RuntimeError(
                "StdCleanCfg illisible : impossible de régler sans connaître "
                "la configuration en place"
            )

        updated = deepcopy(current)
        for entry in updated:
            if isinstance(entry, dict):
                entry[key] = value
        self._write(serial, DOMAIN_MAP, PROP_STD_CLEAN, updated)

    def set_fan_mode(self, serial: str, mode: str) -> None:
        """`mode` vaut quiet, normal, strong ou super."""
        self._set_std_clean(serial, "fanMode", mode)

    def set_water_quantity(self, serial: str, level: str) -> None:
        """`level` vaut dry, low, middle ou high."""
        self._set_std_clean(serial, "waterQuantity", level)

    def set_clean_times(self, serial: str, times: int) -> None:
        """Nombre de passages sur chaque surface."""
        self._set_std_clean(serial, "cleanTimes", times)

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
