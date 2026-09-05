"""Relevé périodique de l'état des aspirateurs."""

from __future__ import annotations

import asyncio
import logging
from time import monotonic
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EzvizVacuumApi
from .const import DOMAIN, SLOW_EVERY, UPDATE_INTERVAL, UPDATE_INTERVAL_ACTIF

_LOGGER = logging.getLogger(__name__)


class EzvizVacuumCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Interroge le cloud EZVIZ et distribue le résultat aux entités."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        api: EzvizVacuumApi,
        devices: dict[str, dict[str, Any]],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
            config_entry=entry,
        )
        self.api = api
        self.devices = devices
        #: Date du dernier relevé lent, pour l'espacer dans le temps.
        self._slow_at = 0.0
        self._slow: dict[str, dict[str, Any]] = {}
        #: Armé après une écriture qui touche les données lentes, pour ne pas
        #: attendre le prochain cycle long avant de les relire.
        self._force_slow = False

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            data = await self.hass.async_add_executor_job(self._fetch)
        except Exception as err:  # noqa: BLE001 - la lib lève large
            raise UpdateFailed(f"Relevé EZVIZ impossible : {err}") from err
        self._ajuster_cadence(data)
        return data

    def _ajuster_cadence(self, data: dict[str, dict[str, Any]]) -> None:
        """Relève vite quand le robot travaille, lentement quand il charge.

        Un robot arrimé ne réserve aucune surprise : le suivre de près ne
        ferait qu'user le quota d'appels. Hors de sa base, en revanche, la
        moindre seconde de retard se voit — c'est là qu'il se coince.
        """
        arrime = all(
            bool((appareil.get("task") or {}).get("inCharging"))
            for appareil in data.values()
        ) if data else True

        voulue = UPDATE_INTERVAL if arrime else UPDATE_INTERVAL_ACTIF
        if self.update_interval != voulue:
            _LOGGER.debug("Cadence du relevé : %s", voulue)
            self.update_interval = voulue

    def _fetch(self) -> dict[str, dict[str, Any]]:
        maintenant = monotonic()
        refresh_slow = (
            self._force_slow
            or maintenant - self._slow_at >= SLOW_EVERY.total_seconds()
        )
        self._force_slow = False
        if refresh_slow:
            self._slow_at = maintenant

        result: dict[str, dict[str, Any]] = {}
        for serial in self.devices:
            data = self.api.fetch_live(serial)
            if refresh_slow:
                self._slow[serial] = self.api.fetch_slow(serial)
            data.update(self._slow.get(serial, {}))
            result[serial] = data
        return result

    async def async_send(self, func, *args, refresh_slow: bool = False) -> None:
        """Exécute une commande puis rafraîchit l'état.

        `refresh_slow` force la relecture des données lentes — puissance
        d'aspiration, configuration des pièces. Sans lui, l'interface
        continuerait d'afficher l'ancienne valeur jusqu'au prochain cycle
        long, donnant l'impression que le réglage n'a pas pris.
        """
        await self.hass.async_add_executor_job(func, *args)
        if refresh_slow:
            self._force_slow = True
            # Le cloud met un instant à publier la nouvelle valeur.
            await asyncio.sleep(2)
        await self.async_request_refresh()

        # Le robot met une dizaine de secondes à se mettre en mouvement : le
        # relevé qui suit immédiatement la commande le montre encore inchangé.
        # On repasse donc le voir, pour que TOUS les écrans apprennent qu'il
        # est reparti sans attendre le cycle suivant — c'est ce qui laissait
        # un triangle de dépannage allumé sur une tablette murale après un
        # dépannage lancé depuis un téléphone.
        for delai in (8, 20):
            async_call_later(self.hass, delai, self._relire)

    @callback
    def _relire(self, _maintenant) -> None:
        """Relance un relevé, sans attendre son résultat."""
        self.hass.async_create_task(self.async_request_refresh())
