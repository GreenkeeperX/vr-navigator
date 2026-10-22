"""Ansichten: Bibliothek, Wunschliste und „Jetzt“ als Zeilen für die Oberfläche."""
from datetime import datetime, timedelta, timezone

from . import prices, titles

STALE_H = 48        # ältere Live-Preise markiert die Oberfläche als veraltet


def _where(t):
    """Wo du den Titel besitzt: meta, pc, beide oder ""."""
    o = t.get("owned") or {}
    if o.get("meta") and o.get("pc"):
        return "beide"
    return "meta" if o.get("meta") else ("pc" if o.get("pc") else "")


def _live(t, at=None):
    """Live-Preise je Quelle, mit Kennzeichen „veraltet“. Ein Meta-Angebot, dessen Ende
    vorbei ist, gilt wieder zum Normalpreis, auch wenn noch kein neuer Abruf lief."""
    at = at or datetime.now(timezone.utc)
    today, old = at.strftime("%Y-%m-%d"), (at - timedelta(hours=STALE_H)).isoformat(timespec="seconds")
    out = {}
    for src, v in (t.get("live") or {}).items():
        if not isinstance(v, dict):
            continue
        v = dict(v, stale=(v.get("at") or "") < old)
        if src == "meta":
            if v.get("price") is None:
                continue
            if v.get("until") and v["until"] < today and v.get("base") is not None:
                v.update(price=v["base"], discount=0, until="", kind="base", ended=True)
            v["at_low"] = bool(v.get("discount")) and v.get("low") is not None and v["price"] <= v["low"]
        out[src] = v
    return out


def _pc_best(live):
    """Günstigstes Angebot für die PC-Fassung: Steam selbst oder ein Händler bei gg.deals.
    Keyshops zählen nicht (Entscheidung 22.10.2026), die Oberfläche zeigt sie grau daneben."""
    offers = [((live.get("steam") or {}).get("price"), "Steam"),
              ((live.get("gg") or {}).get("retail"), "gg.deals Händler")]
    offers = [o for o in offers if o[0] is not None]
    if not offers:
        return None
    p, src = min(offers)
    return {"price": p, "src": src}


def _best(hist, src, ident, price, today):
    """Bestpreis der letzten 24 Monate je Shop aus dem Verlauf, dazu die Stufe des aktuellen
    Preises: best (höchstens 2 % über dem Bestpreis), usual (am üblichen Angebot) oder ""."""
    if not ident or price is None:
        return None
    rows = list((hist.get(src) or {}).get(str(ident)) or [])
    if not rows or rows[-1][1] != price:
        rows.append([today, price])
    b = prices.best_of(rows, today)
    if not b:
        return None
    if not b["full"] and b["best"] == max(p for _, p in rows if _ >= b["since"]):
        # Kurzer Verlauf ohne jede Preisänderung: noch keine Aussage über einen Bestpreis
        return dict(b, level="", over=0.0, thin=True)
    tol = 1 + prices.BEST_TOL
    level = "best" if price <= b["best"] * tol + 0.005 else \
        "usual" if b["usual"] is not None and price <= b["usual"] * tol + 0.005 else ""
    return dict(b, level=level, over=round(price - b["best"], 2))


