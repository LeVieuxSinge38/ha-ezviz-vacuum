#!/usr/bin/env python3
"""
Chasse aux proprietes et actions CACHEES du robot EZVIZ.

Constat : ecrire taskState sur CurrentTask renvoie 200 mais le robot ne bouge
pas. CurrentTask est declaree 'rwu' - le 'u' pour upload : l'appareil REMONTE
cette propriete. Y ecrire met a jour le cache du cloud, sans rien commander.

D'ou l'idee : la vraie commande est ailleurs, dans une propriete EN ECRITURE
SEULE. Or une telle propriete n'apparait jamais dans FEATURE_INFO, qui ne
liste que ce qui se lit. Elle etait donc invisible depuis le debut.

La fuite de schema, elle, la revele : on ecrit une valeur invalide sur un nom
candidat et la reponse tranche.

  - schema detaille renvoye     -> LA PROPRIETE EXISTE (valeur refusee)
  - 设备不支持该功能             -> ce nom n'existe pas
  - 设备功能未报备               -> route action, nom non declare

Toutes les valeurs envoyees sont volontairement invalides : trop longues pour
une chaine, du mauvais type pour tout le reste. Aucune ne peut etre ecrite,
donc le robot ne peut pas bouger.

Usage :
    python3 ezviz_hunt.py [SERIAL]
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
OUTFILE = "ezviz_hunt.json"

INVALID = "Z" * 300

NOT_SUPPORTED = "设备不支持该功能"   # ce nom n'existe pas
NOT_DECLARED = "设备功能未报备"      # route action, nom non declare

DOMAINS = [
    "SweeperTaskMgr",
    "SweeperCleanTask",
    "SweeperMgr",
    "SweeperCtrlMgr",
    "SweeperMapMgr",
    "PowerMgr",
    "InfoMgr",
    "SoundSetting",
]

NAMES = [
    # commande de tache
    "TaskCtrl", "TaskControl", "TaskCmd", "TaskSwitch", "TaskOperation",
    "StartTask", "StopTask", "PauseTask", "ContinueTask", "CancelTask",
    "SetCurrentTask", "TargetTask", "TaskTarget", "ExpectTask", "NextTask",
    # commande de nettoyage
    "CleanCtrl", "CleanControl", "CleanCmd", "CleanSwitch", "CleanMode",
    "StartClean", "StopClean", "PauseClean", "GlobalClean", "RoomClean",
    "AreaClean", "SpotClean", "CustomClean", "SelectClean", "CleanTask",
    "CleanOperation", "CleanRequest", "StartCleanTask", "CleanTaskCtrl",
    # base et deplacement
    "BackCharge", "GoCharge", "Recharge", "ReturnDock", "GoHome",
    "ChargeCtrl", "DockCtrl", "MoveCtrl", "RemoteCtrl", "FindRobot",
    "LocateRobot", "FixedMotion",
    # generique
    "Ctrl", "Control", "Command", "Cmd", "Operation", "Action", "Switch",
    "WorkMode", "WorkState", "DeviceCtrl", "RobotCtrl", "SweeperCtrl",
]


def classify(err: str) -> str:
    if NOT_SUPPORTED in err:
        return "absent"
    if NOT_DECLARED in err:
        return "non-declare"
    if "Profile.Props" in err or "schema=" in err:
        return "TROUVE"
    return "autre"


def main() -> None:
    serial = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERIAL).upper()

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"\nConnexion OK - cible : {serial}")
    print(f"{len(DOMAINS)} domaines x {len(NAMES)} noms, sur deux routes.")
    print("Seules les trouvailles sont affichees. Compter quelques minutes.\n")

    found: list[dict] = []
    tally: dict[str, int] = {}

    for domain in DOMAINS:
        for name in NAMES:
            for route, fn in (
                ("feature", client.set_iot_feature),
                ("action", client.set_iot_action),
            ):
                try:
                    result = fn(serial, RESOURCE, IDX, domain, name, INVALID)
                    verdict, detail = "ACCEPTE", json.dumps(result, ensure_ascii=False)
                except Exception as err:  # noqa: BLE001
                    detail = str(err)
                    verdict = classify(detail)

                tally[verdict] = tally.get(verdict, 0) + 1
                if verdict in ("TROUVE", "ACCEPTE", "autre"):
                    print(f"  [{verdict}] {route} / {domain} / {name}")
                    print(f"      {detail[:400]}")
                    found.append({
                        "route": route, "domain": domain, "name": name,
                        "verdict": verdict, "detail": detail[:6000],
                    })
            time.sleep(0.03)
        print(f"  ... {domain} termine")

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump({"tally": tally, "found": found}, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"Repartition : {tally}")
    print(f"{len(found)} piste(s). Resultat dans {OUTFILE}")
    if not found:
        print("\nAucune trouvaille : la commande ne passe pas par un nom devinable.")
        print("Il faudra intercepter le trafic de l'app EZVIZ.")


if __name__ == "__main__":
    main()
