"use strict";
/* VR-Navigator, Oberfläche ohne Build. Reiter: Jetzt, Wunschliste (VR, PC), Sammlung (mit VR), Einstellungen.
   Farben, Marken und Klappen folgen docs/oberflaeche.md.
   Alle fremden Texte (Titel, Notizen, Links) laufen durch esc() bzw. safeUrl(). */

const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const safeUrl = u => /^https?:\/\//i.test(String(u || "")) ? String(u) : "";
const eur = v => v == null ? "–" : v.toLocaleString("de-DE", {minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2}) + " €";
const day = iso => iso ? new Date(iso).toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit", year: "numeric"}) : "";
// Erscheinen (0.8.8): libretro nennt oft nur Jahr und Monat („2004-11“)
const relDay = r => /^\d{4}-\d{2}$/.test(r || "") ? new Date(r + "-15").toLocaleDateString("de-DE", {month: "long", year: "numeric"}) : (r || "").length > 4 ? day(r) : "";
const mb = b => b >= 1e9 ? `${(b / 1e9).toLocaleString("de-DE", {maximumFractionDigits: 1})} GB` : b >= 1e6 ? `${Math.round(b / 1e6)} MB` : `${Math.max(1, Math.round(b / 1e3))} KB`;
const when = iso => iso ? new Date(iso).toLocaleString("de-DE", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"}) : "";
// Ende eines Angebots als Tag: „bis 28.10.“
const until = d => d ? "bis " + new Date(d + "T12:00:00").toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit"}) : "";

let S = null;                                   // Zustand vom Server
// Die Bibliothek ist seit 0.6.0 der Reiter VR in der Sammlung
const TABS = [["now", "Jetzt"], ["wish", "Wunschliste"], ["find", "Sammlung"], ["settings", "Einstellungen"]];
const V = {tab: "wish", wsub: "pc", pcSort: "near", q: "", sort: "name", prev: {}, folds: {}, sorts: {}};
// Ansicht je Browser (vn.view): Reiter, Klappzustände, Sortierung nach Spalte. Bis 0.2.1 gab es die
// Reiter Abrufe und Import, beide stehen jetzt unter Einstellungen; „lib“ führt in die Sammlung, Reiter VR.
let LIB_IN = false;
try{
  const v = JSON.parse(localStorage.getItem("vn.view") || "{}") || {};
  const t = v.tab || localStorage.getItem("vn.tab") || V.tab;
  LIB_IN = t === "lib";
  V.tab = t === "sync" || t === "import" ? "settings" : LIB_IN ? "find" : TABS.some(x => x[0] === t) ? t : V.tab;
  V.folds = v.folds && typeof v.folds === "object" ? v.folds : {};
  V.sorts = v.sorts && typeof v.sorts === "object" ? v.sorts : {};
  if(v.wsub === "pc" || v.wsub === "vr") V.wsub = v.wsub;
}catch(e){}
function saveView(){ try{ localStorage.setItem("vn.view", JSON.stringify({tab: V.tab, wsub: V.wsub, folds: V.folds, sorts: V.sorts})); }catch(e){} }

/* ---------------------------------------------------------------- Zeiten, Hinweise, Kopieren */
function ago(iso){
  if(!iso) return "noch nie";
  const min = Math.max(0, Math.round((Date.now() - new Date(iso)) / 60000));
  if(min < 2) return "gerade eben";
  if(min < 90) return `vor ${min} Min.`;
  if(min < 48 * 60) return `vor ${Math.round(min / 60)} Std.`;
  return `vor ${Math.round(min / 1440)} Tagen`;
}
const clock = d => d.toLocaleTimeString("de-DE", {hour: "2-digit", minute: "2-digit"});
function whenDay(d){   // „morgen “ oder „23.10. “ vor einer Uhrzeit, die nicht mehr heute ist
  const dd = x => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const n = Math.round((dd(d) - dd(new Date())) / 86400000);
  return n <= 0 ? "" : n === 1 ? "morgen " : d.toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit"}) + " ";
}
/* Kurzer Hinweis unten; mit undo ein Knopf „Rückgängig“ und mehr Zeit (statt einer Rückfrage vorher) */
function toast(msg, undo){
  document.querySelectorAll(".toast").forEach(t => t.remove());
  const t = document.createElement("div");
  t.className = "toast"; t.setAttribute("role", "status");
  t.append(msg);
  if(undo){
    const b = document.createElement("button");
    b.textContent = "Rückgängig";
    b.onclick = () => { t.remove(); undo(); };
    t.appendChild(b);
  }
  document.body.appendChild(t);
  setTimeout(() => t.remove(), undo ? 7000 : 2600);
}
/* Sofort kopieren, noch im Klick: execCommand arbeitet synchron, navigator.clipboard nur als Rückfall */
function copyNow(text){
  const t = document.createElement("textarea");
  t.value = text; t.style.cssText = "position:fixed;top:0;left:0;opacity:0";
  document.body.appendChild(t); t.focus(); t.select();
  let ok = false;
  try{ ok = document.execCommand("copy"); }catch(e){}
  t.remove();
  if(!ok) try{ navigator.clipboard.writeText(text); }catch(e){}
  toast("Kopiert");
}

async function api(path, body){
  const opt = body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)};
  const r = await fetch(path, opt);
  const j = await r.json().catch(() => ({}));
  if(!r.ok) throw new Error(j.error || `Fehler ${r.status}`);
  return j;
}

/* ---------------------------------------------------------------- Ansicht hell/dunkel */
// Runder Knopf mit dem Zeichen der Wahl (halber Kreis System, Sonne, Mond), ein Klick öffnet das Menü
const ICO = d => `<svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">${d}</svg>`;
const THEMES = [
  ["system", ICO(`<circle cx="8" cy="8" r="6"/><path d="M8 2a6 6 0 0 1 0 12z" fill="currentColor"/>`), "System", "wie dein Gerät"],
  ["light", ICO(`<circle cx="8" cy="8" r="3"/><path d="M8 1v1.5M8 13.5V15M1 8h1.5M13.5 8H15M3 3l1 1M12 12l1 1M3 13l1-1M12 4l1-1"/>`), "Hell", ""],
  ["dark", ICO(`<path d="M13.5 10A6 6 0 0 1 6 2.5a6 6 0 1 0 7.5 7.5z"/>`), "Dunkel", ""]];
function themeNow(){ const t = document.documentElement.dataset.theme; return t === "light" || t === "dark" ? t : "system"; }
function renderTheme(){
  const cur = THEMES.find(x => x[0] === themeNow()), b = $("thmBtn");
  b.innerHTML = cur[1];
  b.title = `Ansicht: ${cur[2]}${cur[3] ? ` (${cur[3]})` : ""}. Klick zum Ändern`;
  b.setAttribute("aria-label", b.title);
  $("thmMenu").innerHTML = THEMES.map(([k, ic, l, h]) =>
    `<button role="menuitemradio" aria-checked="${k === cur[0]}" class="${k === cur[0] ? "on" : ""}" data-act="thmset" data-v="${k}"><span class="ic">${ic}</span>${l}${h ? ` <span class="hint">${h}</span>` : ""}</button>`).join("");
}
function themeMenu(open){ $("thmMenu").hidden = !open; $("thmBtn").setAttribute("aria-expanded", open); }
function setTheme(k){
  if(k === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = k;
  try{ if(k === "system") localStorage.removeItem("vn.theme"); else localStorage.setItem("vn.theme", k); }catch(e){}
  renderTheme(); themeMenu(false);
}

/* ---------------------------------------------------------------- Klappen
   Offen als Vorgabe (mit shut zu); gemerkt wird nur die Abweichung davon, je Browser. Während
   einer Suche ist jede Gruppe offen, damit kein Treffer versteckt bleibt. */
const isOpen = (k, shut) => V.q.trim() ? true : k in V.folds ? !V.folds[k] : !shut;
const foldAttr = (k, shut) => `data-kc="${esc(k)}"${shut ? ` data-shut="1"` : ""} ${isOpen(k, shut) ? "open" : ""}`;
function grp(k, title, n, body, shut){
  return `<details class="grp" ${foldAttr(k, shut)}><summary>${title}<span class="n">${esc(n)}</span></summary>${body}</details>`;
}
const foldAll = `<span class="foldall"><button class="link" data-act="foldall" data-v="1">alle aufklappen</button> · <button class="link" data-act="foldall" data-v="">alle zuklappen</button></span>`;

/* ---------------------------------------------------------------- Rahmen */
function renderNav(){
  const c = S.counts, sug = S.suggestions.length + (S.todo || []).length + (S.lists || []).length + (S.retro_near || []).length;
  const sy = S.sync || {};
  const set = sy.running ? "läuft" : Object.values(sy.sources || {}).some(x => !x.ok) ? "Fehler" : sug ? `${sug} offen` : "";
  const cnt = {now: c.now || "", wish: c.wish + (S.pcwish?.rows || []).filter(r => !pcIsVr(r)).length || "", find: (S.imports.collection?.n || 0) + (c.owned || 0) || "", settings: set};
  $("nav").innerHTML = TABS.map(([k, l]) =>
    `<button data-act="tab" data-v="${k}" class="${V.tab === k ? "on" : ""}">${l}${cnt[k] !== "" ? `<span class="cnt">${esc(cnt[k])}</span>` : ""}</button>`).join("");
  renderHead();
  navFade();
}
/* Reiterleiste schmaler als ihre Reiter (Handy): rechts weich ausblenden, damit man sieht, dass es weitergeht */
function navFade(){
  const n = $("nav");
  if(n) n.classList.toggle("more", n.scrollLeft + n.clientWidth < n.scrollWidth - 2);
}
/* Kopfzeile: während eines Laufs Schritt und Fortschritt, sonst Stand und nächster Abgleich */
function renderHead(){
  const sy = S.sync || {}, se = S.settings || {}, hours = se.hours || 6, m = $("meta");
  if(sy.running){
    m.textContent = `${sy.step || "Abgleich"}${sy.total ? ` (${sy.done}/${sy.total})` : ""} …`;
  } else {
    const last = sy.started ? new Date(sy.started) : null;
    const stale = last && Date.now() - last > 2 * hours * 3600000;
    const next = last && se.auto ? new Date(+last + hours * 3600000) : null;
    m.innerHTML = `<span class="${stale ? "stale" : ""}" title="${last ? esc(last.toLocaleString("de-DE")) : ""}">Stand ${ago(sy.started)}</span>` +
      (next ? ` · nächster Abgleich ${next < new Date() ? "in Kürze" : "ca. " + whenDay(next) + clock(next)}` : se.auto === false ? " · Zeitplan aus" : "") +
      ` · ${S.counts.all} Titel · v${esc(S.version)}`;
  }
  $("syncBtn").disabled = !!sy.running;
}
/* Hinweise über den Ansichten: kein Abgleich, ruhende Quelle, Selbstprüfung, Fehler */
const SRC_NAME = {qsdb: "QuestStoreDB", steam: "Steam", gg: "gg.deals", steamacc: "Steam-Konto", ggwish: "gg.deals-Wunschliste", sharenite: "Sharenite", reviews: "Steam-Rezensionen", details: "Steam-Details", rating: "Steam-Wertungen", players: "Steam-Spieler", vrdb: "VRDB", retro: "Retro-Fassungen", igdb: "IGDB", pcgw: "PCGamingWiki", nexus: "Nexus Mods", wheel: "Sim-Racing", eshop: "eShopKompass"};
function banners(){
  const sy = S.sync || {}, out = [];
  const logLink = `<button class="link" data-act="showlog">Protokoll öffnen</button>`;
  if(sy.running) return "";
  if(!sy.started) return `<div class="banner">Noch kein Abgleich. Der erste Lauf holt die Preise deiner Wunschtitel und dauert einige Minuten.
    <button class="link" data-act="sync">Aktualisieren</button></div>`;
  const src = sy.sources || {};
  const resting = Object.entries(src).filter(([, x]) => x.until && new Date(x.until) > new Date());
  if(resting.length) out.push(`${resting.map(([k, x]) => `${SRC_NAME[k] || k} ruht nach einer Sperre bis ${esc(whenDay(new Date(x.until)) + clock(new Date(x.until)))}`).join(", ")}. Bis dahin gelten die zuletzt gelesenen Preise.`);
  if((sy.warnings || []).length) out.push(`Selbstprüfung nach dem letzten Abgleich: ${sy.warnings.map(esc).join(" · ")}.`);
  const failed = Object.entries(src).filter(([k, x]) => !x.ok && !x.until);
  if(failed.length) out.push(`Letzter Abgleich mit Fehlern: ${failed.map(([k, x]) => `${SRC_NAME[k] || k} (${esc(x.msg || "Fehler")})`).join(", ")}.`);
  return out.map(t => `<div class="banner">${t} ${logLink}</div>`).join("");
}

/* Zeichnet neu. Mit anchor (id einer Karte) bleibt diese Karte an ihrer Stelle im Fenster,
   damit die Seite beim Einlesen einer Datei oder einer Vorschau nicht springt. */
function render(anchor){
  const a = anchor && $(anchor), top = a ? a.getBoundingClientRect().top : null;
  renderNav();
  saveView();
  $("main").innerHTML = V.tab === "now" ? banners() + nowView()
    : V.tab === "find" ? findView() : V.tab === "settings" ? settingsView() : banners() + wishView();
  findHash();
  showLog();
  moreOnScroll();
  if(V.tab === "find") fitTags();
  const b = anchor && $(anchor);
  if(b && top !== null) scrollBy(0, b.getBoundingClientRect().top - top);
  const q = $("q");
  if(q && document.activeElement !== q && V.focusQ){ q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
}

/* Marken neben dem Namen. Crossbuy mit Herkunft: von Hand und VRDB ohne Zeichen, aus deiner
   Tabelle mit „Tabelle“, aus der Recherche mit „≈“. Widerspricht eine schwächere Quelle, steht
   sie violett daneben. „ohne Crossbuy“ ist eine Eigenschaft, kein Fehler: grau. */
const CB_FROM = {Hand: "von dir eingetragen", VRDB: "laut VRDB (Angabe im Meta Store)",
  Tabelle: "aus deiner Vergleichstabelle, noch nicht von VRDB bestätigt", Recherche: "aus der Recherche, nicht geprüft"};
function badges(r){
  const out = [];
  if(r.where === "meta" || r.where === "beide") out.push(`<span class="b" title="Im Meta Store gekauft">Meta</span>`);
  if(r.where === "pc" || r.where === "beide") out.push(`<span class="b" title="In Playnite (PC)">${esc(r.pc_label || "PC")}</span>`);
  if(r.crossbuy != null){
    const s = r.crossbuy_src, mark = s === "Tabelle" ? " · Tabelle" : s === "Recherche" ? " ≈" : "", from = CB_FROM[s] ? ` (${CB_FROM[s]})` : "";
    out.push(r.crossbuy ? `<span class="b go" title="Spricht für Meta: der Kauf gilt auch für die PC-Fassung (Rift)${from}">Crossbuy${mark}</span>`
      : `<span class="b" title="Der Meta-Kauf gilt nur auf der Quest${from}">ohne Crossbuy${mark}</span>`);
    if(r.crossbuy_other) out.push(`<span class="b warn" title="Die Quellen widersprechen sich; es gilt ${esc(s)}">${esc(r.crossbuy_other)}</span>`);
  }
  if(r.steam_appid && !r.steam_sure) out.push(`<span class="b warn" title="${esc(r.steam_doubt ? "Steam-ID passt wohl nicht: " + r.steam_doubt + " (siehe Einstellungen, Zu erledigen)" : "Steam-ID nur nach dem Namen zugeordnet, das Tool prüft sie beim nächsten Abgleich")}">Steam-ID ≈</span>`);
  if(r.bundle) out.push(`<span class="b" title="Paket aus mehreren Spielen">Bundle</span>`);
  out.push(wheelBadge(r.wheel));
  out.push(wishListBadge(r));
  return out.filter(Boolean).join(" ");
}
/* Wie im eShopKompass: Steht ein Wunschtitel auf keiner Wunschliste eines Ladens, oder fehlt er
   in einem Laden, der ihn führt, sagt es eine Marke, und „+ Meta“ / „+ gg.deals“ öffnen die Seite,
   auf der du ihn mit einem Klick nachträgst. Der nächste Abgleich ordnet ihn dann selbst zu. */
const addLinks = (links, only) => (links || []).filter(l => safeUrl(l.url) && (!only || only(l))).map(l =>
  `<a class="add" href="${esc(l.url)}" target="_blank" rel="noopener noreferrer" title="Dort auf die Wunschliste setzen">+ ${esc(l.label)}</a>`).join(" ");
function wishListBadge(r){
  if(!r.wish || r.where) return "";
  const miss = r.wish_missing || [];
  if(!r.wish_src?.length) return `<span class="b warn" title="Steht auf keiner Wunschliste eines Ladens, nur ${r.sheet ? "in deiner alten Tabelle" : "im Tool"}">auf keiner Laden-Wunschliste${r.sheet ? " · Tabelle" : ""}</span> ${addLinks(r.add_links || [])}`;
  if(!miss.length) return "";
  const names = {meta: "Meta", pc: S.settings?.steam_wish === false ? "gg.deals" : "Steam/gg.deals"};
  return `<span class="b warn" title="Den Titel gibt es dort, er steht aber nicht auf deiner Wunschliste">fehlt auf Wunschliste: ${miss.map(m => names[m]).join(", ")}</span> ${addLinks(r.add_links, l => miss.includes(l.label === "Meta" ? "meta" : "pc"))}`;
}
const linksHtml = r => `<span class="links">${r.links.filter(l => safeUrl(l.url)).map(l =>
  `<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.label)}</a>`).join("")}</span>`;

function match(r){
  const q = V.q.trim().toLowerCase();
  return !q || r.name.toLowerCase().includes(q) || r.note.toLowerCase().includes(q);
}

/* Fakten in einer Zeile, jede mit kleinem grauem Namen davor:
   Wertung je Laden auf einer Skala (Steam: Anteil positiver Rezensionen ab 50; Meta: Anteil 4 und 5
   Sterne laut VRDB, sonst Sterne × 20 mit „≈“), der bessere ab 5 Punkten Abstand grün;
   Steam-Spieler jetzt (Spitze aus eigenen Messungen), letztes Steam-Update, Meta-Version. */
const num = n => (n ?? 0).toLocaleString("de-DE");
const RATE_GAP = 5;
const fact = (label, body, tip) => `<span class="fact"${tip ? ` title="${esc(tip)}"` : ""}><span class="fl">${label}</span><span class="fv">${body}</span></span>`;
function agoDays(d){
  const n = Math.round((Date.now() - new Date(d + "T12:00:00")) / 864e5);
  return n < 1 ? "heute" : n < 60 ? `vor ${n} Tagen` : n < 730 ? `vor ${Math.round(n / 30.4)} Monaten` : `vor ${Math.round(n / 365)} Jahren`;
}
function factsHtml(r){
  const out = [], m = r.rating?.meta, s = r.rating?.steam, g = r.measured || {};
  if(m || s){
    const mp = m ? m.pos ?? Math.round(m.stars * 20) : null, sp = s?.pct ?? null;
    const win = mp != null && sp != null && Math.abs(mp - sp) >= RATE_GAP ? (mp > sp ? "meta" : "steam") : "";
    const cell = (k, label, v, n, tip) => `<span class="rate${win === k ? " win" : ""}" title="${esc(tip)}">${label} ${v}${n ? ` <span class="hint">(${num(n)})</span>` : ""}</span>`;
    const parts = [];
    if(m) parts.push(m.pos != null ? cell("meta", "Meta", `${mp} %`, m.n, `Meta Store: Anteil 4 und 5 Sterne (laut VRDB), Schnitt ${String(m.stars).replace(".", ",")} von 5`)
      : cell("meta", "Meta", `≈${mp} %`, m.n, `Meta Store: ${String(m.stars).replace(".", ",")} von 5 Sternen, umgerechnet × 20 (gelesen bei QuestStoreDB)`));
    if(s) parts.push(sp != null ? cell("steam", "Steam", `${sp} %`, s.n, "Anteil positiver Steam-Rezensionen") + trendMark(s.trend)
      : `<span class="hint" title="Steam-Rezensionen; eine Wertung gibt es ab 50">Steam ${num(s.n)} Rez.</span>`);
    if(win) parts.push(`<span class="b go" title="Mindestens ${RATE_GAP} Punkte Abstand">${win === "meta" ? "Meta" : "Steam"} +${Math.abs(mp - sp)}</span>`);
    out.push(fact("Wertung", parts.join(" ")));
  }
  if(g.players && g.players.now != null) out.push(fact("Spieler", `${num(g.players.now)}${g.players.peak > g.players.now ? ` <span class="hint">(Spitze ${num(g.players.peak)})</span>` : ""}`,
    `Steam-Spieler gerade eben (${when(g.players.at)}); Spitze: höchster gemessener Wert seit ${day(g.players.since)}`));
  if(s?.trend) out.push(fact("Trend", trendText(s.trend)));
  if(g.update) out.push(fact("Update", agoDays(g.update.date) + (CARE[g.update.care?.state] ? ` <span class="hint">(${CARE[g.update.care.state]})</span>` : ""), `Steam, laut Meldung des Entwicklers: ${g.update.title}`));
  if(g.meta_ver) out.push(fact("Meta", `v${esc(g.meta_ver.v.split("_")[0])}${g.meta_ver.since ? ` seit ${agoDays(g.meta_ver.since).replace("vor ", "")}` : ""}`,
    `Version im Meta Store laut VRDB${g.meta_ver.since ? "; das Tool sah sie zuerst am " + day(g.meta_ver.since) : ", zuerst gesehen beim ersten Abruf"}`));
  return out.length ? `<div class="facts">${out.join("")}</div>` : "";
}

/* Filter für Jetzt und Wunschliste (gemeinsam, je Reiter nur die passenden) */
V.lf = {cb: false, sale: false, best: false, good: false};
const LF = [["cb", "Crossbuy", r => r.crossbuy === true],
  ["sale", "Im Angebot", r => (r.live.meta?.discount || 0) + (r.live.steam?.discount || 0) > 0],
  ["best", "Am Bestpreis", r => ["meta", "steam"].some(s => (r.best?.[s]?.all_level ?? r.best?.[s]?.level) === "best")],
  ["good", "Gut bewertet", r => (r.rating?.score || 0) >= 85]];
const lfOk = (r, keys) => LF.every(([k, , f]) => !keys.includes(k) || !V.lf[k] || f(r));
// Sortierschlüssel, kleiner zuerst
const byRating = r => -(r.rating?.score ?? -1), byAdded = r => -(Date.parse(r.added) || 0);

/* Werkzeugzeile: Suche mit eigenem × (Esc leert sie ebenso), Sortieren als Auswahl, Filter als
   aufklappendes Menü mit Häkchen, „?“ für die Legende. Gewählte Filter stehen darunter als
   Marken mit ×. Menüs schließen bei einem Klick daneben (V.menu merkt, welches offen ist). */
const menuAttr = k => `data-menu="${k}"${V.menu === k ? " open" : ""}`;
function listBar(o){
  const sel = `<label class="kind">Sortieren <select data-sort="${o.sortKey}">${o.sorts.map(([v, l]) => `<option value="${v}"${o.sort === v ? " selected" : ""}>${l}</option>`).join("")}</select></label>`;
  const fs = LF.filter(([k]) => o.filters.includes(k)), on = fs.filter(([k]) => V.lf[k]);
  const menu = fs.length ? `<details class="menu" ${menuAttr("lf")}><summary>Filter${on.length ? ` <span class="cnt">${on.length}</span>` : ""}</summary>
    <div class="pop">${fs.map(([k, l]) => `<label><input type="checkbox" data-lf="${k}"${V.lf[k] ? " checked" : ""}> ${l}</label>`).join("")}</div></details>` : "";
  const chips = on.length ? `<div class="chips act">${on.map(([k, l]) => `<button data-act="lf" data-v="${k}" title="Filter entfernen">${l} ×</button>`).join("")}</div>` : "";
  return `<div class="bar"><span class="sbox"><input type="search" id="q" placeholder="Titel oder Notiz suchen" aria-label="Titel oder Notiz suchen" value="${esc(V.q)}" data-in="q">${V.q ? `<button class="sx" data-act="qclear" title="Suche leeren (Esc)" aria-label="Suche leeren">×</button>` : ""}</span>
    <span class="tools">${sel}${menu}<button data-act="legend" class="${V.legend ? "on" : ""}" aria-label="Legende" title="Was Farben und Zeichen bedeuten">?</button>${o.extra || ""}</span></div>${chips}${V.legend ? legendHtml() : ""}`;
}
// Legende: einmal für alle Listen, statt Erklärtext über jeder Liste (Regeln: docs/oberflaeche.md)
function legendHtml(){
  return `<div class="card legend"><h2>Farben und Zeichen <button class="link" data-act="legend">schließen</button></h2>
    <div class="lg"><span class="over">+7 €</span> über dem Bestpreis der letzten 24 Monate</div>
    <div class="lg"><span class="star">★</span> <span class="best-t">Bestpreis</span>: höchstens 2 % über dem niedrigsten Preis beider Läden; darunter klein der Tiefstpreis des Ladens selbst; „übliches Angebot“: so tief wie in mindestens zwei Angeboten</div>
    <div class="lg">≈ am Bestpreis: übernommen (QuestStoreDB oder gg.deals), solange der eigene Preisverlauf zu kurz ist</div>
    <div class="lg"><span class="vd buy">kaufen</span> höchstens 2 % oder 0,50 € über dem Bestpreis beider Läden · <span class="vd good">gut</span> höchstens 15 % oder 2 € darüber (wie im eShopKompass); „Jetzt“ zeigt Angebote mit diesem Urteil</div>
    <div class="lg"><span class="vd wb buy">Meta kaufen</span> <span class="vd wb wait">Steam warten</span> wo kaufen: der Laden, für den mehr spricht (Crossbuy zählt 2, ein großer Preisabstand ab 40 % und 8 € zählt 2, je 1: Mehrspieler mit wenig Spielern auf Steam, 8 Punkte bessere Wertung, ein Jahr jüngere Pflege, spürbar günstiger; Recherche halb), dahinter das Preisurteil dort; die Gründe stehen in der Zeile „Wo“</div>
    <div class="lg"><span class="b deal">−20 %</span> Rabatt jetzt</div>
    <div class="lg"><span class="shopmark">grüner Rahmen</span> der günstigere Laden, mit Betrag (ab 1 €; Steam-Seite zählt auch Händler und Keyshops bei gg.deals)</div>
    <div class="lg"><span class="b go">Crossbuy</span> Meta-Kauf gilt auch am PC; <span class="b">ohne Crossbuy</span> nur auf der Quest</div>
    <div class="lg"><span class="rate win">Meta 88 %</span> besser bewerteter Laden (ab 5 Punkten Abstand)</div>
    <div class="lg">ohne Zeichen: vom Tool gemessen · <b>≈</b> abgeleitet oder aus fremder Quelle · <b>Tabelle</b> aus deiner Vergleichstabelle · <span class="ux">violett gestrichelt</span> Recherche · <span class="b warn">violett</span> prüfen</div></div>`;
}

/* ---------------------------------------------------------------- Wunschliste */
/* Wunschliste mit Unterreitern VR und PC (0.8.2). PC spiegelt die ganze gg.deals-Wunschliste; gepflegt
   wird sie dort (Entscheidung 27.10.2026), das Tool holt Steam-ID und Preise dazu */
