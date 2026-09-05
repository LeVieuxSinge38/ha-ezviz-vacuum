#!/usr/bin/env python3
"""
Le robot refuse-t-il CETTE action, ou TOUT reglage pendant qu'il est docke ?

SetRoomCustomCleanCfg renvoie 0x00100003 quelle que soit la charge utile :
sept formes essayees, sept fois le meme code. Une erreur de validation
varierait avec le contenu ; celle-ci l'ignore. C'est donc un refus d'etat.

Deux hypotheses a departager :

  1. le robot n'accepte aucun reglage tant qu'il dort sur sa base ;
  2. il manque une etape prealable - passer la carte en 'custom' avant de
     pouvoir configurer une piece.

Ce script envoie deux actions VOLONTAIREMENT SANS EFFET : la configuration
qu'il a deja, et un basculement vers la carte deja active. Si elles passent,
le robot accepte les reglages a l'arret et le probleme est propre a l'action
des pieces (hypothese 2). Si elles echouent avec le meme code, c'est son etat
qui bloque (hypothese 1).

Puis, si SetCleanCfg passe, il enchaine : carte en 'custom', nouvel essai sur
la piece, et retour a 'universal' dans tous les cas.

Le robot ne se deplace a aucun moment.

Usage :
    python3 ezviz_probe_state.py
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

DOMAIN_MAP = "SweeperMapMgr"
DOMAIN_TASK = "SweeperTaskMgr"
PROP_STD_CLEAN = "StdCleanCfg"
PROP_MAP_BASIC = "MapBasicProperty"
PROP_CURRENT_TASK = "CurrentTask"


def read(client, domain: str, prop: str):
    try:
        response = client.get_device_feature_value(
            SERIAL, RESOURCE, domain, prop, local_index=IDX
        )
    except Exception as err:  # noqa: BLE001
        print(f"  lecture {prop} impossible : {err}")
        return None
    if (response.get("meta") or {}).get("code") != 200:
        print(f"  lecture {prop} refusee : {response}")
        return None
    return response.get("data")


def send(client, domain: str, action: str, value) -> bool:
    """Envoie une action et dit si le ROBOT l'a acceptee."""
    print(f"\n--- {domain}.{action}")
    print(f"    {json.dumps(value, ensure_ascii=False)[:300]}")
    try:
        response = client.set_iot_action(
            SERIAL, RESOURCE, IDX, domain, action, value
        )
    except Exception as err:  # noqa: BLE001
        text = str(err)
        print(f"    REFUS : {text[:300]}")
        if "deviceMeta" not in text:
            print("    (refus du cloud : l'appareil n'a rien vu)")
        elif "0x00100003" in text:
            print("    (le meme code que pour les pieces)")
        return False

    meta = response.get("meta") or {}
    device_meta = (meta.get("moreInfo") or {}).get("deviceMeta")
    if device_meta is None:
        print("    PAS de deviceMeta - seul le cloud a repondu")
        return False
    if device_meta.get("errorMsg") == "success":
        print("    ACCEPTE PAR LE ROBOT")
        return True
    print(f"    refus du robot : {device_meta}")
    return False


def main() -> None:
    if not hasattr(EzvizClient, "set_iot_action"):
        sys.exit("pyezvizapi trop ancienne : pas de set_iot_action.")

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"\nConnexion OK - cible : {SERIAL}")

    task = read(client, DOMAIN_TASK, PROP_CURRENT_TASK) or {}
    print(f"\nEtat du robot : taskState={task.get('taskState')!r} "
          f"inCharging={task.get('inCharging')}")

    std = read(client, DOMAIN_MAP, PROP_STD_CLEAN)
    print(f"StdCleanCfg actuel : {json.dumps(std, ensure_ascii=False)[:400]}")

    maps = read(client, DOMAIN_MAP, PROP_MAP_BASIC)
    map_id = None
    if isinstance(maps, list):
        for m in maps:
            if isinstance(m, dict) and m.get("inUse"):
                map_id = m.get("mapID")
                break
    if map_id is None:
        sys.exit("Pas de carte en usage : impossible de tester sans risque.")

    current_type = "universal"
    if isinstance(std, list) and std and isinstance(std[0], dict):
        current_type = std[0].get("cleanConfigType") or "universal"

    print(f"\nCarte en usage : {map_id}   type actuel : {current_type}")
    print("=" * 68)
    print("TEMOINS - deux actions qui ne changent rien")

    ok_cfg = send(client, DOMAIN_MAP, "SetCleanCfg",
                  {"mapID": map_id, "cleanConfigType": current_type})
    time.sleep(1)
    ok_switch = send(client, DOMAIN_MAP, "SwitchMap", map_id)

    print("\n" + "=" * 68)
    print("LE CHAMP source - CleanCtrl l'exige, les Set... ne le declarent pas")
    print("mais le firmware l'attend peut-etre quand meme.")

    for src in ("mobile", "smartSpeaker"):
        send(client, DOMAIN_MAP, "SetRoomCustomCleanCfg",
             {"mapID": map_id, "regionType": "room", "roomID": 0,
              "fanMode": "quiet", "waterQuantity": "middle",
              "cleanTimes": 1, "source": src})
        time.sleep(1)

    print("\n" + "=" * 68)
    if not ok_cfg and not ok_switch:
        print("VERDICT : le robot refuse TOUT reglage dans cet etat.")
        print("C'est son etat qui bloque, pas l'action des pieces.")
        print("Prochaine etape : refaire l'essai pendant qu'il nettoie ou")
        print("qu'il est en pause - ce qui demande de le faire partir.")
        return

    print("VERDICT : le robot accepte des reglages a l'arret.")
    print("Le blocage est donc propre a SetRoomCustomCleanCfg.")

    if not ok_cfg:
        print("\nSetCleanCfg n'etant pas passe, on s'arrete la.")
        return

    print("\n" + "=" * 68)
    print("SUITE - passer la carte en 'custom', puis reessayer la piece")

    if send(client, DOMAIN_MAP, "SetCleanCfg",
            {"mapID": map_id, "cleanConfigType": "custom"}):
        time.sleep(2)
        send(client, DOMAIN_MAP, "SetRoomCustomCleanCfg",
             {"mapID": map_id, "regionType": "room", "roomID": 0,
              "fanMode": "quiet", "waterQuantity": "middle", "cleanTimes": 1})

    print("\n" + "=" * 68)
    print(f"Retour au type d'origine ({current_type}).")
    time.sleep(1)
    send(client, DOMAIN_MAP, "SetCleanCfg",
         {"mapID": map_id, "cleanConfigType": current_type})


if __name__ == "__main__":
    main()
