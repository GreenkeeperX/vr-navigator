"use strict";
/* VR-Navigator, Oberfläche ohne Build. Reiter: Jetzt, Wunschliste, Bibliothek, Einstellungen.
   Farben, Marken und Klappen folgen docs/oberflaeche.md.
   Alle fremden Texte (Titel, Notizen, Links) laufen durch esc() bzw. safeUrl(). */

const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const safeUrl = u => /^https?:\/\//i.test(String(u || "")) ? String(u) : "";
const eur = v => v == null ? "–" : v.toLocaleString("de-DE", {minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2}) + " €";
const day = iso => iso ? new Date(iso).toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit", year: "numeric"}) : "";
const when = iso => iso ? new Date(iso).toLocaleString("de-DE", {day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit"}) : "";
// Ende eines Angebots als Tag: „bis 28.10.“
const until = d => d ? "bis " + new Date(d + "T12:00:00").toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit"}) : "";

let S = null;                                   // Zustand vom Server
const TABS = [["now", "Jetzt"], ["wish", "Wunschliste"], ["lib", "Bibliothek"], ["find", "Entdecken"], ["settings", "Einstellungen"]];
const V = {tab: "wish", q: "", sort: "name", prev: {}, folds: {}};
// Ansicht je Browser (vn.view): Reiter und Klappzustände. Bis 0.2.1 gab es die Reiter Abrufe
// und Import, beide stehen jetzt unter Einstellungen.
try{
  const v = JSON.parse(localStorage.getItem("vn.view") || "{}") || {};
  const t = v.tab || localStorage.getItem("vn.tab") || V.tab;
  V.tab = t === "sync" || t === "import" ? "settings" : TABS.some(x => x[0] === t) ? t : V.tab;
  V.folds = v.folds && typeof v.folds === "object" ? v.folds : {};
}catch(e){}
function saveView(){ try{ localStorage.setItem("vn.view", JSON.stringify({tab: V.tab, folds: V.folds})); }catch(e){} }

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
  const c = S.counts, sug = S.suggestions.length + (S.todo || []).length;
  const sy = S.sync || {};
  const set = sy.running ? "läuft" : Object.values(sy.sources || {}).some(x => !x.ok) ? "Fehler" : sug ? `${sug} offen` : "";
  const cnt = {now: c.now || "", wish: c.wish, lib: c.owned, find: S.imports.collection?.n || "", settings: set};
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
const SRC_NAME = {qsdb: "QuestStoreDB", steam: "Steam", gg: "gg.deals", steamacc: "Steam-Konto", ggwish: "gg.deals-Wunschliste", sharenite: "Sharenite", reviews: "Steam-Rezensionen", details: "Steam-Details", rating: "Steam-Wertungen", players: "Steam-Spieler", vrdb: "VRDB"};
function banners(){
  const sy = S.sync || {}, out = [];
  const logLink = `<button class="link" data-act="showlog">Protokoll öffnen</button>`;
  if(sy.running) return "";
  if(!sy.started) return `<div class="banner">Noch kein Abgleich. Der erste Lauf holt die Preise deiner Wunschtitel und dauert einige Minuten.
    <button class="link" data-act="sync">Jetzt abrufen</button></div>`;
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
  $("main").innerHTML = V.tab === "lib" ? banners() + libView() : V.tab === "now" ? banners() + nowView()
    : V.tab === "find" ? findView() : V.tab === "settings" ? settingsView() : banners() + wishView();
  findHash();
  showLog();
  moreOnScroll();
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
  return out.join(" ");
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
const num = n => n.toLocaleString("de-DE");
const RATE_GAP = 5;
const fact = (label, body, tip) => `<span class="fact"${tip ? ` title="${esc(tip)}"` : ""}><span class="fl">${label}</span> ${body}</span>`;
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
    if(s) parts.push(sp != null ? cell("steam", "Steam", `${sp} %`, s.n, "Anteil positiver Steam-Rezensionen")
      : `<span class="hint" title="Steam-Rezensionen; eine Wertung gibt es ab 50">Steam ${num(s.n)} Rez.</span>`);
    if(win) parts.push(`<span class="b go" title="Mindestens ${RATE_GAP} Punkte Abstand">${win === "meta" ? "Meta" : "Steam"} +${Math.abs(mp - sp)}</span>`);
    out.push(fact("Wertung", parts.join(" ")));
  }
  if(g.players && g.players.now != null) out.push(fact("Spieler", `${num(g.players.now)}${g.players.peak > g.players.now ? ` <span class="hint">(Spitze ${num(g.players.peak)})</span>` : ""}`,
    `Steam-Spieler gerade eben (${when(g.players.at)}); Spitze: höchster gemessener Wert seit ${day(g.players.since)}`));
  if(g.update) out.push(fact("Update", agoDays(g.update.date), `Steam, laut Meldung des Entwicklers: ${g.update.title}`));
  if(g.meta_ver) out.push(fact("Meta", `v${esc(g.meta_ver.v.split("_")[0])}${g.meta_ver.since ? ` seit ${agoDays(g.meta_ver.since).replace("vor ", "")}` : ""}`,
    `Version im Meta Store laut VRDB${g.meta_ver.since ? "; das Tool sah sie zuerst am " + day(g.meta_ver.since) : ", zuerst gesehen beim ersten Abruf"}`));
  return out.length ? `<div class="facts">${out.join("")}</div>` : "";
}

/* Filter für Jetzt, Wunschliste und Bibliothek (gemeinsam, je Reiter nur die passenden) */
V.lf = {cb: false, sale: false, best: false, good: false};
const LF = [["cb", "Crossbuy", r => r.crossbuy === true],
  ["sale", "Im Angebot", r => (r.live.meta?.discount || 0) + (r.live.steam?.discount || 0) > 0],
  ["best", "Am Bestpreis", r => ["meta", "steam"].some(s => r.best?.[s]?.level === "best")],
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
    <div class="lg"><span class="star">★</span> <span class="best-t">Bestpreis</span>: höchstens 2 % über dem niedrigsten Preis; „übliches Angebot“: so tief wie in mindestens zwei Angeboten</div>
    <div class="lg"><span class="b deal">−20 %</span> Rabatt jetzt</div>
    <div class="lg"><span class="shopmark">grüner Rahmen</span> der günstigere Laden, mit Betrag (ab 1 €; Steam-Seite zählt auch Händler bei gg.deals, ohne Keyshops)</div>
    <div class="lg"><span class="b go">Crossbuy</span> Meta-Kauf gilt auch am PC; <span class="b">ohne Crossbuy</span> nur auf der Quest</div>
    <div class="lg"><span class="rate win">Meta 88 %</span> besser bewerteter Laden (ab 5 Punkten Abstand)</div>
    <div class="lg">ohne Zeichen: vom Tool gemessen · <b>≈</b> abgeleitet oder aus fremder Quelle · <b>Tabelle</b> aus deiner Vergleichstabelle · <span class="ux">violett gestrichelt</span> Recherche · <span class="b warn">violett</span> prüfen</div></div>`;
}

/* ---------------------------------------------------------------- Wunschliste */
function wishView(){
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
  return (V.add ? add : "") + head +
    (!rows.length ? `<p class="hint">Kein Treffer.</p>` : !ow ? `<div class="list">${open.map(r => wishRow(r)).join("")}</div>`
      : grp("w-open", "Noch nicht im Besitz", open.length, `<div class="list">${open.map(r => wishRow(r)).join("")}</div>`) +
        grp("w-owned", `Schon im Besitz <span class="hint" title="Titel auf der Wunschliste, die du schon bei Meta oder am PC besitzt">(bei Meta oder am PC)</span>`, owned.length, `<div class="list">${owned.map(r => wishRow(r)).join("")}</div>`, true));
}
// Sortierschlüssel: wie nah der günstigere Shop an seinem Bestpreis liegt (1 = am Bestpreis)
function nearBest(r){
  const q = ["meta", "steam"].map(s => r.best?.[s] && r.live[s] ? r.live[s].price / r.best[s].best : null).filter(x => x != null);
  return q.length ? Math.min(...q) : 1e9;
}

/* Preise: zwei feste Felder, Meta links, Steam rechts (fehlt ein Laden, bleibt sein Feld grau).
   Je Feld Preis, Rabatt und darunter der Abstand zum Bestpreis: rot „+7 € über Bestpreis“ oder
   gold „★ Bestpreis“; „≈“, wenn der Bestpreis aus einer fremden Quelle stammt, solange der eigene
   Verlauf zu kurz ist. Der günstigere Laden bekommt einen grünen Rahmen und den Betrag (ab 1 €). */
function bestLine(v, b){
  if(!b || b.thin || b.best == null) return `<div class="bl hint" title="Der eigene Verlauf hat noch keine Preisänderung">Bestpreis noch offen</div>`;
  const ap = b.src ? " ≈" : "";
  const from = b.src ? `${b.src}${b.best_at ? ", " + day(b.best_at) : ""}` : `${day(b.best_at)}${b.full ? ", 24 Monate" : ", Verlauf seit " + day(b.since)}`;
  const tip = `Jetzt ${eur(v.price)}, Bestpreis ${eur(b.best)} (${from}), Normalpreis ${eur(v.base || v.price)}${b.usual != null ? `, übliches Angebot ${eur(b.usual)}` : ""}`;
  if(b.level === "best") return `<div class="bl at" title="${esc(tip)}"><span class="star">★</span> Bestpreis${ap}</div>`;
  const rel = b.best > 0 ? Math.round((v.price - b.best) / b.best * 100) : 0;
  return `<div class="bl" title="${esc(tip)}"><span class="over">+${eur(v.price - b.best)}</span> über Bestpreis</div>
    <div class="bl" title="${esc(tip)}">${eur(b.best)}${ap} <span class="hint">(+${rel} %)</span>${b.level === "usual" ? " · übliches Angebot" : ""}</div>`;
}
function shopCell(shop, v, b, win, extra){
  if(!v) return `<div class="shop none"><div class="sl">${shop}</div><div class="bl">kein Preis</div>${extra || ""}</div>`;
  const sale = v.discount ? ` <span class="b deal">−${v.discount} %${v.kind === "coupon" ? " Gutschein" : ""}</span>${v.until ? ` <span class="hint">${until(v.until)}</span>` : ""}` : "";
  const old = v.stale ? ` <span class="b warn" title="Älter als zwei Tage: Abruf prüfen">Stand ${ago(v.at)}</span>` : "";
  return `<div class="shop${win ? " win" : ""}"><div class="sl">${shop}${sale}${old}</div>
    <div><span class="price big">${eur(v.price)}</span>${v.discount && v.base ? ` <s>${eur(v.base)}</s>` : ""}</div>
    ${bestLine(v, b)}${extra || ""}${win ? `<div class="cheap">${win}</div>` : ""}</div>`;
}
function shopsHtml(r){
  const L = r.live, B = r.best || {}, g = L.gg, pc = r.pc_best;
  if(!L.meta && !L.steam && !(g && g.retail != null)) return "";
  // Betrag gegenüber dem günstigsten PC-Angebot (Steam oder Händler bei gg.deals); unter 1 € kein Rahmen
  const gap = r.gap_now, big = gap != null && Math.abs(gap) >= 1;
  const metaWin = big && gap < 0 ? `${eur(-gap)} günstiger` : "";
  const pcWin = big && gap > 0 ? `${eur(gap)} günstiger${pc?.src !== "Steam" ? " bei Händlern" : ""}` : "";
  // Händler bei gg.deals unter Steam: als Zeile im Steam-Feld
  const deal = g && g.retail != null && (!L.steam || g.retail < L.steam.price - 0.005)
    ? `<div class="bl" title="Günstigster Händler laut gg.deals (Keyshops zählen nicht)">Händler ${eur(g.retail)} <span class="hint">(gg.deals)</span></div>` : "";
  return `<div class="shops">${shopCell("Meta", L.meta, B.meta, metaWin)}${shopCell("Steam", L.steam, B.steam, pcWin, deal)}</div>`;
}
V.more = new Set();
// Was selten entscheidet, steht in der Klappe „Mehr“: Bestpreise im Einzelnen, gg.deals, Tabelle, Links, Bearbeiten
function moreHtml(r, extra){
  const g = r.live.gg, s = r.sheet, B = r.best || {}, out = [];
  for(const [k, shop] of [["meta", "Meta"], ["steam", "Steam"]]){
    const b = B[k];
    if(b && !b.thin && b.best != null) out.push(`<div class="small">${shop}: Bestpreis ${eur(b.best)}${b.src ? ` ≈ (${esc(b.src)}${b.best_at ? ", " + day(b.best_at) : ""})` : ` am ${day(b.best_at)}${b.full ? " (24 Monate)" : ` (Verlauf seit ${day(b.since)})`}`}${b.usual != null ? `, übliches Angebot ${eur(b.usual)}` : ""}</div>`);
  }
  if(g && (g.retail != null || g.keyshops != null)) out.push(`<div class="small">gg.deals: ${[
    g.retail != null && "Händler " + eur(g.retail), g.keyshops != null && "Keyshop " + eur(g.keyshops),
    g.retail_low != null && "Allzeit-Tief Händler " + eur(g.retail_low)].filter(Boolean).join(", ")}${g.stale ? ` <span class="b warn">Stand ${ago(g.at)}</span>` : ""}
    <span class="hint">(Keyshops zählen nicht mit)</span></div>`);
  if(s && Object.keys(r.live).length) out.push(`<div class="small">Tabelle, ${day(s.at)}: Meta ${eur(s.meta)}, Tief ${eur(s.meta_low)}, gg.deals ${eur(s.gg)}</div>`);
  out.push(`<div class="row2">${linksHtml(r)}</div>`);
  out.push(`<div class="row2"><button class="link" data-act="edit" data-k="${esc(r.key)}">bearbeiten</button>${extra || ""}</div>`);
  return `<details class="more" data-more="${esc(r.key)}" ${V.more.has(r.key) ? "open" : ""}><summary>Mehr</summary>${out.join("")}</details>`;
}
// Ohne Abruf: die Werte aus deiner Tabelle, gekennzeichnet
function sheetHtml(r){
  const s = r.sheet;
  if(!s) return `<div class="shops"><div class="shop none"><div class="sl">Meta</div><div class="bl">kein Preis</div></div><div class="shop none"><div class="sl">Steam</div><div class="bl">kein Preis</div></div></div>`;
  return `<div class="facts" title="Aus deiner Tabelle übernommen, bis ein Abruf eigene Preise liefert">${fact("Tabelle", day(s.at))}
    ${fact("Meta", `<span class="price">${eur(s.meta)}</span>, Tief ${eur(s.meta_low)}`)}${fact("gg.deals", `<span class="price">${eur(s.gg)}</span>`)}
    ${r.gap != null ? fact("Differenz", `<span class="${r.gap >= 1 ? "over" : r.gap <= -1 ? "ok" : ""}">${r.gap > 0 ? "+" : ""}${eur(r.gap)}</span>`) : ""}</div>`;
}
function wishRow(r){
  return `<div class="item wi"><div class="hd"><span class="nm">${esc(r.name)}</span>${badges(r)}</div>
    ${shopsHtml(r) || sheetHtml(r)}<div class="side">${factsHtml(r)}${opinionHtml(r)}
    ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}</div>
    ${moreHtml(r, `<button class="link" data-act="unwish" data-k="${esc(r.key)}" title="Von der Wunschliste nehmen; der Titel bleibt im Tool">nicht mehr wünschen</button>`)}</div>`;
}

/* ---------------------------------------------------------------- Entdecken
   Die ganze PC-Sammlung aus dem Playnite-Export (eigene Datei, beim ersten Öffnen geladen).
   Filter, Sortierung und Zufall laufen hier im Browser. Der Zustand steht in der Adresse
   (#entdecken?…), so lässt sich eine Mischung als Lesezeichen merken und wieder aufrufen. */
let C = null, cLoading = false;
const D0 = {mp: [], min: 0, g: [], gop: "", st: "", sc: 0, old: 0, q: "", sort: "score", seed: 0, mix: "", n: 100};
V.d = Object.assign({}, D0);
const D_SORTS = [["score", "Wertung"], ["gem", "Geheimtipp"], ["known", "Bekanntheit"], ["added", "Neu in der Sammlung"], ["year", "Erscheinungsjahr"], ["name", "Name"], ["random", "Zufall"]];
// Mischungen: ein Klick setzt Filter und Sortierung (alles andere zurück); pick: zeigt drei Vorschläge
const MIXES = [
  ["surprise", "Überrasch mich", "Drei Spiele per Zufall aus dem, was die Filter gerade zeigen; gut bewertete und Geheimtipps kommen öfter", null],
  ["duo", "Koop zu zweit", "Koop-Spiele für zwei, die besten zuerst", {mp: ["coop"], min: 2}],
  ["couch", "Couch-Abend", "Lokal an einem Rechner: Couch-Koop oder Splitscreen", {mp: ["couch"]}],
  ["big", "Große Runde", "Mindestens vier Spieler", {min: 4}],
  ["gems", "Geheimtipps", "Gut bewertet und wenig bekannt (wenige Steam-Rezensionen); nur Spiele, deren Rezensionen schon abgerufen sind", {sc: 80, sort: "gem"}],
  ["old", "Gut, lange her", "Wertung ab 80, seit über zwei Jahren in der Sammlung, in zufälliger Folge", {sc: 80, old: 1, sort: "random"}],
  ["wild", "Wilde Mischung", "Würfelt eine Mehrspieler-Art und ein Genre zusammen und zieht drei Vorschläge", null],
];
const mulberry = a => () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
const newSeed = () => 1 + Math.floor(Math.random() * 2147483646);

function findHash(){
  if(V.tab !== "find"){ if(location.hash.startsWith("#entdecken")) history.replaceState(null, "", location.pathname + location.search); return; }
  const d = V.d, p = new URLSearchParams();
  for(const [k, v] of Object.entries(d)) if(k !== "n" && String(v) !== String(D0[k])) p.set(k, Array.isArray(v) ? v.join(",") : v);
  const h = "#entdecken" + (String(p) ? "?" + p : "");
  if(location.hash !== h) history.replaceState(null, "", location.pathname + location.search + h);
}
function readFindHash(){
  if(!location.hash.startsWith("#entdecken")) return;
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
function dFilter(d){
  const q = d.q.trim().toLowerCase(), cut = new Date(Date.now() - 730 * 864e5).toISOString().slice(0, 10);
  return C.games.filter(g => d.mp.every(m => g.mp.includes(m))
    // Spielerzahl unbekannt: ein Mehrspieler-Spiel zählt als zwei
    && (!d.min || (g.players ? g.players >= d.min : d.min <= 2 && g.mp.includes("multi")))
    // mehrere Genres: eines davon genügt, mit gop „and“ alle
    && (!d.g.length || (d.gop === "and" ? d.g.every(x => g.genres.includes(x)) : d.g.some(x => g.genres.includes(x)))) && (!d.st || g.store === d.st) && (!d.sc || (g.score ?? -1) >= d.sc)
    && (!d.old || (g.added && g.added < cut))
    && (!q || g.name.toLowerCase().includes(q) || g.dev.toLowerCase().includes(q) || g.genres.some(x => x.toLowerCase().includes(q))));
}
function dSort(rows, d){
  const by = {score: g => -(g.score ?? -1), gem: g => -g.gem, known: g => -(g.reviews ?? -1), added: g => g.added ? -Date.parse(g.added) : 0,
              year: g => -(Number(g.year) || 0)}[d.sort];
  if(d.sort === "random"){
    const r = mulberry(d.seed || 1), a = rows.slice();
    for(let i = a.length - 1; i > 0; i--){ const j = Math.floor(r() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; }
    return a;
  }
  return by ? rows.slice().sort((a, b) => by(a) - by(b) || a.name.localeCompare(b.name, "de")) : rows;
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
      const d = Object.assign({}, D0, {mp: [kinds[Math.floor(r() * kinds.length)]].filter(Boolean),
        g: [C.genres[Math.floor(r() * C.genres.length)]].filter(Boolean), sc: r() < .5 ? 70 : 0});
      if(dFilter(d).length >= 3 || i === 29){ V.d = d; break; }
    }
  } else if(m[3]) V.d = Object.assign({}, D0, m[3]);
  V.d.mix = k;
  V.d.seed = newSeed();
  V.d.n = D0.n;
}
const dLabel = d => [d.mp.map(m => C.mp_label[m] || m).join(" + "), d.min && `ab ${d.min} Spieler`, d.g.join(d.gop === "and" ? " und " : " oder "), d.st,
  d.sc && `Wertung ab ${d.sc}`, d.old && "über zwei Jahre in der Sammlung", d.q && `„${d.q}“`].filter(Boolean).join(", ");

function gameRow(g){
  // Mit Steam-Details abgeglichen (src „steam“): was Playnite und Steam beide sagen, steht ohne Zeichen,
  // was nur eine Quelle sagt, mit ≈. Ohne Steam-Details gilt alles nur laut Playnite.
  const chk = g.src === "steam", ok = (list, x) => !chk || (list || []).includes(x);
  const mp = g.mp.filter(m => m !== "multi" || g.mp.length === 1).map(m => `<span class="b"${ok(g.mpc, m) ? "" : ` title="Nur eine Quelle (Playnite oder Steam)"`}>${esc(C.mp_label[m] || m)}${ok(g.mpc, m) ? "" : " ≈"}</span>`).join(" ");
  const name = safeUrl(g.url) ? `<a href="${esc(g.url)}" target="_blank" rel="noopener noreferrer">${esc(g.name)}</a>` : esc(g.name);
  const gen = g.genres.map(x => esc(x) + (ok(g.gc, x) ? "" : " ≈")).join(", ");
  const yr = chk && !g.year_ok ? `${esc(g.year)} ≈` : esc(g.year);
  const yrTip = chk ? (g.year_ok ? "Playnite und Steam einig" : `Playnite ${g.year === g.syear ? "ohne Jahr" : "und Steam verschieden"}${g.syear ? `, Steam ${g.syear}` : ""}`) : "Laut Playnite";
  return `<div class="item"><span class="nm">${name}</span>${mp}
    ${g.vr ? `<span class="b" title="Laut Steam mit VR-Unterstützung">VR</span>` : ""}
    ${g.players ? `<span class="b" title="Höchste Spielerzahl laut Playnite">bis ${g.players}</span>` : ""}
    ${g.gem >= 0.2 ? `<span class="b" title="Geheimtipp-Wert ${String(g.gem).replace(".", ",")} von 1: gute Wertung, wenige Rezensionen">Geheimtipp</span>` : ""}
    <div class="row2">${g.score != null ? `<span title="Anteil positiver Steam-Rezensionen">Steam ${g.score} % <span class="hint">(${g.reviews.toLocaleString("de-DE")})</span></span>`
        : g.reviews != null ? `<span title="Steam-Rezensionen; eine Wertung gibt es ab 50">${g.reviews.toLocaleString("de-DE")} Rezensionen</span>` : ""}
      ${g.genres.length ? `<span title="${chk ? "Ohne ≈: Playnite und Steam einig. ≈: nur eine Quelle; Steam kennt z. B. Puzzle oder Horror nicht als Genre" : "Laut Playnite"}">${gen}</span>` : ""}
      ${g.year ? `<span title="${esc(yrTip)}">${yr}</span>` : ""}
      ${g.store ? `<span title="${g.guess ? "Laden nur vermutet (Kennung ohne Angabe des Ladens)" : chk ? "Laden von Steam bestätigt" : "Laden laut Playnite"}">${esc(g.store)}${g.guess ? " ≈" : ""}</span>` : ""}
      ${chk ? "" : `<span class="hint" title="Noch nicht mit Steam abgeglichen (nur Steam-Spiele, je Lauf ein Teil)">nur Playnite</span>`}</div></div>`;
}
// Entdecken lädt beim Scrollen weiter: kommt „weitere zeigen“ in Sicht, klickt es sich selbst
let moreObs = null;
function moreOnScroll(){
  moreObs?.disconnect();
  const m = $("dmore");
  if(!m || !("IntersectionObserver" in window)) return;
  moreObs = new IntersectionObserver(es => { if(es.some(e => e.isIntersecting)){ moreObs.disconnect(); m.click(); } }, {rootMargin: "400px"});
  moreObs.observe(m);
}
function findView(){
  if(!C){ loadCollection(); return `<p class="hint">Lädt die Sammlung …</p>`; }
  if(C.error) return `<p class="err">Sammlung nicht lesbar: ${esc(C.error)}</p>`;
  if(!C.games.length) return `<div class="card"><h2>Entdecken</h2><p class="hint">Hier filterst du deine ganze PC-Sammlung nach Mehrspieler, Spielerzahl, Genre und Wertung und lässt dir Spiele vorschlagen.
    Dafür braucht das Tool einmal den Playnite-Export mit allen Spielen: unter Einstellungen bei „Datei oder Text einlesen“.</p>
    <button class="link" data-act="tab" data-v="settings">Zu den Einstellungen</button></div>`;
  const d = V.d, rows = dSort(dFilter(d), d), pick = d.mix === "surprise" || d.mix === "wild" ? dPick(rows, d.seed) : [];
  const opt = (k, list, cur) => list.map(([v, l]) => `<option value="${esc(v)}"${String(v) === String(cur) ? " selected" : ""}>${esc(l)}</option>`).join("");
  const stores = [...new Set(C.games.map(g => g.store).filter(Boolean))].sort();
  // ein Klick auf die gewählte Mischung nimmt sie wieder zurück
  const mixes = `<div class="chips mix">${MIXES.map(([k, l, tip]) => `<button data-act="${d.mix === k ? "dmixoff" : "dmix"}" data-v="${k}" title="${esc(d.mix === k ? "Zurücknehmen" : tip)}" class="${d.mix === k ? "on" : ""}">${esc(l)}</button>`).join("")}</div>`;
  // Filter als Menüs mit Häkchen. Die Zahl hinter einem Genre: Spiele mit diesem Genre unter den übrigen
  // Filtern; bei „alle“ zusätzlich mit allen schon gewählten Genres
  const base = dFilter(Object.assign({}, d, {g: d.gop === "and" ? d.g : []})), gn = {};
  for(const g of base) for(const x of g.genres) gn[x] = (gn[x] || 0) + 1;
  const gq = (V.gq || "").trim().toLowerCase();
  const genres = `<details class="menu" ${menuAttr("g")}><summary>Genre${d.g.length ? ` <span class="cnt">${d.g.length}</span>` : ""}</summary><div class="pop wide">
    <div class="seg" role="group" aria-label="Mehrere Genres verknüpfen"><button data-act="dgop" data-v="" class="${d.gop !== "and" ? "on" : ""}" title="Spiele mit mindestens einem der Genres">eines davon</button><button data-act="dgop" data-v="and" class="${d.gop === "and" ? "on" : ""}" title="Nur Spiele mit allen gewählten Genres">alle</button></div>
    <input type="search" data-in="gq" placeholder="Genre suchen" aria-label="Genre suchen" value="${esc(V.gq || "")}">
    <div class="opts">${C.genres.filter(g => !gq || g.toLowerCase().includes(gq) || d.g.includes(g)).map(g => `<label><input type="checkbox" data-dg="${esc(g)}"${d.g.includes(g) ? " checked" : ""}> ${esc(g)} <span class="n">${gn[g] || 0}</span></label>`).join("")}</div>
    ${d.g.length ? `<button class="link" data-act="dgclear">keins</button>` : ""}</div></details>`;
  const kinds = `<details class="menu" ${menuAttr("mp")}><summary>Mehrspieler${d.mp.length ? ` <span class="cnt">${d.mp.length}</span>` : ""}</summary><div class="pop">
    <p class="hint">Mehrere gewählt: alle müssen passen.</p>
    ${Object.entries(C.mp_label).map(([k, l]) => `<label><input type="checkbox" data-dmp="${esc(k)}"${d.mp.includes(k) ? " checked" : ""}> ${esc(l)}</label>`).join("")}</div></details>`;
  const label = dLabel(d);
  const filters = `<div class="dfilter">${kinds}${genres}
      <label>Spieler <select data-dset="min">${opt("min", [[0, "egal"], [2, "ab 2"], [3, "ab 3"], [4, "ab 4"], [8, "ab 8"]], d.min)}</select></label>
      <label>Laden <select data-dset="st">${opt("st", [["", "alle"]].concat(stores.map(x => [x, x])), d.st)}</select></label>
      <label>Wertung <select data-dset="sc">${opt("sc", [[0, "egal"], [60, "ab 60 %"], [70, "ab 70 %"], [80, "ab 80 %"], [90, "ab 90 %"]], d.sc)}</select></label>
      <label><input type="checkbox" data-dset="old"${d.old ? " checked" : ""}> über zwei Jahre in der Sammlung</label></div>
    ${label ? `<div class="chips act">${d.mp.map(m => `<button data-act="dmpoff" data-v="${esc(m)}" title="Filter entfernen">${esc(C.mp_label[m] || m)} ×</button>`).join("")}${d.g.map(g => `<button data-act="dgoff" data-v="${esc(g)}" title="Filter entfernen">${esc(g)} ×</button>`).join("")}<button class="link" data-act="dreset">alle Filter zurücksetzen</button></div>` : ""}`;
  const bar = `<div class="bar"><span class="sbox"><input type="search" id="dq" placeholder="Name, Entwickler oder Genre suchen" aria-label="Name, Entwickler oder Genre suchen" value="${esc(d.q)}" data-in="dq">${d.q ? `<button class="sx" data-act="dqclear" title="Suche leeren" aria-label="Suche leeren">×</button>` : ""}</span>
    <label class="kind">Sortieren <select data-dset="sort">${opt("sort", D_SORTS, d.sort)}</select></label>
    ${d.sort === "random" ? `<button data-act="dshuffle">Neu mischen</button>` : ""}</div>`;
  const pickCard = d.mix === "surprise" || d.mix === "wild" ? `<div class="card"><h2>${d.mix === "wild" ? "Wilde Mischung" : "Vorschlag"}${label ? ` <span class="n">${esc(label)}</span>` : ""}</h2>
    ${pick.length ? `<div class="list">${pick.map(gameRow).join("")}</div>` : `<p class="hint">Nichts passt zu den Filtern.</p>`}
    <div class="actions"><button data-act="dpickoff">Schließen</button><button class="primary" data-act="dmix" data-v="${d.mix}">Noch mal</button></div></div>` : "";
  const at = S.imports.collection?.at;
  return mixes + filters + bar + pickCard +
    `<p class="hint">${rows.length} von ${C.games.length} Spielen${at ? `, Playnite-Export vom ${day(at)}` : ""}. Genres und Mehrspieler aus Playnite, mit Steam abgeglichen: ${C.games.filter(g => g.src === "steam").length} bisher (≈ = nur eine Quelle). Wertung aus Steam-Rezensionen ab 50 (${C.games.filter(g => g.reviews != null).length} abgerufen).</p>
    <div class="list">${rows.slice(0, d.n).map(gameRow).join("") || `<p class="hint">Kein Treffer.</p>`}</div>
    ${rows.length > d.n ? `<div class="actions"><button id="dmore" data-act="dmore">weitere ${Math.min(D0.n, rows.length - d.n)} zeigen</button></div>` : ""}`;
}

/* ---------------------------------------------------------------- Jetzt */
/* Wunschtitel im Angebot, standardmäßig die nah am Bestpreis zuerst */
function nowView(){
  const last = S.sync?.done;
  if(!last && !S.now.length) return `<p class="hint">Noch kein Abruf gelaufen. Oben über „Aktualisieren“ startest du den ersten; danach läuft er nach Zeitplan.</p>`;
  const sort = V.nowSort || "best";
  let rows = S.now.filter(r => match(r) && lfOk(r, ["cb", "best", "good"]));
  const k = {best: nearBest, rating: byRating}[sort];
  if(k) rows = rows.slice().sort((a, b) => k(a) - k(b));
  return listBar({sorts: [["best", "Nah am Bestpreis"], ["sale", "Rabatt"], ["rating", "Wertung"]], sort, sortKey: "now", filters: ["cb", "best", "good"]}) +
    `<p class="hint">Wunschtitel, die gerade bei Meta oder Steam reduziert sind. Letzter Abruf: ${when(last) || "–"}.</p>
    <div class="list">${rows.map(r => wishRow(r)).join("") || `<p class="hint">${S.now.length ? "Kein Treffer." : "Gerade ist kein Wunschtitel reduziert."}</p>`}</div>`;
}

/* ---------------------------------------------------------------- Abrufe */
const SOURCES = [["steamacc", "Steam-Konto (Besitz, Wunschliste)"], ["ggwish", "gg.deals-Wunschliste"], ["sharenite", "Sharenite (Playnite)"],
  ["qsdb", "QuestStoreDB (Meta-Preise)"], ["steam", "Steam-Store"], ["gg", "gg.deals"], ["reviews", "Steam-Rezensionen (Entdecken)"], ["details", "Steam-Details (Entdecken)"], ["rating", "Steam-Wertungen (Wunschliste, Bibliothek)"],
  ["players", "Steam-Spieler und Updates"], ["vrdb", "VRDB (Crossbuy, Version, Meta-Wertung)"]];
const ACCOUNT_SET = {steamacc: se => se.steam_id, ggwish: se => se.gg_wish_set, sharenite: se => se.sharenite};
function srcState(k, x){
  if(!x) return `<span class="hint">${k === "gg" && !S.settings?.gg_key_set ? "ohne Schlüssel aus" : "noch nicht gelaufen"}</span>`;
  const rest = x.until && new Date(x.until) > new Date();
  if(x.manual) return `<span class="b warn" title="gg.deals zeigt dem Server eine Prüfseite; dein Browser kommt durch">per Lesezeichen</span> <span class="hint">${S.imports.ggwish ? "zuletzt " + when(S.imports.ggwish.at) : "noch nie gelesen"}</span>`;
  const tag = x.ok ? `<span class="b go">ok</span>` : rest ? `<span class="b warn" title="${esc(x.msg || "")}">ruht bis ${esc(whenDay(new Date(x.until)) + clock(new Date(x.until)))}</span>`
    : `<span class="b stop">${esc(x.msg || "Fehler")}</span>`;
  return `${tag} <span class="hint">${when(x.at)}, ${x.requests ?? 0} Abrufe${x.errors ? `, ${x.errors} Fehler` : ""}</span>`;
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
  const rows = shown.map(([k, l]) => `<div class="item"><span class="nm">${l}</span>${srcState(k, src[k])}</div>`).join("");
  const bad = shown.filter(([k]) => src[k] && !src[k].ok).length, okN = shown.filter(([k]) => src[k]?.ok).length;
  const srcInfo = [okN && `${okN} ok`, bad && `<span class="err">${bad} mit Problem</span>`].filter(Boolean).join(", ") || "noch nicht gelaufen";
  const todo = S.todo || [], open = sug + todo.length;
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
  const sugCard = open ? box("todo", "Zu erledigen", `${open} offen`, `
    <p class="hint">Was das Tool nicht selbst klären konnte. Alles andere ordnet es bei jedem Abgleich von allein zu.</p>
    ${sug ? sub("sug", "Derselbe Titel?", `${S.suggestions.length} ${S.suggestions.length === 1 ? "Paar" : "Paare"}`, sugList) : ""}
    ${steamTodo.length ? sub("steamtodo", "Steam-ID prüfen", steamTodo.length, steamList) : ""}
    ${metaTodo.length ? sub("metatodo", "Ohne Meta-ID", metaTodo.length, metaList) : ""}`) : "";
  const ll = lastLine(sy);
  const logInfo = sy.running ? "läuft" : !sy.started ? "noch keins" : `${when(sy.started)}${sy.ok === false ? `, <span class="err">mit Fehlern</span>` : ""}${ll.end ? " · " + esc(ll.end) : ""}`;
  const abgleich = box("abgleich", "Abgleich", sy.running ? "läuft" : `Stand ${ago(sy.started)}${next ? ` · nächster ca. ${next < new Date() ? "in Kürze" : whenDay(next) + clock(next)}` : se.auto === false ? " · Zeitplan aus" : ""}`, `
    <form data-form="sched" class="bar sched"><label><input type="checkbox" name="auto" data-sched="1"${se.auto ? " checked" : ""}> automatisch alle</label>
      <input type="number" name="hours" min="2" max="48" value="${esc(hours)}" aria-label="Abstand in Stunden" data-sched="1"> Stunden <span class="err" id="s-err"></span></form>
    <p class="hint">Liest deine Konten, ordnet alle Titel zu und holt Preise und Messwerte. Ein Lauf dauert einige Minuten, weil zwischen zwei Abrufen einer Quelle Pausen liegen; nach einer Sperre ruht eine Quelle 24 Stunden.</p>
    ${sub("quellen", "Quellen", srcInfo, `<div class="list">${rows}</div>`, !bad)}
    <div class="bar" style="margin-top:10px"><button class="primary" data-act="sync" ${sy.running ? "disabled" : ""}>${sy.running ? "Läuft …" : "Jetzt abrufen"}</button>
      <button data-act="diag" ${V.diagRunning ? "disabled" : ""} title="Fragt jede Quelle einmal an und zeigt, was zurückkommt; dauert bis zu einer Minute und speichert nichts">${V.diagRunning ? "Test läuft …" : "Verbindung testen"}</button></div>
    ${V.diag ? sub("diagbox", "Verbindungstest", `${esc(V.diagAt || "")} · <button class="link" data-act="copy" data-v="diag">Ergebnis kopieren</button>`, `<pre class="log" id="diag">${esc(V.diag.join("\n"))}</pre>`) : ""}
    ${sub("logbox", "Protokoll", logInfo + (sy.started ? ` · <button class="link" data-act="copy" data-v="log">kopieren</button>` : ""), `<pre class="log" id="log"></pre>`, sy.ok !== false && !sy.running, "logfold")}
`);
  const importe = box("importe", "Einlesen", "", `<p class="hint">Bringt Käufe und Wünsche ins Tool: Konten automatisch, Meta per Lesezeichen, alles andere als Datei. Gelöscht wird nichts.</p>
    ${accountsCard()}${metaCard()}${fileCard()}`);
  const sicherung = box("sicherung", "Sicherung", "", `<p class="hint">Alle Titel, Notizen und Zuordnungen als eine Datei. Einspielen ersetzt alles.</p>
     <div class="bar"><a href="/api/export" download>Sicherung herunterladen</a>
     <label>Sicherung einspielen <input type="file" accept=".json,application/json" data-file="restore"></label></div>`);
  return banners() + `<div class="jump" role="navigation" aria-label="Abschnitte">${jumps.map(([id, l]) => `<a href="#${id}" data-act="jump" data-v="${id}">${l}</a>`).join("")}${foldAll}</div>` +
    sugCard + importe + abgleich + sicherung;
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

/* ---------------------------------------------------------------- Bibliothek */
/* Meinungen aus der Recherche (Reddit, Web): eine Zeile mit Fassung und Mehrspieler, der Rest
   aufklappbar; alles mit „Recherche“ und Stand gekennzeichnet */
const FASSUNG = {quest: "Quest-Fassung besser", pc: "PC-Fassung besser", gleich: "Fassungen gleichwertig"};
const MP = {lebendig: "Mehrspieler lebendig", ruhig: "Mehrspieler ruhig", tot: "Mehrspieler tot", keiner: "kein Mehrspieler"};
function opinionHtml(r){
  const o = r.opinion;
  if(!o) return "";
  const head = [o.fassung && FASSUNG[o.fassung], o.mehrspieler && MP[o.mehrspieler]].filter(Boolean).join(" · ");
  const rows = [["Fazit", o.fazit], ["Fassung", o.fassung_grund], ["Mehrspieler", o.mehrspieler_stand], ["Pflege", o.pflege],
    ["Crossbuy", o.crossbuy_grund], ["Komfort", o.komfort], ["Warnungen", o.warnungen]].filter(x => x[1]);
  const src = (o.quellen || []).filter(q => safeUrl(q.url)).map(q =>
    `<a href="${esc(q.url)}" target="_blank" rel="noopener noreferrer">${esc(q.titel || q.url.replace(/^https?:\/\/([^\/?#]+).*$/i, "$1"))}</a>${q.datum ? ` <span class="hint">${esc(q.datum)}</span>` : ""}`).join(" · ");
  // Recherche ist nicht gemessen: violett gestrichelt und mit „≈“ wie andere unsichere Werte
  return `<details class="op unsure" ${foldAttr("op-" + r.key, true)}><summary title="Aus Foren und Tests zusammengetragen, nicht vom Tool geprüft"><span class="ux">≈ Recherche${o.stand ? ", " + esc(o.stand) : ""}:</span> ${esc(head || "Meinungen")}</summary>
    ${rows.map(([l, v]) => `<div class="small"><b>${l}:</b> ${esc(v)}</div>`).join("")}${src ? `<div class="small"><b>Quellen:</b> ${src}</div>` : ""}</details>`;
}

function libView(){
  // Gruppen nach Laden: auf beiden Seiten, nur Meta, nur PC; jede klappbar
  const ws = [["beide", "Bei Meta und am PC"], ["meta", "Nur bei Meta"], ["pc", "Nur am PC"]];
  const sorts = [["name", "Name"], ["rating", "Wertung"], ["added", "Neu"]], ls = V.lsort || "name";
  let rows = S.library.filter(r => match(r) && lfOk(r, ["cb", "good"]));
  const k = {rating: byRating, added: byAdded}[ls];
  if(k) rows = rows.slice().sort((a, b) => k(a) - k(b));
  if(!S.library.length) return `<p class="hint">Noch nichts im Besitz. Importiere unter Einstellungen deine Meta-Bestellungen und den Playnite-Export.</p>`;
  const row = r => `<div class="item"><div class="hd"><span class="nm">${esc(r.name)}</span>${badges(r)}
      ${r.wish ? `<span class="b" title="Steht auch auf der Wunschliste">Wunsch</span>` : ""}</div>
      ${factsHtml(r)}${opinionHtml(r)}
      ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}${moreHtml(r)}</div>`;
  const groups = ws.map(([w, l]) => [w, l, rows.filter(r => r.where === w)]).filter(g => g[2].length);
  const head = listBar({sorts, sort: ls, sortKey: "lib", filters: ["cb", "good"], extra: groups.length > 1 ? foldAll : ""});
  return head + (groups.map(([w, l, rs]) =>
    grp("l-" + w, l, rs.length, `<div class="list">${rs.map(row).join("")}</div>`)).join("") || `<p class="hint">Kein Treffer.</p>`);
}

/* ---------------------------------------------------------------- Import */
/* Lesezeichen „Seite lesen“ (wie „Käufe lesen“ im eShopKompass): läuft in deinem Browser, wo du
   angemeldet bist und Prüfseiten wie die von Cloudflare schon bestanden hast.
   - Meta: Bestellseite, Transaktionen von Meta Pay oder Wunschliste; scrollt, bis alles geladen ist.
   - gg.deals: deine Wunschliste; weitere Seiten holt es mit kurzer Pause nach.
   Dann öffnet es dieses Tool mit den Daten im Adressteil hinter # (geht nicht übers Netz an einen
   Server). Das Tool übernimmt sie. Ausweg: „Als Datei sichern“. */
const META_HV = 7;
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
txt=JSON.stringify({kind:"gg-wunschliste",hv:${META_HV},at:new Date().toISOString(),page:location.pathname,pages:pages.length+1,items});
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
  return sub("imp-meta", "Lesezeichen: Meta und gg.deals", info, `<ol>
      <li>Leg einmal dieses Lesezeichen an: <a class="bm" href="${esc(metaBm())}" data-act="nobm" title="In die Lesezeichenleiste ziehen">Seite lesen</a>
        <button data-act="bmcopy" title="Für ein von Hand angelegtes Lesezeichen, auch am Handy">Code kopieren</button></li>
      <li>Öffne angemeldet <a href="https://accountscenter.meta.com/meta_pay_wallet/?tab=transactions" target="_blank" rel="noopener noreferrer">deine Transaktionen bei Meta Pay</a>, <a href="https://www.meta.com/my/orders/?order_type=digital_products&amp;timeFilter=ALL_TIME" target="_blank" rel="noopener noreferrer">deine Meta-Bestellungen</a> oder deine Wunschliste im Meta Store und klick das Lesezeichen an. Es scrollt selbst, bis alles geladen ist.
        Genauso auf deiner <a href="https://gg.deals/wishlist/" target="_blank" rel="noopener noreferrer">Wunschliste bei gg.deals</a>: Dein Browser kommt an der Prüfseite vorbei, der Server nicht.</li>
      <li>Im Kasten oben rechts „Im VR-Navigator übernehmen“: Dieses Tool öffnet sich und übernimmt Käufe oder Wunschliste. Ein altes Lesezeichen „Meta lesen“ ersetzt du durch dieses. Die Daten stehen nur in der Adresse hinter #.</li></ol>
      ${p ? previewHtml(p) : ""}`, !!(lm || lw) && !p, "imp-meta");
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
/* Konten: bei jedem Abgleich automatisch gelesen */
function accountsCard(){
  const se = S.settings || {};
  const on = [se.steam_id && "Steam", (se.gg_wish_set || se.gg_key_set) && "gg.deals", se.sharenite && "Sharenite"].filter(Boolean);
  return sub("konten", "Konten und Schlüssel", on.length ? on.join(", ") : "keins eingerichtet", `<form data-form="accounts" class="form" style="margin-top:8px">
      <label for="a-sid">SteamID oder Profil-Link</label><input type="text" id="a-sid" name="steam_id" value="${esc(se.steam_id || "")}" placeholder="https://steamcommunity.com/profiles/7656…">
      <label for="a-skey">Steam-Schlüssel</label><input type="password" id="a-skey" name="steam_key" autocomplete="off" placeholder="${se.steam_key_set ? "gespeichert, leer lassen zum Behalten" : "für den Besitz; Wunschliste geht auch ohne"}">
      ${se.steam_key_set ? `<span class="full"><label><input type="checkbox" name="steam_clear"> Steam-Schlüssel löschen</label></span>` : ""}
      <label for="a-gw">gg.deals-Wunschliste</label><input type="password" id="a-gw" name="gg_wish" autocomplete="off" placeholder="${se.gg_wish_set ? "gespeichert, leer lassen zum Behalten" : "Link aus „Wunschliste teilen“"}">
      ${se.gg_wish_set ? `<span class="full"><label><input type="checkbox" name="gg_wish_clear"> Link löschen</label></span>` : ""}
      <label for="a-gg">gg.deals-Schlüssel</label><input type="password" id="a-gg" name="gg_key" autocomplete="off" placeholder="${se.gg_key_set ? `gespeichert${se.gg_key_end ? " (…" + esc(se.gg_key_end) + ")" : ""}, leer lassen zum Behalten` : "für Händlerpreise; kostenlos auf gg.deals unter Einstellungen, API"}">
      ${se.gg_key_set ? `<span class="full"><label><input type="checkbox" name="gg_clear"> gg.deals-Schlüssel löschen</label></span>` : ""}
      <label for="a-sn">Sharenite-Profil</label><input type="text" id="a-sn" name="sharenite" value="${esc(se.sharenite || "")}" placeholder="https://www.sharenite.link/profiles/…/games">
      <span class="full"><button class="primary">Speichern</button> <span class="err" id="a-err"></span></span></form>
    <ul class="hint">
      <li><b>Steam:</b> Besitz und Wunschliste mit genauen App-IDs. Den Schlüssel gibt es kostenlos unter steamcommunity.com/dev/apikey (als Domain genügt „localhost“, Steam prüft sie nicht; den Schlüssel niemandem geben, widerrufen geht dort jederzeit); im Profil müssen die Spieldetails öffentlich sein. Ohne Schlüssel liest das Tool nur die Wunschliste. Neue Apps prüft es im Store auf VR (40 je Abgleich).</li>
      <li><b>gg.deals:</b> der Schlüssel holt Händlerpreise je Steam-App; die geteilte Wunschliste bringt Titel, die das Tool kennt oder als VR-App bei Steam findet.</li>
      <li><b>Sharenite:</b> deine Playnite-Bibliothek aller Läden (Steam, GOG, Epic …), wenn das Profil öffentlich ist. Übernommen werden Spiele mit VR-Schlagwort, höchstens alle 20 Stunden.</li>
    </ul>
    <p class="hint">Steht ein Titel auf keiner Wunschliste mehr, die ihn geführt hat, fällt er von deiner; das steht im Protokoll. Schlüssel und Wunschlisten-Link bleiben auf deinem Server (settings.json im Datenordner), stehen nicht in der Sicherung und gehen nie an den Browser zurück.</p>`, on.length > 0, "konten");
}
function wishMoves(p){
  return [p.wish_added?.length && `Neu auf der Wunschliste: ${p.wish_added.map(esc).join(", ")}.`,
    p.wish_removed?.length && `Nicht mehr auf dieser Wunschliste und damit von deiner: ${p.wish_removed.map(esc).join(", ")}.`,
    p.unknown?.length && `Nicht zugeordnet (${p.unknown.length}): ${p.unknown.slice(0, 30).map(esc).join(", ")}${p.unknown.length > 30 ? " …" : ""}.`]
    .filter(Boolean).map(x => `<p class="hint">${x}</p>`).join("");
}
function previewHtml(p){
  if(p.error) return `<p class="err">${esc(p.error)}</p>`;
  const pc = p.collection, cons = pc?.console ? ` ${pc.console} Spiele nur für Konsole (etwa PS4) bleiben draußen.` : "";
  const col = !pc ? "" : pc.n ? ` Dazu die ganze Sammlung für Entdecken: ${pc.n} Spiele, ${pc.new} neu.${cons}`
    : `${cons} Die Sammlung für Entdecken bleibt, wie sie ist${pc.kept ? ` (${pc.kept} Spiele)` : ""}.`;
  if(p.done) return `<p class="ok">${p.what ? esc(p.what) + " übernommen" : "Übernommen"}: ${p.n} erkannt, ${p.new} neu angelegt.${col}</p>` + wishMoves(p) + (p.entries?.length ? `<details class="prev"><summary class="hint">Was übernommen wurde</summary><ul>${p.entries.slice(0, 300).map(e =>
    `<li><span class="${e.known ? "" : "new"}">${esc(e.name)}</span>${e.price != null ? ` ${eur(e.price)}` : ""}${e.known ? " · war schon da" : " · neu"}</li>`).join("")}</ul></details>` : "");
  return `<div class="prev">${p.what ? `<b>${esc(p.what)}</b>${p.kind ? ` <span class="hint">(${p.guess ? "geraten, unter „Art“ änderbar" : "erkannt"})</span>` : ""}: ` : ""}${p.n} erkannt, davon ${p.new} neu.${col} Noch nichts gespeichert.${p.note ? ` <span class="hint">${esc(p.note)}</span>` : ""}<ul>${p.entries.slice(0, 300).map(e =>
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
  else if(a === "tab"){ V.tab = v; V.q = ""; render(); scrollTo(0, 0); }
  else if(a === "lf"){ V.lf[v] = !V.lf[v]; render(); }
  else if(a === "legend"){ V.legend = !V.legend; render(); }
  else if(a === "addopen"){ V.add = !V.add; render(); if(V.add) document.querySelector("form[data-form=add] input")?.focus(); }
  else if(a === "dmix"){ setMix(v); render(); }
  else if(a === "dmixoff" || a === "dpickoff"){
    // Mischung zurücknehmen: Vorschläge weg; ihre Filter bleiben nur bei „Schließen“
    if(a === "dmixoff" && V.d.mix !== "surprise") V.d = Object.assign({}, D0); else V.d.mix = "";
    render();
  }
  else if(a === "dgoff" || a === "dmpoff"){ const f = a === "dgoff" ? "g" : "mp"; V.d[f] = V.d[f].filter(x => x !== v); V.d.mix = ""; V.d.n = D0.n; render(); }
  else if(a === "dgop"){ V.d.gop = v; V.d.mix = ""; V.d.n = D0.n; V.menu = "g"; render(); }
  else if(a === "dgclear"){ V.d.g = []; V.d.mix = ""; V.d.n = D0.n; V.menu = "g"; render(); }
  else if(a === "dreset"){ V.d = Object.assign({}, D0, {sort: V.d.sort}); render(); }
  else if(a === "dshuffle"){ V.d.seed = newSeed(); render(); }
  else if(a === "dmore"){ V.d.n += D0.n; render(); }
  else if(a === "dqclear"){ V.d.q = ""; render(); $("dq")?.focus(); }
  else if(a === "qclear"){ V.q = ""; render(); $("q")?.focus(); }
  else if(a === "foldall"){ $("main").querySelectorAll("details[data-kc]").forEach(d => { d.open = !!v; keepFold(d); }); saveView(); }
  else if(a === "jump"){
    ev.preventDefault();
    const c = $(v), d = c?.matches("details") ? c : null;
    if(d) d.open = true;
    c?.scrollIntoView({block: "start"});
  }
  else if(a === "edit") openEdit(el.dataset.k);
  else if(a === "bundleadd"){ $("f-bundle").insertAdjacentHTML("beforeend", bundleField("")); $("f-bundle").lastElementChild.focus(); }
  else if(a === "close") $("edit").close();
  else if(a === "del"){
    // Kein Rückfrage-Fenster: gelöscht wird sofort, der Hinweis bietet „Rückgängig“
    const name = $("f-name")?.value || "Titel";
    const res = await act("/api/title/delete", {key: el.dataset.k});
    if(res){ $("edit").close(); toast(`„${name}“ gelöscht`, undoTo(res)); }
  }
  else if(a === "sync"){ if(await act("/api/sync", {})) watchSync(); }
  else if(a === "diag"){
    V.diagRunning = true; render();
    try{ V.diag = (await api("/api/diag", {})).lines; V.diagAt = clock(new Date()); }
    catch(e){ V.diag = ["Test fehlgeschlagen: " + e.message]; }
    V.diagRunning = false; render();
  }
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
      const res = await api("/api/import", {kind: v === "file" ? V.kindFile || "auto" : v, text, dry: a === "preview"});
      V.prev[v] = a === "apply" ? Object.assign({done: true}, res, {state: null}) : res;
      if(res.state) S = res.state;
      if(a === "apply"){ V.txt[v] = ""; if(res.collection) C = null; }
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
  if(dt.sort){ V[{wish: "sort", now: "nowSort", lib: "lsort"}[dt.sort]] = t.value; render(); return; }
  if(dt.lf){ V.lf[dt.lf] = t.checked; V.menu = "lf"; render(); return; }
  if(dt.dg || dt.dmp){
    const f = dt.dg ? "g" : "mp", x = dt.dg || dt.dmp;
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
    V.d[ds] = el.type === "checkbox" ? (el.checked ? 1 : 0) : typeof D0[ds] === "number" ? Number(el.value) || 0 : el.value;
    if(ds === "sort" && el.value === "random") V.d.seed = newSeed();
    if(ds !== "sort") V.d.mix = "";
    V.d.n = D0.n;
    render();
    return;
  }
  const kind = ev.target.dataset.file;
  if(!kind || !ev.target.files[0]) return;
  const f = ev.target.files[0];
  if(f.size > 45e6){ alert("Datei zu groß"); return; }
  const text = await f.text();
  if(kind === "restore"){
    let obj;
    try{ obj = JSON.parse(text); }catch(e){ alert("Keine gültige Sicherung"); return; }
    if(confirm(`Sicherung einspielen? Sie ersetzt alle ${S.counts.all} Titel.`)) act("/api/restore", {data: obj.data || obj, collection: obj.collection});
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
    if(f.gg_wish.value.trim()) body.gg_wish = f.gg_wish.value.trim();
    if(f.gg_wish_clear?.checked) body.gg_wish = "";
    if(f.gg_key.value.trim()) body.gg_key = f.gg_key.value.trim();
    if(f.gg_clear?.checked) body.gg_key = "";
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
load().then(() => { if(META_IN !== null && S) metaHandOver(); });
