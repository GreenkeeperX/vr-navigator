"""Leistung messen (0.11.1) mit erfundenen Daten, ohne Netz.

- `synthetic(n)`: eine erfundene Sammlung im Aufbau der echten (dieselben Felder je Quelle; Anteile, Namen, Kennungen,
  Texte und Werte sind erfunden). Dient den Messungen hier, dem Leistungstest der Statuskarte und den Tests.
- `python -m app.leistung N`: dasselbe für die Statuskarte in einem eigenen Prozess (siehe `betrieb.start_test`).
- `measure(...)`: misst in einem temporären Datenordner, was die Oberfläche spürt: `/api/collection` kalt und warm,
  `/api/state`, eine Entscheidung zu einem Spiel (Antwort, danach Sammlung und Zustand), Antwortgrößen, Speicher und
  Rechenzeit. Die echten Dateien bleiben
  unberührt; der Abgleich und das Netz werden nicht gebraucht.
"""
import gzip
import json
import os
import random
import resource
import shutil
import tempfile
import time

WORDS = ("Sky", "Garden", "Laser", "Tennis", "Moon", "Rover", "Deep", "Dive", "Comet", "Chase", "Harbor", "Heist", "Pixel",
         "Kart", "Orbit", "Golf", "Star", "Hop", "Lantern", "Keep", "Night", "Tram", "Paper", "Kite", "Iron", "Valley")
GENRES = ("Action", "Adventure", "Puzzle", "Racing", "Shooter", "Strategy", "Simulation", "Sports", "Platform", "Role-playing (RPG)")
SYSTEMS = ("GBA", "SNES", "NES", "N64", "GB", "GBC", "DS", "PS1", "PS2", "PSP", "Mega Drive", "GameCube", "Wii", "3DS")
# Anteile je Quelle (erfunden: viel Retro, viel Playnite, von den übrigen Quellen je etwas)
MIX = (("retro", 0.55), ("playnite", 0.35), ("ggcoll", 0.04), ("steamacct", 0.03), ("pcvr", 0.01), ("eshop", 0.02))


def _text(r, n):
    return " ".join(r.choice(WORDS).lower() for _ in range(n))


def _name(r, i):
    return f"{r.choice(WORDS)} {r.choice(WORDS)} {i}"


