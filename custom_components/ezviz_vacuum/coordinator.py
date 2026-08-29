"""Relevé périodique de l'état des aspirateurs."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import EzvizVacuumApi
from .const import DOMAIN, SLOW_EVERY, UPDATE_INTERVAL

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
        self._cycle = 0
        self._slow: dict[str, dict[str, Any]] = {}

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            return await self.hass.async_add_executor_job(self._fetch)
        except Exception as err:  # noqa: BLE001 - la lib lève large
            raise UpdateFailed(f"Relevé EZVIZ impossible : {err}") from err

    def _fetch(self) -> dict[str, dict[str, Any]]:
        refresh_slow = self._cycle % SLOW_EVERY == 0
        self._cycle += 1

        result: dict[str, dict[str, Any]] = {}
        for serial in self.devices:
            data = self.api.fetch_live(serial)
            if refresh_slow:
                self._slow[serial] = self.api.fetch_slow(serial)
            data.update(self._slow.get(serial, {}))
            result[serial] = data
        return result

    async def async_send(self, func, *args) -> None:
        """Exécute une commande puis rafraîchit l'état.

        Le robot met quelques secondes à publier son nouvel état ; un premier
        relevé immédiat renverrait encore l'ancien.
        """
        await self.hass.async_add_executor_job(func, *args)
        await self.async_request_refresh()
