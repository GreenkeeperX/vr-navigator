"use strict";
/* VR-Navigator, Oberfläche ohne Build. Reiter: Wunschliste, Bibliothek, Import.
   Alle fremden Texte (Titel, Notizen, Links) laufen durch esc() bzw. safeUrl(). */

const $ = id => document.getElementById(id);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const safeUrl = u => /^https?:\/\//i.test(String(u || "")) ? String(u) : "";
const eur = v => v == null ? "–" : v.toLocaleString("de-DE", {minimumFractionDigits: v % 1 ? 2 : 0, maximumFractionDigits: 2}) + " €";
const day = iso => iso ? new Date(iso).toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit", year: "numeric"}) : "";

let S = null;                                   // Zustand vom Server
const V = {tab: "wish", q: "", where: "all", sort: "name", prev: {}};
try{ V.tab = localStorage.getItem("vn.tab") || V.tab; }catch(e){}

async function api(path, body){
  const opt = body === undefined ? {} : {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)};
  const r = await fetch(path, opt);
  const j = await r.json().catch(() => ({}));
  if(!r.ok) throw new Error(j.error || `Fehler ${r.status}`);
  return j;
}

/* ---------------------------------------------------------------- Ansicht hell/dunkel */
const THEMES = [["system", "Auto", "wie das Gerät"], ["light", "Hell", "hell"], ["dark", "Dunkel", "dunkel"]];
function themeNow(){ const t = document.documentElement.dataset.theme; return t === "light" || t === "dark" ? t : "system"; }
function renderTheme(){ const t = THEMES.find(x => x[0] === themeNow()); $("thmBtn").textContent = t[1]; $("thmBtn").title = "Ansicht: " + t[2] + ". Klick wechselt."; }
function nextTheme(){
  const i = THEMES.findIndex(x => x[0] === themeNow()), k = THEMES[(i + 1) % THEMES.length][0];
  if(k === "system") delete document.documentElement.dataset.theme; else document.documentElement.dataset.theme = k;
  try{ if(k === "system") localStorage.removeItem("vn.theme"); else localStorage.setItem("vn.theme", k); }catch(e){}
  renderTheme();
}

/* ---------------------------------------------------------------- Rahmen */
function renderNav(){
  const c = S.counts, sug = S.suggestions.length;
  const tabs = [["wish", "Wunschliste", c.wish], ["lib", "Bibliothek", c.owned], ["import", "Import", sug ? `${sug} prüfen` : ""]];
  $("nav").innerHTML = tabs.map(([k, l, n]) =>
    `<button data-act="tab" data-v="${k}" class="${V.tab === k ? "on" : ""}">${l}${n !== "" ? `<span class="cnt">${esc(n)}</span>` : ""}</button>`).join("");
  $("meta").textContent = `${c.all} Titel · Meta ${c.meta} · PC ${c.pc} · auf beiden ${c.both} · Version ${S.version}`;
}

