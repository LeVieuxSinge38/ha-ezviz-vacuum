/* Carte aspirateur EZVIZ — discrète.

   Une seule ligne, haute comme une tuile : le robot, son état, sa batterie,
   trois commandes. Rien d'autre n'a le droit d'occuper la place en
   permanence. L'entretien attend sous un chevron ; on le consulte une fois
   par mois.

   Le dessin s'efface derrière la photo dès qu'on en fournit une, et le robot
   s'anime quand il travaille — balayage du lidar, anneau qui se propage.
   C'est la seule chose qui bouge.

   Toutes les dimensions dérivent de --fs (font_scale) et --art (size). */

/* Couleur d'état. Discrètes, elles ne servent qu'au point et au balayage. */
const EVC_STATES = {
  cleaning:   {t:'En nettoyage',     col:'#34c759', busy:true},
  returning:  {t:'Retour à la base', col:'#0a84ff', busy:true},
  paused:     {t:'En pause',         col:'#ff9f0a', busy:false},
  docked:     {t:'À la base',        col:'#5ac8fa', busy:false},
  idle:       {t:"À l'arrêt",        col:'#8e8e93', busy:false},
  error:      {t:'Erreur',           col:'#ff453a', busy:false},
  unavailable:{t:'Indisponible',     col:'#8e8e93', busy:false}
};

const EVC_OK   = '#34c759';
const EVC_WARN = '#ff9f0a';
const EVC_LOW  = '#ff453a';

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

/* Photos livrées avec la carte : l'utilisateur n'a rien à configurer.
   Elles se résolvent par rapport à l'adresse du script — ce qui suppose une
   vraie adresse. Une ressource « inline » est une data: URI, sans base : on
   renonce alors aux valeurs par défaut plutôt que de fabriquer une adresse
   cassée, et le dessin prend le relais. */
const EVC_BASE = (() => {
  const src = document.currentScript && document.currentScript.src;
  if(!src || src.startsWith('data:')) return null;
  return src.replace(/[^/]*$/, '');
})();
const EVC_IMG_DOCKED = EVC_BASE ? EVC_BASE + 'images/re5-base.png' : null;
const EVC_IMG_TOP    = EVC_BASE ? EVC_BASE + 'images/re5-dessus.png' : null;

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
  if(isNaN(w)) return '#8e8e93';
  if(w >= 85) return EVC_LOW;
  if(w >= 65) return EVC_WARN;
  return EVC_OK;
}

/* Robot vu de dessus, à défaut de photo. Coque claire, tourelle lidar,
   pare-chocs sombre, brosse latérale. L'anneau porte la couleur d'état. */
