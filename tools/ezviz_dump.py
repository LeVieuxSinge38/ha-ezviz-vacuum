#!/usr/bin/env python3
"""
Decouverte des capacites d'un aspirateur EZVIZ via l'API cloud EZVIZ.

But : recuperer la liste des "iot-features" exposees par le robot (CS-RE5P-TWT2)
afin de savoir quelles cles pilotent le demarrage, la pause et le retour a la base.

Usage :
    pip install pyezvizapi
    python3 ezviz_dump.py

Le script demande le compte EZVIZ, se connecte, ecrit le dump complet dans
ezviz_dump.json et affiche un resume lisible des appareils non-camera.
"""

from __future__ import annotations

import getpass
import json
import sys
from typing import Any

try:
    from pyezvizapi import EzvizClient
except ImportError:
    sys.exit("Installe d'abord la lib :  pip install pyezvizapi")

# apiieu = Europe. Autres regions : apius, apiisgp, apiaa...
REGION = "apiieu.ezvizlife.com"
OUTFILE = "ezviz_dump.json"


def walk_features(node: Any, path: str = "") -> list[tuple[str, Any]]:
    """Aplatit le bloc FEATURE pour reperer les cles interessantes."""
    found: list[tuple[str, Any]] = []
    if isinstance(node, dict):
        for k, v in node.items():
            found += walk_features(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found += walk_features(v, f"{path}[{i}]")
    else:
        found.append((path, node))
    return found


def main() -> None:
    account = input("Compte EZVIZ (email ou tel) : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()  # gere la MFA de facon interactive si le compte en a une
    print("Connexion OK\n")

    devices = client.get_device_infos()

    with open(OUTFILE, "w", encoding="utf-8") as fh:
        json.dump(devices, fh, indent=2, ensure_ascii=False)
    print(f"Dump complet ecrit dans {OUTFILE}\n")

    for serial, dev in devices.items():
        infos = dev.get("deviceInfos", {}) or {}
        name = infos.get("name", "?")
        category = infos.get("deviceCategory", "?")
        subcat = infos.get("deviceSubCategory", "?")
        product_id = (
            infos.get("productId")
            or infos.get("productKey")
            or (dev.get("FEATURE") or {}).get("productId")
        )

        print("=" * 70)
        print(f"{name}   [{serial}]")
        print(f"  categorie     : {category} / {subcat}")
        print(f"  modele        : {infos.get('deviceType', '?')}")
        print(f"  productId     : {product_id}")
        print(f"  version       : {infos.get('version', '?')}")

        feature = dev.get("FEATURE") or {}
        feature_info = dev.get("FEATURE_INFO") or {}
        if not feature and not feature_info:
            print("  (aucun bloc FEATURE -> appareil pilote par l'API camera classique)")
            continue

        print("  --- cles iot-feature ---")
        for path, value in walk_features(feature):
            print(f"    {path} = {value!r}")
        if feature_info:
            print("  --- FEATURE_INFO ---")
            for path, value in walk_features(feature_info):
                print(f"    {path} = {value!r}")

    print("=" * 70)
    print("\nRepere la ligne du robot (CS-RE5P-TWT2) et envoie-moi ce bloc,")
    print(f"ou directement le fichier {OUTFILE}.")


if __name__ == "__main__":
    main()
