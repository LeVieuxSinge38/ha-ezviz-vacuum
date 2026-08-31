/* Carte aspirateur EZVIZ RE5 Plus, format compact.
   Une seule ligne : le robot, son état, sa batterie et les trois commandes.
   L'entretien vit sous un chevron, replié par défaut — on le consulte une
   fois par mois, il n'a rien à faire en permanence sur un tableau de bord.
   Toutes les tailles dérivent de --fs, réglable par font_scale. */

/* Les cinq pétales du logo EZVIZ. Ils tiennent le liseré de la carte et
   l'état du robot ; réglables par l'option `palette`. */
const EVC_BLUE    = '#1d9cd8';  // pétale bleu
const EVC_CYAN    = '#4cc3ec';  // bord clair du pétale bleu
const EVC_GREEN   = '#8cc63f';  // pétale vert
const EVC_YELLOW  = '#f5b21f';  // pétale jaune
const EVC_MAGENTA = '#ec008c';  // pétale magenta

/* Tout ce qui est un niveau — batterie, usure — suit l'échelle que tout le
   monde lit sans réfléchir : vert, orange, rouge. */
const EVC_OK   = '#5cb85c';
const EVC_WARN = '#f0951f';
const EVC_LOW  = '#e04b4b';

const EVC_STATES = {
  cleaning:   {t:'En nettoyage',     col:EVC_GREEN,   busy:true},
  returning:  {t:'Retour à la base', col:EVC_BLUE,    busy:true},
  paused:     {t:'En pause',         col:EVC_YELLOW,  busy:false},
  docked:     {t:'À la base',        col:EVC_CYAN,    busy:false},
  idle:       {t:"À l'arrêt",        col:'rgba(150,150,150,.85)', busy:false},
  error:      {t:'Erreur',           col:EVC_LOW,     busy:false},
  unavailable:{t:'Indisponible',     col:'rgba(150,150,150,.6)', busy:false}
};

/* Pannes du firmware, traduites. Les absentes s'affichent telles quelles. */
const EVC_FAULTS = {
  CR_RollBrushTwine:'Brosse enroulée', CR_EdgeBrushTrapped:'Brosse latérale coincée',
  CR_WheelTrapped:'Roue bloquée', CR_WheelSuspended:'Roue dans le vide',
  CR_Trapped:'Robot coincé', CR_FailToReturnDock:'Retour impossible',
  CR_LocationFailure:'Perte de repérage', CR_DustBoxOrBagUnset:'Bac absent',
  CR_DustBoxUncover:'Bac ouvert', CR_CleanWaterBoxEmpty:'Réservoir vide',
  CR_CleanWaterBoxLow:'Réservoir bas', CR_CleanWaterBoxUnsetup:'Réservoir absent',
  CR_DirtyWaterBoxFull:'Eau sale pleine', CR_DirtyWaterBoxUnsetup:'Bac eau sale absent',
  CR_AllWaterBoxUnsetup:'Réservoirs absents', CR_MopInstallErr:'Serpillère mal posée',
  CR_MopTryDrop:'Serpillère détachée', CR_RollBrushUnsetup:'Brosse absente',
  CR_LidarCoverErr:'Lidar obstrué', CR_LidarShieldErr:'Lidar masqué',
  CR_DockCommErr:'Base injoignable', CR_DockDryFanStall:'Séchage bloqué',
  CR_DockPumpSewageFail:'Vidange impossible'
};

function evcNum(v){
  if(v === null || v === undefined) return NaN;
  const t = String(v).trim();
  if(t === '') return NaN;
  const n = Number(t);
  return Number.isFinite(n) ? n : NaN;
}

/* Usure : verte tant qu'il reste de la marge, orange quand il faut y
   penser, rouge quand la pièce est à changer. */
function evcWearColor(w){
  if(isNaN(w)) return 'rgba(150,150,150,.7)';
  if(w >= 85) return EVC_LOW;
  if(w >= 65) return EVC_WARN;
  return EVC_OK;
}

/* RE5 Plus vu de dessus : à cette taille, le plan lit mieux qu'une
   perspective. Coque blanche, tourelle lidar, pare-chocs sombre à l'avant,
   brosse latérale à trois bras. L'anneau extérieur porte la couleur d'état. */