function wishView(){
  const pw = S.pcwish || {n: 0};
  if(!pw.n) return vrWishView();
  const tab = (v, l, c, cls, tip) => `<button role="tab" aria-selected="${V.wsub === v}" data-act="wsub" data-v="${v}" class="${cls}${V.wsub === v ? " on" : ""}" title="${esc(tip)}">${l} <span class="n">${c}</span></button>`;
  // PC vor VR wie in der Sammlung (0.8.7); VR-Spiele der gg.deals-Liste stehen nur unter VR
  const pcN = pw.rows.filter(r => !pcIsVr(r)).length;
  const tabs = `<div class="systabs" role="tablist" aria-label="Wunschliste">${tab("pc", "PC", pcN, "fam-pc", "Deine Wunschliste bei gg.deals ohne die VR-Spiele, mit Preisen von Händlern und Keyshops")}${tab("vr", "VR", S.counts.wish, "fam-vr", "Deine VR-Wünsche bei Meta und am PC, mit Preisen beider Läden")}</div>`;
  return tabs + (V.wsub === "pc" ? pcWishView(pw) : vrWishView());
}
const pcIsVr = r => r.vr && !r.vr_guess;
const PC_KIND = {pack: ["Paket", "Paket aus mehreren Spielen oder Edition mit Zusätzen; Preis auf der Seite bei gg.deals"], dlc: ["DLC", "Erweiterung; Preis auf der Seite bei gg.deals"]};
const PC_SORTS = [["near", "Nah am Tief"], ["best", "Preis"], ["score", "Wertung"], ["hours", "Spielzeit"], ["year", "Jahr"], ["name", "Name"], ["new", "Neu"]];
function pcWishView(pw){
  const q = V.q.trim().toLowerCase();
  const all = pw.rows.filter(r => !pcIsVr(r)), nVr = pw.rows.length - all.length;
  let rows = all.filter(r => !q || r.name.toLowerCase().includes(q) || (r.dev || "").toLowerCase().includes(q));
  const key = {near: r => r.over ?? 1e9, best: r => r.best ?? 1e9, score: r => -(r.score ?? -1), hours: r => r.hours ?? 1e9, year: r => -(parseInt(r.year, 10) || -1e4), new: r => -Date.parse(r.since || 0) || 0}[V.pcSort];
  if(key) rows = rows.slice().sort((a, b) => key(a) - key(b));
  const sel = `<label class="kind">Sortieren <select data-sort="pc">${PC_SORTS.map(([v, l]) => `<option value="${v}"${V.pcSort === v ? " selected" : ""}>${l}</option>`).join("")}</select></label>`;
  const bar = `<div class="bar"><span class="sbox"><input type="search" id="q" placeholder="Titel suchen" aria-label="Titel suchen" value="${esc(V.q)}" data-in="q">${V.q ? `<button class="sx" data-act="qclear" title="Suche leeren (Esc)" aria-label="Suche leeren">×</button>` : ""}</span><span class="tools">${sel}</span></div>`;
  const src = {Server: "über den Teilen-Link", Lesezeichen: "per Lesezeichen", Datei: "aus einer Datei"}[pw.via] || "";
  const games = all.filter(r => !r.kind).length, info = all.filter(r => r.srcs?.length).length;
  const note = `<details class="gnote" ${foldAttr("pcnote", true)}><summary>${rows.length === all.length ? `${num(all.length)} Einträge ohne VR` : `${num(rows.length)} von ${num(all.length)} Einträgen`}</summary>
    <p class="hint">Gepflegt wird die Liste bei gg.deals; das Tool liest sie ${src}${pw.at ? `, zuletzt ${when(pw.at)}` : ""}, sucht die Steam-ID und holt die Preise über die gg.deals-API. ${num(pw.priced)} mit Preis${pw.noid ? `, ${num(pw.noid)} noch ohne Steam-ID (gesucht wird nach genau gleichem Namen)` : ""}${S.settings?.gg_key_set ? "" : ". Ohne gg.deals-Schlüssel gibt es keine Preise (Einstellungen, Konten)"}.
    Spielinfos wie in der Sammlung (Wertung, Spielzeit, Genre, Mehrspieler, Beschreibung) kommen von Steam und IGDB über die Steam-ID: ${info < games ? `${num(info)} von ${num(games)} Spielen haben sie schon, der Abgleich holt je Lauf weitere` : "alle Spiele haben sie"}${S.settings?.igdb_set ? "" : "; ohne IGDB-Schlüssel nur von Steam, ohne Spielzeit"}. Klick auf den Namen zeigt Einzelheiten.
    ${pw.kinds?.pack || pw.kinds?.dlc ? `Dazu ${[pw.kinds.pack && `${num(pw.kinds.pack)} Pakete`, pw.kinds.dlc && `${num(pw.kinds.dlc)} DLC`].filter(Boolean).join(" und ")}; für sie hat die gg.deals-API keinen Preis je Steam-App, der Link führt zur Seite bei gg.deals.` : ""}
    ${nVr ? `${num(nVr)} VR-Spiele der Liste stehen unter <button class="link" data-act="wsub" data-v="vr">VR</button>.` : ""} Violett „VR“: nur der Name nennt VR, der Abgleich prüft das bei Steam.</p></details>`;
  return bar + note + (rows.length ? pcTable(rows) : `<p class="hint">Kein Treffer.</p>`);
}
/* Tabelle der PC-Wünsche (0.8.11 mit Spielinfos), auch unter „Jetzt“. Ab 0.8.17 wie im eShopKompass: vorn der Preis jetzt
   (Link zu gg.deals, Händler, Keyshop und Tief im Tooltip) und der Abstand zum Tief („am Tief“ grün, sonst rot), dahinter die
   Spielinfos wie in der Sammlung (gSc, gGenres, gYear); der Name klappt Einzelheiten auf */
const PC_COLS = "minmax(160px,2fr) 76px 76px 62px minmax(0,1.2fr) 66px minmax(90px,.8fr) 44px";
function pcTable(rows){
  const head = `<div class="gr nph"><span>Spiel</span><span class="r" title="Günstigster Preis jetzt bei gg.deals, Händler oder Keyshop; Einzelheiten im Tooltip">Preis</span><span class="r" title="Abstand zum bisherigen Tief laut gg.deals">zum Tief</span><span class="r" title="Anteil positiver Steam-Rezensionen ab 50, sonst IGDB (grau und kursiv)">Wertung</span><span title="Von Steam und IGDB; violett: nur eine Quelle">Genre</span><span class="r" title="Laut IGDB: normal, sonst eilig">Spielzeit</span><span title="Laut Steam und IGDB, violett: nur eine Quelle; dahinter die höchste Spielerzahl laut IGDB, sonst Steam (violett)">Mehrspieler</span><span class="r" title="Erscheinungsjahr">Jahr</span></div>`;
  return `<div class="glist box pcw" style="--gcols:${PC_COLS}">${head}${rows.map(pcRow).join("")}</div>`;
}
function pcPriceTip(r){
  return [`Günstigster Preis: ${r.best_from || "gg.deals"}`, r.retail != null && `Händler ${eur(r.retail)}`, r.keyshops != null && `Keyshop ${eur(r.keyshops)}`,
    (r.retail_low != null || r.keyshops_low != null) && `Tief: ${[r.retail_low != null && `Händler ${eur(r.retail_low)}`, r.keyshops_low != null && `Keyshop ${eur(r.keyshops_low)}`].filter(Boolean).join(", ")}`,
    r.price_at && `Stand ${when(r.price_at)}`, "Klick öffnet die Angebote bei gg.deals"].filter(Boolean).join("\n");
}
function pcRow(r){
  const open = V.pwOpen === r.key, atLow = r.over != null && r.over <= 0.02;
  const cell = (l, v, cls) => `<span class="${cls || ""}${v ? "" : " nil"}" data-l="${l}">${v || G_NIL}</span>`;
  const hours = !r.hours ? "" : `<span title="${esc(`Laut IGDB${r.hours_all ? `; komplett ${hrs(r.hours_all)}` : ""}`)}">${hrs(r.hours)}</span>`;
  const price = r.best != null ? `${atLow ? `<span class="star" title="Am bisherigen Tief (höchstens 2 % darüber)">★</span>` : ""}${extLink(r.url, `<b>${eur(r.best)}</b>`, pcPriceTip(r))}`
    : `<span class="hint" title="${r.kind ? "Preis auf der Seite bei gg.deals" : r.appid ? "gg.deals nennt keinen Preis" : "Noch keine Steam-ID"}">${extLink(r.kind ? r.url : "", "–")}</span>`;
  const low = r.over == null ? "" : atLow ? `<span class="g-buy" title="${esc(`Höchstens 2 % über dem bisherigen Tief ${eur(r.low)}`)}">am Tief</span>`
    : `<span class="over" title="${esc(`${eur(r.best - r.low)} über dem bisherigen Tief ${eur(r.low)} (+${Math.round(r.over * 100)} %)`)}">+${eur(r.best - r.low)}</span>`;
  const pl = !r.players ? "" : `<span class="${r.pl_src === "IGDB" ? "" : "gxc"}" title="${r.pl_src === "IGDB" ? "Laut IGDB" : "Nur eine Quelle"}">bis ${r.players}</span>`;
  return `<div class="gr${open ? " open" : ""}"><span class="t"><button class="link g-n" data-act="pwopen" data-s="${esc(r.key)}" aria-expanded="${open}" title="${esc(r.name)} · Einzelheiten">${esc(r.name)}</button>${r.kind ? `<span class="b" title="${esc(PC_KIND[r.kind]?.[1] || "")}">${esc(PC_KIND[r.kind]?.[0] || r.kind)}</span>` : ""}${r.vr ? `<span class="b vrq" title="Nur ein Hinweis: der Name nennt VR">VR</span>` : ""}${r.owned ? `<span class="b warn" title="Steht in deiner Sammlung; bei gg.deals von der Wunschliste nehmen?">schon in der Sammlung</span>` : ""}${dropMark(r.drop)}${careMark(r.care)}</span>` +
    `<span class="r" data-l="Preis">${price}</span>` + cell("zum Tief", low, "r") +
    cell("Wertung", gSc(r) + (r.score_src === "Steam" ? trendMark(r.trend) : ""), "r") +
    `<span class="c-gen${r.genres?.length ? "" : " nil"}" data-l="Genre">${r.genres?.length ? gGenres(r, open) : G_NIL}</span>` +
    cell("Spielzeit", hours, "r") + cell("Mehrspieler", [r.mp?.length ? gMp(Object.assign({genres: []}, r)) : "", pl].filter(Boolean).join(" ")) + cell("Jahr", gYear(Object.assign({mp: [], genres: []}, r)), "r") + `</div>` + (open ? pcDetail(r) : "");
}
// Einzelheiten eines PC-Wunschs: was die Zeile nicht zeigt, rechts die Beschreibung, darunter Herkunft und Links
function pcDetail(r){
  const row = (l, v, tip) => v ? `<span class="fl">${l}</span><span class="fv"${tip ? ` title="${esc(tip)}"` : ""}>${v}</span>` : "";
  const g = Object.assign({mp: [], genres: []}, r);
  const steamTip = [r.rdesc && (RDESC[r.rdesc] || r.rdesc), r.reviews != null && `${num(r.reviews)} Rezensionen`].filter(Boolean).join(", ");
  const facts = row("Mehrspieler", g.mp.length ? gMp(g) : "") +
    row("Spieler", r.players ? `<span class="${r.pl_src === "IGDB" ? "" : "gxc"}">bis ${r.players}</span>` : "", r.pl_src === "IGDB" ? "Laut IGDB" : "Nur eine Quelle") +
    row("Erschienen", esc(r.sdate || r.year || ""), [r.dev && `Entwickler: ${r.dev}`, r.pub && r.pub !== r.dev && `Verlag: ${r.pub}`, r.sdate ? "Laut Steam" : r.year_src === "IGDB" ? "Laut IGDB" : ""].filter(Boolean).join("\n")) +
    row("Entwickler", esc(r.dev || "")) +
    row("Steam", r.reviews != null ? esc(steamTip) : "", "Steam-Rezensionen; eine Wertung gibt es ab 50") +
    row("Trend", trendText(r.trend)) +
    row("Update", r.care ? `${agoDays(r.care.date)}${CARE[r.care.state] ? ` <span class="hint">(${CARE[r.care.state]})</span>` : ""}` : "", r.care ? `Letztes Update laut Steam-Neuigkeiten am ${day(r.care.date)}` : "") +
    row("Preissturz", r.drop ? `${eur(r.best)} statt üblich ${eur(r.drop.usual)} (−${r.drop.pct} %)` : "", "Median der Preise der letzten Tage aus dem eigenen Verlauf") +
    row("IGDB Kritik", r.icrit != null ? gScore(r.icrit, "Kritiker-Wertung laut IGDB", "") : "") +
    row("Jetzt", [r.retail != null && `Händler ${eur(r.retail)}`, r.keyshops != null && `Keyshop ${eur(r.keyshops)}`].filter(Boolean).join(" · "), "Preise jetzt laut gg.deals") +
    row("Tief", [r.retail_low != null && `Händler ${eur(r.retail_low)}`, r.keyshops_low != null && `Keyshop ${eur(r.keyshops_low)}`].filter(Boolean).join(" · "), "Bisheriges Tief laut gg.deals");
  const dtip = r.desc_src === "IGDB" ? "Beschreibung laut IGDB, nur auf Englisch" : "Kurzbeschreibung laut Steam";
  const side = `<div class="gdm">${r.desc ? `<p class="gdesc${V.gDesc === r.key ? " full" : ""}" data-act="gdesc" data-s="${esc(r.key)}" title="${dtip}${V.gDesc === r.key ? "" : ". Klick zeigt alles"}">${esc(r.desc)}</p>` : `<span class="hint">${r.kind ? "Pakete und DLC bekommen keine Spielinfos." : r.appid ? "Noch keine Spielinfos; der Abgleich holt sie." : "Ohne Steam-ID gibt es keine Spielinfos."}</span>`}</div>`;
  const links = [r.url && `<a href="${esc(r.url)}" target="_blank" rel="noopener noreferrer">bei gg.deals</a>`, r.appid && `<a href="https://store.steampowered.com/app/${esc(r.appid)}/" target="_blank" rel="noopener noreferrer">bei Steam</a>`].filter(Boolean);
  const small = [r.since && `auf der Liste seit ${day(r.since)}`, r.srcs?.length && `Spielinfos von ${srcList(r)}`, r.price_at && `Preis von ${when(r.price_at)}`, ...links].filter(Boolean).join(" · ");
  return `<div class="gd" style="--dcols:minmax(180px,3fr) minmax(320px,5fr)"><div class="gdf">${facts}</div>${side}<p class="hint gds">${small}</p></div>`;
}
function vrWishView(){
  const sorts = [["name", "Name"], ["best", "Nah am Bestpreis"], ["sale", "Rabatt"], ["rating", "Wertung"], ["added", "Neu"]];
  let rows = S.wishlist.filter(r => match(r) && lfOk(r, ["cb", "sale", "best", "good"]));
  const k = {best: nearBest, sale: r => -Math.max(r.live.meta?.discount || 0, r.live.steam?.discount || 0), rating: byRating, added: byAdded}[V.sort];
  if(k) rows = rows.slice().sort((a, b) => k(a) - k(b));
  // Was du schon besitzt (Meta oder PC), steht in einer eigenen, zugeklappten Gruppe
  const open = rows.filter(r => !r.where), owned = rows.filter(r => r.where);
  const add = `<form class="bar addform" data-form="add"><input type="text" name="name" placeholder="Neuer Titel" aria-label="Neuer Titel" required>
    <input type="text" name="link" placeholder="Link zu VRDB, QuestStoreDB, Meta oder Steam (optional)" aria-label="Link zum Titel (optional)">
    <button class="primary">Hinzufügen</button></form>`;
  if(!S.wishlist.length) return add + `<p class="hint">Noch keine Wunschtitel. Importiere deine Vergleichstabelle unter Einstellungen oder trage oben einen Titel ein.</p>`;
  const ow = S.counts.owned_wish;
  const head = listBar({sorts, sort: V.sort, sortKey: "wish", filters: ["cb", "sale", "best", "good"],
    extra: `<button data-act="addopen" class="${V.add ? "on" : ""}" title="Titel von Hand hinzufügen">+ Titel</button>${ow ? foldAll : ""}`});
  // Hinweis auf „Wunschliste abgleichen“, solange es dort etwas zu tun gibt
  const L = S.lists || [], lc = k => L.filter(x => x.kind === k).length;
  const hint = L.length ? `<div class="banner">Abgleich mit deinen Wunschlisten: ${[lc("owned") && `${lc("owned")} schon gekauft`,
    lc("off") && `${lc("off")} im Laden noch gewünscht`, lc("missing") && `${lc("missing")} fehlen auf einer Laden-Wunschliste`, lc("table") && `${lc("table")} nur aus der Tabelle`].filter(Boolean).join(", ")}.
    <button class="link" data-act="golists">ansehen</button></div>` : "";
  return hint + (V.add ? add : "") + head +
    (!rows.length ? `<p class="hint">Kein Treffer.</p>` : !ow ? `<div class="list">${open.map(r => wishRow(r)).join("")}</div>`
      : grp("w-open", "Noch nicht im Besitz", open.length, `<div class="list">${open.map(r => wishRow(r)).join("")}</div>`) +
        grp("w-owned", `Schon im Besitz <span class="hint" title="Titel auf der Wunschliste, die du schon bei Meta oder am PC besitzt">(bei Meta oder am PC)</span>`, owned.length, `<div class="list">${owned.map(r => wishRow(r)).join("")}</div>`, true));
}
// Sortierschlüssel: wie nah der günstigere Shop am Bestpreis beider Läden liegt (1 = am Bestpreis)
function nearBest(r){
  const low = r.best_all?.best;
  const q = ["meta", "steam"].map(s => r.best?.[s] && r.live[s] ? r.live[s].price / (low || r.best[s].best) : null).filter(x => x != null);
  return q.length ? Math.min(...q) : 1e9;
}

/* Preise: zwei feste Felder, Meta links, Steam rechts (fehlt ein Laden, bleibt sein Feld grau).
   Je Feld Preis, Rabatt und darunter der Abstand zum Bestpreis beider Läden (Entscheidung
   22.10.2026): rot „+7 € über Bestpreis“ (jeder Aufpreis) oder gold „★ Bestpreis“;
   klein darunter der Tiefstpreis des Ladens selbst zum Vergleich. „≈“, wenn ein Bestpreis aus einer
   fremden Quelle stammt, solange der eigene Verlauf zu kurz ist. Der günstigere Laden bekommt einen
   grünen Rahmen und den Betrag (ab 1 €). */
const SHOP = {meta: "Meta", steam: "Steam"};
function bestFrom(b){
  return b.src ? `${b.src}${b.best_at ? ", " + day(b.best_at) : ""}` : `${day(b.best_at)}${b.full ? ", 24 Monate" : ", Verlauf seit " + day(b.since)}`;
}
function bestLine(v, b, A, shop){
  const own = b && !b.thin && b.best != null;
  if(!own && !A) return `<div class="bl hint" title="Der eigene Verlauf hat noch keine Preisänderung">Bestpreis noch offen</div>`;
  A = A || {best: b.best, shop, src: b.src, at: b.best_at};
  const ap = A.src ? " ≈" : "", other = A.shop !== shop;
  const tip = `Jetzt ${eur(v.price)}, Bestpreis beider Läden ${eur(A.best)} bei ${SHOP[A.shop]}${A.src ? " (" + A.src + ")" : ""}` +
    (own ? `; ${SHOP[shop]} selbst: ${eur(b.best)} (${bestFrom(b)})${b.usual != null ? `, übliches Angebot ${eur(b.usual)}` : ""}` : `; ${SHOP[shop]} selbst: noch offen`) +
    `, Normalpreis ${eur(v.base || v.price)}`;
  // Vergleich: der Tiefstpreis des Ladens selbst, wenn der Bestpreis aus dem anderen Laden kommt
  const cmp = !other ? "" : own ? `<div class="bl hint">${eur(Math.min(b.best, v.price))}${b.src ? " ≈" : ""} ${SHOP[shop]}-Tief${v.price <= b.best * 1.02 + 0.005 ? " (jetzt)" : ""}</div>`
    : `<div class="bl hint">${SHOP[shop]}-Tief noch offen</div>`;
  if(v.price <= A.best * 1.02 + 0.005) return `<div class="bl at" title="${esc(tip)}"><span class="star">★</span> Bestpreis${ap}</div>${cmp}`;
  // Jeder Aufpreis über dem Bestpreis ist rot (Entscheidung 26.10.2026); die Stufen „kaufen“ und
  // „gut“ entscheiden nur, was unter „Jetzt“ oben steht
  const over = v.price - A.best, rel = A.best > 0 ? Math.round(over / A.best * 100) : 0;
  return `<div class="bl" title="${esc(tip)}"><span class="over">+${eur(over)}</span> über Bestpreis</div>
    <div class="bl" title="${esc(tip)}">${eur(A.best)}${ap}${other ? " bei " + SHOP[A.shop] : ""} <span class="hint">(+${rel} %)</span>${own && !other && b.level === "usual" ? " · übliches Angebot" : ""}</div>${cmp}`;
}
// Preise sind Links (0.8.12, wie im eShopKompass): in den Laden, der Bestpreis zum Preisverlauf
const extLink = (url, inner, tip, cls) => url && safeUrl(url) ? `<a class="pl${cls ? " " + cls : ""}" href="${esc(url)}" target="_blank" rel="noopener noreferrer"${tip ? ` title="${esc(tip)}"` : ""}>${inner}</a>` : inner;
const linkOf = (r, label) => (r.links || []).find(l => l.label === label)?.url || "";
function shopCell(key, v, b, A, win, extra, url){
  const shop = SHOP[key];
  if(!v) return `<div class="shop none"><div class="sl">${shop}</div><div class="bl">kein Preis</div>${extra || ""}</div>`;
  const sale = v.discount ? ` <span class="b deal">−${v.discount} %${v.kind === "coupon" ? " Gutschein" : ""}</span>${v.until ? ` <span class="hint">${until(v.until)}</span>` : ""}` : "";
  const old = v.stale ? ` <span class="b warn" title="Älter als zwei Tage: Abruf prüfen">Stand ${ago(v.at)}</span>` : "";
  // Urteil wie im eShopKompass (0.6.0): grün „kaufen“ (bis 2 % oder 0,50 € über dem Bestpreis beider Läden),
  // grün umrandet „gut“ (bis 15 % oder 2 €); „warten“ ohne Marke
  const vd = b?.grade === "buy" ? ` <span class="vd buy" title="Höchstens 2 % oder 0,50 € über dem Bestpreis beider Läden">kaufen</span>`
    : b?.grade === "good" ? ` <span class="vd good" title="Höchstens 15 % oder 2 € über dem Bestpreis beider Läden">gut</span>` : "";
  return `<div class="shop${win ? " win" : ""}"><div class="sl">${shop}${vd}${sale}${old}</div>
    <div>${extLink(url, `<span class="price big">${eur(v.price)}</span>`, `${shop}: zum Spiel im Laden`)}${v.discount && v.base ? ` <s>${eur(v.base)}</s>` : ""}</div>
    ${bestLine(v, b, A, key)}${extra || ""}${win ? `<div class="cheap">${win}</div>` : ""}</div>`;
}
function shopsHtml(r){
  const L = r.live, B = r.best || {}, g = L.gg, pc = r.pc_best;
  if(!L.meta && !L.steam && !(g && g.retail != null)) return "";
  // Betrag gegenüber dem günstigsten PC-Angebot (Steam oder Händler bei gg.deals); unter 1 € kein Rahmen
  const gap = r.gap_now, big = gap != null && Math.abs(gap) >= 1;
  const metaWin = big && gap < 0 ? `${eur(-gap)} günstiger` : "";
  const pcWin = big && gap > 0 ? `${eur(gap)} günstiger${pc?.src === "gg.deals Keyshop" ? " im Keyshop" : pc?.src !== "Steam" ? " bei Händlern" : ""}` : "";
  // Günstigstes Angebot bei gg.deals (Händler oder Keyshop) unter Steam: als Zeile im Steam-Feld
  const gb = g ? [[g.retail, "Händler"], [g.keyshops, "Keyshop"]].filter(x => x[0] != null).sort((a, b) => a[0] - b[0])[0] : null;
  const deal = gb && (!L.steam || gb[0] < L.steam.price - 0.005)
    ? `<div class="bl" title="Günstigstes Angebot laut gg.deals, Händler und Keyshops">${gb[1]} ${extLink(g.url || linkOf(r, "gg.deals"), eur(gb[0]), "Angebote bei gg.deals")} <span class="hint">(gg.deals)</span></div>` : "";
  return `<div class="shops">${shopCell("meta", L.meta, B.meta, r.best_all, metaWin, "", linkOf(r, "Meta"))}${shopCell("steam", L.steam, B.steam, r.best_all, pcWin, deal, linkOf(r, "Steam"))}</div>`;
}
V.more = new Set();
// Was selten entscheidet, steht in der Klappe; ihre Zeile nennt, was drin ist: „Bestpreise · gg.deals · Tabelle · Links“
function moreHtml(r, extra){
  const g = r.live.gg, s = r.sheet, B = r.best || {}, out = [], has = [];
  for(const [k, shop] of [["meta", "Meta"], ["steam", "Steam"]]){
    const b = B[k];
    if(b && !b.thin && b.best != null) has.push("Bestpreise"), out.push(`<div class="small">${shop}: Bestpreis ${eur(b.best)}${b.src ? ` ≈ (${esc(b.src)}${b.best_at ? ", " + day(b.best_at) : ""})` : ` am ${day(b.best_at)}${b.full ? " (24 Monate)" : ` (Verlauf seit ${day(b.since)})`}`}${b.usual != null ? `, übliches Angebot ${eur(b.usual)}` : ""}</div>`);
  }
  if(g && (g.retail != null || g.keyshops != null)) has.push("gg.deals"), out.push(`<div class="small">gg.deals: ${[
    g.retail != null && "Händler " + eur(g.retail), g.keyshops != null && "Keyshop " + eur(g.keyshops),
    g.retail_low != null && "Allzeit-Tief Händler " + eur(g.retail_low), g.keyshops_low != null && "Keyshop " + eur(g.keyshops_low)].filter(Boolean).join(", ")}${g.stale ? ` <span class="b warn">Stand ${ago(g.at)}</span>` : ""}</div>`);
  const WS = {meta: "Meta", steam: "Steam", gg: "gg.deals", hand: "von Hand"};
  if(r.wish) out.push(`<div class="small">Wunsch aus: ${r.wish_src?.length ? r.wish_src.map(s => WS[s] || s).join(", ") : "nur der alten Tabelle"}</div>`);
  if(s && Object.keys(r.live).length) has.push("Tabelle"), out.push(`<div class="small">Tabelle, ${day(s.at)}: Meta ${eur(s.meta)}, Tief ${eur(s.meta_low)}, gg.deals ${eur(s.gg)}</div>`);
  out.push(`<div class="row2">${linksHtml(r)}</div>`);
  out.push(`<div class="row2"><button class="link" data-act="edit" data-k="${esc(r.key)}">bearbeiten</button>${extra || ""}</div>`);
  const sum = [...new Set(has), "Links", "bearbeiten"].join(" · ");
  return `<details class="more" data-more="${esc(r.key)}" ${V.more.has(r.key) ? "open" : ""}><summary>${sum}</summary>${out.join("")}</details>`;
}
// Ohne Abruf: die Werte aus deiner Tabelle, gekennzeichnet
function sheetHtml(r){
  const s = r.sheet;
  if(!s) return `<div class="shops"><div class="shop none"><div class="sl">Meta</div><div class="bl">kein Preis</div></div><div class="shop none"><div class="sl">Steam</div><div class="bl">kein Preis</div></div></div>`;
  return `<div class="facts" title="Aus deiner Tabelle übernommen, bis ein Abruf eigene Preise liefert">${fact("Tabelle", day(s.at))}
    ${fact("Meta", `<span class="price">${eur(s.meta)}</span>, Tief ${eur(s.meta_low)}`)}${fact("gg.deals", `<span class="price">${eur(s.gg)}</span>`)}
    ${r.gap != null ? fact("Differenz", `<span class="${r.gap >= 1 ? "over" : r.gap <= -1 ? "ok" : ""}">${r.gap > 0 ? "+" : ""}${eur(r.gap)}</span>`) : ""}</div>`;
}
/* Wo kaufen (0.8.15): Laden und Preisurteil im Kopf der Karte, die Gründe als Zeile darunter. Gründe für
   den gewählten Laden normal, die für den anderen grau; was nur aus der Recherche kommt, violett mit „≈“ */
const WB_SHOP = {meta: "Meta", steam: "Steam", egal: "Laden egal"};
const WB_GRADE = {buy: "kaufen", good: "gut", wait: "warten"};
function buyBadge(r){
  const b = r.buy;
  if(!b) return "";
  const tip = `Wo kaufen, aus dem Gemessenen: ${b.why.map(x => (x.shop === "meta" ? "Meta" : "Steam") + ": " + x.text).join("; ") || "nichts unterscheidet die Läden"}`
    + (b.grade ? `. Preis dort: ${WB_GRADE[b.grade]}` : "");
  return `<span class="vd wb ${b.grade || "wait"}" title="${esc(tip)}">${WB_SHOP[b.shop]}${b.grade ? (b.shop === "egal" ? ", " : " ") + WB_GRADE[b.grade] : ""}</span>`;
}
function buyHtml(r){
  const b = r.buy;
  if(!b || !b.why.length) return "";
  const one = x => x.guess ? `<span class="gxc" title="Aus der Recherche, zählt halb">≈ ${esc(x.text)}</span>` : esc(x.text);
  const part = k => {
    const xs = b.why.filter(x => x.shop === k);
    return xs.length ? `<span class="${b.shop !== "egal" && b.shop !== k ? "mut" : ""}">${k === "meta" ? "Meta" : "Steam"}: ${xs.map(one).join(", ")}</span>` : "";
  };
  const order = b.shop === "steam" ? ["steam", "meta"] : ["meta", "steam"];
  return `<div class="facts wbl">${fact("Wo", order.map(part).filter(Boolean).join(" · "), "Gründe je Laden; der mit mehr Gewicht gewinnt, bei Gleichstand ist es egal")}</div>`;
}
function wishRow(r){
  return `<div class="item wi"><div class="hd"><span class="nm">${esc(r.name)}</span>${buyBadge(r)}${badges(r)}</div>
    ${shopsHtml(r) || sheetHtml(r)}<div class="side">${buyHtml(r)}${factsHtml(r)}${opinionHtml(r)}
    ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}</div>
    ${moreHtml(r, `<button class="link" data-act="unwish" data-k="${esc(r.key)}" title="Von der Wunschliste nehmen; der Titel bleibt im Tool">nicht mehr wünschen</button>`)}</div>`;
}

/* ---------------------------------------------------------------- Sammlung
   Nach dem Vorbild der Ansicht „Spiele“ im eShopKompass (0.6.0): je Spiel eine Zeile mit Spalten, ein
   Klick auf einen Spaltenkopf sortiert, ein Klick auf den Namen klappt die Einzelheiten mit „Mein Stand“
   auf. Je System ein Reiter; VR (nach PC) sind deine VR-Titel bei Meta und am PC, bis 0.5.8 der Reiter
   „Bibliothek“. Die übrigen Spiele kommen aus dem Playnite-Export und der Retro-Liste (eigene Datei, beim
   ersten Öffnen geladen). Filter, Sortierung und Zufall laufen im Browser; der Zustand steht in der
   Adresse (#sammlung?…), so lässt sich eine Mischung als Lesezeichen merken. */
