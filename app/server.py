"""Kleiner Webserver: liefert die Oberfläche und eine JSON-Schnittstelle."""
import copy
import gzip
import ipaddress
import json
import os
import re
import sys
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import collection, imports, library, sources, store, sync, titles

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


def settings_view():
    """Einstellungen für die Oberfläche: der Schlüssel selbst geht nie zurück an den Browser."""
    s = sync.load_settings()
    key = s.pop("gg_key")
    steam = s.pop("steam_key")
    wish = s.pop("gg_wish")
    return dict(s, gg_key_set=bool(key), gg_key_end=key[-4:] if len(key) > 12 else "",
                steam_key_set=bool(steam), gg_wish_set=bool(wish))


def import_collection(data, text, dry):
    """Der Playnite-Export füllt neben der Bibliothek (VR-Titel) auch die ganze Sammlung für
    Entdecken. Die Zusammenfassung steht unter imports.collection in data.json."""
    games = collection.parse(text)
    col = store.load_json(collection.FILE, collection.EMPTY)
    if dry:
        return {"n": len(games), "new": sum(k not in (col.get("games") or {}) for k in games)}
    new = collection.replace(col, games)
    store.save_json(collection.FILE, col)
    data["imports"]["collection"] = {"at": col["at"], "n": len(games), "new": new}
    return {"n": len(games), "new": new}


def state():
    return dict(library.view(store.load_data(), hist=store.load_json("history.json", {})), version=sources.VERSION,
                sync=sync.status(), settings=settings_view())


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
            t["crossbuy"] = body["crossbuy"] if body["crossbuy"] in (True, False) else None
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
        titles.set_ids(data, key, body.get("meta_id"), body.get("steam_appid"))
        if body.get("steam_sure") is True and t.get("steam_appid"):
            # „passt“ unter „Zu erledigen“: die Steam-ID gilt als geprüft
            t["steam_sure"] = True
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
            t["steam_sure"] = True
        if body.get("wish", True) and not t.get("owned"):
            titles.wish_by_hand(t, True)
        store.save_data(data)
    return state()


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


class Handler(BaseHTTPRequestHandler):
    server_version = "vr-navigator"

    def log_message(self, fmt, *args):
        pass

    def _send(self, code, body, ctype="application/json; charset=utf-8", extra=None):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        packed = len(body) > 20_000 and "gzip" in (self.headers.get("Accept-Encoding") or "")
        if packed:
            body = gzip.compress(body, compresslevel=5)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        if packed:
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
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
        body = json.loads(self.rfile.read(n) or b"{}")
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
            if path in ("/", "/index.html"):
                with open(os.path.join(STATIC, "index.html"), "rb") as f:
                    self._send(200, f.read(), "text/html; charset=utf-8")
            elif re.fullmatch(r"/(style\.css|js/[a-z-]+\.js)", path) and os.path.isfile(os.path.join(STATIC, path[1:])):
                # Teile der Oberfläche: nur diese Namen, kein Pfad aus der Anfrage sonst
                with open(os.path.join(STATIC, path[1:]), "rb") as f:
                    self._send(200, f.read(), "text/css; charset=utf-8" if path.endswith(".css")
                               else "text/javascript; charset=utf-8")
            elif path == "/api/state":
                self._send(200, state())
            elif path == "/api/status":
                self._send(200, sync.status())
            elif path == "/api/collection":
                self._send(200, collection.view(store.load_json(collection.FILE, collection.EMPTY)))
            elif path == "/api/export":
                self._send(200, {"app": "vr-navigator", "version": sources.VERSION, "data": store.load_data(),
                                 "collection": store.load_json(collection.FILE, collection.EMPTY)},
                           extra={"Content-Disposition": 'attachment; filename="vr-navigator-sicherung.json"'})
            else:
                self._send(404, {"error": "nicht gefunden"})
        except Exception as e:
            self._fail(path, e)

    def do_POST(self):
        path = self.path.split("?")[0]
        if self._foreign():
            return
        try:
            # Importe und Sicherungen dürfen größer sein (Playnite-Export: einige MB)
            big = path in ("/api/import", "/api/restore")
            body = self._body(50_000_000 if big else 1_000_000)
            if path == "/api/import":
                kind = str(body.get("kind") or "")
                if kind != "auto" and kind not in imports.IMPORTERS:
                    raise ValueError("unbekannte Art des Imports")
                dry = body.get("dry") is not False
                fn = imports.import_auto if kind == "auto" else imports.IMPORTERS[kind]
                text = str(body.get("text") or "")
                with store.lock:
                    data = store.load_data()
                    res = fn(data, text, dry=dry)
                    if (res.get("kind") or kind) == "playnite":
                        res["collection"] = import_collection(data, text, dry)
                    if not dry:
                        store.save_data(data)
                self._send(200, dict(res, state=None if dry else state()))
            elif path == "/api/title":
                self._send(200, edit_title(body))
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
                started = sync.start(only)
                self._send(200, dict(state(), started=started))
            elif path == "/api/diag":
                self._send(200, {"lines": sync.diagnose()})
            elif path == "/api/restore":
                d = body.get("data")
                if not isinstance(d, dict) or not isinstance(d.get("titles"), dict):
                    raise ValueError("Keine Sicherung des VR-Navigator")
                bad = [k for k, t in d["titles"].items() if not isinstance(t, dict) or not t.get("name")]
                if bad:
                    raise ValueError(f"{len(bad)} Einträge ohne Namen, Sicherung nicht übernommen")
                col = body.get("collection")
                with store.lock:
                    store.save_data(d)
                    # Sicherungen vor 0.4.0 haben keine Sammlung: dann bleibt die vorhandene
                    if isinstance(col, dict) and isinstance(col.get("games"), dict):
                        games = {str(k): g for k, g in col["games"].items() if isinstance(g, dict) and g.get("name")}
                        store.save_json(collection.FILE, dict(col, games=games, n=len(games)))
                self._send(200, state())
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


def main():
    port = int(os.environ.get("PORT", "8788"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    if os.environ.get("AUTO_SYNC", "1") != "0":
        threading.Thread(target=sync.scheduler, daemon=True).start()
    print(f"VR-Navigator läuft auf Port {port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