const EVC_ART = `
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="evcTop" cx="0.36" cy="0.3" r="0.78">
      <stop offset="0"   stop-color="#ffffff"/>
      <stop offset="0.55" stop-color="#e9edf2"/>
      <stop offset="1"   stop-color="#b9c1cc"/>
    </radialGradient>
  </defs>
  <circle class="halo" cx="50" cy="50" r="47" fill="none"
          stroke="var(--vc)" stroke-width="1.6" opacity=".35"/>
  <circle cx="50" cy="50" r="41" fill="url(#evcTop)"/>
  <circle cx="50" cy="50" r="41" fill="none" stroke="#ffffff"
          stroke-opacity=".7" stroke-width="1.2"/>
  <path d="M18,58 A41,41 0 0,0 82,58 L82,63 A41,41 0 0,1 18,63 Z"
        fill="#232a33" opacity=".92"/>
  <path class="sweep" d="M50,50 L50,9 A41,41 0 0,1 79,21 Z"
        fill="var(--vc)" opacity="0"/>
  <circle cx="50" cy="50" r="30" fill="none" stroke="#9aa4b1"
          stroke-opacity=".25" stroke-width="1"/>
  <circle cx="50" cy="38" r="12.5" fill="#39414c"/>
  <circle cx="50" cy="38" r="8.5"  fill="#151b22"/>
  <circle class="lidar" cx="50" cy="38" r="3.6" fill="var(--vc)"/>
  <circle cx="30" cy="60" r="4" fill="#e3e8ee" stroke="#9aa4b1"
          stroke-opacity=".45" stroke-width=".8"/>
  <g class="brush" transform="translate(70,66)">
    <circle r="4" fill="#39414c"/>
    <g stroke="#f8fafc" stroke-opacity=".9" stroke-width="1.8"
       stroke-linecap="round">
      <path d="M0,0 L11,-4"/><path d="M0,0 L-5,10"/><path d="M0,0 L-7,-8"/>
    </g>
    <circle r="1.6" fill="#cbd5e1"/>
  </g>
</svg>`;

class EzvizVacuumCard extends HTMLElement{
  constructor(){
    super();
    this.attachShadow({mode:'open'});
    this._built = false;
    this._open = false;
    /* Adresses résolues des `media-source://`, avec leur péremption. */
    this._srcCache = {};
    this._curId = null;
    /* État attendu après un appui, le temps que le robot publie le sien. */
    this._pending = null;
    this._pendUntil = 0;
  }

