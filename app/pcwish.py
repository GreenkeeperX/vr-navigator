"""PC-Wunschliste (0.8.2): die ganze Wunschliste von gg.deals, nicht nur die VR-Titel.

gg.deals bleibt führend (Entscheidung 27.10.2026): Das Tool spiegelt die Liste, ordnet jedem Spiel eine
Steam-ID zu und holt dazu die Preise über die gg.deals-API, wie der eShopKompass zu DekuDeals. Abgelegt in
pcwish.json im Datenordner; eine neue Liste behält Steam-ID und Preise je Spiel.
"""
import re
from datetime import date, timedelta

from . import collection, itad, store, titles, trend

FILE = "pcwish.json"
EMPTY = {"items": {}, "at": "", "via": ""}
NEAR = 0.05         # bis 5 % über dem bisherigen Tief gilt als „nah am Tief“

# Preissturz (0.8.18): eigener Preisverlauf je Spiel (ph: [[Tag, bester Preis]], nur Änderungen). Üblich ist der
# Median der Tagespreise der letzten DROP_DAYS Tage; ein Preissturz liegt DROP_PCT darunter und DROP_EUR billiger.
# Steam-Sales zählen nicht eigens: Keyshops sind oft billiger als ein Sale, es gilt der beste Preis
PH_DAYS = 180       # so lange bleibt der Verlauf
DROP_DAYS = 90
DROP_MIN_DAYS = 21  # so viele Tage Verlauf braucht das Urteil
DROP_PCT, DROP_EUR = 25, 3.0


KINDS = {"pack": "Paket", "dlc": "DLC"}


def _key(it):
    if it.get("kind"):
        return f"{it['kind']}:{it['slug']}"     # 0.8.7: Pakete und DLC, eigene Adresse bei gg.deals
    return it["slug"] if it.get("slug") else "name:" + titles.norm(it["name"])


def record(e, gg, day=None):
    """Besten Preis aus gg (Händler oder Keyshop) im Verlauf ph vermerken, nur wenn er sich ändert."""
    vals = [x for x in (gg.get("retail"), gg.get("keyshops")) if isinstance(x, (int, float))]
    if not vals:
        return
    day = day or date.today().isoformat()
    best = round(min(vals), 2)
    ph = [x for x in (e.get("ph") or []) if isinstance(x, list) and len(x) == 2]
    cut = (date.fromisoformat(day) - timedelta(days=PH_DAYS)).isoformat()
    # ältere Einträge fallen weg, der letzte vor der Grenze bleibt als Anfangswert
    while len(ph) > 1 and ph[1][0] <= cut:
        ph.pop(0)
    if not ph or ph[-1][1] != best:
        ph = [x for x in ph if x[0] != day] + [[day, best]]
    e["ph"] = ph


def drop(ph, now_price, today=None):
    """Preissturz aus dem Verlauf: {"usual": Median, "pct": so viel darunter, "days": Tage Verlauf} oder None."""
    if now_price is None or not ph:
        return None
    today = date.fromisoformat(today or date.today().isoformat())
    try:
        first = date.fromisoformat(ph[0][0])
    except (TypeError, ValueError):
        return None
    start = max(first, today - timedelta(days=DROP_DAYS))
    days = (today - start).days
    if days < DROP_MIN_DAYS:
        return None
    daily, i, price = [], 0, None
    for n in range(days):
        d = (start + timedelta(days=n)).isoformat()
        while i < len(ph) and ph[i][0] <= d:
            price = ph[i][1]
            i += 1
        if price is not None:
            daily.append(price)
    if not daily:
        return None
    daily.sort()
    m = len(daily) // 2
    usual = daily[m] if len(daily) % 2 else (daily[m - 1] + daily[m]) / 2
    if usual <= 0 or usual - now_price < DROP_EUR or 100 * (usual - now_price) / usual < DROP_PCT:
        return None
    return {"usual": round(usual, 2), "pct": round(100 * (usual - now_price) / usual), "days": days}


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


# Steam-ID per Suche (0.8.24): gesucht wird mit dem Namen ohne Zeichen, die die Steam-Suche stören (Emoji, „[Studio]“
# vorn), und, wenn das nichts bringt, mit der Grundform (vor „ / “, ohne Zusatz wie „Definitive Edition“).
# Genau gleicher Name, einmal: sicher. Gleich nur in der Grundform, einmal: übernommen, aber als „≈“ markiert und in
# „Zu erledigen“ zum Bestätigen. Sonst bis zu CANDS ähnliche Namen zur Wahl, nie von allein.
CANDS = 3
_EDITION = re.compile(r"\s*[-:–]?\s*\b(?:the\s+)?(?:definitive|complete|enhanced|ultimate|deluxe|gold|zen|goty|game of the year|"
                      r"anniversary|director'?s cut|legacy)(?:\s+edition)?\s*$", re.I)


def search_term(name):
    """Name für die Steam-Suche: ohne Emoji und Zeichen außerhalb von Buchstaben, Ziffern und üblichen Satzzeichen,
    ohne „[…]“ am Anfang."""
    t = re.sub(r"^\s*\[[^\]]*\]\s*", "", str(name or ""))
    t = re.sub(r"[^\w\s:.,&'!?+\-/()]", " ", t)
    return " ".join(t.split())


