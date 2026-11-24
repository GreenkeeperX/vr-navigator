"""Kleiner Webserver: liefert die Oberfläche und eine JSON-Schnittstelle."""
import copy
import datetime
import gzip
import hashlib
import ipaddress
import json
import os
import re
import sys
import threading
import time
import traceback
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import aufgaben, besitz, collection, eingaben, flat2vr, imports, library, lists, muster, pcwish, retro, sicherung, sources, store, sync, titles, verlauf, wheel

STATIC = os.path.join(os.path.dirname(__file__), "static")

# Namen, die nur im eigenen Netz aufgelöst werden (RFC 8375 und üblich): Eine fremde Domain kann
# nicht auf sie zeigen, deshalb gelten sie ohne Eintrag
LOCAL_SUFFIXES = (".home.arpa", ".local", ".lan", ".internal", ".localhost")


def host_allowed(host, extra=None):
    """Schutz gegen DNS-Rebinding: Eine fremde Webseite, deren Domain plötzlich auf den Server
    im Heimnetz zeigt, wäre für den Browser dieselbe Seite und könnte die Daten lesen.
    Angenommen werden nur IP-Adressen, localhost, Namen ohne Punkt, Namen im eigenen Netz
    (LOCAL_SUFFIXES) und, was in ALLOWED_HOSTS steht (mit Komma getrennt; „.beispiel.de“ gilt für
    alle Namen darunter)."""
    if not host:
        return True                    # ohne Host-Kopf: kein Browser
    name = host.strip().lower()
    if name.startswith("["):
        name = name[1:].split("]")[0]  # IPv6 mit Port
    elif name.count(":") == 1:
        name = name.split(":")[0]
    try:
        ipaddress.ip_address(name)
        return True
    except ValueError:
        pass
    name = name.rstrip(".")
    if "." not in name or name.endswith(LOCAL_SUFFIXES):
        return True
    extra = os.environ.get("ALLOWED_HOSTS", "") if extra is None else extra
    for e in (x.strip().lower().rstrip(".") for x in extra.split(",")):
        if e and (name == e or (e.startswith(".") and name.endswith(e))):
            return True
    return False


DIAG = {"id": 0, "running": False, "lines": None, "error": ""}
_diag_lock = threading.Lock()


def start_diag():
    """Verbindungstest im Hintergrund (0.8.0): er dauert bis zu einer Minute, länger als ein Proxy davor
    oft wartet (504). Die Oberfläche fragt den Stand mit GET /api/diag ab."""
    with _diag_lock:
        if DIAG["running"]:
            return False
        DIAG.update(id=DIAG["id"] + 1, running=True, lines=None, error="")

    def run():
        try:
            lines, error = sync.diagnose(), ""
        except Exception as e:
            traceback.print_exc()
            lines, error = None, f"{type(e).__name__}"
        with _diag_lock:
            DIAG.update(running=False, lines=lines, error=error)
    threading.Thread(target=run, daemon=True).start()
    return True


def diag_view():
    with _diag_lock:
        return dict(DIAG)


def settings_view():
    """Einstellungen für die Oberfläche: der Schlüssel selbst geht nie zurück an den Browser."""
    s = sync.load_settings()
    secret = {k: s.pop(k) for k in sync.SECRETS}
    key = secret["gg_key"]
    return dict(s, gg_key_end=key[-4:] if len(key) > 12 else "",
                **{flag: all(secret[k] for k in keys) for flag, keys in sync.SECRET_FLAGS.items()})


def import_collection(data, text, dry):
    """Der Playnite-Export füllt neben der Bibliothek (VR-Titel) auch die ganze Sammlung für
    Entdecken, je System. Die Zusammenfassung steht unter imports.collection in data.json."""
    stats = {}
    games = collection.parse(text, stats=stats)
    col = store.load_json(collection.FILE, collection.EMPTY)
    console, systems, ps = stats.get("console", 0), stats.get("systems", {}), stats.get("ps", 0)
    if not games:
        return {"n": 0, "new": 0, "console": console, "systems": systems, "kept": len(col.get("games") or {}), "ps": ps}
    old = col.get("games") or {}
    kept = sum(1 for k, g in old.items() if ((g.get("system") or "PC") not in systems or g.get("src") == retro.SRC)
               and k not in games)
    if dry:
        return {"n": len(games), "new": sum(k not in old for k in games), "console": console, "systems": systems, "kept": kept, "ps": ps}
    new = collection.replace(col, games)
    collection.sync_pcvr(col, data)          # 0.8.9: kennt Playnite einen VR-Titel jetzt, fällt sein Eintrag weg
    collection.sync_steam(col, data)         # 0.9.7: ebenso Spiele aus dem Steam-Konto
    collection.sync_gg(col, data)            # 0.9.9: und aus der gg.deals-Sammlung
    store.save_json(collection.FILE, col)
    data["imports"]["collection"] = {"at": col["at"], "n": len(col["games"]), "new": new}
    return {"n": len(games), "new": new, "console": console, "systems": systems, "kept": kept, "ps": ps}


