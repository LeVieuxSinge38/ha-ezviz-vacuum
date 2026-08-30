/* Carte aspirateur EZVIZ RE5 Plus.
   Le robot et sa base d'auto-vidage sont dessinés, pas photographiés : le
   dessin se recolore avec l'état et reste net à toute taille. Une vraie photo
   peut le remplacer via `image`.
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

/* Pannes remontées par le robot, traduites depuis l'énumération du firmware.
   Seules les plus probables sont nommées ; les autres s'affichent brutes. */
const EVC_FAULTS = {
  CR_RollBrushTwine:'Brosse rotative enroulée',
  CR_EdgeBrushTrapped:'Brosse latérale coincée',
  CR_WheelTrapped:'Roue bloquée',
  CR_WheelSuspended:'Roue dans le vide',
  CR_Trapped:'Robot coincé',
  CR_FailToReturnDock:'Retour à la base impossible',
  CR_LocationFailure:'Perte de repérage',
  CR_DustBoxOrBagUnset:'Bac à poussière absent',
  CR_DustBoxUncover:'Bac à poussière ouvert',
  CR_CleanWaterBoxEmpty:'Réservoir d’eau vide',
  CR_CleanWaterBoxLow:'Réservoir d’eau bas',
  CR_CleanWaterBoxUnsetup:'Réservoir d’eau absent',
  CR_DirtyWaterBoxFull:'Bac à eau sale plein',
  CR_DirtyWaterBoxUnsetup:'Bac à eau sale absent',
  CR_AllWaterBoxUnsetup:'Réservoirs absents',
  CR_MopInstallErr:'Serpillère mal installée',
  CR_MopTryDrop:'Serpillère détachée',
  CR_RollBrushUnsetup:'Brosse rotative absente',
  CR_LidarCoverErr:'Capot du lidar obstrué',
  CR_LidarShieldErr:'Lidar masqué',
  CR_DockCommErr:'Base injoignable',
  CR_DockDryFanStall:'Ventilateur de séchage bloqué',
  CR_DockPumpSewageFail:'Vidange de la base impossible'
};

function evcNum(v){
  if(v === null || v === undefined) return NaN;
  const t = String(v).trim();
  if(t === '') return NaN;
  const n = Number(t);
  return Number.isFinite(n) ? n : NaN;
}

/* Vert tant qu'il reste de la marge, rouge quand le remplacement approche. */
function evcWearColor(w){
  if(isNaN(w)) return 'rgba(150,150,150,.7)';
  if(w >= 85) return '#f87171';
  if(w >= 65) return '#fbbf24';
  return '#34d399';
}

/* RE5 Plus vu de trois quarts, posé devant sa base d'auto-vidage.
   Corps blanc, bandeau pare-chocs sombre, tourelle lidar décentrée vers
   l'arrière, brosse latérale à trois bras. */
