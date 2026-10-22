"""Abgleich: holt Preise für die Wunschtitel von QuestStoreDB, Steam und gg.deals.

Ablauf eines Laufs (Einzelheiten in docs/abrufe.md):
1. QuestStoreDB, Angebotsliste: alle Seiten, neueste Angebote zuerst.
2. QuestStoreDB, Titelseiten der Wunschtitel, die älter als PAGE_AGE_H sind (höchstens
   MAX_PAGES je Lauf). Fehlt der Pfad, sucht das Tool den Titel erst über die Suche.
3. Steam: fehlende App-IDs über die Store-Suche (nur bei gleichem Namen), dann die Preise in
   Paketen zu 50.
4. gg.deals, nur mit Schlüssel: Preise in Paketen zu 100.

Die Abrufe laufen ohne Sperre auf data.json; erst das Ergebnis wird unter der Sperre in die
aktuelle Fassung eingetragen. Zwischen zwei Abrufen derselben Quelle liegt PAUSE. Antwortet
eine Quelle mit 403 oder 429 oder einer Prüfseite, endet sie für diesen Lauf und ruht danach
REST_H Stunden, auch über Läufe hinweg. Nach einem kurzen Netzfehler gibt es einen zweiten
Versuch.

Das Protokoll entsteht live (STATE), die Oberfläche liest es während des Laufs; am Ende landet
es mit dem Ergebnis je Quelle und der Selbstprüfung in sync.json.
"""
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

from . import prices, sources, store, titles

PAUSE = 2.0
PAGE_AGE_H = 20
MAX_SALE_PAGES = 15
MAX_PAGES = 60
MAX_SEARCH = 30
MAX_ERRORS = 5
MISS_DAYS = 7               # nicht gefundene Titel erst nach so vielen Tagen erneut suchen
SEARCH_V = 2                # Stand der Suche; ändert sie sich, gelten alte Fehlschläge nicht mehr
REST_H = 24                 # Ruhezeit einer Quelle nach Sperre oder Prüfseite
NET_RETRY = 5.0             # Pause vor dem zweiten Versuch nach einem Netzfehler
BOOT_GAP_MIN = 30           # Lauf nach dem Start nur, wenn der letzte länger her ist
LOG_LINES = 200
JUMP = 0.5                  # Selbstprüfung: Normalpreis ändert sich um mehr als 50 %
NAMES = {"qsdb": "QuestStoreDB", "steam": "Steam", "gg": "gg.deals"}
SHOPS = {"meta": "Meta", "steam": "Steam", "gg": "gg.deals Händler"}
QSDB_HEAD = {"Cookie": "currency=EUR"}     # Preise und Verlauf in Euro
STEAM = "https://store.steampowered.com"
GG_API = "https://api.gg.deals/v1/prices/by-steam-app-id/"

SETTINGS = {"gg_key": "", "auto": True, "hours": 6}

sleep = time.sleep          # Tests setzen hier eine Attrappe ein
_old_misses = {"ignore": False}     # Fehlschläge einer früheren Suche (SEARCH_V) zählen nicht
_running = threading.Lock()
# Stand des laufenden Abgleichs, live für die Oberfläche
STATE = {"started": "", "step": "", "done": 0, "total": 0, "log": []}


def now():
    return datetime.now(timezone.utc)


def load_settings():
    s = dict(SETTINGS)
    s.update({k: v for k, v in store.load_json("settings.json", {}).items() if k in SETTINGS})
    return s


def save_settings(body):
    s = load_settings()
    if "gg_key" in body:
        s["gg_key"] = str(body["gg_key"] or "").strip()[:100]
    if "auto" in body:
        s["auto"] = bool(body["auto"])
    if "hours" in body:
        try:
            s["hours"] = min(48, max(2, int(body["hours"])))
        except (TypeError, ValueError):
            raise ValueError("Abstand in Stunden: eine Zahl von 2 bis 48")
    store.save_json("settings.json", s)
    return s


def status():
    """Letzter Lauf aus sync.json; läuft gerade einer, mit Schritt und Protokoll live."""
    st = store.load_json("sync.json", {})
    st["running"] = _running.locked()
    if st["running"]:
        st.update(started=STATE["started"], step=STATE["step"], done=STATE["done"],
                  total=STATE["total"], log=list(STATE["log"]))
    return st


def _iso(at):
    return at.isoformat(timespec="seconds")


