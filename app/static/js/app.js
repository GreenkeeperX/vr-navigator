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
const TABS = [["now", "Jetzt"], ["wish", "Wunschliste"], ["lib", "Bibliothek"], ["settings", "Einstellungen"]];
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
/* Karte der Einstellungen: Überschrift klappt den Inhalt */
function card(id, title, n, body, shut){
  return `<div class="card" id="${id}"><details ${foldAttr("c-" + id, shut)}><summary><h2>${title}</h2>${n ? `<span class="n">${esc(n)}</span>` : ""}</summary>${body}</details></div>`;
}

/* ---------------------------------------------------------------- Rahmen */
function renderNav(){
  const c = S.counts, sug = S.suggestions.length;
  const sy = S.sync || {};
  const set = sy.running ? "läuft" : Object.values(sy.sources || {}).some(x => !x.ok) ? "Fehler" : sug ? `${sug} prüfen` : "";
  const cnt = {now: c.now || "", wish: c.wish, lib: c.owned, settings: set};
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
const SRC_NAME = {qsdb: "QuestStoreDB", steam: "Steam", gg: "gg.deals"};
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
    : V.tab === "settings" ? settingsView() : banners() + wishView();
  showLog();
  const b = anchor && $(anchor);
  if(b && top !== null) scrollBy(0, b.getBoundingClientRect().top - top);
  const q = $("q");
  if(q && document.activeElement !== q && V.focusQ){ q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
}

function badges(r){
  const out = [];
  if(r.where === "meta" || r.where === "beide") out.push(`<span class="b" title="Im Meta Store gekauft">Meta</span>`);
  if(r.where === "pc" || r.where === "beide") out.push(`<span class="b" title="In Playnite (PC)">${esc(r.pc_label || "PC")}</span>`);
  if(r.crossbuy === true) out.push(`<span class="b go" title="Spricht für Meta: der Kauf gilt auch für die PC-Fassung (Rift)">Crossbuy</span>`);
  if(r.crossbuy === false) out.push(`<span class="b" title="Meta-Kauf gilt nur auf der Quest">kein Crossbuy</span>`);
  if(r.steam_appid && !r.steam_sure) out.push(`<span class="b warn" title="Steam-ID aus Playnite geraten, bitte prüfen">Steam-ID ≈</span>`);
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
  const sorts = [["name", "Name"], ["gap", "Abstand"], ["low", "Meta-Tief"]];
  // Was du schon besitzt (Meta oder PC), fällt von der Wunschliste, außer du lässt es zeigen
  let rows = S.wishlist.filter(match);
  const k = {gap: r => r.gap_now ?? r.gap ?? 1e9, low: r => r.live.meta?.low ?? r.sheet?.meta_low ?? 1e9}[V.sort];
  if(k) rows = rows.slice().sort((a, b) => k(a) - k(b));
  // Was du schon besitzt (Meta oder PC), steht in einer eigenen, zugeklappten Gruppe
  const open = rows.filter(r => !r.where), owned = rows.filter(r => r.where);
  const add = `<form class="bar" data-form="add"><input type="text" name="name" placeholder="Neuer Titel" aria-label="Neuer Titel" required>
    <input type="text" name="link" placeholder="Link zu VRDB, QuestStoreDB, Meta oder Steam (optional)" aria-label="Link zum Titel (optional)">
    <button class="primary">Hinzufügen</button></form>`;
  const ow = S.counts.owned_wish;
  const head = searchBar(`<span class="chips">${sorts.map(([v, l]) => `<button data-act="sort" data-v="${v}" class="${V.sort === v ? "on" : ""}">${l}</button>`).join("")}</span>${ow ? foldAll : ""}`);
  if(!S.wishlist.length) return add + `<p class="hint">Noch keine Wunschtitel. Importiere deine Vergleichstabelle unter Einstellungen oder trage oben einen Titel ein.</p>`;
  return add + head + `<p class="hint">Live-Preise von QuestStoreDB (Meta), Steam und gg.deals, Stand jeweils dabei; ohne Abruf gelten die Werte aus deiner Tabelle.
    Abstand = Meta jetzt minus günstigstes PC-Angebot jetzt (bei Tabellenwerten: Meta-Tief minus gg.deals): <span class="gap-steam">+ PC günstiger</span>, <span class="gap-meta">− Meta günstiger</span>.</p>
    ${!rows.length ? `<p class="hint">Kein Treffer.</p>` : !ow ? `<div class="list">${open.map(wishRow).join("")}</div>`
      : grp("w-open", "Noch nicht im Besitz", open.length, `<div class="list">${open.map(wishRow).join("")}</div>`) +
        grp("w-owned", `Schon im Besitz <span class="hint" title="Titel auf der Wunschliste, die du schon bei Meta oder am PC besitzt">(bei Meta oder am PC)</span>`, owned.length, `<div class="list">${owned.map(wishRow).join("")}</div>`, true)}`;
}

function gapHtml(g, label){
  return g != null ? `<span>${label} <span class="price ${g > 0 ? "gap-steam" : g < 0 ? "gap-meta" : ""}">${g > 0 ? "+" : ""}${eur(g)}</span></span>` : "";
}
const stamp = (v, src) => `<span class="${v.stale ? "b warn" : ""}" title="${v.stale ? "Älter als zwei Tage: Abruf prüfen" : "Zeitpunkt des Abrufs"}">${src}, ${when(v.at)}</span>`;
function liveHtml(r){
  const L = r.live, m = L.meta, st = L.steam, g = L.gg, out = [];
  if(m){
    const sale = m.discount ? ` <span class="b deal">−${m.discount} %${m.kind === "coupon" ? " Gutschein" : ""}</span> ${until(m.until)}` : "";
    out.push(`<span>Meta ${m.at_low ? `<span class="star" title="So günstig war der Titel bei Meta noch nie">★</span>` : ""}<span class="price">${eur(m.price)}</span>${m.discount ? ` <s>${eur(m.base)}</s>` : ""}${sale}${m.at_low ? ` <span class="b best" title="So günstig war der Titel bei Meta noch nie">Tiefstpreis</span>` : ""}</span>`);
    if(m.low != null) out.push(`<span title="Tiefstpreis laut QuestStoreDB${m.low_at ? ", " + day(m.low_at) : ""}">Meta-Tief <span class="price">${eur(m.low)}</span></span>`);
  }
  if(st) out.push(`<span>Steam <span class="price">${eur(st.price)}</span>${st.discount ? ` <s>${eur(st.base)}</s> <span class="b deal">−${st.discount} %</span>` : ""}</span>`);
  if(g && (g.retail != null || g.keyshops != null)) out.push(`<span title="gg.deals: Händler / Keyshops, darunter das bisherige Tief">gg.deals <span class="price">${eur(g.retail)}</span> / <span class="price">${eur(g.keyshops)}</span></span>`);
  if(!out.length) return "";
  out.push(gapHtml(r.gap_now, "Abstand"));
  const st2 = [m && stamp(m, "QSDB"), st && stamp(st, "Steam"), g && stamp(g, "gg.deals")].filter(Boolean).join(" ");
  return `<div class="row2">${out.join("")}</div><div class="row2 small">${st2}</div>`;
}

function wishRow(r){
  const s = r.sheet, live = liveHtml(r);
  const prices = live ? live + (s ? `<div class="row2 small"><span title="Aus deiner Tabelle übernommen">Tabelle, ${day(s.at)}: Meta ${eur(s.meta)}, Tief ${eur(s.meta_low)}, gg.deals ${eur(s.gg)}</span></div>` : "")
    : `<div class="row2">${s ? `<span>Meta <span class="price">${eur(s.meta)}</span></span>
      <span>Meta-Tief <span class="price">${eur(s.meta_low)}</span></span>
      <span>gg.deals <span class="price">${eur(s.gg)}</span></span>
      ${r.gap != null ? `<span>Abstand <span class="price ${r.gap > 0 ? "gap-steam" : r.gap < 0 ? "gap-meta" : ""}">${r.gap > 0 ? "+" : ""}${eur(r.gap)}</span></span>` : ""}
      <span title="Aus deiner Tabelle übernommen">Tabelle, ${day(s.at)}</span>` : `<span>keine Preise</span>`}</div>`;
  return `<div class="item"><span class="nm">${esc(r.name)}</span>${badges(r)}
    <button class="link" data-act="edit" data-k="${esc(r.key)}">bearbeiten</button>
    ${prices}
    <div class="row2">${linksHtml(r)}</div>
    ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}</div>`;
}

/* ---------------------------------------------------------------- Jetzt */
function nowView(){
  const last = S.sync?.done;
  if(!last && !S.now.length) return `<p class="hint">Noch kein Abruf gelaufen. Oben über „Aktualisieren“ startest du den ersten; danach läuft er nach Zeitplan.</p>`;
  const rows = S.now.filter(match);
  return searchBar() + `<p class="hint">Wunschtitel, die gerade bei Meta oder Steam reduziert sind, der größte Rabatt zuerst. Letzter Abruf: ${when(last) || "–"}.</p>
    <div class="list">${rows.map(wishRow).join("") || `<p class="hint">Gerade ist kein Wunschtitel reduziert.</p>`}</div>`;
}

/* ---------------------------------------------------------------- Abrufe */
const SOURCES = [["qsdb", "QuestStoreDB (Meta-Preise)"], ["steam", "Steam-Store"], ["gg", "gg.deals"]];
function srcState(k, x){
  if(!x) return `<span class="hint">${k === "gg" && !S.settings?.gg_key_set ? "ohne Schlüssel aus" : "noch nicht gelaufen"}</span>`;
  const rest = x.until && new Date(x.until) > new Date();
  const tag = x.ok ? `<span class="b go">ok</span>` : rest ? `<span class="b warn" title="${esc(x.msg || "")}">ruht bis ${esc(whenDay(new Date(x.until)) + clock(new Date(x.until)))}</span>`
    : `<span class="b stop">${esc(x.msg || "Fehler")}</span>`;
  return `${tag} <span class="hint">${when(x.at)}, ${x.requests ?? 0} Abrufe${x.errors ? `, ${x.errors} Fehler` : ""}</span>`;
}
/* ---------------------------------------------------------------- Einstellungen
   Karten mit Sprungleiste: Abgleich, Zeitplan, Protokoll, die Importe, Sicherung. Jede Karte
   klappt an ihrer Überschrift; was erledigt ist (ein Import, der schon lief), startet zu. */
function settingsView(){
  const sy = S.sync || {}, se = S.settings || {}, src = sy.sources || {}, sug = S.suggestions.length;
  const rows = SOURCES.map(([k, l]) => `<div class="item"><span class="nm">${l}</span>${srcState(k, src[k])}</div>`).join("");
  const jumps = [sug && ["sug", "Derselbe Titel?"], ["abgleich", "Abgleich"], ["zeitplan", "Zeitplan"], ["logcard", "Protokoll"],
    ["imp-sheet", "Tabelle"], ["imp-meta", "Meta-Käufe"], ["imp-playnite", "Playnite"], ["sicherung", "Sicherung"]].filter(Boolean);
  const sugCard = sug ? card("sug", "Derselbe Titel?", sug, `
    <p class="hint">Diese Paare heißen fast gleich, einer stammt aus Meta, der andere vom PC. Zusammenführen heißt: ein Eintrag mit beiden Seiten.</p>
    <div class="list">${S.suggestions.map(x => `<div class="item"><span class="nm">${esc(x.a_name)} ↔ ${esc(x.b_name)}</span>
      <button data-act="merge" data-a="${esc(x.a)}" data-b="${esc(x.b)}">Zusammenführen</button>
      <button data-act="notsame" data-a="${esc(x.a)}" data-b="${esc(x.b)}">Verschieden</button></div>`).join("")}</div>`) : "";
  return banners() + `<div class="jump" role="navigation" aria-label="Abschnitte">${jumps.map(([id, l]) => `<a href="#${id}" data-act="jump" data-v="${id}">${l}</a>`).join("")}${foldAll}</div>` + sugCard +
    card("abgleich", "Abgleich", sy.running ? "läuft" : "", `
    <p class="hint">Holt Preise für deine Wunschtitel, die du noch nicht besitzt. Ein Lauf dauert einige Minuten, weil zwischen zwei Abrufen einer Quelle Pausen liegen. Nach einer Sperre ruht eine Quelle 24 Stunden.</p>
    <div class="bar"><button class="primary" data-act="sync" ${sy.running ? "disabled" : ""}>${sy.running ? "Läuft …" : "Jetzt abrufen"}</button>
      <span class="hint">Zuletzt: ${when(sy.started) || "nie"}${sy.finished ? `, fertig ${when(sy.finished)}` : ""}</span></div>
    <div class="list">${rows}</div>
    <p class="hint" style="margin-top:10px"><button class="link" data-act="diag" ${V.diagRunning ? "disabled" : ""}>${V.diagRunning ? "Test läuft …" : "Verbindung testen"}</button>
      ${V.diag ? ` · <button class="link" data-act="copy" data-v="diag">Ergebnis kopieren</button>` : ""}
      <span class="hint">fragt jede Quelle einmal an und zeigt, was zurückkommt; dauert bis zu einer Minute und speichert nichts</span></p>
    ${V.diag ? `<pre class="log" id="diag">${esc(V.diag.join("\n"))}</pre>` : ""}`) +
    card("zeitplan", "Zeitplan und gg.deals", se.auto ? `alle ${se.hours} Std.` : "aus", `<form data-form="settings" class="form">
      <span class="full"><label><input type="checkbox" name="auto" ${se.auto ? "checked" : ""}> automatisch abrufen</label></span>
      <label for="s-h">alle … Stunden</label><input type="number" id="s-h" name="hours" min="2" max="48" value="${esc(se.hours)}">
      <label for="s-gg">gg.deals-Schlüssel</label><input type="password" id="s-gg" name="gg_key" autocomplete="off" placeholder="${se.gg_key_set ? "gespeichert" + (se.gg_key_end ? " (…" + esc(se.gg_key_end) + ")" : "") + ", leer lassen zum Behalten" : "kostenlos auf gg.deals unter Einstellungen, API"}">
      ${se.gg_key_set ? `<span class="full"><label><input type="checkbox" name="gg_clear"> Schlüssel löschen</label></span>` : ""}
      <span class="full"><button class="primary">Speichern</button> <span class="err" id="s-err"></span></span></form>
      <p class="hint">Der Schlüssel bleibt auf deinem Server (settings.json im Datenordner). Er steht nicht in der Sicherung, nicht im Protokoll und geht nie an den Browser zurück.</p>`) +
    card("logcard", "Protokoll", sy.ok === false ? "mit Fehlern" : "", `
      <p class="hint">Protokoll des letzten Abgleichs, live während eines Laufs · <button class="link" data-act="copy" data-v="log">kopieren</button></p>
      <pre class="log" id="log"></pre>`) +
    importCard("sheet") + importCard("meta") + importCard("playnite") +
    card("sicherung", "Sicherung", "", `<p class="hint">Alle Titel, Notizen und Zuordnungen als eine Datei. Einspielen ersetzt alles.</p>
     <div class="bar"><a href="/api/export" download>Sicherung herunterladen</a>
     <label>Sicherung einspielen <input type="file" accept=".json,application/json" data-file="restore"></label></div>`);
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
function libView(){
  // Gruppen nach Laden: auf beiden Seiten, nur Meta, nur PC; jede klappbar
  const ws = [["beide", "Bei Meta und am PC"], ["meta", "Nur bei Meta"], ["pc", "Nur am PC"]];
  const rows = S.library.filter(match);
  if(!S.library.length) return `<p class="hint">Noch nichts im Besitz. Importiere unter Einstellungen deine Meta-Bestellungen und den Playnite-Export.</p>`;
  const row = r => `<div class="item"><span class="nm">${esc(r.name)}</span>${badges(r)}
      ${r.wish ? `<span class="b" title="Steht auch auf der Wunschliste">Wunsch</span>` : ""}
      <button class="link" data-act="edit" data-k="${esc(r.key)}">bearbeiten</button>
      <div class="row2">${linksHtml(r)}</div>
      ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}</div>`;
  const groups = ws.map(([w, l]) => [w, l, rows.filter(r => r.where === w)]).filter(g => g[2].length);
  return searchBar(groups.length > 1 ? foldAll : "") + (groups.map(([w, l, rs]) =>
    grp("l-" + w, l, rs.length, `<div class="list">${rs.map(row).join("")}</div>`)).join("") || `<p class="hint">Kein Treffer.</p>`);
}

/* ---------------------------------------------------------------- Import */
/* Lesezeichen „Meta-Käufe lesen“ (wie „Käufe lesen“ im eShopKompass): läuft angemeldet auf der
   Bestellseite oder den Transaktionen bei Meta, scrollt, bis alles geladen ist, und öffnet dann
   dieses Tool mit Seitentext und Links im Adressteil hinter # (geht nicht übers Netz an einen
   Server). Das Tool liest die Käufe dort und übernimmt sie. Ausweg: „Als Datei sichern“. */
const META_HV = 2;
function metaHelper(tool){ return `(async()=>{
if(!/(^|\\.)meta\\.com$/.test(location.hostname)){alert("Bitte zuerst angemeldet deine Meta-Bestellungen (meta.com/my/orders) oder die Transaktionen von Meta Pay öffnen, dann das Lesezeichen anklicken.");return}
const box=document.createElement("div");box.style.cssText="position:fixed;z-index:2147483647;top:12px;right:12px;width:min(420px,90vw);background:#fff;color:#111;border:2px solid #24383b;border-radius:8px;padding:12px;font:14px sans-serif";box.textContent="VR-Navigator: lade alle Käufe …";document.body.appendChild(box);
const look=(b,main)=>{b.style.cssText="margin:0 8px 6px 0;padding:6px 12px;border-radius:6px;font:600 13px sans-serif;cursor:pointer;"+(main?"background:#24383b;color:#fff;border:1px solid #24383b":"background:#f3f4f1;color:#1b2224;border:1px solid #9aa3a1");return b};
const wait=t=>new Promise(r=>setTimeout(r,t));
let h=0,same=0;for(let i=0;i<60&&same<3;i++){scrollTo(0,document.documentElement.scrollHeight);await wait(1200);const n=document.documentElement.scrollHeight;same=n===h?same+1:0;h=n;box.textContent="VR-Navigator: lade alle Käufe … ("+(i+1)+")"}
scrollTo(0,0);
const links=[...document.querySelectorAll("a[href]")].filter(a=>/\\/(experiences|order)\\//.test(a.href)).slice(0,3000).map(a=>({href:a.href,text:(a.innerText||"").trim().slice(0,200)}));
const txt=JSON.stringify({kind:"meta-bestellungen",hv:${META_HV},at:new Date().toISOString(),links,text:document.body.innerText.slice(0,400000)});
box.textContent="";const p=document.createElement("p");p.style.margin="0 0 8px";p.textContent="Seite gelesen. Der VR-Navigator erkennt die Käufe und übernimmt sie.";
const go=look(document.createElement("button"),true);go.textContent="Im VR-Navigator übernehmen";go.onclick=()=>{window.open(${JSON.stringify(tool)}+"/#meta="+encodeURIComponent(txt),"_blank");box.remove()};
const f=look(document.createElement("button"));f.textContent="Als Datei sichern";f.onclick=()=>{const a=document.createElement("a");a.href=URL.createObjectURL(new Blob([txt],{type:"application/json"}));a.download="meta-bestellungen.json";document.body.appendChild(a);a.click();a.remove()};
const b=look(document.createElement("button"));b.textContent="Schließen";b.onclick=()=>box.remove();
box.append(p,go,f,b);
})();`; }
const metaBm = () => "javascript:" + encodeURIComponent(metaHelper(location.origin));

const IMPORTS = {
  sheet: {title: "Vergleichstabelle (CSV)", what: "Deine Tabelle mit Spiel, meta, Bestpreis, gg.deals best, Crossbuy und Links. Die Titel landen auf der Wunschliste, sofern du sie nicht schon besitzt.", accept: ".csv,text/csv"},
  playnite: {title: "Playnite-Export (CSV)", what: "Bibliothek aus Playnite. Übernommen werden Spiele mit VR-Schlagwort und alle, die schon in deiner Liste stehen. Sie gelten als Besitz am PC.", accept: ".csv,text/csv"},
  meta: {title: "Meta-Bestellungen", what: "", accept: ".json,.txt,application/json,text/plain"},
};
function importCard(kind){
  const c = IMPORTS[kind], last = S.imports[kind], p = V.prev[kind];
  const metaHow = kind === "meta" ? `<ol>
      <li>Leg einmal dieses Lesezeichen an: <a class="bm" href="${esc(metaBm())}" data-act="nobm" title="In die Lesezeichenleiste ziehen">Meta-Käufe lesen</a>
        <button data-act="bmcopy" title="Für ein von Hand angelegtes Lesezeichen, auch am Handy">Code kopieren</button>
        <span class="hint">Ein Lesezeichen aus einer früheren Version (es lud nur eine Datei herunter) bitte löschen.</span></li>
      <li>Öffne angemeldet <a href="https://www.meta.com/my/orders/?order_type=digital_products&amp;timeFilter=ALL_TIME" target="_blank" rel="noopener noreferrer">deine Meta-Bestellungen</a> (oder die Transaktionen von Meta Pay) und klick das Lesezeichen an. Es scrollt selbst, bis alles geladen ist.</li>
      <li>Im Kasten oben rechts „Im VR-Navigator übernehmen“: Dieses Tool öffnet sich und übernimmt die Käufe. Die Daten stehen nur in der Adresse hinter #.</li></ol>
      <p class="hint">Ohne Lesezeichen: Datei aus „Als Datei sichern“ unten auswählen oder den Seitentext einfügen, dann erst Vorschau.</p>` : `<p class="hint">${c.what}</p>`;
  return card("imp-" + kind, c.title, last ? `zuletzt ${day(last.at)}` : "", `${metaHow}
    ${last ? `<p class="hint">Zuletzt: ${day(last.at)}, ${last.n} erkannt, ${last.new} neu.</p>` : ""}
    <div class="bar"><input type="file" accept="${c.accept}" data-file="${kind}" aria-label="${esc(c.title)}: Datei wählen"></div>
    <textarea id="txt-${kind}" aria-label="${esc(c.title)}: Inhalt einfügen" placeholder="… oder Inhalt hier einfügen">${esc(V.txt?.[kind] || "")}</textarea>
    <div class="bar"><button data-act="preview" data-v="${kind}">Vorschau</button>
      ${p && !p.error && !p.done ? `<button class="primary" data-act="apply" data-v="${kind}">${p.n} übernehmen</button>` : ""}</div>
    ${p ? previewHtml(p) : ""}`, !!last && !p);
}
function previewHtml(p){
  if(p.error) return `<p class="err">${esc(p.error)}</p>`;
  if(p.done) return `<p class="ok">Übernommen: ${p.n} erkannt, ${p.new} neu angelegt.</p>` + (p.entries?.length ? `<details class="prev"><summary class="hint">Was übernommen wurde</summary><ul>${p.entries.slice(0, 300).map(e =>
    `<li><span class="${e.known ? "" : "new"}">${esc(e.name)}</span>${e.price != null ? ` ${eur(e.price)}` : ""}${e.known ? " · war schon da" : " · neu"}</li>`).join("")}</ul></details>` : "");
  return `<div class="prev">${p.n} erkannt, davon ${p.new} neu. Noch nichts gespeichert.<ul>${p.entries.slice(0, 300).map(e =>
    `<li><span class="${e.known ? "" : "new"}">${esc(e.name)}</span>${e.meta_id ? ` <span class="b">Meta-ID</span>` : ""}${e.steam_appid ? ` <span class="b${e.steam_sure === false ? " warn" : ""}">Steam ${esc(e.steam_appid)}${e.steam_sure === false ? " ≈" : ""}</span>` : ""}${e.price != null ? ` ${eur(e.price)}` : ""}${e.known ? " · schon vorhanden" : ""}</li>`).join("")}</ul></div>`;
}
/* ---------------------------------------------------------------- Bearbeiten */
function openEdit(key){
  const r = S.library.concat(S.wishlist).find(x => x.key === key);
  if(!r) return;
  const cb = r.crossbuy === true ? "yes" : r.crossbuy === false ? "no" : "";
  $("edit").innerHTML = `<form method="dialog" data-form="edit" data-k="${esc(key)}"><h2>${esc(r.name)}</h2>
    <div class="form">
      <label for="f-name">Name</label><input type="text" id="f-name" name="name" value="${esc(r.name)}" required>
      <label for="f-meta">Meta-ID</label><input type="text" id="f-meta" name="meta_id" value="${esc(r.meta_id)}" inputmode="numeric" placeholder="Zahl aus dem Store-Link">
      <label for="f-steam">Steam-App-ID</label><input type="text" id="f-steam" name="steam_appid" value="${esc(r.steam_appid)}" inputmode="numeric">
      <label for="f-cb">Crossbuy</label><select id="f-cb" name="crossbuy"><option value="">unbekannt</option><option value="yes" ${cb === "yes" ? "selected" : ""}>ja</option><option value="no" ${cb === "no" ? "selected" : ""}>nein</option></select>
      <span class="full"><label><input type="checkbox" name="wish" ${r.wish ? "checked" : ""}> auf der Wunschliste</label>
        <label><input type="checkbox" name="owned_meta" ${r.where === "meta" || r.where === "beide" ? "checked" : ""}> besitze ich bei Meta</label>
        <label><input type="checkbox" name="owned_pc" ${r.where === "pc" || r.where === "beide" ? "checked" : ""}> besitze ich am PC</label></span>
      <label class="full" for="f-note">Notiz, etwa Meinungen von Reddit mit Link</label>
      <textarea class="full" id="f-note" name="note">${esc(r.note)}</textarea>
    </div>
    <p class="hint">Trägt ein anderer Titel dieselbe ID, werden beide zusammengeführt.</p>
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
  V.tab = "settings"; delete V.folds["c-imp-meta"];
  try{
    const res = await api("/api/import", {kind: "meta", text: META_IN, dry: false});
    S = res.state || S;
    V.prev.meta = {done: true, n: res.n, new: res.new, entries: res.entries};
    toast(res.n ? `${res.n} Meta-Käufe gelesen, ${res.new} neu` : "Keine Käufe erkannt. Bitte die Seite neu laden und noch einmal versuchen");
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
  else if(a === "qclear"){ V.q = ""; render(); $("q")?.focus(); }
  else if(a === "foldall"){ $("main").querySelectorAll("details[data-kc]").forEach(d => { d.open = !!v; keepFold(d); }); saveView(); }
  else if(a === "jump"){
    ev.preventDefault();
    const c = $(v), d = c?.querySelector("details");
    if(d) d.open = true;
    c?.scrollIntoView({block: "start"});
  }
  else if(a === "edit") openEdit(el.dataset.k);
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
    try{ V.diag = (await api("/api/diag", {})).lines; }
    catch(e){ V.diag = ["Test fehlgeschlagen: " + e.message]; }
    V.diagRunning = false; render();
  }
  else if(a === "copy") copyNow(v === "diag" ? (V.diag || []).join("\n") : logText());
  else if(a === "showlog"){
    V.tab = "settings"; delete V.folds["c-logcard"]; render();
    $("logcard")?.scrollIntoView({block: "start"});
  }
  else if(a === "merge"){ const res = await act("/api/merge", {keep: el.dataset.a, gone: el.dataset.b}); if(res) toast("Zusammengeführt", undoTo(res)); }
  else if(a === "notsame") act("/api/not_same", {a: el.dataset.a, b: el.dataset.b});
  else if(a === "preview" || a === "apply"){
    const text = $("txt-" + v).value;
    V.txt = Object.assign(V.txt || {}, {[v]: text});
    el.disabled = true;
    try{
      const res = await api("/api/import", {kind: v, text, dry: a === "preview"});
      V.prev[v] = a === "apply" ? {done: true, n: res.n, new: res.new} : res;
      if(res.state) S = res.state;
      if(a === "apply") V.txt[v] = "";
    }catch(e){ V.prev[v] = {error: e.message}; }
    render("imp-" + v);
  }
});

document.addEventListener("input", ev => {
  if(ev.target.dataset.in === "q"){ V.q = ev.target.value; V.focusQ = true; render(); V.focusQ = false; }
});

document.addEventListener("change", async ev => {
  const kind = ev.target.dataset.file;
  if(!kind || !ev.target.files[0]) return;
  const f = ev.target.files[0];
  if(f.size > 45e6){ alert("Datei zu groß"); return; }
  const text = await f.text();
  if(kind === "restore"){
    let obj;
    try{ obj = JSON.parse(text); }catch(e){ alert("Keine gültige Sicherung"); return; }
    if(confirm(`Sicherung einspielen? Sie ersetzt alle ${S.counts.all} Titel.`)) act("/api/restore", {data: obj.data || obj});
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
  if(kind === "edit"){
    ev.preventDefault();
    const cb = f.crossbuy.value;
    const ok = await act("/api/title", {key: f.dataset.k, name: f.name.value, meta_id: f.meta_id.value, steam_appid: f.steam_appid.value,
      crossbuy: cb === "yes" ? true : cb === "no" ? false : null, wish: f.wish.checked,
      owned_meta: f.owned_meta.checked, owned_pc: f.owned_pc.checked, note: f.note.value}, $("f-err"));
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
});
addEventListener("resize", navFade);
$("nav").addEventListener("scroll", navFade);

renderTheme();
load().then(() => { if(META_IN !== null && S) metaHandOver(); });