const EVC_ART = `
<svg viewBox="0 0 300 190" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="evcShell" x1="0.2" y1="0" x2="0.6" y2="1">
      <stop offset="0"    stop-color="#ffffff"/>
      <stop offset="0.42" stop-color="#eef1f5"/>
      <stop offset="1"    stop-color="#c3cad4"/>
    </linearGradient>
    <linearGradient id="evcRim" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#8c96a3"/>
      <stop offset="1" stop-color="#39414c"/>
    </linearGradient>
    <linearGradient id="evcDock" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0"   stop-color="#f4f6f9"/>
      <stop offset="0.55" stop-color="#dfe4ea"/>
      <stop offset="1"   stop-color="#aeb6c1"/>
    </linearGradient>
    <linearGradient id="evcTurret" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#5b6572"/>
      <stop offset="1" stop-color="#232a33"/>
    </linearGradient>
    <radialGradient id="evcShade" cx="0.5" cy="0.5" r="0.5">
      <stop offset="0" stop-color="#000" stop-opacity=".45"/>
      <stop offset="1" stop-color="#000" stop-opacity="0"/>
    </radialGradient>
  </defs>

  <!-- base d'auto-vidage -->
  <g class="dock">
    <ellipse cx="243" cy="150" rx="46" ry="11" fill="url(#evcShade)"/>
    <path d="M215,150 L215,58 Q215,44 229,44 L257,44 Q271,44 271,58 L271,150 Z"
          fill="url(#evcDock)"/>
    <path d="M221,150 L221,64 Q221,54 231,54 L255,54 Q265,54 265,64 L265,150 Z"
          fill="#0f141b" opacity=".13"/>
    <rect x="226" y="70" width="34" height="42" rx="7" fill="#1a212a" opacity=".82"/>
    <rect x="230" y="76" width="26" height="4" rx="2" fill="#8c96a3" opacity=".5"/>
    <circle class="dled" cx="243" cy="126" r="3.6" fill="var(--vc)"/>
    <path d="M209,150 L277,150 L281,158 L205,158 Z" fill="#c3cad4"/>
  </g>

  <!-- ombre portée du robot -->
  <ellipse class="shade" cx="124" cy="152" rx="96" ry="16" fill="url(#evcShade)"/>

  <!-- flanc puis plateau -->
  <path d="M28,112 A96,50 0 0,0 220,112 L220,128 A96,50 0 0,1 28,128 Z"
        fill="url(#evcRim)"/>
  <ellipse cx="124" cy="112" rx="96" ry="50" fill="url(#evcShell)"/>
  <ellipse cx="124" cy="112" rx="96" ry="50" fill="none"
           stroke="#ffffff" stroke-opacity=".65" stroke-width="1.4"/>
  <ellipse cx="124" cy="110" rx="80" ry="41" fill="none"
           stroke="#9aa4b1" stroke-opacity=".28" stroke-width="1"/>

  <!-- pare-chocs avant, sombre -->
  <path d="M44,126 A96,50 0 0,0 204,126 L204,133 A96,50 0 0,1 44,133 Z"
        fill="#222932"/>
  <path class="ring" d="M46,124 A96,50 0 0,0 202,124"
        fill="none" stroke="var(--vc)" stroke-width="4"
        stroke-linecap="round"/>

  <!-- tourelle lidar -->
  <ellipse cx="146" cy="94" rx="24" ry="12" fill="#161c24" opacity=".45"/>
  <path d="M122,80 L122,92 A24,12 0 0,0 170,92 L170,80 Z" fill="url(#evcTurret)"/>
  <ellipse cx="146" cy="80" rx="24" ry="12" fill="#3b444f"/>
  <ellipse cx="146" cy="79" rx="17" ry="8" fill="#141a21"/>
  <ellipse class="lidar" cx="146" cy="79" rx="7" ry="3.4" fill="var(--vc)"/>

  <!-- capteurs et bouton -->
  <circle cx="86" cy="96" r="7" fill="#e3e8ee" stroke="#9aa4b1"
          stroke-opacity=".5" stroke-width="1"/>
  <circle cx="86" cy="96" r="3" fill="#8c96a3" opacity=".55"/>
  <ellipse cx="70" cy="115" rx="5.5" ry="3" fill="#222932" opacity=".55"/>

  <!-- brosse latérale -->
  <g class="brush" transform="translate(56,138)">
    <circle r="6" fill="#39414c"/>
    <g stroke="#f8fafc" stroke-opacity=".9" stroke-width="2.3" stroke-linecap="round">
      <path d="M0,0 L17,-6"/><path d="M0,0 L-8,15"/><path d="M0,0 L-11,-12"/>
    </g>
    <circle r="2.4" fill="#cbd5e1"/>
  </g>

  <!-- poussière aspirée, visible en nettoyage -->
  <g class="dust" fill="var(--vc)">
    <circle cx="18"  cy="136" r="2.6"/>
    <circle cx="6"   cy="124" r="1.9"/>
    <circle cx="26"  cy="118" r="1.5"/>
  </g>
</svg>`;

class EzvizVacuumCard extends HTMLElement{
  constructor(){
    super();
    this.attachShadow({mode:'open'});
    this._built = false;
  }

