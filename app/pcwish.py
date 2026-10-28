"""PC-Wunschliste (0.8.2): die ganze Wunschliste von gg.deals, nicht nur die VR-Titel.

gg.deals bleibt führend (Entscheidung 27.10.2026): Das Tool spiegelt die Liste, ordnet jedem Spiel eine
Steam-ID zu und holt dazu die Preise über die gg.deals-API, wie der eShopKompass zu DekuDeals. Abgelegt in
pcwish.json im Datenordner; eine neue Liste behält Steam-ID und Preise je Spiel.
"""
from . import collection, store, titles

FILE = "pcwish.json"
EMPTY = {"items": {}, "at": "", "via": ""}
NEAR = 0.05         # bis 5 % über dem bisherigen Tief gilt als „nah am Tief“


KINDS = {"pack": "Paket", "dlc": "DLC"}


def _key(it):
    if it.get("kind"):
        return f"{it['kind']}:{it['slug']}"     # 0.8.7: Pakete und DLC, eigene Adresse bei gg.deals
    return it["slug"] if it.get("slug") else "name:" + titles.norm(it["name"])


def replace(items, via, stamp=None):
    """Neue Liste übernehmen. Bekanntes (Steam-ID, Suche, Preise) bleibt je Spiel. Liefert (neu, weg)."""
    stamp = stamp or titles.now_iso()
    with store.lock:
        pw = store.load_json(FILE, EMPTY)
        old = pw.get("items") or {}
        new = {}
        for it in items:
            k = _key(it)
            e = dict(old.get(k) or {}, name=str(it["name"])[:200], slug=it.get("slug") or "")
            if it.get("kind"):
                e["kind"] = it["kind"]
            e.setdefault("since", stamp)
            new[k] = e
        added = [e["name"] for k, e in new.items() if k not in old]
        gone = [e["name"] for k, e in old.items() if k not in new]
        store.save_json(FILE, {"items": new, "at": stamp, "via": via})
    return added, gone


def steam_index(data, col):
    """Steam-ID je Name aus dem, was das Tool schon kennt: Titel mit sicherer Steam-ID, Steam-Spiele der Sammlung."""
    out = {}
    for t in data["titles"].values():
        if t.get("steam_appid") and t.get("steam_sure"):
            out.setdefault(titles.norm(t["name"]), str(t["steam_appid"]))
    for g in (col.get("games") or {}).values():
        if g.get("store") == "Steam" and str(g.get("id") or "").isdigit():
            out.setdefault(titles.norm(g["name"]), str(g["id"]))
    return out


def _vr_keys(data, col=None):
    """Steam-IDs und Namen der VR-Titel im Tool (Marke „VR“ in der PC-Liste), ab 0.8.7 auch Steam-Apps, die die
    VR-Prüfung im Store oder die Steam-Details als VR kennen."""
    ids, names = set(), set()
    for t in data["titles"].values():
        if t.get("steam_appid"):
            ids.add(str(t["steam_appid"]))
        names.add(titles.base_norm(t["name"]))
    ids |= {a for a, x in (data.get("steam_apps") or {}).items() if (x or {}).get("vr")}
    for g in ((col or {}).get("games") or {}).values():
        if g.get("store") == "Steam" and (g.get("steam") or {}).get("vr"):
            ids.add(str(g.get("id")))
    return ids, names


INFO = ("genres", "gc", "gx", "mp", "mpc", "players", "pl_src", "score", "score_src", "score_alt", "reviews", "rdesc",
        "hours", "hours_all", "hours_src", "year", "year_src", "desc", "desc_lang", "dev", "pub", "gem", "gem_guess", "srcs",
        "src", "ig", "year_ok", "syear", "iyear", "icrit", "sdate", "desc_src", "iname")


