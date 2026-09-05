# Intégration Home Assistant pour aspirateur robot EZVIZ (RE5 Plus)

Piloter un **robot aspirateur EZVIZ** depuis **Home Assistant** : démarrage,
pause, retour à la base, **puissance d'aspiration**, **volume d'eau**,
batterie et usure des consommables. Développée et validée sur un
**EZVIZ RE5 Plus (CS-RE5P-TWT)**.

*Home Assistant custom integration for **EZVIZ robot vacuums** — start, pause,
return to dock, **suction power**, **water level**, battery and consumable
wear. Built and tested on an EZVIZ RE5 Plus.*

Avec une carte Lovelace assortie.

L'intégration officielle `ezviz` ne gère que les caméras, sonnettes, ampoules
et prises : les robots ne correspondent à aucune de ses catégories d'appareil.
Celle-ci parle au même cloud, par le bus « iot-feature ».

**Modèles.** Validé sur le RE5 Plus. Les autres robots EZVIZ — RE4, RE5,
RE7, RS2, RS20, RC3 — utilisent vraisemblablement le même bus : les outils de
`tools/` permettent de le vérifier en quelques minutes.

## Installation

**Par HACS** (recommandé) : HACS → Intégrations → menu ⋮ → *Dépôts
personnalisés* → coller l'adresse de ce dépôt, catégorie *Integration*.
Puis installer, redémarrer Home Assistant, et ajouter l'intégration
« EZVIZ Vacuum » avec les identifiants de ton compte EZVIZ.

**À la main** : copier `custom_components/ezviz_vacuum/` dans le dossier
`custom_components/` de ta configuration, puis redémarrer.

**La carte** : copier `cards/ezviz-vacuum-card.js` dans `www/`, puis
l'ajouter en ressource Lovelace (`/local/ezviz-vacuum-card.js`, type module).
Un seul fichier suffit — les photos du robot y sont embarquées, il n'y a
rien à déposer dans le dossier média ni à configurer.

## Ce que ça donne

Une entité `vacuum` — démarrage, pause, reprise, arrêt, retour à la base —
plus des capteurs : batterie, puissance d'aspiration, panne en cours, et
l'usure des cinq consommables (serpillère, filtre HEPA, brosses, capteurs).

La puissance d'aspiration est exposée en **lecture seule** (capteur
« Aspiration »), et les cartes et pièces du robot en attributs de l'entité.

## Le bouton de dépannage

Quand le robot se coince — une serviette, une roue en l'air — la pause ne le
repart pas une fois dégagé : il faut lui redonner un ordre de **retour à la
base**, qui solde la tâche en cours, avant de pouvoir en lancer une nouvelle.
La carte enchaîne les deux, derrière un triangle de détresse qui clignote en
rouge et n'apparaît que dans ce cas.

**Le détecter a demandé de renoncer à l'évidence.** Ni `CurrentTask.exception`
ni l'état `error` ne servent à rien ici : sur dix jours d'historique, le
capteur de panne n'a jamais quitté « ok », y compris pendant des blocages
avérés. Ce firmware ne remonte pas les incidents physiques.

**Ce qui se voit, mesuré en direct sur un robot volontairement coincé : il
se tait.** `task_state` passe à vide et n'en bouge plus. L'état de l'entité,
lui, reste « en nettoyage » — l'intégration conserve l'activité précédente
quand `task_state` se vide, pour absorber le clignotement connu, si bien
qu'elle ne basculera jamais d'elle-même.

```
état       : cleaning     <- inchangé, et le restera
task_state : ""           <- le robot s'est tu
last_updated : figé depuis  <- l'instant du silence
```

On mesure donc le silence : hors de sa base, `task_state` vide depuis assez
longtemps. `last_updated` date le dernier changement d'attribut, donc
l'instant exact où il s'est tu.

Le clignotement ne peut pas déclencher : `task_state` alterne toutes les 20
à 40 secondes pendant un nettoyage normal, et chaque alternance remet ce
compteur à zéro. Seul un silence prolongé le laisse monter.

