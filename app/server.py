"""Kleiner Webserver: liefert die Oberfläche und eine JSON-Schnittstelle."""
import gzip
import ipaddress
import json
import os
import re
import sys
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import imports, library, sources, store, titles

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


def state():
    return dict(library.view(store.load_data()), version=sources.VERSION)


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
            t["name"] = name
        if "note" in body:
            t["note"] = _text(body["note"], 2000)
        if "wish" in body:
            t["wish"] = bool(body["wish"])
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
        titles.set_ids(data, key, body.get("meta_id"), body.get("steam_appid"))
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
        kind = titles.link_kind(link)
        if kind in ("vrdb", "qsdb"):
            t["links"][kind] = link
        if titles.steam_id_from(link):
            t["steam_sure"] = True
        if body.get("wish", True) and not t.get("owned"):
            t["wish"] = True
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
            elif path == "/api/export":
                self._send(200, {"app": "vr-navigator", "version": sources.VERSION, "data": store.load_data()},
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
                if kind not in imports.IMPORTERS:
                    raise ValueError("unbekannte Art des Imports")
                dry = body.get("dry") is not False
                with store.lock:
                    data = store.load_data()
                    res = imports.IMPORTERS[kind](data, str(body.get("text") or ""), dry=dry)
                    if not dry:
                        store.save_data(data)
                self._send(200, dict(res, state=None if dry else state()))
            elif path == "/api/title":
                self._send(200, edit_title(body))
            elif path == "/api/title/new":
                self._send(200, new_title(body))
            elif path == "/api/title/delete":
                with store.lock:
                    data = store.load_data()
                    data["titles"].pop(str(body.get("key") or ""), None)
                    store.save_data(data)
                self._send(200, state())
            elif path == "/api/merge":
                with store.lock:
                    data = store.load_data()
                    keep, gone = str(body.get("keep") or ""), str(body.get("gone") or "")
                    if keep not in data["titles"] or gone not in data["titles"]:
                        raise ValueError("Titel nicht gefunden")
                    titles.merge(data, keep, gone)
                    store.save_data(data)
                self._send(200, state())
            elif path == "/api/not_same":
                with store.lock:
                    data = store.load_data()
                    pair = sorted([str(body.get("a") or ""), str(body.get("b") or "")])
                    data.setdefault("not_same", [])
                    if pair not in data["not_same"]:
                        data["not_same"].append(pair)
                    store.save_data(data)
                self._send(200, state())
            elif path == "/api/restore":
                d = body.get("data")
                if not isinstance(d, dict) or not isinstance(d.get("titles"), dict):
                    raise ValueError("Keine Sicherung des VR-Navigator")
                bad = [k for k, t in d["titles"].items() if not isinstance(t, dict) or not t.get("name")]
                if bad:
                    raise ValueError(f"{len(bad)} Einträge ohne Namen, Sicherung nicht übernommen")
                with store.lock:
                    store.save_data(d)
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
    print(f"VR-Navigator läuft auf Port {port}", flush=True)
    srv.serve_forever()


if __name__ == "__main__":
    main()