const EVC_ART = `
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <radialGradient id="evcTop" cx="0.36" cy="0.3" r="0.78">
      <stop offset="0"    stop-color="#ffffff"/>
      <stop offset="0.55" stop-color="#e9edf2"/>
      <stop offset="1"    stop-color="#b9c1cc"/>
    </radialGradient>
  </defs>
  <circle class="halo" cx="50" cy="50" r="47" fill="none"
          stroke="var(--vc)" stroke-width="1.6" opacity=".3"/>
  <circle cx="50" cy="50" r="41" fill="url(#evcTop)"/>
  <path d="M18,58 A41,41 0 0,0 82,58 L82,63 A41,41 0 0,1 18,63 Z"
        fill="#232a33" opacity=".92"/>
  <path class="sweep" d="M50,50 L50,9 A41,41 0 0,1 79,21 Z"
        fill="var(--vc)" opacity="0"/>
  <circle cx="50" cy="38" r="12.5" fill="#39414c"/>
  <circle cx="50" cy="38" r="8.5"  fill="#151b22"/>
  <circle class="lidar" cx="50" cy="38" r="3.6" fill="var(--vc)"/>
  <circle cx="30" cy="60" r="4" fill="#e3e8ee"/>
  <g class="brush" transform="translate(70,66)">
    <circle r="4" fill="#39414c"/>
    <g stroke="#f8fafc" stroke-opacity=".9" stroke-width="1.8"
       stroke-linecap="round">
      <path d="M0,0 L11,-4"/><path d="M0,0 L-5,10"/><path d="M0,0 L-7,-8"/>
    </g>
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
      image:undefined, image_docked:undefined, image_round:true,
      consumables:[], consumable_mode:'wear', show_hours:true, alert_wear:85,
      font_scale:1, size:56
    }, cfg);

    /* Sans consigne, on prend les photos livrées avec la carte. `null`
       explicite reste un refus : on retombe alors sur le dessin. */
    if(this._cfg.image === undefined) this._cfg.image = EVC_IMG_TOP;
    if(this._cfg.image_docked === undefined)
      this._cfg.image_docked = EVC_IMG_DOCKED;

    this._cons = (cfg.consumables || []).map(c =>
      typeof c === 'string' ? {entity:c, name:null}
                            : {entity:c.entity, name:c.name || null});
    this._open = !!cfg.expanded;

    this._photo = !!(this._cfg.image || this._cfg.image_docked);
    const art = this._photo ? '<img alt="">' : EVC_ART;

    this.shadowRoot.innerHTML = `
    <style>
    :host{display:block}

    /* Coins largement arrondis, une bordure à peine visible, une ombre
       douce : la carte se pose sur le fond au lieu de s'y découper. */
    ha-card{
      display:block;position:relative;overflow:hidden;
      container-type:inline-size;
      padding:calc(9px * var(--fs)) calc(13px * var(--fs));
      border-radius:var(--ha-card-border-radius, 22px);
      border:1px solid color-mix(in srgb, var(--primary-text-color) 9%, transparent);
      background:var(--ha-card-background, var(--card-background-color, #fff));
      box-shadow:0 1px 2px rgba(0,0,0,.05), 0 6px 18px rgba(0,0,0,.04);
    }

    .main{display:flex;align-items:center;gap:calc(11px * var(--fs))}

    /* ---- le robot ---- */
    .art{
      flex:none;position:relative;cursor:pointer;
      width:var(--art);height:var(--art);
    }
    .art svg, .art img{display:block;width:100%;height:100%}
    .art img{object-fit:contain}
    /* Vu de dessus, le robot est rond : un cadrage circulaire efface les
       coins blancs de la photo produit, et le balayage épouse alors
       exactement le bord de la coque. */
    .art.round img{object-fit:cover;border-radius:50%}

    /* Balayage du lidar et anneau qui se propage : les deux seules
       animations de la carte, réservées au travail en cours. */
    .scan{
      position:absolute;inset:0;border-radius:50%;pointer-events:none;
      opacity:0;transition:opacity .5s;
      background:conic-gradient(from 0deg,
        color-mix(in srgb, var(--vc) 55%, transparent) 0deg,
        transparent 55deg, transparent 360deg);
      -webkit-mask:radial-gradient(circle, #000 62%, transparent 63%);
      mask:radial-gradient(circle, #000 62%, transparent 63%);
    }
    .busy .scan{opacity:.9;animation:evc-scan 1.8s linear infinite}
    @keyframes evc-scan{to{transform:rotate(360deg)}}
    .pulse{
      position:absolute;inset:0;border-radius:50%;pointer-events:none;
      border:1.5px solid var(--vc);opacity:0;
    }
    .busy .pulse{animation:evc-ring 1.8s ease-out infinite}
    @keyframes evc-ring{
      0%{opacity:.5;transform:scale(.85)}
      100%{opacity:0;transform:scale(1.14)}
    }
    .brush{transform-origin:70px 66px}
    .busy .brush{animation:evc-spin .9s linear infinite}
    @keyframes evc-spin{to{transform:translate(70px,66px) rotate(360deg)}}
    .busy .lidar{animation:evc-pulse 1.4s ease-in-out infinite}
    @keyframes evc-pulse{50%{opacity:.2}}
    .busy .sweep{animation:evc-sweep 2.4s linear infinite;
      transform-origin:50px 50px}
    @keyframes evc-sweep{
      0%{opacity:.22;transform:rotate(0deg)}
      100%{opacity:.22;transform:rotate(360deg)}
    }
    .busy .halo{animation:evc-halo 2s ease-in-out infinite}
    @keyframes evc-halo{50%{opacity:.8}}

    /* ---- nom, état, batterie ---- */
    .txt{
      flex:1 1 0;min-width:0;cursor:pointer;
      display:flex;flex-direction:column;gap:2px;
    }
    .nm{
      font-size:calc(.66rem * var(--fs));font-weight:600;letter-spacing:.08em;
      text-transform:uppercase;color:var(--secondary-text-color);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .st{
      display:flex;align-items:center;gap:calc(6px * var(--fs));
      font-size:calc(.94rem * var(--fs));font-weight:600;
      color:var(--primary-text-color);white-space:nowrap;overflow:hidden;
    }
    /* À l'étroit, c'est le libellé d'état qui cède — jamais la batterie,
       qui est un chiffre : tronquée, elle mentirait. */
    .lbl{flex:0 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis}
    .dot{
      flex:none;width:calc(7px * var(--fs));height:calc(7px * var(--fs));
      border-radius:50%;background:var(--vc);
    }
    .busy .dot{animation:evc-dot 1.3s ease-in-out infinite}
    @keyframes evc-dot{50%{opacity:.25;transform:scale(.7)}}
    .st.err{color:var(--vc)}
    /* La batterie suit l'état sur la même ligne : deux informations, une
       seule hauteur. */
    .bat{
      flex:none;font-weight:500;color:var(--secondary-text-color);
      font-variant-numeric:tabular-nums;
    }
    .bat.low{color:#ff453a}
    /* L'éclair de charge en icône, pas en emoji : un emoji garde ses propres
       couleurs et jure avec le thème. */
    .chg{
      flex:none;display:none;color:var(--secondary-text-color);
      --mdc-icon-size:calc(14px * var(--fs));
    }
    .chg.on{display:inline-flex}

    /* ---- commandes ----
       Trois pastilles rondes, contour discret, remplies seulement quand la
       commande est celle en cours. */
    .cmd{flex:none;display:flex;gap:calc(6px * var(--fs))}
    .ico{
      width:calc(34px * var(--fs));height:calc(34px * var(--fs));
      flex:none;border:0;padding:0;border-radius:50%;cursor:pointer;
      display:flex;align-items:center;justify-content:center;
      background:color-mix(in srgb, var(--primary-text-color) 6%, transparent);
      color:var(--primary-text-color);
      transition:background .18s, transform .12s, opacity .18s;
      -webkit-tap-highlight-color:transparent;
    }
    .ico ha-icon{--mdc-icon-size:calc(18px * var(--fs));opacity:.75}
    .ico:hover:not(:disabled){
      background:color-mix(in srgb, var(--primary-text-color) 12%, transparent)}
    .ico:active:not(:disabled){transform:scale(.92)}
    .ico:disabled{opacity:.3;cursor:default}
    .ico.on{background:color-mix(in srgb, var(--vc) 20%, transparent)}
    .ico.on ha-icon{opacity:1;color:var(--vc)}

    /* Le chevron n'est pas une commande : plus petit, sans fond. */
    .chev{
      width:calc(22px * var(--fs));height:calc(34px * var(--fs));
      background:transparent;
    }
    .chev ha-icon{--mdc-icon-size:calc(20px * var(--fs));opacity:.45;
      transition:transform .3s ease}
    .chev:hover{background:transparent}
    .chev.open ha-icon{transform:rotate(180deg)}
    /* Une pièce en fin de vie : un point rouge sur le chevron, sans
       clignotement — il attend qu'on ouvre, il n'a pas à s'agiter. */
    .chev.warn::after{
      content:'';position:absolute;margin:-14px 0 0 13px;
      width:6px;height:6px;border-radius:50%;background:#ff453a;
    }

    /* ---- entretien, replié ---- */
    .fold{display:grid;grid-template-rows:0fr;
      transition:grid-template-rows .3s ease}
    .fold.open{grid-template-rows:1fr}
    .foldin{overflow:hidden;min-height:0}
    .cons{
      display:grid;grid-template-columns:1fr 1fr;
      gap:calc(8px * var(--fs)) calc(16px * var(--fs));
      margin-top:calc(9px * var(--fs));padding-top:calc(9px * var(--fs));
      border-top:1px solid
        color-mix(in srgb, var(--primary-text-color) 8%, transparent);
    }
    .c .l{display:flex;align-items:baseline;gap:6px;margin-bottom:3px}
    .c .k{
      flex:1 1 auto;min-width:0;font-size:calc(.74rem * var(--fs));
      color:var(--secondary-text-color);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .c .v{flex:none;font-size:calc(.76rem * var(--fs));font-weight:600;
      color:var(--wc);font-variant-numeric:tabular-nums}
    .c .v small{font-weight:500;opacity:.65}
    .bar{height:3px;border-radius:999px;overflow:hidden;
      background:color-mix(in srgb, var(--primary-text-color) 9%, transparent)}
    .bar i{display:block;height:100%;border-radius:999px;
      transition:width .6s ease}

    /* Carte étroite : le nom s'efface avant tout le reste, l'état suffit. */
    @container (max-width: 340px){
      .cons{grid-template-columns:1fr}
      .nm{display:none}
      .main{gap:calc(8px * var(--fs))}
      /* Le robot cède quelques pixels avant que l'état ne soit tronqué. */
      .art{width:calc(var(--art) * .82);height:calc(var(--art) * .82)}
    }
    </style>
    <ha-card>
      <div class="main">
        <div class="art">` + art +
          `<div class="scan"></div><div class="pulse"></div></div>
        <div class="txt">
          <div class="nm"></div>
          <div class="st">
            <span class="dot"></span><span class="lbl"></span>
            <span class="bat"></span>
            <ha-icon class="chg" icon="mdi:lightning-bolt"></ha-icon>
          </div>
        </div>
        <div class="cmd">
          <button class="ico go" title="Démarrer">
            <ha-icon icon="mdi:play"></ha-icon></button>
          <button class="ico pause" title="Pause">
            <ha-icon icon="mdi:pause"></ha-icon></button>
          <button class="ico home" title="Retour à la base">
            <ha-icon icon="mdi:home-import-outline"></ha-icon></button>
        </div>
        <button class="ico chev" title="Entretien">
          <ha-icon icon="mdi:chevron-down"></ha-icon></button>
      </div>
      <div class="fold"><div class="foldin"><div class="cons"></div></div></div>
    </ha-card>`;

    const r = this.shadowRoot;
    this._el = {
      card:r.querySelector('ha-card'), main:r.querySelector('.main'),
      art:r.querySelector('.art'), img:r.querySelector('.art img'),
      nm:r.querySelector('.nm'), st:r.querySelector('.st'),
      lbl:r.querySelector('.lbl'), bat:r.querySelector('.bat'),
      chg:r.querySelector('.chg'),
      go:r.querySelector('.go'), pause:r.querySelector('.pause'),
      home:r.querySelector('.home'), chev:r.querySelector('.chev'),
      fold:r.querySelector('.fold'), cons:r.querySelector('.cons')
    };
    this._el.card.style.setProperty('--fs', String(this._cfg.font_scale));
    this._el.card.style.setProperty('--art',
      Math.round(this._cfg.size * this._cfg.font_scale) + 'px');

    /* Une photo introuvable ne doit pas laisser un cadre vide : on repasse
       au dessin, qui ne dépend de rien. Le cas se présente si les images
       livrées n'ont pas suivi, ou si une adresse configurée est fausse. */
    if(this._el.img)
      this._el.img.addEventListener('error', () => {
        this._photo = false;
        this._curId = null;
        this._el.img.remove();
        this._el.img = null;
        this._el.art.classList.remove('round');
        this._el.art.insertAdjacentHTML('afterbegin', EVC_ART);
      });

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
    this._el.st.addEventListener('click', more);

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
    const info = EVC_STATES[state] || {t:state, col:'#8e8e93', busy:false};

    e.card.style.setProperty('--vc', info.col);
    e.nm.textContent = c.name || (st ? st.attributes.friendly_name : 'Aspirateur');

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

    e.main.classList.toggle('busy', info.busy);

    /* Une panne remplace l'état : c'est l'information qui prime. */
    let fault = '';
    if(c.fault){
      const fs = this._hass.states[c.fault];
      if(fs && fs.state && !['ok','unknown','unavailable',''].includes(
          String(fs.state).toLowerCase()))
        fault = EVC_FAULTS[fs.state] || fs.state;
    }
    if(fault) e.card.style.setProperty('--vc', EVC_LOW);
    e.lbl.textContent = fault || info.t;
    e.st.classList.toggle('err', !!fault);

    /* ---- batterie, sur la même ligne que l'état ---- */
    let pct = NaN;
    if(c.battery){
      const bs = this._hass.states[c.battery];
      pct = bs ? evcNum(bs.state) : NaN;
    }
    if(isNaN(pct) && st) pct = evcNum(st.attributes.battery_level);
    const charging = !!(st && st.attributes.in_charging) && pct < 100;
    e.bat.textContent = isNaN(pct) ? '' : '· ' + Math.round(pct) + ' %';
    e.bat.classList.toggle('low', !isNaN(pct) && pct <= 20);
    e.chg.classList.toggle('on', charging);

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
      let val = '—', pctBar = 0, col = '#8e8e93';
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
          val = shown + '<small> %</small>' +
            (c.show_hours ? '<small> · ' + Math.round(remain) + ' h</small>' : '');
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
    e.chev.classList.toggle('warn', worn.length > 0);
    e.chev.title = worn.length ? 'À remplacer : ' + worn.join(', ') : 'Entretien';

    /* ---- commandes ---- */
    const dead = !st || state === 'unavailable';
    e.go.disabled    = dead || state === 'cleaning';
    e.pause.disabled = dead || (state !== 'cleaning' && state !== 'returning');
    e.home.disabled  = dead || state === 'docked' || state === 'returning';
    e.go.classList.toggle('on', state === 'cleaning');
    e.pause.classList.toggle('on', state === 'paused');
    e.home.classList.toggle('on', state === 'returning' || state === 'docked');
  }

  getCardSize(){ return 1; }

  static getConfigElement(){
    return document.createElement('ezviz-vacuum-card-editor');
  }
  static getStubConfig(hass){
    const first = hass
      ? Object.keys(hass.states).find(id => id.startsWith('vacuum.'))
      : null;
    return {entity:first || 'vacuum.robot'};
  }
}

/* ---------------------------------------------------------------------
   Éditeur visuel, sur `ha-form` : on hérite des sélecteurs natifs de Home
   Assistant (choix d'entité, curseurs) sans les réécrire.
   --------------------------------------------------------------------- */
const EVC_SCHEMA = [
  {name:'entity', required:true, selector:{entity:{domain:'vacuum'}}},
  {name:'name', selector:{text:{}}},
  {name:'battery',
   selector:{entity:{domain:'sensor', device_class:'battery'}}},
  {name:'fault', selector:{entity:{domain:'sensor'}}},
  {name:'consumables',
   selector:{entity:{domain:'sensor', multiple:true}}},

  /* `name:''` est obligatoire : avec un nom, ha-form range les champs de la
     section dans un sous-objet portant ce nom, et la carte, qui les lit à la
     racine, ne voit plus rien changer. Le titre passe par `title`. */
  {name:'', type:'expandable', title:'Apparence', schema:[
    {name:'size',
     selector:{number:{min:40, max:96, step:2, mode:'slider'}}},
    {name:'font_scale',
     selector:{number:{min:.8, max:1.3, step:.02, mode:'slider'}}},
    {name:'image_round', selector:{boolean:{}}}
  ]},

  {name:'', type:'expandable', title:'Photos', schema:[
    {name:'image_docked', selector:{text:{}}},
    {name:'image', selector:{text:{}}}
  ]},

  {name:'', type:'expandable', title:'Entretien', schema:[
    {name:'consumable_mode', selector:{select:{mode:'dropdown', options:[
      {value:'wear', label:'Usure (100 % = à remplacer)'},
      {value:'remaining', label:'Restant (0 % = à remplacer)'}
    ]}}},
    {name:'alert_wear',
     selector:{number:{min:50, max:100, step:1, mode:'slider'}}},
    {name:'show_hours', selector:{boolean:{}}},
    {name:'expanded', selector:{boolean:{}}}
  ]}
];

const EVC_LABELS = {
  entity:'Aspirateur', name:'Titre affiché',
  battery:'Capteur de batterie', fault:'Capteur de panne',
  consumables:'Consommables suivis',
  size:'Taille du robot (px)', font_scale:'Taille du texte',
  image_round:'Recadrer la vue de dessus en rond',
  image_docked:'Photo sur la base', image:'Photo en fonctionnement',
  consumable_mode:'Afficher',
  alert_wear:'Seuil du point d\'alerte (%)',
  show_hours:'Afficher les heures restantes',
  expanded:'Entretien déplié par défaut'
};

const EVC_HELPERS = {
  size:'C\'est elle qui fixe la hauteur de la carte.',
  image_docked:'Laisser vide pour la photo livrée avec la carte.',
  image:'Affichée dès que le robot quitte sa base. Vide = photo livrée.',
  alert_wear:'Au-delà, un point rouge apparaît sur le chevron.'
};

class EzvizVacuumCardEditor extends HTMLElement{
  setConfig(config){
    this._config = config || {};
    this._render();
  }
  set hass(h){
    this._hass = h;
    if(this._form) this._form.hass = h;
  }

  _render(){
    if(!this._form){
      const f = document.createElement('ha-form');
      f.computeLabel = sc => EVC_LABELS[sc.name] || sc.name;
      f.computeHelper = sc => EVC_HELPERS[sc.name] || '';
      f.addEventListener('value-changed', ev => {
        ev.stopPropagation();
        this.dispatchEvent(new CustomEvent('config-changed', {
          detail:{config:this._toConfig(ev.detail.value)},
          bubbles:true, composed:true
        }));
      });
      this.appendChild(f);
      this._form = f;
    }
    this._form.schema = EVC_SCHEMA;
    if(this._hass) this._form.hass = this._hass;
    this._form.data = this._toForm(this._config);
  }

  /* Le sélecteur de consommables ne rend que des identifiants ; la carte, elle,
     accepte aussi la forme {entity, name}. */
  _toForm(cfg){
    return Object.assign({}, cfg, {
      consumables:(cfg.consumables || []).map(
        c => typeof c === 'string' ? c : c.entity)
    });
  }

  _toConfig(data){
    const out = Object.assign({type:this._config.type}, data);
    for(const k of Object.keys(out))
      if(out[k] === undefined || out[k] === '') delete out[k];
    return out;
  }
}

if(!customElements.get('ezviz-vacuum-card-editor'))
  customElements.define('ezviz-vacuum-card-editor', EzvizVacuumCardEditor);

if(!customElements.get('ezviz-vacuum-card'))
  customElements.define('ezviz-vacuum-card', EzvizVacuumCard);
/* Alias : les tableaux de bord qui utilisaient déjà ce nom continuent de
   fonctionner sans modification. */
if(!customElements.get('maison-vacuum-card'))
  customElements.define('maison-vacuum-card', class extends EzvizVacuumCard{});

window.customCards = window.customCards || [];
window.customCards.push({
  type:'ezviz-vacuum-card', name:'EZVIZ — Aspirateur',
  description:'Carte compacte : etat, batterie, commandes, entretien repliable',
  preview:true
});
