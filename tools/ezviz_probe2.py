#!/usr/bin/env python3
"""
Sonde LECTURE SEULE n2 : recherche des ACTIONS du robot EZVIZ.

Deux pistes, toutes deux sans risque :

  A. La forme d'URL a parametres revelee par les erreurs 400 de la sonde n1
     (champs channelNo / itemKey). Elle renvoie peut-etre le schema complet.

  B. Un detecteur d'existence : on fait un GET sur les URL d'ACTION. Les
     actions s'invoquent en PUT, donc un GET ne declenche jamais rien. Mais
     le code de reponse trahit l'existence de l'action :
         404 -> l'action n'existe pas
         405 / 400 -> l'action EXISTE (mauvaise methode / parametre manquant)

IMPORTANT : uniquement des GET et des OPTIONS. Le robot ne peut pas bouger.

Usage :
    python3 ezviz_probe2.py [SERIAL]
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
OUTFILE = "ezviz_probe2.json"

DOMAINS = [
    "SweeperTaskMgr",
    "SweeperMgr",
    "SweeperCleanTask",
    "SweeperCtrlMgr",
    "SweeperMapMgr",
    "PowerMgr",
]

ACTIONS = [
    # cycle de tache
    "StartTask", "StopTask", "PauseTask", "ContinueTask", "ResumeTask",
    "CancelTask", "TaskCtrl", "TaskControl", "CurrentTask", "SwitchTask",
    # nettoyage
    "StartClean", "StopClean", "PauseClean", "ContinueClean", "CleanCtrl",
    "CleanSwitch", "GlobalClean", "RoomClean", "AreaClean", "SpotClean",
    "SelectRoomClean", "CustomClean",
    # retour base
    "BackCharge", "GoCharge", "Charge", "ReturnCharge", "GoHome", "Recharge",
    # divers
    "WorkMode", "ControlCmd", "Ctrl", "Control", "Command", "SwitchMode",
    "FindMe", "FindRobot", "Locate", "SetCleanMode",
]


def get(client, path, **params):
    return client._session.get(client._url(path), params=params or None, timeout=25)


def main() -> None:
    serial = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERIAL).upper()

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"Connexion OK - cible : {serial}\n")

    out: dict[str, object] = {}

    # ---------- PARTIE A : forme a parametres ----------
    print("=" * 70)
    print("A. FORME A PARAMETRES (channelNo / itemKey)")
    print("=" * 70)

    a_results = {}
    item_keys = [
        RESOURCE,
        f"{RESOURCE}.SweeperTaskMgr",
        f"{RESOURCE}.SweeperTaskMgr.CurrentTask",
        f"{RESOURCE}.PowerMgr.SurplusPower",
        "*",
        "all",
    ]
    for key in item_keys:
        try:
            r = get(client, f"/v3/iot-feature/feature/{serial}", channelNo=0, itemKey=key)
            body = r.text
            label = f"itemKey={key!r}"
            interesting = r.status_code < 400 and '"code":400' not in body
            print(f"\n{'OK ' if interesting else '.. '}[{r.status_code}] {label}")
            print("   " + body[:900].replace("\n", "\n   "))
            a_results[key] = body[:4000]
        except Exception as err:  # noqa: BLE001
            print(f"\n!! itemKey={key!r} -> {type(err).__name__}: {err}")
    out["A_itemKey"] = a_results

    # ---------- PARTIE B : calibration du detecteur ----------
    print("\n" + "=" * 70)
    print("B1. CALIBRATION DU DETECTEUR")
    print("=" * 70)
    print("On compare une URL connue-valide et une URL connue-fausse,")
    print("pour savoir si les codes de reponse permettent de distinguer.\n")

    calib = {}
    for label, path in (
        ("propriete VALIDE (feature)", f"/v3/iot-feature/feature/{serial}/{RESOURCE}/{IDX}/PowerMgr/SurplusPower"),
        ("propriete BIDON (feature)", f"/v3/iot-feature/feature/{serial}/{RESOURCE}/{IDX}/PowerMgr/ZzzNexistePas"),
        ("domaine BIDON  (feature)", f"/v3/iot-feature/feature/{serial}/{RESOURCE}/{IDX}/ZzzMgr/ZzzNexistePas"),
        ("action  BIDON  (action)", f"/v3/iot-feature/action/{serial}/{RESOURCE}/{IDX}/ZzzMgr/ZzzNexistePas"),
        ("action  plausible (action)", f"/v3/iot-feature/action/{serial}/{RESOURCE}/{IDX}/SweeperTaskMgr/StartTask"),
    ):
        try:
            r = get(client, path)
            print(f"  [{r.status_code}] {label}")
            print(f"        {r.text[:220]}")
            calib[label] = {"status": r.status_code, "body": r.text[:600]}
        except Exception as err:  # noqa: BLE001
            print(f"  !!  {label} -> {type(err).__name__}: {err}")
    out["B1_calibration"] = calib

    try:
        r = client._session.options(
            client._url(f"/v3/iot-feature/action/{serial}/{RESOURCE}/{IDX}/SweeperTaskMgr/StartTask"),
            timeout=25,
        )
        print(f"\n  OPTIONS -> [{r.status_code}] Allow: {r.headers.get('Allow')}")
        out["B1_options"] = {"status": r.status_code, "allow": r.headers.get("Allow")}
    except Exception as err:  # noqa: BLE001
        print(f"\n  !! OPTIONS -> {type(err).__name__}: {err}")

    # ---------- PARTIE B2 : balayage ----------
    print("\n" + "=" * 70)
    print("B2. BALAYAGE DES ACTIONS CANDIDATES (GET uniquement)")
    print("=" * 70)
    print(f"{len(DOMAINS) * len(ACTIONS)} combinaisons. Seules les reponses")
    print("differentes du 404 majoritaire sont affichees.\n")

    hits = []
    counts: dict[int, int] = {}
    for domain in DOMAINS:
        for action in ACTIONS:
            for kind in ("action", "feature"):
                path = f"/v3/iot-feature/{kind}/{serial}/{RESOURCE}/{IDX}/{domain}/{action}"
                try:
                    r = get(client, path)
                except Exception:  # noqa: BLE001
                    continue
                counts[r.status_code] = counts.get(r.status_code, 0) + 1
                if r.status_code != 404:
                    snippet = r.text[:300]
                    print(f"  [{r.status_code}] {kind}/{domain}/{action}")
                    print(f"        {snippet}")
                    hits.append(
                        {"kind": kind, "domain": domain, "action": action,
                         "status": r.status_code, "body": r.text[:1500]}
                    )
            time.sleep(0.05)

    out["B2_hits"] = hits
    out["B2_status_counts"] = counts

    print("\n" + "-" * 70)
    print(f"Repartition des codes : {counts}")
    print(f"{len(hits)} piste(s) retenue(s).")

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False, default=str)
    print(f"\nResultat complet ecrit dans {OUTFILE}")


if __name__ == "__main__":
    main()
