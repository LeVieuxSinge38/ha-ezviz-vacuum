#!/usr/bin/env python3
"""
Sonde LECTURE SEULE de l'API iot-feature EZVIZ pour un aspirateur robot.

Le dump initial (ezviz_dump.py) revele les proprietes lisibles du robot, mais
pas les ACTIONS (demarrer, mettre en pause, retour a la base). Ce script
interroge l'API a differents niveaux de profondeur pour faire apparaitre le
schema complet du produit, actions comprises.

IMPORTANT : ce script ne fait QUE des GET. Il ne peut pas faire bouger le
robot, ni modifier un reglage.

Usage :
    python3 ezviz_probe.py [SERIAL]
"""

from __future__ import annotations

import getpass
import json
import sys

from pyezvizapi import EzvizClient

REGION = "apiieu.ezvizlife.com"
DEFAULT_SERIAL = "BD1522206"
RESOURCE = "SweepingRobot"
LOCAL_INDEX = "0"
OUTFILE = "ezviz_probe.json"

# Domaines vus dans FEATURE_INFO : on les reinterroge un par un, car l'API
# renvoie souvent le schema complet (proprietes + actions) quand on demande
# un niveau au-dessus de la propriete.
DOMAINS = [
    "SweeperTaskMgr",
    "SweeperMgr",
    "SweeperCleanTask",
    "SweeperMapMgr",
    "PowerMgr",
    "InfoMgr",
    "SweeperConsumable",
    "SoundSetting",
    "TimeMgr",
]


def show(label: str, status: int, body: str, *, limit: int = 1500) -> None:
    flag = "OK " if 200 <= status < 300 else "-- "
    print(f"\n{flag}[{status}] {label}")
    if 200 <= status < 300:
        print(body[:limit] + (" ...(tronque)" if len(body) > limit else ""))


def main() -> None:
    serial = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERIAL).upper()

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"Connexion OK - cible : {serial}\n")

    collected: dict[str, object] = {}

    # --- 1. Payload brut du robot : on cherche productId sous son vrai nom ---
    print("=" * 70)
    print("1. PAYLOAD BRUT DU ROBOT")
    print("=" * 70)
    devices = client.get_device_infos()
    robot = devices.get(serial)
    if robot is None:
        sys.exit(f"Serial {serial} absent du compte. Presents : {list(devices)}")

    collected["deviceInfos"] = robot.get("deviceInfos", {})
    collected["resourceInfos"] = robot.get("resourceInfos", [])
    collected["FEATURE"] = robot.get("FEATURE", {})

    print("\n-- deviceInfos (toutes les cles) --")
    print(json.dumps(robot.get("deviceInfos", {}), indent=2, ensure_ascii=False))
    print("\n-- resourceInfos --")
    print(json.dumps(robot.get("resourceInfos", []), indent=2, ensure_ascii=False))

    # --- 2. Exploration en profondeur du bus iot-feature ---
    print("\n" + "=" * 70)
    print("2. BUS IOT-FEATURE (lecture seule)")
    print("=" * 70)

    paths = [
        f"/v3/iot-feature/feature/{serial}",
        f"/v3/iot-feature/feature/{serial}/{RESOURCE}",
        f"/v3/iot-feature/feature/{serial}/{RESOURCE}/{LOCAL_INDEX}",
        f"/v3/iot-feature/action/{serial}/{RESOURCE}/{LOCAL_INDEX}",
    ]
    for domain in DOMAINS:
        paths.append(f"/v3/iot-feature/feature/{serial}/{RESOURCE}/{LOCAL_INDEX}/{domain}")

    probe: dict[str, object] = {}
    for path in paths:
        try:
            resp = client._session.get(client._url(path), timeout=25)
            body = resp.text
            show(path, resp.status_code, body)
            if 200 <= resp.status_code < 300:
                try:
                    probe[path] = resp.json()
                except ValueError:
                    probe[path] = body
        except Exception as err:  # noqa: BLE001 - on veut voir toutes les erreurs
            print(f"\n!! {path} -> {type(err).__name__}: {err}")
    collected["probe"] = probe

    # --- 3. Verification de la methode publique de lecture ---
    print("\n" + "=" * 70)
    print("3. LECTURE VIA LA METHODE PUBLIQUE")
    print("=" * 70)
    for domain, prop in (
        ("PowerMgr", "SurplusPower"),
        ("SweeperTaskMgr", "CurrentTask"),
    ):
        try:
            value = client.get_device_feature_value(
                serial, RESOURCE, domain, prop, local_index=LOCAL_INDEX
            )
            print(f"\nOK  {domain}.{prop} = {json.dumps(value, ensure_ascii=False)}")
            collected[f"read:{domain}.{prop}"] = value
        except Exception as err:  # noqa: BLE001
            print(f"\n!!  {domain}.{prop} -> {type(err).__name__}: {err}")

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump(collected, fh, indent=2, ensure_ascii=False, default=str)
    print(f"\n\nResultat complet ecrit dans {OUTFILE}")
    print("Envoie-moi la sortie de la console (ou ce fichier).")


if __name__ == "__main__":
    main()
