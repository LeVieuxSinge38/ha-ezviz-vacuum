"""Intégration EZVIZ Vacuum."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from pyezvizapi import EzvizClient

from .api import EzvizVacuumApi
from .const import CONF_REGION_URL, DEFAULT_REGION, DOMAIN
from .coordinator import EzvizVacuumCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SELECT, Platform.SENSOR, Platform.VACUUM]

EzvizVacuumConfigEntry = ConfigEntry[EzvizVacuumCoordinator]


async def async_setup_entry(
    hass: HomeAssistant, entry: EzvizVacuumConfigEntry
) -> bool:
    """Ouvre la session EZVIZ et met en place les entités."""

    def _connect() -> tuple[EzvizVacuumApi, dict]:
        client = EzvizClient(
            entry.data[CONF_USERNAME],
            entry.data[CONF_PASSWORD],
            entry.data.get(CONF_REGION_URL, DEFAULT_REGION),
        )
        client.login()
        api = EzvizVacuumApi(client)
        return api, api.discover()

    try:
        api, devices = await hass.async_add_executor_job(_connect)
    except Exception as err:  # noqa: BLE001 - la lib lève large
        message = str(err)
        # 1226 : « utilisateur inexistant ou mot de passe incorrect »
        if "1226" in message or "password" in message.lower():
            raise ConfigEntryAuthFailed(message) from err
        raise ConfigEntryNotReady(f"Connexion à EZVIZ impossible : {err}") from err

    if not devices:
        raise ConfigEntryNotReady(
            "Aucun aspirateur sur ce compte EZVIZ. Vérifie que le robot y est "
            "bien rattaché et qu'il est en ligne."
        )

    _LOGGER.debug("Aspirateurs détectés : %s", list(devices))

    coordinator = EzvizVacuumCoordinator(hass, entry, api, devices)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: EzvizVacuumConfigEntry
) -> bool:
    """Retire l'intégration."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