def synthetic(n=8000, seed=7):
    """Erfundene Sammlung ({"games": …}) mit n Spielen, dazu data.json mit erfundenen VR-Titeln."""
    r = random.Random(seed)
    games = {}
    kinds = []
    for kind, share in MIX:
        kinds += [kind] * int(round(n * share))
    kinds = (kinds + ["playnite"] * n)[:n]
    r.shuffle(kinds)
    for i, kind in enumerate(kinds):
        name = _name(r, i)
        g = {"name": name, "mp": r.sample(["single", "multi", "coop"], r.randint(0, 2)), "players": r.choice([1, 1, 2, 4]),
             "genres": r.sample(GENRES, r.randint(1, 3)), "released": str(r.randint(1985, 2026)), "added": "",
             "dev": r.choice(WORDS), "score": r.randint(40, 95), "score_src": "IGDB"}
        if r.random() < 0.96:
            g["igdb"] = {"id": 100000 + i, "name": name, "genres": g["genres"], "modes": ["Single player"], "on": 0, "off": 0,
                         "coop_on": False, "coop_off": False, "split": False, "lan": False, "year": g["released"],
                         "desc": _text(r, 80), "at": "2026-11-01", "v": 3}
        if kind == "retro":
            sy = r.choice(SYSTEMS)
            key = f"retro:{sy.lower()}:{name.lower()}"
            g.update(src="retro", system=sy, store="", id="", langs=["En"], files=1, regions=["Europe"], lang_guess=False,
                     flags=[], size=r.randint(1 << 18, 1 << 26), de={"st": r.choice(["ok", "missing", "unknown"])},
                     lr={"n": name, "genre": [r.choice(GENRES)], "users": 1, "dev": r.choice(WORDS), "rel": g["released"]})
            if r.random() < 0.93:
                g["own"] = {"title": name, "series": r.choice(WORDS), "coll": "", "genre": r.choice(GENRES),
                            "folder": sy, "file": name + ".zip"}
            if r.random() < 0.15:
                g["tdb"] = {"id": f"G{i:05d}", "de_t": name, "desc": _text(r, 70), "genre": [r.choice(GENRES)], "at": "2026-11-01", "v": 1}
        else:
            appid = str(4000000 + i)
            key = {"playnite": f"steam:{appid}", "steamacct": f"steam:{appid}", "ggcoll": f"gg:erfunden-{i}",
                   "pcvr": f"pcvr:erfunden-{i}", "eshop": f"eshop:erfunden-{i}"}[kind]
            g.update(store="Steam", id=appid)
            if kind != "playnite":
                g["src"] = kind
            if kind == "eshop":
                g.update(system="Switch", kv={"genre": r.choice(GENRES), "players": 2, "s2": True, "via": _text(r, 60)})
            elif r.random() < 0.85:
                g["steam"] = {"type": "game", "name": name, "genres": g["genres"], "mp": g["mp"], "vr": r.random() < 0.1,
                              "year": g["released"], "recs": r.randint(10, 90000), "mc": None, "desc": _text(r, 45),
                              "date": g["released"], "devs": [g["dev"]], "pubs": [g["dev"]], "langs": 12, "de": True,
                              "ok": True, "at": "2026-11-01"}
                g["rev"] = {"n": r.randint(10, 90000), "pct": r.randint(40, 99), "desc": "Sehr positiv", "at": "2026-11-01"}
                g["stag"] = {"tags": r.sample(WORDS, 8), "at": "2026-11-01", "v": 1}
                g["pcgw"] = {"ok": True, "page": True, "mod": [], "native": [], "vorpx": False, "mp": [], "pl": {}, "coop": [], "v": 2, "at": "2026-11-01"}
                g["nexus"] = {"none": True, "at": "2026-11-01", "v": 1}
                if r.random() < 0.7:
                    g["play"] = {"now": r.randint(0, 5000), "at": "2026-11-01"}
        games[key] = g
    data = {"titles": {f"t{i}": {"name": _name(r, 90000 + i), "wish": i % 3 == 0, "owned": {}, "links": {}, "aliases": []}
                       for i in range(min(400, n // 20 + 1))},
            "imports": {}, "marks": {}}
    return {"games": games, "at": "2026-11-01", "n": len(games)}, data


def _rss_mb():
    return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)


def _cpu():
    t = os.times()
    return t.user + t.system


def measure(n=8000, rounds=3):
    """Messung im temporären Datenordner (die Module schalten store.DATA_DIR um und zurück). Gibt die Werte zurück.
    Nur aufrufen, wenn kein Abgleich läuft: der Datenordner gilt prozessweit."""
    from . import collection, eingaben, retro, server, store
    old_dir = store.DATA_DIR
    tmp = tempfile.mkdtemp(prefix="vr-navigator-leistung-")
    out = {"n": n, "rss_start_mb": _rss_mb()}
    cpu0, t_all = _cpu(), time.monotonic()
    try:
        store.DATA_DIR = tmp
        col, data = synthetic(n)
        store.save_data(data)
        t = time.monotonic()
        store.save_json(collection.FILE, col)
        out["write_collection_s"] = round(time.monotonic() - t, 3)
        out["collection_bytes"] = os.path.getsize(os.path.join(tmp, collection.FILE))
        t = time.monotonic()
        col = store.load_json(collection.FILE, collection.EMPTY)       # mit Umzug (leer)
        out["load_collection_s"] = round(time.monotonic() - t, 3)
        server._memo.clear()
        t = time.monotonic()
        raw, packed, _ = server.collection_body()
        out["api_collection_cold_s"] = round(time.monotonic() - t, 3)
        t = time.monotonic()
        server.collection_body()
        out["api_collection_warm_s"] = round(time.monotonic() - t, 4)
        out["api_collection_bytes"], out["api_collection_gzip_bytes"] = len(raw), len(packed)
        t = time.monotonic()
        st = server.state()
        out["api_state_cold_s"] = round(time.monotonic() - t, 3)
        body = json.dumps(st, ensure_ascii=False).encode("utf-8")
        out["api_state_bytes"], out["api_state_gzip_bytes"] = len(body), len(gzip.compress(body, 5))
        t = time.monotonic()
        server.state()
        out["api_state_warm_s"] = round(time.monotonic() - t, 4)
        # eine Entscheidung: „DE fehlt“ ignorieren, genau wie POST /api/retro/de (mit der Antwort), dann die Sammlung
        # und der Zustand, wie der nächste Abruf sie braucht
        keys = [k for k, g in col["games"].items() if g.get("src") == "retro"][:rounds]
        took, after, st_after, sizes = [], [], [], []
        for k in keys:
            t = time.monotonic()
            with store.lock:
                c = store.load_json(collection.FILE, collection.EMPTY)
                before = store.stamp(*server.COL_FILES)
                retro.settle_de(c, [k], True)
                eingaben.save(c, [k])
                rows = server.decided(c, [k], before)
            sizes.append(len(json.dumps({"retro_de": retro.de_list(c), "rows": rows}, ensure_ascii=False).encode("utf-8")))
            took.append(time.monotonic() - t)
            t = time.monotonic()
            server.collection_body()
            after.append(time.monotonic() - t)
            t = time.monotonic()
            server.state()
            st_after.append(time.monotonic() - t)
        avg = lambda xs, nd=3: round(sum(xs) / len(xs), nd) if xs else None
        out["decision_write_s"] = avg(took)
        out["decision_response_bytes"] = avg(sizes, 0)
        out["decision_then_collection_s"] = avg(after)
        out["decision_then_state_s"] = avg(st_after)
        out["eingaben_bytes"] = os.path.getsize(os.path.join(tmp, eingaben.FILE)) if eingaben.exists() else 0
    finally:
        store.DATA_DIR = old_dir
        server._memo.clear()
        shutil.rmtree(tmp, ignore_errors=True)
    out["took_s"] = round(time.monotonic() - t_all, 2)
    out["cpu_s"] = round(_cpu() - cpu0, 2)
    out["rss_peak_mb"] = _rss_mb()
    return out


def _no_net(*a, **kw):
    raise RuntimeError("Der Leistungstest fragt kein Netz an")


def main(argv):
    """Für den Leistungstest der Statuskarte (betrieb.start_test): in einem eigenen Prozess mit DATA_DIR in einem
    temporären Ordner, niedriger Priorität und ohne Netz; schreibt das Ergebnis als eine Zeile JSON."""
    from . import sources
    sources.request = sources.fetch = _no_net
    try:
        os.nice(10)             # der Server bleibt bedienbar, solange der Test rechnet
    except OSError:
        pass
    n = int(argv[0]) if argv else 8000
    print(json.dumps(measure(max(100, min(30000, n)))), flush=True)


if __name__ == "__main__":
    import sys
    main(sys.argv[1:])
