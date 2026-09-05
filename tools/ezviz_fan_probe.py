#!/usr/bin/env python3
"""
Chasse a la commande qui REGLE le robot : aspiration, eau, nombre de passages.

Trois reglages, un seul objet : StdCleanCfg et RoomCustomCleanCfg portent
ensemble fanMode, waterQuantity et cleanTimes. Les ecrire en propriete
(route 'feature') renvoie 200 mais n'atteint jamais l'appareil. Il manque donc
une ACTION, sur la route qui, elle, arrive au robot.

ezviz_hunt.py avait deja ratisse 8 domaines x 60 noms - mais tous ces noms
parlaient de DEMARRER ou d'ARRETER (TaskCtrl, StartClean, GoCharge...). Pas un
seul nom de REGLAGE. L'action cherchee ici n'a donc jamais ete testee.

Deux hypotheses, dans cet ordre de vraisemblance :

  A. Les reglages voyagent DANS la commande de demarrage. L'app enverrait
     CleanCtrl avec fanMode a cote de action, plutot qu'un reglage separe.
     Le schema de CleanCtrl tranchera : il liste tous les champs acceptes.

  B. Il existe une action dediee, sous un nom qu'on n'a pas encore essaye
     (FanCtrl, WaterCtrl, SetCleanCfg...). C'est la phase 2.

Toutes les valeurs envoyees sont volontairement invalides : action inconnue,
chaine trop longue, mauvais type. Aucune ne peut etre executee, donc le robot
ne bouge pas de sa base pendant le balayage.

Usage :
    python3 ezviz_fan_probe.py [SERIAL]
"""

from __future__ import annotations

import getpass
import json
import sys
import time

from pyezvizapi import EzvizClient

REGION = "apiieu.ezvizlife.com"
DEFAULT_SERIAL = "BD1522206"
RESOURCE = "SweepingRobot"
IDX = "0"
OUTFILE = "ezviz_fan_probe.json"

INVALID = "Z" * 300
#: Action inexistante : le robot ne peut rien en faire, mais la validation du
#: serveur se prononce quand meme sur les AUTRES champs de l'objet.
INVALID_ACTION = "zzInvalide"

NOT_SUPPORTED = "设备不支持该功能"   # ce nom n'existe pas
NOT_DECLARED = "设备功能未报备"      # route action, nom non declare

# --- Phase 1 : les actions dont on sait deja qu'elles atteignent le robot.
KNOWN_ACTIONS = [
    ("SweeperCleanTask", "CleanCtrl"),
    ("SweeperTaskMgr", "RechargeCtrl"),
]

# --- Phase 1b : faire voyager un reglage a cote de 'action'.
# Si fanMode est un champ legitime de CleanCtrl, l'erreur ne portera que sur
# l'action inconnue. S'il est etranger au schema, le serveur le dira.
RIDERS = [
    ("fanMode a plat", {"action": INVALID_ACTION, "source": "mobile",
                        "fanMode": "strong"}),
    ("les trois reglages a plat", {"action": INVALID_ACTION, "source": "mobile",
                                   "fanMode": "strong",
                                   "waterQuantity": "middle",
                                   "cleanTimes": 2}),
    ("reglages imbriques", {"action": INVALID_ACTION, "source": "mobile",
                            "cleanCfg": {"fanMode": "strong"}}),
    ("temoin, action seule", {"action": INVALID_ACTION, "source": "mobile"}),
]

# --- Phase 2 : les noms d'action jamais essayes.
DOMAINS = [
    "SweeperCleanTask",
    "SweeperTaskMgr",
    "SweeperMapMgr",
    "SweeperMgr",
    "SweeperCtrlMgr",
    "SweeperSetting",
    "SweeperConfigMgr",
]

NAMES = [
    # aspiration
    "FanCtrl", "FanModeCtrl", "SetFanMode", "FanSetting", "FanModeSet",
    "SuctionCtrl", "SuctionMode", "WindCtrl", "WindMode", "WindPower",
    "PowerMode", "PowerCtrl", "CleanPowerCtrl",
    # eau et serpillere
    "WaterCtrl", "WaterMode", "WaterQuantityCtrl", "SetWaterQuantity",
    "WaterVolumeCtrl", "MopCtrl", "MopMode", "MopSetting",
    # nombre de passages
    "CleanTimesCtrl", "SetCleanTimes", "RepeatCtrl", "CleanCountCtrl",
    # la configuration en bloc - le plus probable si A echoue
    "CleanCfgCtrl", "SetCleanCfg", "StdCleanCfgCtrl", "CleanConfigCtrl",
    "CleanModeCtrl", "SweepModeCtrl", "ConfigCtrl", "SetConfig",
    "CleanParamCtrl", "ParamCtrl", "SettingCtrl", "PreferenceCtrl",
    "CfgCtrl", "ModeCtrl",
    # par piece
    "RoomCleanCtrl", "RoomCustomCleanCtrl", "CustomCleanCtrl",
    "RoomCfgCtrl", "SelectRoomCtrl", "AreaCleanCtrl",
]


