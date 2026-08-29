"""Assistant de configuration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
)
from pyezvizapi import EzvizClient

from .api import EzvizVacuumApi
from .const import CONF_REGION_URL, DEFAULT_REGION, DOMAIN, REGIONS

_LOGGER = logging.getLogger(__name__)

STEP_USER = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Required(CONF_REGION_URL, default=DEFAULT_REGION): SelectSelector(
            SelectSelectorConfig(
                options=[
                    SelectOptionDict(value=url, label=label)
                    for url, label in REGIONS.items()
                ]
            )
        ),
    }
)


class EzvizVacuumConfigFlow(ConfigFlow, domain=DOMAIN):
    """Demande les identifiants EZVIZ et vérifie qu'un aspirateur répond."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_USERNAME].lower())
            self._abort_if_unique_id_configured()

            def _check() -> dict:
                client = EzvizClient(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_REGION_URL],
                )
                client.login()
                return EzvizVacuumApi(client).discover()

            try:
                devices = await self.hass.async_add_executor_job(_check)
            except Exception as err:  # noqa: BLE001 - la lib lève large
                message = str(err)
                if "1226" in message:
                    errors["base"] = "invalid_auth"
                elif "mfa" in message.lower() or "verification" in message.lower():
                    errors["base"] = "mfa_required"
                else:
                    _LOGGER.exception("Connexion à EZVIZ impossible")
                    errors["base"] = "cannot_connect"
            else:
                if not devices:
                    errors["base"] = "no_vacuum"
                else:
                    return self.async_create_entry(
                        title=f"EZVIZ Vacuum ({user_input[CONF_USERNAME]})",
                        data=user_input,
                    )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER, errors=errors
        )
