#!/usr/bin/env python3
"""
Extraction du schema complet + premieres vraies commandes du robot EZVIZ.

Decouverte cle : quand on ecrit une valeur invalide sur une propriete
inscriptible, l'API renvoie le SCHEMA COMPLET de cette propriete dans son
message d'erreur - types, bornes, enumerations. C'est une fuite exploitable :
elle documente l'appareil mieux que n'importe quelle devinette.

PHASE 1 - on s'en sert pour cartographier tout le robot. Une valeur trop
          longue est invalide pour tous les types, donc aucune ecriture ne
          peut aboutir. Strictement sans effet.

PHASE 2 - les vraies commandes, une par une, chacune confirmee au clavier.
          Rien ne part sans un 'o' explicite. On commence par le retour a la
          base alors que le robot y est deja : la commande est donc sans
          effet visible, mais prouve qu'on sait commander.

Usage :
    python3 ezviz_command.py [SERIAL]
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
TASK_DOMAIN = "SweeperTaskMgr"
TASK_PROP = "CurrentTask"
OUTFILE = "ezviz_schema.json"

# Trop longue pour une chaine (maxLength=64), du mauvais type pour un entier,
# un objet ou un tableau : invalide partout, donc jamais ecrite.
INVALID = "Z" * 300

TARGETS = [
    ("SweeperTaskMgr", "CurrentTask"),
    ("SweeperMapMgr", "StdCleanCfg"),
    ("SweeperMapMgr", "RoomCustomCleanCfg"),
    ("SweeperMapMgr", "MapBasicProperty"),
    ("SweeperMapMgr", "VirtualWall"),
    ("SweeperMapMgr", "ForbiddenRegion"),
    ("SweeperMapMgr", "CustomRegion"),
    ("SweeperMapMgr", "RoomBasicProperty"),
    ("SweeperMapMgr", "AreaUnitCfg"),
    ("SweeperCleanTask", "CarpetTurboCleanSwitch"),
    ("SweeperMgr", "ValleyCharge"),
    ("SweeperMgr", "RestMode"),
    ("SweeperConsumable", "MopWorkingTime"),
    ("PowerMgr", "SurplusPower"),
    ("SoundSetting", "PromptToneVolume"),
    ("InfoMgr", "DeviceLanguage"),
]


def read_task(client, serial):
    try:
        r = client.get_device_feature_value(
            serial, RESOURCE, TASK_DOMAIN, TASK_PROP, local_index=IDX
        )
        return r.get("data", r)
    except Exception as err:  # noqa: BLE001
        return f"<lecture impossible : {err}>"


def ask(question: str) -> bool:
    while True:
        answer = input(f"\n{question} [o/n] ").strip().lower()
        if answer in ("o", "oui", "y", "yes"):
            return True
        if answer in ("n", "non", "no"):
            return False


def send(client, serial, state: str):
    """Envoie une commande et affiche l'etat avant/apres."""
    print(f"\n  avant : {read_task(client, serial)}")
    print(f"  -> envoi taskState = {state!r}")
    try:
        result = client.set_iot_feature(
            serial, RESOURCE, IDX, TASK_DOMAIN, TASK_PROP, {"taskState": state}
        )
        print(f"  reponse : {json.dumps(result, ensure_ascii=False)[:300]}")
    except Exception as err:  # noqa: BLE001
        print(f"  ECHEC : {type(err).__name__}: {str(err)[:600]}")
        return
    for delay in (3, 6):
        time.sleep(delay)
        print(f"  apres {delay}s cumule : {read_task(client, serial)}")


def main() -> None:
    serial = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERIAL).upper()

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()
    print(f"\nConnexion OK - cible : {serial}")

    # ---------------- PHASE 1 : schemas ----------------
    print("\n" + "=" * 70)
    print("PHASE 1 - EXTRACTION DES SCHEMAS (sans effet)")
    print("=" * 70)

    schemas: dict[str, str] = {}
    for domain, prop in TARGETS:
        try:
            client.set_iot_feature(serial, RESOURCE, IDX, domain, prop, INVALID)
            verdict = "<accepte ?! - a examiner>"
        except Exception as err:  # noqa: BLE001
            verdict = str(err)  # non tronque : c'est la que vit le schema
        schemas[f"{domain}.{prop}"] = verdict
        supported = "设备不支持该功能" not in verdict
        print(f"  {'OK ' if supported else '-- '} {domain}.{prop}")

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump(schemas, fh, indent=2, ensure_ascii=False)
    print(f"\nSchemas ecrits dans {OUTFILE} - c'est le fichier a m'envoyer.")

    # ---------------- PHASE 2 : commandes ----------------
    print("\n" + "=" * 70)
    print("PHASE 2 - VRAIES COMMANDES")
    print("=" * 70)
    print("Chaque commande est confirmee separement. Repondre 'n' passe a la")
    print("suivante sans rien envoyer.")
    print(f"\nEtat actuel : {read_task(client, serial)}")

    if not ask("Le robot est-il bien SUR SA BASE ?"):
        print("\nOn s'arrete la : les tests supposent qu'il est arrime.")
        return

    print("\n" + "-" * 70)
    print("TEST 1 - retour a la base, alors qu'il y est deja.")
    print("La commande est donc sans effet visible : elle sert uniquement a")
    print("prouver qu'on sait commander. C'est le test le plus sur.")
    if ask("Envoyer 'cleanDoneRecharge' ?"):
        send(client, serial, "cleanDoneRecharge")

    print("\n" + "-" * 70)
    print("TEST 2 - DEMARRAGE REEL. Le robot va quitter sa base et nettoyer.")
    print("Ne reponds 'o' que si tu peux le surveiller.")
    if ask("Envoyer 'clean' (le robot va demarrer) ?"):
        send(client, serial, "clean")

        print("\n" + "-" * 70)
        if ask("Envoyer 'cleanPause' pour l'arreter en place ?"):
            send(client, serial, "cleanPause")

        print("\n" + "-" * 70)
        if ask("Envoyer 'cleanDoneRecharge' pour le renvoyer a sa base ?"):
            send(client, serial, "cleanDoneRecharge")

    print("\n" + "=" * 70)
    print(f"Etat final : {read_task(client, serial)}")
    print(f"\nEnvoie-moi {OUTFILE} et la sortie de la phase 2.")


if __name__ == "__main__":
    main()
