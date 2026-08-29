# ha-ezviz-vacuum

Intégration Home Assistant (en cours de développement) pour les aspirateurs
robots EZVIZ — cible initiale : **EZVIZ RE5 Plus (CS-RE5P-TWT2)**.

## Pourquoi ce dépôt

L'intégration officielle `ezviz` de Home Assistant ne gère que les caméras,
sonnettes, ampoules et prises. Les robots aspirateurs ne sont reconnus par
aucune catégorie d'appareil de la bibliothèque `pyezvizapi`, et aucune
intégration communautaire n'existe à ce jour.

En revanche, EZVIZ pilote ses appareils non-caméra via un bus générique
« iot-feature » :

```
PUT /v3/iot-feature/feature/{SERIAL}/{resource}/{index}/{domain}/{action}
PUT /v3/iot-feature/action/{SERIAL}/{resource}/{index}/{domain}/{action}
```

C'est ce bus qui pilote déjà les ampoules EZVIZ. L'hypothèse de travail est
que les robots y exposent aussi leurs commandes.

## État d'avancement

- [ ] **Étape 1 — Découverte** : lister les clés `FEATURE` exposées par le robot
- [ ] **Étape 2 — Validation** : confirmer qu'écrire une clé fait réagir le robot
- [ ] **Étape 3 — Intégration** : entité `vacuum` (start / pause / stop /
      return_to_base / batterie / puissance d'aspiration)
- [ ] **Étape 4 — Cartographie** : nettoyage par zones, si le robot expose les
      données nécessaires (incertain)

## Outils

### `tools/ezviz_dump.py`

Se connecte au compte EZVIZ et affiche les capacités de chaque appareil.

```bash
pip install -U pyezvizapi
python3 tools/ezviz_dump.py
```

Écrit `ezviz_dump.json` et affiche un résumé par appareil.

> Le fichier `ezviz_dump.json` contient les numéros de série et codes de
> vérification de tous les appareils du compte. Il est ignoré par Git —
> ne le commite jamais.

### `tools/ezviz_try_action.py`

Teste l'écriture d'une clé repérée à l'étape 1.

```bash
python3 tools/ezviz_try_action.py <SERIAL> <PRODUCT_ID> <CLÉ> <VALEUR>
```

## Crédits

S'appuie sur [`pyezvizapi`](https://github.com/RenierM26/pyEzvizApi) de
Renier Moorcroft, la bibliothèque derrière l'intégration EZVIZ officielle.
