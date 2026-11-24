"""Datenablage: Titel und Importe (data.json) im Datenordner.

Wie im eShopKompass: jede Datei wird erst vollständig geschrieben und dann umbenannt, und eine
kaputte Datei bleibt daneben liegen, statt still überschrieben zu werden.
"""
import json
import math
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
    with lock:
        keep = f"{_path(name)}.kaputt-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        try:
            os.replace(_path(name), keep)
            print(f"{name} nicht lesbar ({why}), aufgehoben als {os.path.basename(keep)}", file=sys.stderr)
        except OSError:
            pass
    return json.loads(json.dumps(default))


def finite(obj):
    """Kopie ohne NaN und Unendlich (0.10.29): solche Zahlen werden zu None. JSON kennt sie nicht, und eine
    Rechnung damit gibt still falsche Ergebnisse. Bei sauberen Daten kostet das nur den schnellen Versuch in _save."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: finite(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [finite(v) for v in obj]
    return obj


def _save(name, obj):
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        text = json.dumps(obj, ensure_ascii=False, indent=1, allow_nan=False)
    except ValueError:
        print(f"{name}: Zahl ohne Wert (NaN oder unendlich) als leer gespeichert", file=sys.stderr)
        text = json.dumps(finite(obj), ensure_ascii=False, indent=1, allow_nan=False)
    tmp = _path(name) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())      # erst auf der Platte, dann umbenennen: kein leeres File nach Stromausfall
    os.replace(tmp, _path(name))


def load_data():
    # Lesen ohne Schloss (0.10.29): geschrieben wird immer erst in .tmp und dann umbenannt, ein Leser sieht also
    # die alte oder die neue Datei, nie eine halbe. Wer ändert, hält das Schloss vom Lesen bis zum Schreiben
    d = _load("data.json", EMPTY_DATA)
    for k, v in EMPTY_DATA.items():
        if not isinstance(d.get(k), type(v)):
            d[k] = json.loads(json.dumps(v))
    return d


def save_data(d):
    with lock:
        _save("data.json", d)


def load_json(name, default):
    """Weitere Dateien im Datenordner: settings.json, history.json, sync.json. Ohne Schloss, siehe load_data."""
    return _load(name, default)


def stamp(*names):
    """Stand der Dateien (Änderungszeit und Größe) zum Zwischenspeichern daraus berechneter Antworten (0.8.14)."""
    out = []
    for n in names:
        try:
            st = os.stat(_path(n))
            out.append((st.st_mtime_ns, st.st_size))
        except OSError:
            out.append(None)
    return tuple(out)


def save_json(name, obj):
    with lock:
        _save(name, obj)
