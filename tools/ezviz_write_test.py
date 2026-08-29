#!/usr/bin/env python3
"""
Test d'ECRITURE sans effet sur le robot EZVIZ.

Observer les etats a livre leur vocabulaire, mais pas les commandes. Il faut
donc ecrire. Pour le faire sans risque, deux principes :

  PHASE A - on reecrit une valeur benigne A L'IDENTIQUE (le volume des bips
            sonores, deja a sa valeur actuelle). Si l'API repond 200, on sait
            que l'ecriture marche et on connait le format attendu, sans que
            rien n'ait change sur le robot.

  PHASE B - on ecrit une valeur VOLONTAIREMENT INVALIDE sur la tache courante.
            Une valeur invalide ne peut pas commander le robot, mais la
            reponse distingue "chemin non inscriptible" de "valeur refusee",
            ce qui nous dit si c'est bien par la qu'on commande.

Le robot ne peut ni demarrer, ni s'arreter, ni bouger a cause de ce script.
A lancer de preference quand il est sur sa base.

Usage :
    python3 ezviz_write_test.py [SERIAL]
"""

from __future__ import annotations

import getpass
import json
import sys

from pyezvizapi import EzvizClient

REGION = "apiieu.ezvizlife.com"
DEFAULT_SERIAL = "BD1522206"
RESOURCE = "SweepingRobot"
IDX = "0"
PRODUCT_ID = "CS-RE5P-TWT"
OUTFILE = "ezviz_write_test.json"


def dump(label: str, fn) -> dict:
    print(f"\n--- {label}")
    try:
        result = fn()
        text = json.dumps(result, ensure_ascii=False, default=str)
        print(f"    {text[:700]}")
        return {"label": label, "ok": True, "result": text[:2000]}
    except Exception as err:  # noqa: BLE001
        print(f"    {type(err).__name__}: {err}")
        return {"label": label, "ok": False, "error": f"{type(err).__name__}: {err}"[:2000]}


def main() -> None:
    serial = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERIAL).upper()

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"\nConnexion OK - cible : {serial}")

    log: list[dict] = []

    # ---------- Valeur de reference ----------
    print("\n" + "=" * 70)
    print("VALEUR DE REFERENCE (avant tout)")
    print("=" * 70)
    before = dump(
        "lecture SoundSetting.PromptToneVolume",
        lambda: client.get_device_feature_value(
            serial, RESOURCE, "SoundSetting", "PromptToneVolume", local_index=IDX
        ),
    )
    log.append(before)

    volume = None
    try:
        volume = json.loads(before["result"])["data"]
    except Exception:  # noqa: BLE001
        pass

    if not isinstance(volume, int):
        print("\n!! Volume actuel illisible - on s'arrete la pour ne rien ecrire au hasard.")
        with open(OUTFILE, "w", encoding="utf-8") as fh:
            json.dump(log, fh, indent=2, ensure_ascii=False)
        return

    print(f"\n    Volume actuel = {volume}. C'est cette valeur exacte qu'on va")
    print("    reecrire : l'operation est donc sans effet.")

    # ---------- PHASE A : ecriture benigne, valeur identique ----------
    print("\n" + "=" * 70)
    print("PHASE A - REECRITURE A L'IDENTIQUE (sans effet)")
    print("=" * 70)

    log.append(dump(
        "set_iot_feature(SoundSetting, PromptToneVolume, <valeur actuelle>)",
        lambda: client.set_iot_feature(
            serial, RESOURCE, IDX, "SoundSetting", "PromptToneVolume", volume
        ),
    ))
    log.append(dump(
        "set_iot_feature(... , {'PromptToneVolume': <valeur actuelle>})",
        lambda: client.set_iot_feature(
            serial, RESOURCE, IDX, "SoundSetting", "PromptToneVolume",
            {"PromptToneVolume": volume},
        ),
    ))
    log.append(dump(
        f"set_device_feature_by_key(productId={PRODUCT_ID}, key=PromptToneVolume)",
        lambda: client.set_device_feature_by_key(
            serial, PRODUCT_ID, volume, "PromptToneVolume"
        ),
    ))

    log.append(dump(
        "relecture du volume (doit etre inchange)",
        lambda: client.get_device_feature_value(
            serial, RESOURCE, "SoundSetting", "PromptToneVolume", local_index=IDX
        ),
    ))

    # ---------- PHASE B : valeur invalide sur la tache courante ----------
    print("\n" + "=" * 70)
    print("PHASE B - VALEUR INVALIDE SUR LA TACHE COURANTE")
    print("=" * 70)
    print("'zzInvalide' ne correspond a aucune commande : le robot ne peut pas")
    print("l'executer. Seule la forme de l'erreur nous interesse.")

    for label, fn in (
        ("feature SweeperTaskMgr/CurrentTask = {'taskState': 'zzInvalide'}",
         lambda: client.set_iot_feature(
             serial, RESOURCE, IDX, "SweeperTaskMgr", "CurrentTask",
             {"taskState": "zzInvalide"})),
        ("action  SweeperTaskMgr/CurrentTask = {'taskState': 'zzInvalide'}",
         lambda: client.set_iot_action(
             serial, RESOURCE, IDX, "SweeperTaskMgr", "CurrentTask",
             {"taskState": "zzInvalide"})),
        ("feature SweeperTaskMgr/ZzzBidon = {'taskState': 'zzInvalide'}  (temoin)",
         lambda: client.set_iot_feature(
             serial, RESOURCE, IDX, "SweeperTaskMgr", "ZzzBidon",
             {"taskState": "zzInvalide"})),
    ):
        log.append(dump(label, fn))

    # ---------- Etat final ----------
    print("\n" + "=" * 70)
    print("ETAT FINAL DU ROBOT")
    print("=" * 70)
    log.append(dump(
        "lecture CurrentTask",
        lambda: client.get_device_feature_value(
            serial, RESOURCE, "SweeperTaskMgr", "CurrentTask", local_index=IDX
        ),
    ))

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump(log, fh, indent=2, ensure_ascii=False)
    print(f"\n\nResultat ecrit dans {OUTFILE}")
    print("Envoie-moi la sortie console.")


if __name__ == "__main__":
    main()
