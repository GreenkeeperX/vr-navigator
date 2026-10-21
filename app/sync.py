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
eine Quelle mit 403 oder 429, endet sie für diesen Lauf.
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
QSDB_HEAD = {"Cookie": "currency=EUR"}     # Preise und Verlauf in Euro
STEAM = "https://store.steampowered.com"
GG_API = "https://api.gg.deals/v1/prices/by-steam-app-id/"

SETTINGS = {"gg_key": "", "auto": True, "hours": 6}

sleep = time.sleep          # Tests setzen hier eine Attrappe ein
_running = threading.Lock()


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
    st = store.load_json("sync.json", {})
    st["running"] = _running.locked()
    return st


def due(settings=None, at=None):
    """Ist ein Lauf nach Zeitplan fällig?"""
    s = settings or load_settings()
    if not s["auto"]:
        return False
    last = store.load_json("sync.json", {}).get("started") or ""
    if not last:
        return True
    try:
        return (at or now()) - datetime.fromisoformat(last) >= timedelta(hours=s["hours"])
    except ValueError:
        return True


class _Source:
    """Eine Quelle in einem Lauf: Pausen, Fehlerzähler, Ende bei Sperre."""

    def __init__(self, name, log, headers=None):
        self.name, self.log, self.headers = name, log, headers
        self.n = self.errors = 0
        self.stopped = ""

    def get(self, url, shown=None):
        if self.stopped:
            return None
        if self.n:
            sleep(PAUSE)
        self.n += 1
        try:
            return sources.fetch(url, headers=self.headers)
        except sources.FetchError as e:
            where = shown or url
            if e.status in sources.BLOCKED:
                self.stopped = f"gesperrt ({e.status})"
                self.log(f"{self.name}: {e.status} bei {where}, Quelle für diesen Lauf beendet")
            else:
                self.errors += 1
                self.log(f"{self.name}: Fehler {e.status or ''} bei {where}".replace("  ", " "))
                if self.errors >= MAX_ERRORS:
                    self.stopped = f"{self.errors} Fehler"
                    self.log(f"{self.name}: zu viele Fehler, Quelle für diesen Lauf beendet")
            return None

    def result(self):
        return {"at": titles.now_iso(), "requests": self.n, "errors": self.errors,
                "ok": not self.stopped, "msg": self.stopped}


def _targets(data):
    """Wunschtitel, die du noch nirgends besitzt."""
    return {k: t for k, t in data["titles"].items() if t.get("wish") and not t.get("owned")}


def _missed(t, field):
    """Suche nach diesem Titel schlug vor weniger als MISS_DAYS fehl."""
    return (t.get(field) or "") > (now() - timedelta(days=MISS_DAYS)).isoformat(timespec="seconds")


def _pick(cards, t):
    """Den passenden Treffer einer Suche: gleiche Meta-ID, sonst genau ein gleicher Name."""
    if t.get("meta_id"):
        hit = [c for c in cards if c["meta_id"] == t["meta_id"]]
        if hit:
            return hit[0]
    same = [c for c in cards if titles.norm(c["name"]) == titles.norm(t["name"])]
    return same[0] if len(same) == 1 else None


def _qsdb(targets, upd, log):
    src = _Source("QuestStoreDB", log, QSDB_HEAD)
    stamp = titles.now_iso()
    # 1. Angebotsliste
    sale, pages, page = {}, 1, 1
    while page <= min(pages, MAX_SALE_PAGES):
        text = src.get(f"{prices.QSDB}/on_sale/?sort=-sale_start_time&page={page}")
        if text is None:
            break
        if page == 1:
            pages = prices.qsdb_pages(text)
        for c in prices.qsdb_cards(text):
            sale.setdefault(c["meta_id"], c)
        page += 1
    for k, t in targets.items():
        c = sale.get(t.get("meta_id") or "")
        if c and c["price"] is not None:
            u = upd.setdefault(k, {})
            u["meta"] = {"price": c["price"], "base": c["base"], "discount": c["discount"],
                         "until": c["until"], "kind": c["kind"], "at": stamp}
    # 2. Titelseiten, die älteste zuerst
    old = (now() - timedelta(hours=PAGE_AGE_H)).isoformat(timespec="seconds")
    todo = sorted((((t.get("live") or {}).get("meta") or {}).get("page_at") or "", k)
                  for k, t in targets.items())
    searches = pages_done = 0
    for page_at, k in todo:
        if page_at > old or pages_done >= MAX_PAGES or src.stopped:
            continue
        t = targets[k]
        path = ((t.get("live") or {}).get("meta") or {}).get("path") or ""
        link = (t.get("links") or {}).get("qsdb") or ""
        if not path and link.startswith(prices.QSDB + "/"):
            path = link[len(prices.QSDB):]
        if not path:
            if searches >= MAX_SEARCH or _missed(t, "meta_miss"):
                continue
            searches += 1
            q = urllib.parse.urlencode({"release_status": "all", "q": t["name"]})
            text = src.get(f"{prices.QSDB}/all_apps/?{q}")
            hit = _pick(prices.qsdb_cards(text), t) if text else None
            if not hit:
                if text is not None:
                    upd.setdefault(k, {})["meta_miss"] = stamp
                continue
            path = hit["path"]
        text = src.get(prices.QSDB + path)
        pages_done += 1
        g = prices.qsdb_game(text) if text else None
        if not g:
            continue
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
    log(f"QuestStoreDB: {len(sale)} Angebote, {pages_done} Titelseiten, {searches} Suchen")
    return src.result()


