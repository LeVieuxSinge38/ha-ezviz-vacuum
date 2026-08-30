/* Carte aspirateur EZVIZ RE5 Plus, format compact.
   Une seule ligne : le robot, son état, sa batterie et les trois commandes.
   L'entretien vit sous un chevron, replié par défaut — on le consulte une
   fois par mois, il n'a rien à faire en permanence sur un tableau de bord.
   Toutes les tailles dérivent de --fs, réglable par font_scale. */

const EVC_STATES = {
  cleaning:   {t:'En nettoyage',     col:'#34d399', busy:true},
  returning:  {t:'Retour à la base', col:'#38bdf8', busy:true},
  paused:     {t:'En pause',         col:'#fbbf24', busy:false},
  docked:     {t:'À la base',        col:'#2dd4bf', busy:false},
  idle:       {t:"À l'arrêt",        col:'rgba(150,150,150,.85)', busy:false},
  error:      {t:'Erreur',           col:'#f87171', busy:false},
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

function evcWearColor(w){
  if(isNaN(w)) return 'rgba(150,150,150,.7)';
  if(w >= 85) return '#f87171';
  if(w >= 65) return '#fbbf24';
  return '#34d399';
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
          stroke="var(--vc)" stroke-width="2.5" opacity=".35"/>
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
  }

  setConfig(cfg){
    if(!cfg.entity) throw new Error('Il faut renseigner "entity"');
    if(cfg.entity.split('.')[0] !== 'vacuum')
      throw new Error('Cette carte attend une entité du domaine vacuum');

    this._cfg = Object.assign({
      name:null, battery:null, fault:null, image:null,
      consumables:[], consumable_mode:'wear', show_hours:true,
      font_scale:1
    }, cfg);
    this._cons = (cfg.consumables || []).map(c =>
      typeof c === 'string' ? {entity:c, name:null}
                            : {entity:c.entity, name:c.name || null});
    this._open = !!cfg.expanded;

    const art = this._cfg.image
      ? '<img src="' + this._cfg.image + '" alt="">'
      : EVC_ART;

    this.shadowRoot.innerHTML = `
    <style>
    :host{display:block}
    ha-card{
      position:relative;overflow:hidden;container-type:inline-size;
      padding:12px 14px;
      background:
        radial-gradient(130% 110% at 50% -25%, rgba(255,255,255,.08), transparent 62%),
        var(--ha-card-background, var(--card-background-color, #1c1c1c));
      border-radius:var(--ha-card-border-radius, 16px);
    }
    ha-card::after{
      content:'';position:absolute;inset:0;border-radius:inherit;
      pointer-events:none;border:1px solid var(--vc);opacity:.18;
    }

    .row{display:flex;align-items:center;gap:12px}

    /* ---- le robot, petit et vivant ---- */
    .art{
      flex:none;width:calc(52px * var(--fs));height:calc(52px * var(--fs));
      cursor:pointer;position:relative;
      filter:drop-shadow(0 4px 9px rgba(0,0,0,.4));
    }
    .art svg,.art img{display:block;width:100%;height:100%;
      object-fit:cover;border-radius:50%}
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

    /* ---- nom et état ---- */
    .txt{flex:1 1 auto;min-width:0;display:flex;flex-direction:column;gap:2px;
      cursor:pointer}
    .nm{
      font-size:calc(.78rem * var(--fs));font-weight:800;letter-spacing:.13em;
      text-transform:uppercase;color:var(--secondary-text-color);opacity:.72;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .stt{
      display:flex;align-items:center;gap:7px;
      font-size:calc(1.02rem * var(--fs));font-weight:700;color:var(--vc);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
      transition:color .4s ease;
    }
    .dot{width:7px;height:7px;border-radius:50%;background:var(--vc);flex:none}
    .busy .dot{animation:evc-dot 1.3s ease-in-out infinite}
    @keyframes evc-dot{50%{opacity:.25;transform:scale(.7)}}
    .stt.err{color:#f87171}

    /* ---- batterie ---- */
    .bat{
      flex:none;display:flex;align-items:center;gap:5px;
      font-size:calc(1.02rem * var(--fs));font-weight:700;
      color:var(--bc);font-variant-numeric:tabular-nums;
    }
    .bat ha-icon{--mdc-icon-size:calc(19px * var(--fs))}
    .bat small{font-size:calc(.78rem * var(--fs));opacity:.75;margin-left:-2px}

    /* ---- commandes ---- */
    .cmd{flex:none;display:flex;gap:6px}
    .b{
      width:calc(38px * var(--fs));height:calc(38px * var(--fs));
      border:0;border-radius:11px;cursor:pointer;padding:0;
      display:flex;align-items:center;justify-content:center;
      background:color-mix(in srgb, var(--primary-text-color) 8%, transparent);
      transition:background .18s, box-shadow .18s;
      -webkit-tap-highlight-color:transparent;
    }
    .b:hover:not(:disabled){
      background:color-mix(in srgb, var(--primary-text-color) 15%, transparent)}
    .b:disabled{opacity:.28;cursor:not-allowed}
    .b ha-icon{--mdc-icon-size:calc(21px * var(--fs));
      color:var(--secondary-text-color);transition:color .18s}
    .b.on{
      background:color-mix(in srgb, var(--bcol) 22%, transparent);
      box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--bcol) 50%, transparent);
    }
    .b.on ha-icon{color:var(--bcol)}
    .chev{background:transparent;width:calc(28px * var(--fs))}
    .chev ha-icon{transition:transform .3s ease}
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
      margin-top:12px;padding-top:11px;
      border-top:1px solid var(--divider-color, rgba(127,127,127,.2));
    }
    .c .l{display:flex;align-items:baseline;gap:6px;margin-bottom:4px}
    .c .k{
      flex:1 1 auto;min-width:0;font-size:calc(.84rem * var(--fs));
      font-weight:600;color:var(--secondary-text-color);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .c .v{flex:none;font-size:calc(.88rem * var(--fs));font-weight:700;
      color:var(--wc);font-variant-numeric:tabular-nums}
    .c .v small{font-size:calc(.74rem * var(--fs));opacity:.7}
    .bar{height:5px;border-radius:999px;overflow:hidden;
      background:color-mix(in srgb, var(--primary-text-color) 10%, transparent)}
    .bar i{display:block;height:100%;border-radius:999px;
      transition:width .6s ease}

    @container (max-width: 430px){
      .cons{grid-template-columns:1fr}
      .nm{display:none}
    }
    @container (max-width: 330px){
      .bat{display:none}
    }
    </style>
    <ha-card>
      <div class="row">
        <div class="art">` + art + `</div>
        <div class="txt">
          <div class="nm"></div>
          <div class="stt"><span class="dot"></span><span class="lbl"></span></div>
        </div>
        <div class="bat"><ha-icon></ha-icon><span class="pct"></span></div>
        <div class="cmd">
          <button class="b go"    style="--bcol:#34d399" title="Démarrer">
            <ha-icon icon="mdi:play"></ha-icon></button>
          <button class="b pause" style="--bcol:#fbbf24" title="Pause">
            <ha-icon icon="mdi:pause"></ha-icon></button>
          <button class="b home"  style="--bcol:#38bdf8" title="Retour à la base">
            <ha-icon icon="mdi:home-import-outline"></ha-icon></button>
          <button class="b chev" title="Entretien">
            <ha-icon icon="mdi:chevron-down"></ha-icon></button>
        </div>
      </div>
      <div class="fold"><div class="foldin"><div class="cons"></div></div></div>
    </ha-card>`;

    const r = this.shadowRoot;
    this._el = {
      card:r.querySelector('ha-card'), art:r.querySelector('.art'),
      nm:r.querySelector('.nm'), stt:r.querySelector('.stt'),
      lbl:r.querySelector('.lbl'), bat:r.querySelector('.bat'),
      batIcon:r.querySelector('.bat ha-icon'), pct:r.querySelector('.pct'),
      go:r.querySelector('.go'), pause:r.querySelector('.pause'),
      home:r.querySelector('.home'), chev:r.querySelector('.chev'),
      fold:r.querySelector('.fold'), cons:r.querySelector('.cons')
    };
    this._el.card.style.setProperty('--fs', String(this._cfg.font_scale));

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
    this._hass.callService('vacuum', service, {}, {entity_id:this._cfg.entity});
  }

  set hass(h){ this._hass = h; if(this._built) this._paint(); }

  _paint(){
    const c = this._cfg, e = this._el;
    const st = this._hass.states[c.entity];
    const state = st ? st.state : 'unavailable';
    const info = EVC_STATES[state] ||
      {t:state, col:'rgba(150,150,150,.85)', busy:false};

    e.card.style.setProperty('--vc', info.col);
    e.nm.textContent = c.name || (st ? st.attributes.friendly_name : 'Aspirateur');
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
      : pct <= 20 ? '#f87171' : pct <= 50 ? '#fbbf24' : '#34d399';
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