  setConfig(cfg){
    if(!cfg.entity) throw new Error('Il faut renseigner "entity"');
    if(cfg.entity.split('.')[0] !== 'vacuum')
      throw new Error('Cette carte attend une entité du domaine vacuum');

    this._cfg = Object.assign({
      name:null, battery:null, fault:null,
      image:null, image_docked:null,
      consumables:[], consumable_mode:'wear', show_hours:true, alert_wear:85,
      font_scale:1, art_size:112, image_round:false,
      palette:null
    }, cfg);
    this._cons = (cfg.consumables || []).map(c =>
      typeof c === 'string' ? {entity:c, name:null}
                            : {entity:c.entity, name:c.name || null});
    this._open = !!cfg.expanded;

    /* Une photo par état si l'utilisateur en fournit deux : le robot sur sa
       base quand il y est, vu de dessus quand il travaille. À défaut, le
       dessin, qui se recolore avec l'état. */
    this._photo = !!(this._cfg.image || this._cfg.image_docked);
    const art = this._photo
      ? '<img alt="">'
      : EVC_ART;

    this.shadowRoot.innerHTML = `
    <style>
    :host{
      display:block;
      --ez-blue: #1d9cd8;
      --ez-cyan: #4cc3ec;
      --ez-green: #8cc63f;
      --ez-yellow: #f5b21f;
      --ez-magenta: #ec008c;
    }
    ha-card{
      position:relative;overflow:hidden;container-type:inline-size;
      padding:12px 16px;
      border-radius:var(--ha-card-border-radius, 16px);
      /* Le liseré porte les cinq pétales du logo : deux fonds superposés,
         l'un plein jusqu'au bord du padding, l'autre en dégradé jusqu'au
         bord de la bordure — seule la bordure laisse voir le dégradé. */
      border:1.5px solid transparent;
      background:
        linear-gradient(
          var(--ha-card-background, var(--card-background-color, #1c1c1c)) 0 0)
          padding-box,
        conic-gradient(from 215deg,
          var(--ez-blue), var(--ez-cyan) 18%, var(--ez-green) 40%,
          var(--ez-yellow) 60%, var(--ez-magenta) 80%, var(--ez-blue))
          border-box;
    }

    /* Alerte d'entretien : un point rouge dans le coin, qui bat lentement.
       C'est la seule chose de la carte qui a le droit d'attirer l'œil. */
    .badge{
      position:absolute;top:7px;left:10px;z-index:2;
      width:17px;height:17px;border-radius:50%;
      display:flex;align-items:center;justify-content:center;
      background:#e04b4b;color:#fff;
      font-size:12px;font-weight:800;line-height:1;
      box-shadow:0 0 0 3px color-mix(in srgb, #e04b4b 22%, transparent);
      animation:evc-badge 1.6s ease-in-out infinite;pointer-events:auto;
      cursor:default;
    }
    @keyframes evc-badge{
      50%{opacity:.35;box-shadow:0 0 0 6px color-mix(in srgb, #e04b4b 0%, transparent)}
    }

    /* Trois zones : le robot à gauche sur toute la hauteur, les commandes
       empilées au milieu, l'état et la batterie à droite. */
    .row{display:flex;align-items:center;gap:14px}

    /* ---- le robot, mis en avant ---- */
    .art{
      flex:none;width:var(--art);height:var(--art);
      cursor:pointer;position:relative;
      filter:drop-shadow(0 3px 7px rgba(0,0,0,.22));
    }
    .art.photo{width:calc(var(--art) * 1.12)}
    .art svg{display:block;width:100%;height:100%}
    .art img{display:block;width:100%;height:100%;
      object-fit:contain;border-radius:10px}
    /* Le robot vu de dessus est rond : un cadrage circulaire fait disparaître
       les coins blancs de la photo produit, et le balayage vient alors
       épouser exactement le bord de la coque. */
    .art.round{width:var(--art)}
    .art.round img{object-fit:cover;border-radius:50%}

    /* Balayage du lidar, superposé à la photo pendant le travail. */
    .scan{
      position:absolute;inset:0;border-radius:50%;pointer-events:none;
      opacity:0;transition:opacity .5s;
      background:conic-gradient(from 0deg,
        color-mix(in srgb, var(--vc) 55%, transparent) 0deg,
        transparent 55deg, transparent 360deg);
      -webkit-mask:radial-gradient(circle, #000 62%, transparent 63%);
      mask:radial-gradient(circle, #000 62%, transparent 63%);
    }
    .art.busy .scan{opacity:.9;animation:evc-scan 1.8s linear infinite}
    @keyframes evc-scan{to{transform:rotate(360deg)}}
    .pulse{
      position:absolute;inset:3px;border-radius:50%;pointer-events:none;
      border:1.5px solid var(--vc);opacity:0;
    }
    .art.busy .pulse{animation:evc-ring 1.8s ease-out infinite}
    @keyframes evc-ring{
      0%{opacity:.55;transform:scale(.82)}
      100%{opacity:0;transform:scale(1.12)}
    }
    .brush{transform-origin:70px 66px}
    .busy .brush{animation:evc-spin .9s linear infinite}
    @keyframes evc-spin{to{transform:translate(70px,66px) rotate(360deg)}}
    .lidar{transition:opacity .3s}
    .busy .lidar{animation:evc-pulse 1.4s ease-in-out infinite}
    @keyframes evc-pulse{50%{opacity:.2}}
    .busy .sweep{animation:evc-sweep 2.4s linear infinite;transform-origin:50px 50px}
    @keyframes evc-sweep{
      0%{opacity:.22;transform:rotate(0deg)}
      100%{opacity:.22;transform:rotate(360deg)}
    }
    .halo{transition:opacity .4s}
    .busy .halo{animation:evc-halo 2s ease-in-out infinite}
    @keyframes evc-halo{50%{opacity:.85}}

    /* ---- colonne de droite : nom, état, batterie ---- */
    .info{
      flex:1 1 0;min-width:0;display:flex;flex-direction:column;
      align-items:flex-end;justify-content:center;gap:5px;text-align:right;
    }
    .txt{min-width:0;max-width:100%;display:flex;flex-direction:column;gap:1px;
      align-items:flex-end;cursor:pointer}
    .nm{
      font-size:calc(.68rem * var(--fs));font-weight:600;letter-spacing:.11em;
      text-transform:uppercase;opacity:.7;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
      /* Gris, comme le mot « EZVIZ » du logo : c'est une étiquette, elle
         n'a aucune information à porter. */
      color:var(--secondary-text-color);
    }
    .stt{
      display:flex;align-items:center;gap:6px;
      font-size:calc(1rem * var(--fs));font-weight:600;color:var(--vc);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
      transition:color .4s ease;
    }
    .dot{width:6px;height:6px;border-radius:50%;background:var(--vc);flex:none}
    .busy .dot{animation:evc-dot 1.3s ease-in-out infinite}
    @keyframes evc-dot{50%{opacity:.25;transform:scale(.7)}}
    .stt.err{color:var(--ez-magenta)}

    /* ---- batterie ---- */
    .bat{
      flex:none;display:flex;align-items:center;gap:4px;
      font-size:calc(1rem * var(--fs));font-weight:600;
      color:var(--bc);font-variant-numeric:tabular-nums;
    }
    .bat ha-icon{--mdc-icon-size:calc(20px * var(--fs))}
    .bat small{font-size:calc(.7rem * var(--fs));opacity:.7;margin-left:-1px}

    /* ---- commandes ----
       Empilées au milieu, en pastilles ouvertes et neutres : la couleur de
       la carte est déjà dans le liseré et dans l'état, les boutons n'ont pas
       à en rajouter. */
    /* Les commandes prennent une part de la largeur : sur une carte large
       elles s'étirent au lieu de laisser un trou au milieu. */
    .cmd{flex:none;width:clamp(46px, 20%, 172px);
      display:flex;flex-direction:column;gap:6px}
    .b{
      width:100%;height:calc(31px * var(--fs));
      border:0;border-radius:999px;cursor:pointer;padding:0;
      display:flex;align-items:center;justify-content:center;gap:7px;
      background:transparent;
      box-shadow:inset 0 0 0 1px
        color-mix(in srgb, var(--primary-text-color) 22%, transparent);
      transition:background .18s, box-shadow .18s;
      -webkit-tap-highlight-color:transparent;
    }
    .b:hover:not(:disabled){
      background:color-mix(in srgb, var(--primary-text-color) 10%, transparent)}
    .b:disabled{opacity:.28;cursor:not-allowed}
    .b ha-icon{--mdc-icon-size:calc(18px * var(--fs));
      color:var(--primary-text-color);opacity:.8;transition:opacity .18s}
    /* La commande en cours : pastille remplie, contour franc. */
    .b.on{
      background:color-mix(in srgb, var(--primary-text-color) 14%, transparent);
      box-shadow:inset 0 0 0 1.5px
        color-mix(in srgb, var(--primary-text-color) 45%, transparent);
    }
    .b.on ha-icon{opacity:1}
    /* Le libellé n'apparaît que si le bouton est assez large pour le porter
       en entier : jamais de texte tronqué. */
    .bl{display:none;font-size:calc(.78rem * var(--fs));font-weight:600;
      color:var(--primary-text-color);opacity:.8;white-space:nowrap}
    .b.on .bl{opacity:1}
    @container (min-width: 620px){ .bl{display:inline} }

    /* Le chevron n'est pas une commande du robot : il reste en marge. */
    .chev{
      flex:none;align-self:stretch;width:calc(22px * var(--fs)) !important;
      height:auto;
      background:transparent;box-shadow:none;border-radius:8px;
    }
    .chev:hover:not(:disabled){
      background:color-mix(in srgb, var(--primary-text-color) 7%, transparent)}
    .chev ha-icon{--mdc-icon-size:calc(20px * var(--fs));opacity:.5;
      transition:transform .3s ease}
    .chev.open ha-icon{transform:rotate(180deg)}

    /* ---- entretien, replié ---- */
    .fold{
      display:grid;grid-template-rows:0fr;
      transition:grid-template-rows .32s ease;
    }
    .fold.open{grid-template-rows:1fr}
    .foldin{overflow:hidden;min-height:0}
    .cons{
      display:grid;grid-template-columns:1fr 1fr;gap:9px 16px;
      margin-top:10px;padding-top:9px;
      border-top:1px solid var(--divider-color, rgba(127,127,127,.2));
    }
    .c .l{display:flex;align-items:baseline;gap:6px;margin-bottom:4px}
    .c .k{
      flex:1 1 auto;min-width:0;font-size:calc(.78rem * var(--fs));
      font-weight:500;color:var(--secondary-text-color);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .c .v{flex:none;font-size:calc(.82rem * var(--fs));font-weight:600;
      color:var(--wc);font-variant-numeric:tabular-nums}
    .c .v small{font-size:calc(.74rem * var(--fs));opacity:.7}
    .bar{height:3px;border-radius:999px;overflow:hidden;
      background:color-mix(in srgb, var(--primary-text-color) 10%, transparent)}
    .bar i{display:block;height:100%;border-radius:999px;
      transition:width .6s ease}

    /* Carte étroite : la photo cède la place en premier, c'est elle qui
       coûte le plus de largeur. */
    @container (max-width: 420px){
      .row{gap:10px}
      .art{width:calc(var(--art) * .8);height:calc(var(--art) * .8)}
      .art.photo{width:calc(var(--art) * .9)}
      .cons{grid-template-columns:1fr}
    }
    @container (max-width: 330px){
      .nm{display:none}
      .cmd{width:calc(40px * var(--fs))}
    }
    </style>
    <ha-card>
      <div class="badge" style="display:none">!</div>
      <div class="row">
        <div class="art">` + art +
              `<div class="scan"></div><div class="pulse"></div></div>
        <div class="cmd">
          <button class="b go" title="Démarrer">
            <ha-icon icon="mdi:play"></ha-icon><span class="bl">Démarrer</span></button>
          <button class="b pause" title="Pause">
            <ha-icon icon="mdi:pause"></ha-icon><span class="bl">Pause</span></button>
          <button class="b home" title="Retour à la base">
            <ha-icon icon="mdi:home-import-outline"></ha-icon><span class="bl">Base</span></button>
        </div>
        <div class="info">
          <div class="txt">
            <div class="nm"></div>
            <div class="stt"><span class="dot"></span><span class="lbl"></span></div>
          </div>
          <div class="bat"><ha-icon></ha-icon><span class="pct"></span></div>
        </div>
        <button class="b chev" title="Entretien">
          <ha-icon icon="mdi:chevron-down"></ha-icon></button>
      </div>
      <div class="fold"><div class="foldin"><div class="cons"></div></div></div>
    </ha-card>`;

    const r = this.shadowRoot;
    this._el = {
      card:r.querySelector('ha-card'), art:r.querySelector('.art'),
      img:r.querySelector('.art img'),
      nm:r.querySelector('.nm'), stt:r.querySelector('.stt'),
      lbl:r.querySelector('.lbl'), bat:r.querySelector('.bat'),
      batIcon:r.querySelector('.bat ha-icon'), pct:r.querySelector('.pct'),
      go:r.querySelector('.go'), pause:r.querySelector('.pause'),
      home:r.querySelector('.home'), chev:r.querySelector('.chev'),
      fold:r.querySelector('.fold'), cons:r.querySelector('.cons'),
      badge:r.querySelector('.badge')
    };
    this._el.card.style.setProperty('--fs', String(this._cfg.font_scale));
    this._el.card.style.setProperty('--art', this._cfg.art_size + 'px');
    /* `palette: {blue, cyan, green, yellow, magenta}` permet d'ajuster les
       teintes de marque sans toucher au code. */
    const pal = this._cfg.palette || {};
    for(const k of ['blue', 'cyan', 'green', 'yellow', 'magenta'])
      if(pal[k]) this.style.setProperty('--ez-' + k, pal[k]);
    this._el.art.classList.toggle('photo', this._photo);

    this._el.go.addEventListener('click', () => this._call('start'));
    this._el.pause.addEventListener('click', () => this._call('pause'));
    this._el.home.addEventListener('click', () => this._call('return_to_base'));
    this._el.chev.addEventListener('click', () => {
      this._open = !this._open;
      this._el.fold.classList.toggle('open', this._open);
      this._el.chev.classList.toggle('open', this._open);
    });
    const more = () => {
      const ev = new Event('hass-more-info', {bubbles:true, composed:true});
      ev.detail = {entityId:this._cfg.entity};
      this.dispatchEvent(ev);
    };
    this._el.art.addEventListener('click', more);
    r.querySelector('.txt').addEventListener('click', more);

    this._el.fold.classList.toggle('open', this._open);
    this._el.chev.classList.toggle('open', this._open);
    this._built = true;
  }

