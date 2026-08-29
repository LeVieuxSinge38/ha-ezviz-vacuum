#!/usr/bin/env python3
"""
Chasse aux proprietes et actions CACHEES du robot EZVIZ.

Cette version affiche chaque requete au fur et a mesure : un balayage muet ne
permet pas de distinguer un script qui travaille d'un script bloque.

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


def raw_put(client, path, value, **params):
    """PUT brut, pour essayer des parametres que la lib n'expose pas."""
    r = client._session.put(
        client._url(path), params=params or None, json=value, timeout=25
    )
    return r.status_code, r.text


def phase_force_check(client, serial) -> list[dict]:
    """Le champ forceCheck du PropertyRequest force peut-etre la transmission
    a l'appareil, au lieu d'une simple mise a jour du cache."""
    print("=" * 70)
    print("PHASE 0 - LE DRAPEAU forceCheck")
    print("=" * 70)
    print("Valeur volontairement invalide : si forceCheck existe, l'erreur")
    print("changera de nature. Le robot ne peut pas l'executer.\n")

    path = f"/v3/iot-feature/feature/{serial}/{RESOURCE}/{IDX}/SweeperTaskMgr/CurrentTask"
    out = []
    attempts = [
        ("forceCheck=true en parametre", {"forceCheck": "true"}, {"taskState": "zzInvalide"}),
        ("forceCheck=1 en parametre", {"forceCheck": "1"}, {"taskState": "zzInvalide"}),
        ("forceCheck dans le corps", {}, {"taskState": "zzInvalide", "forceCheck": True}),
        ("temoin, sans forceCheck", {}, {"taskState": "zzInvalide"}),
    ]
    for label, params, value in attempts:
        try:
            status, body = raw_put(client, path, value, **params)
            print(f"  [{status}] {label}")
            print(f"      {body[:350]}")
            out.append({"label": label, "status": status, "body": body[:4000]})
        except Exception as err:  # noqa: BLE001
            print(f"  !!  {label} -> {type(err).__name__}: {err}")
    print()
    return out


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
    print("Chaque ligne est une requete. Les trouvailles sont signalees par")
    print("<<< TROUVE en bout de ligne.\n")

    force = phase_force_check(client, serial)

    print("=" * 70)
    print("PHASE 1 - NOMS CACHES")
    print("=" * 70)

    found: list[dict] = []
    tally: dict[str, int] = {}

    total = len(DOMAINS) * len(NAMES)
    done = 0
    started = time.time()

    for domain in DOMAINS:
        for name in NAMES:
            verdicts = []
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

                verdicts.append(verdict)
                tally[verdict] = tally.get(verdict, 0) + 1
                if verdict in ("TROUVE", "ACCEPTE", "autre"):
                    found.append({
                        "route": route, "domain": domain, "name": name,
                        "verdict": verdict, "detail": detail[:6000],
                    })

            done += 1
            rate = done / max(time.time() - started, 0.001)
            eta = int((total - done) / rate) if rate else 0
            flag = "  <<< TROUVE" if "TROUVE" in verdicts or "ACCEPTE" in verdicts else ""
            print(
                f"  [{done:3}/{total}] {domain}.{name:<20} "
                f"{'/'.join(verdicts):<24} reste ~{eta // 60}m{eta % 60:02}s{flag}",
                flush=True,
            )
            if flag:
                for entry in found[-2:]:
                    if entry["verdict"] in ("TROUVE", "ACCEPTE"):
                        print(f"        {entry['detail'][:500]}", flush=True)

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump({"forceCheck": force, "tally": tally, "found": found},
                  fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"Repartition : {tally}")
    print(f"{len(found)} piste(s). Resultat dans {OUTFILE}")
    if not found:
        print("\nAucune trouvaille : la commande ne passe pas par un nom devinable.")
        print("Il faudra intercepter le trafic de l'app EZVIZ.")


if __name__ == "__main__":
    main()