def import_retro(data, text, dry, lists=()):
    """Retro-Liste in die Sammlung (collection.json). Die Vorschau nennt je System die Zahl,
    was neu ist, was in der Liste fehlt, und was übersprungen oder nicht erkannt wurde. lists (0.8.8): deine
    Ordner-Listen aus der Ordnerwahl als [(Pfad, Text)]."""
    games, st = retro.parse(text)
    if not games:
        raise ValueError("In der Liste ist kein Spiel zu erkennen. Erwartet sind Dateinamen mit Ordnern, etwa "
                         "„SNES/Pixel Kart (Europe).sfc“, oder eine CSV mit den Spalten System und Titel.")
    col = store.load_json(collection.FILE, collection.EMPTY)
    old = col.get("games") or {}
    own = retro.apply_folder_lists(games, lists) if lists else None
    new, gone = retro.apply(col, games, dry=dry, own_systems=own["systems"] if own else ())
    if not dry:
        store.save_json(collection.FILE, col)
        data["imports"]["retro"] = {"at": col["at"], "n": len(games), "new": new, "files": st["files"], "gone": len(gone)}
    rows = sorted(games.items(), key=lambda kv: (collection.system_order(kv[1]["system"]), titles.norm(kv[1]["name"])))
    return {"kind": "retro", "what": imports.KINDS["retro"], "n": len(games), "new": new, "files": st["files"],
            "systems": dict(sorted(st["systems"].items(), key=lambda kv: collection.system_order(kv[0]))),
            "skipped": {"save": st["save"], "extra": st["extra"], "archive": st["archive"]},
            "unknown_n": st["unknown"], "unknown": retro.unknown_lines(text) if st["unknown"] else [],
            "gone": gone[:200], "gone_n": len(gone),
            "own": dict(own, extra=own["extra"][:100], missing=own["missing"][:100], extra_n=len(own["extra"]),
                        missing_n=len(own["missing"])) if own else None,
            "size": sum(g.get("size") or 0 for g in games.values()),
            "entries": [{"name": g["name"], "system": g["system"], "known": k in old, "langs": g["langs"],
                         "lang_guess": g["lang_guess"], "files": g["files"]} for k, g in rows[:300]]}


def _lists(body):
    """Ordner-Listen aus dem Import: höchstens 60, je 5 MB, nur Dateien „…_ordner.csv“."""
    out = []
    for x in (body.get("lists") or [])[:60] if isinstance(body.get("lists"), list) else []:
        if isinstance(x, dict) and retro.is_folder_list(x.get("path")):
            out.append((str(x["path"])[:500], str(x.get("text") or "")[:5_000_000]))
    return out


# Antworten aus großen Dateien bleiben zwischengespeichert, bis sich eine der Dateien ändert (0.8.14):
# collection.json allein zu lesen dauert auf einem kleinen Server schon eine Weile
_memo = {}
_memo_lock = threading.Lock()
_memo_busy = {}          # je Schlüssel ein Riegel (0.10.15): wer gleichzeitig fragt, wartet auf dieselbe Rechnung


def memo(key, files, make, extra=None):
    """extra: was außer den Dateien zählt (etwa die Uhrzeit, gerundet)."""
    with _memo_lock:
        busy = _memo_busy.setdefault(key, threading.Lock())
    with busy:
        st = (store.DATA_DIR, store.stamp(*files), extra)
        with _memo_lock:
            hit = _memo.get(key)
        if hit and hit[0] == st:
            return hit[1]
        val = make()
        with _memo_lock:
            _memo[key] = (st, val)
        return val


def _retro_lists():
    col = store.load_json(collection.FILE, collection.EMPTY)
    return retro.near_list(col), retro.own_list(col), retro.de_list(col)


def price_stats(data=None, pw=None, hist=None):
    """Preismuster aus dem eigenen Verlauf (0.10.0), zwischengespeichert bis sich eine der Dateien oder der Tag ändert."""
    def make():
        return muster.stats(data if data is not None else store.load_data(),
                            (pw if pw is not None else store.load_json(pcwish.FILE, pcwish.EMPTY)).get("items") or {},
                            hist if hist is not None else store.load_json("history.json", {}))
    return memo("muster:" + datetime.date.today().isoformat(), ("data.json", pcwish.FILE, "history.json"), make)


# Was der Zustand liest (0.10.15): ändert sich keine dieser Dateien, kommt er aus dem Zwischenspeicher
STATE_FILES = ("data.json", collection.FILE, eingaben.FILE, pcwish.FILE, "history.json", "settings.json", wheel.LIST_FILE, flat2vr.PORTS_FILE, flat2vr.UEVR_FILE)


def _state_core():
    data = store.load_data()
    near, own, de = memo("retro", (collection.FILE, eingaben.FILE), _retro_lists)
    games = collection_view().get("games") or []
    hist, pw = store.load_json("history.json", {}), store.load_json(pcwish.FILE, pcwish.EMPTY)
    view, pcv = library.view(data, hist=hist, settings=sync.load_settings()), pcwish.view(data)
    st = price_stats(data, pw, hist)
    muster.annotate(view, pcv, data, pw.get("items") or {}, st, hist)
    return dict(view, muster=st, own_check=besitz.check(data),
                marks=data["marks"], version=sources.VERSION, pcwish=pcv,
                pcwish_ids=pcwish.id_todo(pw),
                retro_near=near, retro_own=own, retro_de=de, mp_label=collection.MP_LABEL, opinion_task=imports.opinion_task(data), opinion_batch=imports.OPINION_BATCH,
                todo_tasks=aufgaben.tasks(data, near, own, pcwish.id_todo(pw), games=games), todo_batch=aufgaben.BATCH,
                # 0.10.26: Recherche zur Sammlung: Lenkrad (die Spiele) und VR-Mods (nur die Zahl, es sind Tausende)
                research={"wheel": [{"key": x["id"], "name": x["name"], "tags": x["schlagwoerter"]} for x in aufgaben.items("wheel", data, games=games)],
                          "vrmod_n": len(aufgaben.items("vrmod", data, games=games)), "vrmod_batch": aufgaben.BATCHES["vrmod"]})