  _call(service){
    if(!this._hass) return;
    /* Le robot met une vingtaine de secondes à publier son nouvel état. On
       affiche donc l'état attendu sans attendre, quitte à le corriger si
       l'appareil dit autre chose. */
    const expect = {start:'cleaning', pause:'paused',
                    return_to_base:'returning'}[service];
    if(expect){
      this._pending = expect;
      this._pendUntil = Date.now() + 30000;
      this._paint();
    }
    this._hass.callService('vacuum', service, {}, {entity_id:this._cfg.entity});
  }

  /* Une image de la médiathèque n'a pas d'adresse fixe : Home Assistant la
     sert sous une signature qui expire. On la lui redemande donc, et on la
     garde quelques heures plutôt que d'interroger à chaque rafraîchissement. */
  async _applyPhoto(id){
    if(!id || !this._el.img) return;
    this._curId = id;

    if(!id.startsWith('media-source://')){
      if(this._el.img.getAttribute('src') !== id)
        this._el.img.setAttribute('src', id);
      return;
    }

    const hit = this._srcCache[id];
    if(hit && Date.now() < hit.until){
      if(this._el.img.getAttribute('src') !== hit.url)
        this._el.img.setAttribute('src', hit.url);
      return;
    }

    try{
      const r = await this._hass.callWS({
        type:'media_source/resolve_media', media_content_id:id, expires:86400
      });
      this._srcCache[id] = {url:r.url, until:Date.now() + 6 * 3600 * 1000};
      /* L'état a pu changer pendant l'attente : on n'écrase pas l'image
         courante si ce n'est plus celle qu'on veut afficher. */
      if(this._curId === id) this._el.img.setAttribute('src', r.url);
    }catch(err){
      console.error('ezviz-vacuum-card : image introuvable', id, err);
    }
  }

