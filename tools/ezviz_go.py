#!/usr/bin/env python3
"""
Commander le robot EZVIZ - pour de vrai cette fois.

La chasse a trouve le canal de commande :

    route    : /v3/iot-feature/action/...
    domaine  : SweeperCleanTask
    action   : CleanCtrl
    direction: Plt2Dev  (plateforme -> appareil)
    input    : {"action": start|pause|resume|stop, "source": mobile|smartSpeaker}

PHASE 1 - on l'essaie, chaque commande confirmee au clavier.
PHASE 2 - on cherche l'action de retour a la base, absente de l'enumeration
          de CleanCtrl. Valeurs invalides uniquement : sans effet.

Usage :
    python3 ezviz_go.py [SERIAL]
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
CLEAN_DOMAIN = "SweeperCleanTask"
CLEAN_ACTION = "CleanCtrl"
OUTFILE = "ezviz_go.json"

INVALID = "Z" * 300
NOT_SUPPORTED = "设备不支持该功能"
NOT_DECLARED = "设备功能未报备"

# Convention observee : domaine Sweeper<Chose>Task/Mgr, action suffixee Ctrl.
HUNT_DOMAINS = [
    "SweeperCleanTask", "SweeperChargeTask", "SweeperTaskMgr", "SweeperMgr",
    "SweeperCtrlMgr", "SweeperMoveTask", "SweeperDockTask", "SweeperMapMgr",
    "SweeperRemoteTask", "SweeperMaintainTask", "SweeperInspectTask",
    "SweeperDryTask", "SweeperMopTask", "SweeperFindTask", "ChargeMgr",
    "DockMgr", "PowerMgr", "SweeperConsumable",
]

HUNT_NAMES = [
    "ChargeCtrl", "DockCtrl", "RechargeCtrl", "ReturnCtrl", "HomeCtrl",
    "BackChargeCtrl", "BackCharge", "GoCharge", "GoHome", "ReturnDock",
    "MoveCtrl", "RemoteCtrl", "FindCtrl", "LocateCtrl", "FindRobotCtrl",
    "RoomCleanCtrl", "AreaCleanCtrl", "CustomCleanCtrl", "SpotCleanCtrl",
    "PartCleanCtrl", "SelectCleanCtrl", "MapCtrl", "MapCleanCtrl",
    "MopCtrl", "DryCtrl", "WashCtrl", "DustCollectCtrl", "InspectCtrl",
    "TaskCtrl", "ModeCtrl", "FanCtrl", "WaterCtrl", "VoiceCtrl",
    "ResetCtrl", "ConsumableCtrl", "PowerCtrl", "SwitchCtrl", "StateCtrl",
]


def read_state(client, serial):
    try:
        r = client.get_device_feature_value(
            serial, RESOURCE, "SweeperTaskMgr", "CurrentTask", local_index=IDX
        )
        return r.get("data", r)
    except Exception as err:  # noqa: BLE001
        return f"<illisible : {err}>"


def ask(question: str) -> bool:
    while True:
        answer = input(f"\n{question} [o/n] ").strip().lower()
        if answer in ("o", "oui", "y", "yes"):
            return True
        if answer in ("n", "non", "no"):
            return False


def command(client, serial, action: str) -> dict:
    payload = {"action": action, "source": "mobile"}
    print(f"\n  etat avant : {read_state(client, serial)}")
    print(f"  -> CleanCtrl {payload}")
    entry = {"action": action}
    try:
        result = client.set_iot_action(
            serial, RESOURCE, IDX, CLEAN_DOMAIN, CLEAN_ACTION, payload
        )
        print(f"  reponse : {json.dumps(result, ensure_ascii=False)[:300]}")
        entry["result"] = str(result)[:1000]
    except Exception as err:  # noqa: BLE001
        print(f"  ECHEC : {type(err).__name__}: {str(err)[:700]}")
        entry["error"] = str(err)[:2000]
        return entry

    for wait in (5, 10):
        time.sleep(wait)
        state = read_state(client, serial)
        print(f"  +{wait}s : {state}")
        entry[f"state_{wait}s"] = str(state)[:500]
    return entry


def main() -> None:
    serial = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERIAL).upper()

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"\nConnexion OK - cible : {serial}")

    log: dict = {"commands": [], "hunt": []}

    # ---------------- PHASE 1 ----------------
    print("\n" + "=" * 70)
    print("PHASE 1 - LA COMMANDE")
    print("=" * 70)
    print(f"Etat : {read_state(client, serial)}")
    print("\nCette fois le robot devrait REELLEMENT reagir.")
    print("Reste a portee de vue, et garde l'app EZVIZ sous la main pour")
    print("reprendre la main si besoin.")

    if ask("Envoyer 'start' (le robot va demarrer) ?"):
        log["commands"].append(command(client, serial, "start"))

        if ask("A-t-il demarre ?"):
            print("\n  >>> Le canal de commande fonctionne.")
            log["works"] = True
            for act, question in (
                ("pause", "Envoyer 'pause' ?"),
                ("resume", "Envoyer 'resume' ?"),
                ("stop", "Envoyer 'stop' ? (regarde s'il rentre a sa base tout seul)"),
            ):
                if ask(question):
                    log["commands"].append(command(client, serial, act))
            log["stop_returns_to_dock"] = ask(
                "Apres 'stop', est-il reparti vers sa base de lui-meme ?"
            )
        else:
            log["works"] = False
            print("\n  Pas de reaction : on note et on continue la recherche.")

    # ---------------- PHASE 2 ----------------
    print("\n" + "=" * 70)
    print("PHASE 2 - L'ACTION DE RETOUR A LA BASE")
    print("=" * 70)
    print("Valeurs invalides uniquement : le robot ne peut pas les executer.")
    print(f"{len(HUNT_DOMAINS)} domaines x {len(HUNT_NAMES)} noms.\n")

    total = len(HUNT_DOMAINS) * len(HUNT_NAMES)
    done = 0
    started = time.time()
    tally: dict[str, int] = {}

    for domain in HUNT_DOMAINS:
        for name in HUNT_NAMES:
            if domain == CLEAN_DOMAIN and name == CLEAN_ACTION:
                continue
            try:
                client.set_iot_action(serial, RESOURCE, IDX, domain, name, INVALID)
                verdict, detail = "ACCEPTE", "(aucune erreur)"
            except Exception as err:  # noqa: BLE001
                detail = str(err)
                if NOT_SUPPORTED in detail:
                    verdict = "absent"
                elif NOT_DECLARED in detail:
                    verdict = "non-declare"
                elif "Profile.Actions" in detail or "schema=" in detail:
                    verdict = "TROUVE"
                else:
                    verdict = "autre"

            tally[verdict] = tally.get(verdict, 0) + 1
            done += 1
            rate = done / max(time.time() - started, 0.001)
            eta = int((total - done) / rate)
            mark = "  <<< TROUVE" if verdict in ("TROUVE", "ACCEPTE", "autre") else ""
            print(f"  [{done:3}/{total}] {domain}.{name:<18} {verdict:<12} "
                  f"reste ~{eta // 60}m{eta % 60:02}s{mark}", flush=True)
            if mark:
                print(f"      {detail[:900]}", flush=True)
                log["hunt"].append({"domain": domain, "name": name,
                                    "verdict": verdict, "detail": detail[:6000]})

    log["tally"] = tally
    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print(f"Repartition : {tally}")
    print(f"Resultat dans {OUTFILE} - envoie-le moi.")


if __name__ == "__main__":
    main()