def _ago(iso, at):
    try:
        return at - datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def due(settings=None, at=None, boot=False):
    """Ist ein Lauf nach Zeitplan fällig? boot: erster Blick nach dem Start des Containers;
    dann gleich ein Lauf (etwa mit neuen Lesern nach einem Update), außer der letzte liegt
    weniger als BOOT_GAP_MIN zurück. Nach einem Fehlschlag wartet auch der Start so lange."""
    s = settings or load_settings()
    if not s["auto"]:
        return False
    last = store.load_json("sync.json", {})
    at = at or now()
    since = _ago(last.get("started"), at)
    if since is None:
        return True
    gap = timedelta(minutes=BOOT_GAP_MIN)
    if last.get("ok") is False and since < gap:
        return False
    return since >= (gap if boot else timedelta(hours=s["hours"]))


def progress(step, done=0, total=0):
    STATE.update(step=step, done=done, total=total)


class _Source:
    """Eine Quelle in einem Lauf: Pausen, Fehlerzähler, zweiter Versuch nach Netzfehler, Ende
    bei Sperre oder Prüfseite (blocked: die Quelle ruht danach)."""

    def __init__(self, name, log, headers=None):
        self.name, self.log, self.headers = name, log, headers
        self.n = self.errors = 0
        self.stopped = ""
        self.blocked = False
        self.stats = {}

    def _stop(self, why, where):
        self.stopped, self.blocked = why, True
        self.log(f"{self.name}: {why} bei {where}, Quelle ruht {REST_H} Stunden")

    def get(self, url, shown=None):
        if self.stopped:
            return None
        if self.n:
            sleep(PAUSE)
        self.n += 1
        where = shown or url
        for attempt in (1, 2):
            try:
                text = sources.fetch(url, headers=self.headers)
                break
            except sources.FetchError as e:
                if e.status == 0 and attempt == 1:
                    self.log(f"{self.name}: keine Verbindung bei {where}, zweiter Versuch")
                    sleep(NET_RETRY)
                    continue
                if e.status in sources.BLOCKED:
                    self._stop(f"gesperrt (HTTP {e.status})", where)
                else:
                    self.errors += 1
                    self.log(f"{self.name}: {'HTTP ' + str(e.status) if e.status else 'keine Verbindung'} bei {where}")
                    if self.errors >= MAX_ERRORS:
                        self.stopped = f"{self.errors} Fehler"
                        self.log(f"{self.name}: zu viele Fehler, Quelle für diesen Lauf beendet")
                return None
        why = sources.challenge(text)
        if why:
            self._stop(why, where)
            return None
        return text

    def result(self):
        return {"at": titles.now_iso(), "requests": self.n, "errors": self.errors,
                "ok": not self.stopped, "msg": self.stopped, "blocked": self.blocked, **self.stats}


def _targets(data):
    """Wunschtitel, die du noch nirgends besitzt."""
    return {k: t for k, t in data["titles"].items() if t.get("wish") and not t.get("owned")}


def _missed(t, field):
    """Suche nach diesem Titel schlug vor weniger als MISS_DAYS fehl."""
    if _old_misses["ignore"]:
        return False
    return (t.get(field) or "") > (now() - timedelta(days=MISS_DAYS)).isoformat(timespec="seconds")


def _retry_day(items, field):
    """Tag, an dem die erste der übersprungenen Suchen wieder fällig ist."""
    first = min((t.get(field) or "" for t in items), default="")
    try:
        return (datetime.fromisoformat(first) + timedelta(days=MISS_DAYS)).strftime("%d.%m.")
    except ValueError:
        return "?"


def _few(names, n=12):
    """Namen fürs Protokoll, höchstens n."""
    names = list(names)
    return ", ".join(names[:n]) + (f" und {len(names) - n} weitere" if len(names) > n else "")


def _took(start):
    s = int(time.monotonic() - start)
    return f"{s // 60}:{s % 60:02d} min"


def _pick(cards, t):
    """Den passenden Treffer einer Suche: gleiche Meta-ID, sonst genau einer, dessen Name zu
    einem der Namen aus titles.store_names passt."""
    if t.get("meta_id"):
        hit = [c for c in cards if c["meta_id"] == t["meta_id"]]
        if hit:
            return hit[0]
    names = {titles.norm(x) for x in titles.store_names(t)}
    same = [c for c in cards if titles.norm(c["name"]) in names]
    return same[0] if len(same) == 1 else None


