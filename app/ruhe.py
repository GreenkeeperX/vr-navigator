"""Ruhezeit je Server (0.10.29): Antwortet ein Server mit 403 oder 429 oder einer Prüfseite, fragt das Tool ihn
eine Weile gar nicht mehr, gleich aus welcher Quelle, aus dem Abgleich oder aus dem Verbindungstest.

Vorher hing die Ruhe am Namen der Quelle: Wurde „Steam“ gesperrt, fragten Rezensionen, Details und Spielerzahlen
denselben Server weiter. Jetzt zählt der Name des Servers (etwa store.steampowered.com). Die Ruhezeiten stehen in
ruhe.json im Datenordner und überstehen Neustarts; geschrieben wird sofort bei der Sperre, nicht erst am Ende eines
Laufs. Länge: RUHE_STUNDEN in der Umgebung (1 bis 168), sonst 24 Stunden.
"""
import os
import threading
import urllib.parse
from datetime import datetime, timedelta, timezone

from . import store

FILE = "ruhe.json"
DEFAULT_H = 24
_lock = threading.Lock()
_cache = {"stamp": (), "hosts": {}}


def hours():
    """Ruhezeit in Stunden aus RUHE_STUNDEN, sonst DEFAULT_H. Unsinnige Werte gelten nicht."""
    try:
        h = int(os.environ.get("RUHE_STUNDEN", "") or DEFAULT_H)
    except ValueError:
        return DEFAULT_H
    return h if 1 <= h <= 168 else DEFAULT_H


def host_of(url):
    """Server einer Adresse in Kleinbuchstaben; ein Name ohne Schema gilt schon als Server."""
    s = str(url or "")
    if "://" not in s:
        return s.strip().lower().rstrip(".")
    return (urllib.parse.urlsplit(s).hostname or "").lower().rstrip(".")


def _now():
    return datetime.now(timezone.utc)


def _iso(at):
    return at.isoformat(timespec="seconds")


def _hosts():
    """Alle Einträge, zwischengespeichert, solange sich die Datei nicht ändert (wird bei jedem Abruf gefragt)."""
    st = (store.DATA_DIR, store.stamp(FILE))
    if st != _cache["stamp"]:
        got = store.load_json(FILE, {})
        hosts = got.get("hosts") if isinstance(got.get("hosts"), dict) else {}
        _cache.update(stamp=st, hosts={str(h): e for h, e in hosts.items() if isinstance(e, dict) and isinstance(e.get("until"), str)})
    return _cache["hosts"]


def until(url, at=None):
    """Ende der Ruhezeit des Servers als ISO-Zeit, "" wenn er gefragt werden darf."""
    host = host_of(url)
    if not host:
        return ""
    e = _hosts().get(host)
    if not e:
        return ""
    return e["until"] if e["until"] > _iso(at or _now()) else ""


def block(url, why, source="", at=None):
    """Sperre eintragen und sofort speichern. Eine längere Ruhe bleibt bestehen. Gibt das Ende zurück."""
    host = host_of(url)
    if not host:
        return ""
    at = at or _now()
    end = _iso(at + timedelta(hours=hours()))
    with _lock, store.lock:
        got = store.load_json(FILE, {})
        hosts = got.get("hosts") if isinstance(got.get("hosts"), dict) else {}
        old = hosts.get(host) if isinstance(hosts.get(host), dict) else {}
        if str(old.get("until") or "") >= end:
            return old["until"]
        hist = [x for x in (got.get("history") or []) if isinstance(x, dict)][-49:]
        hosts[host] = {"until": end, "at": _iso(at), "why": str(why or "")[:120], "source": str(source or "")[:60]}
        hist.append(dict(hosts[host], host=host))
        # abgelaufene Einträge fallen beim Schreiben weg, die Liste der Sperren (history) bleibt für die Statuskarte
        now = _iso(at)
        store.save_json(FILE, {"hosts": {h: e for h, e in hosts.items() if isinstance(e, dict) and str(e.get("until") or "") > now},
                               "history": hist})
        _cache["stamp"] = ()
    return end


def active(at=None):
    """Ruhende Server {Name: {until, at, why, source}}."""
    now = _iso(at or _now())
    return {h: dict(e) for h, e in _hosts().items() if e["until"] > now}


def history():
    """Die letzten Sperren (höchstens 50), älteste zuerst."""
    got = store.load_json(FILE, {})
    return [x for x in (got.get("history") or []) if isinstance(x, dict)]


def clear():
    """Nur für Tests und den Notfall: alle Ruhezeiten aufheben."""
    with _lock, store.lock:
        store.save_json(FILE, {"hosts": {}, "history": history()})
        _cache["stamp"] = ()