def row(key, t, at=None, hist=None, data=None):
    sheet = t.get("sheet") or None
    gap = None
    if sheet and sheet.get("meta_low") is not None and sheet.get("gg") is not None:
        # Aufpreis von Meta (Tief) gegenüber dem günstigsten Steam-Angebot; negativ: Meta günstiger
        gap = round(sheet["meta_low"] - sheet["gg"], 2)
    o = t.get("owned") or {}
    live = _live(t, at)
    pc = _pc_best(live)
    # Crossbuy von Hand oder aus der Tabelle geht vor; sonst der aus der Recherche, gekennzeichnet
    cb, cb_src = t.get("crossbuy"), ""
    if cb is None and (t.get("opinion") or {}).get("crossbuy") is not None:
        cb, cb_src = t["opinion"]["crossbuy"], "Recherche"
    meta_now = (live.get("meta") or {}).get("price")
    today = (at or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    hist = hist or {}
    best = {"meta": _best(hist, "meta", t.get("meta_id"), meta_now, today),
            "steam": _best(hist, "steam", t.get("steam_appid"), (live.get("steam") or {}).get("price"), today)}
    return {
        "key": key, "name": t["name"], "meta_id": t.get("meta_id") or "",
        "steam_appid": t.get("steam_appid") or "", "steam_sure": bool(t.get("steam_sure")),
        "steam_doubt": t.get("steam_doubt") or "", "bundle": titles.is_bundle(t),
        "where": _where(t), "pc_label": (o.get("pc") or {}).get("label") or "",
        "meta_price": (o.get("meta") or {}).get("price"),
        "wish": bool(t.get("wish")), "crossbuy": cb, "crossbuy_src": cb_src,
        "opinion": t.get("opinion") or None, "origin": titles.origins(t, data),
        "contains": [{"key": k, "name": data["titles"][k]["name"]} for k in t.get("contains") or []
                     if data and k in data["titles"]],
        "sheet": sheet, "gap": gap, "note": t.get("note") or "",
        "live": live, "pc_best": pc, "best": {k: v for k, v in best.items() if v},
        # Aufpreis von Meta jetzt gegenüber dem günstigsten PC-Angebot jetzt
        "gap_now": round(meta_now - pc["price"], 2) if meta_now is not None and pc else None,
        "links": titles.search_links(t), "added": t.get("added") or "",
        "rating": rating(t),
    }


def rating(t):
    """Wertungen je Laden: Meta-Sterne (über QuestStoreDB) und Steam-Anteil positiv. Steam erst
    ab 50 Rezensionen wie in Entdecken; darunter nur die Zahl. score: 0 bis 100 zum Sortieren
    (Sterne mal 20), der bessere der beiden."""
    m = ((t.get("live") or {}).get("meta") or {})
    meta = None
    if isinstance(m.get("rating"), (int, float)) and 0 < m["rating"] <= 5:
        meta = {"stars": round(float(m["rating"]), 1), "n": m.get("ratings") if isinstance(m.get("ratings"), int) else None}
    rev = t.get("rev") or {}
    steam = None
    if isinstance(rev.get("n"), int) and rev["n"] > 0:
        steam = {"pct": rev.get("pct") if rev["n"] >= 50 else None, "n": rev["n"]}
    vals = ([meta["stars"] * 20] if meta else []) + ([steam["pct"]] if steam and steam["pct"] is not None else [])
    score = round(max(vals)) if vals else None
    return {"meta": meta, "steam": steam, "score": score}


def _sale(r):
    """Höchster Rabatt eines Wunschtitels gerade jetzt (Meta oder Steam), sonst 0."""
    return max((r["live"].get("meta") or {}).get("discount") or 0,
               (r["live"].get("steam") or {}).get("discount") or 0)


def view(data, at=None, hist=None):
    rows = sorted((row(k, t, at, hist, data) for k, t in data["titles"].items()), key=lambda r: titles.norm(r["name"]))
    owned = [r for r in rows if r["where"]]
    # Die Wunschliste führt auch Titel, die du inzwischen besitzt; die Oberfläche blendet sie
    # aus, solange du sie nicht ausdrücklich zeigen lässt (owned_wish zählt sie)
    wish = [r for r in rows if r["wish"]]
    now = sorted((r for r in wish if not r["where"] and _sale(r)), key=lambda r: (-_sale(r), titles.norm(r["name"])))
    return {
        "now": now,
        "library": owned,
        "wishlist": wish,
        "counts": {"all": len(rows), "now": len(now), "owned": len(owned), "wish": sum(not r["where"] for r in wish),
                   "owned_wish": sum(bool(r["where"]) for r in wish),
                   "meta": sum(r["where"] in ("meta", "beide") for r in rows),
                   "pc": sum(r["where"] in ("pc", "beide") for r in rows),
                   "both": sum(r["where"] == "beide" for r in rows)},
        "suggestions": titles.suggestions(data),
        # Mit der Zeile, damit „bearbeiten“ auch Titel öffnet, die weder Besitz noch Wunsch sind
        "todo": [dict(x, row=row(x["key"], data["titles"][x["key"]], at, hist, data)) for x in titles.todo(data)],
        "imports": data.get("imports") or {},
    }