def info(e):
    """Spielinfos (0.8.11) wie in der Sammlung: Steam-Rezensionen, Steam-Details und IGDB nach denselben Regeln
    (collection.check, collection.merge_igdb). Leer, solange der Abgleich nichts gelesen hat."""
    st, rev, ig = e.get("steam") or {}, e.get("rev") or {}, e.get("igdb") or {}
    if not st.get("ok") and not isinstance(rev.get("n"), int) and not ig.get("id"):
        return {}
    r = {"name": e["name"], "system": "PC", "mp": [], "players": 0, "genres": [], "score": None, "score_src": "",
         "year": "", "dev": "", "pub": ""}
    r["reviews"] = rev.get("n") if isinstance(rev.get("n"), int) else None
    r["rdesc"] = rev.get("desc") or ""
    if r["reviews"] is not None and r["reviews"] >= 50 and rev.get("pct") is not None:
        r["score"], r["score_src"] = rev["pct"], "Steam"
    r["gem"], r["gem_guess"] = collection.gem(e)
    collection.check(r, st)
    # Ohne Playnite kommen Genre und Mehrspieler nur von Steam: Steam allein gilt dann als bestätigt
    if r["src"] == "steam":
        r["gc"], r["mpc"] = list(r["genres"]), list(r["mp"])
    r["srcs"] = ["Steam"] if r["src"] == "steam" or r["reviews"] is not None else []
    if ig.get("id"):
        collection.merge_igdb(r, ig)
    out = {f: r[f] for f in INFO if r.get(f) not in (None, "", [])}
    out["svr"] = bool(st.get("vr"))
    return out


def view(data, col=None):
    """Zeilen für den Unterreiter PC der Wunschliste."""
    pw = store.load_json(FILE, EMPTY)
    col = col if col is not None else store.load_json(collection.FILE, collection.EMPTY)
    owned = {str(g.get("id")) for g in (col.get("games") or {}).values() if g.get("store") == "Steam"}
    owned_names = {titles.norm(g["name"]) for g in (col.get("games") or {}).values() if (g.get("system") or "PC") == "PC"}
    vr_ids, vr_names = _vr_keys(data, col)
    rows = []
    for k, e in (pw.get("items") or {}).items():
        gg = e.get("gg") or {}
        cands = [(gg.get("retail"), "Händler"), (gg.get("keyshops"), "Keyshop")]
        best = min((c for c in cands if c[0] is not None), default=(None, ""))
        lows = [x for x in (gg.get("retail_low"), gg.get("keyshops_low")) if x is not None]
        low = min(lows) if lows else None
        kind = e.get("kind") or ""
        inf = info(e)
        vr = (bool(e.get("appid") and e["appid"] in vr_ids) or titles.base_norm(e["name"]) in vr_names
              or inf.pop("svr", False))
        r = {"key": k, "name": e["name"], "slug": e.get("slug") or "", "appid": e.get("appid") or "", "kind": kind,
             "url": gg.get("url") or (f"https://gg.deals/{kind or 'game'}/{e['slug']}/" if e.get("slug") else ""),
             "retail": gg.get("retail"), "keyshops": gg.get("keyshops"), "retail_low": gg.get("retail_low"),
             "keyshops_low": gg.get("keyshops_low"), "best": best[0], "best_from": best[1], "low": low,
             "price_at": gg.get("at") or "", "since": e.get("since") or "",
             "vr": vr or collection.vr_name(e["name"]), "vr_guess": not vr and collection.vr_name(e["name"]),
             "owned": bool(e.get("appid") and e["appid"] in owned) or titles.norm(e["name"]) in owned_names, **inf}
        if best[0] is not None and low is not None:
            r["over"] = round((best[0] - low) / low, 3) if low > 0 else 0.0
            r["near"] = best[0] <= low * (1 + NEAR) + 0.005
        rows.append(r)
    rows.sort(key=lambda r: titles.norm(r["name"]))
    return {"at": pw.get("at") or "", "via": pw.get("via") or "", "n": len(rows), "rows": rows,
            "priced": sum(1 for r in rows if r["best"] is not None), "info": sum(1 for r in rows if r.get("srcs")), "noid": sum(1 for r in rows if not r["appid"] and not r["kind"]),
            "kinds": {kd: sum(1 for r in rows if r["kind"] == kd) for kd in KINDS}}
