#!/usr/bin/env python3
"""
Aspiration et volume d'eau, pour toute la maison. Derniere idee bon marche.

Les deux reglages vivent dans SweeperMapMgr.StdCleanCfg :
    [{mapID, cleanConfigType, fanMode, waterQuantity, cleanTimes}]

Ce qu'on a deja elimine :
  - SetCleanCfg (sid=20) est acceptee par le robot mais n'applique que
    cleanConfigType ; fanMode en passager est recu puis ignore ;
  - SetRoomCustomCleanCfg (sid=24) rend 0x00100003 quoi qu'on envoie ;
  - aucune autre action de reglage ne se laisse deviner (plus de 500 noms) ;
  - le profil complet ne se telecharge pas (allow list fermee).

L'idee neuve : l'ecriture de propriete avait ete ecartee tres tot, quand on
ne savait pas encore que SetCleanCfg atteignait le robot. Or cette action
porte sur le meme objet, et sa sortie renvoie la configuration complete -
elle fait sans doute republier sa config a l'appareil. D'ou la combinaison :
ecrire la propriete, puis pousser l'action pour forcer la relecture.

LE JUGE : l'appareil republie son etat toutes les ~4 s. Si la valeur ecrite
tient encore 15 s plus tard, c'est qu'il l'a adoptee. Si elle est revenue a
l'ancienne, c'est lui qui a ecrase le cache - et la, c'est plie.

Le robot ne se deplace a aucun moment.

Usage :
    python3 ezviz_set_global2.py                 # vise quiet + low
    python3 ezviz_set_global2.py strong middle
"""

from __future__ import annotations

import copy
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
PROP = "StdCleanCfg"
ACTION_CFG = "SetCleanCfg"
ACTION_SWITCH = "SwitchMap"

FAN_MODES = ("quiet", "normal", "strong", "super")
WATER_LEVELS = ("dry", "low", "middle", "high")
SETTLE = 15


def read(client):
    try:
        response = client.get_device_feature_value(
            SERIAL, RESOURCE, DOMAIN_MAP, PROP, local_index=IDX
        )
    except Exception as err:  # noqa: BLE001
        print(f"    lecture impossible : {err}")
        return None
    if (response.get("meta") or {}).get("code") != 200:
        return None
    return response.get("data")


def summary(std) -> str:
    if isinstance(std, list) and std and isinstance(std[0], dict):
        c = std[0]
        return (f"fanMode={c.get('fanMode')} water={c.get('waterQuantity')} "
                f"times={c.get('cleanTimes')} type={c.get('cleanConfigType')}")
    return f"(forme inattendue : {std!r})"


def write_property(client, value) -> str:
    """Ecrit la propriete via la route feature. Renvoie un texte lisible."""
    try:
        response = client.set_iot_feature(
            SERIAL, RESOURCE, IDX, DOMAIN_MAP, PROP, value
        )
    except Exception as err:  # noqa: BLE001
        return f"refus : {str(err)[:250]}"
    code = (response.get("meta") or {}).get("code")
    device_meta = ((response.get("meta") or {}).get("moreInfo")
                   or {}).get("deviceMeta")
    marker = " AVEC deviceMeta" if device_meta else " sans deviceMeta"
    return f"ecriture code={code}{marker}"


def poke(client, action: str, value) -> str:
    try:
        response = client.set_iot_action(
            SERIAL, RESOURCE, IDX, DOMAIN_MAP, action, value
        )
    except Exception as err:  # noqa: BLE001
        return f"refus : {str(err)[:200]}"
    device_meta = ((response.get("meta") or {}).get("moreInfo")
                   or {}).get("deviceMeta")
    if device_meta and device_meta.get("errorMsg") == "success":
        return "accepte"
    return f"non accepte : {device_meta}"


def check(client, fan: str, water: str) -> bool:
    print(f"    attente de {SETTLE} s (le robot republie toutes les ~4 s)...")
    time.sleep(SETTLE)
    after = read(client)
    print(f"    relecture : {summary(after)}")
    if isinstance(after, list) and after and isinstance(after[0], dict):
        got = after[0]
        if got.get("fanMode") == fan and got.get("waterQuantity") == water:
            return True
    return False


def main() -> None:
    fan = (sys.argv[1] if len(sys.argv) > 1 else "quiet").lower()
    water = (sys.argv[2] if len(sys.argv) > 2 else "low").lower()
    if fan not in FAN_MODES:
        sys.exit(f"aspiration : {', '.join(FAN_MODES)}")
    if water not in WATER_LEVELS:
        sys.exit(f"eau : {', '.join(WATER_LEVELS)}")

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"\nConnexion OK - cible : {SERIAL}")

    before = read(client)
    print(f"\nAVANT : {summary(before)}")
    if not isinstance(before, list) or not before:
        sys.exit("StdCleanCfg illisible : impossible de juger le resultat.")

    origin = copy.deepcopy(before)
    map_id = before[0].get("mapID")
    cfg_type = before[0].get("cleanConfigType", "universal")
    print(f"Objectif : fanMode={fan}  waterQuantity={water}\n")

    wanted = copy.deepcopy(before)
    wanted[0]["fanMode"] = fan
    wanted[0]["waterQuantity"] = water

    attempts = [
        ("le tableau complet, ecriture seule", wanted, None),
        ("le tableau complet, puis SetCleanCfg",
         wanted, (ACTION_CFG, {"mapID": map_id, "cleanConfigType": cfg_type})),
        ("le tableau complet, puis SwitchMap",
         wanted, (ACTION_SWITCH, map_id)),
        ("l'objet seul, hors tableau", wanted[0],
         (ACTION_CFG, {"mapID": map_id, "cleanConfigType": cfg_type})),
    ]

    print("=" * 70)
    for label, value, action in attempts:
        print(f"\n--- {label}")
        print(f"    {write_property(client, value)}")
        if action is not None:
            name, payload = action
            print(f"    {name} : {poke(client, name, payload)}")
        if check(client, fan, water):
            print("\n" + "=" * 70)
            print("LA VALEUR A TENU. Le robot l'a adoptee.")
            print(f"Recette : {label}")
            print(f"Charge utile : {json.dumps(value, ensure_ascii=False)}")
            print("\nVerifie dans l'app EZVIZ, et ecoute-le au prochain")
            print("nettoyage : c'est la preuve definitive.")
            return
        print("    -> revenu en arriere : le robot a ecrase le cache")

    print("\n" + "=" * 70)
    print("Aucune recette ne tient. L'appareil republie toujours sa propre")
    print("valeur : le reglage global ne s'ecrit pas par ce canal.")
    print("\nIl ne reste que la capture du trafic de l'app EZVIZ.")

    print(f"\nRemise en etat du cache : {write_property(client, origin)}")


if __name__ == "__main__":
    main()