def _search(src, t, url, pick, budget):
    """Sucht den Titel unter jedem Namen aus titles.store_names, bis einer passt. Liefert
    (Treffer, Zahl der Suchen, ohne Treffer). ohne Treffer ist False, wenn eine Anfrage scheiterte
    oder das Budget nicht für alle Namen reichte; dann gilt die Suche nicht als fehlgeschlagen."""
    n = 0
    for name in titles.store_names(t):
        if n >= budget or src.stopped:
            return None, n, False
        n += 1
        text = src.get(url(name))
        if text is None:
            return None, n, False
        hit = pick(text)
        if hit:
            return hit, n, False
    return None, n, True


def _qsdb(targets, upd, log):
    src = _Source("QuestStoreDB", log, QSDB_HEAD)
    stamp = titles.now_iso()
    start = time.monotonic()
    # 1. Angebotsliste
    sale, pages, page = {}, 1, 1
    while page <= min(pages, MAX_SALE_PAGES):
        progress("QuestStoreDB: Angebotsliste", page, min(pages, MAX_SALE_PAGES))
        text = src.get(f"{prices.QSDB}/on_sale/?sort=-sale_start_time&page={page}")
        if text is None:
            break
        if page == 1:
            pages = prices.qsdb_pages(text)
        for c in prices.qsdb_cards(text):
            sale.setdefault(c["meta_id"], c)
        page += 1
    wished = []
    for k, t in targets.items():
        c = sale.get(t.get("meta_id") or "")
        if c and c["price"] is not None:
            wished.append(t["name"])
            u = upd.setdefault(k, {})
            u["meta"] = {"price": c["price"], "base": c["base"], "discount": c["discount"],
                         "until": c["until"], "kind": c["kind"], "at": stamp}
    # 2. Titelseiten, die älteste zuerst
    old = (now() - timedelta(hours=PAGE_AGE_H)).isoformat(timespec="seconds")
    todo = sorted((((t.get("live") or {}).get("meta") or {}).get("page_at") or "", k)
                  for k, t in targets.items())
    searches = pages_done = parsed = 0
    fresh, later, found, missed, waiting, unread = 0, 0, [], [], [], []
    due_n = min(MAX_PAGES, sum(p <= old for p, _ in todo))
    for page_at, k in todo:
        if page_at > old:
            fresh += 1
            continue
        if pages_done >= MAX_PAGES or src.stopped:
            later += 1
            continue
        progress("QuestStoreDB: Titelseiten", pages_done, due_n)
        t = targets[k]
        path = ((t.get("live") or {}).get("meta") or {}).get("path") or ""
        link = (t.get("links") or {}).get("qsdb") or ""
        if not path and link.startswith(prices.QSDB + "/"):
            path = link[len(prices.QSDB):]
        if not path:
            if _missed(t, "meta_miss"):
                waiting.append(t)
                continue
            if searches >= MAX_SEARCH:
                later += 1
                continue

            def url(name):
                return f"{prices.QSDB}/all_apps/?" + urllib.parse.urlencode({"release_status": "all", "q": name})
            hit, n, miss = _search(src, t, url, lambda text: _pick(prices.qsdb_cards(text), t), MAX_SEARCH - searches)
            searches += n
            if not hit:
                if miss:
                    upd.setdefault(k, {})["meta_miss"] = stamp
                    missed.append(t["name"])
                continue
            found.append(t["name"])
            path = hit["path"]
        text = src.get(prices.QSDB + path)
        pages_done += 1
        g = prices.qsdb_game(text) if text else None
        if not g:
            if text is not None:
                unread.append(path)
            continue
        parsed += 1
        u = upd.setdefault(k, {})
        today = now().strftime("%Y-%m-%d")
        on_sale = g["price"] is not None and g["base"] and g["price"] < g["base"]
        u["meta"] = {"price": g["price"], "base": g["base"],
                     "discount": round((1 - g["price"] / g["base"]) * 100) if on_sale else 0,
                     "until": g["until"] if on_sale and g["until"] >= today else "",
                     "kind": (u.get("meta") or {}).get("kind") or ("discount" if on_sale else "base"),
                     "low": g["low"], "low_at": g["low_at"], "rating": g["rating"],
                     "ratings": g["ratings"], "version": g["version"], "path": g["path"] or path,
                     "at": stamp, "page_at": stamp}
        if g["meta_id"]:
            u["meta_id"] = g["meta_id"]
        u["qsdb"] = prices.QSDB + (g["path"] or path)
    log(f"QuestStoreDB, Angebotsliste: {len(sale)} Angebote auf {page - 1} Seiten"
        + (f", von deiner Wunschliste ({len(wished)}): {_few(wished)}" if wished else ", keines von deiner Wunschliste"))
    log(f"QuestStoreDB, Titelseiten: {pages_done} gelesen ({parsed} lesbar), {fresh} aktuell (jünger als {PAGE_AGE_H} h)"
        + (f", {later} folgen beim nächsten Abgleich" if later else ""))
    if unread:
        log(f"QuestStoreDB, Titelseiten ohne lesbaren Preis ({len(unread)}): {_few(unread, 6)}")
    if searches or waiting:
        log(f"QuestStoreDB, Suche: {searches} Anfragen, {len(found)} Titel gefunden"
            + (f", ohne Treffer ({len(missed)}): {_few(missed)}" if missed else "")
            + (f"; {len(waiting)} ohne Treffer in den letzten {MISS_DAYS} Tagen, nächste Suche ab {_retry_day(waiting, 'meta_miss')}"
               if waiting else ""))
    log(f"QuestStoreDB: fertig nach {_took(start)}, {src.n} Anfragen" + (f", {src.errors} Fehler" if src.errors else ""))
    src.stats = {"sale": len(sale), "pages": pages_done, "parsed": parsed, "searches": searches}
    return src.result()


