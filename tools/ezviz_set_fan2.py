#!/usr/bin/env python3
"""
Trouver la forme de charge utile que le robot accepte pour SetRoomCustomCleanCfg.

Premier essai (ezviz_set_fan.py) avec {mapID, regionType, roomID, fanMode} :

    meta.code = 1048579
    deviceMeta = {code: 0x00100003, errorMsg: failure}

Le deviceMeta EST la : la commande a atteint l'appareil, contrairement aux
ecritures de propriete qui n'obtenaient qu'un 200 du cloud. Le robot a donc
recu et refuse - c'est la forme de l'objet qui ne lui va pas, pas le canal.

Ce script essaie sept variantes et S'ARRETE a la premiere acceptee, pour ne
jamais changer plus d'un reglage. Les valeurs actuelles sont relues avant, et
reaffichees a la fin pour pouvoir revenir en arriere.

Aucune variante ne demande au robot de se deplacer.

Usage :
    python3 ezviz_set_fan2.py [fanMode]     # defaut : quiet
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
PROP_ROOM_CFG = "RoomCustomCleanCfg"
PROP_MAP_BASIC = "MapBasicProperty"
ACTION = "SetRoomCustomCleanCfg"

FAN_MODES = ("quiet", "normal", "strong", "super")


def read(client, prop: str):
    try:
        response = client.get_device_feature_value(
            SERIAL, RESOURCE, DOMAIN_MAP, prop, local_index=IDX
        )
    except Exception as err:  # noqa: BLE001
        print(f"  lecture {prop} impossible : {err}")
        return None
    if (response.get("meta") or {}).get("code") != 200:
        print(f"  lecture {prop} refusee : {response}")
        return None
    return response.get("data")


def show_rooms(cfg, title: str) -> None:
    print(f"\n{title}")
    if not isinstance(cfg, list):
        print(f"  (forme inattendue : {type(cfg).__name__})")
        return
    for entry in cfg:
        if not isinstance(entry, dict):
            continue
        print(f"  carte {entry.get('mapID')}")
        for room in entry.get("room") or []:
            print(
                "    piece {rid:<4} fanMode={fan:<7} water={water:<7} "
                "times={times:<3} order={order}".format(
                    rid=room.get("roomID", room.get("customRegionID")),
                    fan=str(room.get("fanMode")),
                    water=str(room.get("waterQuantity")),
                    times=str(room.get("cleanTimes")),
                    order=str(room.get("order")),
                )
            )


def find_room(cfg, maps):
    """Carte en usage + sa premiere piece, avec ses valeurs actuelles."""
    in_use = None
    if isinstance(maps, list):
        for m in maps:
            if isinstance(m, dict) and m.get("inUse"):
                in_use = m.get("mapID")
                break

    entries = [e for e in cfg if isinstance(e, dict)] if isinstance(cfg, list) else []
    chosen = next((e for e in entries if e.get("mapID") == in_use), None)
    if chosen is None:
        chosen = entries[0] if entries else None
    if chosen is None:
        return None, None, None, None

    for room in chosen.get("room") or []:
        if room.get("regionType", "room") == "room" and "roomID" in room:
            return chosen.get("mapID"), room.get("roomID"), room, in_use
    return chosen.get("mapID"), None, None, in_use


def variants(map_id, room_id, current, fan, other_map):
    """Sept facons de dire la meme chose, de la plus plausible a la plus exotique."""
    water = current.get("waterQuantity", "middle")
    times = current.get("cleanTimes", 1)
    order = current.get("order", -1)

    full = {"mapID": map_id, "regionType": "room", "roomID": room_id,
            "fanMode": fan, "waterQuantity": water, "cleanTimes": times}

    return [
        ("la piece entiere, sans order", dict(full)),
        ("la piece entiere, avec son order actuel", {**full, "order": order}),
        ("la piece entiere, order=1 (incluse au nettoyage)",
         {**full, "order": 1}),
        ("sans regionType", {"mapID": map_id, "roomID": room_id,
                             "fanMode": fan, "waterQuantity": water,
                             "cleanTimes": times}),
        ("cleanTimes=0", {**full, "cleanTimes": 0}),
        ("la forme tableau, calquee sur la sortie de l'action",
         [{"mapID": map_id, "room": [{**{k: v for k, v in full.items()
                                         if k != "mapID"}, "order": order}]}]),
        ("sur l'autre carte", {**full, "mapID": other_map}
         if other_map is not None else None),
    ]


def verdict(response) -> tuple[str, bool]:
    meta = response.get("meta") or {}
    device_meta = (meta.get("moreInfo") or {}).get("deviceMeta")
    if device_meta is None:
        return "PAS de deviceMeta - seul le cloud a repondu", False
    if device_meta.get("errorMsg") == "success":
        return "ACCEPTE PAR LE ROBOT", True
    return f"refus du robot : {device_meta}", False


def main() -> None:
    if not hasattr(EzvizClient, "set_iot_action"):
        sys.exit("pyezvizapi trop ancienne : pas de set_iot_action.")

    fan = (sys.argv[1] if len(sys.argv) > 1 else "quiet").lower()
    if fan not in FAN_MODES:
        sys.exit(f"fanMode doit valoir l'un de : {', '.join(FAN_MODES)}")

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"\nConnexion OK - cible : {SERIAL}")

    before = read(client, PROP_ROOM_CFG)
    maps = read(client, PROP_MAP_BASIC)
    show_rooms(before, "AVANT")

    map_id, room_id, current, in_use = find_room(before, maps)
    if map_id is None or room_id is None or current is None:
        sys.exit("\nAucune piece exploitable.")

    other_map = None
    if isinstance(before, list):
        for entry in before:
            if isinstance(entry, dict) and entry.get("mapID") != map_id:
                other_map = entry.get("mapID")
                break

    print(f"\nCarte en usage : {in_use}   cible : carte {map_id}, piece {room_id}")
    print(f"Aspiration demandee : {fan}\n")
    print("=" * 68)

    winner = None
    for label, value in variants(map_id, room_id, current, fan, other_map):
        if value is None:
            continue
        print(f"\n--- {label}")
        print(f"    {json.dumps(value, ensure_ascii=False)[:300]}")
        try:
            response = client.set_iot_action(
                SERIAL, RESOURCE, IDX, DOMAIN_MAP, ACTION, value
            )
        except Exception as err:  # noqa: BLE001
            text = str(err)
            print(f"    REFUS : {text[:400]}")
            if "deviceMeta" not in text:
                print("    (refus du cloud, pas du robot)")
            continue

        message, ok = verdict(response)
        print(f"    {message}")
        if ok:
            winner = (label, value)
            break
        time.sleep(1)

    print("\n" + "=" * 68)
    if winner is None:
        print("Aucune variante acceptee. La forme n'est pas en cause :")
        print("il faudra intercepter l'app EZVIZ pendant un changement.")
        return

    label, value = winner
    print(f"GAGNE : {label}")
    print(f"Charge utile : {json.dumps(value, ensure_ascii=False)}")
    print("\nRelecture dans 5 s...")
    time.sleep(5)
    show_rooms(read(client, PROP_ROOM_CFG), "APRES")
    print(f"\nVerifier dans l'app EZVIZ : carte {map_id}, piece {room_id}.")


if __name__ == "__main__":
    main()
