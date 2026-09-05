Sources des photos du robot.

`re5-base.png`   — le robot sur sa station, affiché quand il y est
`re5-dessus.png` — vu de dessus, affiché dès qu'il en part

**Ces fichiers ne sont pas lus à l'exécution.** La carte ne va chercher
aucune image : les deux photos sont écrites en base64 directement dans
`../ezviz-vacuum-card.js`. C'est la seule façon d'être sûr que tout le monde
les voie sans rien configurer — y compris quand la carte est servie comme
ressource « inline », c'est-à-dire une data: URI, sans adresse de base à
laquelle rattacher un chemin relatif.

Ils sont conservés ici pour pouvoir refaire l'encodage. Après les avoir
remplacés :

    python3 tools/embed_photos.py

Le script recadre sur le robot, met au carré, réduit à 224 px, encode en
WebP et réécrit les deux constantes de la carte.
