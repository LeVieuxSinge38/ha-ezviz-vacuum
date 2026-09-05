#!/usr/bin/env python3
"""
Reencode les photos du robot et les injecte dans la carte.

Les photos ne sont ni telechargees ni cherchees dans un dossier media :
elles sont ecrites en base64 dans ezviz-vacuum-card.js. C'est la seule facon
d'etre sur que tout le monde les voie sans rien configurer, y compris quand
la carte est servie comme ressource « inline » (une data: URI, sans adresse
de base a laquelle rattacher un chemin relatif).

Trois traitements, dans cet ordre :
  1. couper les marges transparentes, pour que le robot remplisse le cadre ;
  2. mettre au carre - le balayage du lidar est un cercle centre sur la
     boite, il n'epouse la coque que si la boite est carree ;
  3. reduire a 224 px et encoder en WebP : la carte n'affiche que 96 px au
     maximum, 224 couvre les ecrans a haute densite, et WebP pese environ
     quatre fois moins qu'un PNG a qualite egale.

Usage, depuis la racine du depot :
    python3 tools/embed_photos.py
"""

from __future__ import annotations

import base64
import io
import re
import sys
from pathlib import Path

from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
CARTE = RACINE / "cards" / "ezviz-vacuum-card.js"
SOURCES = {
    "EVC_PHOTO_DOCKED": RACINE / "cards" / "images" / "re5-base.png",
    "EVC_PHOTO_MOVING": RACINE / "cards" / "images" / "re5-dessus.png",
}
CIBLE = 224


def encoder(src: Path) -> str:
    im = Image.open(src).convert("RGBA")
    bbox = im.getbbox()
    if bbox:
        im = im.crop(bbox)
    cote = max(im.size)
    carre = Image.new("RGBA", (cote, cote), (0, 0, 0, 0))
    carre.paste(im, ((cote - im.width) // 2, (cote - im.height) // 2))
    carre = carre.resize((CIBLE, CIBLE), Image.LANCZOS)
    buf = io.BytesIO()
    carre.save(buf, "WEBP", quality=82, method=6)
    data = buf.getvalue()
    print(f"  {src.name:20} -> {len(data):6} octets de WebP")
    return base64.b64encode(data).decode()


def main() -> None:
    texte = CARTE.read_text(encoding="utf-8")
    for nom, src in SOURCES.items():
        if not src.exists():
            sys.exit(f"Photo manquante : {src}")
        motif = re.compile(
            rf"(const {nom} = 'data:image/webp;base64,)[^']*(';)"
        )
        if not motif.search(texte):
            sys.exit(f"Constante {nom} introuvable dans {CARTE.name}")
        texte = motif.sub(lambda m: m.group(1) + encoder(src) + m.group(2), texte)

    CARTE.write_text(texte, encoding="utf-8", newline="\n")
    print(f"\n{CARTE.name} : {len(texte.encode('utf-8'))} octets")


if __name__ == "__main__":
    main()
