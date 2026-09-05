"""Les réglages que l'entité aspirateur ne sait pas porter.

Home Assistant offre `fan_speed` pour la puissance d'aspiration, mais rien
pour le volume d'eau ni le nombre de passages. Ces deux-là vivent pourtant
dans le même objet `StdCleanCfg`, et s'écrivent de la même façon.
"""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import EzvizVacuumConfigEntry
from .const import CLEAN_TIMES, CLEAN_TIMES_DEFAULT, WATER_LEVELS
from .entity import EzvizVacuumBaseEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: EzvizVacuumConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = []
    for serial in coordinator.devices:
        entities.append(EzvizVacuumWater(coordinator, serial))
        entities.append(EzvizVacuumCleanTimes(coordinator, serial))
    async_add_entities(entities)


class EzvizVacuumWater(EzvizVacuumBaseEntity, SelectEntity):
    """Volume d'eau, de la serpillère sèche au débit maximal."""

    _attr_name = "Volume d'eau"
    _attr_options = list(WATER_LEVELS.values())

    def __init__(self, coordinator, serial: str) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_water"

    @property
    def current_option(self) -> str | None:
        level = self._std_clean.get("waterQuantity")
        return WATER_LEVELS.get(level)

    async def async_select_option(self, option: str) -> None:
        level = next(
            (key for key, label in WATER_LEVELS.items() if label == option), None
        )
        if level is None:
            raise ValueError(f"Volume d'eau inconnu : {option}")
        await self.coordinator.async_send(
            self.coordinator.api.set_water_quantity,
            self._serial,
            level,
            refresh_slow=True,
        )


class EzvizVacuumCleanTimes(EzvizVacuumBaseEntity, SelectEntity):
    """Nombre de passages sur chaque surface.

    Le robot publie parfois `0`, qu'il traite comme un passage unique : on
    l'affiche donc comme « Une fois » plutôt que de laisser l'entité vide.
    """

    _attr_name = "Passages"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = list(CLEAN_TIMES.values())

    def __init__(self, coordinator, serial: str) -> None:
        super().__init__(coordinator, serial)
        self._attr_unique_id = f"{serial}_clean_times"

    @property
    def current_option(self) -> str | None:
        times = self._std_clean.get("cleanTimes")
        if times is None:
            return None
        return CLEAN_TIMES.get(times or CLEAN_TIMES_DEFAULT)

    async def async_select_option(self, option: str) -> None:
        times = next(
            (key for key, label in CLEAN_TIMES.items() if label == option), None
        )
        if times is None:
            raise ValueError(f"Nombre de passages inconnu : {option}")
        await self.coordinator.async_send(
            self.coordinator.api.set_clean_times,
            self._serial,
            times,
            refresh_slow=True,
        )
