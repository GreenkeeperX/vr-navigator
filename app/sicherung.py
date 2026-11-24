"""Sicherungen im Datenordner und Wiederherstellen (0.10.29), ohne Netz.

- `make`: alles, was die Sicherung zum Herunterladen enthält (Titel, Mein Stand, Sammlung, PC-Wunschliste), gepackt
  unter sicherungen/ im Datenordner. Einmal am Tag von selbst (`daily`), außerdem vor jedem Wiederherstellen und vor
  Umbauten der Ablage. Es bleiben die neuesten KEEP Dateien.
- `plan` und `restore`: eine Sicherung feldweise einspielen, erst als Vorschau. Was in der Sicherung fehlt, bleibt
  wie es ist; was nicht die erwartete Form hat, wird nicht übernommen und steht in der Vorschau.
- `check`: Wiederherstellungstest (monatlich von selbst, `check_due`): die jüngste Sicherung in einen temporären
  Ordner auspacken, prüfen und mit den Rechnungen der Oberfläche durchrechnen. Die echten Dateien bleiben unberührt.

Der Stand (letzte Sicherung, letzter Test) steht in sicherung.json.
"""
import gzip
import json
import math
import os
import re
import shutil
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone

from . import collection, eingaben, pcwish, sources, store

DIR = "sicherungen"
STATE = "sicherung.json"
KEEP = 14                   # neueste Dateien, die bleiben (bei täglicher Sicherung gut zwei Wochen)
DAILY_H = 20                # tägliche Sicherung, wenn die letzte so lange her ist
CHECK_DAYS = 30             # Wiederherstellungstest so oft
_lock = threading.RLock()
NAME = re.compile(r"^vr-navigator-(\d{8}-\d{6})-([a-z-]+)\.json\.gz$")


def _now():
    return datetime.now(timezone.utc)


def _iso(at):
    return at.isoformat(timespec="seconds")


def folder():
    return os.path.join(store.DATA_DIR, DIR)


def state():
    return store.load_json(STATE, {})


def _set_state(**kw):
    with store.lock:
        st = state()
        st.update(kw)
        store.save_json(STATE, st)


def snapshot():
    """Die Teile der Sicherung, wie /api/export sie liefert."""
    return {"app": "vr-navigator", "version": sources.VERSION, "at": _iso(_now()), "data": store.load_data(),
            "collection": store.load_json(collection.FILE, collection.EMPTY), "pcwish": store.load_json(pcwish.FILE, pcwish.EMPTY),
            # 0.11.0: Nutzereingaben extra; die Sammlung oben enthält sie zusammengeführt (für ältere Versionen)
            "eingaben": eingaben.raw()}


def counts(snap):
    d, c, p = snap.get("data") or {}, snap.get("collection") or {}, snap.get("pcwish") or {}
    return {"titles": len(d.get("titles") or {}), "marks": len(d.get("marks") or {}),
            "games": len(c.get("games") or {}), "pcwish": len(p.get("items") or {}),
            "eingaben": len((snap.get("eingaben") or {}).get("games") or {})}


def files():
    """Sicherungen im Ordner, neueste zuerst: [{file, at, why, bytes}]."""
    try:
        names = os.listdir(folder())
    except OSError:
        return []
    out = []
    for n in names:
        m = NAME.match(n)
        if not m:
            continue
        try:
            size = os.path.getsize(os.path.join(folder(), n))
        except OSError:
            continue
        at = datetime.strptime(m.group(1), "%Y%m%d-%H%M%S").replace(tzinfo=timezone.utc)
        out.append({"file": n, "at": _iso(at), "why": m.group(2), "bytes": size})
    return sorted(out, key=lambda x: x["file"], reverse=True)


def make(why="taeglich"):
    """Sicherung schreiben (erst .tmp, dann umbenennen) und alte über KEEP löschen. Gibt die Angaben zurück."""
    why = re.sub(r"[^a-z-]", "", why.lower())[:30] or "hand"
    if not eingaben.exists() and not eingaben.migrating():
        eingaben.migrate()            # 0.11.0: erst der Umzug (er sichert selbst), dann diese Sicherung
    with store.lock, _lock:          # immer erst store.lock, dann _lock (der Umzug sichert unter store.lock)
        snap = snapshot()
        raw = json.dumps(snap, ensure_ascii=False, allow_nan=False).encode("utf-8")
        os.makedirs(folder(), exist_ok=True)
        at = _now()
        name = f"vr-navigator-{at.strftime('%Y%m%d-%H%M%S')}-{why}.json.gz"
        path = os.path.join(folder(), name)
        tmp = path + ".tmp"
        with open(tmp, "wb") as f:
            f.write(gzip.compress(raw, compresslevel=6))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        for old in files()[KEEP:]:
            try:
                os.remove(os.path.join(folder(), old["file"]))
            except OSError:
                pass
        info = {"file": name, "at": _iso(at), "why": why, "bytes": os.path.getsize(path), "raw": len(raw),
                "version": sources.VERSION, **counts(snap)}
        _set_state(last=info)
        return info


