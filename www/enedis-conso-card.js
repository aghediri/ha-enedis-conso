/* enedis-conso-card.js — Enedis Consumption (custom Lovelace card)
 * Dark, modern consumption dashboard: KPIs + HP/HC split + Tempo + cost + a
 * 30-day consumption history chart. Wired to the enedis_conso sensors.
 * Resource type: JavaScript module.
 *
 * Add:  type: custom:enedis-conso-card
 *       (optional) prefix: salon_enedis   # auto-detected if omitted
 */

const HC_SRC = "https://code.highcharts.com/highcharts.js";

class EnedisConsoCard extends HTMLElement {
  setConfig(config) {
    this._cfg = config || {};
    this._prefix = this._cfg.prefix || null;
    this._built = false;
    this._charts = {};
    this._hcReady = false;
    this._historyLoaded = false;
  }
  getCardSize() { return 10; }

  set hass(hass) {
    this._hass = hass;
    try {
      if (!this._prefix) this._prefix = this._detectPrefix();
      if (!this._built) this._build();
      this._updateValues();
      this._ensureHighchartsThenCharts();
    } catch (e) { this._renderError(e); }
  }

  // Find the entity prefix by locating *_daily_consumption among states.
  _detectPrefix() {
    if (!this._hass) return "enedis";
    for (const eid of Object.keys(this._hass.states)) {
      const m = eid.match(/^sensor\.(.*)_daily_consumption$/);
      if (m) return m[1];
    }
    return "enedis";
  }

  _id(s) { return `${this._prefix}_${s}`; }
  _s(s) { return this._hass && this._hass.states[`sensor.${this._id(s)}`]; }
  _num(s, d = null) {
    const e = this._s(s);
    if (!e || ["unknown", "unavailable", ""].includes(e.state)) return d;
    const n = parseFloat(e.state); return isNaN(n) ? d : n;
  }
  _txt(s, d = "—") {
    const e = this._s(s);
    return (!e || ["unknown", "unavailable"].includes(e.state)) ? d : e.state;
  }

  _renderError(e) {
    this.innerHTML = `<ha-card style="padding:16px;color:#ff6b6b">enedis-conso-card error: ${(e && e.message) || e}</ha-card>`;
    console.error("[enedis-conso-card]", e);
  }

  _tempoColor(name) {
    const v = (this._txt(name, "") || "").toLowerCase();
    return { blue: "#2f6bff", white: "#e9eef7", red: "#ff3b5c" }[v] || "#73839b";
  }