def state():
    """Zustand für die Oberfläche. Der große Teil bleibt zwischengespeichert, bis sich eine Datei ändert, höchstens
    zehn Minuten (Preise gelten nach 48 Stunden als veraltet, Meta-Angebote enden); Abgleich und Einstellungen frisch."""
    core = memo("state", STATE_FILES, _state_core, extra=datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M")[:-1])
    return dict(core, sync=sync.status(), settings=settings_view())


# Was die Sammlung liest; ab 0.11.0 mit den Nutzereingaben (eine Entscheidung ändert nur eingaben.json)
COL_FILES = (collection.FILE, eingaben.FILE, "data.json", wheel.LIST_FILE, flat2vr.PORTS_FILE, flat2vr.UEVR_FILE)


def collection_view():
    """Die Sammlung wie in der Oberfläche, zwischengespeichert, bis sich eine der Dateien ändert."""
    return memo("colview", COL_FILES,
                lambda: collection.view(store.load_json(collection.FILE, collection.EMPTY), store.load_data()))


# Nur in den Einzelheiten gebraucht (0.11.1): fehlt in /api/collection, kommt beim Aufklappen über /api/details.
# Die Beschreibung ist rund ein Drittel der Antwort; hd sagt der Oberfläche, dass es eine gibt
DETAIL_FIELDS = ("desc",)


def slim(r):
    """Zeile der Sammlung ohne die Felder der Einzelheiten."""
    out = {k: v for k, v in r.items() if k not in DETAIL_FIELDS}
    if r.get("desc"):
        out["hd"] = 1
    return out


def slim_view(v):
    return dict(v, games=[slim(r) for r in v["games"]], detail=list(DETAIL_FIELDS))


def etag_of(raw):
    return '"' + hashlib.sha1(raw).hexdigest()[:20] + '"'


def collection_body():
    """Die Sammlung als fertige Antwort: roh, gepackt und ihr ETag (0.11.1)."""
    def make():
        raw = json.dumps(slim_view(collection_view()), ensure_ascii=False).encode("utf-8")
        return raw, gzip.compress(raw, compresslevel=5), etag_of(raw)
    return memo("collection", COL_FILES, make)


def details(keys):
    """Felder der Einzelheiten je Spiel (0.11.1) aus der zwischengespeicherten Sammlung: {Schlüssel: {Feld: Wert}}."""
    want = {str(k) for k in keys[:5000] if isinstance(k, str)}
    return {r["key"]: {f: r.get(f) or "" for f in DETAIL_FIELDS}
            for r in collection_view().get("games") or [] if r["key"] in want}


def colview_patch(rows, before):
    """Nach einer Entscheidung (unter store.lock): die zwischengespeicherte Sammlung bekommt nur die neuen Zeilen der
    betroffenen Spiele, statt alles neu zu rechnen (0.11.1). before ist der Stand der Dateien beim Lesen der Sammlung;
    passt der Zwischenspeicher nicht genau dazu (oder rechnet gerade jemand), bleibt er, wie er ist, und wird beim
    nächsten Abruf ganz neu gerechnet."""
    with _memo_lock:
        busy = _memo_busy.get("colview")
    if busy is None or not busy.acquire(blocking=False):
        return False
    try:
        with _memo_lock:
            hit = _memo.get("colview")
        if not hit or hit[0] != (store.DATA_DIR, before, None):
            return False
        games = [rows.get(r["key"], r) for r in hit[1]["games"]]
        nv = dict(hit[1], games=games, genres=sorted({x for r in games for x in r["genres"]}))
        with _memo_lock:
            _memo["colview"] = ((store.DATA_DIR, store.stamp(*COL_FILES), None), nv)
        return True
    finally:
        busy.release()


def decided(col, keys, before):
    """Zeilen der Spiele nach einer Entscheidung (ohne Einzelheiten) für die Antwort; der Zwischenspeicher bekommt sie
    auch. Die Oberfläche tauscht nur diese Zeilen aus, statt die ganze Sammlung neu zu laden (0.11.1)."""
    rows = collection.rows(col, store.load_data(), keys)
    colview_patch(rows, before)
    return {k: slim(r) for k, r in rows.items()}


# Mein Stand (0.6.0, wie im eShopKompass): je Spiel der Sammlung von Hand Backlog, angefangen oder
# durchgespielt, Favorit oder ab 0.10.2 ignorieren. Steht in data.json und damit in der Sicherung
MARK_ST = ("backlog", "started", "done")


def set_mark(data, body):
    key = _text(body.get("key"), 300)
    k, v = body.get("k"), body.get("v")
    if not key or k not in ("s", "fav", "ign"):
        raise ValueError("Mein Stand: Spiel und Art fehlen")
    if k == "s" and v not in (None, "", *MARK_ST):
        raise ValueError("Mein Stand: unbekannter Stand")
    m = dict(data["marks"].get(key) or {})
    if k == "s":
        m.pop("s", None)
        if v:
            m["s"] = v
    else:
        # Favorit und ignorieren (0.10.2, nie wieder vorschlagen) schließen sich aus
        m.pop(k, None)
        if v:
            m.pop("ign" if k == "fav" else "fav", None)
            m[k] = True
    if m:
        data["marks"][key] = m
    else:
        data["marks"].pop(key, None)
    return data["marks"]


def _text(v, limit):
    return str(v if v is not None else "").strip()[:limit]


def edit_title(body):
    """Felder eines Titels von Hand ändern. Nur, was in der Anfrage steht, ändert sich."""
    with store.lock:
        data = store.load_data()
        key = str(body.get("key") or "")
        if key not in data["titles"]:
            raise ValueError("Titel nicht gefunden")
        t = data["titles"][key]
        if "name" in body:
            name = _text(body["name"], 200)
            if not name:
                raise ValueError("Der Name darf nicht leer sein")
            old, t["name"] = t["name"], name
            titles.add_alias(t, old)
        if "note" in body:
            t["note"] = _text(body["note"], 2000)
        if "wish" in body and bool(body["wish"]) != bool(t.get("wish")):
            titles.wish_by_hand(t, bool(body["wish"]))
        if isinstance(body.get("contains"), list):
            titles.set_bundle(data, key, body["contains"])
        if "crossbuy" in body:
            # Eigene Angabe (ja, nein) oder „automatisch“ (None): dann gelten VRDB und Tabelle;
            # ein Tabellenwert bleibt dabei stehen
            cb = body["crossbuy"] if body["crossbuy"] in (True, False) else None
            if cb is not None:
                t["crossbuy"], t["crossbuy_src"] = cb, "Hand"
            elif library.crossbuy_origin(t) == "Hand":
                t["crossbuy"] = None
                t.pop("crossbuy_src", None)
        for side in ("meta", "pc"):
            f = "owned_" + side
            if f in body:
                if body[f]:
                    t["owned"].setdefault(side, {"src": "hand", "at": titles.now_iso(),
                                                 **({"label": "PC"} if side == "pc" else {})})
                else:
                    t["owned"].pop(side, None)
        mid = _text(body.get("meta_id"), 500) if body.get("meta_id") is not None else None
        if mid and not mid.isdigit():
            # Ein Link statt der Zahl: Meta-ID daraus, QuestStoreDB- und VRDB-Links bleiben stehen
            link, mid = mid, titles.meta_id_from(mid)
            if not mid:
                raise ValueError("In diesem Link steht keine Meta-ID")
            if titles.link_kind(link) in ("vrdb", "qsdb"):
                t.setdefault("links", {})[titles.link_kind(link)] = link
            body = dict(body, meta_id=mid)
        if body.get("meta_id") is not None or body.get("steam_appid") is not None:
            # Neue Kennung von Hand: beim nächsten Abgleich wieder suchen
            t.pop("meta_miss", None)
            t.pop("steam_miss", None)
        key = titles.set_ids(data, key, body.get("meta_id"), body.get("steam_appid"))
        t = data["titles"][key]
        if body.get("steam_appid") is not None:
            # 0.10.23: von Hand gesetzt, accounts.unlink_flat lässt sie stehen
            if t.get("steam_appid"):
                t["steam_hand"] = True
            else:
                t.pop("steam_hand", None)
        if body.get("steam_sure") is True and t.get("steam_appid"):
            # „passt“ unter „Zu erledigen“: die Steam-ID gilt als geprüft
            t["steam_sure"] = True
            t["steam_hand"] = True
            t.pop("steam_doubt", None)
        store.save_data(data)
    return state()


def new_title(body):
    with store.lock:
        data = store.load_data()
        name = _text(body.get("name"), 200)
        if not name:
            raise ValueError("Bitte einen Namen eintragen")
        link = _text(body.get("link"), 500)
        k, _ = titles.upsert(data, name, titles.meta_id_from(link), titles.steam_id_from(link))
        t = data["titles"][k]
        titles.note_origin(t, "hand")
        kind = titles.link_kind(link)
        if kind in ("vrdb", "qsdb"):
            t["links"][kind] = link
        if titles.steam_id_from(link):
            t["steam_sure"] = t["steam_hand"] = True
        if body.get("wish", True) and not t.get("owned"):
            titles.wish_by_hand(t, True)
        store.save_data(data)
    return state()


def _is_todo(text):
    try:
        return imports.detect(text) == "todo"
    except ValueError:
        return False


def import_todo(text, dry):
    """Antwort auf einen Auftrag aus „Zu erledigen“ (0.10.24): erst Vorschau, dann übernehmen. Die Retro-Listen und die
    PC-Wunschliste liegen in eigenen Dateien; sie ändert act mit denselben Schritten wie die Knöpfe."""
    with store.lock:
        data = store.load_data()
        col = store.load_json(collection.FILE, collection.EMPTY)
        pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
        changed, user = set(), []           # user (0.11.0): Spiele mit geänderten Nutzereingaben
        cache = {}

        def act(kind, key, val):
            if kind == "pcid":
                pcwish.settle_id(pw, key, val)
                changed.add("pw")
            elif kind == "near":
                g = (col.get("games") or {}).get(key) or {}
                sy = g.get("system") or ""
                if sy not in cache:
                    cache[sy] = (store.load_json(retro.CACHE, {}).get(sy) or {}).get("idx")
                retro.settle_near(col, key, bool(val), cache[sy])
                user.append(key)
                changed.add("col")          # die Fassung (de) ist gleich neu gerechnet
            elif kind == "own":
                retro.settle_own(col, key, take=bool(val))
                user.append(key)
            elif kind in ("wheel", "vrmod") and key in (col.get("games") or {}):
                col["games"][key]["r_" + kind] = val
                user.append(key)
        games = collection.view(col, data)["games"]
        res = aufgaben.apply(text, data, retro.near_list(col), retro.own_list(col), pcwish.id_todo(pw), dry=dry, act=act, games=games)
        if not dry:
            store.save_data(data)
            if user:
                eingaben.save(col, user)    # erst die kleine Datei: der Haken beim Speichern der Sammlung liest sie
            if "col" in changed:
                store.save_json(collection.FILE, col)
            if "pw" in changed:
                store.save_json(pcwish.FILE, pw)
    return dict(res, kind="todo", state=None if dry else state())


def restore_titles(recs):
    """Rückgängig für Löschen und Zusammenführen: legt die alten Einträge unter ihrem Schlüssel
    wieder ab. Nur Einträge mit Namen, höchstens zwei auf einmal."""
    if not isinstance(recs, dict) or not 0 < len(recs) <= 2 or \
            not all(isinstance(t, dict) and _text(t.get("name"), 200) for t in recs.values()):
        raise ValueError("Nichts zum Zurücknehmen")
    with store.lock:
        data = store.load_data()
        for k, t in recs.items():
            data["titles"][str(k)[:200]] = t
        store.save_data(data)
    return state()


def index_html():
    """index.html mit der Version an Stilen und Skript (0.11.1), damit der Browser beide lange behalten darf."""
    with open(os.path.join(STATIC, "index.html"), encoding="utf-8") as f:
        page = f.read()
    v = urllib.parse.quote(sources.VERSION)
    return page.replace('href="style.css"', f'href="style.css?v={v}"').replace('src="js/app.js"', f'src="js/app.js?v={v}"').encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    server_version = "vr-navigator"
    # 0.11.1: HTTP/1.1, sonst fragt Chromium mit dem ETag nicht nach (If-None-Match) und lädt jedes Mal alles. Jede
    # Antwort hat eine Länge; eine Verbindung ohne Anfrage schließt nach timeout Sekunden
    protocol_version = "HTTP/1.1"
    timeout = 60

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None, cache="no-store", etag=None):
        """etag (0.11.1): mit If-None-Match gleich kommt 304 ohne Inhalt; der Browser fragt jedes Mal nach (no-cache),
        lädt aber nur, was sich geändert hat."""
        if etag:
            cache = "no-cache"
            if code == 200 and etag in [x.strip() for x in (self.headers.get("If-None-Match") or "").split(",")]:
                self.send_response(304)
                self.send_header("ETag", etag)
                self.send_header("Cache-Control", cache)
                self.end_headers()
                return
            extra = dict(extra or {}, ETag=etag)
        if self.command == "POST" and not getattr(self, "_consumed", False):
            # Inhalt der Anfrage nicht gelesen (zu groß, falscher Typ, fremde Adresse): die Verbindung endet hier,
            # sonst läse der Server den Rest als nächste Anfrage
            self.close_connection = True
            extra = dict(extra or {}, Connection="close")
        zipped = None
        if isinstance(body, tuple):         # schon fertig: (roh, gepackt), siehe collection_body
            body, zipped = body
        elif not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        packed = len(body) > 20_000 and "gzip" in (self.headers.get("Accept-Encoding") or "")
        if packed:
            body = zipped or gzip.compress(body, compresslevel=5)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if packed:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", cache)
        # Nicht in fremde Seiten einbetten, Typen nicht raten, keine Adresse an verlinkte Seiten
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _body(self, limit=1_000_000):
        # Nur JSON annehmen: Ein einfaches Formular einer fremden Seite im Browser kann so
        # nichts ändern.
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            raise ValueError("nur application/json")
        n = int(self.headers.get("Content-Length") or 0)
        if n < 0 or n > limit:          # negativ hieße: lesen bis zum Ende
            raise ValueError("zu groß")
        raw = self.rfile.read(n)
        self._consumed = True
        body = sicherung.loads(raw or b"{}")      # 0.10.29: NaN und Infinity gelten nicht
        if not isinstance(body, dict):
            raise ValueError("JSON-Objekt erwartet")
        return body

    def _foreign(self):
        if host_allowed(self.headers.get("Host")):
            return False
        self._send(421, {"error": "Unbekannte Adresse. Erlaubte Namen stehen in ALLOWED_HOSTS (siehe README)."})
        return True

    def do_GET(self):
        path = self.path.split("?")[0]
        if self._foreign():
            return
        try:
            if path == "/healthz":
                # 0.10.29: für den HEALTHCHECK von Docker; liest keine großen Dateien
                h = health()
                self._send(200 if h["ok"] else 503, h)
            elif path in ("/", "/index.html"):
                self._send(200, index_html(), "text/html; charset=utf-8", cache="no-cache")
            elif re.fullmatch(r"/(style\.css|js/[a-z-]+\.js)", path) and os.path.isfile(os.path.join(STATIC, path[1:])):
                # Teile der Oberfläche: nur diese Namen, kein Pfad aus der Anfrage sonst. Ab 0.11.1 mit der Version in
                # der Adresse (index_html): die gilt ein Jahr, ein Update bringt eine neue Adresse
                versioned = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query).get("v") == [sources.VERSION]
                with open(os.path.join(STATIC, path[1:]), "rb") as f:
                    self._send(200, f.read(), "text/css; charset=utf-8" if path.endswith(".css")
                               else "text/javascript; charset=utf-8",
                               cache="public, max-age=31536000, immutable" if versioned else "no-cache")
            elif path == "/api/state":
                raw = json.dumps(state(), ensure_ascii=False).encode("utf-8")
                self._send(200, raw, etag=etag_of(raw))
            elif path == "/api/diag":
                self._send(200, diag_view())
            elif path == "/api/status":
                self._send(200, sync.status())
            elif path == "/api/verlauf":
                # Preisverlauf eines Titels (0.9.1): ?vr=<Schlüssel> oder ?pc=<Schlüssel der PC-Wunschliste>
                q = urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query)
                vk, pk = (q.get("vr") or [""])[0][:300], (q.get("pc") or [""])[0][:300]
                if vk and vk in store.load_data()["titles"]:
                    self._send(200, verlauf.vr(store.load_data()["titles"][vk], store.load_json("history.json", {})))
                elif pk and pk in (store.load_json(pcwish.FILE, pcwish.EMPTY).get("items") or {}):
                    self._send(200, verlauf.pc(store.load_json(pcwish.FILE, pcwish.EMPTY)["items"][pk]))
                else:
                    self._send(404, {"error": "Titel nicht gefunden"})
            elif path == "/api/collection":
                raw, packed, tag = collection_body()
                self._send(200, (raw, packed), etag=tag)
            elif path == "/api/export":
                # dieselben Teile wie die Sicherungen im Datenordner, ab 0.11.0 mit den Nutzereingaben (eingaben)
                self._send(200, sicherung.snapshot(),
                           extra={"Content-Disposition": 'attachment; filename="vr-navigator-sicherung.json"'})
            elif path == "/api/abgleich":
                # Zum Nachprüfen (wie im eShopKompass): Stand und Protokoll des Abgleichs, Preisverlauf,
                # Einstellungen ohne Schlüssel und Links. Zum Einspielen nicht nötig
                se = {k: v for k, v in sync.load_settings().items() if k not in sync.SECRETS and k not in ("sharenite", "steam_id")}
                self._send(200, {"app": "vr-navigator", "version": sources.VERSION, "settings": se,
                                 "sync": store.load_json("sync.json", {}), "history": store.load_json("history.json", {})},
                           extra={"Content-Disposition": 'attachment; filename="vr-navigator-abgleich.json"'})
            else:
                self._send(404, {"error": "nicht gefunden"})
        except Exception as e:
            self._fail(path, e)

    def do_POST(self):
        path = self.path.split("?")[0]
        self._consumed = False          # dieselbe Verbindung trägt mehrere Anfragen (HTTP/1.1)
        if self._foreign():
            return
        try:
            # Importe und Sicherungen dürfen größer sein (Playnite-Export: einige MB)
            big = path in ("/api/import", "/api/restore")
            body = self._body(50_000_000 if big else 1_000_000)
            if path == "/api/import":
                kind = str(body.get("kind") or "")
                if kind not in ("auto", "retro", "todo") and kind not in imports.IMPORTERS:
                    raise ValueError("unbekannte Art des Imports")
                dry = body.get("dry") is not False
                text = str(body.get("text") or "")
                if kind == "auto" and retro.looks_like(text):
                    kind = "retro"
                if kind in ("auto", "todo") and _is_todo(text):
                    self._send(200, import_todo(text, dry))
                    return
                fn = import_retro if kind == "retro" else imports.import_auto if kind == "auto" else imports.IMPORTERS[kind]
                # 0.10.29: die Vorschau ändert nichts und braucht das Schloss nicht; nur Übernehmen hält es
                with store.lock if not dry else _NO_LOCK:
                    data = store.load_data()
                    res = fn(data, text, dry=dry, lists=_lists(body)) if fn is import_retro else fn(data, text, dry=dry)
                    if (res.get("kind") or kind) == "playnite":
                        res["collection"] = import_collection(data, text, dry)
                    if not dry:
                        store.save_data(data)
                self._send(200, dict(res, state=None if dry else state()))
            elif path == "/api/retro/gone":
                # „Stand übernehmen“ (drop) oder „behalten“ (keep) für Spiele, die in der Retro-Liste fehlen
                action = str(body.get("action") or "")
                if action not in ("drop", "keep"):
                    raise ValueError("unbekannte Aktion")
                with store.lock:
                    col = store.load_json(collection.FILE, collection.EMPTY)
                    n = retro.settle(col, action)
                    store.save_json(collection.FILE, col)
                    data = store.load_data()
                    if data["imports"].get("retro"):
                        data["imports"]["retro"]["gone"] = 0
                        store.save_data(data)
                # Spiele fallen weg: die ganze Sammlung, ab 0.11.1 ohne Einzelheiten (selten)
                self._send(200, {"changed": n, "collection": slim_view(collection_view())})
            elif path == "/api/retro/own":
                # Widerspruch zu deiner Ordner-Liste (0.8.8): „Liste gilt“ für ein Spiel oder alle; ab 0.9.6 mit
                # take „Quellen gelten“ (libretro und IGDB einig)
                with store.lock:
                    col = store.load_json(collection.FILE, collection.EMPTY)
                    before = store.stamp(*COL_FILES)
                    keys = [x["key"] for x in retro.own_list(col)] if body.get("all") is True else [_text(body.get("key"), 300)]
                    for k in keys:
                        retro.settle_own(col, k, take=body.get("take") is True)
                    eingaben.save(col, keys)        # 0.11.0: nur die kleine Datei, nicht die ganze Sammlung
                    rows = decided(col, keys, before)
                self._send(200, {"retro_own": retro.own_list(col), "rows": rows})
            elif path == "/api/retro/de":
                # „DE fehlt“ aus „Zu erledigen“ (0.10.12): ignorieren (ein Spiel, alle oder alle eines Systems) oder wieder melden
                ign = body.get("ign") is not False
                with store.lock:
                    col = store.load_json(collection.FILE, collection.EMPTY)
                    before = store.stamp(*COL_FILES)
                    if body.get("all") is True:
                        sy = _text(body.get("system"), 40)
                        keys = [x["key"] for x in retro.de_list(col) if not sy or x["system"] == sy]
                    elif isinstance(body.get("keys"), list):      # „Rückgängig“ nach „alle ignorieren“
                        keys = [_text(k, 300) for k in body["keys"][:5000]]
                    else:
                        keys = [_text(body.get("key"), 300)]
                    n = retro.settle_de(col, keys, ign)
                    eingaben.save(col, keys)        # 0.11.0: nur die kleine Datei
                    rows = decided(col, keys, before)
                self._send(200, {"changed": n, "retro_de": retro.de_list(col), "rows": rows})
            elif path == "/api/retro/near":
                # Ähnlicher Name aus „Zu erledigen“ (0.8.4): dieselbe Fassung oder nicht
                key = _text(body.get("key"), 300)
                with store.lock:
                    col = store.load_json(collection.FILE, collection.EMPTY)
                    before = store.stamp(*COL_FILES)
                    g = (col.get("games") or {}).get(key) or {}
                    idx = (store.load_json(retro.CACHE, {}).get(g.get("system") or "") or {}).get("idx")
                    retro.settle_near(col, key, bool(body.get("ok")), idx)
                    eingaben.save(col, [key])
                    store.save_json(collection.FILE, col)      # die Fassung (de) ist neu gerechnet, nur bei diesem Spiel
                    rows = decided(col, [key], before)
                self._send(200, {"retro_near": retro.near_list(col), "rows": rows})
            elif path == "/api/pcwish/id":
                # Steam-ID eines PC-Wunschs aus „Zu erledigen“ (0.8.24): eine der angebotenen oder keine
                with store.lock:
                    pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
                    pcwish.settle_id(pw, _text(body.get("key"), 300), _text(body.get("appid"), 20))
                    store.save_json(pcwish.FILE, pw)
                data = store.load_data()
                pcv = pcwish.view(data)
                muster.annotate({}, pcv, data, pw.get("items") or {}, price_stats(data, pw))
                self._send(200, {"pcwish": pcv, "pcwish_ids": pcwish.id_todo(pw)})
            elif path == "/api/details":
                # Einzelheiten der Sammlung beim Aufklappen (0.11.1): {"keys": [...]}, liest nur den Zwischenspeicher
                keys = body.get("keys")
                if not isinstance(keys, list):
                    raise ValueError("keys fehlt")
                self._send(200, {"games": details(keys)})
            elif path == "/api/title":
                self._send(200, edit_title(body))
            elif path == "/api/mark":
                with store.lock:
                    data = store.load_data()
                    marks = set_mark(data, body)
                    store.save_data(data)
                self._send(200, {"marks": marks})
            elif path == "/api/wishes":
                # Eine Aktion für mehrere Titel aus „Wunschliste abgleichen“
                with store.lock:
                    data = store.load_data()
                    keys = [str(k) for k in (body.get("keys") or [])][:2000]
                    old = {k: copy.deepcopy(data["titles"][k]) for k in keys if k in data["titles"]}
                    n = lists.apply(data, str(body.get("kind") or ""), keys)
                    store.save_data(data)
                self._send(200, dict(state(), changed=n, undo=old or None))
            elif path == "/api/title/new":
                self._send(200, new_title(body))
            elif path == "/api/title/delete":
                # Statt einer Rückfrage: Die Oberfläche bietet „Rückgängig“ und schickt den
                # alten Eintrag an /api/title/restore zurück
                with store.lock:
                    data = store.load_data()
                    key = str(body.get("key") or "")
                    old = data["titles"].pop(key, None)
                    store.save_data(data)
                self._send(200, dict(state(), undo={key: old} if old else None))
            elif path == "/api/title/restore":
                self._send(200, restore_titles(body.get("titles")))
            elif path == "/api/merge":
                with store.lock:
                    data = store.load_data()
                    keep, gone = str(body.get("keep") or ""), str(body.get("gone") or "")
                    if keep not in data["titles"] or gone not in data["titles"]:
                        raise ValueError("Titel nicht gefunden")
                    undo = {keep: copy.deepcopy(data["titles"][keep]), gone: copy.deepcopy(data["titles"][gone])}
                    titles.merge(data, keep, gone)
                    store.save_data(data)
                self._send(200, dict(state(), undo=undo))
            elif path == "/api/not_same":
                with store.lock:
                    data = store.load_data()
                    pair = sorted([str(body.get("a") or ""), str(body.get("b") or "")])
                    data.setdefault("not_same", [])
                    if pair not in data["not_same"]:
                        data["not_same"].append(pair)
                    store.save_data(data)
                self._send(200, state())
            elif path == "/api/settings":
                sync.save_settings(body)
                self._send(200, state())
            elif path == "/api/sync":
                only = body.get("only")
                only = {str(x) for x in only} if isinstance(only, list) else None
                started = sync.start(only, fast=body.get("fast") is True)
                self._send(200, dict(state(), started=started))
            elif path == "/api/diag":
                start_diag()
                self._send(200, diag_view())
            elif path == "/api/restore":
                # 0.10.29: erst Vorschau (dry), dann feldweise und mit Sicherung des jetzigen Stands vorher.
                # Sicherungen vor 0.4.0 haben keine Sammlung, vor 0.8.7 keine PC-Wunschliste: die bleiben dann
                if sync.status_running() and body.get("dry") is False:
                    raise ValueError("Gerade läuft ein Abgleich. Bitte nach dessen Ende einspielen.")
                # Ohne dry wie bisher: einspielen und den Zustand zurück (Schnittstelle bleibt), jetzt mit dem Bericht
                res = sicherung.restore(body, dry=body.get("dry") is True)
                self._send(200, res if res["dry"] else dict(state(), restore=res))
            else:
                self._send(404, {"error": "nicht gefunden"})
        except ValueError as e:
            self._send(400, {"error": str(e)})      # Eingabefehler: Text für dich gedacht
        except Exception as e:
            self._fail(path, e)

    def _fail(self, path, e):
        """Unerwarteter Fehler: Einzelheiten ins Protokoll des Containers, an den Browser nur
        die Art des Fehlers, keine Pfade oder Innereien des Servers."""
        print(f"Fehler bei {path}:", file=sys.stderr)
        traceback.print_exception(e, file=sys.stderr)
        self._send(500, {"error": f"Interner Fehler ({type(e).__name__}), Einzelheiten im Protokoll des Containers"})


