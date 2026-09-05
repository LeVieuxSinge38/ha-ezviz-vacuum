#!/usr/bin/env python3
"""
Deuxieme passe : les actions 'Set...' du robot EZVIZ.

Le premier balayage (ezviz_fan_probe.py) a rapporte une seule trouvaille, mais
elle vaut une methode :

    SweeperMapMgr.SetCleanCfg  sid=20  direction=Plt2Dev
    input = {mapID: integer, cleanConfigType: universal|custom}

D'ou trois enseignements :
  - les actions de REGLAGE existent, et vivent dans SweeperMapMgr ;
  - elles se nomment 'Set' + le nom d'une propriete du domaine ;
  - les sid connus sont 3, 6 et 20 : il en reste une quinzaine a nommer.

Ce script n'essaie donc que des noms NOUVEAUX - aucun de ceux deja ecartes par
la premiere passe - construits en miroir des proprietes connues du robot :
StdCleanCfg, RoomCustomCleanCfg, MapBasicProperty, RoomBasicProperty,
VirtualWall, ForbiddenRegion. C'est dans StdCleanCfg que vivent fanMode,
waterQuantity et cleanTimes ; une action 'SetStdCleanCfg' serait la reponse.

Quelques 'Get...' sont inclus : s'ils repondent, la famille est plus large que
prevu et le robot se laisse interroger action par action.

Toutes les valeurs envoyees sont invalides (chaine de 300 caracteres, refusee
par tous les types). Le robot ne peut rien executer et ne bouge pas.

Usage :
    python3 ezviz_fan_probe2.py [SERIAL]
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
OUTFILE = "ezviz_fan_probe2.json"

INVALID = "Z" * 300

NOT_SUPPORTED = "设备不支持该功能"   # ce nom n'existe pas
NOT_DECLARED = "设备功能未报备"      # route action, nom non declare

#: SweeperMapMgr en premier : c'est lui qui a livre SetCleanCfg.
DOMAINS = [
    "SweeperMapMgr",
    "SweeperCleanTask",
    "SweeperTaskMgr",
    "SweeperMgr",
]

NAMES = [
    # --- en miroir exact des proprietes du domaine (la piste principale)
    "SetStdCleanCfg", "SetRoomCustomCleanCfg", "SetRoomCleanCfg",
    "SetCustomCleanCfg", "SetMapBasicProperty", "SetRoomBasicProperty",
    "SetVirtualWall", "SetForbiddenRegion",
    # --- aspiration
    "SetFanCfg", "SetFanLevel", "SetFanPower", "SetSuctionMode",
    "SetSuctionLevel", "SetWindLevel", "SetWindPower", "SetWindMode",
    # --- eau et serpillere
    "SetWaterCfg", "SetWaterLevel", "SetWaterVolume", "SetWaterMode",
    "SetMopCfg", "SetMopMode", "SetMopLevel",
    # --- nombre de passages
    "SetCleanTimesCfg", "SetCleanCount", "SetRepeatTimes", "SetCleanRepeat",
    # --- la configuration sous d'autres noms
    "SetCleanParam", "SetCleanParameter", "SetCleanPreference",
    "SetCleanMode", "SetSweepMode", "SetWorkMode",
    "SetGlobalCleanCfg", "SetUniversalCleanCfg", "SetDefaultCleanCfg",
    # --- pieces et cartes
    "SetRoomOrder", "SetCleanOrder", "SetRoomSort", "SetRoomProperty",
    "SetRoomName", "SetMap", "SetCurrentMap", "SetUseMap", "SelectMap",
    "SwitchMap",
    # --- la famille Get existe-t-elle ?
    "GetCleanCfg", "GetStdCleanCfg", "GetRoomCustomCleanCfg",
]


def classify(err: str) -> str:
    if NOT_SUPPORTED in err:
        return "absent"
    if NOT_DECLARED in err:
        return "non-declare"
    if "Profile.Actions" in err or "Profile.Props" in err or "schema=" in err:
        return "TROUVE"
    return "autre"


def main() -> None:
    serial = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERIAL).upper()

    # Sur une version trop ancienne de pyezvizapi, set_iot_action n'existe pas
    # et chaque essai echoue en local sans qu'aucune requete ne parte. Le
    # balayage semble se derouler et ne rapporte rien : on coupe court.
    if not hasattr(EzvizClient, "set_iot_action"):
        sys.exit(
            "pyezvizapi est trop ancienne : elle n'a pas set_iot_action.\n"
            "Mettre a jour avec :\n"
            "    python3 -m pip install --upgrade 'pyezvizapi>=1.0.5'"
        )

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()

    total = len(DOMAINS) * len(NAMES)
    print(f"\nConnexion OK - cible : {serial}")
    print(f"{len(DOMAINS)} domaines x {len(NAMES)} noms = {total} requetes.")
    print("Aucune valeur envoyee n'est executable : le robot ne bougera pas.")
    print("Une trouvaille est signalee par <<< TROUVE en bout de ligne.\n")

    found: list[dict] = []
    tally: dict[str, int] = {}
    done = 0
    started = time.time()

    for domain in DOMAINS:
        for name in NAMES:
            try:
                result = client.set_iot_action(
                    serial, RESOURCE, IDX, domain, name, INVALID
                )
                verdict = "ACCEPTE"
                detail = json.dumps(result, ensure_ascii=False)
            except Exception as err:  # noqa: BLE001 - la lib leve large
                detail = str(err)
                verdict = classify(detail)

            tally[verdict] = tally.get(verdict, 0) + 1
            if verdict in ("TROUVE", "ACCEPTE", "autre"):
                found.append({"domain": domain, "name": name,
                              "verdict": verdict, "detail": detail[:20000]})

            done += 1
            rate = done / max(time.time() - started, 0.001)
            eta = int((total - done) / rate) if rate else 0
            flag = "  <<< TROUVE" if verdict in ("TROUVE", "ACCEPTE") else ""
            print(
                f"  [{done:3}/{total}] {domain}.{name:<24} {verdict:<12} "
                f"reste ~{eta // 60}m{eta % 60:02}s{flag}",
                flush=True,
            )
            if flag:
                print(f"        {detail[:800]}", flush=True)

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump({"tally": tally, "found": found}, fh,
                  indent=2, ensure_ascii=False)

    print("\n" + "=" * 72)
    print(f"Repartition : {tally}")
    print(f"{len(found)} piste(s). Resultat complet dans {OUTFILE}")
    if not found:
        print("\nBredouille. Le nom ne se devine pas : il reste a intercepter")
        print("le trafic de l'app EZVIZ pendant un changement d'aspiration.")


if __name__ == "__main__":
    main()