let C = null, cLoading = false;
const D0 = {sys: "PC", sw: "", how: [], hr: 0, usk: "", mp: [], min: 0, g: [], gop: "", st: "", sc: 0, old: 0, lang: "", me: "", cb: 0, vm: 0, wh: 0, vr: 0, q: "", sort: "score", seed: 0, mix: "", n: 100};
V.d = Object.assign({}, D0);
if(LIB_IN) V.d.sys = "VR";
V.gOpen = null;
// Alle aufklappen (0.7.2, wie im eShopKompass): jedes Spiel offen außer den einzeln zugeklappten; nicht gemerkt.
// Nur bei höchstens G_ALL Spielen in der Liste (Reiter, Filter oder Suche), sonst grau (0.7.4: 150 statt 100,
// damit etwa ein ganzes System wie 3DS aufgeht)
V.gAll = false;
V.gShut = new Set();
// Kurzbeschreibung: vier Zeilen, ein Klick zeigt alles (wie im eShopKompass)
V.gDesc = null;
const G_ALL = 150;
const D_SORTS = [["score", "Wertung"], ["gem", "Geheimtipp"], ["known", "Bekanntheit"], ["added", "Neu in der Sammlung"], ["year", "Erscheinungsjahr"], ["name", "Name"], ["random", "Zufall"]];
// Mischungen: ein Klick setzt Filter und Sortierung (alles andere zurück); pick: zeigt drei Vorschläge.
// vr: auch im Reiter VR sinnvoll
const MIXES = [
  ["surprise", "Überrasch mich", "Drei Spiele per Zufall aus dem, was die Filter gerade zeigen; gut bewertete und Geheimtipps kommen öfter", null, true],
  ["duo", "Koop zu zweit", "Koop-Spiele für zwei, die besten zuerst", {mp: ["coop"], min: 2}],
  ["couch", "Couch-Abend", "Lokal an einem Rechner: Couch-Koop oder Splitscreen", {mp: ["couch"]}],
  ["big", "Große Runde", "Mindestens vier Spieler", {min: 4}],
  ["gems", "Geheimtipps", "Gut bewertet und wenig bekannt (wenige Steam-Rezensionen); nur Spiele, deren Rezensionen schon abgerufen sind", {sc: 80, sort: "gem"}],
  ["old", "Gut, lange her", "Wertung ab 80, seit über zwei Jahren in der Sammlung, in zufälliger Folge", {sc: 80, old: 1, sort: "random"}],
  ["backlog", "Aus dem Backlog", "Was du dir zum Spielen vorgenommen hast, die besten zuerst; „Überrasch mich“ wählt dann daraus", {me: "backlog"}, true],
  ["wild", "Wilde Mischung", "Würfelt eine Mehrspieler-Art und ein Genre zusammen und zieht drei Vorschläge", null],
];
// Mein Stand (wie im eShopKompass): von Hand je Spiel, in data.json und damit in der Sicherung
const G_ST = [["backlog", "Backlog", "○", "Willst du spielen, noch nicht angefangen"], ["started", "angefangen", "▷", "Angefangen"],
  ["done", "durchgespielt", "✓", "Durchgespielt"]];
const G_STF = [["", "egal"], ["open", "nicht durchgespielt"], ["backlog", "Backlog"], ["started", "angefangen"], ["done", "durchgespielt"],
  ["fav", "Favoriten"], ["none", "ohne Stand"]];
// Switch-Spiele aus dem eShopKompass (0.7.3): Mein Stand von dort, hier nur lesend
const mine = g => g.eshop ? g.mine || {} : (S.marks || {})[g.key] || {};
const ESH = "Laut eShopKompass";
// Link auf das Spiel im eShopKompass, dort aufgeklappt (ab eShopKompass 1.7.18: #spiele?o=<slug>)
const eshUrl = g => `${C.eshop_link.replace(/\/+$/, "")}/#spiele?o=${encodeURIComponent(g.slug)}`;
const hrs = h => `${String(Math.round(h * 2) / 2).replace(".", ",")} h`;
const meOk = (m, f) => f === "open" ? m.s !== "done" : f === "fav" ? !!m.fav : f === "none" ? !m.s && !m.fav : m.s === f;
const mulberry = a => () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
const newSeed = () => 1 + Math.floor(Math.random() * 2147483646);