  setConfig(cfg){
    if(!cfg.entity) throw new Error('Il faut renseigner "entity"');
    if(cfg.entity.split('.')[0] !== 'vacuum')
      throw new Error('Cette carte attend une entité du domaine vacuum');

    this._cfg = Object.assign({
      name:null, battery:null, fault:null, fan:null, image:null,
      consumables:[], consumable_mode:'wear', show_hours:true,
      art_opacity:1, font_scale:1
    }, cfg);
    this._cons = (cfg.consumables || []).map(c =>
      typeof c === 'string' ? {entity:c, name:null}
                            : {entity:c.entity, name:c.name || null});

    const art = this._cfg.image
      ? '<img src="' + this._cfg.image + '" alt="">'
      : EVC_ART;

    this.shadowRoot.innerHTML = `
    <style>
    :host{display:block}
    ha-card{
      position:relative;overflow:hidden;container-type:inline-size;
      padding:16px 18px 15px;
      background:
        radial-gradient(130% 110% at 50% -25%, rgba(255,255,255,.08), transparent 62%),
        var(--ha-card-background, var(--card-background-color, #1c1c1c));
      border-radius:var(--ha-card-border-radius, 16px);
    }
    ha-card::after{
      content:'';position:absolute;inset:0;border-radius:inherit;
      pointer-events:none;border:1px solid var(--vc);opacity:.2;
    }

    /* ---- en-tête : nom à gauche, pastille d'état à droite ---- */
    .head{
      display:flex;align-items:center;gap:10px;padding-bottom:12px;
      border-bottom:1px solid var(--divider-color, rgba(127,127,127,.2));
    }
    .nm{
      flex:1 1 auto;min-width:0;
      font-size:calc(1.02rem * var(--fs));font-weight:800;
      letter-spacing:.13em;text-transform:uppercase;color:var(--vc);
      text-shadow:0 0 18px color-mix(in srgb, var(--vc) 38%, transparent);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
      transition:color .4s ease;
    }
    .pill{
      flex:none;display:flex;align-items:center;gap:6px;
      padding:5px 11px 5px 8px;border-radius:999px;
      background:color-mix(in srgb, var(--vc) 16%, transparent);
      box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--vc) 40%, transparent);
      font-size:calc(.82rem * var(--fs));font-weight:700;color:var(--vc);
      white-space:nowrap;
    }
    .dot{width:7px;height:7px;border-radius:50%;background:var(--vc);flex:none}
    .busy .dot{animation:evc-dot 1.3s ease-in-out infinite}
    @keyframes evc-dot{50%{opacity:.25;transform:scale(.7)}}

    /* ---- illustration ---- */
    .art{
      position:relative;margin:6px auto 2px;width:78%;max-width:330px;
      opacity:var(--art-op);cursor:pointer;
      filter:drop-shadow(0 14px 22px rgba(0,0,0,.42));
    }
    .art svg,.art img{display:block;width:100%;height:auto;border-radius:12px}
    .art::before{
      content:'';position:absolute;left:50%;top:56%;
      transform:translate(-50%,-50%);width:112%;height:120%;
      border-radius:50%;z-index:-1;
      background:radial-gradient(circle,
        color-mix(in srgb, var(--vc) 26%, transparent), transparent 66%);
    }
    .brush{transform-origin:56px 138px}
    .busy .brush{animation:evc-spin 1s linear infinite}
    @keyframes evc-spin{to{transform:translate(56px,138px) rotate(360deg)}}
    .busy .lidar{animation:evc-pulse 1.5s ease-in-out infinite}
    @keyframes evc-pulse{50%{opacity:.25}}
    .busy .shade{animation:evc-hover 2.6s ease-in-out infinite}
    @keyframes evc-hover{50%{transform:scale(.94);opacity:.72}}
    .dust{opacity:0;transition:opacity .4s}
    .busy .dust{opacity:.85;animation:evc-dust 1.4s ease-out infinite}
    @keyframes evc-dust{
      0%{opacity:0;transform:translate(-14px,10px) scale(.5)}
      45%{opacity:.9}
      100%{opacity:0;transform:translate(16px,-8px) scale(1.15)}
    }
    .dock{transition:opacity .5s}
    .away .dock{opacity:.32}
    .dled{transition:opacity .4s}

    /* ---- bandeau de panne ---- */
    .fault{
      display:none;align-items:center;gap:9px;margin-top:12px;
      padding:10px 12px;border-radius:12px;
      background:color-mix(in srgb, #f87171 15%, transparent);
      box-shadow:inset 0 0 0 1px color-mix(in srgb, #f87171 42%, transparent);
      font-size:calc(.9rem * var(--fs));font-weight:700;color:#f87171;
    }
    .fault.on{display:flex}
    .fault ha-icon{--mdc-icon-size:calc(20px * var(--fs));flex:none}

    /* ---- batterie ---- */
    .bat{margin-top:14px}
    .line{display:flex;align-items:baseline;gap:8px;margin-bottom:6px}
    .line .k{
      flex:1 1 auto;min-width:0;font-size:calc(.94rem * var(--fs));
      font-weight:600;color:var(--secondary-text-color);
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .line .v{
      flex:none;font-weight:700;font-variant-numeric:tabular-nums;
      color:var(--bc, var(--primary-text-color));
      font-size:calc(1.05rem * var(--fs));
    }
    .line .v small{font-size:calc(.8rem * var(--fs));opacity:.72;margin-left:1px}
    .bat .line .v{font-size:calc(1.5rem * var(--fs));font-weight:680;
      letter-spacing:-.015em}
    .bar{height:7px;border-radius:999px;overflow:hidden;
      background:color-mix(in srgb, var(--primary-text-color) 10%, transparent)}
    .bar i{display:block;height:100%;border-radius:999px;
      background:var(--bc);transition:width .6s ease, background .4s}

    /* ---- consommables ---- */
    .sec{
      margin-top:15px;padding-top:12px;
      border-top:1px solid var(--divider-color, rgba(127,127,127,.2));
    }
    .ch{
      font-size:calc(.75rem * var(--fs));font-weight:800;letter-spacing:.12em;
      text-transform:uppercase;color:var(--secondary-text-color);
      opacity:.7;margin-bottom:10px;
    }
    .cons{display:flex;flex-direction:column;gap:9px}

    /* ---- commandes ---- */
    .btns{
      display:flex;gap:8px;margin-top:15px;padding-top:13px;
      border-top:1px solid var(--divider-color, rgba(127,127,127,.2));
    }
    .b{
      flex:1 1 0;min-width:0;border:0;cursor:pointer;font-family:inherit;
      padding:12px 5px;border-radius:12px;
      display:flex;align-items:center;justify-content:center;gap:7px;
      background:color-mix(in srgb, var(--primary-text-color) 7%, transparent);
      transition:background .18s, box-shadow .18s;
      -webkit-tap-highlight-color:transparent;
    }
    .b:hover:not(:disabled){
      background:color-mix(in srgb, var(--primary-text-color) 13%, transparent)}
    .b:disabled{opacity:.3;cursor:not-allowed}
    .b ha-icon{--mdc-icon-size:calc(22px * var(--fs));
      color:var(--secondary-text-color);flex:none;transition:color .18s}
    .b span{
      font-size:calc(.92rem * var(--fs));font-weight:700;
      color:var(--secondary-text-color);transition:color .18s;
      white-space:nowrap;overflow:hidden;text-overflow:ellipsis;
    }
    .b.on{
      background:color-mix(in srgb, var(--bcol) 20%, transparent);
      box-shadow:inset 0 0 0 1px color-mix(in srgb, var(--bcol) 48%, transparent);
    }
    .b.on ha-icon,.b.on span{color:var(--bcol)}

    @container (max-width: 380px){
      .art{width:92%}
      .b span{display:none}
      .pill .lbl{display:none}
      .pill{padding:6px 9px}
    }
    </style>
    <ha-card>
      <div class="head">
        <div class="nm"></div>
        <div class="pill"><span class="dot"></span><span class="lbl"></span></div>
      </div>
      <div class="art">` + art + `</div>
      <div class="fault"><ha-icon icon="mdi:alert-circle"></ha-icon><span></span></div>
      <div class="bat">
        <div class="line"><span class="k"></span><span class="v"></span></div>
        <div class="bar"><i></i></div>
      </div>
      <div class="sec cons-sec">
        <div class="ch">Entretien</div>
        <div class="cons"></div>
      </div>
      <div class="btns">
        <button class="b go"    style="--bcol:#34d399">
          <ha-icon icon="mdi:play"></ha-icon><span>Démarrer</span></button>
        <button class="b pause" style="--bcol:#fbbf24">
          <ha-icon icon="mdi:pause"></ha-icon><span>Pause</span></button>
        <button class="b home"  style="--bcol:#38bdf8">
          <ha-icon icon="mdi:home-import-outline"></ha-icon><span>Base</span></button>
      </div>
    </ha-card>`;

    const r = this.shadowRoot;
    this._el = {
      card:r.querySelector('ha-card'), nm:r.querySelector('.nm'),
      pill:r.querySelector('.pill'), lbl:r.querySelector('.pill .lbl'),
      art:r.querySelector('.art'),
      fault:r.querySelector('.fault'), faultTxt:r.querySelector('.fault span'),
      batK:r.querySelector('.bat .k'), batV:r.querySelector('.bat .v'),
      batBar:r.querySelector('.bat .bar i'),
      consSec:r.querySelector('.cons-sec'), cons:r.querySelector('.cons'),
      go:r.querySelector('.go'), pause:r.querySelector('.pause'),
      home:r.querySelector('.home')
    };
    this._el.card.style.setProperty('--art-op', String(this._cfg.art_opacity));
    this._el.card.style.setProperty('--fs', String(this._cfg.font_scale));

    this._el.go.addEventListener('click', () => this._call('start'));
    this._el.pause.addEventListener('click', () => this._call('pause'));
    this._el.home.addEventListener('click', () => this._call('return_to_base'));
    this._el.art.addEventListener('click', () => {
      const ev = new Event('hass-more-info', {bubbles:true, composed:true});
      ev.detail = {entityId:this._cfg.entity};
      this.dispatchEvent(ev);
    });
    this._built = true;
  }

