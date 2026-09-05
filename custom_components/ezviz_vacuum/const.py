"""Constantes de l'intégration EZVIZ Vacuum.

Les identifiants ci-dessous ont été relevés sur un EZVIZ RE5 Plus
(CS-RE5P-TWT) ; la démarche est documentée dans le README du dépôt.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "ezviz_vacuum"

CONF_REGION_URL: Final = "region_url"
DEFAULT_REGION: Final = "apiieu.ezvizlife.com"

REGIONS: Final = {
    "apiieu.ezvizlife.com": "Europe",
    "apius.ezvizlife.com": "Amérique du Nord",
    "apiisgp.ezvizlife.com": "Singapour",
    "apiiin.ezvizlife.com": "Inde",
    "apiiru.ezvizlife.com": "Russie",
}

#: Catégorie EZVIZ des robots aspirateurs.
DEVICE_CATEGORY: Final = "SweepingRobot"
RESOURCE: Final = "SweepingRobot"
LOCAL_INDEX: Final = "0"

UPDATE_INTERVAL: Final = timedelta(seconds=30)
#: Les consommables et les cartes bougent lentement : un relevé sur dix suffit.
SLOW_EVERY: Final = 10

# --- Lecture -----------------------------------------------------------
DOMAIN_TASK: Final = "SweeperTaskMgr"
PROP_CURRENT_TASK: Final = "CurrentTask"
DOMAIN_POWER: Final = "PowerMgr"
PROP_BATTERY: Final = "SurplusPower"
DOMAIN_MAP: Final = "SweeperMapMgr"
PROP_STD_CLEAN: Final = "StdCleanCfg"
PROP_MAP_BASIC: Final = "MapBasicProperty"
PROP_ROOM_BASIC: Final = "RoomBasicProperty"
PROP_ROOM_CUSTOM: Final = "RoomCustomCleanCfg"
DOMAIN_CONSUMABLE: Final = "SweeperConsumable"

# --- Écriture : c'est la route « action » qui commande, jamais « feature ».
DOMAIN_CLEAN_TASK: Final = "SweeperCleanTask"
ACTION_CLEAN: Final = "CleanCtrl"
ACTION_RECHARGE: Final = "RechargeCtrl"
SOURCE_MOBILE: Final = "mobile"

# --- Vocabulaire du robot ---------------------------------------------
STATE_STANDBY: Final = "standby"
STATE_CLEAN: Final = "clean"
STATE_CLEAN_PAUSE: Final = "cleanPause"
STATE_CLEAN_DONE_RECHARGE: Final = "cleanDoneRecharge"
STATE_DRYING_MOP: Final = "dryingMop"
STATE_INSPECT: Final = "inspect"
STATE_INSPECT_PAUSE: Final = "inspectPause"
STATE_INSPECT_DONE_RECHARGE: Final = "inspectDoneRecharge"
STATE_CONTINUE_CHARGING: Final = "continueCharging"

#: Un robot coincé cesse de publier son `taskState`. Mais il se tait aussi
#: par intermittence pendant un nettoyage normal — jusqu'à 40 secondes
#: d'affilée. Au-delà, le silence n'est plus un clignotement : il est bloqué.
SILENCE_BLOQUE: Final = timedelta(seconds=45)

RETURNING_STATES: Final = {
    STATE_CLEAN_DONE_RECHARGE,
    STATE_INSPECT_DONE_RECHARGE,
    STATE_CONTINUE_CHARGING,
}
CLEANING_STATES: Final = {STATE_CLEAN, STATE_INSPECT}
PAUSED_STATES: Final = {STATE_CLEAN_PAUSE, STATE_INSPECT_PAUSE}

#: `fanMode` du robot -> libellé présenté dans Home Assistant.
FAN_SPEEDS: Final = {
    "quiet": "Silencieux",
    "normal": "Standard",
    "strong": "Puissant",
    "super": "Maximum",
}

#: Ordre de nettoyage : -1 exclut la pièce de la tâche.
ORDER_EXCLUDED: Final = -1
#: `cleanConfigType` : toute la surface, ou sélection par pièce.
CLEAN_UNIVERSAL: Final = "universal"
CLEAN_CUSTOM: Final = "custom"

#: Consommables : propriété -> (clé d'entité, libellé).
CONSUMABLES: Final = {
    "MopWorkingTime": ("mop", "Serpillère"),
    "HepaWorkingTime": ("hepa", "Filtre HEPA"),
    "EdgeBrushWorkingTime": ("edge_brush", "Brosse latérale"),
    "RotatingBrushWorkingTime": ("rotating_brush", "Brosse rotative"),
    "SensorWorkingTime": ("sensors", "Capteurs"),
}