  _build() {
    this._built = true;
    this.style.display = "block";
    this.style.width = "100%";
    const card = document.createElement("ha-card");
    card.style.cssText = "border:none;background:transparent;display:block;width:100%";
    card.innerHTML = `
      <style>
        .w{--bg:#070b12;--card:rgba(255,255,255,.04);--line:rgba(255,255,255,.08);
          --txt:#e9f1fb;--muted:#73839b;--cyan:#1fe0ff;--lime:#8aff00;--amber:#ffb020;
          --red:#ff3b5c;--violet:#9d7bff;--green:#2ee6a0;
          background:radial-gradient(1000px 500px at 85% -10%,rgba(31,224,255,.08),transparent 60%),var(--bg);
          color:var(--txt);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
          padding:clamp(14px,2.5vw,22px);border-radius:16px;container-type:inline-size;width:100%}
        .w *{box-sizing:border-box;margin:0;padding:0}
        .w h1{font-size:clamp(16px,2.4cqw,21px);font-weight:700;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
        .chip{font-size:clamp(11px,1.4cqw,13px);padding:5px 12px;border-radius:999px;border:1px solid var(--line);display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
        .tdot{width:9px;height:9px;border-radius:50%;display:inline-block}
        .sub{color:var(--muted);font-size:clamp(11px,1.5cqw,13px);margin:6px 0 18px;display:flex;gap:clamp(8px,2cqw,16px);flex-wrap:wrap}
        .grid{display:grid;gap:clamp(10px,1.6cqw,14px);width:100%}
        .grid>*{min-width:0}
        .kpis{grid-template-columns:repeat(auto-fit,minmax(150px,1fr))}
        .two{grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}
        .c{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:clamp(13px,1.8cqw,18px);min-width:0}
        .label{font-size:clamp(9px,1.1cqw,10px);letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}
        .big{font-size:clamp(26px,4.4cqw,36px);font-weight:700;font-family:ui-monospace,'SF Mono',monospace;line-height:1}
        .unit{font-size:13px;color:var(--muted)}
        .sub2{font-size:clamp(11px,1.4cqw,12px);color:var(--muted);margin-top:6px}
        .bar{height:9px;border-radius:6px;background:rgba(255,255,255,.07);overflow:hidden;margin-top:12px;display:flex}
        .bar>span{display:block;height:100%}
        .section{font-size:clamp(11px,1.5cqw,13px);color:var(--muted);text-transform:uppercase;letter-spacing:.1em;margin:clamp(16px,2.5cqw,24px) 0 10px}
        .hr{display:flex;justify-content:space-between;gap:8px;padding:9px 0;border-bottom:1px solid var(--line);font-size:clamp(12px,1.6cqw,14px)}
        .hr:last-child{border:none}
        .dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px}
        .chart{height:clamp(200px,28cqw,260px);width:100%}
        .splitlabels{display:flex;justify-content:space-between;font-size:11px;color:var(--muted);margin-top:7px}
      </style>
      <div class="w">
        <h1>⚡ Électricité — Linky
          <span class="chip"><span class="tdot" id="tdot"></span><span id="tempoTxt">Tempo —</span></span>
        </h1>
        <div class="sub">
          <span>Hier: <b style="color:var(--txt)" id="dayKwh">—</b></span>
          <span>Ce mois: <b style="color:var(--txt)" id="monKwh">—</b></span>
          <span>Puissance souscrite: <b style="color:var(--txt)" id="subP">—</b></span>
          <span id="addr" style="color:var(--cyan)"></span>
        </div>

        <div class="grid kpis">
          <div class="c"><div class="label">Conso hier</div>
            <div><span class="big" style="color:var(--cyan)" id="kDay">—</span><span class="unit"> kWh</span></div>
            <div class="sub2" id="kDayCost">— €</div></div>
          <div class="c"><div class="label">Coût du mois</div>
            <div><span class="big" style="color:var(--amber)" id="kMonCost">—</span><span class="unit"> €</span></div>
            <div class="sub2" id="kMonKwh">— kWh ce mois</div></div>
          <div class="c"><div class="label">Puissance actuelle</div>
            <div><span class="big" style="color:var(--lime)" id="kPow">—</span><span class="unit"> W</span></div>
            <div class="sub2" id="kMaxP">pic — VA</div></div>
          <div class="c"><div class="label">Répartition HP / HC</div>
            <div><span class="big" id="kHP" style="color:var(--violet)">—</span><span class="unit"> / </span><span class="big" id="kHC" style="color:var(--green);font-size:clamp(20px,3cqw,26px)">—</span></div>
            <div class="bar"><span id="barHP" style="width:50%;background:var(--violet)"></span><span id="barHC" style="width:50%;background:var(--green)"></span></div>
            <div class="splitlabels"><span>HP (pleine)</span><span>HC (creuse)</span></div></div>
        </div>

        <div class="section">Historique — 30 jours</div>
        <div class="grid two">
          <div class="c"><div class="label">Consommation par jour (kWh)</div><div id="chDaily" class="chart"></div></div>
          <div class="c"><div class="label">Coût estimé par jour (€)</div><div id="chCost" class="chart"></div></div>
        </div>

        <div class="section">Contrat & Tempo</div>
        <div class="grid two">
          <div class="c">
            <div class="label">Contrat</div>
            <div class="hr"><span><span class="dot" style="background:var(--cyan)"></span>Tarif</span><span id="rTariff">—</span></div>
            <div class="hr"><span><span class="dot" style="background:var(--amber)"></span>Puissance souscrite</span><span id="rSub">—</span></div>
            <div class="hr"><span><span class="dot" style="background:var(--lime)"></span>Pic puissance (hier)</span><span id="rMax">—</span></div>
            <div class="hr"><span><span class="dot" style="background:var(--violet)"></span>Adresse</span><span id="rAddr" style="text-align:right;max-width:60%">—</span></div>
          </div>
          <div class="c">
            <div class="label">Tempo</div>
            <div class="hr"><span><span class="dot" id="dTodo"></span>Aujourd'hui</span><span id="rToday">—</span></div>
            <div class="hr"><span><span class="dot" id="dTom"></span>Demain</span><span id="rTom">—</span></div>
            <div class="sub2" style="margin-top:12px">Les couleurs Tempo déterminent le tarif du kWh (bleu &lt; blanc &lt; rouge). Décalez les gros usages hors des jours rouges.</div>
          </div>
        </div>
      </div>`;
    this.innerHTML = "";
    this.appendChild(card);
    this._root = card;

    if (window.ResizeObserver && !this._ro) {
      this._ro = new ResizeObserver(() => {
        if (!window.Highcharts) return;
        clearTimeout(this._rt);
        this._rt = setTimeout(() => {
          Object.values(this._charts).forEach((c) => { try { c && c.reflow && c.reflow(); } catch (e) {} });
        }, 120);
      });
      this._ro.observe(card);
    }
  }

