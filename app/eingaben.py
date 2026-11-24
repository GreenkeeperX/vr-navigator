"""Nutzereingaben zur Sammlung (0.11.0, V-2): deine Entscheidungen zu Spielen der Sammlung in einer eigenen kleinen
Datei statt in collection.json. Bestandsaufnahme und Begründung: docs/sammlung-felder.md.

- `overlay(col)`: hängt store beim Lesen von collection.json ein. Entfernt die Nutzerfelder aus den Spielen und setzt
  die aus eingaben.json ein; jede Stelle im Code sieht also die zusammengeführte Sammlung wie bisher.
- `save(col, keys)`: nach einer Entscheidung nur eingaben.json schreiben (für die genannten Spiele), nicht die
  ganze Sammlung.
- `migrate()`: beim ersten Lesen ohne eingaben.json die Nutzerfelder aus collection.json übernehmen, mit Sicherung
  vorher und Prüfung danach; collection.json bleibt dabei unverändert.
"""
import json
import sys
import threading

from . import store

FILE = "eingaben.json"
COLLECTION = "collection.json"
FIELDS = ("de_ign", "own_ok", "own_take", "alias", "near_no", "r_wheel", "r_vrmod")
V = 1
_cache = {"stamp": (), "games": {}}
_migrating = threading.local()


def _empty():
    return {"v": V, "games": {}}


def _games():
    """Einträge aus eingaben.json, zwischengespeichert, solange sich die Datei nicht ändert."""
    st = (store.DATA_DIR, store.stamp(FILE))
    if st != _cache["stamp"]:
        got = store.load_json(FILE, _empty())
        games = got.get("games") if isinstance(got.get("games"), dict) else {}
        _cache.update(stamp=st, games={str(k): {f: v for f, v in e.items() if f in FIELDS}
                                       for k, e in games.items() if isinstance(e, dict)})
    return _cache["games"]


def migrating():
    return getattr(_migrating, "on", False)


def exists():
    return store.stamp(FILE)[0] is not None


def extract(col):
    """Nutzerfelder aller Spiele einer Sammlung: {Schlüssel: {Feld: Wert}} (nur Spiele mit mindestens einem)."""
    out = {}
    for k, g in ((col or {}).get("games") or {}).items():
        if isinstance(g, dict):
            e = {f: g[f] for f in FIELDS if f in g}
            if e:
                out[str(k)] = e
    return out


def overlay(col):
    """Beim Lesen von collection.json (store.load_json): Nutzerfelder aus eingaben.json gelten. Ohne eingaben.json
    erst der Umzug; misslingt er, bleibt die Sammlung, wie sie ist."""
    if not isinstance(col, dict) or not isinstance(col.get("games"), dict) or getattr(_migrating, "on", False):
        return col
    if not exists():
        if not migrate(col):
            return col
    user = _games()
    for k, g in col["games"].items():
        if not isinstance(g, dict):
            continue
        for f in FIELDS:
            g.pop(f, None)
        e = user.get(k)
        if e:
            g.update(json.loads(json.dumps(e)))
    return col


def save(col, keys):
    """Die Nutzerfelder der genannten Spiele aus col nach eingaben.json schreiben (nur diese, unter dem Schloss)."""
    with store.lock:
        got = store.load_json(FILE, _empty())
        games = got.get("games") if isinstance(got.get("games"), dict) else {}
        for k in keys:
            g = (col.get("games") or {}).get(k)
            e = {f: g[f] for f in FIELDS if f in g} if isinstance(g, dict) else None
            if e:
                games[str(k)] = e
            elif isinstance(g, dict):
                games.pop(str(k), None)         # alle Entscheidungen zurückgenommen
            # gibt es das Spiel nicht (mehr), bleibt ein vorhandener Eintrag stehen
        store.save_json(FILE, dict(got, v=V, games=games))
        _cache["stamp"] = ()


def replace(games):
    """Ganze Nutzereingaben setzen (Wiederherstellen einer Sicherung)."""
    with store.lock:
        got = store.load_json(FILE, _empty())
        store.save_json(FILE, dict(got, v=V, games={str(k): {f: v for f, v in e.items() if f in FIELDS}
                                                    for k, e in games.items() if isinstance(e, dict)}))
        _cache["stamp"] = ()


def before_save(col):
    """Beim Schreiben von collection.json: die Nutzerfelder dort auf den Stand von eingaben.json bringen. Maßgeblich
    sind sie dort nicht, aber eine ältere Version (Rückschritt) und eine Sicherung sehen so den neuesten Stand."""
    if exists() and not getattr(_migrating, "on", False):
        overlay(col)
    return col


store.LOAD_HOOKS[COLLECTION] = overlay
store.SAVE_HOOKS[COLLECTION] = before_save


def raw():
    """eingaben.json, wie sie ist (für Sicherung und Statuskarte)."""
    return store.load_json(FILE, _empty())


def migrate(col=None):
    """Umzug aus collection.json (siehe docs/sammlung-felder.md). Gibt True zurück, wenn eingaben.json danach gilt."""
    from . import sicherung, sources
    with store.lock:
        if exists():
            return True
        _migrating.on = True
        try:
            if col is None:
                col = store.load_raw(COLLECTION, {"games": {}})
            found = extract(col)
            before = ""
            if col.get("games"):
                before = sicherung.make("vor-umbau")["file"]
            info = {"at": sicherung._iso(sicherung._now()), "version": sources.VERSION, "games": len(found),
                    "fields": sum(len(e) for e in found.values()), "backup": before}
            store.save_json(FILE, {"v": V, "games": found, "migrated": info})
            _cache["stamp"] = ()
            back = store.load_json(FILE, {})
            if back.get("games") != json.loads(json.dumps(found)):
                raise ValueError("eingaben.json nach dem Schreiben anders als die Felder der Sammlung")
            if found:
                print(f"Nutzereingaben der Sammlung in {FILE} übernommen: {info['games']} Spiele, {info['fields']} Felder"
                      + (f", Sicherung vorher {before}" if before else ""), file=sys.stderr)
            return True
        except Exception as e:
            print(f"Umzug nach {FILE} nicht gelungen ({type(e).__name__}: {e}); die Sammlung bleibt wie bisher", file=sys.stderr)
            store.remove(FILE)
            _cache["stamp"] = ()
            return False
        finally:
            _migrating.on = False
