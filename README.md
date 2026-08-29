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
- [x] **Étape 4a — Schéma des cartes** : extrait, le nettoyage par pièce est
      pilotable (voir *Nettoyage par pièce*)
- [ ] **Étape 4b — Nettoyage par pièce** : à implémenter et valider

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

Les commandes passent par la route **`action`**, jamais par `feature` :

```python
client.set_iot_action(
    "BD1522206", "SweepingRobot", "0",
    "SweeperCleanTask", "CleanCtrl",
    {"action": "start", "source": "mobile"},
)
```

Schéma de `CleanCtrl` (`sid=6`, `direction=Plt2Dev` — plateforme vers
appareil, c'est le vrai canal de commande) :

| `action` | Libellé d'origine |
|---|---|
| `start` | 开始全屋清洁 — démarrer le nettoyage complet |
| `pause` | 暂停清洁 — mettre en pause |
| `resume` | 继续清洁 — reprendre |
| `stop` | 停止清洁 — arrêter |

`source` vaut `mobile` (app) ou `smartSpeaker` (enceinte). `action` est requis,
`source` non.

> ⚠️ **`SweeperTaskMgr.CurrentTask` n'est PAS une commande.** C'est un miroir
> d'état (`access=rwu`, le `u` pour *upload* : l'appareil le remonte). Y écrire
> renvoie `200`, le robot ne bouge pas, et **l'objet entier est remplacé** dans
> le cache du cloud — après un envoi de `{"taskState": …}`, la relecture ne
> renvoie plus que ce champ. Le cache se répare seul, l'appareil republiant son
> état toutes les ~4 s.

### Ce qui a coûté du temps

- Les commandes ne sont pas sur `feature` mais sur `action`, et il faut y
  envoyer un `PUT`. Un `GET` sur une URL d'action répond **405 pour tout**,
  y compris les noms inventés — ce qui masque complètement l'existence des
  actions réelles. Sonder les actions **en PUT avec une valeur invalide**.
- `set_device_feature_by_key()` ne marche pas ici → `itemKey不存在`. Cette
  route attend une clé plate façon ampoule (`light_switch`), absente sur ce
  modèle. Utiliser `set_iot_feature()` / `set_iot_action()`.
- `forceCheck`, aperçu dans le `PropertyRequest`, n'est pas réglable par le
  client : en paramètre d'URL il reste `null`, et dans le corps il est absorbé
  par la valeur — le corps de la requête *est* la valeur.
- Envelopper un scalaire dans un objet échoue :
  `$: object found, integer expected`. Pour `PromptToneVolume` on envoie `80`,
  pas `{"PromptToneVolume": 80}`.

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

## Nettoyage par pièce

Tout est en écriture. Trois propriétés à combiner.

**`SweeperMapMgr.RoomBasicProperty`** (`rw`) — l'annuaire des pièces, avec
leurs noms. À lire pour nommer les zones côté Home Assistant.

```
[{ mapID, room: [{ roomID, roomName, backgroundColor }] }]
```

⚠️ `FEATURE_INFO` la réduit à `true` ; il faut passer par
`get_device_feature_value()` pour obtenir le tableau réel.

**`SweeperMapMgr.RoomCustomCleanCfg`** (`rw`) — le réglage par pièce.

```
[{ mapID, room: [{ regionType: "room" | "customRegion",
                   roomID,          # si regionType = room
                   customRegionID,  # si regionType = customRegion
                   fanMode, waterQuantity, cleanTimes,
                   order }] }]
```

`order` (清洁顺序, ordre de nettoyage) commande la sélection : les pièces du
robot sont toutes à `-1`, donc exclues. Un ordre positif les fait entrer dans
la tâche.

**`SweeperMapMgr.StdCleanCfg`** (`rw`) — le mode global de la carte.

```
[{ mapID, cleanConfigType: "universal" | "custom",
   fanMode, waterQuantity, cleanTimes }]
```

`universal` = toute la surface, `custom` = 按房间定制, « personnalisé par
pièce ».

**Séquence pour nettoyer des pièces précises** — à valider :

1. `RoomCustomCleanCfg` : `order` positif sur les pièces voulues, `-1` sur les
   autres
2. `StdCleanCfg` : `cleanConfigType = "custom"` sur la carte concernée
3. `CurrentTask` : `{"taskState": "clean"}`

### Réglages d'aspiration

Communs à `StdCleanCfg` et `RoomCustomCleanCfg` — ils alimenteront le
`fan_speed` de l'entité Home Assistant :

| `fanMode` | | `waterQuantity` | |
|---|---|---|---|
| `quiet` | silencieux | `dry` | serpillère sèche |
| `normal` | standard | `low` | faible |
| `strong` | puissant | `middle` | moyen |
| `super` | maximum | `high` | élevé |

### Zones interdites et murs virtuels

`ForbiddenRegion` et `VirtualWall` sont en écriture, coordonnées comprises —
de quoi créer une zone interdite depuis une automatisation.

- `ForbiddenRegion` : rectangles `ltx/lty/rbx/rby`, de type `sweep`, `mop`,
  `sweepMop` ou `time` (interdiction horaire, avec `timeStart`/`timeEnd`)
- `VirtualWall` : segments `startX/startY` → `endX/endY`

### Diagnostic

`CurrentTask.exception` énumère environ 80 pannes, chacune traduite :
`CR_RollBrushTwine` (brosse enroulée), `CR_DirtyWaterBoxFull` (bac à eau sale
plein), `CR_FailToReturnDock` (échec du retour à la base),
`CR_CleanWaterBoxEmpty` (réservoir vide), `CR_Trapped` (robot coincé)…
Matière à de vrais capteurs, plutôt qu'un booléen « en erreur ».

### Autres propriétés inscriptibles

| Propriété | Forme |
|---|---|
| `SweeperCleanTask.CarpetTurboCleanSwitch` | `{"enabled": bool}` — surpression sur tapis |
| `SweeperMgr.RestMode` | `{"enabled", "startTime", "endTime"}` — mode silence |
| `SweeperMgr.ValleyCharge` | idem — charge en heures creuses |
| `SoundSetting.PromptToneVolume` | entier |
| `InfoMgr.DeviceLanguage` | `{"languageType": "french"}` |
| `SweeperMapMgr.AreaUnitCfg` | `{"unit": "m2"}` |

`SweeperMapMgr.CustomRegion` répond `设备不支持该功能` : elle apparaît dans
`FEATURE_INFO` mais n'est pas inscriptible sur ce modèle.

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

### `tools/ezviz_go.py`

Envoie les vraies commandes via `CleanCtrl`, chacune confirmée au clavier, puis
cherche l'action de retour à la base.

```bash
python3 tools/ezviz_go.py [SERIAL]
```

### `tools/ezviz_try_action.py`

Teste l'écriture d'une clé repérée à l'étape 1.

```bash
python3 tools/ezviz_try_action.py <SERIAL> <PRODUCT_ID> <CLÉ> <VALEUR>
```

## Crédits

S'appuie sur [`pyezvizapi`](https://github.com/RenierM26/pyEzvizApi) de
Renier Moorcroft, la bibliothèque derrière l'intégration EZVIZ officielle.