def base_forms(name):
    """Grundformen des Namens zum Vergleichen: vor „ / “ und „ | “, ohne Editions-Zusatz, ohne Klammer am Ende."""
    t = search_term(name)
    out = []
    for part in (t, re.split(r"\s+[/|]\s+", t)[0]):
        for x in (part, _EDITION.sub("", part)):
            n = titles.base_norm(x)
            if n and n not in out:
                out.append(n)
    return out


def _words(n):
    return set(n.split())


def pick(name, results, no=()):
    """Steam-ID aus Suchtreffern: {"appid", "how": "exact" oder "near"} oder {"cands": [{appid, name}]} oder {}."""
    res = [r for r in results if r["appid"] not in no]
    exact = [r for r in res if titles.norm(r["name"]) == titles.norm(name)]
    if len(exact) == 1:
        return {"appid": exact[0]["appid"], "how": "exact"}
    if len(exact) > 1:
        return {"cands": exact[:CANDS]}
    forms = set(base_forms(name))
    near = [r for r in res if set(base_forms(r["name"])) & forms]
    if len(near) == 1:
        return {"appid": near[0]["appid"], "how": "near"}
    if len(near) > 1:
        return {"cands": near[:CANDS]}
    # Ähnlich: gleiche Zahlen, mindestens die Hälfte der Wörter gemeinsam (Jaccard)
    mine = _words(titles.norm(name))
    digits = lambda ws: {w for w in ws if w.isdigit()}
    cands = []
    for r in res:
        other = _words(titles.norm(r["name"]))
        if mine and other and digits(mine) == digits(other) and len(mine & other) / len(mine | other) >= 0.5:
            cands.append(r)
    return {"cands": cands[:CANDS]} if cands else {}


def id_todo(pw):
    """PC-Wünsche für „Zu erledigen“ (0.8.24): Steam-ID nur nach der Grundform (bestätigen) oder Vorschläge zur Wahl."""
    out = []
    for k, e in (pw.get("items") or {}).items():
        if e.get("kind"):
            continue
        if e.get("appid") and e.get("id_near"):
            out.append({"key": k, "name": e["name"], "appid": e["appid"], "steam": e.get("id_name") or "", "kind": "near"})
        elif not e.get("appid") and e.get("cand"):
            out.append({"key": k, "name": e["name"], "cands": e["cand"], "kind": "cand"})
    return sorted(out, key=lambda x: titles.norm(x["name"]))


def settle_id(pw, key, appid):
    """Antwort aus „Zu erledigen“: appid gilt (aus den Vorschlägen oder die übernommene bestätigt); leer heißt falsch
    oder keiner davon, diese IDs schlägt das Tool nicht wieder vor."""
    e = (pw.get("items") or {}).get(key)
    if not e:
        raise ValueError("kein PC-Wunsch mit diesem Schlüssel")
    offered = [c["appid"] for c in e.get("cand") or []] + ([e["appid"]] if e.get("id_near") else [])
    if appid:
        if appid not in offered:
            raise ValueError("diese Steam-ID stand nicht zur Wahl")
        if e.get("appid") != appid:
            for f in ("gg", "steam", "rev", "igdb", "news", "play", "ph", "itad", "itad_id", "itad_tried", "sh", "sh_at"):
                e.pop(f, None)
        e["appid"] = appid
    else:
        e["no_ids"] = sorted(set(e.get("no_ids") or []) | set(offered))
        e.pop("appid", None)
        for f in ("gg", "steam", "rev", "igdb", "news", "play", "ph", "itad", "itad_id", "itad_tried", "sh", "sh_at"):
            e.pop(f, None)
    for f in ("id_near", "id_name", "cand"):
        e.pop(f, None)
    return e


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


INFO = ("genres", "gc", "gx", "mp", "mpc", "players", "pl_src", "plm", "score", "score_src", "score_alt", "score_n", "hours_n", "reviews", "rdesc",
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
        r["trend"] = trend.trend(e.get("rev"))
        if e.get("id_near"):
            r["id_near"] = e.get("id_name") or True       # 0.8.24: Steam-ID nur nach der Grundform des Namens
        r["care"] = trend.care((e.get("news") or {}).get("date"))
        r["drop"] = drop(e.get("ph"), best[0])
        # 0.9.0: Läden einzeln von IsThereAnyDeal; nah am Tief wie oben, gemessen am Tief der offiziellen Läden
        # (Händler bei gg.deals oder IsThereAnyDeal), nicht am Keyshop
        it = e.get("itad") or {}
        if it.get("shops"):
            lo = min((x for x in (gg.get("retail_low"), it.get("low")) if x is not None), default=None)
            r["shops"], r["shops_at"], r["shops_low"] = itad.shop_rows(it, lo, NEAR), it.get("at") or "", lo
        if isinstance((e.get("play") or {}).get("now"), int):
            r["active"] = {"now": e["play"]["now"], "at": e["play"].get("at") or ""}   # Aktiv (0.8.23)
        if best[0] is not None and low is not None:
            r["over"] = round((best[0] - low) / low, 3) if low > 0 else 0.0
            r["near"] = best[0] <= low * (1 + NEAR) + 0.005
        rows.append(r)
    rows.sort(key=lambda r: titles.norm(r["name"]))
    return {"at": pw.get("at") or "", "via": pw.get("via") or "", "n": len(rows), "rows": rows,
            "priced": sum(1 for r in rows if r["best"] is not None), "info": sum(1 for r in rows if r.get("srcs")), "noid": sum(1 for r in rows if not r["appid"] and not r["kind"]),
            "kinds": {kd: sum(1 for r in rows if r["kind"] == kd) for kd in KINDS}}
