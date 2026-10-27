"""Datenablage: Titel und Importe (data.json) im Datenordner.

Wie im eShopKompass: jede Datei wird erst vollständig geschrieben und dann umbenannt, und eine
kaputte Datei bleibt daneben liegen, statt still überschrieben zu werden.
"""
import json
import os
import sys
import threading
from datetime import datetime

DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))

# titles: {Schlüssel: Titel}, Form siehe titles.new_title
# imports: {Art: {"at": Zeit, "n": Anzahl, "new": neu angelegt}}
EMPTY_DATA = {"titles": {}, "imports": {}, "marks": {}}     # marks: Mein Stand je Spiel (0.6.0)

lock = threading.RLock()


def _path(name):
    return os.path.join(DATA_DIR, name)


def _load(name, default):
    try:
        with open(_path(name), encoding="utf-8") as f:
            got = json.load(f)
        if type(got) is type(default):
            return got
        why = "falsche Form"
    except FileNotFoundError:
        return json.loads(json.dumps(default))
    except ValueError as e:
        why = str(e)[:80]
    # Kaputte Datei: nicht still durch die Vorgabe ersetzen, sonst überschriebe das nächste
    # Speichern sie endgültig. Sie bleibt daneben liegen, das Protokoll des Containers nennt sie
    keep = f"{_path(name)}.kaputt-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    try:
        os.replace(_path(name), keep)
        print(f"{name} nicht lesbar ({why}), aufgehoben als {os.path.basename(keep)}", file=sys.stderr)
    except OSError:
        pass
    return json.loads(json.dumps(default))


def _save(name, obj):
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = _path(name) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
        f.flush()
        os.fsync(f.fileno())      # erst auf der Platte, dann umbenennen: kein leeres File nach Stromausfall
    os.replace(tmp, _path(name))


def load_data():
    with lock:
        d = _load("data.json", EMPTY_DATA)
        for k, v in EMPTY_DATA.items():
            if not isinstance(d.get(k), type(v)):
                d[k] = json.loads(json.dumps(v))
        return d


def save_data(d):
    with lock:
        _save("data.json", d)


def load_json(name, default):
    """Weitere Dateien im Datenordner: settings.json, history.json, sync.json."""
    with lock:
        return _load(name, default)


def save_json(name, obj):
    with lock:
        _save(name, obj)