def classify(err: str) -> str:
    if NOT_SUPPORTED in err:
        return "absent"
    if NOT_DECLARED in err:
        return "non-declare"
    if "Profile.Props" in err or "schema=" in err:
        return "TROUVE"
    return "autre"


def attempt(client, serial, domain, name, value):
    """Envoie une valeur invalide et rapporte ce que le serveur en dit."""
    try:
        result = client.set_iot_action(serial, RESOURCE, IDX, domain, name, value)
        return "ACCEPTE", json.dumps(result, ensure_ascii=False)
    except Exception as err:  # noqa: BLE001 - la lib leve large
        detail = str(err)
        return classify(detail), detail


def phase_schemas(client, serial) -> list[dict]:
    """Le schema complet des actions qui marchent deja.

    C'est la question centrale : CleanCtrl accepte-t-il autre chose que
    'action' et 'source' ? Le serveur renvoie l'enumeration de chaque champ
    des qu'on lui envoie une valeur invalide.
    """
    print("=" * 72)
    print("PHASE 1 - LE SCHEMA DES ACTIONS CONNUES")
    print("=" * 72)
    print("Si fanMode, waterQuantity ou cleanTimes apparaissent la-dedans,")
    print("les reglages passent par la commande de demarrage et c'est gagne.\n")

    out = []
    for domain, name in KNOWN_ACTIONS:
        verdict, detail = attempt(client, serial, domain, name, INVALID)
        print(f"  {domain}.{name} -> {verdict}")
        print(f"      {detail[:1500]}\n", flush=True)
        out.append({"domain": domain, "name": name,
                    "verdict": verdict, "detail": detail[:20000]})
    return out


def phase_riders(client, serial) -> list[dict]:
    """Glisser un reglage a cote d'une action volontairement inconnue."""
    print("=" * 72)
    print("PHASE 1b - UN REGLAGE EN PASSAGER DE CleanCtrl")
    print("=" * 72)
    print("L'action est fausse, donc rien ne peut s'executer. Ce qu'on lit,")
    print("c'est si le serveur reconnait les champs qui l'accompagnent.")
    print("Comparer chaque essai au temoin de la derniere ligne.\n")

    out = []
    for label, value in RIDERS:
        verdict, detail = attempt(
            client, serial, "SweeperCleanTask", "CleanCtrl", value
        )
        print(f"  {label:<28} -> {verdict}")
        print(f"      {detail[:600]}\n", flush=True)
        out.append({"label": label, "value": value,
                    "verdict": verdict, "detail": detail[:8000]})
    return out


def phase_hunt(client, serial) -> tuple[list[dict], dict[str, int]]:
    """Balayage des noms d'action orientes reglage."""
    print("=" * 72)
    print("PHASE 2 - LES NOMS DE REGLAGE JAMAIS ESSAYES")
    print("=" * 72)
    print(f"{len(DOMAINS)} domaines x {len(NAMES)} noms, route 'action' seule.")
    print("Une trouvaille est signalee par <<< TROUVE en bout de ligne.\n")

    found: list[dict] = []
    tally: dict[str, int] = {}
    total = len(DOMAINS) * len(NAMES)
    done = 0
    started = time.time()

    for domain in DOMAINS:
        for name in NAMES:
            verdict, detail = attempt(client, serial, domain, name, INVALID)
            tally[verdict] = tally.get(verdict, 0) + 1
            if verdict in ("TROUVE", "ACCEPTE", "autre"):
                found.append({"domain": domain, "name": name,
                              "verdict": verdict, "detail": detail[:8000]})

            done += 1
            rate = done / max(time.time() - started, 0.001)
            eta = int((total - done) / rate) if rate else 0
            flag = "  <<< TROUVE" if verdict in ("TROUVE", "ACCEPTE") else ""
            print(
                f"  [{done:3}/{total}] {domain}.{name:<22} {verdict:<12} "
                f"reste ~{eta // 60}m{eta % 60:02}s{flag}",
                flush=True,
            )
            if flag:
                print(f"        {detail[:600]}", flush=True)

    return found, tally


def main() -> None:
    serial = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERIAL).upper()

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"\nConnexion OK - cible : {serial}")
    print("Aucune valeur envoyee n'est executable : le robot ne bougera pas.\n")

    schemas = phase_schemas(client, serial)
    riders = phase_riders(client, serial)
    found, tally = phase_hunt(client, serial)

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump({"schemas": schemas, "riders": riders,
                   "tally": tally, "found": found},
                  fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 72)
    print(f"Repartition : {tally}")
    print(f"{len(found)} piste(s) en phase 2. Resultat complet dans {OUTFILE}")
    if not found:
        print("\nPhase 2 bredouille. Si la phase 1 n'a rien montre non plus,")
        print("il reste a intercepter le trafic de l'app EZVIZ.")


if __name__ == "__main__":
    main()