L'`idle` prolongé reste surveillé en parallèle — c'est l'autre forme
d'immobilité, celle où le robot annonce un état au lieu de se taire :

| `idle` observés | Durée |
|---|---|
| entre deux sessions, normal | 30 s à 3 min |
| blocages réels | 22 min, 31 min, 2 h 51 |

**Deux mécanismes, deux seuils** — ils n'ont pas la même contrainte :

| Mécanisme | Ce qui le borne | Seuil |
|---|---|---|
| silence (les vrais blocages) | le clignotement de `task_state`, 20 à 40 s | **2 min**, réglable |
| `idle` prolongé | un arrêt normal entre deux sessions, jusqu'à 3 min | 5 min, fixe |

Le seuil réglable est celui du silence, parce que c'est lui qui attrape les
blocages et qu'on le veut court : on va à la tablette *parce qu'on a vu* le
robot coincé, le bouton doit déjà être là. Ne pas descendre sous 2 minutes,
sous peine de voir le triangle clignoter en plein nettoyage normal — et un
voyant qui crie au loup finit par ne plus être vu.

⚠️ Un robot immobilisé ne publie plus rien : sans changement d'état, Home
Assistant ne réveille jamais la carte. Elle se redessine donc d'elle-même
toutes les 30 secondes, uniquement pour regarder l'heure.

## Ce que cette intégration ne peut pas faire

**Régler l'aspiration, le volume d'eau et le nombre de passages**, et
**nettoyer une pièce précise**. Ces fonctions ont été implémentées, testées,
puis retirées — deux fois plutôt qu'une, la seconde après s'être laissé
prendre au piège décrit ci-dessous.

Le cloud EZVIZ expose deux routes. Elles ne sont pas équivalentes :

| Route | Effet | Réponse |
|---|---|---|
| `/v3/iot-feature/action/…` | atteint l'appareil | `200` **avec** `deviceMeta` |
| `/v3/iot-feature/feature/…` | met à jour le cache du cloud | `200` **sans** `deviceMeta` |

Démarrer, mettre en pause et renvoyer à la base sont des **actions** : le
robot les reçoit et les exécute.

Les trois réglages vivent ensemble dans la **propriété**
`SweeperMapMgr.StdCleanCfg` — `{mapID, cleanConfigType, fanMode,
waterQuantity, cleanTimes}`. Y écrire ne commande rien.

### Le bloc-notes du cloud

C'est le piège, et il est redoutable. `StdCleanCfg` se comporte comme un
bloc-notes partagé : il affiche fidèlement le dernier qui y a écrit, qu'il
ait commandé le robot ou non.

L'application EZVIZ, elle, fait **deux** choses : elle écrit le bloc-notes
*et* envoie une vraie commande à l'appareil. Nous ne faisons que la première.
D'où une illusion parfaite — l'entité affiche la nouvelle valeur, la
relecture la confirme, l'historique aussi, **et l'application EZVIZ également,
puisqu'elle lit ce même bloc-notes**.

Trois « preuves » qui n'en sont pas :

- **Un `200`.** Il n'atteste que la réception côté serveur.
- **La valeur qui tient dans le temps.** On pourrait croire que l'appareil
  l'a adoptée, faute d'être corrigée. Mais l'appareil ne republie pas cet
  objet : rien ne corrige jamais le bloc-notes. Une valeur fantaisiste y
  restera des heures. (Ce raisonnement vaut pour `CurrentTask`, déclarée
  `rwu` — le `u` pour *upload* — pas pour `StdCleanCfg`.)
- **L'application EZVIZ qui affiche le changement.** Elle lit le cloud.

**Le seul juge fiable est l'appareil lui-même :** le RE5 Plus émet un **bip
de confirmation** à chaque réglage reçu, et l'aspiration s'entend. Pas de
bip, pas de commande. Vérifiez à l'oreille, jamais à l'écran.

### Le nettoyage par pièce