  set hass(h){
    this._hass = h;
    if(this._pending){
      const st = h.states[this._cfg.entity];
      if((st && st.state === this._pending) || Date.now() > this._pendUntil)
        this._pending = null;
    }
    if(this._built) this._paint();
  }

  _paint(){
    const c = this._cfg, e = this._el;
    const st = this._hass.states[c.entity];
    const state = this._pending || (st ? st.state : 'unavailable');
    const info = EVC_STATES[state] ||
      {t:state, col:'rgba(150,150,150,.85)', busy:false};

    e.card.style.setProperty('--vc', info.col);
    e.nm.textContent = c.name || (st ? st.attributes.friendly_name : 'Aspirateur');
    /* La photo sur base quand il y est, l'autre sinon. */
    if(this._photo && e.img){
      const want = (state === 'docked' && c.image_docked)
        ? c.image_docked
        : (c.image || c.image_docked);
      /* Cadrage rond réservé à la vue de dessus : celle sur la base est plus
         large que haute, un cercle lui couperait la station. */
      e.art.classList.toggle('round',
        c.image_round !== false && !!c.image && want === c.image);
      if(want !== this._curId) this._applyPhoto(want);
    }

    e.card.classList.toggle('busy', info.busy);
    e.art.classList.toggle('busy', info.busy);
    e.stt.classList.toggle('busy', info.busy);

    /* Une panne remplace l'état : c'est l'information qui prime. */
    let fault = '';
    if(c.fault){
      const fs = this._hass.states[c.fault];
      if(fs && fs.state && !['ok','unknown','unavailable',''].includes(
          String(fs.state).toLowerCase()))
        fault = EVC_FAULTS[fs.state] || fs.state;
    }
    e.lbl.textContent = fault || info.t;
    e.stt.classList.toggle('err', !!fault);

    /* ---- batterie ---- */
    let pct = NaN;
    if(c.battery){
      const bs = this._hass.states[c.battery];
      pct = bs ? evcNum(bs.state) : NaN;
    }
    if(isNaN(pct) && st) pct = evcNum(st.attributes.battery_level);
    const charging = !!(st && st.attributes.in_charging) && pct < 100;
    const bcol = isNaN(pct) ? 'rgba(150,150,150,.7)'
      : pct <= 20 ? EVC_LOW : pct <= 50 ? EVC_WARN : EVC_OK;
    const lvl = isNaN(pct) ? null : Math.round(pct / 10) * 10;
    e.batIcon.setAttribute('icon', isNaN(pct) ? 'mdi:battery-unknown'
      : charging ? 'mdi:battery-charging'
      : lvl >= 100 ? 'mdi:battery'
      : lvl <= 0 ? 'mdi:battery-outline'
      : 'mdi:battery-' + lvl);
    e.bat.style.setProperty('--bc', bcol);
    e.pct.innerHTML = (isNaN(pct) ? '—' : Math.round(pct)) + '<small>%</small>';

    /* ---- entretien ----
       Le capteur donne les heures restantes, son attribut les heures faites :
       leur somme est la durée de vie totale, d'où l'usure. */
    const wearMode = c.consumable_mode !== 'remaining';
    const alertAt = evcNum(c.alert_wear);
    const seuil = isNaN(alertAt) ? 85 : alertAt;
    const worn = [];
    let rows = '';
    for(const cons of this._cons){
      const cs = this._hass.states[cons.entity];
      const label = cons.name ||
        (cs ? String(cs.attributes.friendly_name || cons.entity)
                .replace(/^RE5 Plus\s+/i, '') : cons.entity);
      let val = '—', pctBar = 0, col = 'rgba(150,150,150,.7)';
      if(cs && !['unavailable','unknown'].includes(cs.state)){
        const remain = evcNum(cs.state);
        const used = evcNum(cs.attributes.hours_used);
        const total = (!isNaN(remain) && !isNaN(used)) ? remain + used : NaN;
        if(!isNaN(total) && total > 0){
          const wear = Math.round((used / total) * 100);
          const shown = wearMode ? wear : 100 - wear;
          col = evcWearColor(wear);
          if(wear >= seuil) worn.push(label);
          pctBar = shown;
          val = shown + '<small>%</small>' +
            (c.show_hours ? ' <small>· ' + Math.round(remain) + ' h</small>' : '');
        }else if(!isNaN(remain)){
          val = Math.round(remain) + '<small> h</small>';
        }
      }
      rows += '<div class="c" style="--wc:' + col + '">' +
        '<div class="l"><span class="k">' + label + '</span>' +
        '<span class="v">' + val + '</span></div>' +
        '<div class="bar"><i style="width:' + pctBar + '%;background:' +
        col + '"></i></div></div>';
    }
    e.cons.innerHTML = rows;
    e.chev.style.display = rows ? '' : 'none';

    /* Un consommable en fin de vie n'a pas à attendre qu'on déplie la carte :
       un point rouge clignotant le signale, et son infobulle dit lequel. */
    e.badge.style.display = worn.length ? '' : 'none';
    e.badge.title = worn.length
      ? 'À remplacer : ' + worn.join(', ')
      : '';

    /* ---- commandes ---- */
    const dead = !st || state === 'unavailable';
    e.go.disabled    = dead || state === 'cleaning';
    e.pause.disabled = dead || (state !== 'cleaning' && state !== 'returning');
    e.home.disabled  = dead || state === 'docked' || state === 'returning';
    e.go.classList.toggle('on', state === 'cleaning');
    e.pause.classList.toggle('on', state === 'paused');
    e.home.classList.toggle('on', state === 'returning' || state === 'docked');
  }

  getCardSize(){ return 2; }
  static getStubConfig(){ return {entity:'vacuum.robot'}; }
}

if(!customElements.get('ezviz-vacuum-card'))
  customElements.define('ezviz-vacuum-card', EzvizVacuumCard);
/* Alias : les tableaux de bord qui utilisaient déjà ce nom continuent de
   fonctionner sans modification. */
if(!customElements.get('maison-vacuum-card'))
  customElements.define('maison-vacuum-card', class extends EzvizVacuumCard{});

window.customCards = window.customCards || [];
window.customCards.push({
  type:'ezviz-vacuum-card', name:'EZVIZ — Aspirateur',
  description:'Format compact : etat, batterie, commandes, entretien repliable',
  preview:true
});