class _NoLock:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


_NO_LOCK = _NoLock()


def health():
    """Lebenszeichen (0.10.29): Version, ob der Datenordner da ist, ob ein Abgleich läuft."""
    ok = os.path.isdir(store.DATA_DIR) and os.access(store.DATA_DIR, os.W_OK)
    return {"ok": ok, "version": sources.VERSION, "sync_running": sync.status_running()}


WARTUNG_S = 600
WARTUNG_START_S = 120


def wartung(once=False):
    """Pflege im Hintergrund (0.10.29): tägliche Sicherung, monatlicher Wiederherstellungstest; nie während eines
    Abgleichs (der schreibt laufend). Läuft auch ohne Zeitplan (AUTO_SYNC=0). Erst WARTUNG_START_S nach dem Start, damit
    das erste Vorrechnen der Ansichten Vorrang hat."""
    if not once:
        time.sleep(WARTUNG_START_S)
    while True:
        try:
            if not sync.status_running():
                sicherung.daily()
                if sicherung.check_due() and sicherung.files():
                    sicherung.check()
        except Exception as e:
            print("Wartung:", type(e).__name__, e, file=sys.stderr)
        if once:
            return
        time.sleep(WARTUNG_S)


def _warm(once=False):
    """Sammlung und Zustand gleich nach dem Start berechnen, ab 0.10.15 auch nach jedem Abgleich und Import: alle
    paar Sekunden prüfen, ob sich eine Datei geändert hat (nur die Änderungszeit, ohne Lesen), und dann vorab
    rechnen; so öffnet der erste Klick ohne Warten. Während eines Abgleichs nicht, der schreibt laufend."""
    while True:
        try:
            if not sync.status_running():
                collection_body()
                state()
        except Exception:
            pass
        if once:
            return
        time.sleep(WARM_S)


WARM_S = 3


def main():
    port = int(os.environ.get("PORT", "8788"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    if os.environ.get("AUTO_SYNC", "1") != "0":
        threading.Thread(target=sync.scheduler, daemon=True).start()
    threading.Thread(target=_warm, daemon=True).start()
    threading.Thread(target=wartung, daemon=True).start()
    print(f"VR-Navigator läuft auf Port {port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
