#!/usr/bin/env python3
"""
Dernier coup pas cher avant la capture de trafic.

Etat des lieux :
  - le reglage global vit dans SweeperMapMgr.StdCleanCfg (fanMode,
    waterQuantity, cleanTimes) ;
  - SetCleanCfg (sid=20) est accepte par le robot mais n'applique que
    cleanConfigType : les passagers sont recus puis ignores ;
  - SetRoomCustomCleanCfg (sid=24) porte les bons champs mais renvoie
    0x00100003 quoi qu'on lui envoie ;
  - actions connues : sid 3, 6, 11, 20, 24, 26. Il en manque une quinzaine.

PHASE 1 - LE PROFIL COMPLET
Les erreurs du cloud exhibent un objet Profile.Actions(identifier=..., sid=N)
construit cote serveur a partir du productId. Si une URL renvoie ce profil
entier, on obtient toutes les actions d'un coup au lieu de les deviner. On
essaie une douzaine de chemins plausibles, en GET, sans rien modifier.

PHASE 2 - LES NOMS 'A CRANS'
Les niveaux d'eau s'appellent 低档 / 中档 / 高档 : 档 = cran, gear. Les API
chinoises nomment souvent ces reglages Gear. Famille jamais essayee, plus
quelques noms courts oublies (SetFan, SetWater, SetSuction).

Tout est en lecture ou en valeur invalide : le robot ne bouge pas.

Usage :
    python3 ezviz_profile_hunt.py
"""

from __future__ import annotations

import getpass
import json
import sys
import time

from pyezvizapi import EzvizClient

REGION = "apiieu.ezvizlife.com"
SERIAL = "BD1522206"
RESOURCE = "SweepingRobot"
IDX = "0"
PRODUCT_ID = "CS-RE5P-TWT"
OUTFILE = "ezviz_profile_hunt.json"

INVALID = "Z" * 300
NOT_SUPPORTED = "设备不支持该功能"
NOT_DECLARED = "设备功能未报备"

PATHS = [
    f"/v3/iot-feature/profile/{SERIAL}/{RESOURCE}/{IDX}",
    f"/v3/iot-feature/profile/{SERIAL}",
    f"/v3/iot-feature/{SERIAL}/{RESOURCE}/{IDX}",
    f"/v3/iot-feature/features/{SERIAL}/{RESOURCE}/{IDX}",
    f"/v3/iot-feature/feature/{SERIAL}/{RESOURCE}/{IDX}",
    f"/v3/iot-feature/action/{SERIAL}/{RESOURCE}/{IDX}",
    f"/v3/iot-feature/model/{SERIAL}",
    f"/v3/iot-feature/thingmodel/{SERIAL}",
    f"/v3/iot/profile/{PRODUCT_ID}",
    f"/v3/iot/product/{PRODUCT_ID}/profile",
    f"/v3/devices/{SERIAL}/profile",
    f"/v3/device/profile/{SERIAL}",
]

DOMAINS = ["SweeperMapMgr", "SweeperCleanTask"]

NAMES = [
    # la famille 'cran' (档), jamais essayee
    "SetGear", "SetFanGear", "SetWaterGear", "SetCleanGear", "SetMopGear",
    "GearCtrl", "FanGearCtrl", "WaterGearCtrl",
    # noms courts oublies
    "SetFan", "SetWater", "SetSuction", "SetWind", "SetMop", "SetPower",
    "SetLevel", "SetCleanLevel", "SetSweepLevel",
    # variantes autour de Std / Standard
    "SetStdCfg", "SetStandardCleanCfg", "SetStdClean", "StdCleanCfgSet",
    # variantes autour de la config, style SetCleanCfg qui, lui, existe
    "SetCleanCfgEx", "SetCleanCfgV2", "SetCleanSetting", "SetSweepSetting",
    "SetSweepCfg", "SetCleanPara", "SetCleanAttr", "SetCleanProperty",
    "SetCleanCfgAll", "SetMapCleanCfg", "SetWholeCleanCfg",
    # le pendant de SetRoomCustomCleanCfg pour la maison entiere
    "SetUniversalCfg", "SetGlobalCfg", "SetAllRoomCleanCfg",
    "SetRoomCleanCfgAll", "SetCustomCleanCfgAll",
]


def try_paths(client) -> list[dict]:
    print("=" * 70)
    print("PHASE 1 - LE PROFIL COMPLET")
    print("=" * 70)
    out = []
    for path in PATHS:
        try:
            response = client._session.get(client._url(path), timeout=20)
            status, body = response.status_code, response.text
        except Exception as err:  # noqa: BLE001
            print(f"  !!  {path}\n      {type(err).__name__}: {err}")
            continue

        interesting = status == 200 and (
            "sid" in body or "Actions" in body or "identifier" in body
        )
        flag = "  <<< A LIRE" if interesting else ""
        print(f"  [{status}] {path}{flag}")
        print(f"      {body[:300]}")
        out.append({"path": path, "status": status, "body": body[:20000],
                    "interesting": interesting})
    print()
    return out


def classify(err: str) -> str:
    if NOT_SUPPORTED in err:
        return "absent"
    if NOT_DECLARED in err:
        return "non-declare"
    if "Profile.Actions" in err or "Profile.Props" in err or "schema=" in err:
        return "TROUVE"
    return "autre"


def hunt(client) -> tuple[list[dict], dict[str, int]]:
    print("=" * 70)
    print("PHASE 2 - LES NOMS 'A CRANS'")
    print("=" * 70)
    total = len(DOMAINS) * len(NAMES)
    print(f"{total} requetes, valeurs invalides : le robot ne bouge pas.\n")

    found: list[dict] = []
    tally: dict[str, int] = {}
    done = 0
    started = time.time()

    for domain in DOMAINS:
        for name in NAMES:
            try:
                result = client.set_iot_action(
                    SERIAL, RESOURCE, IDX, domain, name, INVALID
                )
                verdict = "ACCEPTE"
                detail = json.dumps(result, ensure_ascii=False)
            except Exception as err:  # noqa: BLE001
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
            print(f"  [{done:3}/{total}] {domain}.{name:<22} {verdict:<12} "
                  f"reste ~{eta // 60}m{eta % 60:02}s{flag}", flush=True)
            if flag:
                print(f"        {detail[:800]}", flush=True)

    return found, tally


def main() -> None:
    if not hasattr(EzvizClient, "set_iot_action"):
        sys.exit("pyezvizapi trop ancienne : pas de set_iot_action.")

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"\nConnexion OK - cible : {SERIAL}\n")

    paths = try_paths(client)
    found, tally = hunt(client)

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump({"paths": paths, "tally": tally, "found": found},
                  fh, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    hits = [p for p in paths if p["interesting"]]
    print(f"Profil : {len(hits)} URL(s) a lire" if hits
          else "Profil : aucune URL n'a repondu quelque chose d'exploitable")
    print(f"Noms   : {tally}")
    print(f"Resultat complet dans {OUTFILE}")


if __name__ == "__main__":
    main()