`SweeperMapMgr.SetRoomCustomCleanCfg` (`sid=24`) est une vraie action, et son
schéma porte exactement les bons champs — `fanMode`, `waterQuantity`,
`cleanTimes` par pièce. Mais elle répond invariablement `0x00100003`, quelle
que soit la charge utile : toutes les pièces des deux cartes, les zones
personnalisées, avec ou sans `order`, avec ou sans `regionType`, avec
`source`, et carte passée en `custom` au préalable. Le code ne varie jamais —
ce n'est donc pas un problème de validation, mais un refus de l'appareil dont
la raison nous échappe encore.

Ces réglages restent donc à faire depuis l'application EZVIZ. La vraie
commande existe forcément, puisque l'application la passe : il faudra
intercepter son trafic pour la voir.

## Limites connues

- **Cloud uniquement.** Aucune commande locale : sans Internet, rien ne
  répond. Le robot n'expose pas d'API sur le réseau local.
- **Pas de réglage d'aspiration, d'eau ni de passages, pas de nettoyage par
  pièce** — voir la section précédente.
- **La carte active change toute seule.** Le robot bascule entre ses cartes au
  fil de ses trajets ; un code qui suppose une carte fixe se trompera.
- **Les pièces s'appellent « Pièce N ».** `RoomBasicProperty`, seule
  propriété censée porter les noms, renvoie `true` au lieu de son tableau sur
  ce firmware. Sans conséquence pratique : c'est l'association aux zones Home
  Assistant qui leur donne leur vrai nom.
- **Pas de carte affichable.** Les contours ne sont pas exposés par cette
  API ; seuls les noms et identifiants des pièces le sont.
- **Double authentification non gérée** à la configuration.

## Compatibilité

Développé contre Home Assistant **2026.8** et validé sur un **RE5 Plus**
(firmware V0.01.92). Les autres robots EZVIZ (RE4, RE5, RS2, RC3, RS20…)
utilisent vraisemblablement le même bus : les outils de `tools/` permettent de
le vérifier, et les retours sont bienvenus.

---

# Notes de rétro-ingénierie

Ce qui suit documente comment le protocole a été découvert, et surtout les
impasses — pour éviter de les reparcourir.

## Le bus iot-feature

EZVIZ pilote ses appareils non-caméra via un bus générique :

```
PUT /v3/iot-feature/feature/{SERIAL}/{resource}/{index}/{domain}/{action}
PUT /v3/iot-feature/action/{SERIAL}/{resource}/{index}/{domain}/{action}
```

C'est ce bus qui pilote déjà les ampoules EZVIZ. Les robots y exposent bien
leurs commandes, mais **sur la route `action`, pas `feature`** — c'est ce
détail qui a coûté le plus de temps.

## État d'avancement

