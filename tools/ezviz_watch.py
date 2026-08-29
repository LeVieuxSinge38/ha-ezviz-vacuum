#!/usr/bin/env python3
"""
Surveillance LECTURE SEULE des proprietes du robot EZVIZ.

Deviner les noms de commandes a echoue deux fois. Cette fois on laisse le
robot parler : le script releve toutes ses proprietes en boucle et affiche
uniquement ce qui CHANGE. Pendant ce temps, l'utilisateur pilote le robot
depuis l'app EZVIZ. Chaque appui dans l'app revele la propriete concernee et
la valeur exacte qu'elle prend.

C'est ainsi qu'on apprend le vocabulaire du robot (valeurs de taskState,
etc.) sans jamais rien ecrire.

IMPORTANT : lecture seule. Le script ne peut pas commander le robot.

Usage :
    python3 ezviz_watch.py [SERIAL]
    (Ctrl+C pour arreter)
"""

from __future__ import annotations

import getpass
import json
import sys
import time
from datetime import datetime
from typing import Any

from pyezvizapi import EzvizClient

REGION = "apiieu.ezvizlife.com"
DEFAULT_SERIAL = "BD1522206"
INTERVAL = 4.0
OUTFILE = "ezviz_watch.json"


def flatten(node: Any, path: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    if isinstance(node, dict):
        for k, v in node.items():
            out |= flatten(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out |= flatten(v, f"{path}[{i}]")
    else:
        out[path] = node
    return out


def snapshot(client: EzvizClient, serial: str) -> dict[str, Any]:
    devices = client.get_device_infos()
    dev = devices.get(serial, {})
    merged = {
        "FEATURE_INFO": dev.get("FEATURE_INFO", {}),
        "STATUS": dev.get("STATUS", {}),
        "SWITCH": dev.get("SWITCH", {}),
    }
    return flatten(merged)


def main() -> None:
    serial = (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SERIAL).upper()

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()

    print("\n" + "=" * 70)
    print("SURVEILLANCE ACTIVE - lecture seule")
    print("=" * 70)
    print(f"Cible : {serial}   |   releve toutes les {INTERVAL:.0f} s")
    print()
    print("  A FAIRE MAINTENANT, dans l'app EZVIZ sur ton telephone :")
    print()
    print("   1. Attends la ligne 'etat initial releve' ci-dessous")
    print("   2. Appuie sur DEMARRER  -> laisse tourner ~1 minute")
    print("   3. Appuie sur PAUSE     -> attends ~15 secondes")
    print("   4. Appuie sur RETOUR A LA BASE")
    print("   5. Attends qu'il soit revenu, puis Ctrl+C ici")
    print()
    print("=" * 70)

    previous = snapshot(client, serial)
    print(f"\n[{datetime.now():%H:%M:%S}] etat initial releve : "
          f"{len(previous)} proprietes. Vas-y, pilote depuis l'app.\n")

    timeline: list[dict[str, Any]] = [
        {"time": datetime.now().isoformat(), "event": "initial", "state": previous}
    ]

    try:
        while True:
            time.sleep(INTERVAL)
            try:
                current = snapshot(client, serial)
            except Exception as err:  # noqa: BLE001
                print(f"[{datetime.now():%H:%M:%S}] !! releve echoue : "
                      f"{type(err).__name__}: {err}")
                continue

            changes = []
            for key in sorted(set(previous) | set(current)):
                before, after = previous.get(key, "<absent>"), current.get(key, "<absent>")
                if before != after:
                    changes.append({"key": key, "avant": before, "apres": after})

            if changes:
                stamp = f"{datetime.now():%H:%M:%S}"
                print(f"[{stamp}] {len(changes)} changement(s)")
                for c in changes:
                    print(f"    {c['key']}")
                    print(f"        {c['avant']!r}  ->  {c['apres']!r}")
                print()
                timeline.append(
                    {"time": datetime.now().isoformat(), "event": "diff", "changes": changes}
                )
            previous = current

    except KeyboardInterrupt:
        print("\n\nArret demande.")

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump(timeline, fh, indent=2, ensure_ascii=False, default=str)
    print(f"Chronologie ecrite dans {OUTFILE} ({len(timeline)} entrees).")
    print("Envoie-moi ce fichier.")


if __name__ == "__main__":
    main()
