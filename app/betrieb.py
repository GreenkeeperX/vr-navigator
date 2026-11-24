"""Statuskarte im Einstellungsreiter (0.11.2, V-5): Zustand des Betriebs auf einen Blick, ohne Netz.

- `view(n_games)`: Gesamtstatus (ok, Hinweis, Problem mit Gründen), ruhende Server und die letzten Sperren, die
  letzten Läufe mit Problemen, Größe der Daten, Speicher des Prozesses, freier Platz, Version, letzte Sicherung,
  letzter Wiederherstellungstest und die Ergebnisse des Leistungstests.
- `start_test(n)`: Leistungstest nur auf Klick, nie während eines Abgleichs. Er läuft in einem eigenen Prozess mit
  einem temporären Datenordner und erfundenen Daten (`python -m app.leistung`), ohne Netz, ohne Docker und ohne
  Neustart; das Ergebnis steht mit Version und Zeit in leistung.json.
"""
import json
import os
import resource
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta, timezone

from . import ruhe, sicherung, sources, store, sync

FILE = "leistung.json"
KEEP = 10                   # so viele Ergebnisse des Leistungstests bleiben
TEST_TIMEOUT_S = 1200
DISK_LOW_MB = 2000          # darunter ein Hinweis
DISK_BAD_MB = 500           # darunter ein Problem
BACKUP_OLD_H = 72           # tägliche Sicherung älter: Problem
CHECK_OLD_D = 45            # Wiederherstellungstest älter (monatlich fällig): Hinweis
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_test = {"running": False, "started": ""}
_test_lock = threading.Lock()


def _now():
    return datetime.now(timezone.utc)


def _iso(at):
    return at.isoformat(timespec="seconds")


def _age(iso, at):
    try:
        return at - datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def _rss_mb():
    """Speicher des Prozesses jetzt (Linux), sonst None."""
    try:
        with open("/proc/self/status", encoding="ascii") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return round(int(line.split()[1]) / 1024, 1)
    except (OSError, ValueError):
        pass
    return None


def data_files():
    """Dateien im Datenordner mit Größe, größte zuerst; der Ordner der Sicherungen als ein Eintrag."""
    out = []
    try:
        names = os.listdir(store.DATA_DIR)
    except OSError:
        return out
    for n in names:
        p = os.path.join(store.DATA_DIR, n)
        if os.path.isfile(p):
            out.append({"name": n, "bytes": os.path.getsize(p)})
        elif n == sicherung.DIR and os.path.isdir(p):
            out.append({"name": n + "/", "bytes": sum(x.get("bytes") or 0 for x in sicherung.files()),
                        "n": len(sicherung.files())})
    return sorted(out, key=lambda x: -x["bytes"])


def results():
    got = store.load_json(FILE, {})
    return [x for x in (got.get("results") or []) if isinstance(x, dict)]


def test_running():
    return _test["running"]


def overall(v, sy, at=None):
    """Gesamtstatus aus der Ansicht: (Stufe, Probleme, Hinweise). Stufe „ok“, „hinweis“ oder „problem“."""
    at = at or _now()
    bad, hint = [], []
    if not v["data_ok"]:
        bad.append("Datenordner nicht beschreibbar")
    free = (v.get("disk") or {}).get("free_mb")
    if free is not None and free < DISK_BAD_MB:
        bad.append(f"nur noch {free} MB frei")
    elif free is not None and free < DISK_LOW_MB:
        hint.append(f"nur noch {free} MB frei")
    chk = (v.get("backup") or {}).get("check") or {}
    if chk and chk.get("ok") is False:
        bad.append("Wiederherstellungstest fehlgeschlagen")
    elif v["has_data"]:
        age = _age(chk.get("at"), at)
        if age is None:
            hint.append("noch kein Wiederherstellungstest")
        elif age > timedelta(days=CHECK_OLD_D):
            hint.append("Wiederherstellungstest älter als " + str(CHECK_OLD_D) + " Tage")
    last = (v.get("backup") or {}).get("last") or {}
    if v["has_data"]:
        age = _age(last.get("at"), at)
        if age is None:
            bad.append("noch keine Sicherung")
        elif age > timedelta(hours=BACKUP_OLD_H):
            bad.append("letzte Sicherung älter als drei Tage")
    if sy.get("error") and not sy.get("running"):
        bad.append(f"letzter Abgleich abgebrochen ({sy['error']})")
    if sy.get("interrupted"):
        hint.append("letzter Abgleich unterbrochen, wird nachgeholt")
    if v["resting"]:
        hint.append(f"{len(v['resting'])} {'Server ruht' if len(v['resting']) == 1 else 'Server ruhen'}")
    src = sy.get("sources") or {}
    probs = sorted(sync.NAMES.get(k, k) for k, r in src.items()
                   if isinstance(r, dict) and r.get("ok") is False and not r.get("manual") and r.get("msg") != "ruht")
    if probs:
        hint.append("Problem bei " + ", ".join(probs))
    level = "problem" if bad else "hinweis" if hint else "ok"
    return level, bad, hint


