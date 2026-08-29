#!/usr/bin/env python3
"""
Test d'ecriture d'une iot-feature EZVIZ (etape 2, apres ezviz_dump.py).

Une fois la cle reperee dans le dump (ex. "work_mode", "clean_switch",
"charge_state"...), on essaie de l'ecrire pour voir si le robot reagit.

Usage :
    python3 ezviz_try_action.py <SERIAL> <PRODUCT_ID> <CLE> <VALEUR>

Exemple :
    python3 ezviz_try_action.py BD152220E abcd1234 work_mode 1
"""

from __future__ import annotations

import getpass
import json
import sys

from pyezvizapi import EzvizClient

REGION = "apiieu.ezvizlife.com"


def coerce(raw: str):
    """Convertit la valeur CLI en int/bool/json si possible."""
    for caster in (json.loads,):
        try:
            return caster(raw)
        except (ValueError, TypeError):
            pass
    return raw


def main() -> None:
    if len(sys.argv) != 5:
        sys.exit(__doc__)

    serial, product_id, key, raw_value = sys.argv[1:5]
    value = coerce(raw_value)

    account = input("Compte EZVIZ : ").strip()
    password = getpass.getpass("Mot de passe EZVIZ : ")

    client = EzvizClient(account, password, REGION)
    client.login()

    print(f"-> set {key} = {value!r} sur {serial} (product {product_id})")
    result = client.set_device_feature_by_key(serial, product_id, value, key)
    print(f"<- reponse : {result!r}")


if __name__ == "__main__":
    main()