def _steam(targets, upd, log):
    src = _Source("Steam", log)
    stamp = titles.now_iso()
    ids = {}
    searches = 0
    for k, t in targets.items():
        if t.get("steam_appid"):
            ids[k] = t["steam_appid"]
            continue
        if searches >= MAX_SEARCH or src.stopped or _missed(t, "steam_miss"):
            continue
        searches += 1
        q = urllib.parse.urlencode({"term": t["name"], "l": "german", "cc": "DE"})
        text = src.get(f"{STEAM}/api/storesearch/?{q}")
        same = [i for i in prices.steam_search(text or "") if titles.norm(i["name"]) == titles.norm(t["name"])]
        if len(same) == 1:
            ids[k] = same[0]["appid"]
            upd.setdefault(k, {})["steam_appid"] = same[0]["appid"]
        elif text is not None:
            upd.setdefault(k, {})["steam_miss"] = stamp
    keys = list(ids)
    found = 0
    for i in range(0, len(keys), 50):
        chunk = keys[i:i + 50]
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
    log(f"Steam: {found} Preise, {searches} Suchen")
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
    found = 0
    for i in range(0, len(apps), 100):
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
            for k in ids.get(a, []):
                found += 1
                upd.setdefault(k, {})["gg"] = dict(p, at=stamp)
    log(f"gg.deals: {found} Preise")
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
                    if src == "meta":
                        prev = live.get("meta") or {}
                        for f in ("low", "low_at", "rating", "ratings", "version", "path", "page_at"):
                            if v.get(f) is None and prev.get(f) is not None:
                                v[f] = prev[f]
                        if v.get("price") is not None and (v.get("low") is None or v["price"] < v["low"]):
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


def run(only=None):
    """Ein Lauf. only: Menge der Quellen (qsdb, steam, gg), sonst alle. Läuft schon einer,
    kommt False zurück."""
    if not _running.acquire(blocking=False):
        return False
    try:
        st = {"started": now().isoformat(timespec="seconds"), "log": [], "sources": status().get("sources") or {}}

        def log(msg):
            st["log"].append(f"{datetime.now().strftime('%H:%M:%S')} {msg}")
            print(msg, flush=True)

        settings = load_settings()
        targets = _targets(store.load_data())
        log(f"Abgleich für {len(targets)} Wunschtitel")
        upd = {}
        steps = [("qsdb", _qsdb), ("steam", _steam)]
        if settings["gg_key"]:
            steps.append(("gg", lambda t, u, lg: _gg(t, u, settings["gg_key"], lg)))
        for name, step in steps:
            if only and name not in only:
                continue
            try:
                st["sources"][name] = step(targets, upd, log)
            except Exception as e:          # ein Fehler im Lesen soll die anderen Quellen nicht aufhalten
                log(f"{name}: unerwarteter Fehler ({type(e).__name__})")
                print(f"Fehler beim Abgleich {name}:", e, file=sys.stderr)
                st["sources"][name] = {"at": titles.now_iso(), "ok": False, "msg": type(e).__name__}
        apply(upd)
        st["done"] = now().isoformat(timespec="seconds")
        log(f"fertig, {len(upd)} Titel aktualisiert")
        store.save_json("sync.json", st)
        return True
    finally:
        _running.release()


def start(only=None):
    """Lauf im Hintergrund starten. False, wenn schon einer läuft."""
    if _running.locked():
        return False
    threading.Thread(target=run, args=(only,), daemon=True).start()
    return True


def scheduler():
    """Prüft jede Minute, ob ein Lauf nach Zeitplan fällig ist. Erster Blick zwei Minuten nach
    dem Start, damit ein Neustart des Containers nicht sofort abruft."""
    time.sleep(120)
    while True:
        try:
            if due() and not _running.locked():
                run()
        except Exception as e:
            print("Zeitplan:", e, file=sys.stderr)
        time.sleep(60)


TESTS = {
    "qsdb": f"{prices.QSDB}/on_sale/?sort=-sale_start_time",
    "steam": f"{STEAM}/api/appdetails?appids=10&cc=de&filters=price_overview",
}


def test(source):
    """Verbindung prüfen: ein Abruf, Ergebnis als Text."""
    if source == "gg":
        key = load_settings()["gg_key"]
        if not key:
            return {"ok": False, "msg": "Kein Schlüssel eingetragen"}
        url = f"{GG_API}?ids=10&region=de&key={urllib.parse.quote(key)}"
    elif source in TESTS:
        url = TESTS[source]
    else:
        raise ValueError("unbekannte Quelle")
    r = sources.request(url, headers=QSDB_HEAD if source == "qsdb" else None)
    if r["error"]:
        return {"ok": False, "msg": r["error"].replace(key, "…") if source == "gg" else r["error"]}
    if r["status"] >= 400:
        return {"ok": False, "msg": f"HTTP {r['status']}" + (" (gesperrt oder Prüfseite)" if r["status"] in sources.BLOCKED else "")}
    if source == "qsdb":
        n = len(prices.qsdb_cards(r["text"]))
        return {"ok": n > 0, "msg": f"{n} Angebote auf Seite 1" if n else "Seite geladen, aber keine Angebote erkannt"}
    if source == "steam":
        n = len(prices.steam_prices(r["text"]))
        return {"ok": n > 0, "msg": "Preis gelesen" if n else "Antwort nicht erkannt"}
    try:
        prices.gg_prices(r["text"])
        return {"ok": True, "msg": "Schlüssel angenommen"}
    except ValueError as e:
        return {"ok": False, "msg": str(e)}