function findHash(){
  if(V.tab !== "find"){ if(/^#(sammlung|entdecken)/.test(location.hash)) history.replaceState(null, "", location.pathname + location.search); return; }
  const d = V.d, p = new URLSearchParams();
  for(const [k, v] of Object.entries(d)) if(k !== "n" && String(v) !== String(D0[k])) p.set(k, Array.isArray(v) ? v.join(",") : v);
  const h = "#sammlung" + (String(p) ? "?" + p : "");
  if(location.hash !== h) history.replaceState(null, "", location.pathname + location.search + h);
}
// Bis 0.5.8 hieß die Adresse #entdecken, alte Lesezeichen gelten weiter
function readFindHash(){
  if(!/^#(sammlung|entdecken)/.test(location.hash)) return;
  V.tab = "find";
  const p = new URLSearchParams(location.hash.split("?")[1] || ""), d = Object.assign({}, D0);
  for(const [k, v] of p){
    if(!(k in D0) || k === "n") continue;
    d[k] = Array.isArray(D0[k]) ? v.split(",").filter(Boolean) : typeof D0[k] === "number" ? (Number(v) || 0) : v;
  }
  V.d = d;
}
async function loadCollection(){
  if(cLoading) return;
  cLoading = true;
  try{ C = await api("/api/collection"); }catch(e){ C = {error: e.message, games: []}; }
  cLoading = false;
  if(V.tab === "find" && !document.querySelector("dialog[open]")) render();
}
/* Deine VR-Titel als Zeilen der Sammlung, System „VR“. Laden heißt hier: wo du ihn hast */
function vrStore(r){
  const pc = r.pc_label || "PC";
  return r.where === "beide" ? `Meta + ${pc}` : r.where === "meta" ? "Meta" : pc;
}
let GM = null;
function allGames(){
  if(!GM || GM.s !== S || GM.c !== C)
    GM = {s: S, c: C, list: ((C && C.games) || []).concat((S.library || []).map(r => ({key: "vr:" + r.key, lib: r, name: r.name, system: "VR",
      store: vrStore(r), guess: false, mp: [], players: 0, genres: [], score: r.rating?.score ?? null, reviews: r.rating?.steam?.n ?? null,
      year: "", added: r.added || "", dev: "", pub: "", rel: "", desc: "", gem: 0, url: "", wheel: r.wheel || null})))};
  return GM.list;
}
/* Genres in fester Reihenfolge, in jeder Zeile gleich (wie im eShopKompass): zuerst das in der Sammlung
   seltenere, weil es das Spiel genauer beschreibt; bei gleicher Häufigkeit das Alphabet; „Sonstiges“ ans Ende */
let GN = null;
function genreOrder(list){
  if(!GN || GN.c !== C){
    const n = {};
    for(const g of (C && C.games) || []) for(const x of g.genres) n[x] = (n[x] || 0) + 1;
    GN = {c: C, n};
  }
  const rank = x => x === "Sonstiges" ? 1e9 : GN.n[x] || 0;
  return list.slice().sort((a, b) => rank(a) - rank(b) || a.localeCompare(b, "de"));
}
// Sprache der Retro-Spiele: mit Deutsch, deutsche Fassung fehlt, ohne Deutsch (keine bekannt)
const LANG_FILTER = [["", "alle"], ["de", "mit Deutsch"], ["miss", "DE fehlt"], ["nde", "ohne Deutsch"]];
function langOk(g, f){
  const de = (g.langs || []).includes(g.eshop ? "german" : "De"), miss = g.de?.st === "missing";
  return f === "de" ? de : f === "miss" ? miss : f === "nde" ? !!(g.retro || g.eshop && g.langs?.length) && !de && !miss : true;
}
// „Alle“ heißt alle Systeme aus Playnite und der Retro-Liste; VR-Titel stehen nur unter VR, am PC
// meist ohnehin auch unter PC
// Familien (0.7.4): oben nur Alle, PC, VR und je Familie ein Reiter; die einzelnen Konsolen klappen rechts
// daneben heraus, sobald die Familie gewählt ist. Alles außer PlayStation und Nintendo steht unter „Weitere“
// (Entscheidung 27.10.2026). Eine Familie mit nur einem System steht als dieses System da
const FAMS = [["@ps", "PlayStation", n => /^PS/.test(n)], ["@nin", "Nintendo", n => NINTENDO.has(n)],
  ["@more", "Weitere", n => n !== "PC" && n !== "VR"]];
const famOf = n => (FAMS.find(f => f[2](n)) || [""])[0];
const famName = k => (FAMS.find(f => f[0] === k) || [k, k])[1];
const inSys = (g, sys) => sys ? (sys[0] === "@" ? famOf(g.system) === sys : g.system === sys) : g.system !== "VR";
function dFilter(d){
  const q = d.q.trim().toLowerCase(), cut = new Date(Date.now() - 730 * 864e5).toISOString().slice(0, 10);
  return allGames().filter(g => inSys(g, d.sys) && (!d.sw || (d.sw === "s1") === !!g.sw1) && kFilter(g, d) && d.mp.every(m => g.mp.includes(m))
    // Spielerzahl unbekannt: ein Mehrspieler-Spiel zählt als zwei
    && (!d.min || (g.players ? g.players >= d.min : d.min <= 2 && g.mp.includes("multi")))
    // mehrere Genres: eines davon genügt, mit gop „and“ alle
    && (!d.g.length || (d.gop === "and" ? d.g.every(x => g.genres.includes(x)) : d.g.some(x => g.genres.includes(x)))) && (!d.st || g.store === d.st) && (!d.sc || (g.score ?? -1) >= d.sc)
    && (!d.old || (g.added && g.added < cut)) && (!d.lang || langOk(g, d.lang)) && (!d.me || meOk(mine(g), d.me)) && (!d.cb || g.lib?.crossbuy === true) && (!d.vm || vrMod(g)) && (!d.wh || !!g.wheel) && (!d.vr || (g.vr && !g.vr_guess))
    && (!q || g.name.toLowerCase().includes(q) || g.dev.toLowerCase().includes(q) || (g.pub || "").toLowerCase().includes(q) || g.genres.some(x => x.toLowerCase().includes(q))
      || !!g.lib?.note?.toLowerCase().includes(q) || (g.own && [g.own.series, g.own.coll, g.own.genre, g.own.sub, g.fname].some(x => (x || "").toLowerCase().includes(q)))));
}
function dSort(rows, d, cols){
  if(d.sort === "random" && !V.sorts.find){
    const r = mulberry(d.seed || 1), a = rows.slice();
    for(let i = a.length - 1; i > 0; i--){ const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  }
  const by = {score: g => -(g.score ?? -1), gem: g => -g.gem, known: g => -(g.reviews ?? -1), added: g => g.added ? -Date.parse(g.added) : 0,
              year: g => -(Number(g.year) || 0)}[d.sort];
  const out = by ? rows.slice().sort((a, b) => by(a) - by(b) || a.name.localeCompare(b.name, "de")) : rows;
  return sortRows("find", out, Object.fromEntries([["title", g => g.name]].concat(cols.map(c => [c.k, c.sort]))));
}
/* Sortieren per Klick auf Spaltenköpfe (wie im eShopKompass): V.sorts[Tabelle] = {k, dir}. Erster Klick
   in Leserichtung (bei Wertungen und Zahlen, wo mehr besser ist, absteigend), zweiter andersherum,
   dritter zurück zur gewählten Sortierung. Leere Werte stehen immer am Ende. */
function sortRows(t, arr, keys){
  const s = V.sorts[t], f = s && keys[s.k];
  if(!f) return arr;
  const empty = v => v === null || v === undefined || v === "" || (typeof v === "number" && !isFinite(v));
  return arr.map((x, i) => [x, f(x), i]).sort((a, b) => {
    const ea = empty(a[1]), eb = empty(b[1]);
    if(ea || eb) return (ea - eb) || (a[2] - b[2]);
    const c = typeof a[1] === "string" ? a[1].localeCompare(b[1], "de") : a[1] - b[1];
    return c * s.dir || (a[2] - b[2]);
  }).map(x => x[0]);
}
function gTh(k, label, tip, cls = "", d0 = 1){
  const s = V.sorts.find, on = !!(s && s.k === k);
  return `<span class="sth ${on ? "on" : ""} ${cls}" role="columnheader" tabindex="0" data-act="tsort" data-t="find" data-k="${k}"${d0 < 0 ? ` data-d0="-1"` : ""} title="${esc(tip ? tip + " · " : "")}Klick sortiert"${on ? ` aria-sort="${s.dir > 0 ? "ascending" : "descending"}"` : ""}>${label}<span class="sa">${on ? (s.dir > 0 ? "▲" : "▼") : ""}</span></span>`;
}
// Drei Vorschläge, gewichtet: Wertung über 60 und Geheimtipp-Wert machen ein Spiel wahrscheinlicher
function dPick(rows, seed, k = 3){
  const r = mulberry(seed || 1), pool = rows.slice(), out = [];
  const w = g => 1 + Math.max(0, (g.score ?? 60) - 60) / 10 + g.gem * 4;
  while(out.length < k && pool.length){
    let x = r() * pool.reduce((s, g) => s + w(g), 0), i = 0;
    while(i < pool.length - 1 && (x -= w(pool[i])) > 0) i++;
    out.push(pool.splice(i, 1)[0]);
  }
  return out;
}
function setMix(k){
  const m = MIXES.find(x => x[0] === k);
  if(!m) return;
  if(k === "wild"){
    // würfeln, bis mindestens drei Spiele übrig bleiben
    const kinds = ["coop", "couch", "online", "lan", "", ""], r = mulberry(newSeed());
    for(let i = 0; i < 30; i++){
      const d = Object.assign({}, D0, {sys: V.d.sys, mp: [kinds[Math.floor(r() * kinds.length)]].filter(Boolean),
        g: [C.genres[Math.floor(r() * C.genres.length)]].filter(Boolean), sc: r() < .5 ? 70 : 0});
      if(dFilter(d).length >= 3 || i === 29){ V.d = d; break; }
    }
  } else if(m[3]) V.d = Object.assign({}, D0, m[3], {sys: V.d.sys});
  V.d.mix = k;
  V.d.seed = newSeed();
  V.d.n = D0.n;
  delete V.sorts.find;
}
const dLabel = d => [d.how.map(h => (K_HOW.find(x => x[0] === h) || [h, h])[1]).join(" + "), d.mp.map(m => C.mp_label[m] || m).join(" + "),
  d.hr && (d.hr > 0 ? `bis ${d.hr} h` : `ab ${-d.hr} h`), d.usk && `USK bis ${d.usk}`, d.min && `ab ${d.min} Spieler`, d.g.join(d.gop === "and" ? " und " : " oder "), d.st,
  d.sc && `Wertung ab ${d.sc}`, d.old && "über zwei Jahre in der Sammlung", d.me && (G_STF.find(x => x[0] === d.me) || ["", ""])[1],
  d.cb && "Crossbuy", d.vm && "VR per Mod", d.vr && "VR", d.wh && "SimRacing", d.lang && (LANG_FILTER.find(x => x[0] === d.lang) || ["", ""])[1], d.q && `„${d.q}“`].filter(Boolean).join(", ");

/* Zellen. Leer heißt grauer Strich; violett (.gxc): nur eine Quelle oder geschätzt, der Tooltip sagt woher */
const G_NIL = `<span class="hint">–</span>`;
// Wertung (wie im eShopKompass): fein gestuft von Rot über Gelb nach Grün, Skala 50 bis 95
const gScoreHue = v => Math.round(Math.max(0, Math.min(1, (v - 50) / 45)) * 125);
// Zusammenfassung der Steam-Rezensionen auf Deutsch, wie im Steam-Store
const RDESC = {"Overwhelmingly Positive": "Äußerst positiv", "Very Positive": "Sehr positiv", "Positive": "Positiv",
  "Mostly Positive": "Größtenteils positiv", "Mixed": "Ausgeglichen", "Mostly Negative": "Größtenteils negativ",
  "Negative": "Negativ", "Very Negative": "Sehr negativ", "Overwhelmingly Negative": "Äußerst negativ"};
const gScore = (v, tip, unit = " %") => v == null ? "" : `<span class="gsc" style="--sh:${gScoreHue(v)}" title="${esc(tip)}">${v}${unit}</span>`;
/* Trend und Pflege (0.8.18): ein Pfeil neben der Steam-Wertung, wenn die letzten 30 Tage mindestens 8 Punkte besser
   (grün) oder schlechter (rot) bewertet sind als insgesamt; die Zahlen im Tooltip. „ruht“: über ein Jahr ohne Update */
function trendTip(t){
  const span = t.src === "steam" ? "Letzte 30 Tage" : `Seit ${day(t.since)} (eigene Messung)`;
  return `${span}: ${t.recent} % positiv aus ${num(t.n)} Rezensionen, insgesamt ${t.all} %`;
}
const trendMark = t => !t || t.dir === "flat" ? "" : `<span class="tr ${t.dir}" title="${esc(trendTip(t))}">${t.dir === "up" ? "↗" : "↘"}</span>`;
const trendText = t => !t ? "" : `<span title="${esc(trendTip(t))}">${t.dir === "up" ? "steigend" : t.dir === "down" ? "fallend" : "gleichbleibend"}${trendMark(t) ? " " + trendMark(t) : ""} <span class="hint">(${t.recent} % gegen ${t.all} %)</span></span>`;
const CARE = {fresh: "gepflegt", ok: "", stale: "ruht"};
const careMark = c => c?.state === "stale" ? `<span class="b care" title="${esc(`Letztes Update laut Steam-Neuigkeiten am ${day(c.date)}, über ein Jahr her`)}">ruht</span>` : "";
const dropMark = d => !d ? "" : `<span class="b go" title="${esc(`${d.pct} % unter dem üblichen Preis von ${eur(d.usual)} (Median der letzten ${d.days} Tage, eigener Preisverlauf aus gg.deals)`)}">Preissturz</span>`;
/* Genres als Blasen, Farbton nach Verwandtschaft (wie im eShopKompass): Action und Kampf rot, Tempo
   orange bis gelbgrün, Plattformer gelb, ruhiges Leben grün, Erkunden türkis bis cyan, Denken blau bis
   indigo, Gesellig rosa bis magenta, Sonstiges grau. Violett bleibt frei, es heißt „prüfen“ */
const G_HUE = {"Action": 4, "Kampfspiel": 352, "Prügelspiel": 352, "Shooter": 14, "Arcade": 26, "Rennspiel": 36, "Rennen": 36, "Sport": 66,
  "Plattformer": 48, "Simulation": 128, "Aufbau": 118, "Survival": 150, "Roguelike": 158, "Abenteuer": 172, "Metroidvania": 182, "Rollenspiel": 194,
  "Puzzle": 212, "Lernen": 204, "Strategie": 232, "Brettspiel": 242, "Kartenspiel": 250, "Party": 330, "Musik": 316, "Rhythmus": 316, "Horror": 0,
  "Visual Novel": 300, "Point & Click": 168, "Stealth": 222, "Sandbox": 140, "Karten und Brett": 246, "Quiz": 222, "Casual": 100};
const gTag = n => { const h = G_HUE[n]; return `<span class="chip gg" style="${h === undefined ? "--gh:0;--gg-s:0%;--gg-ts:0%" : `--gh:${h}`}">${esc(n)}</span>`; };
/* Herkunft (0.6.1, wie im eShopKompass): kein Zeichen. Mit Steam-Details abgeglichen (src „steam“) gilt,
   was Playnite und Steam beide sagen; sagt es nur eine Quelle, ist der Wert dezent violett (.gxc) und der
   Tooltip nennt die Quellen. Ohne Steam-Details gilt alles nur laut Playnite */
// 0.8.0: IGDB ist eine weitere Quelle; g.srcs nennt alle, die zu dem Spiel etwas sagen
const chk = g => g.src === "steam" || !!g.ig;
const srcList = g => (g.srcs || ["Playnite"]).join(", ").replace(/, ([^,]+)$/, " und $1");
const one = (g, list, x) => chk(g) && !(list || []).includes(x);
// In der Zeile einzeilig: was nicht passt, zählt „+n“ (siehe fitTags); in den Einzelheiten alle
function gGenres(g, all){
  if(!g.genres.length) return "";
  const only = g.genres.filter(x => one(g, g.gc, x));
  const tip = chk(g) ? (only.length ? `Nur eine Quelle (${srcList(g)}): ${only.join(", ")}; die übrigen nennen zwei` : `${srcList(g)} einig`) : g.eshop ? ESH
    : g.retro ? (g.own?.genre ? `Zuerst dein Genre aus der Ordner-Liste (${g.own.genre})${g.lgen?.length ? `; libretro: ${g.lgen.join(", ")}` : ""}` : g.lgen?.length ? "Laut libretro-database" : "") : "Laut Playnite";
  return `<span class="gtags${all ? "" : " fit"}" title="${esc(tip)}">${genreOrder(g.genres).map(gTag).join("")}</span>`;
}
function gMp(g){
  const ms = g.mp.filter(m => m !== "multi" || g.mp.length === 1);
  return ms.map(m => `<span${one(g, g.mpc, m) ? ` class="gxc" title="Nur eine Quelle (${esc(srcList(g))})"` : ""}>${esc(C?.mp_label?.[m] || m)}</span>`).join(", ");
}
function gYear(g){
  if(!g.year) return "";
  const tip = g.src === "steam" ? (g.year_ok ? "Playnite und Steam einig" : `Playnite ${g.year === g.syear ? "ohne Jahr" : "und Steam verschieden"}${g.syear ? `, Steam ${g.syear}` : ""}`)
    : g.ig ? (g.year_src === "IGDB" ? "Laut IGDB" : g.year_ok ? `${g.retro ? "libretro" : "Playnite"} und IGDB einig` : `${g.retro ? "libretro" : "Playnite"} ${g.year}, IGDB ${g.iyear || "ohne Jahr"}`)
    : g.retro ? (g.year_src === "libretro" ? "Laut libretro-database" : "") : g.eshop ? ESH : "Laut Playnite";
  // Wie im eShopKompass: Erscheinen, Entwickler und Verlag im Tooltip (0.6.2), die Suche findet sie
  const who = [g.rel?.length > 4 && `Erschienen ${/^\d{4}-\d{2}$/.test(g.rel) ? "im" : "am"} ${relDay(g.rel)}`, g.dev && `Entwickler: ${g.dev}`, g.pub && g.pub !== g.dev && `Verlag: ${g.pub}`].filter(Boolean);
  return `<span class="${chk(g) && !g.year_ok ? "gxc" : ""}" title="${esc(who.concat(tip ? [tip] : []).join("\n"))}">${esc(g.year)}</span>`;
}
const vrMod = g => !!(g.vrmod?.length || g.nexus?.vr?.length || g.vorpx);
// Wertung nach Rangfolge (0.8.0); eine Ersatzquelle grau und kursiv wie OpenCritic im eShopKompass
function gSc(g){
  if(g.score == null) return "";
  if(g.eshop) return gScore(g.score, `${g.score_src}, laut eShopKompass`, "");
  if(g.score_src === "Steam") return gScore(g.score, `Anteil positiver Steam-Rezensionen (${g.reviews != null ? num(g.reviews) : "–"})`);
  const tip = `${g.score_src === "IGDB Kritik" ? `IGDB: Kritiker-Wertung aus ${g.score_n} Tests` : `IGDB: Gesamtwertung aus ${num(g.score_n)} Bewertungen, keine Kritiker-Wertung`}${g.reviews != null && g.reviews < 50 ? `; Steam: erst ${num(g.reviews)} Rezensionen` : ""}`;
  return g.score_alt ? `<span class="galt" title="${esc(tip)}">${g.score}</span>` : gScore(g.score, tip, "");
}
// Launcher bei PC-Spielen (laut Playnite; nur vermutet: violett), sonst das System, solange der Reiter es nicht schon sagt
function gSrc(g){
  if(g.system !== "PC") return V.d.sys && V.d.sys[0] !== "@" ? "" : esc(g.system);
  return g.store ? `<span class="${g.guess ? "gxc" : ""}" title="${g.guess ? "Launcher nur vermutet (Kennung ohne Angabe des Launchers)" : chk(g) ? "Von Steam bestätigt" : "Laut Playnite"}">${esc(g.store)}</span>` : "";
}
// Sprache eines Retro-Spiels: Deutsch vor Englisch vor Japanisch, violett wenn nur aus der Region geschätzt
const LANG_SHORT = {De: "DE", En: "EN", Ja: "JP"};
function langBadge(g){
  if(!g.langs?.length) return "";
  // Switch (0.7.3): Sprachen laut Nintendo Europa, englische Namen
  if(g.eshop) return g.langs.includes("german") ? `<span title="Laut Nintendo Europa: Deutsch und ${g.langs.length - 1} weitere">DE</span>` : `<span class="gno" title="Laut Nintendo Europa ohne Deutsch: ${esc(g.langs.join(", "))}">ohne DE</span>`;
  const l = ["De", "En", "Ja"].find(x => g.langs.includes(x)) || g.langs[0];
  return `<span class="${g.lang_guess ? "gxc" : ""}" title="Sprachen ${g.de?.langs ? `laut No-Intro (über den Produktcode: ${esc(g.de.rel)})` : g.lang_dat ? "laut No-Intro (deine Datei steht genau so in der Fassungsliste)" : "laut Dateiname"}: ${esc(g.langs.join(", "))}${g.lang_guess ? " (nur aus der Region geschätzt)" : ""}${g.de?.st === "none" ? "; eine deutsche Fassung ist nicht bekannt" : ""}">${esc(LANG_SHORT[l] || l.toUpperCase())}</span>`;
}
const FASS_SHORT = {quest: "Quest besser", pc: "PC besser", gleich: "gleichwertig"};
const MP_SHORT = {lebendig: "lebendig", ruhig: "ruhig", tot: "tot", keiner: "keiner"};
const short = s => s.replace(/^vor /, "").replace(" Tagen", " T.").replace(" Monaten", " Mon.").replace(" Jahren", " J.");
/* Spalten je Reiter: eine Spalte erscheint nur, wenn ein Spiel im Reiter dafür einen Wert hat. d0 -1:
   erster Klick absteigend (mehr ist besser) */
const COLS = [
  {k: "own", l: "Besitz", w: "112px", vr: true, tip: "Wo du den Titel hast", cell: g => esc(g.store), sort: g => g.store},
  {k: "cb", l: "Crossbuy", w: "70px", vr: true, tip: "Gilt der Meta-Kauf auch am PC? Herkunft im Tooltip", d0: -1,
    cell: g => { const r = g.lib; if(r.crossbuy == null) return ""; const s = r.crossbuy_src, m = s === "Tabelle" ? " T" : "";
      return `<span class="${r.crossbuy ? "ok" : ""}${r.crossbuy_other || s === "Recherche" ? " ux" : ""}" title="${esc((r.crossbuy ? "Crossbuy" : "ohne Crossbuy") + (CB_FROM[s] ? ` (${CB_FROM[s]})` : "") + (r.crossbuy_other ? `; widerspricht: ${r.crossbuy_other}` : ""))}">${r.crossbuy ? "ja" : "nein"}${m}</span>`; },
    sort: g => g.lib.crossbuy == null ? null : +g.lib.crossbuy},
  {k: "rmeta", l: "Meta", w: "62px", cls: "r", vr: true, tip: "Wertung im Meta Store: Anteil 4 und 5 Sterne (VRDB), sonst aus dem Sternschnitt (Tooltip)", d0: -1,
    cell: g => { const m = g.lib.rating?.meta; if(!m) return ""; const v = m.pos ?? Math.round(m.stars * 20);
      return gScore(v, `Meta Store: ${m.pos != null ? "Anteil 4 und 5 Sterne (laut VRDB)" : "Sterne × 20 (QuestStoreDB)"}, ${String(m.stars).replace(".", ",")} von 5${m.n ? `, ${num(m.n)} Bewertungen` : ""}`); },
    sort: g => { const m = g.lib.rating?.meta; return m ? m.pos ?? Math.round(m.stars * 20) : null; }},
  {k: "rsteam", l: "Steam", w: "62px", cls: "r", vr: true, tip: "Anteil positiver Steam-Rezensionen", d0: -1,
    cell: g => { const s = g.lib.rating?.steam; return s?.pct != null ? gScore(s.pct, `Anteil positiver Steam-Rezensionen (${num(s.n)})`) + trendMark(s.trend) : s ? `<span class="hint" title="Eine Wertung gibt es ab 50 Rezensionen">${num(s.n)} R.</span>` : ""; },
    sort: g => g.lib.rating?.steam?.pct ?? null},
  {k: "play", l: "Spieler", w: "62px", cls: "r", vr: true, tip: "Steam-Spieler gerade eben; Spitze im Tooltip", d0: -1,
    cell: g => { const p = g.lib.measured?.players; return p && p.now != null ? `<span title="${esc(`Gerade eben (${when(p.at)}); Spitze ${num(p.peak || p.now)} seit ${day(p.since)}`)}">${num(p.now)}</span>` : ""; },
    sort: g => g.lib.measured?.players?.now ?? null},
  {k: "upd", l: "Update", w: "64px", cls: "r", vr: true, tip: "Letztes Steam-Update laut Entwickler",
    cell: g => { const u = g.lib.measured?.update; return u ? `<span class="${u.care?.state === "stale" ? "hint" : ""}" title="${esc(`${day(u.date)}: ${u.title}${u.care?.state === "stale" ? "\nÜber ein Jahr ohne Update" : ""}`)}">${short(agoDays(u.date))}</span>` : ""; },
    sort: g => g.lib.measured?.update ? -Date.parse(g.lib.measured.update.date) : null},
  {k: "op", l: "Recherche", w: "minmax(0,1fr)", vr: true, tip: "Aus Foren und Tests zusammengetragen, nicht geprüft (violett)",
    cell: g => { const o = g.lib.opinion; if(!o) return ""; const t = [o.fassung && FASS_SHORT[o.fassung], o.mehrspieler && "MP " + MP_SHORT[o.mehrspieler]].filter(Boolean).join(" · ");
      return `<span class="ux" title="Recherche aus Foren und Tests, nicht geprüft${o.stand ? ", " + esc(o.stand) : ""}">${esc(t || "Meinungen")}</span>`; },
    sort: g => g.lib.opinion?.fassung || null},
  {k: "pl", l: "Spieler", w: "52px", cls: "r", tip: "Höchste Spielerzahl online oder an einem Gerät laut IGDB, sonst Playnite (violett)", d0: -1,
    cell: g => !g.players ? "" : `<span class="${g.ig && g.pl_src !== "IGDB" ? "gxc" : ""}" title="${g.pl_src === "IGDB" ? `Laut IGDB${g.pl_ok ? " und libretro" : ""}` : g.pl_src === "libretro" ? `Laut libretro-database${g.ig ? ", IGDB nennt keine Zahl" : ""}` : g.ig ? "Nur laut Playnite, IGDB nennt keine Zahl" : "Laut Playnite"}">bis ${g.players}</span>`, sort: g => g.players || null},
  {k: "mp", l: "Mehrspieler", w: "minmax(90px,.7fr)", tip: "Laut Playnite, bei PC-Spielen mit Steam abgeglichen; violett: nur eine Quelle", cell: gMp, sort: g => g.mp.length || null, d0: -1},
  {k: "sc", l: "Wertung", w: "70px", cls: "r", tip: "PC: Anteil positiver Steam-Rezensionen ab 50, sonst IGDB (grau und kursiv). Konsolen und Retro: IGDB-Kritiken, sonst IGDB gesamt (grau und kursiv). Switch: Metacritic, sonst OpenCritic", d0: -1,
    cell: gSc, sort: g => g.score},
  {k: "hours", l: "Spielzeit", w: "70px", cls: "r", tip: "IGDB: normal, sonst eilig; Switch: HowLongToBeat über den eShopKompass", sort: g => g.hours || null,
    cell: g => !g.hours ? "" : g.hours_src === "IGDB" ? `<span title="${esc(`Laut IGDB${g.hours_all ? `; komplett ${hrs(g.hours_all)}` : ""}${g.hours_n ? ` (${g.hours_n} Angaben)` : ""}`)}">${hrs(g.hours)}</span>` : hrs(g.hours)},
  {k: "rev", l: "Rezensionen", w: "98px", cls: "r", tip: "Wie bekannt: Zahl der Steam-Rezensionen", d0: -1, cell: g => g.reviews != null ? num(g.reviews) : "", sort: g => g.reviews},
  {k: "lang", l: "Sprache", w: "58px", tip: "Laut Dateiname; violett: nur aus der Region geschätzt", cell: langBadge, sort: g => g.langs?.includes("De") ? 0 : g.langs?.length ? 1 : null},
  {k: "genre", l: "Genre", w: "minmax(0,1fr)", tip: "Laut Playnite, bei PC-Spielen mit Steam abgeglichen", cell: gGenres, sort: g => g.genres[0] || null},
  {k: "year", l: "Jahr", w: "44px", cls: "r", d0: -1, cell: gYear, sort: g => g.year || null},
  {k: "store", l: "Launcher", w: "92px", tip: "PC: Launcher laut Playnite (violett: nur vermutet); Konsolen: das System", cell: gSrc, sort: g => g.system !== "PC" ? g.system : g.store || null},
];
/* Reihenfolge (0.8.19, Entscheidung 28.10.2026): links, wonach du entscheidest (Wertung, Genre, Spielzeit, Mehrspieler),
   rechts das Nachschlagen (Jahr, Rezensionen, Launcher); Retro mit der Sprache vorn. Reiter VR: Besitz, Wertungen, Spieler
   und Update vorn, Crossbuy und Recherche rechts */
const COL_ORDER = ["own", "rmeta", "rsteam", "play", "upd", "cb", "op", "lang", "sc", "genre", "hours", "mp", "pl", "year", "rev", "store"];
COLS.sort((a, b) => COL_ORDER.indexOf(a.k) - COL_ORDER.indexOf(b.k));
/* Switch-Spiele (0.7.5, Entscheidung 27.10.2026): Spalten, Marken und Einzelheiten 1:1 wie „Spiele“ im
   eShopKompass, aus der Zeile, die er unter kv mitgibt (ab eShopKompass 1.7.17). Violett heißt wie dort:
   Nintendo nennt etwas anderes als DekuDeals (Tooltip); grau und kursiv: OpenCritic statt Metacritic */
const kOn = g => !!(g.eshop && g.kv && Object.keys(g.kv).length);
// Spielweisen wie im eShopKompass: mehrere gewählt heißt, alle müssen passen
const K_HOW = [["couch", "An einer Konsole (ab 2)", "Mehrere Spieler an einer Konsole: Couch, Splitscreen, geteilte Joy-Con"],
  ["local", "Lokal drahtlos", "Mehrere Konsolen im selben Raum"], ["online", "Online", "Über das Internet, mit Mitgliedschaft"],
  ["coop", "Koop", "Miteinander statt gegeneinander: laut IGDB, sonst kennt HowLongToBeat eine Koop-Spielzeit"],
  ["coopl", "Koop an einer Konsole", "Laut IGDB Koop lokal"], ["coopo", "Koop online", "Laut IGDB Koop online"],
  ["gs", "GameShare", "Laut Nintendos Liste mit GameShare: Freunde spielen mit, ohne das Spiel zu haben"],
  ["handheld", "Handheld", "Unterwegs spielbar"], ["tv", "TV", "Am Fernseher spielbar"]];
const kAge = k => { const a = parseInt(k.usk ?? k.pegi, 10); return isNaN(a) ? null : a; };
// Filter nur für Switch-Spiele mit der Zeile aus dem eShopKompass (Spielweise, Spielzeit, USK); andere fallen dann heraus
function kFilter(g, d){
  if(!d.how.length && !d.hr && d.usk === "") return true;
  if(!kOn(g)) return false;
  const k = g.kv, pl = x => kPl(g, x) || 0;
  for(const h of d.how){
    if(h === "couch" && pl("offline") < Math.max(2, d.min)) return false;
    if((h === "local" || h === "online") && pl(h) < Math.max(2, d.min)) return false;
    if(h === "coop" && !k.coop) return false;
    if(h === "coopl" && !k.coop?.local) return false;
    if(h === "coopo" && !k.coop?.online) return false;
    if(h === "gs" && !k.gs) return false;
    if((h === "handheld" || h === "tv") && !(k.modes || []).some(m => m.n === h)) return false;
  }
  if(d.usk !== "" && !(kAge(k) !== null && kAge(k) <= Number(d.usk))) return false;
  if(d.hr > 0 && !(k.hours && k.hours <= d.hr)) return false;
  if(d.hr < 0 && !(k.hours && k.hours >= -d.hr)) return false;
  return true;
}
const kHours = h => h == null ? "" : h < 1 ? "unter 1 h" : h < 10 ? `${String(Math.round(h * 2) / 2).replace(".", ",")} h` : `${Math.round(h)} h`;
const kRange = v => esc(!v ? "ja" : v[0] === v[1] ? String(v[1]) : `${v[0]}–${v[1]}`);
const kVal = (v, tip, bad) => `<span class="${bad ? "gxc" : ""}" title="${esc(tip)}">${v}</span>`;
const kPl = (g, k) => { const p = (g.kv.players || {})[k]; return p ? (p.v ? p.v[1] : 2) : null; };
const K_PL = {offline: "an einer Konsole", local: "lokal drahtlos", online: "online"};
const K_HLTB = {main: "Story", extra: "mit Nebenaufgaben", complete: "insgesamt", solo: "allein", coop: "Koop", vs: "gegeneinander", all: "alle Spielweisen"};
const K_MODE = {tv: "TV", tabletop: "Tisch", handheld: "Handheld"};
const K_LANG = {german: "Deutsch", english: "Englisch", french: "Französisch", italian: "Italienisch", spanish: "Spanisch", dutch: "Niederländisch",
  portuguese: "Portugiesisch", russian: "Russisch", japanese: "Japanisch", korean: "Koreanisch", chinese: "Chinesisch", polish: "Polnisch"};
const kLangs = l => l.map(x => K_LANG[x] || x).join(", ");
function kPlayers(g, k){
  const p = (g.kv.players || {})[k];
  if(!p) return "";
  const tip = (p.ok ? `${K_PL[k]}: DekuDeals und Nintendo einig` : p.alt ? `${K_PL[k]}: DekuDeals ${kRange(p.v)}, Nintendo ${kRange(p.alt)}`
    : p.src === "Nintendo" ? `${K_PL[k]}: nur laut Nintendo` : `${K_PL[k]}: nur laut DekuDeals`) +
    (k === "online" && g.kv.paid_online ? ". Braucht die Online-Mitgliedschaft (Nintendo)" : "");
  return kVal(kRange(p.v), tip, !!p.alt);
}
function kCoopTip(c){
  if(!c) return "";
  if(c.src !== "IGDB") return "Nur ein Hinweis: HowLongToBeat kennt eine Koop-Spielzeit";
  const n = v => v === true ? "" : ` bis ${v}`;
  return "Koop laut IGDB: " + ([c.local && `an einer Konsole${n(c.local)}`, c.online && `online${n(c.online)}`, c.split && "geteilter Bildschirm"].filter(Boolean).join(", ") || "ja, ohne Einzelheiten");
}
function kCoop(g){
  const c = g.kv.coop;
  if(!c) return "";
  return `<span title="${esc(kCoopTip(c))}">${c.local && c.online ? "beides" : c.local ? "lokal" : c.online ? "online" : "ja"}</span>`;
}
function kScore(g){
  const k = g.kv, more = [k.mcu != null && `Metacritic-Nutzer ${String(k.mcu).replace(".", ",")}`, k.oc != null && `OpenCritic ${k.oc}`].filter(Boolean).join(", ");
  if(k.mc != null) return `<span class="gsc" style="--sh:${gScoreHue(k.mc)}" title="${esc(`Metacritic ${k.mc}${more ? `; ${more}` : ""} (über DekuDeals)`)}">${esc(k.mc)}</span>`;
  if(k.oc != null) return `<span class="galt" title="${esc(`Keine Metacritic-Wertung. OpenCritic ${k.oc} (über DekuDeals)`)}">${esc(k.oc)}</span>`;
  return "";
}
function kYear(g){
  const k = g.kv;
  if(!k.year) return "";
  const tip = [k.year_ok ? "DekuDeals und Nintendo einig" : k.year_alt ? `DekuDeals ${k.year}, Nintendo ${k.year_alt} (Erscheinen je Region verschieden)` : "Nur eine Quelle",
    k.developer && `Entwickler: ${k.developer}`, k.publisher && `Verlag: ${k.publisher}`].filter(Boolean).join("\n");
  return kVal(esc(k.year), tip, !!k.year_alt);
}
const kHltbTip = g => "HowLongToBeat (über DekuDeals): " + Object.entries(g.kv.hltb || {}).map(([a, b]) => `${K_HLTB[a] || a} ${kHours(b)}`).join(", ");
/* „aus: …“ kurz wie dort: was das Paket vom Spielnamen unterscheidet („Golf - Ultimate Edition“ wird
   „Ultimate Edition“); Pakete mit „+“ oder „&“ bleiben ganz, der volle Name steht im Tooltip */
function kPackShort(title, pack){
  if(/\s[+&]\s/.test(pack)) return pack;
  const w = t => String(t).split(/\s+/), k = x => x.toLowerCase().normalize("NFKD").replace(/[\u0300-\u036f]/g, "");
  const a = w(title), b = w(pack);
  let i = 0; while(i < a.length && i < b.length && k(a[i]) === k(b[i])) i++;
  let j = 0; while(j < a.length - i && j < b.length - i && k(a[a.length - 1 - j]) === k(b[b.length - 1 - j])) j++;
  const out = b.slice(j >= 2 ? 0 : i, b.length - (j >= 2 ? j : 0)).join(" ").replace(/^[\s:&+–—-]+|[\s:&+–—-]+$/g, "");
  return out && out.length < pack.length ? out : pack;
}
// Marken hinter dem Namen wie dort: Switch 2, fehlende Spielmodi, GameShare, ohne Deutsch, „aus: Paket“
function kBadges(g){
  const k = g.kv, b = [];
  if(k.s2 && k.s2 !== "edition") b.push(`<span class="lgt de" title="${k.s2 === "upgrade" ? "Mit Upgrade-Paket für die Switch 2, das du hast" : "Spiel für die Switch 2"}">${k.s2 === "upgrade" ? "S2-Upgrade" : "Switch 2"}</span>`);
  const ms = (k.modes || []).map(m => m.n), miss = ["tv", "tabletop", "handheld"].filter(m => !ms.includes(m));
  if(ms.length && miss.length) b.push(`<span class="lgt de" title="${esc(`Spielbar: ${ms.map(m => K_MODE[m]).join(", ")}. Nicht: ${miss.map(m => K_MODE[m]).join(", ")}`)}">${miss.length === 1 ? `ohne ${K_MODE[miss[0]]}` : `nur ${ms.map(m => K_MODE[m]).join(", ")}`}</span>`);
  if(k.gs) b.push(`<span class="lgt gsh" title="${esc(`GameShare laut Nintendo: ${[k.gs.local && "lokal", k.gs.online && "online über GameChat"].filter(Boolean).join(" und ")}. Freunde spielen mit, ohne das Spiel zu haben`)}">GameShare</span>`);
  if(g.langs?.length && !g.langs.includes("german")) b.push(`<span class="lgt no" title="${esc("Laut Nintendo Europa ohne Deutsch. Sprachen: " + kLangs(g.langs))}">ohne Deutsch</span>`);
  if(k.via) b.push(`<small class="hint gvia" title="${esc("Hast du im Paket " + k.via)}">aus: ${esc(kPackShort(g.name, String(k.via)))}</small>`);
  return b.join("");
}
const K_COLS = [
  {k: "koff", l: "Konsole", w: "68px", cls: "c-pl", tip: "Spieler an einer Konsole (Couch, Splitscreen)", d0: -1, cell: g => kPlayers(g, "offline"), sort: g => kPl(g, "offline")},
  {k: "kloc", l: "Lokal", w: "48px", cls: "c-pl", tip: "Spieler mit mehreren Konsolen im selben Raum", d0: -1, cell: g => kPlayers(g, "local"), sort: g => kPl(g, "local")},
  {k: "kon", l: "Online", w: "52px", cls: "c-pl", tip: "Spieler online", d0: -1, cell: g => kPlayers(g, "online"), sort: g => kPl(g, "online")},
  {k: "kcoop", l: "Koop", w: "50px", cls: "c-pl", tip: "Laut IGDB: lokal, online oder beides; „ja“: nur ein Hinweis von HowLongToBeat", d0: -1, cell: kCoop,
    sort: g => g.kv.coop ? (g.kv.coop.local && g.kv.coop.online ? 3 : g.kv.coop.local || g.kv.coop.online ? 2 : 1) : null},
  {k: "kmc", l: "Metacritic", w: "86px", cls: "r", tip: "Grau und kursiv: keine Metacritic-Wertung, dafür OpenCritic", d0: -1, cell: kScore, sort: g => g.kv.mc ?? g.kv.oc ?? null},
  {k: "khours", l: "Spielzeit", w: "66px", cls: "r", tip: "HowLongToBeat: Story, sonst allein", cell: g => g.kv.hours ? `<span title="${esc(kHltbTip(g))}">${kHours(g.kv.hours)}</span>` : "", sort: g => g.kv.hours ?? null},
  {k: "genre", l: "Genre", w: "minmax(0,1fr)", tip: "Von Nintendo, sonst DekuDeals", cell: gGenres, sort: g => g.genres[0] || null},
  {k: "kyear", l: "Jahr", w: "42px", cls: "r", d0: -1, cell: kYear, sort: g => g.kv.year || null}];
// Einzelheiten wie dort: Wertung, Spielzeit, Erschienen, USK, Spieler-Widersprüche, Koop, GameShare, Online;
// rechts Mein Stand (setzt du im eShopKompass), darunter klein Sprachen, Größe, Kaufdatum, Paket und Links
function kDetail(g, side){
  const k = g.kv;
  const row = (l, v, tip) => v ? `<span class="fl">${l}</span><span class="fv"${tip ? ` title="${esc(tip)}"` : ""}>${v}</span>` : "";
  const n1 = v => String(v).replace(".", ",");
  const sc = (v, x = v) => `<span class="gsc" style="--sh:${gScoreHue(x)}">${esc(v)}</span>`;
  const score = [k.mc != null && `Metacritic ${sc(k.mc)}`, k.mcu != null && `Nutzer ${sc(n1(k.mcu), k.mcu * 10)}`, k.oc != null && `OpenCritic ${sc(k.oc)}`].filter(Boolean).join(" · ");
  const hltb = Object.entries(k.hltb || {}).map(([a, b]) => `${esc(K_HLTB[a] || a)} ${kHours(Number(b))}`).join(" · ");
  const who = [k.developer && `Entwickler: ${k.developer}`, k.publisher && `Verlag: ${k.publisher}${k.pub_alt ? ` (Nintendo: ${k.pub_alt})` : ""}`].filter(Boolean).join("\n");
  const rel = k.released ? `${esc(k.released.length > 4 ? day(k.released) : k.released)}${k.year_alt ? ` <span class="gxc">(Nintendo: ${esc(k.year_alt)})</span>` : ""}` : "";
  const age = k.usk ? `<span class="${["16", "18"].includes(k.usk) ? "usk" + k.usk : ""}">${esc(k.usk)}</span>` : k.pegi ? `<span title="Keine USK-Angabe">PEGI ${esc(k.pegi)}</span>` : "";
  const odd = ["offline", "local", "online"].filter(x => (k.players || {})[x]?.alt)
    .map(x => `${K_PL[x]} <span class="gxc">DekuDeals ${kRange(k.players[x].v)}, Nintendo ${kRange(k.players[x].alt)}</span>`).join(" · ");
  const facts = row("Wertung", score) + row("Spielzeit", hltb, "HowLongToBeat, über DekuDeals") +
    row("Erschienen", rel, who) + row("USK", age, [k.usk && `USK ${k.usk}`, k.pegi && `PEGI ${k.pegi}`].filter(Boolean).join(", ")) +
    (odd ? row("Spieler", odd, "DekuDeals und Nintendo nennen verschiedene Zahlen") : "") +
    (k.coop?.src === "IGDB" ? row("Koop", esc(kCoopTip(k.coop).replace("Koop laut IGDB: ", "")), "IGDB") : "") +
    (k.gs ? row("GameShare", [k.gs.local && "lokal", k.gs.online && "online über GameChat"].filter(Boolean).join(", "), "Laut Nintendos Liste der hervorgehobenen GameShare-Spiele") : "") +
    (k.paid_online ? row("Online", "mit Mitgliedschaft", "Laut Nintendo braucht das Online-Spiel die Nintendo Switch Online-Mitgliedschaft") : "");
  const langs = g.langs?.length ? `<span title="${esc("Sprachen laut Nintendo Europa: " + kLangs(g.langs))}">${g.langs.includes("german") ? `Deutsch${g.langs.length > 1 ? ` und ${g.langs.length - 1} weitere Sprache${g.langs.length > 2 ? "n" : ""}` : ""}` : `<span class="gno">ohne Deutsch</span>`}</span>` : "";
  const pk = k.pack ? `aus ${esc(k.pack.title)}${k.pack.filled?.length ? " (Angaben teils vom Paket)" : ""}` : "";
  const ed = k.ed ? `<span title="${esc("Du hast das Upgrade-Paket: Spieler, Spielzeit und Größe von der Seite der Switch-2-Edition" + (Object.keys(k.ed.diff || {}).length ? ". Die Switch-1-Seite nennt anderes bei: " + Object.keys(k.ed.diff).join(", ") : ""))}">Angaben der Switch-2-Edition</span>` : "";
  const deku = `<a href="https://www.dekudeals.com/items/${encodeURIComponent(g.slug)}" target="_blank" rel="noopener noreferrer">DekuDeals</a>${k.nin ? ", von Nintendo geprüft" : k.read ? ", noch nicht von Nintendo geprüft" : ", Seite noch nicht gelesen"}`;
  const small = [langs, k.size_gb && `${esc(n1(k.size_gb))} GB`, g.added && `gekauft am ${day(g.added)}`, pk, ed, deku,
    `laut eShopKompass${C.eshop_at ? `, gelesen ${day(C.eshop_at)}` : ""}`].filter(Boolean).join(" · ");
  return `<div class="gd"><div class="gdf">${facts}</div>${side}<p class="hint gds">${small}</p></div>`;
}
// Nur Switch-Spiele mit der Zeile aus dem eShopKompass: dessen Spalten (0.7.5)
const colsFor = (d, rows) => rows.length && rows.every(kOn) ? K_COLS : COLS.filter(c => (d.sys === "VR") === !!c.vr && (!c.only || c.only(d)) && rows.some(g => c.cell(g)));
/* Marken hinter dem Namen, knapp: Mein Stand, VR, Geheimtipp, Retro (DE fehlt, Homebrew, Hack, nicht mehr
   in der Liste), bei VR-Titeln Wunsch, Bundle und was zu prüfen ist */
const GEM_MIN = 0.4;
function gBadges(g){
  const b = [], m = mine(g), st = G_ST.find(x => x[0] === m.s);
  if(st || m.fav) b.push(`<span class="gme">${st ? `<span class="gst ${m.s}" title="Mein Stand: ${st[1]}">${st[2]}</span>` : ""}${m.fav ? `<span class="gfav" title="Favorit">★</span>` : ""}</span>`);
  if(g.lib){
    const r = g.lib;
    if(r.wish) b.push(`<span class="b" title="Steht auch auf der Wunschliste">Wunsch</span>`);
    if(r.bundle) b.push(`<span class="b" title="Paket aus mehreren Spielen">Bundle</span>`);
    b.push(wheelBadge(r.wheel));
    if(r.steam_appid && !r.steam_sure) b.push(`<span class="b warn" title="${esc(r.steam_doubt ? "Steam-ID passt wohl nicht: " + r.steam_doubt : "Steam-ID nur nach dem Namen zugeordnet")}">Steam-ID prüfen</span>`);
    return b.join("");
  }
  if(kOn(g)) return b.join("") + kBadges(g);
  // VR am PC (0.8.7): Steam, VR-Titel im Tool oder VR-Prüfung im Store; nennt nur der Name VR, ist es ein Hinweis (ab 0.8.20 türkis gestrichelt)
  if(g.vr) b.push(g.vr_guess ? `<span class="b vrq" title="Nur ein Hinweis: der Name nennt VR, Steam und das Tool sagen nichts dazu">VR</span>`
    : `<span class="b vrb" title="${esc(g.from_vr ? `Dein VR-Titel (${g.store}); Playnite kennt ihn nicht` : `VR laut ${g.vr_src || "Steam"}`)}">VR</span>`);
  // VR per Mod (0.8.1): PCGamingWiki „hackable“ gilt; nur Nexus-Mods mit VR im Namen oder vorpX ist ein Hinweis (gestrichelt)
  else if(g.vrmod?.length) b.push(`<span class="b vrb" title="${esc(`Laut PCGamingWiki per Mod: ${g.vrmod.join(", ")}${g.vorpx ? "; auch mit vorpX" : ""}`)}">VR per Mod</span>`);
  else if(vrMod(g)) b.push(`<span class="b vrq" title="${esc(["Nur ein Hinweis, nicht geprüft", g.nexus?.vr?.length && `Nexus Mods: ${g.nexus.vr.map(m => m.name).join(", ")}`, g.vorpx && "PCGamingWiki: geht mit vorpX"].filter(Boolean).join("\n"))}">VR-Mod</span>`);
  // Sim-Racing (0.8.3): in der Liste der Rennsimulationen bestätigt; nur Steam-Schlagwörter sind ein Hinweis (gestrichelt)
  b.push(wheelBadge(g.wheel));
  // Ab 0.8.12 erst ab 0,4 (vorher 0,2: das traf zu viele Spiele, um noch ein Tipp zu sein); heißt etwa 90 % positiv
  // bei bis zu 100 Rezensionen oder 95 % bei bis zu 400
  if(g.gem >= GEM_MIN) b.push(`<span class="b gemb" title="Geheimtipp-Wert ${String(g.gem).replace(".", ",")} von 1: sehr gute Wertung, wenig bekannt (Steam-Rezensionen)">Geheimtipp</span>`);
  if(g.retro){
    if(g.de?.st === "missing") b.push(`<span class="b warn" title="Es gab eine Fassung mit Deutsch: ${esc(g.de.alt)}${g.de.guess ? " (Deutsch nur aus der Region geschätzt)" : ""}; gefunden über ${{code: "den Produktcode", retool: "die Retool-Liste", name: "den gleichen Namen", alias: "den von dir bestätigten ähnlichen Namen"}[g.de.via] || "die Fassungsliste"}">DE fehlt</span>`);
    if(g.flags.includes("homebrew")) b.push(`<span class="b">Homebrew</span>`);
    if(g.flags.includes("hack")) b.push(`<span class="b">Hack</span>`);
    if(g.gone) b.push(`<span class="b warn" title="Stand in der letzten Retro-Liste nicht mehr">nicht mehr in der Liste</span>`);
  }
  return b.join("");
}
/* Liste herunterladen und Titel kopieren (0.8.7): genau die gefilterte und sortierte Liste mit den gezeigten
   Spalten; aufgeklappte Spiele bekommen ihre Einzelheiten als letzte Spalte */
let G_SHOWN = null;
const plain = h => { const e = document.createElement("div"); e.innerHTML = h || ""; return (e.textContent || "").replace(/\s+/g, " ").trim(); };
// Einzelheiten als Text: „Angabe: Wert“ je Zeile der linken Seite, dann Beschreibung und Herkunft; Mein Stand hat eine eigene Spalte
function detailText(g){
  const e = document.createElement("div");
  e.innerHTML = gDetail(g);
  e.querySelectorAll(".gdm .fl, .gmark, .gmk").forEach(x => x.remove());
  const out = [...e.querySelectorAll(".gdf .fl, .gdv .fl")].map(l => `${l.textContent.trim()}: ${plain(l.nextElementSibling?.innerHTML)}`);
  for(const x of e.querySelectorAll(".gdesc, .gds")) out.push(plain(x.innerHTML));
  return out.filter(Boolean).join(" | ");
}
function gExport(){
  const {rows, cols, sys} = G_SHOWN || {rows: [], cols: []};
  const cell = v => /[";\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
  const open = rows.some(g => V.gAll ? !V.gShut.has(g.key) : V.gOpen === g.key);
  const stand = g => { const m = mine(g), st = G_ST.find(x => x[0] === m.s); return [st && st[1], m.fav && "Favorit"].filter(Boolean).join(", "); };
  const lines = [["Spiel", ...cols.map(c => c.l), "Mein Stand", ...(open ? ["Einzelheiten"] : [])].map(cell).join(";")];
  for(const g of rows){
    const det = open && (V.gAll ? !V.gShut.has(g.key) : V.gOpen === g.key) ? detailText(g) : "";
    lines.push([g.name, ...cols.map(c => plain(c.k === "genre" ? (g.genres || []).join(", ") : c.cell(g))), stand(g), ...(open ? [det] : [])].map(x => cell(String(x ?? ""))).join(";"));
  }
  const name = `sammlung-${(sys ? (sys[0] === "@" ? famName(sys) : sys) : "alle").toLowerCase().replace(/[^a-z0-9]+/g, "-")}.csv`;
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["\ufeff" + lines.join("\r\n")], {type: "text/csv;charset=utf-8"}));
  a.download = name; document.body.appendChild(a); a.click(); a.remove();
  toast(`${num(rows.length)} Spiele als ${name}`);
}
function gRow(g, cols, pick){
  const open = (V.gAll ? !V.gShut.has(g.key) : V.gOpen === g.key) && !pick;
  return `<div class="gr${open ? " open" : ""}"><span class="t"><button class="link g-n" data-act="gopen" data-s="${esc(g.key)}" aria-expanded="${open}" title="${esc(g.name)} · Einzelheiten">${esc(g.name)}</button>${gBadges(g)}</span>` +
    cols.map(c => { const v = c.k === "genre" && open ? gGenres(g, true) : c.cell(g); return `<span class="${c.cls || ""}${c.k === "genre" || c.k === "op" ? " c-gen" : ""}${v ? "" : " nil"}" data-l="${c.l}">${v || G_NIL}</span>`; }).join("") + `</div>` + (open ? gDetail(g) : "");
}
/* Einzelheiten (wie im eShopKompass): links die Angaben untereinander, rechts Mein Stand, darunter klein
   Herkunft und Links. Bei VR-Titeln dieselben Fakten, Recherche und Klappe wie in der Wunschliste */
function gDetail(g){
  const row = (l, v, tip) => v ? `<span class="fl">${l}</span><span class="fv"${tip ? ` title="${esc(tip)}"` : ""}>${v}</span>` : "";
  const m = mine(g);
  const marks = `<span class="seg gmark">${G_ST.map(([k, l, ic, tip]) => `<button data-act="gmark" data-s="${esc(g.key)}" data-k="s" data-v="${m.s === k ? "" : k}" class="${m.s === k ? "on" : ""}" title="${esc(m.s === k ? "Zurücknehmen" : tip)}"><span class="gst ${k}">${ic}</span> ${l}</button>`).join("")}</span><span class="seg gmark"><button data-act="gmark" data-s="${esc(g.key)}" data-k="fav" data-v="${m.fav ? "" : "1"}" class="${m.fav ? "on" : ""}" title="${m.fav ? "Kein Favorit mehr" : "Als Favorit merken"}"><span class="gfav">${m.fav ? "★" : "☆"}</span> Favorit</button></span>`;
  // Switch (0.7.3): Mein Stand setzt du im eShopKompass, hier steht er nur
  const st = G_ST.find(x => x[0] === m.s);
  const shown = g.eshop ? `<span class="gmk hint">${st || m.fav ? [st && `<span class="gst ${m.s}">${st[2]}</span> ${st[1]}`, m.fav && `<span class="gfav">★</span> Favorit`].filter(Boolean).join(" · ") : "noch keiner"}; ändern im ${C.eshop_link ? `<a class="eshl" href="${esc(eshUrl(g))}" target="_blank" rel="noopener noreferrer" title="Öffnet das Spiel im eShopKompass"><span class="brand">eShop</span>Kompass</a>` : "eShopKompass"}</span>` : `<span class="gmk">${marks}</span>`;
  // Kurzbeschreibung (0.7.1, Steam auf Deutsch; Switch von Nintendo Europa) unter Mein Stand
  const dtip = g.eshop ? (g.desc_lang === "en" ? "Beschreibung von Nintendo Europa, nur auf Englisch" : "Beschreibung von Nintendo Europa") : g.desc_src === "IGDB" ? "Beschreibung laut IGDB, nur auf Englisch" : g.desc_src === "libretro" ? "Beschreibung laut libretro-database, nur auf Englisch" : "Kurzbeschreibung laut Steam";
  const side = `<div class="gdm"><span class="fl">Mein Stand</span>${shown}${g.desc ? `<p class="gdesc${V.gDesc === g.key ? " full" : ""}" data-act="gdesc" data-s="${esc(g.key)}" title="${dtip}${V.gDesc === g.key ? "" : ". Klick zeigt alles"}">${esc(g.desc)}</p>` : ""}</div>`;
  if(g.lib){
    const r = g.lib;
    return `<div class="gd vrd"><div class="gdv">${badges(r)}${factsHtml(r)}${opinionHtml(r)}${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}${moreHtml(r)}</div>${side}</div>`;
  }
  if(kOn(g)) return kDetail(g, side);
  if(g.eshop){
    // Wie „Spiele“ im eShopKompass (vor eShopKompass 1.7.17, ohne kv): Wertung, Spielzeit, Erschienen (Firmen im Tooltip), USK, Sprachen
    const de = g.langs.includes("german");
    const facts = row("Wertung", g.score != null ? `${esc(g.score_src)} ${gScore(g.score, g.score_src, "")}` : "") +
      row("Spielzeit", g.hours ? hrs(g.hours) : "", "HowLongToBeat: Story, sonst allein") +
      row("Erschienen", g.rel?.length > 4 ? day(g.rel) : "", [g.dev && `Entwickler: ${g.dev}`, g.pub && g.pub !== g.dev && `Verlag: ${g.pub}`].filter(Boolean).join("\n")) +
      row("USK", esc(g.usk)) +
      row("Sprachen", !g.langs.length ? "" : de ? `Deutsch${g.langs.length > 1 ? ` und ${g.langs.length - 1} weitere Sprache${g.langs.length > 2 ? "n" : ""}` : ""}` : `<span class="gno">ohne Deutsch</span>`, "Laut Nintendo Europa");
    const link = C.eshop_link ? `<a href="${esc(eshUrl(g))}" target="_blank" rel="noopener noreferrer">im eShopKompass</a>` : "";
    const small = [g.added && `gekauft am ${day(g.added)}`, `laut eShopKompass${C.eshop_at ? `, gelesen ${day(C.eshop_at)}` : ""}`, link].filter(Boolean).join(" · ");
    return `<div class="gd"><div class="gdf">${facts}</div>${side}<p class="hint gds">${small}</p></div>`;
  }
  const files = g.retro ? [g.files > 1 ? `${g.files} Dateien` : "", g.regions?.length ? g.regions.join(", ") : "", g.size ? mb(g.size) : g.own?.mb ? `${num(g.own.mb)} MB laut deiner Liste` : ""].filter(Boolean).join(", ") : "";
  // Deine Ordner-Liste (0.8.8): Ordner, Reihe; ein anderer Titel im Dateinamen; was andere Quellen zum Genre sagen
  const o = g.own || {};
  const ownRows = !g.retro ? "" : row("Dein Ordner", esc([o.genre, o.sub].filter(Boolean).join(" › ") + (o.folder && o.folder !== [o.genre, o.sub].filter(Boolean).join("\\") ? ` (Ordner ${o.folder})` : "")), "Aus deiner Ordner-Liste") +
    row("Reihe", esc([o.series, o.coll].filter(Boolean).join(", ")), "Reihe und Sammelreihe aus deiner Ordner-Liste") +
    row("Status", esc(o.status || ""), "Aus deiner Ordner-Liste") +
    row("Dateiname", g.fname ? esc(g.fname) : "", "Titel laut Dateiname (No-Intro); es gilt deiner aus der Ordner-Liste") +
    row("Genre anders", g.own_diff ? `<span class="gxc">${g.own_diff.map(d => `${esc(d.src)}: ${esc(d.other)}`).join(" · ")}</span>` : "", "Widerspricht deinem Genre; unter Einstellungen, Zu erledigen bestätigst du deins");
  // Nur, was die Zeile nicht schon zeigt (0.6.2): Spieler, Genre, Jahr und Launcher stehen in den Spalten.
  // Dazu wie im eShopKompass (0.7.1): Wertung aus weiteren Quellen, genaues Erscheinen, Sprachen
  // Wertung wie im eShopKompass (0.7.2): Zahlen statt Steams Worten, Steam in Prozent, Metacritic auf 100
  const steamTip = [g.rdesc && (RDESC[g.rdesc] || g.rdesc), g.reviews != null && `${num(g.reviews)} Rezensionen`].filter(Boolean).join(", ");
  // Die Zeile zeigt die Wertung schon; hier nur, wenn eine weitere Quelle etwas sagt (Metacritic, IGDB neben Steam)
  const score = !(g.mc != null || g.icrit != null) ? "" : [g.score != null && g.score_src === "Steam" && `Steam ${gScore(g.score, `Anteil positiver Steam-Rezensionen${steamTip ? ": " + steamTip : ""}`)}`,
    g.mc != null && `Metacritic ${gScore(g.mc, "Metacritic laut Steam", "")}`,
    g.icrit != null && `IGDB Kritik ${gScore(g.icrit, "Kritiker-Wertung laut IGDB", "")}`].filter(Boolean).join(" · ");
  const date = g.sdate && !/^\d{4}$/.test(g.sdate) ? g.sdate : relDay(g.rel);
  const who = [g.dev && `Entwickler: ${g.dev}`, g.pub && g.pub !== g.dev && `Verlag: ${g.pub}`].filter(Boolean).join("\n");
  const langs = g.sde == null ? "" : g.sde ? `Deutsch${g.slangs > 1 ? ` und ${g.slangs - 1} weitere Sprache${g.slangs > 2 ? "n" : ""}` : ""}` : `<span class="gno">ohne Deutsch</span>${g.slangs ? ` (${g.slangs} Sprache${g.slangs > 1 ? "n" : ""})` : ""}`;
  const facts = row("Wertung", score) + row("Erschienen", esc(date), who) + row("Sprachen", langs, "Laut Steam") + row("Sprachen", g.langs?.length > 1 ? `<span class="${g.lang_guess ? "gxc" : ""}">${esc(g.langs.join(", "))}</span>` : "", g.lang_guess ? "Nur aus der Region geschätzt" : g.de?.langs ? `Laut No-Intro über den Produktcode: ${g.de.rel}` : "Laut Dateiname") +
    row("VR per Mod", vrModHtml(g)) + row("Nexus Mods", nexusHtml(g)) + row("Sim-Racing", wheelHtml(g)) +
    row("Gesucht", g.de?.st === "missing" ? esc(g.de.alt) : "", "Die Fassung mit Deutsch laut No-Intro, Redump oder Retool") + row("Dateien", esc(files), "Regionen, Fassungen oder Discs desselben Spiels") + ownRows;
  const src = [g.from_vr ? `dein VR-Titel im Tool (${esc(g.store)}), Playnite kennt ihn nicht${g.src === "steam" ? "; Steam-Details" : ""}` : g.retro ? `System laut Retro-Liste${S.imports.retro?.at ? ` vom ${day(S.imports.retro.at)}` : ""}` : g.src === "steam" ? "Playnite, mit Steam abgeglichen (Steam-Details)" : g.system === "PC" ? "Playnite, noch nicht mit Steam abgeglichen" : "laut Playnite",
    g.own && "deine Ordner-Liste", g.lname && `libretro-database (dort „${esc(g.lname)}“)`,
    g.ig ? `IGDB${g.iname ? ` (dort „${esc(g.iname)}“)` : ""}` : ""].filter(Boolean).join(", ");
  const small = [g.added && `hinzugefügt am ${day(g.added)}`, src, safeUrl(g.url) && `<a href="${esc(g.url)}" target="_blank" rel="noopener noreferrer">Seite im Launcher</a>`].filter(Boolean).join(" · ");
  return `<div class="gd"><div class="gdf">${facts}</div>${side}<p class="hint gds">${small}</p></div>`;
}
// Sim-Racing (0.8.3, Listen ab 0.8.5): bestätigt in einer Liste der Rennspiele; nur Steam-Schlagwörter: gestrichelt; ab 0.8.20 beide umrandet, ohne „?“
const WHEEL_SRC = {"SimHub": ["https://www.simhubdash.com/supported-games/", "SimHub unterstützt das Spiel (Liste der Rennspiele)"],
  "Simucube-Forum": ["https://community.granitedevices.com/t/5645", "Rennsimulationen für Direktantriebe mit Force Feedback; was dort läuft, läuft auch mit Simagic"]};
const WHEEL_LIST = "Liste der Rennspiele (SimHub, Simucube-Forum)";
function wheelBadge(w){
  if(!w) return "";
  const tags = w.tags.length ? `Steam-Schlagwörter: ${w.tags.join(", ")}` : "";
  return w.src.length ? `<span class="b simb" title="${esc([`Laut ${w.src.join(" und ")}`, tags].filter(Boolean).join("\n"))}">SimRacing</span>`
    : `<span class="b simq" title="${esc(`Nur ein Hinweis, nicht geprüft\n${tags}`)}">SimRacing</span>`;
}
function wheelHtml(g){
  const w = g.wheel;
  if(!w) return "";
  return [...w.src.map(s => `<a href="${WHEEL_SRC[s]?.[0] || ""}" target="_blank" rel="noopener noreferrer" title="${esc(WHEEL_SRC[s]?.[1] || "")}">${esc(s)}</a>`),
    w.tags.length && `<span class="${w.src.length ? "" : "gxc"}" title="Steam-Schlagwörter${w.src.length ? "" : ", nur ein Hinweis"}">${esc(w.tags.join(", "))}</span>`].filter(Boolean).join(" · ");
}
// VR per Mod und Nexus Mods in den Einzelheiten (0.8.1), mit Links
const nxLink = (g, m) => `<a href="https://www.nexusmods.com/${encodeURIComponent(g.nexus.dom)}/mods/${Number(m.id)}" target="_blank" rel="noopener noreferrer" title="${num(m.end)} Empfehlungen">${esc(m.name)}</a>`;
function vrModHtml(g){
  const p = [g.vrmod?.length && `<span title="Laut PCGamingWiki: „hackable“">${esc(g.vrmod.join(", "))}</span>`, g.vorpx && "vorpX",
    g.nexus?.vr?.length && `<span class="gxc" title="Mods mit VR im Namen, nicht geprüft">${g.nexus.vr.map(m => nxLink(g, m)).join(", ")}</span>`].filter(Boolean);
  return p.join(" · ");
}
function nexusHtml(g){
  const n = g.nexus;
  if(!n?.dom) return "";
  return `<a href="https://www.nexusmods.com/games/${encodeURIComponent(n.dom)}" target="_blank" rel="noopener noreferrer">${num(n.n)} Mods</a>${n.top?.length ? `, beliebt: ${n.top.map(m => nxLink(g, m)).join(", ")}` : ""}`;
}
/* Genres in der Zeile einzeilig (0.6.1): so viele Blasen, wie mit „+n“ dahinter in die Spalte passen;
   alle stehen in den Einzelheiten */
function fitTags(){
  // Erst alles lesen, dann alles schreiben (0.8.14): sonst rechnet der Browser je Blase das Layout neu
  const ts = [...document.querySelectorAll(".gr .gtags.fit")];
  if(!ts.length) return;
  for(const t of ts){ t.querySelector(".gmore")?.remove(); for(const c of t.children) c.hidden = false; }
  const probe = document.createElement("span");
  probe.className = "chip gmore";
  probe.textContent = "+9 weitere";
  ts[0].appendChild(probe);
  const moreW = probe.getBoundingClientRect().width, gap = 4;
  const plan = ts.map(t => {
    const cs = [...t.children].filter(c => c !== probe);
    if(cs.length < 2) return null;
    const box = t.getBoundingClientRect(), rs = cs.map(c => c.getBoundingClientRect());
    if(rs[rs.length - 1].top === rs[0].top) return null;
    let n = cs.length - 1;
    while(n > 1 && (rs[n - 1].top !== rs[0].top || rs[n - 1].right - box.left + gap + moreW > box.width)) n--;
    return [t, cs, n];
  });
  probe.remove();
  for(const p of plan){
    if(!p) continue;
    const [t, cs, n] = p, more = document.createElement("span");
    cs.slice(n).forEach(c => { c.hidden = true; });
    more.className = "chip gmore";
    more.textContent = `+${cs.length - n} weitere`;
    more.title = cs.slice(n).map(c => c.textContent).join(", ");
    t.appendChild(more);
  }
}
addEventListener("resize", () => { if(V.tab === "find") fitTags(); });
// Sammlung lädt beim Scrollen weiter: kommt „weitere zeigen“ in Sicht, klickt es sich selbst
let moreObs = null;
function moreOnScroll(){
  moreObs?.disconnect();
  const m = $("dmore");
  if(!m || !("IntersectionObserver" in window)) return;
  moreObs = new IntersectionObserver(es => { if(es.some(e => e.isIntersecting)){ moreObs.disconnect(); m.click(); } }, {rootMargin: "400px"});
  moreObs.observe(m);
}
// Farbe eines System-Reiters: Nintendo rot, PlayStation blau, PC grün, VR im Türkis des Tools
const NINTENDO = new Set(["Switch 2", "Switch", "Wii U", "Wii", "GameCube", "N64", "SNES", "NES", "3DS", "DS", "GBA", "GBC", "GB", "VB", "Pokémon Mini"]);
const sysFam = n => n === "PC" ? "fam-pc" : n === "VR" ? "fam-vr" : n === "@ps" || /^PS/.test(n) ? "fam-ps" : n === "@nin" || NINTENDO.has(n) ? "fam-nin" : "";
function findView(){
  if(!C){ loadCollection(); return `<p class="hint">Lädt die Sammlung …</p>`; }
  if(C.error) return `<p class="err">Sammlung nicht lesbar: ${esc(C.error)}</p>`;
  if(!allGames().length) return `<div class="card"><h2>Sammlung</h2><p class="hint">Hier filterst du deine ganze Spielesammlung, je System, nach Mehrspieler, Spielerzahl, Genre und Wertung und lässt dir Spiele vorschlagen.
    Dafür braucht das Tool einmal den Playnite-Export mit allen Spielen (unter Einstellungen bei „Datei oder Text einlesen“), deine Retro-Liste (unter „Retro-Sammlung“) oder deine Meta-Käufe.</p>
    <button class="link" data-act="tab" data-v="settings">Zu den Einstellungen</button></div>`;
  const d = V.d;
  // Reiter je System, „Alle“ vorn, VR nach PC. Gibt es das gewählte System nicht (etwa PC, der Standard,
  // ohne PC-Spiele), gilt „Alle“, ohne Playnite und Retro-Liste VR
  const sys = (C.systems || []).slice(), nVr = (S.library || []).length;
  if(nVr) sys.splice(sys.findIndex(([n]) => n === "PC") + 1, 0, ["VR", nVr]);
  // Familien mit mehr als einem System bekommen einen eigenen Reiter (Reihenfolge wie FAMS, darin wie die Systeme)
  const fams = {};
  for(const [n, c] of sys) if(n !== "PC" && n !== "VR"){ const f = famOf(n); (fams[f] = fams[f] || []).push([n, c]); }
  const famKeys = Object.keys(fams).filter(f => fams[f].length > 1);
  if(d.sys === "Switch"){ d.sys = "Switch 2"; d.sw = "s1"; }      // Lesezeichen von vor 0.7.5
  if(d.sys && !sys.some(([n]) => n === d.sys) && !famKeys.includes(d.sys)) d.sys = sys.length === 1 ? sys[0][0] : "";
  // „Alle“ nur, wenn Playnite und Retro-Liste mehr als ein System liefern
  const nAll = C.games.length, multi = (C.systems || []).length > 1;
  if(!d.sys && !multi && sys.length) d.sys = sys[0][0];
  const curFam = d.sys && (d.sys[0] === "@" ? d.sys : famKeys.includes(famOf(d.sys)) ? famOf(d.sys) : "");
  // Herausgleiten nur beim Öffnen der Familie, nicht bei jedem neuen Zeichnen
  // Neu gezeichnet wird oft gleich danach (Sammlung geladen, Abgleich): die Animation läuft dann an derselben
  // Stelle weiter (negative Verzögerung), statt abzubrechen; so gleiten alle Familien gleich (0.7.5)
  if(curFam && V.lastFam !== curFam) V.famAt = Date.now();
  V.lastFam = curFam;
  const since = Date.now() - (V.famAt || 0), anim = curFam && since < 700;
  const tab = (v, l, c, cls, tip) => `<button role="tab" aria-selected="${d.sys === v}" data-act="dsys" data-v="${esc(v)}" class="${sysFam(v)}${d.sys === v ? " on" : ""}${cls || ""}"${tip ? ` title="${esc(tip)}"` : ""}>${esc(l)} <span class="n">${c}</span></button>`;
  const top = sys.filter(([n]) => n === "PC" || n === "VR").map(([n, c]) => tab(n, n, c, "", n === "VR" ? "Deine VR-Titel bei Meta und am PC" : ""));
  for(const [f] of FAMS){
    if(!fams[f]) continue;
    if(!famKeys.includes(f)){ const [n, c] = fams[f][0]; top.push(tab(n, n, c)); continue; }
    const open = curFam === f;
    top.push(tab(f, famName(f), fams[f].reduce((a, [, x]) => a + x, 0), open && d.sys !== f ? " part" : "", `Alle Spiele von ${famName(f)}; ein Klick zeigt die Konsolen einzeln`) +
      (open ? `<span class="subtabs${anim ? " anim" : ""}"${anim && since > 30 ? ` style="animation-delay:-${since}ms"` : ""}>${fams[f].map(([m, x]) => tab(m, m, x, " sub")).join("")}</span>` : ""));
  }
  const tabs = sys.length > 1 ? `<div class="systabs" role="tablist" aria-label="System">${multi ? tab("", "Alle", nAll, "", "Alle Systeme aus Playnite, der Retro-Liste und dem eShopKompass; deine VR-Titel stehen unter VR") : ""}${top.join("")}</div>` : "";
  const inTab = allGames().filter(g => inSys(g, d.sys)), vr = d.sys === "VR";
  const filtered = dFilter(d), cols = colsFor(d, inTab), rows = dSort(filtered, d, cols);
  G_SHOWN = {rows, cols, sys: d.sys};
  const pick = d.mix === "surprise" || d.mix === "wild" ? dPick(filtered, d.seed) : [];
  const opt = (list, cur) => list.map(([v, l]) => `<option value="${esc(v)}"${String(v) === String(cur) ? " selected" : ""}>${esc(l)}</option>`).join("");
  const stores = [...new Set(inTab.map(g => g.store).filter(Boolean))].sort();
  const genresIn = [...new Set(inTab.flatMap(g => g.genres))].sort((a, b) => a.localeCompare(b, "de"));
  const mpIn = Object.keys(C.mp_label || {}).filter(k => inTab.some(g => g.mp.includes(k)));
  // ein Klick auf die gewählte Mischung nimmt sie wieder zurück; nur Mischungen, die im Reiter etwas finden können
  const mixOk = ([k, , , m, vrOk]) => vr ? vrOk : k !== "wild" || (mpIn.length && genresIn.length);
  const mixes = `<div class="chips mix">${MIXES.filter(mixOk).map(([k, l, tip]) => `<button data-act="${d.mix === k ? "dmixoff" : "dmix"}" data-v="${k}" title="${esc(d.mix === k ? "Zurücknehmen" : tip)}" class="${d.mix === k ? "on" : ""}">${esc(l)}</button>`).join("")}</div>`;
  // Filter als Menüs mit Häkchen. Die Zahl hinter einem Genre: Spiele mit diesem Genre unter den übrigen
  // Filtern; bei „alle“ zusätzlich mit allen schon gewählten Genres
  const base = dFilter(Object.assign({}, d, {g: d.gop === "and" ? d.g : []})), gn = {};
  for(const g of base) for(const x of g.genres) gn[x] = (gn[x] || 0) + 1;
  const gq = (V.gq || "").trim().toLowerCase();
  const genres = genresIn.length ? `<details class="menu" ${menuAttr("g")}><summary>Genre${d.g.length ? ` <span class="cnt">${d.g.length}</span>` : ""}</summary><div class="pop wide">
    <div class="seg" role="group" aria-label="Mehrere Genres verknüpfen"><button data-act="dgop" data-v="" class="${d.gop !== "and" ? "on" : ""}" title="Spiele mit mindestens einem der Genres">eines davon</button><button data-act="dgop" data-v="and" class="${d.gop === "and" ? "on" : ""}" title="Nur Spiele mit allen gewählten Genres">alle</button></div>
    <input type="search" data-in="gq" placeholder="Genre suchen" aria-label="Genre suchen" value="${esc(V.gq || "")}">
    <div class="opts">${genresIn.filter(g => !gq || g.toLowerCase().includes(gq) || d.g.includes(g)).map(g => `<label><input type="checkbox" data-dg="${esc(g)}"${d.g.includes(g) ? " checked" : ""}> ${gTag(g)} <span class="n">${gn[g] || 0}</span></label>`).join("")}</div>
    ${d.g.length ? `<button class="link" data-act="dgclear">keins</button>` : ""}</div></details>` : "";
  const mn = {};
  for(const k of mpIn) mn[k] = dFilter(Object.assign({}, d, {mp: d.mp.includes(k) ? d.mp : d.mp.concat(k)})).length;
  const kinds = mpIn.length ? `<details class="menu" ${menuAttr("mp")}><summary>Mehrspieler${d.mp.length ? ` <span class="cnt">${d.mp.length}</span>` : ""}</summary><div class="pop">
    <p class="hint">Mehrere gewählt: alle müssen passen.</p>
    ${mpIn.map(k => `<label><input type="checkbox" data-dmp="${esc(k)}"${d.mp.includes(k) ? " checked" : ""}> ${esc(C.mp_label[k])} <span class="n">${mn[k]}</span></label>`).join("")}</div></details>` : "";
  const label = dLabel(d);
  // Switch und Switch 2 stehen in einem Reiter (0.7.5); wie im eShopKompass lässt sich das System wählen
  const sw = d.sys === "Switch 2" && inTab.some(g => g.sw1) && inTab.some(g => !g.sw1);
  // Nur Switch-Spiele aus dem eShopKompass im Reiter: dessen Filter (0.7.6)
  const kv = inTab.length > 0 && inTab.every(kOn);
  const hn = {};
  if(kv) for(const [k] of K_HOW) hn[k] = dFilter(Object.assign({}, d, {how: d.how.includes(k) ? d.how : d.how.concat(k)})).length;
  const how = kv ? `<details class="menu" ${menuAttr("how")}><summary>Spielweise${d.how.length ? ` <span class="cnt">${d.how.length}</span>` : ""}</summary><div class="pop">
    <p class="hint">Mehrere gewählt: alle müssen passen.</p>
    ${K_HOW.map(([k, l, tip]) => `<label title="${esc(tip)}"><input type="checkbox" data-dhow="${k}"${d.how.includes(k) ? " checked" : ""}> ${esc(l)} <span class="n">${hn[k]}</span></label>`).join("")}</div></details>` : "";
  // 0.8.20: als Menü am Ende der Zeile, damit die übrigen Filter beim Wechsel der Reiter an ihrem Platz bleiben
  const SW = [["", "alle"], ["s2", "Switch 2"], ["s1", "nur Switch"]];
  const swMenu = sw ? `<details class="menu" ${menuAttr("sw")}><summary>${d.sw ? esc(SW.find(x => x[0] === d.sw)[1]) : "System"}</summary><div class="pop">
    ${SW.map(([k, l]) => `<label><input type="radio" name="dsw" data-dset="sw" value="${k}"${(d.sw || "") === k ? " checked" : ""}> ${l}</label>`).join("")}</div></details>` : "";
  const filters = `<div class="dfilter">${kv ? how : kinds}${genres}
      ${inTab.some(g => g.players) ? `<label>Spieler <select data-dset="min">${opt([[0, "egal"], [2, "ab 2"], [3, "ab 3"], [4, "ab 4"], [8, "ab 8"]], d.min)}</select></label>` : ""}
      ${stores.length > 1 ? `<label>${vr ? "Besitz" : "Launcher"} <select data-dset="st">${opt([["", "alle"]].concat(stores.map(x => [x, x])), d.st)}</select></label>` : ""}
      ${inTab.some(g => g.score != null) ? `<label>Wertung <select data-dset="sc">${opt(kv ? [[0, "egal"], [70, "ab 70"], [80, "ab 80"], [90, "ab 90"]] : [[0, "egal"], [60, "ab 60 %"], [70, "ab 70 %"], [80, "ab 80 %"], [90, "ab 90 %"]], d.sc)}</select></label>` : ""}
      ${kv ? `<label>Spielzeit <select data-dset="hr">${opt([[0, "egal"], [5, "bis 5 h"], [10, "bis 10 h"], [20, "bis 20 h"], [-40, "ab 40 h"]], d.hr)}</select></label>
      <label title="Höchstens diese Altersfreigabe: USK, ohne USK PEGI; Spiele ohne Angabe fallen heraus">USK <select data-dset="usk">${opt([["", "egal"], ["0", "bis 0"], ["6", "bis 6"], ["12", "bis 12"], ["16", "bis 16"]], d.usk)}</select></label>` : ""}
      ${inTab.some(g => g.retro) ? `<label title="Sprache laut Dateiname; „DE fehlt“: es gab eine Fassung mit Deutsch, deine hat keins">Sprache <select data-dset="lang">${opt(LANG_FILTER, d.lang)}</select></label>` : ""}
      <label title="Dein Stand je Spiel, setzt du in den Einzelheiten">Mein Stand <select data-dset="me">${opt(G_STF, d.me)}</select></label>
      ${vr ? `<label><input type="checkbox" data-dset="cb"${d.cb ? " checked" : ""}> Crossbuy</label>` : ""}
      ${inTab.some(g => g.wheel) ? `<label title="In der ${WHEEL_LIST} (bestätigt) oder laut Steam-Schlagwörtern (gestrichelt, nur ein Hinweis)"><input type="checkbox" data-dset="wh"${d.wh ? " checked" : ""}> SimRacing</label>` : ""}
      ${inTab.some(g => g.vr && !g.vr_guess) && d.sys === "PC" ? `<label title="Spiele mit VR laut Steam, Store-Prüfung oder als dein VR-Titel"><input type="checkbox" data-dset="vr"${d.vr ? " checked" : ""}> VR</label>` : ""}
      ${inTab.some(vrMod) ? `<label title="VR per Mod laut PCGamingWiki oder Mods mit VR im Namen bei Nexus Mods (gestrichelt, nur ein Hinweis)"><input type="checkbox" data-dset="vm"${d.vm ? " checked" : ""}> VR per Mod</label>` : ""}
      ${inTab.some(g => g.added) && !vr ? `<label><input type="checkbox" data-dset="old"${d.old ? " checked" : ""}> über zwei Jahre in der Sammlung</label>` : ""}${swMenu}</div>
    ${label ? `<div class="chips act">${d.how.map(h => `<button data-act="dhowoff" data-v="${esc(h)}" title="Filter entfernen">${esc((K_HOW.find(x => x[0] === h) || [h, h])[1])} ×</button>`).join("")}${d.mp.map(m => `<button data-act="dmpoff" data-v="${esc(m)}" title="Filter entfernen">${esc(C.mp_label[m] || m)} ×</button>`).join("")}${d.g.map(g => `<button data-act="dgoff" data-v="${esc(g)}" title="Filter entfernen">${esc(g)} ×</button>`).join("")}<button class="link" data-act="dreset">alle Filter zurücksetzen</button></div>` : ""}`;
  const colSort = !!V.sorts.find;
  const canAll = rows.length <= G_ALL;
  if(V.gAll && !canAll){ V.gAll = false; V.gShut.clear(); }
  const foldall = `<span class="foldall" title="${canAll ? rows.length === 1 ? "Das eine Spiel der Liste aufklappen" : `Alle ${num(rows.length)} Spiele der Liste aufklappen` : `Alle aufklappen geht bei höchstens ${G_ALL} Spielen, hier sind es ${num(rows.length)}. Wähl ein System, filtere oder suche`}"><button class="link" data-act="gall" data-v="1"${canAll ? "" : " disabled"}>alle aufklappen</button> · <button class="link" data-act="gall" data-v=""${V.gAll || V.gOpen ? "" : " disabled"}>alle zuklappen</button></span>`;
  const bar = `<div class="bar"><span class="sbox"><input type="search" id="dq" placeholder="${vr ? "Name oder Notiz suchen" : "Name, Entwickler oder Genre suchen"}" aria-label="In der Sammlung suchen" value="${esc(d.q)}" data-in="dq">${d.q ? `<button class="sx" data-act="dqclear" title="Suche leeren (Esc)" aria-label="Suche leeren">×</button>` : ""}</span>
    <label class="kind">Sortieren <select data-dset="sort">${colSort ? `<option value="" selected>nach Spalte</option>` : ""}${opt(D_SORTS.filter(([k]) => !vr || !["gem", "known", "year"].includes(k)), colSort ? "" : d.sort)}</select></label>
    ${d.sort === "random" && !colSort ? `<button data-act="dshuffle">Neu mischen</button>` : ""}${foldall}
    <button class="link gdl" data-act="gdl" title="Die Liste mit den gezeigten Spalten als Datei (CSV); aufgeklappte Spiele mit ihren Einzelheiten">herunterladen</button></div>`;
  const gcols = `minmax(180px,1.5fr) ${cols.map(c => c.w).join(" ")}`;
  // Einzelheiten: Mein Stand steht in jedem Reiter an derselben Stelle (0.8.7), unabhängig von den Spalten
  // Mein Stand gleich nach der Spalte „Spiel“, wie in der Switch-Ansicht bis 0.8.6 (0.8.10: 3 zu 5 statt 1,5 zu 1)
  const dcols = "minmax(180px,3fr) minmax(320px,5fr)";
  const glist = (list, head) => `<div class="glist${head ? " box" : ""}" style="--gcols:${gcols};--dcols:${dcols}">${head || ""}${list}</div>`;
  const pickCard = pick.length || d.mix === "surprise" || d.mix === "wild" ? `<div class="card gpick"><h2>${d.mix === "wild" ? "Wilde Mischung" : "Vorschlag"}${label ? ` <span class="n">${esc(label)}</span>` : ""}</h2>
    ${pick.length ? glist(pick.map(g => gRow(g, cols, true)).join("")) : `<p class="hint">Nichts passt zu den Filtern.</p>`}
    <div class="actions"><button data-act="dpickoff">Schließen</button><button class="primary" data-act="dmix" data-v="${d.mix}">Noch mal</button></div></div>` : "";
  const at = S.imports.collection?.at, rat = S.imports.retro?.at;
  const nRetro = inTab.filter(g => g.retro).length, nEsh = inTab.filter(g => g.eshop).length, nPn = inTab.length - nRetro - nEsh, pcTab = !d.sys || d.sys === "PC";
  const gone = C.games.filter(g => g.gone);
  // Spiele, die in der letzten Retro-Liste fehlen: einmal ansehen, dann Stand übernehmen oder behalten
  const goneCard = gone.length ? `<div class="card"><h2>Nicht mehr in der Retro-Liste <span class="n">${gone.length}</span></h2>
    <p class="hint">${gone.slice(0, 40).map(g => `${esc(g.name)} (${esc(g.system)})`).join(", ")}${gone.length > 40 ? " …" : ""}</p>
    <div class="actions"><button data-act="retrogone" data-v="keep" title="Die Spiele bleiben in der Sammlung, der Hinweis verschwindet">Behalten</button>
      <button class="primary" data-act="retrogone" data-v="drop" title="Die Spiele werden aus der Sammlung entfernt">Stand übernehmen</button></div></div>` : "";
  const src = vr ? `Deine VR-Titel: Meta-Käufe und VR-Spiele aus Playnite. Wertungen von Meta (VRDB, sonst aus dem Sternschnitt) und Steam, Spieler und Updates von Steam, Recherche aus Foren und Tests violett.`
    : [nPn && `${at ? `Playnite-Export vom ${day(at)}. ` : ""}Genres und Mehrspieler aus Playnite${pcTab ? `, bei PC-Spielen mit Steam abgeglichen: ${inTab.filter(g => g.src === "steam").length} bisher (violett: nur eine Quelle). Wertung aus Steam-Rezensionen ab 50 (${inTab.filter(g => g.reviews != null).length} abgerufen)` : "; Steam-Abgleich und Wertung gibt es nur für PC-Spiele"}.`,
      nEsh && `Switch-Sammlung aus dem eShopKompass${C.eshop_at ? `, gelesen ${day(C.eshop_at)}` : ""}: Genre, Spieler, Wertung und Spielzeit von DekuDeals und Nintendo, Mein Stand setzt du dort.`,
      nRetro && `Retro-Liste${rat ? ` vom ${day(rat)}` : ""}: Sprache laut Dateiname, violett: nur aus der Region geschätzt${inTab.some(g => g.de) ? `; deutsche Fassung fehlt bei ${inTab.filter(g => g.de?.st === "missing").length}, laut No-Intro, Redump und Retool` : ""}. Genres und Spielerzahl für Retro-Spiele kommen später.`].filter(Boolean).join(" ");
  // Kurz, die Herkunft zum Aufklappen (0.7.5, Entscheidung 27.10.2026: der lange Text war zu viel)
  const note = `<details class="gnote"><summary class="hint">${rows.length === inTab.length ? (inTab.length === 1 ? "1 Spiel" : `Alle ${num(inTab.length)} Spiele`) : `${num(rows.length)} von ${num(inTab.length)} Spielen`}${d.sys ? ` (${esc(d.sys[0] === "@" ? famName(d.sys) : d.sys)})` : ""}.</summary><p class="hint">${src}</p></details>`;
  const es = cols === K_COLS;
  const head = `<div class="gr nph${es ? " es" : ""}" role="row">${es ? `<span class="gh-sp" aria-hidden="true">Spieler</span>` : ""}${gTh("title", `Spiel <button class="link gcopy" data-act="gcopy" title="Alle ${num(rows.length)} Titel der Liste kopieren, einer je Zeile" aria-label="Titel kopieren">⧉</button>`, "", "gh-t")}${cols.map(c => gTh(c.k, c.l, c.tip || "", c.cls || "", c.d0 || 1)).join("")}</div>`;
  return goneCard + tabs + bar + mixes + filters + pickCard + note +
    glist(rows.slice(0, d.n).map(g => gRow(g, cols)).join("") || `<p class="hint">Kein Treffer.</p>`, head) +
    (rows.length > d.n ? `<div class="actions"><button id="dmore" data-act="dmore">weitere ${Math.min(D0.n, rows.length - d.n)} zeigen</button></div>` : "");
}

/* ---------------------------------------------------------------- Jetzt */
/* Wunschtitel im Angebot, die nah am Bestpreis beider Läden liegen („kaufen“: bis 2 % oder 0,50 €
   darüber, „gut“: bis 15 % oder 2 €); die übrigen Angebote auf Wunsch darunter */
function nowView(){
  const last = S.sync?.done, far = S.now_far || [];
  // 0.8.11: auch die PC-Wünsche nah am bisherigen Tief bei gg.deals; ab 0.8.20 steht PC über VR wie in den Reitern
  const q = V.q.trim().toLowerCase();
  const pcAll = (S.pcwish?.rows || []).filter(r => r.near && !pcIsVr(r) && !r.owned);
  const pc = pcAll.filter(r => !q || r.name.toLowerCase().includes(q)).sort((a, b) => (a.over ?? 1e9) - (b.over ?? 1e9));
  if(!last && !S.now.length && !far.length && !pcAll.length) return `<p class="hint">Noch kein Abruf gelaufen. Oben über „Aktualisieren“ startest du den ersten; danach läuft er nach Zeitplan.</p>`;
  const sort = V.nowSort || "best", kind = V.nowKind || "";
  let rows = S.now.filter(r => match(r) && lfOk(r, ["cb", "best", "good"]));
  const k = {best: nearBest, rating: byRating}[sort];
  if(k) rows = rows.slice().sort((a, b) => k(a) - k(b));
  // Reiter wie in Wunschliste und Sammlung (0.8.17, statt des Schalters): Alle, PC, VR an derselben Stelle
  const kb = (v, l, n, cls, tip) => `<button role="tab" aria-selected="${kind === v}" data-act="nowk" data-v="${v}" class="${cls}${kind === v ? " on" : ""}" title="${tip}">${l} <span class="n">${n}</span></button>`;
  const tabs = `<div class="systabs" role="tablist" aria-label="Welche Wünsche">${kb("", "Alle", S.now.length + pcAll.length, "", "VR- und PC-Wünsche")}${kb("pc", "PC", pcAll.length, "fam-pc", "PC-Wünsche von gg.deals nah am bisherigen Tief")}${kb("vr", "VR", S.now.length, "fam-vr", "VR-Wünsche bei Meta und Steam")}</div>`;
  const vr = `<p class="hint">VR: Wunschtitel, die gerade bei Meta oder Steam reduziert sind und höchstens 15 % oder 2 € über dem Bestpreis beider Läden liegen. Letzter Abruf: ${when(last) || "–"}.</p>
    <div class="list">${rows.map(r => wishRow(r)).join("") || `<p class="hint">${S.now.length ? "Kein Treffer." : "Gerade ist kein Wunschtitel nah am Bestpreis reduziert."}</p>`}</div>
    ${far.length ? grp("now-far", `Reduziert, aber noch weit über dem Bestpreis`, far.length,
      `<div class="list">${far.filter(r => match(r)).map(r => wishRow(r)).join("")}</div>`, true) : ""}`;
  const pcPart = `<p class="hint">PC: Wünsche deiner gg.deals-Wunschliste, die höchstens 5 % über dem bisherigen Tief liegen (Händler oder Keyshop).</p>` +
    (pc.length ? pcTable(pc) : `<p class="hint">${pcAll.length ? "Kein Treffer." : S.pcwish?.n ? "Gerade ist kein PC-Wunsch nah am Tief." : "Noch keine PC-Wunschliste (Einstellungen, Konten)."}</p>`);
  return tabs + listBar({sorts: [["best", "Nah am Bestpreis"], ["sale", "Rabatt"], ["rating", "Wertung"]], sort, sortKey: "now", filters: kind === "pc" ? [] : ["cb", "best", "good"]}) +
    (kind === "pc" ? pcPart : kind === "vr" ? vr : (kind === "" && pcAll.length ? grp("now-pc", "PC", pc.length, pcPart) + grp("now-vr", "VR", rows.length, vr) : vr));
}

/* ---------------------------------------------------------------- Abrufe */
const SOURCES = [["steamacc", "Steam-Konto (Besitz, Wunschliste)"], ["ggwish", "gg.deals-Wunschliste"], ["sharenite", "Sharenite (Playnite)"],
  ["qsdb", "QuestStoreDB (Meta-Preise)"], ["steam", "Steam-Store"], ["gg", "gg.deals"], ["reviews", "Steam-Rezensionen (Sammlung)"], ["details", "Steam-Details (Sammlung)"], ["rating", "Steam-Wertungen (Wunschliste, Sammlung VR)"],
  ["players", "Steam-Spieler und Updates"], ["vrdb", "VRDB (Crossbuy, Version, Meta-Wertung)"], ["retro", "Retro-Fassungen (No-Intro, Redump, Retool)"], ["igdb", "IGDB (Spielinfos der Sammlung)"], ["pcinfo", "PC-Wunschliste, Spielinfos (Steam, IGDB)"], ["pcgw", "PCGamingWiki (VR per Mod)"], ["nexus", "Nexus Mods (Mods je PC-Spiel)"], ["wheel", "Sim-Racing (Steam-Schlagwörter, Listen von SimHub und Simucube)"], ["eshop", "eShopKompass (Switch-Sammlung)"]];
const ACCOUNT_SET = {igdb: se => se.igdb_set, steamacc: se => se.steam_id, ggwish: se => se.gg_wish_set, sharenite: se => se.sharenite};
/* Eine Tabellenzeile je Quelle (0.6.2, kompakt wie im eShopKompass): Name, Zustand farbig, wann, Abrufe und Meldung */
function srcRow(k, l, x){
  const td = (a, b, c) => `<tr><td>${l}</td><td>${a}</td><td class="hint">${b}</td><td class="hint">${c}</td></tr>`;
  if(!x) return td(`<span class="hint">${k === "gg" && !S.settings?.gg_key_set ? "ohne Schlüssel aus" : "noch nicht gelaufen"}</span>`, "", "");
  if(x.manual) return td(`<span class="warnc" title="gg.deals zeigt dem Server eine Prüfseite; dein Browser kommt durch">per Lesezeichen</span>`, S.imports.ggwish ? when(S.imports.ggwish.at) : "noch nie gelesen", "");
  const rest = x.until && new Date(x.until) > new Date();
  const st = x.ok ? `<span class="ok">ok</span>` : rest ? `<span class="warnc">ruht bis ${esc(whenDay(new Date(x.until)) + clock(new Date(x.until)))}</span>` : `<span class="err">Problem</span>`;
  return td(st, when(x.at), `${x.requests ?? 0} Abrufe${x.errors ? `, ${x.errors} Fehler` : ""}${!x.ok && x.msg ? ` · ${esc(x.msg)}` : ""}`);
}
/* ---------------------------------------------------------------- Einstellungen
   Drei feste Karten (Abgleich, Importe, Sicherung), oben „Derselbe Titel?“, wenn etwas zu
   entscheiden ist. Klappbar sind die Teile darin, nicht die Karten: Protokoll, Verbindungstest,
   Zeitplan und jeder Import. Jede Klappzeile nennt im zugeklappten Zustand das Nötigste. */
function box(id, title, info, body){
  return `<div class="card" id="${id}"><h2>${title}${info ? ` <span class="n">${info}</span>` : ""}</h2>${body}</div>`;
}
function sub(k, title, info, body, shut, id){
  return `<details class="sub" ${foldAttr(k, shut)}${id ? ` id="${id}"` : ""}><summary><b>${title}</b>${info ? ` <span class="n">${info}</span>` : ""}</summary>${body}</details>`;
}
// Letzte Zeile des Protokolls ohne Uhrzeit, etwa „fertig, 58 Titel aktualisiert“
const lastLine = sy => { const l = sy.log || []; return {end: (l[l.length - 1] || "").replace(/^\d\d:\d\d:\d\d /, "")}; };
function settingsView(){
  const sy = S.sync || {}, se = S.settings || {}, src = sy.sources || {}, sug = S.suggestions.length;
  const hours = se.hours || 6, last = sy.started ? new Date(sy.started) : null;
  const next = last && se.auto ? new Date(+last + hours * 3600000) : null;
  const shown = SOURCES.filter(([k]) => !ACCOUNT_SET[k] || ACCOUNT_SET[k](se));
  const rows = shown.map(([k, l]) => srcRow(k, l, src[k])).join("");
  // „per Lesezeichen“ (gg.deals-Wunschliste hinter Cloudflare) ist kein Fehler, sondern der Weg
  const isBad = k => src[k] && !src[k].ok && !src[k].manual;
  const bad = shown.filter(([k]) => isBad(k)).length, okN = shown.filter(([k]) => src[k]?.ok).length;
  // Wie im eShopKompass: grün, was läuft, rot mit Namen, was nicht läuft
  const badNames = shown.filter(([k]) => isBad(k)).map(([k]) => SRC_NAME[k] || k).join(", ");
  const srcInfo = [okN && `<b class="ok">${okN} ok</b>`, bad && `<b class="err">${bad} mit Problem</b> (${esc(badNames)})`].filter(Boolean).join(", ") || "noch nicht gelaufen";
  const todo = S.todo || [], lists = S.lists || [], near = S.retro_near || [], rown = S.retro_own || [], open = sug + todo.length + lists.length + near.length + rown.length;
  const jumps = [open && ["todo", "Zu erledigen"], ["importe", "Einlesen"], ["abgleich", "Abgleich"], ["sicherung", "Sicherung"]].filter(Boolean);
  const sugList = `<p class="hint">Diese Paare heißen fast gleich, einer stammt aus Meta, der andere vom PC. Zusammenführen heißt: ein Eintrag mit beiden Seiten, unter dem Namen, den du anklickst. Der andere Name bleibt für spätere Importe bekannt, und unter „bearbeiten“ kannst du jederzeit umbenennen.</p>
    <div class="list">${S.suggestions.map(x => `<div class="item"><span class="nm">${esc(x.a_name)} ↔ ${esc(x.b_name)}</span>
      <span class="row2">Zusammenführen als
        <button data-act="merge" data-a="${esc(x.a)}" data-b="${esc(x.b)}" title="Ein Eintrag mit diesem Namen">„${esc(x.a_name)}“</button>
        <button data-act="merge" data-a="${esc(x.b)}" data-b="${esc(x.a)}" title="Ein Eintrag mit diesem Namen">„${esc(x.b_name)}“</button>
        oder <button data-act="notsame" data-a="${esc(x.a)}" data-b="${esc(x.b)}">Verschieden</button></span></div>`).join("")}</div>`;
  const steamTodo = todo.filter(x => x.kind === "steam"), metaTodo = todo.filter(x => x.kind === "meta");
  const steamList = `<p class="hint">Diese Steam-IDs stammen nur aus einem Namen, und die Prüfung im Steam-Store hat sie nicht bestätigt.</p>
    <div class="list">${steamTodo.map(x => `<div class="item"><span class="nm">${esc(x.name)} <a href="https://store.steampowered.com/app/${esc(x.steam_appid)}/" target="_blank" rel="noopener noreferrer">Steam ${esc(x.steam_appid)}</a></span>
      <span class="row2"><span class="hint">${esc(x.why)}</span>
        <button data-act="steamok" data-k="${esc(x.key)}" title="Die App gehört zu diesem Titel">passt</button>
        <button data-act="steamwrong" data-k="${esc(x.key)}" title="Steam-ID entfernen; diese App schlägt das Tool nicht wieder vor">falsch</button></span></div>`).join("")}</div>`;
  const metaList = `<p class="hint">QuestStoreDB fand diese Titel unter keinem ihrer Namen. Unter „bearbeiten“ kannst du einen Link oder die Meta-ID eintragen, dann holt das Tool den Rest.</p>
    <div class="list">${metaTodo.map(x => `<div class="item"><span class="nm">${esc(x.name)}</span>
      <span class="row2"><span class="hint">${esc(x.why)}${x.row?.origin?.length ? `. Herkunft: ${originText(x.row)}` : ""}</span>
        <a href="https://queststoredb.com/all_apps/?release_status=all&amp;q=${encodeURIComponent(x.name)}" target="_blank" rel="noopener noreferrer">suchen</a>
        <button class="link" data-act="edit" data-k="${esc(x.key)}">bearbeiten</button></span></div>`).join("")}</div>`;
  // Retro (0.8.4): Titel ohne Treffer in der Fassungsliste, dort aber ein ähnlicher
  const nearList = `<p class="hint">Diese Retro-Spiele stehen nicht unter ihrem Namen in der Fassungsliste (No-Intro oder Redump), dort aber ein ähnlicher Titel. Ist es dasselbe Spiel, prüft das Tool darüber, ob es eine Fassung mit Deutsch gab.</p>
    <div class="list">${near.map(x => `<div class="item"><span class="nm">${esc(x.name)} <span class="hint">(${esc(x.system)})</span></span>
      <span class="row2"><span class="hint">ähnlich: „${esc(x.near)}“</span>
        <button data-act="nearok" data-k="${esc(x.key)}" title="Dasselbe Spiel; der Titel der Liste gilt fortan">dasselbe</button>
        <button data-act="nearno" data-k="${esc(x.key)}" title="Ein anderes Spiel; dieser Vorschlag kommt nicht wieder">anderes</button></span></div>`).join("")}</div>`;
  // Retro (0.8.8): andere Quellen widersprechen deinem Genre aus der Ordner-Liste
  const ownList = `<p class="hint">Deine Ordner-Liste gilt zuerst. Hier nennen libretro und IGDB beide ein anderes Genre und sind sich darin einig (ab 0.8.12; was nur eine Quelle anders sieht, steht nur in den Einzelheiten, ihr Genre kommt in der Zeile dazu). „Liste gilt“ blendet den Hinweis aus; ändert sich ein Wert, kommt er wieder. Stimmt die andere Quelle, änderst du deine Liste und liest den Ordner neu ein.</p>
    <div class="bar"><button data-act="ownok" data-k="" title="Für alle hier: deine Liste gilt">Alle: Liste gilt</button></div>
    <div class="list">${rown.slice(0, 300).map(x => `<div class="item"><span class="nm">${esc(x.name)} <span class="hint">(${esc(x.system)})</span></span>
      <span class="row2"><span class="hint">deins: ${esc(x.diff[0].own)}; ${x.diff.map(d => `${esc(d.src)}: ${esc(d.other)}`).join("; ")}</span>
        <button data-act="ownok" data-k="${esc(x.key)}" title="Dein Genre gilt; der Hinweis verschwindet">Liste gilt</button></span></div>`).join("")}</div>${rown.length > 300 ? `<p class="hint">… und ${rown.length - 300} weitere</p>` : ""}`;
  // Zahlen, die etwas zu tun bedeuten, violett und fett (0.7.4, wie im eShopKompass „offen“)
  const tn = n => `<b class="warnc">${n}</b>`;
  const sugCard = open ? box("todo", "Zu erledigen", `${tn(open)} offen`, `
    <p class="hint">Was das Tool nicht selbst klären konnte. Alles andere ordnet es bei jedem Abgleich von allein zu.</p>
    ${listsHtml()}
    ${sug ? sub("sug", "Derselbe Titel?", `${tn(S.suggestions.length)} ${S.suggestions.length === 1 ? "Paar" : "Paare"}`, sugList) : ""}
    ${steamTodo.length ? sub("steamtodo", "Steam-ID prüfen", tn(steamTodo.length), steamList) : ""}
    ${metaTodo.length ? sub("metatodo", "Ohne Meta-ID", tn(metaTodo.length), metaList) : ""}
    ${near.length ? sub("retronear", "Retro: ähnlicher Name", tn(near.length), nearList) : ""}
    ${rown.length ? sub("retroown", "Retro: Genre weicht von deiner Liste ab", tn(rown.length), ownList) : ""}`) : "";
  const ll = lastLine(sy);
  const logInfo = sy.running ? "läuft" : !sy.started ? "noch keins" : `${when(sy.started)}${sy.ok === false ? `, <span class="err">mit Fehlern</span>` : ""}${ll.end ? " · " + esc(ll.end) : ""}`;
  const abgleich = box("abgleich", "Abgleich", sy.running ? "läuft" : `Stand ${ago(sy.started)}${next ? ` · nächster ca. ${next < new Date() ? "in Kürze" : whenDay(next) + clock(next)}` : se.auto === false ? " · Zeitplan aus" : ""}`, `
    <form data-form="sched" class="bar sched"><label><input type="checkbox" name="auto" data-sched="1"${se.auto ? " checked" : ""}> automatisch alle</label>
      <input type="number" name="hours" min="2" max="48" value="${esc(hours)}" aria-label="Abstand in Stunden" data-sched="1"> Stunden <span class="err" id="s-err"></span></form>
    <p class="hint">Liest deine Konten, ordnet alle Titel zu und holt Preise und Messwerte. Ein Lauf dauert einige Minuten, weil zwischen zwei Abrufen einer Quelle Pausen liegen; nach einer Sperre ruht eine Quelle 24 Stunden.</p>
    ${sub("quellen", "Quellen", srcInfo, `<div class="scroll"><table class="mini-t"><tbody>${rows}</tbody></table></div>`, !bad)}
    <div class="bar slim" style="margin-top:10px"><button class="primary" data-act="sync" ${sy.running ? "disabled" : ""}>${sy.running ? "Läuft …" : "Aktualisieren"}</button>
      <button data-act="sync" data-v="fast" ${sy.running ? "disabled" : ""} title="Ein Lauf mit 5-mal so vielen Abrufen je Quelle, für das erste Auffüllen einer großen Sammlung. Die Pausen bleiben, darum dauert er etwa eine Stunde.">Beschleunigt auffüllen</button>
      <button data-act="diag" ${V.diagRunning ? "disabled" : ""} title="Fragt jede Quelle einmal an und zeigt, was zurückkommt; dauert bis zu einer Minute und speichert nichts">${V.diagRunning ? "Test läuft …" : "Verbindung testen"}</button></div>
    ${V.diag ? sub("diagbox", "Verbindungstest", `${esc(V.diagAt || "")} · <button class="link" data-act="copy" data-v="diag">Ergebnis kopieren</button>`, `<pre class="log" id="diag">${esc(V.diag.join("\n"))}</pre>`) : ""}
    ${sub("logbox", "Protokoll", logInfo + (sy.started ? ` · <button class="link" data-act="copy" data-v="log">kopieren</button>` : ""), `<pre class="log" id="log"></pre>`, sy.ok !== false && !sy.running, "logfold")}
`);
  const importe = box("importe", "Einlesen", "", `<p class="hint">Bringt Käufe und Wünsche ins Tool: Konten automatisch, Meta per Lesezeichen, alles andere als Datei. Gelöscht wird nichts.</p>
    ${accountsCard()}${metaCard()}${fileCard()}${retroCard()}`);
  // Wie im eShopKompass: drei Knöpfe; der dritte öffnet die Dateiwahl
  const sicherung = box("sicherung", "Sicherung", "", `<p class="hint">Enthält alle Titel mit Notizen, Zuordnungen und zuletzt gelesenen Preisen, dazu Mein Stand, die ganze Sammlung und die PC-Wunschliste, keine Schlüssel und keine Konten. Einlesen ersetzt alles.</p>
     <div class="bar"><a class="btn" href="/api/abgleich" download="vr-navigator-abgleich.json" title="Stand und Protokoll des Abgleichs, Preisverlauf und Einstellungen ohne Schlüssel, zum Nachprüfen. Zum Einlesen nicht nötig.">Abgleichsdaten herunterladen</a>
     <a class="btn" href="/api/export" download="vr-navigator-sicherung.json">Sicherung herunterladen</a>
     <button data-act="pickrestore">Sicherung einlesen</button><input type="file" id="restoreFile" accept=".json,application/json" data-file="restore" hidden aria-label="Sicherung wählen"></div>`);
  return banners() + `<div class="jump" role="navigation" aria-label="Abschnitte">${jumps.map(([id, l]) => `<a href="#${id}" data-act="jump" data-v="${id}">${l}</a>`).join("")}${foldAll}</div>` +
    sugCard + importe + abgleich + sicherung;
}
/* Wunschliste abgleichen: das Tool führt deine Wünsche, die Wunschlisten der Läden sind Spiegel.
   Je Gruppe eine Aktion für alle, je Titel dieselbe einzeln; Links führen zur Liste im Laden,
   wo du einen Eintrag selbst entfernst (das Tool schreibt nirgends hin). */
const LIST_GROUPS = [
  ["owned", "Gekauft, noch auf der Wunschliste", "Du besitzt diese Titel schon. Nimm sie von der Wunschliste; steht ein Titel noch bei Steam, gg.deals oder Meta, zeigt der Link dorthin. „behalten“, wenn du die Fassung im anderen Laden willst.",
    [["drop", "von der Wunschliste"], ["keep", "behalten"]]],
  ["off", "Im Tool entfernt, im Laden noch gewünscht", "Du hast sie im Tool entfernt, die Liste im Laden führt sie noch. Entferne sie dort, dann verschwindet der Hinweis beim nächsten Abgleich; oder wünsche sie wieder.",
    [["wish", "wieder wünschen"]]],
  ["missing", "Fehlt auf einer Laden-Wunschliste", "Gewünscht, aber in einem Laden, der den Titel führt, nicht auf deiner Wunschliste: Meta schickt dir dann keine Rabatt-Mail, Steam und gg.deals keinen Hinweis. „+ Meta“ und „+ gg.deals“ öffnen die Seite zum Eintragen; der nächste Abgleich (Meta: das nächste Lesezeichen) ordnet ihn dann zu. „so lassen“, wenn du nur die eine Fassung willst.",
    [["ok", "so lassen"]]],
  ["table", "Nur aus der alten Tabelle", "Diese Wünsche stehen auf keiner Wunschliste, nur in deiner Vergleichstabelle. Am schnellsten: mit „+ Meta“ und „+ gg.deals“ dort eintragen, dann ordnet das Tool sie beim nächsten Lesen selbst zu. Oder „behalten“ (nur im Tool, von Hand) oder „entfernen“.",
    [["keep", "behalten"], ["drop", "entfernen"]]]];
function listsHtml(){
  const L = S.lists || [], st = S.lists_stale || [];
  const metaWish = st.find(x => x.src === "metawish");
  // Erst lesen, dann entscheiden: was auf der Meta-Wunschliste steht, ordnet das Tool selbst zu
  const first = metaWish && L.some(x => x.kind === "table")
    ? `<p class="banner">${metaWish.at ? `Deine Meta-Wunschliste hast du zuletzt ${ago(metaWish.at)} gelesen` : "Deine Meta-Wunschliste hat das Tool noch nie gelesen"}. Öffne zuerst ${metaWishLink()} und klick dort das Lesezeichen „Seite lesen“: Was dort steht, ordnet das Tool selbst zu, hier bleiben nur die echten Reste. <a href="#importe" data-act="jump" data-v="importe">zum Lesezeichen</a></p>` : "";
  const groups = LIST_GROUPS.map(([kind, title, hint, acts]) => {
    const rows = L.filter(x => x.kind === kind);
    if(!rows.length) return "";
    const keys = rows.map(x => x.key).join(",");
    const bulk = acts.map(([a, l]) => `<button data-act="lists" data-v="${a}" data-keys="${esc(keys)}">alle ${rows.length} ${l}</button>`).join(" ");
    const list = rows.map(x => `<div class="item"><span class="nm">${esc(x.name)}</span>
      <span class="row2"><span class="hint">${esc(x.why)}</span>
        ${kind === "table" || kind === "missing" ? addLinks(x.links) : x.links.filter(l => safeUrl(l.url)).map(l => `<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.label)}</a>`).join(" ")}
        ${acts.map(([a, l]) => `<button data-act="lists" data-v="${a}" data-keys="${esc(x.key)}">${l}</button>`).join(" ")}</span></div>`).join("");
    return sub("lists-" + kind, title, `<b class="warnc">${rows.length}</b>`, `<p class="hint">${hint}</p><div class="bar">${bulk}</div><div class="list">${list}</div>`, kind === "table" && rows.length > 20);
  }).join("");
  return groups ? first + groups : "";
}

/* Protokoll: Zeiten kommen in UTC, gezeigt in der Zeit des Browsers; die Box folgt der neuesten
   Zeile, solange du nicht hochgescrollt hast */
function localStamp(line){
  const m = /^(\d\d):(\d\d):(\d\d)( .*)$/s.exec(line);
  if(!m) return line;
  const d = new Date(); d.setUTCHours(+m[1], +m[2], +m[3], 0);
  return d.toLocaleTimeString("de-DE") + m[4];
}
function logText(){
  const sy = S.sync || {};
  if(!(sy.log || []).length) return "Noch kein Protokoll.";
  const head = `Abgleich vom ${new Date(sy.started).toLocaleString("de-DE")}, v${S.version}${sy.running ? ", läuft" : sy.ok === false ? ", mit Fehlern" : ""}\n`;
  return head + sy.log.map(localStamp).join("\n");
}
function showLog(){
  const l = $("log");
  if(!l) return;
  const atEnd = l.scrollHeight - l.scrollTop - l.clientHeight < 30;
  l.textContent = logText();
  if(atEnd || !l.dataset.seen){ l.scrollTop = l.scrollHeight; l.dataset.seen = "1"; }
}

/* ---------------------------------------------------------------- Recherche */
/* Meinungen aus der Recherche (Reddit, Web): eine Zeile mit Fassung und Mehrspieler, der Rest
   aufklappbar; alles mit „Recherche“ und Stand gekennzeichnet */
const FASSUNG = {quest: "Quest-Fassung besser", pc: "PC-Fassung besser", gleich: "Fassungen gleichwertig"};
const MP = {lebendig: "Mehrspieler lebendig", ruhig: "Mehrspieler ruhig", tot: "Mehrspieler tot", keiner: "kein Mehrspieler"};
function opinionHtml(r){
  const o = r.opinion;
  if(!o) return "";
  // Crossplay: Quest und PC spielen zusammen (nicht Crossbuy, das ist der gemeinsame Kauf im Meta Store)
  const head = [o.fassung && FASSUNG[o.fassung], o.mehrspieler && MP[o.mehrspieler],
    o.crossplay === true ? "Crossplay Quest/PC" : o.crossplay === false ? "kein Crossplay" : ""].filter(Boolean).join(" · ");
  const rows = [["Fazit", o.fazit], ["Fassung", o.fassung_grund], ["Mehrspieler", o.mehrspieler_stand], ["Pflege", o.pflege],
    ["Crossbuy", o.crossbuy_grund], ["Crossplay", o.crossplay_grund], ["Komfort", o.komfort], ["Warnungen", o.warnungen]].filter(x => x[1]);
  const src = (o.quellen || []).filter(q => safeUrl(q.url)).map(q =>
    `<a href="${esc(q.url)}" target="_blank" rel="noopener noreferrer">${esc(q.titel || q.url.replace(/^https?:\/\/([^\/?#]+).*$/i, "$1"))}</a>${q.datum ? ` <span class="hint">${esc(q.datum)}</span>` : ""}`).join(" · ");
  // Recherche ist nicht gemessen: violett gestrichelt und mit „≈“ wie andere unsichere Werte
  return `<details class="op unsure" ${foldAttr("op-" + r.key, true)}><summary title="Aus Foren und Tests zusammengetragen, nicht vom Tool geprüft"><span class="ux">≈ Recherche${o.stand ? ", " + esc(o.stand) : ""}:</span> ${esc(head || "Meinungen")}</summary>
    ${rows.map(([l, v]) => `<div class="small"><b>${l}:</b> ${esc(v)}</div>`).join("")}${src ? `<div class="small"><b>Quellen:</b> ${src}</div>` : ""}</details>`;
}

/* ---------------------------------------------------------------- Import */
/* Lesezeichen „Seite lesen“ (wie „Käufe lesen“ im eShopKompass): läuft in deinem Browser, wo du
   angemeldet bist und Prüfseiten wie die von Cloudflare schon bestanden hast.
   - Meta: Bestellseite, Transaktionen von Meta Pay oder Wunschliste; scrollt, bis alles geladen ist.
   - gg.deals: deine Wunschliste; weitere Seiten holt es mit kurzer Pause nach.
   Dann öffnet es dieses Tool mit den Daten im Adressteil hinter # (geht nicht übers Netz an einen
   Server). Das Tool übernimmt sie. Ausweg: „Als Datei sichern“. */
const META_HV = 8;
function metaHelper(tool){ return `(async()=>{
const gg=/(^|\\.)gg\\.deals$/.test(location.hostname);
if(!gg&&!/(^|\\.)meta\\.com$/.test(location.hostname)){alert("Bitte zuerst eine dieser Seiten öffnen, dann das Lesezeichen anklicken: angemeldet deine Meta-Bestellungen (meta.com/my/orders), die Transaktionen von Meta Pay, deine Wunschliste im Meta Store oder deine Wunschliste bei gg.deals.");return}
if(gg&&!/wishlist/.test(location.pathname)){alert("Bitte deine Wunschliste bei gg.deals öffnen (angemeldet oder über den Teilen-Link), dann das Lesezeichen anklicken.");return}
const box=document.createElement("div");box.style.cssText="position:fixed;z-index:2147483647;top:12px;right:12px;width:min(420px,90vw);background:#fff;color:#111;border:2px solid #24383b;border-radius:8px;padding:12px;font:14px sans-serif";box.textContent="VR-Navigator: lade alles …";document.body.appendChild(box);
const look=(b,main)=>{b.style.cssText="margin:0 8px 6px 0;padding:6px 12px;border-radius:6px;font:600 13px sans-serif;cursor:pointer;"+(main?"background:#24383b;color:#fff;border:1px solid #24383b":"background:#f3f4f1;color:#1b2224;border:1px solid #9aa3a1");return b};
const wait=t=>new Promise(r=>setTimeout(r,t));
let txt,msg,file;
if(gg){
const read=d=>[...d.querySelectorAll("a[href]")].map(a=>{const m=(a.getAttribute("href")||"").match(/\\/(game|pack|dlc|bundle)\\/([a-z0-9-]+)\\/?(?:[?#].*)?$/);return m&&{kind:m[1],slug:m[2],name:(a.innerText||a.title||"").trim().replace(/\\s+/g," ").slice(0,200)}}).filter(Boolean);
let items=read(document);const base=location.href.split(/[?#]/)[0];
const last=Math.min(30,Math.max(1,...[...document.querySelectorAll("a[href*='page=']")].filter(a=>a.href.split("?")[0]===base).map(a=>+((a.href.match(/[?&]page=(\\d+)/)||[])[1]||1))));
const pages=[];for(let p=2;p<=last;p++){const u=new URL(location.href);u.searchParams.set("page",p);pages.push(u.href)}
for(let i=0;i<pages.length;i++){box.textContent="VR-Navigator: lese Seite "+(i+2)+" von "+(pages.length+1)+" …";await wait(1200);try{const r=await fetch(pages[i],{credentials:"include"});items=items.concat(read(new DOMParser().parseFromString(await r.text(),"text/html")))}catch(e){}}
const by={};items.forEach(x=>{const k=x.kind+":"+x.slug;if(!by[k]||(!by[k].name&&x.name))by[k]=x});items=Object.values(by);
const games=items.filter(x=>x.kind==="game").length;
const found=(document.body.innerText.match(/we found\\s+([\\d.,]+)\\s+results?/i)||[])[1];
txt=JSON.stringify({kind:"gg-wunschliste",hv:${META_HV},at:new Date().toISOString(),page:location.pathname,pages:pages.length+1,shown:found?+found.replace(/[.,]/g,""):null,items});
msg="gg.deals-Wunschliste gelesen: "+games+" Spiele"+(items.length>games?" und "+(items.length-games)+" Pakete oder DLC":"")+" auf "+(pages.length+1)+" Seiten. Der VR-Navigator übernimmt die Spiele.";file="gg-wunschliste.json";
}else{
const wish=/wish/i.test(location.pathname)||/wunschliste|wishlist/i.test(document.title);
const boxes=()=>[document.scrollingElement||document.documentElement,...[...document.querySelectorAll("div,main,section,ul")].filter(e=>e.scrollHeight>e.clientHeight+50&&/(auto|scroll)/.test(getComputedStyle(e).overflowY))];
let h=0,same=0;for(let i=0;i<60&&same<3;i++){const bs=boxes();bs.forEach(e=>{e.scrollTop=e.scrollHeight});await wait(1200);const n=bs.reduce((a,e)=>a+e.scrollHeight,0)+document.querySelectorAll("a[href]").length;same=n===h?same+1:0;h=n;box.textContent="VR-Navigator: lade alles … ("+(i+1)+")"}
boxes().forEach(e=>{e.scrollTop=0});
const links=[...document.querySelectorAll("a[href]")].filter(a=>/\\/(experiences|order)\\//.test(a.href)).slice(0,3000).map(a=>({href:a.href,text:(a.innerText||a.getAttribute("aria-label")||(a.querySelector("img")||{}).alt||"").trim().slice(0,200)}));
txt=JSON.stringify({kind:wish?"meta-wunschliste":"meta-bestellungen",hv:${META_HV},at:new Date().toISOString(),page:location.pathname,links,text:document.body.innerText.slice(0,400000)});
msg=wish?"Wunschliste gelesen. Der VR-Navigator übernimmt sie.":"Seite gelesen. Der VR-Navigator erkennt die Käufe und übernimmt sie.";file=wish?"meta-wunschliste.json":"meta-bestellungen.json";
}
box.textContent="";const p=document.createElement("p");p.style.margin="0 0 8px";p.textContent=msg;
const go=look(document.createElement("button"),true);go.textContent="Im VR-Navigator übernehmen";go.onclick=()=>{window.open(${JSON.stringify(tool)}+"/#meta="+encodeURIComponent(txt),"_blank");box.remove()};
const f=look(document.createElement("button"));f.textContent="Als Datei sichern";f.onclick=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([txt],{type:"application/json"}));a.download=file;document.body.appendChild(a);a.click();a.remove()};
const b=look(document.createElement("button"));b.textContent="Schließen";b.onclick=()=>box.remove();
box.append(p,go,f,b);
})();`; }
const metaBm = () => "javascript:" + encodeURIComponent(metaHelper(location.origin));

const KINDS = {sheet: "Vergleichstabelle", playnite: "Playnite-Export", meta: "Meta-Käufe", metawish: "Meta-Wunschliste", ggwish: "gg.deals-Wunschliste"};
/* Meta-Lesezeichen: Käufe und Wunschliste, beides ohne Datei */
function metaCard(){
  const p = V.prev.meta, lm = S.imports.meta, lw = S.imports.metawish, lg = S.imports.ggwish;
  const info = [lm && `Meta-Käufe ${day(lm.at)}`, lw && `Meta-Wunschliste ${day(lw.at)}`, lg && `gg.deals ${day(lg.at)}`].filter(Boolean).join(", ") || "noch nie";
  // Wie die Browser-Helfer im eShopKompass (0.7.1): Knopf zum Ziehen, „Code kopieren“, Anleitung zum Aufklappen,
  // dann je Seite eine Zeile mit Link und Stand (violett: älter als eine Woche oder nie gelesen)
  const st = x => !x ? `<span class="warnc">noch nie</span>` : `<span class="${(Date.now() - new Date(x.at)) / 864e5 > 7 ? "warnc" : "ok"}">${esc(day(x.at))}</span>`;
  const a = (href, t) => `<a href="${href}" target="_blank" rel="noopener noreferrer">${t}</a>`;
  const rows = [[a("https://www.meta.com/my/orders/?order_type=digital_products&amp;timeFilter=ALL_TIME", "Meta-Bestellungen") + " oder " + a("https://accountscenter.meta.com/meta_pay_wallet/?tab=transactions", "Meta-Pay-Transaktionen"), st(lm), "Käufe"],
    [metaWishLink().replace("deine Wunschliste im Meta Store", "Meta-Wunschliste"), st(lw), "VR-Wünsche"],
    [a("https://gg.deals/wishlist/", "gg.deals-Wunschliste"), st(lg), "PC-Wünsche; der Server sieht dort nur die Prüfseite"]];
  return sub("imp-meta", "Lesezeichen: Meta und gg.deals", info, `
    <span class="bm-w"><a class="bm" href="${esc(metaBm())}" data-act="nobm" title="In die Lesezeichenleiste ziehen">⠿ <b>Seite lesen</b></a>
      <button data-act="bmcopy" title="Für ein von Hand angelegtes Lesezeichen, auch am Handy">Code kopieren</button></span>
    <details class="how" ${foldAttr("bmhow", true)}><summary class="hint">So legst du es an</summary><ul class="hint">
      <li>Am Computer: Lesezeichenleiste einblenden (Strg+Umschalt+B, am Mac ⌘+Umschalt+B) und den Knopf hineinziehen.</li>
      <li>Ohne Ziehen, auch am Handy: „Code kopieren“, ein beliebiges Lesezeichen anlegen, bearbeiten, „Seite lesen“ als Namen und den Code als Adresse einfügen.</li>
      <li>Ein älteres Lesezeichen „Meta lesen“ oder „Seite lesen“ vorher löschen.</li></ul></details>
    <p class="hint">Eine dieser Seiten angemeldet öffnen und das Lesezeichen anklicken. Es scrollt selbst, bis alles geladen ist, dann im Kasten oben rechts „Im VR-Navigator übernehmen“. Die Daten stehen nur in der Adresse hinter #.</p>
    <div class="scroll"><table class="mini-t"><tbody>${rows.map(([l, s, n]) => `<tr><td>${l}</td><td>${s}</td><td class="hint">${n}</td></tr>`).join("")}</tbody></table></div>
    ${p ? previewHtml(p) : ""}`, !!(lm || lw) && !p, "imp-meta");
}
// Die Seite der Wunschliste merkt sich das Tool beim ersten Lesen; davor die Startseite des Stores
function metaWishLink(){
  const page = S.imports?.metawish?.page || "";
  return /^\/(?:[a-z]{2}-[a-z]{2}\/)?experiences\/section\/\d+\/?$/.test(page)
    ? `<a href="https://www.meta.com${esc(page)}" target="_blank" rel="noopener noreferrer">deine Wunschliste im Meta Store</a>`
    : `<a href="https://www.meta.com/de-de/experiences/" target="_blank" rel="noopener noreferrer">deine Wunschliste im Meta Store</a> (im Store oben über dein Profil, „Wunschliste“)`;
}
/* Ein Feld für jede Datei: das Tool erkennt die Art selbst und zeigt erst eine Vorschau */
// Arten, die du im Importfeld von Hand wählen kannst, wenn die Erkennung danebenliegt
const FILE_KINDS = {sheet: "Vergleichstabelle", playnite: "Playnite-Export", ggwish: "gg.deals-Wunschliste (CSV)",
  meta: "Meta (Lesezeichen, Text)", opinions: "Meinungen"};
function fileCard(){
  const p = V.prev.file, last = ["sheet", "playnite", "ggwish"].map(k => S.imports[k] && `${KINDS[k]} ${day(S.imports[k].at)}`).filter(Boolean);
  return sub("imp-file", "Datei oder Text einlesen", last.join(", ") || "noch nie", `
    <p class="hint">Vergleichstabelle (CSV), Playnite-Export (CSV), eine gg.deals-Wunschliste (CSV), die Datei des Meta-Lesezeichens, kopierter Text deiner Meta-Bestellungen oder eine Meinungen-Datei aus der Recherche. Das Tool erkennt die Art am Aufbau und zeigt erst, was es übernehmen würde.</p>
    <div class="bar"><input type="file" accept=".csv,.json,.txt,text/csv,application/json,text/plain" data-file="file" aria-label="Datei wählen">
      <label class="kind">Art <select id="kind-file">${[["auto", "erkennen"], ...Object.entries(FILE_KINDS)].map(([k, l]) => `<option value="${k}" ${V.kindFile === k ? "selected" : ""}>${l}</option>`).join("")}</select></label></div>
    <textarea id="txt-file" aria-label="Inhalt einfügen" placeholder="… oder Inhalt hier einfügen">${esc(V.txt?.file || "")}</textarea>
    <div class="bar"><button data-act="preview" data-v="file">Vorschau</button>
      ${p && !p.error && !p.done ? `<button class="primary" data-act="apply" data-v="file">${p.collection ? "Übernehmen" : p.n + " übernehmen"}</button>` : ""}</div>
    ${p ? previewHtml(p) : ""}`, !p && !V.txt?.file, "imp-file");
}
/* Retro-Sammlung: Dateinamen aus dem ROM-Ordner, erst als Vorschau. Die Ordnerwahl liest nur Namen. */
const RETRO_LINUX = `cd "/pfad/zu/ROMs"
find . -type f -not -path '*_zip/*' -not -path '*/saves/*' -printf '%P\\n' > ~/retro-liste.txt`;
const RETRO_WIN = `$r = "E:\\pfad\\zu\\ROMs"
Get-ChildItem $r -Recurse -File | Where-Object { $_.FullName -notmatch '_zip\\\\|\\\\saves\\\\' } | ForEach-Object { $_.FullName.Substring($r.Length + 1) } | Set-Content -Encoding utf8 "$HOME\\retro-liste.txt"`;
function retroCard(){
  const p = V.prev.retro, l = S.imports.retro;
  const info = l ? `${l.n} Spiele, ${day(l.at)}${l.gone ? `, ${l.gone} nicht mehr in der Liste` : ""}` : "noch nie";
  return sub("imp-retro", "Retro-Sammlung (ROM-Liste)", info, `
    <p class="hint">Wähl deinen ROM-Ordner. Der Browser gibt dem Tool nur Datei- und Ordnernamen und lädt keine Spiele hoch. Ordner, die auf „_zip“ enden, Spielstände und Beiwerk zählen nicht, Pfade speichert das Tool nicht. Jedes Spiel steht danach einmal je System in der Sammlung, mit Region und Sprache aus dem Dateinamen (No-Intro, Redump).</p>
    <div class="bar"><label class="btn quiet">ROM-Ordner wählen <input type="file" webkitdirectory multiple data-file="retrodir" class="vh"></label></div>
    <details class="op"><summary>Liste stattdessen per Befehl erstellen</summary>
      <p class="hint">Linux (Terminal), danach die Datei unten einfügen:</p><pre class="log">${esc(RETRO_LINUX)}</pre>
      <p class="hint">Windows (PowerShell):</p><pre class="log">${esc(RETRO_WIN)}</pre>
      <p class="hint">Auch eine CSV mit den Spalten „System“ und „Titel“ geht.</p></details>
    <textarea id="txt-retro" aria-label="Liste einfügen" placeholder="… oder die Liste hier einfügen">${esc(V.txt?.retro || "")}</textarea>
    <div class="bar"><button data-act="preview" data-v="retro">Vorschau</button>
      ${p && !p.error && !p.done ? `<button class="primary" data-act="apply" data-v="retro">${p.n} übernehmen</button>` : ""}</div>
    ${p ? retroPreview(p) : ""}`, !p && !V.txt?.retro, "imp-retro");
}
function retroPreview(p){
  if(p.error) return `<p class="err">${esc(p.error)}</p>`;
  const sy = Object.entries(p.systems || {}).map(([n, c]) => `${esc(n)} ${c}`).join(", ");
  const sk = p.skipped || {}, skip = [sk.archive && `${sk.archive} in Archiv-Ordnern`, sk.save && `${sk.save} Spielstände`, sk.extra && `${sk.extra} Beiwerk`].filter(Boolean).join(", ");
  const gone = p.gone_n ? `<p class="hint">Nicht mehr in der Liste (${p.gone_n}): ${p.gone.slice(0, 40).map(esc).join(", ")}${p.gone_n > 40 ? " …" : ""}. ${p.done ? "Im Reiter Sammlung übernimmst du den Stand oder behältst sie." : "Sie werden nicht gelöscht, sondern im Reiter Sammlung markiert."}</p>` : "";
  const unk = p.unknown_n ? `<p class="hint">Nicht erkannt (${p.unknown_n}): ${p.unknown.map(esc).join(", ")}${p.unknown_n > p.unknown.length ? " …" : ""}</p>` : "";
  // Deine Ordner-Listen (0.8.8): wie viele Zeilen passen, was nur in der Liste steht, was in der Liste fehlt
  const o = p.own, more = (l, n) => `${l.slice(0, 30).map(esc).join(", ")}${n > 30 ? " …" : ""}`;
  const own = o ? `<p class="hint">Deine Ordner-Listen (${o.systems.map(esc).join(", ")}): ${o.matched} von ${o.rows} Zeilen passen zu einer Datei. Titel und Genre daraus gelten zuerst.${o.extra_n ? ` Nur in der Liste, ohne Datei (${o.extra_n}): ${more(o.extra, o.extra_n)}.` : ""}${o.missing_n ? ` Datei da, aber nicht in der Liste (${o.missing_n}): ${more(o.missing, o.missing_n)}.` : ""}</p>` : "";
  const size = p.size ? ` Zusammen ${mb(p.size)}.` : "";
  if(p.done) return `<p class="ok">Retro-Liste übernommen: ${p.n} Spiele (${sy}), ${p.new} neu.</p>${own}${gone}`;
  return `<div class="prev"><b>Retro-Liste</b>: ${p.files} Dateien ergeben ${p.n} Spiele (${sy}), davon ${p.new} neu.${size}${skip ? ` Übersprungen: ${skip}.` : ""} Noch nichts gespeichert.${own}${unk}${gone}<ul>${p.entries.map(e =>
    `<li><span class="${e.known ? "" : "new"}">${esc(e.name)}</span> <span class="b">${esc(e.system)}</span> ${langBadge(e)}${e.files > 1 ? ` <span class="hint">${e.files} Dateien</span>` : ""}${e.known ? " · schon vorhanden" : ""}</li>`).join("")}</ul>${p.n > p.entries.length ? `<p class="hint">… und ${p.n - p.entries.length} weitere</p>` : ""}</div>`;
}
/* Konten: bei jedem Abgleich automatisch gelesen */
function accountsCard(){
  const se = S.settings || {};
  const on = [se.steam_id && "Steam", (se.gg_wish_set || se.gg_key_set) && "gg.deals", se.igdb_set && "IGDB", se.nexus_set && "Nexus Mods", se.sharenite && "Sharenite"].filter(Boolean);
  return sub("konten", "Konten und Schlüssel", on.length ? on.join(", ") : "keins eingerichtet", `<form data-form="accounts" class="form acc" style="margin-top:8px">
      <label for="a-sid">SteamID oder Profil-Link</label><input type="text" id="a-sid" name="steam_id" value="${esc(se.steam_id || "")}" placeholder="https://steamcommunity.com/profiles/7656…">
      <label for="a-skey">Steam-Schlüssel</label><input type="password" id="a-skey" name="steam_key" autocomplete="off" placeholder="${se.steam_key_set ? "gespeichert, leer lassen zum Behalten" : "für den Besitz; Wunschliste geht auch ohne"}">
      ${se.steam_key_set ? `<span class="clr"><label><input type="checkbox" name="steam_clear"> Steam-Schlüssel löschen</label></span>` : ""}
      <span class="clr"><label><input type="checkbox" name="steam_wish"${se.steam_wish === false ? "" : " checked"}> Steam-Wunschliste lesen (aus, wenn du sie nicht pflegst und am PC gg.deals nutzt)</label></span>
      <label for="a-gw">gg.deals-Wunschliste</label><input type="password" id="a-gw" name="gg_wish" autocomplete="off" placeholder="${se.gg_wish_set ? "gespeichert, leer lassen zum Behalten" : "Link aus „Wunschliste teilen“"}">
      ${se.gg_wish_set ? `<span class="clr"><label><input type="checkbox" name="gg_wish_clear"> Link löschen</label></span>` : ""}
      <label for="a-gg">gg.deals-Schlüssel</label><input type="password" id="a-gg" name="gg_key" autocomplete="off" placeholder="${se.gg_key_set ? `gespeichert${se.gg_key_end ? " (…" + esc(se.gg_key_end) + ")" : ""}, leer lassen zum Behalten` : "für Händlerpreise; kostenlos auf gg.deals unter Einstellungen, API"}">
      ${se.gg_key_set ? `<span class="clr"><label><input type="checkbox" name="gg_clear"> gg.deals-Schlüssel löschen</label></span>` : ""}
      <label for="a-ii">IGDB Client-ID</label><input type="password" id="a-ii" name="igdb_id" autocomplete="off" placeholder="${se.igdb_set ? "gespeichert, leer lassen zum Behalten" : "derselbe Twitch-Schlüssel wie im eShopKompass"}">
      <label for="a-is">IGDB Secret</label><input type="password" id="a-is" name="igdb_secret" autocomplete="off" placeholder="${se.igdb_set ? "gespeichert, leer lassen zum Behalten" : "Client-Secret der Twitch-App"}">
      ${se.igdb_set ? `<span class="clr"><label><input type="checkbox" name="igdb_clear"> IGDB-Schlüssel löschen</label></span>` : ""}
      <label for="a-nx">Nexus-Mods-Schlüssel</label><input type="password" id="a-nx" name="nexus_key" autocomplete="off" placeholder="${se.nexus_set ? "gespeichert, leer lassen zum Behalten" : "persönlicher API-Schlüssel (nexusmods.com, Einstellungen, API Keys)"}">
      ${se.nexus_set ? `<span class="clr"><label><input type="checkbox" name="nexus_clear"> Nexus-Schlüssel löschen</label></span>` : ""}
      <label for="a-sn">Sharenite-Profil</label><input type="text" id="a-sn" name="sharenite" value="${esc(se.sharenite || "")}" placeholder="https://www.sharenite.link/profiles/…/games">
      <span class="full"><button class="primary">Speichern</button> <span class="err" id="a-err"></span></span></form>
    <ul class="hint">
      <li><b>Steam:</b> Besitz und Wunschliste mit genauen App-IDs; die Wunschliste lässt sich abschalten, dann zählt am PC nur gg.deals. Den Schlüssel gibt es kostenlos unter steamcommunity.com/dev/apikey (als Domain genügt „localhost“, Steam prüft sie nicht; den Schlüssel niemandem geben, widerrufen geht dort jederzeit); im Profil müssen die Spieldetails öffentlich sein. Ohne Schlüssel liest das Tool nur die Wunschliste. Neue Apps prüft es im Store auf VR (40 je Abgleich).</li>
      <li><b>gg.deals:</b> der Schlüssel holt Händlerpreise je Steam-App; die geteilte Wunschliste bringt Titel, die das Tool kennt oder als VR-App bei Steam findet.</li>
      <li><b>IGDB:</b> Spielinfos für alle Plattformen (Genre, Spieler, Wertung, Spielzeit, Beschreibung). Client-ID und Secret einer kostenlosen Twitch-Entwickler-App (dev.twitch.tv, Anwendung registrieren); derselbe Schlüssel wie im eShopKompass geht. Bis 0.7 nur im Verbindungstest.</li>
      <li><b>Nexus Mods:</b> Mods für PC-Spiele, etwa VR-Mods. Die Abfrage geht auch ohne Schlüssel; mit dem persönlichen Schlüssel (im Nexus-Konto unter Einstellungen, API Keys) fragt das Tool als dein Konto mit eigenen Grenzen. Bis 0.7.7 nur im Verbindungstest.</li>
      <li><b>Sharenite:</b> deine Playnite-Bibliothek aller Läden (Steam, GOG, Epic …), wenn das Profil öffentlich ist. Übernommen werden Spiele mit VR-Schlagwort, höchstens alle 20 Stunden.</li>
    </ul>
    <p class="hint">Steht ein Titel auf keiner Wunschliste mehr, die ihn geführt hat, fällt er von deiner; das steht im Protokoll. Schlüssel und Wunschlisten-Link bleiben auf deinem Server (settings.json im Datenordner), stehen nicht in der Sicherung und gehen nie an den Browser zurück.</p>`, on.length > 0, "konten");
}
function wishMoves(p){
  return [p.wish_added?.length && `Neu auf der Wunschliste: ${p.wish_added.map(esc).join(", ")}.`,
    p.wish_removed?.length && `Nicht mehr auf dieser Wunschliste und damit von deiner: ${p.wish_removed.map(esc).join(", ")}.`,
    p.unknown?.length && (p.pc_n != null
      ? `Noch kein VR-Titel im Tool (${p.unknown.length}): ${p.unknown.slice(0, 30).map(esc).join(", ")}${p.unknown.length > 30 ? " …" : ""}. Sie stehen auf der PC-Wunschliste; der nächste Abgleich fragt bei Steam, ob sie VR können.`
      : `Nicht zugeordnet (${p.unknown.length}): ${p.unknown.slice(0, 30).map(esc).join(", ")}${p.unknown.length > 30 ? " …" : ""}.`)]
    .filter(Boolean).map(x => `<p class="hint">${x}</p>`).join("");
}
function previewHtml(p){
  if(p.error) return `<p class="err">${esc(p.error)}</p>`;
  // Einfach gesagt (0.7.2): erst, was in die Sammlung kommt, dann was bleibt, dann die VR-Titel
  const pc = p.collection, sy = Object.entries(pc?.systems || {});
  const per = sy.length > 1 ? ` (${sy.map(([n, c]) => `${esc(n)} ${num(c)}`).join(", ")})` : sy.length ? ` (${esc(sy[0][0])})` : "";
  const col = !pc ? "" : (pc.n ? ` Für die Sammlung: ${num(pc.n)} Spiele${per}, ${pc.new === pc.n ? "alle neu" : `davon ${num(pc.new)} neu`}.${pc.kept ? ` Deine anderen ${num(pc.kept)} Spiele bleiben, wie sie sind.` : ""}`
    : ` Die Sammlung bleibt, wie sie ist${pc.kept ? ` (${num(pc.kept)} Spiele)` : ""}.`);
  // Playnite: die erste Zahl zählt nur VR-Titel für Sammlung (VR) und Wunschliste
  const found = pc ? (p.n ? ` VR-Titel: ${p.n}, davon ${p.new} neu.` : " VR-Titel: keine darin.") : `${p.n} erkannt, davon ${p.new} neu.`;
  // gg.deals (0.8.7): erst die ganze PC-Wunschliste, dann wie viele davon VR-Titel im Tool sind
  const gg = p.pc_n != null ? ` ${num(p.pc_n)} Einträge für die PC-Wunschliste (${[`${num(p.pc_n - (p.pc_kinds?.pack || 0) - (p.pc_kinds?.dlc || 0))} Spiele`, p.pc_kinds?.pack && `${num(p.pc_kinds.pack)} Pakete`, p.pc_kinds?.dlc && `${num(p.pc_kinds.dlc)} DLC`].filter(Boolean).join(", ")}), davon ${num(p.n - (p.unknown?.length || 0))} VR-Titel im Tool.` : "";
  const mark = e => p.pc_n != null ? (e.known ? " · VR-Titel" : " · PC") : e.known ? " · war schon da" : " · neu";
  if(p.done) return `<p class="ok">${p.what ? esc(p.what) + " übernommen" : "Übernommen"}${pc || gg ? "." : ":"}${pc ? `${col}${found}` : gg || ` ${p.n} erkannt, ${p.new} neu angelegt.`}</p>` + wishMoves(p) + (p.entries?.length ? `<details class="prev"><summary class="hint">Was übernommen wurde</summary><ul>${p.entries.slice(0, 600).map(e =>
    `<li><span class="${e.known ? "" : "new"}">${esc(e.name)}</span>${e.price != null ? ` ${eur(e.price)}` : ""}${mark(e)}</li>`).join("")}</ul></details>` : "");
  return `<div class="prev">${p.what ? `<b>${esc(p.what)}</b>${p.kind ? ` <span class="hint">(${p.guess ? "geraten, unter „Art“ änderbar" : "erkannt"})</span>` : ""}${pc ? "." : ":"} ` : ""}${pc ? `${col}${found}`.trim() : found} Noch nichts gespeichert.${p.note ? ` <span class="hint">${esc(p.note)}</span>` : ""}<ul>${p.entries.slice(0, 300).map(e =>
    `<li><span class="${e.known ? "" : "new"}">${esc(e.name)}</span>${e.meta_id ? ` <span class="b">Meta-ID</span>` : ""}${e.steam_appid ? ` <span class="b${e.steam_sure === false ? " warn" : ""}">Steam ${esc(e.steam_appid)}${e.steam_sure === false ? " ≈" : ""}</span>` : ""}${e.price != null ? ` ${eur(e.price)}` : ""}${e.known ? " · schon vorhanden" : ""}</li>`).join("")}</ul></div>`;
}
/* ---------------------------------------------------------------- Bearbeiten */
/* Herkunft eines Titels, etwa „Vergleichstabelle, Zeile 128 (21.10.2026)“; vermutet heißt: aus
   der Zeit vor 0.3.4, abgeleitet aus Besitz, Wunschquellen und Importzeitpunkt */
const originText = r => (r.origin || []).map(o => `${esc(o.label)}${o.detail ? ", " + esc(o.detail) : ""}${o.at ? " (" + day(o.at) + ")" : ""}${o.guess ? " ≈" : ""}`).join(" · ");
/* Inhalt eines Bundles: je Spiel ein Feld für Name oder Link, „+“ fügt eines an */
const bundleField = v => `<input type="text" name="contains" value="${esc(v)}" placeholder="Name oder Link (Meta, QuestStoreDB, VRDB, Steam)" aria-label="Spiel im Bundle">`;
function bundleEdit(r){
  const items = (r.contains || []).map(x => x.name);
  return `<details class="op" ${r.bundle || items.length ? "open" : ""}><summary>${r.bundle || items.length ? "Inhalt des Bundles" : "Ist das ein Bundle? Inhalt eintragen"}</summary>
    <div class="bundle" id="f-bundle">${(items.length ? items : [""]).map(bundleField).join("")}</div>
    <button type="button" data-act="bundleadd" title="Weiteres Spiel im Bundle">+ Spiel</button>
    <p class="hint">Jedes Spiel wird ein eigener Titel, mit dem Bundle als Herkunft. Besitzt du das Bundle, besitzt du die Spiele darin.</p></details>`;
}
function openEdit(key){
  const r = S.library.concat(S.wishlist, (S.todo || []).map(x => x.row)).find(x => x.key === key);
  if(!r) return;
  // Eigene Angabe oder „automatisch“: dann gilt VRDB, sonst deine Tabelle, sonst die Recherche
  const cb = r.crossbuy_hand === true ? "yes" : r.crossbuy_hand === false ? "no" : "";
  const auto = r.crossbuy != null && r.crossbuy_src !== "Hand" ? `automatisch (${r.crossbuy ? "ja" : "nein"} laut ${r.crossbuy_src})` : "automatisch (unbekannt)";
  $("edit").innerHTML = `<form method="dialog" data-form="edit" data-k="${esc(key)}"><h2>${esc(r.name)}</h2>
    <div class="form">
      <label for="f-name">Name</label><input type="text" id="f-name" name="name" value="${esc(r.name)}" required>
      <label for="f-meta">Meta-ID</label><input type="text" id="f-meta" name="meta_id" value="${esc(r.meta_id)}" inputmode="numeric" placeholder="Zahl oder Link (Meta, QuestStoreDB, VRDB)">
      <label for="f-steam">Steam-App-ID</label><input type="text" id="f-steam" name="steam_appid" value="${esc(r.steam_appid)}" inputmode="numeric">
      <label for="f-cb">Crossbuy</label><select id="f-cb" name="crossbuy"><option value="">${esc(auto)}</option><option value="yes" ${cb === "yes" ? "selected" : ""}>ja (von Hand)</option><option value="no" ${cb === "no" ? "selected" : ""}>nein (von Hand)</option></select>
      <span class="full"><label><input type="checkbox" name="wish" ${r.wish ? "checked" : ""}> auf der Wunschliste</label>
        <label><input type="checkbox" name="owned_meta" ${r.where === "meta" || r.where === "beide" ? "checked" : ""}> besitze ich bei Meta</label>
        <label><input type="checkbox" name="owned_pc" ${r.where === "pc" || r.where === "beide" ? "checked" : ""}> besitze ich am PC</label></span>
      <label class="full" for="f-note">Notiz, etwa Meinungen von Reddit mit Link</label>
      <textarea class="full" id="f-note" name="note">${esc(r.note)}</textarea>
    </div>
    ${bundleEdit(r)}
    <p class="hint">Trägt ein anderer Titel dieselbe ID, werden beide zusammengeführt.</p>
    ${r.origin?.length ? `<p class="hint">Herkunft: ${originText(r)}</p>` : ""}
    <p class="err" id="f-err"></p>
    <div class="actions"><button type="button" class="danger" data-act="del" data-k="${esc(key)}">Löschen</button><span class="sp"></span>
      <button type="button" data-act="close">Abbrechen</button><button class="primary" value="save">Speichern</button></div></form>`;
  $("edit").showModal();
}

/* Kopfleiste beim Scrollen (wie im eShopKompass): nach unten erst 300 px mitkommen, dann ausblenden;
   40 px nach oben zeigen sie wieder. Kleine Gegenbewegungen (Touchpad) unter 8 px zählen nicht als
   Richtungswechsel. --stick sagt der Sprungleiste, wie viel Platz die Kopfleiste gerade belegt. */
(function(){
  let lastY = scrollY, turn = scrollY, dir = 0, hidden = false;
  const set = hid => {
    hidden = hid; const el = $("stick");
    el.classList.toggle("hid", hid);
    document.documentElement.style.setProperty("--stick", hid ? "0px" : el.offsetHeight + "px");
  };
  addEventListener("scroll", () => {
    const y = scrollY;
    if(Math.abs(y - lastY) < 8 && y > 60) return;
    const d = Math.sign(y - lastY);
    if(d !== dir){ dir = d; turn = lastY; }          // Richtung gewechselt: ab hier messen
    if(dir > 0 && !hidden && y > 300 && y - turn > 300 && $("thmMenu").hidden) requestAnimationFrame(() => set(true));
    else if(dir < 0 && hidden && (turn - y > 40 || y < 60)) requestAnimationFrame(() => set(false));
    lastY = y;
  }, {passive: true});
  addEventListener("resize", () => set(hidden));
  set(false);
})();

/* ---------------------------------------------------------------- Ereignisse */
let poll = null;
function watchSync(){
  // Läuft ein Abgleich, alle 2 Sekunden Schritt und Protokoll holen; am Ende alles neu laden
  if(!S?.sync?.running || poll) return;
  poll = setInterval(async () => {
    let st;
    try{ st = await api("/api/status"); }catch(e){ return; }
    S.sync = st;
    if(!st.running){
      clearInterval(poll); poll = null;
      C = null;           // Sammlung neu laden: der Abgleich hat sie ergänzt (0.7.6, sonst galt bis zum Neuladen der alte Stand)
      await load();
      toast(st.ok === false ? "Abgleich mit Fehlern beendet" : "Abgleich fertig");
      return;
    }
    renderNav(); showLog();
  }, 2000);
}
async function load(){
  try{ S = await api("/api/state"); }
  catch(e){ $("main").innerHTML = `<p class="err">Server nicht erreichbar: ${esc(e.message)}</p>`; return; }
  if(!document.querySelector("dialog[open]")) render();
  watchSync();
}
/* Vom Lesezeichen „Meta-Käufe lesen“: Daten im Adressteil hinter #meta=, sofort aus der Adresse
   entfernen. Übernommen wird direkt (das Lesezeichen ist dein Klick); was neu war, steht in der
   Karte Meta-Bestellungen. */
const META_IN = location.hash.startsWith("#meta=") ? (() => { try{ return decodeURIComponent(location.hash.slice(6)); }catch(e){ return ""; } })() : null;
if(META_IN !== null) history.replaceState(null, "", location.pathname + location.search);
async function metaHandOver(){
  V.tab = "settings"; V.folds["imp-meta"] = false;
  try{
    const res = await api("/api/import", {kind: "meta", text: META_IN, dry: false});
    S = res.state || S;
    V.prev.meta = Object.assign({done: true}, res, {state: null});
    toast(res.n ? `${res.what || "Meta-Käufe"}: ${res.n} gelesen, ${res.new} neu` : "Nichts erkannt. Bitte die Seite neu laden und noch einmal versuchen");
  }catch(e){ V.prev.meta = {error: e.message}; }
  render();
  $("imp-meta")?.scrollIntoView({block: "start"});
}
/* Offene Seite hält sich selbst aktuell: jede Minute den Stand prüfen */
setInterval(async () => {
  if(!S || poll || document.hidden) return;
  try{
    const st = await api("/api/status");
    if(st.running){ S.sync = st; renderNav(); watchSync(); }
    else if(st.finished !== (S.sync || {}).finished && !document.activeElement?.matches("input,textarea,select")) await load();
    else renderHead();
  }catch(e){}
}, 60000);
// Schickt eine Änderung, zeichnet neu und gibt die Antwort zurück (mit undo, wo es eins gibt)
async function act(path, body, errEl){
  try{ const r = await api(path, body); S = r; render(); return r; }
  catch(e){ if(errEl) errEl.textContent = e.message; else alert(e.message); return null; }
}
const undoTo = res => res?.undo ? () => act("/api/title/restore", {titles: res.undo}).then(r => r && toast("Zurückgenommen")) : null;

document.addEventListener("click", async ev => {
  const el = ev.target.closest("[data-act]");
  if(!el) return;
  const a = el.dataset.act, v = el.dataset.v;
  if(a === "nobm"){ ev.preventDefault(); toast("Bitte in die Lesezeichenleiste ziehen, nicht anklicken"); return; }
  if(a === "bmcopy"){ copyNow(metaBm()); toast("Code kopiert. Jetzt ein Lesezeichen anlegen und den Code als Adresse einfügen"); return; }
  if(a === "thm") themeMenu($("thmMenu").hidden);
  else if(a === "thmset") setTheme(v);
  else if(a === "tab"){ V.tab = v; V.q = ""; if(V.d) V.d.q = ""; render(); scrollTo(0, 0); }
  else if(a === "lf"){ V.lf[v] = !V.lf[v]; render(); }
  else if(a === "legend"){ V.legend = !V.legend; render(); }
  else if(a === "addopen"){ V.add = !V.add; render(); if(V.add) document.querySelector("form[data-form=add] input")?.focus(); }
  else if(a === "gopen"){
    // Aufgeklappt rückt das Fenster nach, bis die Einzelheiten ganz zu sehen sind (wie im eShopKompass)
    const k = el.dataset.s;
    if(V.gAll){ if(V.gShut.has(k)) V.gShut.delete(k); else V.gShut.add(k); render(); return; }
    V.gOpen = V.gOpen === k ? null : k; render();
    const gd = V.gOpen && document.querySelector(".gd");
    if(gd){ const r = gd.getBoundingClientRect(); if(r.bottom > innerHeight) scrollBy(0, Math.min(r.bottom - innerHeight + 12, r.top - 120)); }
  }
  else if(a === "pwopen"){ V.pwOpen = V.pwOpen === el.dataset.s ? null : el.dataset.s; render(); }
  else if(a === "nowk"){ V.nowKind = v || ""; render(); }
  else if(a === "gdesc"){ if(String(getSelection() || "").trim()) return; V.gDesc = V.gDesc === el.dataset.s ? null : el.dataset.s; render(); }
  else if(a === "gall"){ V.gAll = !!v; V.gShut.clear(); V.gOpen = null; render(); }
  else if(a === "gmark"){
    // Sofort zeigen, dann speichern; ein Fehler lädt den Stand des Servers neu
    const key = el.dataset.s, k = el.dataset.k, val = k === "fav" ? !!v : v || null;
    const m = Object.assign({}, (S.marks = S.marks || {})[key]);
    if(val) m[k] = val; else delete m[k];
    if(Object.keys(m).length) S.marks[key] = m; else delete S.marks[key];
    render();
    api("/api/mark", {key, k, v: val}).then(r => { S.marks = r.marks; }).catch(e => { toast(e.message); load(); });
  }
  else if(a === "tsort"){
    // data-d0="-1": erster Klick absteigend, etwa bei Wertungen; dritter Klick zurück zur gewählten Sortierung
    const t = el.dataset.t, k = el.dataset.k, cur = V.sorts[t], d0 = Number(el.dataset.d0) || 1;
    if(!cur || cur.k !== k) V.sorts[t] = {k, dir: d0};
    else if(cur.dir === d0) cur.dir = -d0;
    else delete V.sorts[t];
    const kb = document.activeElement?.matches("[data-act=tsort]");
    render();
    if(kb) document.querySelector(`[data-act="tsort"][data-t="${CSS.escape(t)}"][data-k="${CSS.escape(k)}"]`)?.focus();
  }
  else if(a === "dmix"){ setMix(v); render(); }
  else if(a === "dmixoff" || a === "dpickoff"){
    // Mischung zurücknehmen: Vorschläge weg; ihre Filter bleiben nur bei „Schließen“
    if(a === "dmixoff" && V.d.mix !== "surprise") V.d = Object.assign({}, D0, {sys: V.d.sys}); else V.d.mix = "";
    render();
  }
  else if(a === "dgoff" || a === "dmpoff" || a === "dhowoff"){ const f = a === "dgoff" ? "g" : a === "dhowoff" ? "how" : "mp"; V.d[f] = V.d[f].filter(x => x !== v); V.d.mix = ""; V.d.n = D0.n; render(); }
  else if(a === "dgop"){ V.d.gop = v; V.d.mix = ""; V.d.n = D0.n; V.menu = "g"; render(); }
  else if(a === "dgclear"){ V.d.g = []; V.d.mix = ""; V.d.n = D0.n; V.menu = "g"; render(); }
  else if(a === "dreset"){ V.d = Object.assign({}, D0, {sort: V.d.sort, sys: V.d.sys}); delete V.sorts.find; render(); }
  // Suche gilt nur im Reiter, in dem sie steht (0.8.7)
  else if(a === "wsub"){ V.wsub = v === "pc" ? "pc" : "vr"; V.q = ""; render(); }
  else if(a === "dsys"){
    // Ein anderer Reiter hat andere Spalten: Sortierung nach Spalte und Filter, die es dort nicht gibt, fallen weg
    V.d.sys = v; V.d.q = ""; V.d.sw = ""; V.d.how = []; V.d.hr = 0; V.d.usk = ""; V.d.st = ""; V.d.cb = 0; V.d.vm = 0; V.d.wh = 0; V.d.vr = 0; V.d.n = D0.n; V.gOpen = null; V.gAll = false; V.gShut.clear(); delete V.sorts.find;
    if(V.d.mix && !(v === "VR" ? MIXES.find(x => x[0] === V.d.mix)?.[4] : true)) V.d = Object.assign({}, D0, {sys: v, sort: V.d.sort});
    if(V.d.mix) V.d.seed = newSeed();
    render();
  }
  else if(a === "dshuffle"){ V.d.seed = newSeed(); render(); }
  else if(a === "dmore"){ V.d.n += D0.n; render(); }
  else if(a === "dqclear"){ V.d.q = ""; render(); $("dq")?.focus(); }
  else if(a === "qclear"){ V.q = ""; render(); $("q")?.focus(); }
  else if(a === "foldall"){ $("main").querySelectorAll("details[data-kc]").forEach(d => { d.open = !!v; keepFold(d); }); saveView(); }
  else if(a === "golists"){
    V.tab = "settings"; render();
    const c = $("todo"); c?.scrollIntoView({block: "start"});
  }
  else if(a === "jump"){
    ev.preventDefault();
    const c = $(v), d = c?.matches("details") ? c : null;
    if(d) d.open = true;
    c?.scrollIntoView({block: "start"});
  }
  else if(a === "pickrestore") $("restoreFile").click();
  else if(a === "edit") openEdit(el.dataset.k);
  else if(a === "bundleadd"){ $("f-bundle").insertAdjacentHTML("beforeend", bundleField("")); $("f-bundle").lastElementChild.focus(); }
  else if(a === "close") $("edit").close();
  else if(a === "del"){
    // Kein Rückfrage-Fenster: gelöscht wird sofort, der Hinweis bietet „Rückgängig“
    const name = $("f-name")?.value || "Titel";
    const res = await act("/api/title/delete", {key: el.dataset.k});
    if(res){ $("edit").close(); toast(`„${name}“ gelöscht`, undoTo(res)); }
  }
  else if(a === "sync"){ if(await act("/api/sync", el.dataset.v === "fast" ? {fast: true} : {})) watchSync(); }
  else if(a === "diag"){
    V.diagRunning = true; render();
    // 0.8.0: der Test läuft auf dem Server weiter, die Seite fragt alle zwei Sekunden nach (kein 504 mehr)
    try{
      let d = await api("/api/diag", {}), miss = 0;
      while(d.running){
        await new Promise(r => setTimeout(r, 2000));
        try{ d = await api("/api/diag"); miss = 0; }
        catch(e){ if(++miss > 5) throw e; }
      }
      if(d.error || !d.lines) throw new Error(d.error || "keine Antwort");
      V.diag = d.lines; V.diagAt = clock(new Date());
    }
    catch(e){ V.diag = ["Test fehlgeschlagen: " + e.message]; }
    V.diagRunning = false; render();
  }
  else if(a === "gcopy"){ ev.stopPropagation(); copyNow((G_SHOWN?.rows || []).map(g => g.name).join("\n")); }
  else if(a === "gdl") gExport();
  else if(a === "copy") copyNow(v === "diag" ? (V.diag || []).join("\n") : logText());
  else if(a === "showlog"){
    V.tab = "settings"; V.folds.logbox = false; render();
    $("logfold")?.scrollIntoView({block: "start"});
  }
  else if(a === "unwish"){
    const k = el.dataset.k, name = (S.wishlist.find(r => r.key === k) || {}).name || "Titel";
    if(await act("/api/title", {key: k, wish: false})) toast(`„${name}“ von der Wunschliste genommen`, () => act("/api/title", {key: k, wish: true}));
  }
  else if(a === "merge"){ const res = await act("/api/merge", {keep: el.dataset.a, gone: el.dataset.b}); if(res) toast("Zusammengeführt", undoTo(res)); }
  else if(a === "notsame") act("/api/not_same", {a: el.dataset.a, b: el.dataset.b});
  else if(a === "steamok") act("/api/title", {key: el.dataset.k, steam_sure: true});
  else if(a === "retrogone"){
    try{
      const res = await api("/api/retro/gone", {action: v});
      C = res.collection; if(S.imports.retro) S.imports.retro.gone = 0;
      toast(v === "drop" ? `${res.changed} Spiele aus der Sammlung entfernt` : `${res.changed} Spiele behalten`);
    }catch(e){ toast(e.message); }
    render();
  }
  else if(a === "nearok" || a === "nearno"){
    const k = el.dataset.k, x = (S.retro_near || []).find(y => y.key === k) || {};
    try{
      const res = await api("/api/retro/near", {key: k, ok: a === "nearok"});
      C = res.collection; S.retro_near = res.retro_near;
      toast(a === "nearok" ? `„${x.name}“ gilt jetzt als „${x.near}“` : `Vorschlag für „${x.name}“ verworfen`);
    }catch(e){ toast(e.message); }
    render();
  }
  else if(a === "lists"){
    const keys = el.dataset.keys.split(",").filter(Boolean);
    const res = await act("/api/wishes", {kind: v, keys});
    if(res) toast(`${res.changed} ${res.changed === 1 ? "Titel" : "Titel"} ${{keep: "behalten", drop: "von der Wunschliste genommen", wish: "wieder gewünscht"}[v]}`, undoTo(res));
  }
  else if(a === "ownok"){
    const k = el.dataset.k;
    const res = await api("/api/retro/own", k ? {key: k} : {all: true});
    C = res.collection; S.retro_own = res.retro_own;
    toast(k ? "Deine Liste gilt" : "Deine Liste gilt für alle");
    render();
  }
  else if(a === "steamwrong"){
    const k = el.dataset.k, x = (S.todo || []).find(y => y.key === k) || {};
    if(await act("/api/title", {key: k, steam_appid: ""})) toast(`Steam-ID von „${x.name || "Titel"}“ entfernt`, x.steam_appid ? () => act("/api/title", {key: k, steam_appid: x.steam_appid}) : null);
  }
  else if(a === "preview" || a === "apply"){
    const text = $("txt-" + v).value;
    V.txt = Object.assign(V.txt || {}, {[v]: text});
    el.disabled = true;
    try{
      if(v === "file") V.kindFile = $("kind-file")?.value || "auto";
      const res = await api("/api/import", Object.assign({kind: v === "file" ? V.kindFile || "auto" : v, text, dry: a === "preview"}, v === "retro" && V.retroLists?.length ? {lists: V.retroLists} : {}));
      V.prev[v] = a === "apply" ? Object.assign({done: true}, res, {state: null}) : res;
      if(res.state) S = res.state;
      if(a === "apply"){ V.txt[v] = ""; if(v === "retro") V.retroLists = null; if(res.collection || res.kind === "retro") C = null; }
    }catch(e){ V.prev[v] = {error: e.message}; }
    render("imp-" + v);
  }
});

document.addEventListener("input", ev => {
  if(ev.target.dataset.in === "q"){ V.q = ev.target.value; V.focusQ = true; render(); V.focusQ = false; }
  if(ev.target.dataset.in === "gq"){
    V.gq = ev.target.value; V.menu = "g"; render();
    const q = document.querySelector("[data-in=gq]"); q?.focus(); q?.setSelectionRange(q.value.length, q.value.length);
  }
  if(ev.target.dataset.in === "dq"){
    V.d.q = ev.target.value; V.d.n = D0.n; render();
    const q = $("dq"); q.focus(); q.setSelectionRange(q.value.length, q.value.length);
  }
});

document.addEventListener("change", async ev => {
  const t = ev.target, dt = t.dataset;
  // Sortieren, Filter-Häkchen, Genre und Mehrspieler in Entdecken; ein offenes Menü bleibt offen
  if(dt.sort){ V[{wish: "sort", now: "nowSort", pc: "pcSort"}[dt.sort]] = t.value; render(); return; }
  if(dt.lf){ V.lf[dt.lf] = t.checked; V.menu = "lf"; render(); return; }
  if(dt.dg || dt.dmp || dt.dhow){
    const f = dt.dg ? "g" : dt.dhow ? "how" : "mp", x = dt.dg || dt.dmp || dt.dhow;
    V.d[f] = t.checked ? V.d[f].concat(x) : V.d[f].filter(y => y !== x);
    V.d.mix = ""; V.d.n = D0.n; V.menu = f; render(); return;
  }
  if(dt.sched){
    const f = t.form, body = {auto: f.auto.checked, hours: Number(f.hours.value)};
    if(await act("/api/settings", body, $("s-err"))) toast("Zeitplan gespeichert");
    return;
  }
  const ds = dt.dset;
  if(ds){
    const el = ev.target;
    if(ds === "sort"){ delete V.sorts.find; if(!el.value){ render(); return; } }
    V.d[ds] = el.type === "checkbox" ? (el.checked ? 1 : 0) : typeof D0[ds] === "number" ? Number(el.value) || 0 : el.value;
    if(ds === "sort" && el.value === "random") V.d.seed = newSeed();
    if(ds !== "sort") V.d.mix = "";
    V.d.n = D0.n;
    render();
    return;
  }
  const kind = ev.target.dataset.file;
  if(!kind || !ev.target.files[0]) return;
  if(kind === "retrodir"){
    // Nur die Namen: relativer Pfad je Datei, Archiv-Ordner (…_zip) gleich hier weggelassen
    // 0.8.8: dazu die Größe (hinter einem Tabulator) und deine Ordner-Listen „…_ordner.csv“, auch aus „…_zip/_Sortierung“
    const all = [...ev.target.files], path = f => f.webkitRelativePath || f.name;
    const lines = all.filter(f => !/(^|\/)[^/]*_zip\//i.test(path(f))).map(f => path(f) + (f.size ? "\t" + f.size : ""));
    V.retroLists = await Promise.all(all.filter(f => /(^|\/)[^/]*_ordner\.csv$/i.test(path(f)) && f.size < 5e6).slice(0, 60).map(async f => ({path: path(f), text: await f.text()})));
    ev.target.value = "";
    V.txt = Object.assign(V.txt || {}, {retro: lines.join("\n")});
    V.prev.retro = null; V.folds["imp-retro"] = false;
    render("imp-retro");
    document.querySelector("[data-act=preview][data-v=retro]")?.click();
    return;
  }
  const f = ev.target.files[0];
  if(f.size > 45e6){ alert("Datei zu groß"); return; }
  const text = await f.text();
  if(kind === "restore"){
    let obj;
    try{ obj = JSON.parse(text); }catch(e){ alert("Keine gültige Sicherung"); return; }
    ev.target.value = "";
    if(confirm(`Sicherung einlesen? Sie ersetzt alle ${S.counts.all} Titel.`) && await act("/api/restore", {data: obj.data || obj, collection: obj.collection, pcwish: obj.pcwish})){ C = null; toast("Sicherung eingelesen"); }
    return;
  }
  V.txt = Object.assign(V.txt || {}, {[kind]: text});
  V.prev[kind] = null;
  render("imp-" + kind);
});

document.addEventListener("submit", async ev => {
  const f = ev.target, kind = f.dataset.form;
  if(kind === "add"){
    ev.preventDefault();
    if(await act("/api/title/new", {name: f.name.value, link: f.link.value})) f.reset();
  }
  if(kind === "sched") ev.preventDefault();
  if(kind === "accounts"){
    ev.preventDefault();
    const body = {steam_id: f.steam_id.value.trim(), sharenite: f.sharenite.value.trim()};
    if(f.steam_key.value.trim()) body.steam_key = f.steam_key.value.trim();
    if(f.steam_clear?.checked) body.steam_key = "";
    body.steam_wish = f.steam_wish.checked;
    if(f.gg_wish.value.trim()) body.gg_wish = f.gg_wish.value.trim();
    if(f.gg_wish_clear?.checked) body.gg_wish = "";
    if(f.gg_key.value.trim()) body.gg_key = f.gg_key.value.trim();
    if(f.gg_clear?.checked) body.gg_key = "";
    for(const k of ["igdb_id", "igdb_secret"]) if(f[k].value.trim()) body[k] = f[k].value.trim();
    if(f.igdb_clear?.checked) body.igdb_id = body.igdb_secret = "";
    if(f.nexus_key.value.trim()) body.nexus_key = f.nexus_key.value.trim();
    if(f.nexus_clear?.checked) body.nexus_key = "";
    if(await act("/api/settings", body, $("a-err"))) toast("Gespeichert, gilt ab dem nächsten Abgleich");
  }
  if(kind === "edit"){
    ev.preventDefault();
    const cb = f.crossbuy.value;
    const ok = await act("/api/title", {key: f.dataset.k, name: f.name.value, meta_id: f.meta_id.value, steam_appid: f.steam_appid.value,
      crossbuy: cb === "yes" ? true : cb === "no" ? false : null, wish: f.wish.checked,
      owned_meta: f.owned_meta.checked, owned_pc: f.owned_pc.checked, note: f.note.value,
      contains: [...f.querySelectorAll("input[name=contains]")].map(x => x.value.trim()).filter(Boolean)}, $("f-err"));
    if(ok) $("edit").close();
  }
});

// Klappzustände merken: nur die Abweichung von der Vorgabe (offen, mit data-shut zu). Während
// einer Suche ist alles offen; das zählt nicht als Wahl.
function keepFold(d){
  const k = d.dataset?.kc;
  if(!k || V.q.trim()) return;
  if(d.open === !d.dataset.shut) delete V.folds[k]; else V.folds[k] = !d.open;
}
document.addEventListener("toggle", ev => {
  const d = ev.target.dataset;
  if(d?.kc){ keepFold(ev.target); saveView(); }
  else if(d?.menu){
    // ein Menü zur Zeit
    if(ev.target.open){ V.menu = d.menu; document.querySelectorAll("details.menu[open]").forEach(x => { if(x !== ev.target) x.open = false; }); }
    else if(V.menu === d.menu) V.menu = "";
  }
  else if(d?.more) ev.target.open ? V.more.add(d.more) : V.more.delete(d.more);    // nur bis zum Neuladen
}, true);
document.addEventListener("click", ev => {
  if(!ev.target.closest(".thm")) themeMenu(false);
  if(!ev.target.closest("details.menu")){ V.menu = ""; document.querySelectorAll("details.menu[open]").forEach(x => { x.open = false; }); }
});
document.addEventListener("keydown", ev => {
  // Spaltenköpfe sind keine Knöpfe: Enter und Leertaste sortieren wie ein Klick
  if((ev.key === "Enter" || ev.key === " ") && ev.target.matches?.("[data-act=tsort]")){ ev.preventDefault(); ev.target.click(); return; }
  if(ev.key !== "Escape") return;
  themeMenu(false);
  if(V.menu){ V.menu = ""; document.querySelectorAll("details.menu[open]").forEach(x => { x.open = false; }); }
  if(ev.target.id === "q" && V.q){ ev.preventDefault(); V.q = ""; render(); $("q")?.focus(); }
  if(ev.target.id === "dq" && V.d.q){ ev.preventDefault(); V.d.q = ""; render(); $("dq")?.focus(); }
});
addEventListener("resize", navFade);
$("nav").addEventListener("scroll", navFade);

renderTheme();
readFindHash();
load().then(() => {
  if(META_IN !== null && S) metaHandOver();
  // Sammlung im Hintergrund vorladen (0.8.14): der Wechsel in den Reiter wartet dann nicht auf den Server
  setTimeout(() => { if(!C) loadCollection(); }, 1500);
});