- [x] **Étape 1 — Découverte** : le RE5 Plus expose bien ses propriétés sur le
      bus iot-feature (voir *Ce qu'on sait* ci-dessous)
- [x] **Étape 1a — Lecture confirmée** : `get_device_feature_value()` renvoie
      bien les valeurs en direct (batterie, état de la tâche)
- [x] **Étape 1b — Vocabulaire d'état** : capturé en observant le robot piloté
      depuis l'app (voir *États observés*). Manque l'état de retour à la base.
- [x] **Étape 1c — Écriture** : mécanisme trouvé et validé (voir *Commander
      le robot*)
- [x] **Étape 2 — Validation** : `start`, `pause`, `resume` et `stop` testés
      sur le robot, tous suivis d'effet
- [x] **Étape 3 — Intégration** : entité `vacuum` (start / pause / stop /
      return_to_base / batterie / puissance d'aspiration)
- [x] **Étape 4a — Schéma des cartes** : extrait, le nettoyage par pièce est
      pilotable (voir *Nettoyage par pièce*)
- [x] **Étape 4b — Nettoyage par pièce** : implémenté, testé, **retiré** —
      `SetRoomCustomCleanCfg` répond `0x00100003` quoi qu'on lui envoie
- [x] **Étape 5 — Réglages globaux** : implémentés par écriture de
      `StdCleanCfg`, **retirés** — c'est le bloc-notes du cloud, le robot
      n'émet aucun bip et rien ne change à l'oreille
- [ ] **Étape 6 — La capture de trafic.** Seule voie restante, pour les
      réglages comme pour le nettoyage par pièce. Tout le reste a été
      épuisé : plus de 500 noms d'action essayés, et le profil complet du
      produit ne se télécharge pas — les URL de profil répondent toutes
      `http allow list not found`.

## Les actions connues

Trouvées en écrivant une valeur invalide sur un nom candidat, route `action` :
la réponse d'erreur contient le schéma complet (voir *La fuite de schéma*).
Plus de 500 noms essayés pour ces six-là, tous dans `tools/`.

| Domaine | Action | `sid` | Entrée |
|---|---|---|---|
| `SweeperCleanTask` | `CleanCtrl` | 6 | `action` ∈ start, pause, resume, stop |
| `SweeperTaskMgr` | `RechargeCtrl` | 3 | `action` ∈ start, stop |
| `SweeperMapMgr` | `SetCleanCfg` | 20 | `mapID`, `cleanConfigType` |
| `SweeperMapMgr` | `SetRoomName` | 11 | `mapID`, `roomID`, `roomName` |
| `SweeperMapMgr` | `SetRoomCustomCleanCfg` | 24 | réglages par pièce — **refuse** |
| `SweeperMapMgr` | `SwitchMap` | 26 | l'identifiant de carte, en entier nu |

Les `sid` manquants (1, 2, 4, 5, 7-10, 12-19, 21-23, 25) sont autant d'actions
qui existent et dont on n'a pas trouvé le nom.

⚠️ **`SetCleanCfg` n'applique que `cleanConfigType`.** Lui glisser `fanMode`
en passager donne un accusé de réception du robot, et aucun effet : le cloud
transmet les champs non déclarés, le firmware les jette.

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

`source` vaut `mobile` (app) ou `smartSpeaker` (enceinte). Pour `CleanCtrl`,
seul `action` est requis.

**Retour à la base** — autre domaine, autre action :

```python
client.set_iot_action(
    "BD1522206", "SweepingRobot", "0",
    "SweeperTaskMgr", "RechargeCtrl",
    {"action": "start", "source": "mobile"},
)
```

`RechargeCtrl` (`sid=3`, `direction=Plt2Dev`) prend `action` ∈ `start`
(开始回充, lancer le retour) ou `stop` (结束回充, l'interrompre). Ici
**`action` et `source` sont tous deux requis**.

`CleanCtrl` avec `stop` renvoie aussi le robot à sa base — vérifié.

### Reconnaître une commande qui a vraiment abouti

Une commande reçue par l'appareil renvoie un bloc `deviceMeta` :

```json
{"meta": {"code": 200, "message": "success",
          "moreInfo": {"deviceMeta": {"code": "0x00000000",
                                      "errorMsg": "success"}}}}
```

C'est l'accusé de réception du robot. Un `200` **sans** `deviceMeta` (comme
pour une écriture sur `CurrentTask`) signifie que seul le cloud a répondu et
que l'appareil n'a rien reçu.

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

**`SweeperMapMgr.RoomBasicProperty`** — annonce ce schéma :

```
[{ mapID, room: [{ roomID, roomName, backgroundColor }] }]
```

⚠️ **mais ne renvoie jamais ce tableau.** Sur le RE5 Plus (firmware
V0.01.92), une lecture directe répond `code 200` avec la donnée `true` — un
simple drapeau de capacité, pas un porteur de données. `FEATURE_INFO` montre
la même chose. **Les noms de pièces ne sont pas récupérables par cette
propriété** ; inutile d'insister.

Les identifiants de pièces viennent donc de `RoomCustomCleanCfg`, qui, elle,
renvoie bien son tableau. Les segments exposés à Home Assistant s'appellent
« Pièce N » — sans conséquence, puisque l'association aux zones leur donne
leur vrai nom.

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

**Séquence pour nettoyer des pièces précises** — implémentée dans
`vacuum.py` :

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