  disconnectedCallback() { if (this._ro) { try { this._ro.disconnect(); } catch (e) {} this._ro = null; } }

  _q(id) { return this._root && this._root.querySelector("#" + id); }

  _updateValues() {
    if (!this._root || !this._hass) return;
    const set = (id, v) => { const el = this._q(id); if (el) el.textContent = v; };

    const day = this._num("daily_consumption"), dayCost = this._num("daily_cost");
    const mon = this._num("month_consumption"), monCost = this._num("month_cost");
    const pow = this._num("last_power"), maxp = this._num("daily_max_power");
    const hp = this._num("hp_consumption"), hc = this._num("hc_consumption");

    set("kDay", day == null ? "—" : day.toFixed(2));
    set("kDayCost", dayCost == null ? "— €" : dayCost.toFixed(2) + " €");
    set("dayKwh", day == null ? "—" : day.toFixed(1) + " kWh");
    set("kMonCost", monCost == null ? "—" : monCost.toFixed(2));
    set("kMonKwh", mon == null ? "— kWh ce mois" : mon.toFixed(1) + " kWh ce mois");
    set("monKwh", mon == null ? "—" : mon.toFixed(1) + " kWh");
    set("kPow", pow == null ? "—" : Math.round(pow));
    set("kMaxP", maxp == null ? "pic — VA" : "pic " + Math.round(maxp) + " VA");

    if (hp != null && hc != null) {
      set("kHP", hp.toFixed(1)); set("kHC", hc.toFixed(1));
      const tot = hp + hc;
      const php = tot > 0 ? (hp / tot) * 100 : 50;
      const bHP = this._q("barHP"), bHC = this._q("barHC");
      if (bHP) bHP.style.width = php + "%";
      if (bHC) bHC.style.width = (100 - php) + "%";
    }

    // Contract rows
    set("rTariff", this._txt("tariff")); set("rSub", this._txt("subscribed_power"));
    set("subP", this._txt("subscribed_power"));
    set("rMax", maxp == null ? "—" : Math.round(maxp) + " VA");
    const addr = this._txt("address", "");
    set("rAddr", addr || "—");
    const addrEl = this._q("addr"); if (addrEl) addrEl.textContent = addr || "";

    // Tempo
    const today = this._txt("tempo_today"), tom = this._txt("tempo_tomorrow");
    set("rToday", today); set("rTom", tom);
    set("tempoTxt", "Tempo " + (today === "—" ? "—" : today));
    const col = (name) => this._tempoColor(name);
    const td = this._q("tdot"); if (td) td.style.background = col("tempo_today");
    const d1 = this._q("dTodo"); if (d1) d1.style.background = col("tempo_today");
    const d2 = this._q("dTom"); if (d2) d2.style.background = col("tempo_tomorrow");
  }

  _cv(v) { const w = this._root && this._root.querySelector(".w"); return w ? getComputedStyle(w).getPropertyValue(v).trim() : ""; }
  _base() {
    const m = this._cv("--muted"), l = this._cv("--line"), t = this._cv("--txt");
    return { chart: { backgroundColor: "transparent", spacing: [8, 6, 4, 6] }, credits: { enabled: false },
      title: { text: null }, legend: { enabled: false },
      xAxis: { labels: { style: { color: m, fontSize: "9px" } }, lineColor: l, tickLength: 0 },
      yAxis: { title: { text: null }, gridLineColor: "rgba(255,255,255,.05)", labels: { style: { color: m, fontSize: "9px" } } },
      tooltip: { backgroundColor: "#0f1620", borderColor: l, style: { color: t } } };
  }

