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

- [x] **Étape 1 — Découverte** : le RE5 Plus expose bien ses propriétés sur le
      bus iot-feature (voir *Ce qu'on sait* ci-dessous)
- [x] **Étape 1a — Lecture confirmée** : `get_device_feature_value()` renvoie
      bien les valeurs en direct (batterie, état de la tâche)
- [x] **Étape 1b — Vocabulaire d'état** : capturé en observant le robot piloté
      depuis l'app (voir *États observés*). Manque l'état de retour à la base.
- [x] **Étape 1c — Écriture** : mécanisme trouvé et validé (voir *Commander
      le robot*)
- [ ] **Étape 2 — Validation** : confirmer qu'écrire une clé fait réagir le robot
- [ ] **Étape 3 — Intégration** : entité `vacuum` (start / pause / stop /
      return_to_base / batterie / puissance d'aspiration)
- [ ] **Étape 4 — Cartographie** : nettoyage par pièce — les `roomID` sont
      exposés, c'est jouable

## Ce qu'on sait (RE5 Plus, firmware V0.01.92)

Catégorie EZVIZ : `SweepingRobot` / sous-type `RE5P`.

Les propriétés arrivent dans le bloc `FEATURE_INFO` sous la forme
`{localIndex}.{resource}.{domain}.{property}`, ce qui correspond directement à
l'URL du bus iot-feature :

```
/v3/iot-feature/feature/{SERIAL}/{resource}/{localIndex}/{domain}/{property}
```

Propriétés utiles repérées :

| Chemin | Rôle |
|---|---|
| `0.SweepingRobot.PowerMgr.SurplusPower` | niveau de batterie (%) |
| `0.SweepingRobot.SweeperTaskMgr.CurrentTask.taskState` | état de la tâche courante |
| `0.SweepingRobot.SweeperTaskMgr.CurrentTask.inCharging` | en charge ou non |
| `0.SweepingRobot.SweeperMapMgr.MapBasicProperty[]` | cartes : `mapID`, `mapName`, `inUse` |
| `0.SweepingRobot.SweeperMapMgr.RoomCustomCleanCfg[]` | pièces par carte : `roomID`, `fanMode`, `waterQuantity`, `cleanTimes` |
| `0.SweepingRobot.SweeperMapMgr.VirtualWall[]` | murs virtuels |
| `0.SweepingRobot.SweeperMapMgr.ForbiddenRegion[]` | zones interdites (coordonnées) |
| `0.SweepingRobot.SweeperConsumable.*` | usure brosses / filtre / serpillère |

### Lecture — confirmée

L'appel suivant fonctionne et renvoie la valeur en direct :

```python
client.get_device_feature_value(
    "BD1522206", "SweepingRobot", "PowerMgr", "SurplusPower", local_index="0"
)
# -> {"meta": {"code": 200}, "data": 77}
```

L'URL sous-jacente est en cinq segments :
`/v3/iot-feature/feature/{serial}/{resource}/{localIndex}/{domain}/{property}`.
Une URL plus courte renvoie 404 (mauvaise arité) ou 400.

Les 400 révèlent une **seconde route**, à paramètres de requête : elle attend
`channelNo` (entier) et `itemKey` (chaîne non vide). Piste à explorer — elle
pourrait renvoyer plusieurs propriétés d'un coup.

`resourceInfos` confirme `resourceIdentifier = "SweepingRobot"` et
`localIndex = "0"`.

### États observés

Capturés en pilotant le robot depuis l'app EZVIZ pendant que `ezviz_watch.py`
relevait les propriétés. Chemin :
`0.SweepingRobot.SweeperTaskMgr.CurrentTask`.

| `taskState` | Signification | `inCharging` |
|---|---|---|
| `''` | à l'arrêt / inactif | — |
| `'clean'` | nettoyage en cours | `0` |
| `'cleanPause'` | en pause | `0` |

**Le retour à la base n'a pas d'état propre.** Vérifié sur un cycle complet :
`taskState` repasse à `''`, puis `inCharging` passe à `1` une fois arrimé.
Aucune valeur `backCharge` / `goCharge` n'existe. Inutile de la chercher.

⚠️ **`taskState` clignote.** Pendant un nettoyage ininterrompu il alterne
`'clean'` et `''` toutes les 20–40 s. Une intégration qui s'y fierait seule
afficherait « à l'arrêt » en pleine session. Il faut le croiser avec
`inCharging` et amortir les transitions.

Autres observations pendant un cycle :

- `PowerMgr.SurplusPower` décroît d'environ 1 % par 30 s en nettoyage
- `CurrentTask.datetime` est un battement de cœur, mis à jour en permanence —
  à ignorer dans une intégration, sinon l'entité se rafraîchit sans cesse
- `SweeperMapMgr.StdCleanCfg[0].mapID` change quand le robot bascule de carte
- `CurrentTask.exception` est resté vide même quand le robot s'est retrouvé
  bloqué par un objet et soulevé — ce champ ne semble pas remonter les
  incidents physiques

## Commander le robot

`SweeperTaskMgr.CurrentTask` est déclaré `access=rwu` — inscriptible. On
commande le robot en y écrivant un `taskState` :

```python
client.set_iot_feature(
    "BD1522206", "SweepingRobot", "0",
    "SweeperTaskMgr", "CurrentTask",
    {"taskState": "clean"},
)
```

Valeurs acceptées, extraites de l'énumération du schéma :

| `taskState` | Libellé d'origine | Usage |
|---|---|---|
| `standby` | 休息中 | au repos |
| `clean` | 清洁中 | **démarrer le nettoyage** |
| `cleanPause` | 清洁暂停中 | **mettre en pause** |
| `cleanDoneRecharge` | 清洁完成回充 | **retour à la base** |
| `dryingMop` | 烘干拖布中 | séchage de la serpillère |
| `inspect` / `inspectPause` / `inspectDoneRecharge` | 巡检… | patrouille |
| `remoteControl` | 遥控中 | pilotage manuel |
| `fixedMotion` | 定点移动中 | déplacement ponctuel |
| `continueCharging` | 电量低补电中 | recharge batterie faible |

Ce qui ne marche **pas** :

- `/v3/iot-feature/action/…` → `设备功能未报备` (« fonction non déclarée »).
  Tout passe par `feature`, jamais par `action`.
- `set_device_feature_by_key()` → `itemKey不存在`. Cette route attend une clé
  plate façon ampoule (`light_switch`), que le robot n'expose pas. Utiliser
  `set_iot_feature()`.
- Envelopper la valeur d'un scalaire dans un objet →
  `$: object found, integer expected`. Pour `PromptToneVolume` on envoie `80`,
  pas `{"PromptToneVolume": 80}`. Pour `CurrentTask`, qui est de type objet,
  on envoie bien `{"taskState": …}`.

## La fuite de schéma

Écrire une valeur **invalide** sur une propriété inscriptible fait renvoyer par
l'API le **schéma JSON complet** de cette propriété : types, bornes,
énumérations et libellés. C'est la meilleure documentation disponible sur cet
appareil, et elle vient du serveur lui-même.

Une valeur trop longue (`"Z" * 300`) est invalide pour tous les types — chaîne
au-delà de `maxLength`, mauvais type pour un entier, un objet ou un tableau.
Elle ne peut donc jamais être écrite, ce qui en fait une sonde sûre.

Trois réponses distinctes, à savoir lire :

| Réponse | Signification |
|---|---|
| schéma détaillé + erreur de validation | propriété inscriptible, valeur refusée |
| `设备不支持该功能` | la propriété n'existe pas sur cet appareil |
| `设备功能未报备` | fonction non déclarée sur cette route |

Le schéma de `CurrentTask` contient aussi l'énumération complète des pannes
(`CR_LidarInitErr`, `CR_MopInstallErr`, `CR_DockDryFanStall`…), matière à de
vrais capteurs de diagnostic.

### Actions — point ouvert

`FEATURE_INFO` ne liste que les propriétés **lisibles**. Les
actions (démarrer, pause, retour à la base) passent vraisemblablement par
`/v3/iot-feature/action/...` et restent à identifier — c'est le rôle de
`tools/ezviz_probe.py`.

### L'oracle d'existence

Un `GET` sur le chemin en cinq segments répond **toujours** HTTP 200 ; c'est le
code **interne** qui tranche :

| Réponse interne | Signification |
|---|---|
| `{"code":200, "data":…}` | la propriété existe, voici sa valeur |
| `{"code":400, "msgDetail":"设备不支持该功能"}` | l'appareil ne gère pas cette fonction |

C'est un détecteur fiable et sans effet de bord : on peut tester autant de noms
qu'on veut sans jamais rien déclencher.

### productId

`get_device_infos()` renvoie `productId: None`, mais l'API se trahit dans ses
messages d'erreur — la route à paramètres recrache son objet interne :

```
FeatureGetParam(devSerial=BD1522206, protocol=0, channelNo=0,
                itemKey=…, productId=CS-RE5P-TWT,
                firmVersion=V0.01.92 build 240428, vFeatureItem=null)
```

**`productId = CS-RE5P-TWT`** (identique à `deviceType`). `itemKey` y est une
clé plate, pas un chemin pointé : les chemins `SweepingRobot.PowerMgr.…`
renvoient tous `itemKey不存在`.

### Ce qui ne marche pas — à ne pas refaire

- `/v3/iot-feature/action/…` en `GET` répond **405 pour tout**, y compris des
  noms inventés (page d'erreur Tomcat). Inutilisable comme détecteur.
  `OPTIONS` confirme `Allow: PUT`.
- Deux balayages de noms d'actions plausibles (228 combinaisons chacun) :
  aucun résultat. Deviner les noms est une impasse.

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

### `tools/ezviz_probe.py`

Sonde **en lecture seule** le bus iot-feature pour faire apparaître le schéma
complet du produit, actions comprises. Ne peut pas faire bouger le robot.

```bash
python3 tools/ezviz_probe.py [SERIAL]
```

### `tools/ezviz_probe2.py`

Recherche les **actions**, toujours en lecture seule. Deux approches :
la route à paramètres `channelNo`/`itemKey`, et un détecteur d'existence qui
fait un `GET` sur les URL d'action — une action s'invoque en `PUT`, donc le
`GET` ne déclenche rien, mais le code de retour (404 contre 405/400) trahit
son existence.

```bash
python3 tools/ezviz_probe2.py [SERIAL]
```

### `tools/ezviz_watch.py`

Surveille **en lecture seule** toutes les propriétés du robot et n'affiche que
ce qui change. On pilote le robot depuis l'app EZVIZ pendant que le script
tourne : chaque appui révèle la propriété concernée et sa valeur exacte. C'est
le robot qui livre son vocabulaire, au lieu de le deviner.

```bash
python3 tools/ezviz_watch.py [SERIAL]   # Ctrl+C pour arrêter
```

### `tools/ezviz_write_test.py`

Teste l'**écriture** sans effet sur le robot. Deux principes : réécrire une
valeur bénigne à l'identique (le volume des bips, à sa valeur actuelle) pour
valider le mécanisme sans rien changer ; puis écrire une valeur volontairement
invalide sur la tâche courante — elle ne peut pas être exécutée, mais la forme
de l'erreur distingue « chemin non inscriptible » de « valeur refusée ».

```bash
python3 tools/ezviz_write_test.py [SERIAL]
```

### `tools/ezviz_command.py`

Exploite la fuite de schéma pour cartographier tout le robot (phase 1, sans
effet), puis envoie les vraies commandes une par une, chacune confirmée au
clavier (phase 2).

```bash
python3 tools/ezviz_command.py [SERIAL]
```

### `tools/ezviz_try_action.py`

Teste l'écriture d'une clé repérée à l'étape 1.

```bash
python3 tools/ezviz_try_action.py <SERIAL> <PRODUCT_ID> <CLÉ> <VALEUR>
```

## Crédits

S'appuie sur [`pyezvizapi`](https://github.com/RenierM26/pyEzvizApi) de
Renier Moorcroft, la bibliothèque derrière l'intégration EZVIZ officielle.