function render(){
  renderNav();
  try{ localStorage.setItem("vn.tab", V.tab); }catch(e){}
  $("main").innerHTML = V.tab === "lib" ? libView() : V.tab === "import" ? importView() : wishView();
  const q = $("q");
  if(q && document.activeElement !== q && V.focusQ){ q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
}

function badges(r){
  const out = [];
  if(r.where === "meta" || r.where === "beide") out.push(`<span class="b meta" title="Im Meta Store gekauft">Meta</span>`);
  if(r.where === "pc" || r.where === "beide") out.push(`<span class="b pc" title="In Playnite (PC)">${esc(r.pc_label || "PC")}</span>`);
  if(r.crossbuy === true) out.push(`<span class="b go" title="Meta-Kauf gilt auch für die PC-Fassung (Rift)">Crossbuy</span>`);
  if(r.crossbuy === false) out.push(`<span class="b" title="Meta-Kauf gilt nur auf der Quest">kein Crossbuy</span>`);
  if(r.steam_appid && !r.steam_sure) out.push(`<span class="b warn" title="Steam-ID aus Playnite geraten, bitte prüfen">Steam-ID ≈</span>`);
  return out.join(" ");
}
const linksHtml = r => `<span class="links">${r.links.filter(l => safeUrl(l.url)).map(l =>
  `<a href="${esc(l.url)}" target="_blank" rel="noopener noreferrer">${esc(l.label)}</a>`).join("")}</span>`;

function match(r){
  const q = V.q.trim().toLowerCase();
  if(q && !r.name.toLowerCase().includes(q) && !r.note.toLowerCase().includes(q)) return false;
  if(V.tab === "lib" && V.where !== "all"){
    if(V.where === "beide") return r.where === "beide";
    return r.where === V.where;
  }
  return true;
}

function searchBar(extra){
  return `<div class="bar"><input type="search" id="q" placeholder="Titel oder Notiz suchen" value="${esc(V.q)}" data-in="q">${extra || ""}</div>`;
}

/* ---------------------------------------------------------------- Wunschliste */
function wishView(){
  const sorts = [["name", "Name"], ["gap", "Abstand"], ["low", "Meta-Tief"]];
  let rows = S.wishlist.filter(match);
  const k = {gap: r => r.gap ?? 1e9, low: r => r.sheet?.meta_low ?? 1e9}[V.sort];
  if(k) rows = rows.slice().sort((a, b) => k(a) - k(b));
  const add = `<form class="bar" data-form="add"><input type="text" name="name" placeholder="Neuer Titel" required>
    <input type="text" name="link" placeholder="Link zu VRDB, QuestStoreDB, Meta oder Steam (optional)">
    <button class="primary">Hinzufügen</button></form>`;
  const head = searchBar(`<span class="chips">${sorts.map(([v, l]) => `<button data-act="sort" data-v="${v}" class="${V.sort === v ? "on" : ""}">${l}</button>`).join("")}</span>`);
  if(!S.wishlist.length) return add + `<p class="hint">Noch keine Wunschtitel. Importiere deine Vergleichstabelle unter Import oder trage oben einen Titel ein.</p>`;
  return add + head + `<p class="hint">Preise stammen vorerst aus deiner Tabelle (Stand jeweils dabei). Live-Preise von QuestStoreDB, Steam und gg.deals folgen in Version 0.2.
    Abstand = Meta-Tief minus gg.deals-Bestpreis: <span class="gap-steam">+ Steam günstiger</span>, <span class="gap-meta">− Meta günstiger</span>.</p>
    <div class="list">${rows.map(wishRow).join("") || `<p class="hint">Kein Treffer.</p>`}</div>`;
}

function wishRow(r){
  const s = r.sheet;
  const prices = s ? `<span>Meta <span class="price">${eur(s.meta)}</span></span>
      <span>Meta-Tief <span class="price">${eur(s.meta_low)}</span></span>
      <span>gg.deals <span class="price">${eur(s.gg)}</span></span>
      ${r.gap != null ? `<span>Abstand <span class="price ${r.gap > 0 ? "gap-steam" : r.gap < 0 ? "gap-meta" : ""}">${r.gap > 0 ? "+" : ""}${eur(r.gap)}</span></span>` : ""}
      <span title="Aus deiner Tabelle übernommen">Tabelle, ${day(s.at)}</span>` : `<span>keine Preise</span>`;
  return `<div class="item"><span class="nm">${esc(r.name)}</span>${badges(r)}
    <button class="link" data-act="edit" data-k="${esc(r.key)}">bearbeiten</button>
    <div class="row2">${prices}</div>
    <div class="row2">${linksHtml(r)}</div>
    ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}</div>`;
}

/* ---------------------------------------------------------------- Bibliothek */
function libView(){
  const ws = [["all", "Alle"], ["meta", "Nur Meta"], ["pc", "Nur PC"], ["beide", "Beide"]];
  const rows = S.library.filter(match);
  if(!S.library.length) return `<p class="hint">Noch nichts im Besitz. Importiere unter Import deine Meta-Bestellungen und den Playnite-Export.</p>`;
  return searchBar(`<span class="chips">${ws.map(([v, l]) => `<button data-act="where" data-v="${v}" class="${V.where === v ? "on" : ""}">${l}</button>`).join("")}</span>`) +
    `<div class="list">${rows.map(r => `<div class="item"><span class="nm">${esc(r.name)}</span>${badges(r)}
      ${r.wish ? `<span class="b" title="Steht auch auf der Wunschliste">Wunsch</span>` : ""}
      <button class="link" data-act="edit" data-k="${esc(r.key)}">bearbeiten</button>
      <div class="row2">${linksHtml(r)}</div>
      ${r.note ? `<div class="note">${esc(r.note)}</div>` : ""}</div>`).join("") || `<p class="hint">Kein Treffer.</p>`}</div>`;
}

/* ---------------------------------------------------------------- Import */
// Lesezeichen für die Meta-Bestellseite: sammelt Links und Seitentext und lädt sie als Datei
// herunter. Es schickt nichts an einen Server; die Datei lädst du hier selbst hoch.
const BOOKMARKLET = "javascript:(()=>{const L=[...document.querySelectorAll('a[href]')].map(a=>({href:a.href,text:(a.innerText||a.textContent||'').trim().slice(0,200)}));" +
  "const d={kind:'meta-bestellungen',at:new Date().toISOString(),links:L,text:document.body.innerText.slice(0,2000000)};" +
  "const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(d)],{type:'application/json'}));" +
  "a.download='meta-bestellungen.json';document.body.appendChild(a);a.click();a.remove();})()";

const IMPORTS = {
  sheet: {title: "Vergleichstabelle (CSV)", what: "Deine Tabelle mit Spiel, meta, Bestpreis, gg.deals best, Crossbuy und Links. Die Titel landen auf der Wunschliste, sofern du sie nicht schon besitzt.", accept: ".csv,text/csv"},
  playnite: {title: "Playnite-Export (CSV)", what: "Bibliothek aus Playnite. Übernommen werden Spiele mit VR-Schlagwort und alle, die schon in deiner Liste stehen. Sie gelten als Besitz am PC.", accept: ".csv,text/csv"},
  meta: {title: "Meta-Bestellungen", what: "", accept: ".json,.txt,application/json,text/plain"},
};
function importCard(kind){
  const c = IMPORTS[kind], last = S.imports[kind], p = V.prev[kind];
  const metaHow = kind === "meta" ? `<ol>
      <li>Ziehe diesen Knopf in deine Lesezeichenleiste: <a class="bm" href="${esc(BOOKMARKLET)}" data-act="nobm">Meta-Bestellungen sichern</a></li>
      <li>Öffne angemeldet <a href="https://www.meta.com/my/orders/?order_type=digital_products&amp;timeFilter=ALL_TIME" target="_blank" rel="noopener noreferrer">deine Meta-Bestellungen</a> und scrolle bis ganz nach unten, damit alle geladen sind.</li>
      <li>Klicke das Lesezeichen. Es lädt die Datei <code>meta-bestellungen.json</code> herunter und schickt nichts weg.</li>
      <li>Wähle die Datei hier aus. Alternativ: Seite markieren, kopieren und unten einfügen.</li></ol>` : `<p class="hint">${c.what}</p>`;
  return `<div class="card"><h2>${c.title}</h2>${metaHow}
    ${last ? `<p class="hint">Zuletzt: ${day(last.at)}, ${last.n} erkannt, ${last.new} neu.</p>` : ""}
    <div class="bar"><input type="file" accept="${c.accept}" data-file="${kind}"></div>
    <textarea id="txt-${kind}" placeholder="… oder Inhalt hier einfügen">${esc(V.txt?.[kind] || "")}</textarea>
    <div class="bar"><button data-act="preview" data-v="${kind}">Vorschau</button>
      ${p && !p.error ? `<button class="primary" data-act="apply" data-v="${kind}">${p.n} übernehmen</button>` : ""}</div>
    ${p ? previewHtml(p) : ""}</div>`;
}
function previewHtml(p){
  if(p.error) return `<p class="err">${esc(p.error)}</p>`;
  if(p.done) return `<p class="ok">Übernommen: ${p.n} erkannt, ${p.new} neu angelegt.</p>`;
  return `<div class="prev">${p.n} erkannt, davon ${p.new} neu. Noch nichts gespeichert.<ul>${p.entries.slice(0, 300).map(e =>
    `<li><span class="${e.known ? "" : "new"}">${esc(e.name)}</span>${e.meta_id ? ` <span class="b meta">Meta-ID</span>` : ""}${e.steam_appid ? ` <span class="b ${e.steam_sure === false ? "warn" : "pc"}">Steam ${esc(e.steam_appid)}${e.steam_sure === false ? " ≈" : ""}</span>` : ""}${e.price != null ? ` ${eur(e.price)}` : ""}${e.known ? " · schon vorhanden" : ""}</li>`).join("")}</ul></div>`;
}
function importView(){
  const sug = S.suggestions.length ? `<div class="card"><h2>Derselbe Titel?</h2>
    <p class="hint">Diese Paare heißen fast gleich, einer stammt aus Meta, der andere vom PC. Zusammenführen heißt: ein Eintrag mit beiden Seiten.</p>
    <div class="list">${S.suggestions.map(s => `<div class="item"><span class="nm">${esc(s.a_name)} ↔ ${esc(s.b_name)}</span>
      <button data-act="merge" data-a="${esc(s.a)}" data-b="${esc(s.b)}">Zusammenführen</button>
      <button data-act="notsame" data-a="${esc(s.a)}" data-b="${esc(s.b)}">Verschieden</button></div>`).join("")}</div></div>` : "";
  return sug + importCard("sheet") + importCard("meta") + importCard("playnite") +
    `<div class="card"><h2>Sicherung</h2><p class="hint">Alle Titel, Notizen und Zuordnungen als eine Datei.</p>
     <div class="bar"><a href="/api/export" download>Sicherung herunterladen</a>
     <label>Sicherung einspielen <input type="file" accept=".json,application/json" data-file="restore"></label></div></div>`;
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
async function load(){
  try{ S = await api("/api/state"); render(); }
  catch(e){ $("main").innerHTML = `<p class="err">Server nicht erreichbar: ${esc(e.message)}</p>`; }
}
async function act(path, body, errEl){
  try{ S = await api(path, body); render(); return true; }
  catch(e){ if(errEl) errEl.textContent = e.message; else alert(e.message); return false; }
}

document.addEventListener("click", async ev => {
  const el = ev.target.closest("[data-act]");
  if(!el) return;
  const a = el.dataset.act, v = el.dataset.v;
  if(a === "nobm"){ ev.preventDefault(); alert("Bitte in die Lesezeichenleiste ziehen und auf der Meta-Bestellseite anklicken."); return; }
  if(a === "thm") nextTheme();
  else if(a === "tab"){ V.tab = v; V.q = ""; render(); }
  else if(a === "sort"){ V.sort = v; render(); }
  else if(a === "where"){ V.where = v; render(); }
  else if(a === "edit") openEdit(el.dataset.k);
  else if(a === "close") $("edit").close();
  else if(a === "del"){
    if(confirm("Titel samt Notiz löschen?") && await act("/api/title/delete", {key: el.dataset.k})) $("edit").close();
  }
  else if(a === "merge") act("/api/merge", {keep: el.dataset.a, gone: el.dataset.b});
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
    render();
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
  render();
});

document.addEventListener("submit", async ev => {
  const f = ev.target, kind = f.dataset.form;
  if(kind === "add"){
    ev.preventDefault();
    if(await act("/api/title/new", {name: f.name.value, link: f.link.value})) f.reset();
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

renderTheme();
load();