  _ensureHighchartsThenCharts() {
    if (this._hcReady) return;
    if (window.Highcharts) { this._hcReady = true; this._initCharts(); this._loadHistory(); return; }
    if (this._hcLoading) return;
    this._hcLoading = true;
    const sc = document.createElement("script");
    sc.src = HC_SRC;
    sc.onload = () => { this._hcReady = true; try { this._initCharts(); this._loadHistory(); } catch (e) { console.error(e); } };
    sc.onerror = () => console.error("[enedis-conso-card] Highcharts CDN failed");
    document.head.appendChild(sc);
  }

  _initCharts() {
    const H = window.Highcharts; if (!H || !this._root || this._charts._done) return;
    this._charts._done = true;
    const b = this._base(), C = this._charts, el = (id) => this._q(id);
    const cyan = this._cv("--cyan"), amber = this._cv("--amber"), muted = this._cv("--muted");
    const g = (c, a) => ({ linearGradient: { x1: 0, x2: 0, y1: 0, y2: 1 }, stops: [[0, c], [1, a]] });
    const days = [...Array(30)].map((_, i) => "" + (i + 1));
    C.chDaily = H.chart(el("chDaily"), { ...b, chart: { ...b.chart, type: "column" }, xAxis: { ...b.xAxis, categories: days },
      yAxis: { ...b.yAxis, title: { text: "kWh", style: { color: muted } } },
      series: [{ data: [], borderRadius: 3, color: g(cyan, "rgba(31,224,255,.2)") }] });
    C.chCost = H.chart(el("chCost"), { ...b, chart: { ...b.chart, type: "column" }, xAxis: { ...b.xAxis, categories: days },
      yAxis: { ...b.yAxis, title: { text: "€", style: { color: muted } } },
      series: [{ data: [], borderRadius: 3, color: g(amber, "rgba(255,176,32,.2)") }] });
  }

  async _loadHistory() {
    if (this._historyLoaded || !this._hass || !window.Highcharts) return;
    this._historyLoaded = true;
    const now = new Date(), ago = (n) => new Date(now.getTime() - n * 864e5).toISOString();
    const eid = `sensor.${this._id("daily_consumption")}`;
    try {
      const r = await this._hass.callWS({ type: "history/history_during_period",
        start_time: ago(30), end_time: now.toISOString(), entity_ids: [eid],
        minimal_response: true, no_attributes: true });
      const hist = (r && r[eid]) || [];
      const nDays = 30, out = new Array(nDays).fill(null), start = now.getTime() - nDays * 864e5;
      hist.forEach((p) => {
        const t = p.lu ? p.lu * 1000 : Date.parse(p.last_updated || 0);
        if (!t || t < start) return;
        const idx = Math.floor((t - start) / 864e5), v = parseFloat(p.s != null ? p.s : p.state);
        if (!isNaN(v) && idx >= 0 && idx < nDays) out[idx] = v;
      });
      const kwh = out.map((v) => v == null ? 0 : v);
      if (this._charts.chDaily) this._charts.chDaily.series[0].setData(kwh, true);
      // Cost series = kWh * representative price (daily_cost/daily_consumption ratio).
      const dc = this._num("daily_cost"), dk = this._num("daily_consumption");
      const rate = (dc && dk) ? dc / dk : 0.2;
      if (this._charts.chCost) this._charts.chCost.series[0].setData(kwh.map((v) => +(v * rate).toFixed(2)), true);
    } catch (e) { console.error("[enedis-conso-card] history", e); }
  }
}

customElements.define("enedis-conso-card", EnedisConsoCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "enedis-conso-card", name: "Enedis Consumption Card", description: "Dark consumption dashboard: KPIs, HP/HC, Tempo, cost, 30-day history." });
console.info("%c ENEDIS-CONSO-CARD ", "background:#1fe0ff;color:#070b12;font-weight:700", "loaded");