def view(n_games=0, at=None):
    at = at or _now()
    sy = sync.status()
    try:
        du = shutil.disk_usage(store.DATA_DIR)
        disk = {"free_mb": du.free // (1 << 20), "total_mb": du.total // (1 << 20)}
    except OSError:
        disk = {}
    files = data_files()
    bst = sicherung.state()
    v = {"version": sources.VERSION, "at": _iso(at),
         "data_ok": os.path.isdir(store.DATA_DIR) and os.access(store.DATA_DIR, os.W_OK),
         "has_data": any(f["name"] in ("data.json", "collection.json") for f in files),
         "disk": disk, "files": files, "data_bytes": sum(f["bytes"] for f in files),
         "memory": {"rss_mb": _rss_mb(), "peak_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)},
         "backup": {"last": bst.get("last") or {}, "n": len(sicherung.files()), "check": bst.get("check") or {},
                    "restored": bst.get("restored") or {}},
         "resting": [dict(e, host=h) for h, e in sorted((sy.get("resting") or {}).items())],
         "blocks": ruhe.history()[-10:][::-1],
         "runs": [r for r in (sy.get("runs") or []) if isinstance(r, dict)][-10:][::-1],
         "sync_running": bool(sy.get("running")), "games": n_games,
         "leistung": {"running": _test["running"], "started": _test["started"], "results": results()[::-1],
                      "n": test_size(n_games)}}
    v["level"], v["problems"], v["hints"] = overall(v, sy, at)
    return v


def test_size(n_games):
    """Größe der erfundenen Sammlung: so groß wie deine, auf Tausend aufgerundet (1000 bis 30000)."""
    n = -(-int(n_games or 0) // 1000) * 1000
    return min(30000, max(1000, n))


def start_test(n_games=0):
    """Leistungstest im Hintergrund starten. Fehler (ValueError), wenn ein Abgleich oder schon ein Test läuft."""
    if sync.status_running():
        raise ValueError("Während eines Abgleichs nicht; der Test misst sonst den Abgleich mit")
    with _test_lock:
        if _test["running"]:
            raise ValueError("Der Leistungstest läuft schon")
        _test.update(running=True, started=_iso(_now()))
        sync.leistung_running.set()
    threading.Thread(target=_run, args=(test_size(n_games),), daemon=True).start()
    return True


def _run(n):
    res = {"at": _iso(_now()), "version": sources.VERSION, "n": n, "ok": False, "error": ""}
    tmp = tempfile.mkdtemp(prefix="vr-navigator-leistung-")
    t0 = time.monotonic()
    try:
        env = {k: v for k, v in os.environ.items() if k in ("PATH", "LANG", "LC_ALL", "PYTHONPATH", "TZ")}
        env.update(DATA_DIR=tmp, AUTO_SYNC="0", PYTHONDONTWRITEBYTECODE="1")
        proc = subprocess.run([sys.executable, "-m", "app.leistung", str(n)], cwd=ROOT, env=env, capture_output=True,
                              text=True, timeout=TEST_TIMEOUT_S)
        lines = [x for x in proc.stdout.strip().splitlines() if x.startswith("{")]
        if proc.returncode != 0 or not lines:
            raise RuntimeError((proc.stderr.strip().splitlines() or ["ohne Ausgabe"])[-1][:160])
        got = json.loads(lines[-1])
        res.update({k: v for k, v in got.items() if isinstance(v, (int, float)) and k != "n"}, ok=True)
    except subprocess.TimeoutExpired:
        res["error"] = f"nach {TEST_TIMEOUT_S // 60} Minuten abgebrochen"
    except Exception as e:
        res["error"] = f"{type(e).__name__}: {str(e)[:160]}"
        print("Leistungstest:", res["error"], file=sys.stderr)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        res["wall_s"] = round(time.monotonic() - t0, 1)
        try:
            with store.lock:
                store.save_json(FILE, {"results": (results() + [res])[-KEEP:]})
        finally:
            _test.update(running=False, started="")
            sync.leistung_running.clear()
    return res