  _call(service){
    if(!this._hass) return;
    this._hass.callService('vacuum', service, {}, {entity_id:this._cfg.entity});
  }

  set hass(h){ this._hass = h; if(this._built) this._paint(); }

  /* Une ligne de consommable : libellé, valeur, barre d'usure. */
  _consRow(label, value, pct, color){
    return '<div><div class="line"><span class="k">' + label + '</span>' +
      '<span class="v" style="--bc:' + color + '">' + value + '</span></div>' +
      '<div class="bar"><i style="width:' + pct + '%;background:' + color +
      '"></i></div></div>';
  }

  _paint(){
    const c = this._cfg, e = this._el;
    const st = this._hass.states[c.entity];
    const state = st ? st.state : 'unavailable';
    const info = EVC_STATES[state] || {t:state, col:'rgba(150,150,150,.85)', busy:false};

    e.card.style.setProperty('--vc', info.col);
    e.nm.textContent = c.name || (st ? st.attributes.friendly_name : 'Aspirateur');
    e.lbl.textContent = info.t;
    e.pill.classList.toggle('busy', info.busy);
    e.art.classList.toggle('busy', info.busy);
    e.art.classList.toggle('away', state !== 'docked');

    /* ---- panne ---- */
    let fault = '';
    if(c.fault){
      const fs = this._hass.states[c.fault];
      if(fs && fs.state && !['ok','unknown','unavailable',''].includes(
          String(fs.state).toLowerCase()))
        fault = EVC_FAULTS[fs.state] || fs.state;
    }
    e.fault.classList.toggle('on', !!fault);
    e.faultTxt.textContent = fault;

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
    e.batK.textContent = 'Batterie' + (charging ? '  ⚡ en charge' : '');
    e.batV.style.setProperty('--bc', bcol);
    e.batV.innerHTML = (isNaN(pct) ? '—' : Math.round(pct)) + '<small>%</small>';
    e.batBar.style.width = (isNaN(pct) ? 0 : Math.max(0, Math.min(100, pct))) + '%';
    e.batBar.style.background = bcol;

    /* ---- consommables ----
       Le capteur donne les heures restantes, son attribut les heures faites :
       leur somme est la durée de vie totale, d'où l'usure. */
    const wearMode = c.consumable_mode !== 'remaining';
    let rows = '';
    for(const cons of this._cons){
      const cs = this._hass.states[cons.entity];
      const label = cons.name ||
        (cs ? String(cs.attributes.friendly_name || cons.entity)
                .replace(/^RE5 Plus\s+/i, '') : cons.entity);
      if(!cs || ['unavailable','unknown'].includes(cs.state)){
        rows += this._consRow(label, '—', 0, 'rgba(150,150,150,.7)');
        continue;
      }
      const remain = evcNum(cs.state);
      const used = evcNum(cs.attributes.hours_used);
      const total = (!isNaN(remain) && !isNaN(used)) ? remain + used : NaN;
      if(!isNaN(total) && total > 0){
        const wear = Math.round((used / total) * 100);
        const shown = wearMode ? wear : 100 - wear;
        const hours = c.show_hours
          ? ' <small>· ' + Math.round(remain) + ' h</small>' : '';
        rows += this._consRow(label, shown + '<small>%</small>' + hours,
                              shown, evcWearColor(wear));
      }else if(!isNaN(remain)){
        rows += this._consRow(label, Math.round(remain) + '<small> h</small>',
                              0, 'rgba(150,150,150,.7)');
      }
    }
    e.cons.innerHTML = rows;
    e.consSec.style.display = rows ? '' : 'none';

    /* ---- commandes ---- */
    const dead = !st || state === 'unavailable';
    e.go.disabled    = dead || state === 'cleaning';
    e.pause.disabled = dead || (state !== 'cleaning' && state !== 'returning');
    e.home.disabled  = dead || state === 'docked' || state === 'returning';
    e.go.classList.toggle('on', state === 'cleaning');
    e.pause.classList.toggle('on', state === 'paused');
    e.home.classList.toggle('on', state === 'returning' || state === 'docked');
  }

  getCardSize(){ return 6; }
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
  description:'Robot et base dessines, etat, batterie, usure et commandes',
  preview:true
});