def _steam(targets, upd, log):
    src = _Source("Steam", log)
    stamp = titles.now_iso()
    start = time.monotonic()
    ids = {}
    searches, later, hits, missed, waiting = 0, 0, [], [], []
    for k, t in targets.items():
        if t.get("steam_appid"):
            ids[k] = t["steam_appid"]
            continue
        if _missed(t, "steam_miss"):
            waiting.append(t)
            continue
        if searches >= MAX_SEARCH or src.stopped:
            later += 1
            continue
        progress("Steam: Suche", searches, 0)
        names = {titles.norm(x) for x in titles.store_names(t)}

        def pick(text):
            same = [i for i in prices.steam_search(text) if titles.norm(i["name"]) in names]
            return same[0] if len(same) == 1 else None
        hit, n, miss = _search(src, t, lambda name: f"{STEAM}/api/storesearch/?"
                               + urllib.parse.urlencode({"term": name, "l": "german", "cc": "DE"}),
                               pick, MAX_SEARCH - searches)
        searches += n
        if hit:
            ids[k] = hit["appid"]
            upd.setdefault(k, {})["steam_appid"] = hit["appid"]
            hits.append(t["name"])
        elif miss:
            upd.setdefault(k, {})["steam_miss"] = stamp
            missed.append(t["name"])
    if searches or waiting or later:
        # Viele Quest-Titel gibt es auf Steam nicht; ohne Treffer ist hier der Normalfall
        log(f"Steam, Suche: {searches} Anfragen, {len(hits)} App-IDs gefunden"
            + (f" ({_few(hits)})" if hits else "")
            + (f", ohne Treffer {len(missed)}" if missed else "")
            + (f"; {len(waiting)} ohne Treffer in den letzten {MISS_DAYS} Tagen, nächste Suche ab {_retry_day(waiting, 'steam_miss')}"
               if waiting else "")
            + (f"; {later} folgen beim nächsten Abgleich" if later else ""))
    keys = list(ids)
    found, sale, none = 0, [], []
    for i in range(0, len(keys), 50):
        chunk = keys[i:i + 50]
        progress("Steam: Preise", i // 50 + 1, (len(keys) + 49) // 50)
        q = ",".join(dict.fromkeys(ids[k] for k in chunk))
        text = src.get(f"{STEAM}/api/appdetails?appids={q}&cc=de&filters=price_overview")
        if text is None:
            continue
        got = prices.steam_prices(text)
        for k in chunk:
            p = got.get(ids[k])
            if p:
                found += 1
                upd.setdefault(k, {})["steam"] = dict(p, at=stamp)
                if p.get("discount"):
                    sale.append(targets[k]["name"])
            else:
                none.append(targets[k]["name"])
    log(f"Steam, Preise: {found} Preise für {len(keys)} App-IDs"
        + (f", im Angebot ({len(sale)}): {_few(sale)}" if sale else ", keiner im Angebot")
        + (f"; ohne Preis im deutschen Store ({len(none)}): {_few(none, 6)}" if none else ""))
    log(f"Steam: fertig nach {_took(start)}, {src.n} Anfragen" + (f", {src.errors} Fehler" if src.errors else ""))
    src.stats = {"ids": len(keys), "found": found, "searches": searches}
    return src.result()


def _gg(targets, upd, key, log):
    src = _Source("gg.deals", log)
    stamp = titles.now_iso()
    ids = {}
    for k, t in targets.items():
        a = (upd.get(k) or {}).get("steam_appid") or t.get("steam_appid")
        if a:
            ids.setdefault(a, []).append(k)
    apps = list(ids)
    found, retail, keyshop, seen = 0, 0, 0, set()
    for i in range(0, len(apps), 100):
        progress("gg.deals: Preise", i // 100 + 1, (len(apps) + 99) // 100)
        q = urllib.parse.urlencode({"ids": ",".join(apps[i:i + 100]), "region": "de"})
        # Der Schlüssel steht nur in der Anfrage, nie im Protokoll
        text = src.get(f"{GG_API}?{q}&key={urllib.parse.quote(key)}", shown=f"{GG_API}?{q}")
        if text is None:
            continue
        try:
            got = prices.gg_prices(text)
        except ValueError as e:
            log(str(e))
            src.stopped = "abgelehnt"
            break
        for a, p in got.items():
            seen.add(a)
            retail += p["retail"] is not None
            keyshop += p["keyshops"] is not None
            for k in ids.get(a, []):
                found += 1
                upd.setdefault(k, {})["gg"] = dict(p, at=stamp)
    log(f"gg.deals: {found} Preise für {len(apps)} App-IDs, {retail} mit Händlerpreis, {keyshop} mit Keyshop-Preis"
        + (f", {len(apps) - len(seen)} ohne Eintrag bei gg.deals" if len(seen) < len(apps) else ""))
    src.stats = {"ids": len(apps), "found": found}
    return src.result()


def _history(hist, src, ident, price, day):
    if not ident or price is None:
        return
    rows = hist.setdefault(src, {}).setdefault(str(ident), [])
    if not rows or rows[-1][1] != price:
        rows.append([day, price])


def apply(upd):
    """Ergebnis eines Laufs in die aktuelle data.json eintragen und den Verlauf fortschreiben.
    Titel, die es inzwischen nicht mehr gibt, fallen weg."""
    day = now().strftime("%Y-%m-%d")
    jumps = 0
    moves = {"down": [], "up": [], "low": []}     # fürs Protokoll: günstiger, teurer, neuer Tiefstpreis
    with store.lock:
        data = store.load_data()
        hist = store.load_json("history.json", {})
        for k, u in upd.items():
            t = data["titles"].get(k)
            if not t:
                continue
            live = t.setdefault("live", {})
            for src in ("meta", "steam", "gg"):
                if src in u:
                    v = dict(u[src])
                    old = (live.get(src) or {}).get("base")
                    if old and v.get("base") is not None and abs(v["base"] - old) > JUMP * old:
                        jumps += 1
                    was = (live.get(src) or {}).get("price" if src != "gg" else "retail")
                    new = v.get("price" if src != "gg" else "retail")
                    if was is not None and new is not None and new != was:
                        moves["down" if new < was else "up"].append(f"{t['name']} ({SHOPS[src]} {_eur(was)} → {_eur(new)})")
                    if src == "meta":
                        prev = live.get("meta") or {}
                        for f in ("low", "low_at", "rating", "ratings", "version", "path", "page_at"):
                            if v.get(f) is None and prev.get(f) is not None:
                                v[f] = prev[f]
                        if v.get("price") is not None and (v.get("low") is None or v["price"] < v["low"]):
                            if prev.get("low") is not None:
                                moves["low"].append(f"{t['name']} {_eur(v['price'])}")
                            v["low"], v["low_at"] = v["price"], day
                    live[src] = v
            links = t.setdefault("links", {})
            if u.get("qsdb"):
                links["qsdb"] = u["qsdb"]
            if (u.get("gg") or {}).get("url", "").startswith("https://gg.deals/"):
                links["gg"] = u["gg"]["url"]
            for f in ("meta_miss", "steam_miss"):
                if u.get(f):
                    t[f] = u[f]
            ids = {}
            if u.get("meta_id") and not t.get("meta_id"):
                ids["meta_id"] = u["meta_id"]
            if u.get("steam_appid") and not t.get("steam_appid"):
                ids["steam_appid"] = u["steam_appid"]
            if ids:
                titles.set_ids(data, k, **ids)
            _history(hist, "meta", t.get("meta_id"), (live.get("meta") or {}).get("price"), day)
            _history(hist, "steam", t.get("steam_appid"), (live.get("steam") or {}).get("price"), day)
            g = live.get("gg") or {}
            best = min([x for x in (g.get("retail"), g.get("keyshops")) if x is not None], default=None)
            _history(hist, "gg", t.get("steam_appid"), best, day)
        store.save_data(data)
        store.save_json("history.json", hist)
    return {"jumps": jumps, "moves": moves, "coverage": _coverage(data)}


def _eur(v):
    return f"{v:.2f} €".replace(".", ",")


def _coverage(data):
    """Stand der Wunschliste nach dem Lauf: je Quelle, wie viele Titel einen Preis haben, und
    welche gar keinen."""
    tg = list(_targets(data).values())
    has = {s: sum(1 for t in tg if ((t.get("live") or {}).get(s) or {})) for s in ("meta", "steam", "gg")}
    bare = [t["name"] for t in tg if not any((t.get("live") or {}).get(s) for s in ("meta", "steam", "gg"))]
    return {"n": len(tg), "has": has, "bare": bare}


def self_check(results, prev, applied):
    """Ergebnisse glaubhaft? Meldet, statt still weiterzurechnen: leere Listen, wo sonst etwas
    stand, Seiten ohne lesbaren Preis, Normalpreise mit großen Sprüngen."""
    w = []
    q, pq = results.get("qsdb") or {}, prev.get("qsdb") or {}
    if q.get("ok") and q.get("sale") == 0 and (pq.get("sale") or 0) > 0:
        w.append(f"QuestStoreDB: keine Angebote erkannt (zuletzt {pq['sale']}), hat sich die Seite geändert?")
    if q.get("pages") and not q.get("parsed"):
        w.append(f"QuestStoreDB: auf {q['pages']} Titelseiten kein Preis lesbar")
    for k in ("steam", "gg"):
        r = results.get(k) or {}
        if r.get("ok") and r.get("ids") and not r.get("found"):
            w.append(f"{NAMES[k]}: kein Preis für {r['ids']} App-IDs")
    if applied.get("jumps"):
        w.append(f"{applied['jumps']} Normalpreise änderten sich um mehr als {round(JUMP * 100)} %")
    return w


def run(only=None, boot=False, by_hand=False):
    """Ein Lauf. only: Menge der Quellen (qsdb, steam, gg), sonst alle. Läuft schon einer,
    kommt False zurück."""
    if not _running.acquire(blocking=False):
        return False
    try:
        prev = store.load_json("sync.json", {})
        st = {"started": _iso(now()), "log": [], "sources": dict(prev.get("sources") or {}),
              "rest": {k: v for k, v in (prev.get("rest") or {}).items() if v > _iso(now())}}
        STATE.update(started=st["started"], step="Start", done=0, total=0, log=st["log"])

        def log(msg):
            # Zeit in UTC, die Oberfläche zeigt sie in der Zeit des Browsers
            st["log"].append(f"{now().strftime('%H:%M:%S')} {msg}")
            del st["log"][:-LOG_LINES]
            print(msg, flush=True)

        begun = time.monotonic()
        settings = load_settings()
        targets = _targets(store.load_data())
        log(f"VR-Navigator {sources.VERSION}, Abgleich für {len(targets)} Wunschtitel, "
            + ("von Hand" if by_hand else "nach dem Start" if boot else "nach Zeitplan")
            + (", nur " + ", ".join(NAMES[x] for x in NAMES if x in only) if only else ""))
        _old_misses["ignore"] = prev.get("search_v") != SEARCH_V
        if _old_misses["ignore"] and prev:
            log("Suche geändert: Titel ohne Treffer werden diesmal neu gesucht")
        upd, results = {}, {}
        steps = [("qsdb", _qsdb), ("steam", _steam)]
        if settings["gg_key"]:
            steps.append(("gg", lambda t, u, lg: _gg(t, u, settings["gg_key"], lg)))
        else:
            log("gg.deals: kein Schlüssel eingetragen, nicht abgefragt")
        for name, step in steps:
            if only and name not in only:
                continue
            if st["rest"].get(name):
                until = datetime.fromisoformat(st["rest"][name])
                log(f"{NAMES[name]}: ruht nach einer Sperre bis {until.strftime('%d.%m. %H:%M')} UTC, nicht abgefragt")
                results[name] = {"at": titles.now_iso(), "ok": False, "msg": "ruht", "until": st["rest"][name],
                                 "requests": 0, "errors": 0}
                continue
            progress(NAMES[name])
            try:
                results[name] = step(targets, upd, log)
            except Exception as e:          # ein Fehler im Lesen soll die anderen Quellen nicht aufhalten
                log(f"{NAMES[name]}: unerwarteter Fehler ({type(e).__name__}), Einzelheiten im Protokoll des Containers")
                print(f"Fehler beim Abgleich {name}:", e, file=sys.stderr)
                results[name] = {"at": titles.now_iso(), "ok": False, "msg": type(e).__name__}
            if results[name].get("blocked"):
                st["rest"][name] = _iso(now() + timedelta(hours=REST_H))
                results[name]["until"] = st["rest"][name]
        progress("Speichern")
        applied = apply(upd)
        st["sources"].update(results)
        st["warnings"] = self_check(results, prev.get("sources") or {}, applied)
        mv = applied["moves"]
        if any(mv.values()):
            log("Preise: " + "; ".join(x for x in (
                f"günstiger ({len(mv['down'])}): {_few(mv['down'], 8)}" if mv["down"] else "",
                f"teurer ({len(mv['up'])}): {_few(mv['up'], 8)}" if mv["up"] else "",
                f"neuer Meta-Tiefstpreis ({len(mv['low'])}): {_few(mv['low'], 8)}" if mv["low"] else "") if x))
        else:
            log("Preise: keine Änderung seit dem letzten Abgleich")
        cov = applied["coverage"]
        log(f"Stand: {cov['n']} Wunschtitel, mit Preis bei Meta {cov['has']['meta']}, Steam {cov['has']['steam']}, "
            f"gg.deals {cov['has']['gg']}" + (f"; ohne jeden Preis ({len(cov['bare'])}): {_few(cov['bare'])}" if cov["bare"] else ""))
        for w in st["warnings"]:
            log("Selbstprüfung: " + w)
        if not st["warnings"]:
            log("Selbstprüfung: alles glaubhaft")
        st["ok"] = all(r.get("ok") for r in results.values())
        st["finished"] = st["done"] = _iso(now())
        if not _old_misses["ignore"] or not only:
            st["search_v"] = SEARCH_V
        log(f"fertig nach {_took(begun)}, {len(upd)} Titel aktualisiert" + ("" if st["ok"] else ", mit Fehlern"))
        store.save_json("sync.json", st)
        return True
    finally:
        STATE.update(step="", done=0, total=0)
        _running.release()


def start(only=None):
    """Lauf im Hintergrund starten. False, wenn schon einer läuft."""
    if _running.locked():
        return False
    threading.Thread(target=run, args=(only,), kwargs={"by_hand": True}, daemon=True).start()
    return True


def scheduler():
    """Prüft jede Minute, ob ein Lauf nach Zeitplan fällig ist. Erster Blick zwei Minuten nach
    dem Start: dann ein Lauf, wenn der letzte über BOOT_GAP_MIN zurückliegt (siehe due)."""
    time.sleep(120)
    boot = True
    while True:
        try:
            if due(boot=boot) and not _running.locked():
                run(boot=boot)
        except Exception as e:
            print("Zeitplan:", e, file=sys.stderr)
        boot = False
        time.sleep(60)


def diagnose():
    """Verbindung testen: jede Quelle einmal abfragen und beschreiben, was zurückkommt (Status,
    Server, Kodierung, was die Leser erkennen). Nimmt, wo es geht, einen Titel deiner
    Wunschliste. Speichert nichts; der gg.deals-Schlüssel erscheint nie im Ergebnis."""
    data = store.load_data()
    key = load_settings()["gg_key"]
    targets = list(_targets(data).values())
    lines = [f"VR-Navigator {sources.VERSION}, Test vom {now().strftime('%d.%m.%Y %H:%M')} UTC"]
    hosts = set()

    def probe(name, url, info, headers=None, shown=None):
        host = urllib.parse.urlsplit(url).hostname
        if host in hosts:
            sleep(PAUSE)
        hosts.add(host)
        r = sources.request(url, headers=headers)
        if r["error"]:
            lines.append(f"{name}: keine Verbindung ({r['error']})")
            return None
        head = f"{name}: HTTP {r['status']}, Server {r['server'] or '?'}, Kodierung {r['enc'] or 'keine'}, {len(r['text'])} Zeichen"
        why = sources.challenge(r["text"])
        if why or r["status"] >= 400:
            lines.append(head + (f", {why}" if why else "") + (", gesperrt" if r["status"] in sources.BLOCKED else "")
                         + f". Anfang: {' '.join(r['text'][:160].split())}")
            return None
        try:
            lines.append(f"{head}, {info(r['text'])}")
        except Exception as e:     # ein Lesefehler soll nicht den ganzen Test abbrechen
            lines.append(f"{head}, nicht auswertbar ({type(e).__name__}: {e})")
        return r["text"]

    def sale_info(text):
        cards = prices.qsdb_cards(text)
        return f"{len(cards)} Angebote erkannt, {prices.qsdb_pages(text)} Seiten" + (
            f", erstes: {cards[0]['name']} {cards[0]['price']} € statt {cards[0]['base']} €" if cards else "")
    sale = probe("QuestStoreDB, Angebotsliste", f"{prices.QSDB}/on_sale/?sort=-sale_start_time", sale_info, QSDB_HEAD)

    t = next((t for t in targets if t.get("meta_id") or (t.get("links") or {}).get("qsdb")), targets[0] if targets else None)
    name = t["name"] if t else "vr"
    hit = {}

    def search_info(text):
        cards = prices.qsdb_cards(text)
        h = _pick(cards, t) if t else (cards[0] if cards else None)
        if h:
            hit.update(h)
        return f"{len(cards)} Treffer für „{name}“" + (f", passend: {h['name']} (Meta-ID {h['meta_id']})" if h else ", keiner passt eindeutig")
    q = urllib.parse.urlencode({"release_status": "all", "q": name})
    probe("QuestStoreDB, Suche", f"{prices.QSDB}/all_apps/?{q}", search_info, QSDB_HEAD)

    path = ((t or {}).get("live") or {}).get("meta", {}).get("path") or hit.get("path") or ""
    link = ((t or {}).get("links") or {}).get("qsdb") or ""
    if not path and link.startswith(prices.QSDB + "/"):
        path = link[len(prices.QSDB):]
    if not path and sale:
        path = next((c["path"] for c in prices.qsdb_cards(sale)), "")

    def game_info(text):
        g = prices.qsdb_game(text)
        if not g:
            return "kein Preis lesbar (strukturierte Daten fehlen)"
        return (f"„{g['name']}“, Preis {g['price']} €, Normalpreis {g['base']} €"
                + (f" bis {g['until']}" if g["until"] and g["price"] != g["base"] else "")
                + (f", Tief {g['low']} € am {g['low_at']}" if g["low"] is not None else ", ohne Preisverlauf")
                + (f", Version {g['version']}" if g["version"] else ""))
    if path:
        probe("QuestStoreDB, Titelseite", prices.QSDB + path, game_info, QSDB_HEAD)
    else:
        lines.append("QuestStoreDB, Titelseite: kein Pfad bekannt, nicht angefragt")

    st = next((t for t in targets if t.get("steam_appid")), None)
    appid = st["steam_appid"] if st else "10"

    def steam_info(text):
        p = prices.steam_prices(text).get(appid)
        return (f"App {appid}: {p['price']} € statt {p['base']} €, −{p['discount']} %" if p and p["discount"]
                else f"App {appid}: {p['price']} €" if p and p["price"] else f"App {appid}: kostenlos oder ohne Preis" if p else f"App {appid}: kein Preis im deutschen Store")
    probe("Steam, Preise", f"{STEAM}/api/appdetails?appids={appid}&cc=de&filters=price_overview", steam_info)
    sname = (st or t or {}).get("name") or "vr"
    probe("Steam, Suche", f"{STEAM}/api/storesearch/?" + urllib.parse.urlencode({"term": sname, "l": "german", "cc": "DE"}),
          lambda text: f"{len(prices.steam_search(text))} Treffer für „{sname}“")

    if not key:
        lines.append("gg.deals: kein Schlüssel eingetragen, nicht angefragt")
    else:
        def gg_info(text):
            try:
                got = prices.gg_prices(text)
            except ValueError as e:
                return f"{e}. Anfang: {' '.join(text[:200].split())}"
            p = got.get(appid)
            if not p:
                return f"Schlüssel angenommen, für App {appid} kein Eintrag. Anfang: {' '.join(text[:200].split())}"

            def eur(v):
                return "keins" if v is None else f"{v} €"
            return (f"Schlüssel angenommen, App {appid}: Händler {eur(p['retail'])} (Tief {eur(p['retail_low'])}), "
                    f"Keyshops {eur(p['keyshops'])} (Tief {eur(p['keyshops_low'])})")
        q = urllib.parse.urlencode({"ids": appid, "region": "de"})
        probe("gg.deals, Preise", f"{GG_API}?{q}&key={urllib.parse.quote(key)}", gg_info, shown=f"{GG_API}?{q}")
    if key:
        lines = [x.replace(key, "…").replace(urllib.parse.quote(key), "…") for x in lines]
    return lines
