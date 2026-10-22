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
const SRC_NAME = {qsdb: "QuestStoreDB", steam: "Steam", gg: "gg.deals", steamacc: "Steam-Konto", ggwish: "gg.deals-Wunschliste", sharenite: "Sharenite", reviews: "Steam-Rezensionen", details: "Steam-Details"};
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

function badges(r){
  const out = [];
  if(r.where === "meta" || r.where === "beide") out.push(`<span class="b" title="Im Meta Store gekauft">Meta</span>`);
  if(r.where === "pc" || r.where === "beide") out.push(`<span class="b" title="In Playnite (PC)">${esc(r.pc_label || "PC")}</span>`);
  const cbr = r.crossbuy_src ? ` ≈` : "", cbt = r.crossbuy_src ? " (laut Recherche)" : "";
  if(r.crossbuy === true) out.push(`<span class="b go" title="Spricht für Meta: der Kauf gilt auch für die PC-Fassung (Rift)${cbt}">Crossbuy${cbr}</span>`);
  if(r.crossbuy === false) out.push(`<span class="b stop" title="Spricht gegen Meta: der Kauf gilt nur auf der Quest${cbt}">kein Crossbuy${cbr}</span>`);
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

/* Werkzeugzeile: Suche mit eigenem × (Esc leert sie ebenso), dahinter Sortierung und Klappen */
function searchBar(extra){
  return `<div class="bar"><span class="sbox"><input type="search" id="q" placeholder="Titel oder Notiz suchen" aria-label="Titel oder Notiz suchen" value="${esc(V.q)}" data-in="q">${V.q ? `<button class="sx" data-act="qclear" title="Suche leeren (Esc)" aria-label="Suche leeren">×</button>` : ""}</span>${extra || ""}</div>`;
}

/* ---------------------------------------------------------------- Wunschliste */
function wishView(){
  const sorts = [["name", "Name"], ["best", "Nah am Bestpreis"], ["sale", "Rabatt"]];
  let rows = S.wishlist.filter(match);
  const k = {best: nearBest, sale: r => -Math.max(r.live.meta?.discount || 0, r.live.steam?.discount || 0)}[V.sort];
  if(k) rows = rows.slice().sort((a, b) => k(a) - k(b));
  // Was du schon besitzt (Meta oder PC), steht in einer eigenen, zugeklappten Gruppe
  const open = rows.filter(r => !r.where), owned = rows.filter(r => r.where);
  const add = `<form class="bar" data-form="add"><input type="text" name="name" placeholder="Neuer Titel" aria-label="Neuer Titel" required>
    <input type="text" name="link" placeholder="Link zu VRDB, QuestStoreDB, Meta oder Steam (optional)" aria-label="Link zum Titel (optional)">
    <button class="primary">Hinzufügen</button></form>`;
  const ow = S.counts.owned_wish;
  const head = searchBar(`<span class="chips">${sorts.map(([v, l]) => `<button data-act="sort" data-v="${v}" class="${V.sort === v ? "on" : ""}">${l}</button>`).join("")}</span>${ow ? foldAll : ""}`);
  if(!S.wishlist.length) return add + `<p class="hint">Noch keine Wunschtitel. Importiere deine Vergleichstabelle unter Einstellungen oder trage oben einen Titel ein.</p>`;
  return add + head + `<p class="hint">Preise bei Meta und Steam, das günstigere vorn, je Shop gemessen am Bestpreis der letzten 24 Monate:
    <span class="star">★</span> am Bestpreis (bis 2 % darüber), „übliches Angebot“: so tief wie in mindestens zwei Angeboten. Darunter klein gg.deals (Keyshops zählen nicht mit) und die Differenz zwischen Meta und PC. Ohne Abruf gelten die Werte aus deiner Tabelle.</p>
    ${!rows.length ? `<p class="hint">Kein Treffer.</p>` : !ow ? `<div class="list">${open.map(r => wishRow(r)).join("")}</div>`
      : grp("w-open", "Noch nicht im Besitz", open.length, `<div class="list">${open.map(r => wishRow(r)).join("")}</div>`) +
        grp("w-owned", `Schon im Besitz <span class="hint" title="Titel auf der Wunschliste, die du schon bei Meta oder am PC besitzt">(bei Meta oder am PC)</span>`, owned.length, `<div class="list">${owned.map(r => wishRow(r)).join("")}</div>`, true)}`;
}
// Sortierschlüssel: wie nah der günstigere Shop an seinem Bestpreis liegt (1 = am Bestpreis)
function nearBest(r){
  const q = ["meta", "steam"].map(s => r.best?.[s] && r.live[s] ? r.live[s].price / r.best[s].best : null).filter(x => x != null);
  return q.length ? Math.min(...q) : 1e9;
}

/* Ein Shop: Preis, Rabatt, Stufe zum Bestpreis (Farben nach docs/oberflaeche.md); der
   Abrufzeitpunkt nur, wenn der Preis älter als zwei Tage ist */
function offerHtml(shop, v, b){
  const sale = v.discount ? ` <s>${eur(v.base)}</s> <span class="b deal">−${v.discount} %${v.kind === "coupon" ? " Gutschein" : ""}</span>${v.until ? " " + until(v.until) : ""}` : "";
  let lv = "";
  if(b && !b.thin){
    const tip = `Bestpreis bei ${shop} ${b.full ? "in den letzten 24 Monaten" : "seit " + day(b.since)}: ${eur(b.best)} am ${day(b.best_at)}${b.usual != null ? `, übliches Angebot ${eur(b.usual)}` : ""}`;
    if(b.level === "best") lv = ` <span class="star" title="${esc(tip)}">★</span><span class="b best" title="${esc(tip)}">am Bestpreis${b.full ? "" : " seit " + day(b.since)}</span>`;
    else if(b.level === "usual") lv = ` <span class="hint" title="${esc(tip)}">übliches Angebot</span>`;
    else lv = ` <span class="hint" title="${esc(tip)}">Bestpreis${b.full ? "" : " seit " + day(b.since)} ${eur(b.best)}${b.once && b.usual != null ? " einmalig, sonst " + eur(b.usual) : ""} (+${eur(b.over)})</span>`;
  }
  const old = v.stale ? ` <span class="b warn" title="Älter als zwei Tage: Abruf prüfen">Stand ${ago(v.at)}</span>` : "";
  return `<span>${shop} <span class="price">${eur(v.price)}</span>${sale}${lv}${old}</span>`;
}
function liveHtml(r){
  const L = r.live, B = r.best || {}, g = L.gg;
  const offers = [["Meta", L.meta, B.meta], ["Steam", L.steam, B.steam]].filter(o => o[1]).sort((a, b) => a[1].price - b[1].price);
  const small = [];
  if(g && (g.retail != null || g.keyshops != null)) small.push(`<span title="gg.deals: günstigster Händler und Keyshop. Keyshops zählen nicht für Bestpreis und Differenz.">gg.deals ${[
    g.retail != null && "Händler " + eur(g.retail), g.keyshops != null && "Keyshop " + eur(g.keyshops),
    g.retail_low != null && "Allzeit-Tief " + eur(g.retail_low)].filter(Boolean).join(", ")}${g.stale ? ` <span class="b warn">Stand ${ago(g.at)}</span>` : ""}</span>`);
  if(r.gap_now) small.push(`<span title="Differenz: Meta jetzt gegenüber dem günstigsten PC-Angebot (Steam oder Händler)">${r.gap_now > 0 ? "PC" : "Meta"} ${eur(Math.abs(r.gap_now))} günstiger</span>`);
  if(!offers.length && !small.length) return "";
  return (offers.length ? `<div class="row2">${offers.map(o => offerHtml(...o)).join("")}</div>` : "") +
    (small.length ? `<div class="row2 small">${small.join("")}</div>` : "");
}

function wishRow(r, bars){
  const s = r.sheet, live = liveHtml(r);
  const B = r.best || {}, bar = bars ? [["Meta", r.live.meta, B.meta], ["Steam", r.live.steam, B.steam]].map(o => bestBar(...o)).join("") : "";
  const prices = live ? live + (s ? `<div class="row2 small"><span title="Aus deiner Tabelle übernommen">Tabelle, ${day(s.at)}: Meta ${eur(s.meta)}, Tief ${eur(s.meta_low)}, gg.deals ${eur(s.gg)}</span></div>` : "")
    : `<div class="row2">${s ? `<span>Meta <span class="price">${eur(s.meta)}</span></span>
      <span>Meta-Tief <span class="price">${eur(s.meta_low)}</span></span>
      <span>gg.deals <span class="price">${eur(s.gg)}</span></span>
      ${r.gap != null ? `<span>Differenz <span class="price ${r.gap > 0 ? "gap-steam" : r.gap < 0 ? "gap-meta" : ""}">${r.gap > 0 ? "+" : ""}${eur(r.gap)}</span></span>` : ""}
      <span title="Aus deiner Tabelle übernommen">Tabelle, ${day(s.at)}</span>` : `<span>keine Preise</span>`}</div>`;
  return `<div class="item"><span class="nm">${esc(r.name)}</span>${badges(r)}
    <button class="link" data-act="edit" data-k="${esc(r.key)}">bearbeiten</button>
    <button class="link" data-act="unwish" data-k="${esc(r.key)}" title="Von der Wunschliste nehmen; der Titel bleibt im Tool">nicht mehr wünschen</button>
    ${prices}${bar}
    <div class="row2">${linksHtml(r)}</div>${opinionHtml(r)}
    ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}</div>`;
}

/* ---------------------------------------------------------------- Entdecken
   Die ganze PC-Sammlung aus dem Playnite-Export (eigene Datei, beim ersten Öffnen geladen).
   Filter, Sortierung und Zufall laufen hier im Browser. Der Zustand steht in der Adresse
   (#entdecken?…), so lässt sich eine Mischung als Lesezeichen merken und wieder aufrufen. */
let C = null, cLoading = false;
const D0 = {mp: [], min: 0, g: [], st: "", sc: 0, old: 0, q: "", sort: "score", seed: 0, mix: "", n: 100};
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
    // mehrere Genres: eines davon genügt
    && (!d.g.length || d.g.some(x => g.genres.includes(x))) && (!d.st || g.store === d.st) && (!d.sc || (g.score ?? -1) >= d.sc)
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
const dLabel = d => [d.mp.map(m => C.mp_label[m] || m).join(" + "), d.min && `ab ${d.min} Spieler`, d.g.join(" oder "), d.st,
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
  const kinds = Object.entries(C.mp_label).map(([k, l]) => `<button data-act="dmp" data-v="${k}" class="${d.mp.includes(k) ? "on" : ""}">${esc(l)}</button>`).join("");
  const label = dLabel(d);
  const filters = `<details class="sub" ${foldAttr("d-filter", true)}><summary><b>Filter</b> <span class="n">${label ? esc(label) : "keine"}</span></summary>
    <div class="dfilter">
      <div class="chips" role="group" aria-label="Mehrspieler-Art">${kinds}</div>
      <label>Spieler <select data-dset="min">${opt("min", [[0, "egal"], [2, "ab 2"], [3, "ab 3"], [4, "ab 4"], [8, "ab 8"]], d.min)}</select></label>
      <div class="chips" role="group" aria-label="Genre, eines davon genügt">${C.genres.map(g => `<button data-act="dgenre" data-v="${esc(g)}" class="${d.g.includes(g) ? "on" : ""}">${esc(g)}</button>`).join("")}</div>
      <label>Laden <select data-dset="st">${opt("st", [["", "alle"]].concat(stores.map(x => [x, x])), d.st)}</select></label>
      <label>Steam-Wertung <select data-dset="sc">${opt("sc", [[0, "egal"], [60, "ab 60 %"], [70, "ab 70 %"], [80, "ab 80 %"], [90, "ab 90 %"]], d.sc)}</select></label>
      <label><input type="checkbox" data-dset="old"${d.old ? " checked" : ""}> über zwei Jahre in der Sammlung</label>
      ${label ? `<button class="link" data-act="dreset">Filter zurücksetzen</button>` : ""}
    </div></details>`;
  const bar = `<div class="bar"><span class="sbox"><input type="search" id="dq" placeholder="Name, Entwickler oder Genre suchen" aria-label="Name, Entwickler oder Genre suchen" value="${esc(d.q)}" data-in="dq">${d.q ? `<button class="sx" data-act="dqclear" title="Suche leeren" aria-label="Suche leeren">×</button>` : ""}</span>
    <label class="kind">Sortierung <select data-dset="sort">${opt("sort", D_SORTS, d.sort)}</select></label>
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
/* Abstand zum Bestpreis als Leiste, wie im eShopKompass: links der Bestpreis der letzten 24
   Monate, rechts der Normalpreis, die Füllung bis zum Preis jetzt; am Bestpreis gold */
function bestBar(shop, v, b){
  if(!v || !b || b.thin || b.best == null) return "";
  const span = (v.base || v.price) - b.best, at = b.level === "best";
  const w = at ? 0 : span > 0 ? Math.min(100, Math.max(4, (v.price - b.best) / span * 100)) : 100;
  const rel = b.best > 0 ? Math.round((v.price - b.best) / b.best * 100) : 0;
  const tip = `${shop}: jetzt ${eur(v.price)}, Bestpreis ${eur(b.best)} am ${day(b.best_at)}${b.full ? " (24 Monate)" : " (seit " + day(b.since) + ")"}, Normalpreis ${eur(v.base || v.price)}`;
  return `<div class="bbar${at ? " at" : ""}" title="${esc(tip)}"><span class="lbl">${shop}</span>
    <span class="txt">${at ? `<span class="star">★</span> am Bestpreis ${eur(b.best)}` : `<b>+${eur(v.price - b.best)}</b> über Bestpreis ${eur(b.best)} (+${rel} %)${b.level === "usual" ? ", übliches Angebot" : ""}`}</span>
    <span class="track" aria-hidden="true"><span class="fill" style="width:${w.toFixed(0)}%"></span></span></div>`;
}
function nowView(){
  const last = S.sync?.done;
  if(!last && !S.now.length) return `<p class="hint">Noch kein Abruf gelaufen. Oben über „Aktualisieren“ startest du den ersten; danach läuft er nach Zeitplan.</p>`;
  const sort = V.nowSort || "best";
  let rows = S.now.filter(match);
  if(sort === "best") rows = rows.slice().sort((a, b) => nearBest(a) - nearBest(b));
  const sorts = [["best", "Nah am Bestpreis"], ["sale", "Rabatt"]];
  return searchBar(`<span class="chips">${sorts.map(([v, l]) => `<button data-act="nowsort" data-v="${v}" class="${sort === v ? "on" : ""}">${l}</button>`).join("")}</span>`) +
    `<p class="hint">Wunschtitel, die gerade bei Meta oder Steam reduziert sind. Die Leiste zeigt je Shop, wie weit der Preis jetzt über dem Bestpreis der letzten 24 Monate liegt (links Bestpreis, rechts Normalpreis). Letzter Abruf: ${when(last) || "–"}.</p>
    <div class="list">${rows.map(r => wishRow(r, true)).join("") || `<p class="hint">Gerade ist kein Wunschtitel reduziert.</p>`}</div>`;
}

/* ---------------------------------------------------------------- Abrufe */
const SOURCES = [["steamacc", "Steam-Konto (Besitz, Wunschliste)"], ["ggwish", "gg.deals-Wunschliste"], ["sharenite", "Sharenite (Playnite)"],
  ["qsdb", "QuestStoreDB (Meta-Preise)"], ["steam", "Steam-Store"], ["gg", "gg.deals"], ["reviews", "Steam-Rezensionen (Entdecken)"], ["details", "Steam-Details (Entdecken)"]];
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
  const jumps = [open && ["todo", "Zu erledigen"], ["abgleich", "Abgleich"], ["importe", "Einlesen"], ["sicherung", "Sicherung"]].filter(Boolean);
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
  const keyInfo = se.gg_key_set ? `gg.deals-Schlüssel gespeichert${se.gg_key_end ? " (…" + esc(se.gg_key_end) + ")" : ""}` : "ohne gg.deals-Schlüssel";
  const abgleich = box("abgleich", "Abgleich", sy.running ? "läuft" : `Stand ${ago(sy.started)}${next ? ` · nächster ca. ${next < new Date() ? "in Kürze" : whenDay(next) + clock(next)}` : se.auto === false ? " · Zeitplan aus" : ""}`, `
    <p class="hint">Liest deine Konten, ordnet alle Titel zu (Meta-ID, Steam-ID prüfen) und holt Preise für deine Wunschtitel, die du noch nicht besitzt. Ein Lauf dauert einige Minuten, weil zwischen zwei Abrufen einer Quelle Pausen liegen. Nach einer Sperre ruht eine Quelle 24 Stunden.</p>
    ${sub("quellen", "Quellen", srcInfo, `<div class="list">${rows}</div>`, !bad)}
    <div class="bar" style="margin-top:10px"><button class="primary" data-act="sync" ${sy.running ? "disabled" : ""}>${sy.running ? "Läuft …" : "Jetzt abrufen"}</button>
      <button data-act="diag" ${V.diagRunning ? "disabled" : ""} title="Fragt jede Quelle einmal an und zeigt, was zurückkommt; dauert bis zu einer Minute und speichert nichts">${V.diagRunning ? "Test läuft …" : "Verbindung testen"}</button></div>
    ${V.diag ? sub("diagbox", "Verbindungstest", `${esc(V.diagAt || "")} · <button class="link" data-act="copy" data-v="diag">Ergebnis kopieren</button>`, `<pre class="log" id="diag">${esc(V.diag.join("\n"))}</pre>`) : ""}
    ${sub("logbox", "Protokoll", logInfo + (sy.started ? ` · <button class="link" data-act="copy" data-v="log">kopieren</button>` : ""), `<pre class="log" id="log"></pre>`, sy.ok !== false && !sy.running, "logfold")}
    ${sub("zeitplan", "Zeitplan und gg.deals", `${se.auto ? `alle ${esc(hours)} Std.` : "Zeitplan aus"} · ${keyInfo}`, `<form data-form="settings" class="form" style="margin-top:8px">
      <span class="full"><label><input type="checkbox" name="auto" ${se.auto ? "checked" : ""}> automatisch abrufen</label></span>
      <label for="s-h">alle … Stunden</label><input type="number" id="s-h" name="hours" min="2" max="48" value="${esc(se.hours)}">
      <label for="s-gg">gg.deals-Schlüssel</label><input type="password" id="s-gg" name="gg_key" autocomplete="off" placeholder="${se.gg_key_set ? "gespeichert, leer lassen zum Behalten" : "kostenlos auf gg.deals unter Einstellungen, API"}">
      ${se.gg_key_set ? `<span class="full"><label><input type="checkbox" name="gg_clear"> Schlüssel löschen</label></span>` : ""}
      <span class="full"><button class="primary">Speichern</button> <span class="err" id="s-err"></span></span></form>
      <p class="hint">Der Schlüssel bleibt auf deinem Server (settings.json im Datenordner). Er steht nicht in der Sicherung, nicht im Protokoll und geht nie an den Browser zurück.</p>`, !!se.gg_key_set)}`);
  const importe = box("importe", "Einlesen", "", `<p class="hint">Bringt Käufe und Wünsche ins Tool: Konten automatisch, Meta per Lesezeichen, alles andere als Datei. Gelöscht wird nichts.</p>
    ${accountsCard()}${metaCard()}${fileCard()}`);
  const sicherung = box("sicherung", "Sicherung", "", `<p class="hint">Alle Titel, Notizen und Zuordnungen als eine Datei. Einspielen ersetzt alles.</p>
     <div class="bar"><a href="/api/export" download>Sicherung herunterladen</a>
     <label>Sicherung einspielen <input type="file" accept=".json,application/json" data-file="restore"></label></div>`);
  return banners() + `<div class="jump" role="navigation" aria-label="Abschnitte">${jumps.map(([id, l]) => `<a href="#${id}" data-act="jump" data-v="${id}">${l}</a>`).join("")}${foldAll}</div>` +
    sugCard + abgleich + importe + sicherung;
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
  return `<details class="op" ${foldAttr("op-" + r.key, true)}><summary><span class="hint">Recherche${o.stand ? ", " + esc(o.stand) : ""}:</span> ${esc(head || "Meinungen")}</summary>
    ${rows.map(([l, v]) => `<div class="small"><b>${l}:</b> ${esc(v)}</div>`).join("")}${src ? `<div class="small"><b>Quellen:</b> ${src}</div>` : ""}</details>`;
}

function libView(){
  // Gruppen nach Laden: auf beiden Seiten, nur Meta, nur PC; jede klappbar
  const ws = [["beide", "Bei Meta und am PC"], ["meta", "Nur bei Meta"], ["pc", "Nur am PC"]];
  const rows = S.library.filter(match);
  if(!S.library.length) return `<p class="hint">Noch nichts im Besitz. Importiere unter Einstellungen deine Meta-Bestellungen und den Playnite-Export.</p>`;
  const row = r => `<div class="item"><span class="nm">${esc(r.name)}</span>${badges(r)}
      ${r.wish ? `<span class="b" title="Steht auch auf der Wunschliste">Wunsch</span>` : ""}
      <button class="link" data-act="edit" data-k="${esc(r.key)}">bearbeiten</button>
      <div class="row2">${linksHtml(r)}</div>${opinionHtml(r)}
      ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}</div>`;
  const groups = ws.map(([w, l]) => [w, l, rows.filter(r => r.where === w)]).filter(g => g[2].length);
  return searchBar(groups.length > 1 ? foldAll : "") + (groups.map(([w, l, rs]) =>
    grp("l-" + w, l, rs.length, `<div class="list">${rs.map(row).join("")}</div>`)).join("") || `<p class="hint">Kein Treffer.</p>`);
}

/* ---------------------------------------------------------------- Import */
/* Lesezeichen „Seite lesen“ (wie „Käufe lesen“ im eShopKompass): läuft in deinem Browser, wo du
   angemeldet bist und Prüfseiten wie die von Cloudflare schon bestanden hast.
   - Meta: Bestellseite, Transaktionen von Meta Pay oder Wunschliste; scrollt, bis alles geladen ist.
   - gg.deals: deine Wunschliste; weitere Seiten holt es mit kurzer Pause nach.
   Dann öffnet es dieses Tool mit den Daten im Adressteil hinter # (geht nicht übers Netz an einen
   Server). Das Tool übernimmt sie. Ausweg: „Als Datei sichern“. */
const META_HV = 6;
function metaHelper(tool){ return `(async()=>{
const gg=/(^|\\.)gg\\.deals$/.test(location.hostname);
if(!gg&&!/(^|\\.)meta\\.com$/.test(location.hostname)){alert("Bitte zuerst eine dieser Seiten öffnen, dann das Lesezeichen anklicken: angemeldet deine Meta-Bestellungen (meta.com/my/orders), die Transaktionen von Meta Pay, deine Wunschliste im Meta Store oder deine Wunschliste bei gg.deals.");return}
if(gg&&!/wishlist/.test(location.pathname)){alert("Bitte deine Wunschliste bei gg.deals öffnen (angemeldet oder über den Teilen-Link), dann das Lesezeichen anklicken.");return}
const box=document.createElement("div");box.style.cssText="position:fixed;z-index:2147483647;top:12px;right:12px;width:min(420px,90vw);background:#fff;color:#111;border:2px solid #24383b;border-radius:8px;padding:12px;font:14px sans-serif";box.textContent="VR-Navigator: lade alles …";document.body.appendChild(box);
const look=(b,main)=>{b.style.cssText="margin:0 8px 6px 0;padding:6px 12px;border-radius:6px;font:600 13px sans-serif;cursor:pointer;"+(main?"background:#24383b;color:#fff;border:1px solid #24383b":"background:#f3f4f1;color:#1b2224;border:1px solid #9aa3a1");return b};
const wait=t=>new Promise(r=>setTimeout(r,t));
let txt,msg,file;
if(gg){
const read=d=>[...d.querySelectorAll("a[href*='/game/']")].map(a=>{const m=(a.getAttribute("href")||"").match(/\\/game\\/([a-z0-9-]+)\\/?(?:[?#].*)?$/);return m&&{slug:m[1],name:(a.innerText||a.title||"").trim().replace(/\\s+/g," ").slice(0,200)}}).filter(Boolean);
let items=read(document);const base=location.href.split(/[?#]/)[0];
const last=Math.min(30,Math.max(1,...[...document.querySelectorAll("a[href*='page=']")].filter(a=>a.href.split("?")[0]===base).map(a=>+((a.href.match(/[?&]page=(\\d+)/)||[])[1]||1))));
const pages=[];for(let p=2;p<=last;p++){const u=new URL(location.href);u.searchParams.set("page",p);pages.push(u.href)}
for(let i=0;i<pages.length;i++){box.textContent="VR-Navigator: lese Seite "+(i+2)+" von "+(pages.length+1)+" …";await wait(1200);try{const r=await fetch(pages[i],{credentials:"include"});items=items.concat(read(new DOMParser().parseFromString(await r.text(),"text/html")))}catch(e){}}
const by={};items.forEach(x=>{if(!by[x.slug]||(!by[x.slug].name&&x.name))by[x.slug]=x});items=Object.values(by);
txt=JSON.stringify({kind:"gg-wunschliste",hv:${META_HV},at:new Date().toISOString(),page:location.pathname,pages:pages.length+1,items});
msg="gg.deals-Wunschliste gelesen: "+items.length+" Spiele. Der VR-Navigator übernimmt sie.";file="gg-wunschliste.json";
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
  const on = [se.steam_id && "Steam", se.gg_wish_set && "gg.deals", se.sharenite && "Sharenite"].filter(Boolean);
  return sub("konten", "Konten, automatisch bei jedem Abgleich", on.length ? on.join(", ") : "keins eingerichtet", `<form data-form="accounts" class="form" style="margin-top:8px">
      <label for="a-sid">SteamID oder Profil-Link</label><input type="text" id="a-sid" name="steam_id" value="${esc(se.steam_id || "")}" placeholder="https://steamcommunity.com/profiles/7656…">
      <label for="a-skey">Steam-Schlüssel</label><input type="password" id="a-skey" name="steam_key" autocomplete="off" placeholder="${se.steam_key_set ? "gespeichert, leer lassen zum Behalten" : "für den Besitz; Wunschliste geht auch ohne"}">
      ${se.steam_key_set ? `<span class="full"><label><input type="checkbox" name="steam_clear"> Steam-Schlüssel löschen</label></span>` : ""}
      <label for="a-gw">gg.deals-Wunschliste</label><input type="password" id="a-gw" name="gg_wish" autocomplete="off" placeholder="${se.gg_wish_set ? "gespeichert, leer lassen zum Behalten" : "Link aus „Wunschliste teilen“"}">
      ${se.gg_wish_set ? `<span class="full"><label><input type="checkbox" name="gg_wish_clear"> Link löschen</label></span>` : ""}
      <label for="a-sn">Sharenite-Profil</label><input type="text" id="a-sn" name="sharenite" value="${esc(se.sharenite || "")}" placeholder="https://www.sharenite.link/profiles/…/games">
      <span class="full"><button class="primary">Speichern</button> <span class="err" id="a-err"></span></span></form>
    <ul class="hint">
      <li><b>Steam:</b> Besitz und Wunschliste mit genauen App-IDs. Den Schlüssel gibt es kostenlos unter steamcommunity.com/dev/apikey (als Domain genügt „localhost“, Steam prüft sie nicht; den Schlüssel niemandem geben, widerrufen geht dort jederzeit); im Profil müssen die Spieldetails öffentlich sein. Ohne Schlüssel liest das Tool nur die Wunschliste. Neue Apps prüft es im Store auf VR (40 je Abgleich).</li>
      <li><b>gg.deals:</b> deine geteilte Wunschliste. Es zählen Titel, die das Tool kennt oder als VR-App bei Steam findet.</li>
      <li><b>Sharenite:</b> deine Playnite-Bibliothek aller Läden (Steam, GOG, Epic …), wenn das Profil öffentlich ist. Übernommen werden Spiele mit VR-Schlagwort, höchstens alle 20 Stunden.</li>
    </ul>
    <p class="hint">Steht ein Titel auf keiner Wunschliste mehr, die ihn geführt hat, fällt er von deiner; das steht im Protokoll. Schlüssel und Wunschlisten-Link bleiben auf deinem Server und gehen nie an den Browser zurück.</p>`, on.length > 0, "konten");
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
  const cb = r.crossbuy === true ? "yes" : r.crossbuy === false ? "no" : "";
  $("edit").innerHTML = `<form method="dialog" data-form="edit" data-k="${esc(key)}"><h2>${esc(r.name)}</h2>
    <div class="form">
      <label for="f-name">Name</label><input type="text" id="f-name" name="name" value="${esc(r.name)}" required>
      <label for="f-meta">Meta-ID</label><input type="text" id="f-meta" name="meta_id" value="${esc(r.meta_id)}" inputmode="numeric" placeholder="Zahl oder Link (Meta, QuestStoreDB, VRDB)">
      <label for="f-steam">Steam-App-ID</label><input type="text" id="f-steam" name="steam_appid" value="${esc(r.steam_appid)}" inputmode="numeric">
      <label for="f-cb">Crossbuy</label><select id="f-cb" name="crossbuy"><option value="">unbekannt</option><option value="yes" ${cb === "yes" ? "selected" : ""}>ja</option><option value="no" ${cb === "no" ? "selected" : ""}>nein</option></select>
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
  else if(a === "sort"){ V.sort = v; render(); }
  else if(a === "nowsort"){ V.nowSort = v; render(); }
  else if(a === "dmix"){ setMix(v); render(); }
  else if(a === "dmixoff" || a === "dpickoff"){
    // Mischung zurücknehmen: Vorschläge weg; ihre Filter bleiben nur bei „Schließen“
    if(a === "dmixoff" && V.d.mix !== "surprise") V.d = Object.assign({}, D0); else V.d.mix = "";
    render();
  }
  else if(a === "dgenre"){ const g = V.d.g; V.d.g = g.includes(v) ? g.filter(x => x !== v) : g.concat(v); V.d.mix = ""; V.d.n = D0.n; render(); }
  else if(a === "dmp"){ const m = V.d.mp; V.d.mp = m.includes(v) ? m.filter(x => x !== v) : m.concat(v); V.d.mix = ""; V.d.n = D0.n; render(); }
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
  if(ev.target.dataset.in === "dq"){
    V.d.q = ev.target.value; V.d.n = D0.n; render();
    const q = $("dq"); q.focus(); q.setSelectionRange(q.value.length, q.value.length);
  }
});

document.addEventListener("change", async ev => {
  const ds = ev.target.dataset.dset;
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
  if(kind === "settings"){
    ev.preventDefault();
    const body = {auto: f.auto.checked, hours: Number(f.hours.value)};
    if(f.gg_key.value.trim()) body.gg_key = f.gg_key.value.trim();
    if(f.gg_clear?.checked) body.gg_key = "";
    if(await act("/api/settings", body, $("s-err"))) toast("Gespeichert");
  }
  if(kind === "accounts"){
    ev.preventDefault();
    const body = {steam_id: f.steam_id.value.trim(), sharenite: f.sharenite.value.trim()};
    if(f.steam_key.value.trim()) body.steam_key = f.steam_key.value.trim();
    if(f.steam_clear?.checked) body.steam_key = "";
    if(f.gg_wish.value.trim()) body.gg_wish = f.gg_wish.value.trim();
    if(f.gg_wish_clear?.checked) body.gg_wish = "";
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
document.addEventListener("toggle", ev => { if(ev.target.dataset?.kc){ keepFold(ev.target); saveView(); } }, true);
document.addEventListener("click", ev => { if(!ev.target.closest(".thm")) themeMenu(false); });
document.addEventListener("keydown", ev => {
  if(ev.key !== "Escape") return;
  themeMenu(false);
  if(ev.target.id === "q" && V.q){ ev.preventDefault(); V.q = ""; render(); $("q")?.focus(); }
  if(ev.target.id === "dq" && V.d.q){ ev.preventDefault(); V.d.q = ""; render(); $("dq")?.focus(); }
});
addEventListener("resize", navFade);
$("nav").addEventListener("scroll", navFade);

renderTheme();
readFindHash();
load().then(() => { if(META_IN !== null && S) metaHandOver(); });