def read(name):
    """Eine Sicherung aus dem Ordner lesen (nur Namen aus files(), kein Pfad)."""
    if not NAME.match(str(name or "")):
        raise ValueError("Unbekannte Sicherung")
    with open(os.path.join(folder(), name), "rb") as f:
        return loads(gzip.decompress(f.read()).decode("utf-8"))


def _no_const(c):
    raise ValueError("Nur endliche Zahlen (kein NaN oder Infinity)")


def loads(text):
    """JSON ohne NaN und Unendlich: json.loads nähme sie sonst stillschweigend an."""
    return json.loads(text, parse_constant=_no_const)


def finite(obj):
    """Gibt es irgendwo NaN oder unendlich?"""
    if isinstance(obj, float):
        return math.isfinite(obj)
    if isinstance(obj, dict):
        return all(finite(v) for v in obj.values())
    if isinstance(obj, list):
        return all(finite(v) for v in obj)
    return True


def daily():
    """Tägliche Sicherung, wenn die letzte älter als DAILY_H ist. Gibt die neue zurück oder None."""
    last = files()
    if last and _now() - datetime.fromisoformat(last[0]["at"]) < timedelta(hours=DAILY_H):
        return None
    return make("taeglich")


# ---- Wiederherstellen ----

def _part(name, got, key, what):
    """Ein Teil der Sicherung (data, collection, pcwish): nur Einträge mit Namen. Gibt (Teil, Bericht)."""
    rep = {"take": False, "n": 0, "dropped": 0, "why": ""}
    if got is None:
        rep["why"] = "nicht in der Sicherung, bleibt wie es ist"
        return None, rep
    if not isinstance(got, dict) or not isinstance(got.get(key), dict):
        rep["why"] = f"keine {what} in erwarteter Form, bleibt wie es ist"
        return None, rep
    good = {str(k)[:300]: e for k, e in got[key].items() if isinstance(e, dict) and isinstance(e.get("name"), str) and e["name"].strip()}
    rep.update(take=True, n=len(good), dropped=len(got[key]) - len(good))
    return dict(got, **{key: good}), rep


def plan(body):
    """Vorschau: was aus der Sicherung übernommen würde, je Teil und je Feld von data.json. Fehler als ValueError."""
    d = body.get("data")
    if not isinstance(d, dict) or not isinstance(d.get("titles"), dict):
        raise ValueError("Keine Sicherung des VR-Navigator")
    if not finite(body):
        raise ValueError("Die Sicherung enthält Zahlen ohne Wert (NaN oder unendlich), nicht übernommen")
    bad = [k for k, t in d["titles"].items() if not isinstance(t, dict) or not t.get("name")]
    if bad:
        raise ValueError(f"{len(bad)} Einträge ohne Namen, Sicherung nicht übernommen")
    now = store.load_data()
    fields, skipped = {}, []
    for k, v in d.items():
        want = type(store.EMPTY_DATA[k]) if k in store.EMPTY_DATA else type(now[k]) if k in now and now[k] is not None else None
        if want is not None and v is not None and not isinstance(v, want):
            skipped.append(k)          # falsche Form: das Feld bleibt wie es ist
            continue
        fields[k] = v
    col, col_rep = _part("collection", body.get("collection"), "games", "Sammlung")
    pw, pw_rep = _part("pcwish", body.get("pcwish"), "items", "PC-Wunschliste")
    # Nutzereingaben (0.11.0): aus der Sicherung, sonst aus den Spielen ihrer Sammlung (Sicherungen vor 0.11.0)
    ein = body.get("eingaben")
    if isinstance(ein, dict) and isinstance(ein.get("games"), dict):
        user = {str(k)[:300]: e for k, e in ein["games"].items() if isinstance(e, dict)}
        ein_rep = {"take": True, "n": len(user), "dropped": len(ein["games"]) - len(user), "why": "aus der Sicherung"}
    elif col is not None:
        user = eingaben.extract(col)
        ein_rep = {"take": True, "n": len(user), "dropped": 0, "why": "aus der Sammlung der Sicherung"}
    else:
        user, ein_rep = None, {"take": False, "n": 0, "dropped": 0, "why": "nicht in der Sicherung, bleibt wie es ist"}
    cur_col = store.load_json(collection.FILE, collection.EMPTY)
    cur_pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
    report = {
        "version": str(body.get("version") or "")[:20],
        "data": {"fields": sorted(fields), "kept": sorted(k for k in now if k not in fields), "skipped": sorted(skipped),
                 "titles": len(d["titles"]), "titles_now": len(now["titles"]),
                 "marks": len(fields.get("marks") or {}) if "marks" in fields else None, "marks_now": len(now["marks"])},
        "collection": dict(col_rep, now=len(cur_col.get("games") or {})),
        "pcwish": dict(pw_rep, now=len(cur_pw.get("items") or {})),
        "eingaben": dict(ein_rep, now=len(eingaben.raw().get("games") or {})),
    }
    return report, {"data": fields, "collection": col, "pcwish": pw, "eingaben": user}


def restore(body, dry=True):
    """Sicherung einspielen: erst Vorschau (dry), sonst vorher eine Sicherung des jetzigen Stands, dann feldweise.
    Gibt den Bericht zurück, mit dem Namen der Sicherung vorher (before)."""
    report, parts = plan(body)
    if dry:
        return dict(report, dry=True)
    with store.lock:
        before = make("vor-wiederherstellung")
        data = store.load_data()
        data.update(parts["data"])          # Felder, die die Sicherung nicht kennt, bleiben
        store.save_data(data)
        if parts["eingaben"] is not None:
            eingaben.replace(parts["eingaben"])         # vor der Sammlung: deren Haken setzt die Nutzerfelder von hier
        if parts["collection"] is not None:
            cur = store.load_json(collection.FILE, collection.EMPTY)
            new = dict(cur, **parts["collection"])
            new["n"] = len(new["games"])
            store.save_json(collection.FILE, new)
        if parts["pcwish"] is not None:
            cur = store.load_json(pcwish.FILE, pcwish.EMPTY)
            store.save_json(pcwish.FILE, dict(cur, **parts["pcwish"]))
    _set_state(restored={"at": _iso(_now()), "before": before["file"], "version": report["version"]})
    return dict(report, dry=False, before=before["file"])


# ---- Wiederherstellungstest ----

def check_due():
    last = (state().get("check") or {}).get("at")
    try:
        return _now() - datetime.fromisoformat(last) >= timedelta(days=CHECK_DAYS)
    except (TypeError, ValueError):
        return True


def check(name=None):
    """Jüngste (oder genannte) Sicherung in einen temporären Ordner auspacken, die Dateien dort schreiben und mit
    den Lesern der Ablage und den Rechnungen der Oberfläche durchrechnen. Echte Dateien bleiben unberührt; das
    Ergebnis steht in sicherung.json unter check."""
    from . import library          # erst hier: library zieht viele Module, die Sicherung selbst braucht sie nicht
    t0 = time.monotonic()
    res = {"at": _iso(_now()), "ok": False, "file": "", "error": "", "counts": {}, "version": sources.VERSION}
    tmp = tempfile.mkdtemp(prefix="vr-navigator-test-")
    try:
        name = name or (files()[0]["file"] if files() else "")
        if not name:
            raise ValueError("keine Sicherung vorhanden")
        res["file"] = name
        snap = read(name)
        report, parts = plan(snap)
        if report["collection"]["dropped"] or report["pcwish"]["dropped"]:
            raise ValueError("Einträge ohne Namen in der Sicherung")
        # wie beim Wiederherstellen: Dateien schreiben und wieder lesen, aber im temporären Ordner
        files_ = (("data.json", snap["data"]), (collection.FILE, snap.get("collection") or collection.EMPTY),
                  (pcwish.FILE, snap.get("pcwish") or pcwish.EMPTY), (eingaben.FILE, snap.get("eingaben") or {"games": {}}))
        for fname, obj in files_:
            with open(os.path.join(tmp, fname), "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False, allow_nan=False)
        back = {}
        for fname, _ in files_:
            with open(os.path.join(tmp, fname), encoding="utf-8") as f:
                back[fname] = loads(f.read())
        data = json.loads(json.dumps(store.EMPTY_DATA))
        data.update(back["data.json"])
        got = {"titles": len(data["titles"]), "marks": len(data.get("marks") or {}),
               "games": len(back[collection.FILE].get("games") or {}), "pcwish": len(back[pcwish.FILE].get("items") or {}),
               "eingaben": len(back[eingaben.FILE].get("games") or {})}
        if got != counts(snap):
            raise ValueError(f"Anzahl nach dem Lesen anders: {got} statt {counts(snap)}")
        # nutzbar: dieselben Rechnungen wie die Oberfläche
        view = collection.view(back[collection.FILE], data)
        library.view(data)
        pcwish.view(data)
        if len(view.get("games") or []) < got["games"] * 0.5 and got["games"] > 20:
            raise ValueError("Sammlung nach dem Rechnen unvollständig")
        res.update(ok=True, counts=got, backup_version=snap.get("version") or "")
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        print("Wiederherstellungstest:", res["error"], file=sys.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    res["took_s"] = round(time.monotonic() - t0, 2)
    _set_state(check=res)
    return res
