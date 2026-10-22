"""Ansichten: Bibliothek, Wunschliste und „Jetzt“ als Zeilen für die Oberfläche."""
from datetime import datetime, timedelta, timezone

from . import titles

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
    """Günstigstes Angebot für die PC-Fassung: Steam selbst oder gg.deals (Händler, Keyshops)."""
    offers = [((live.get("steam") or {}).get("price"), "Steam"),
              ((live.get("gg") or {}).get("retail"), "gg.deals Händler"),
              ((live.get("gg") or {}).get("keyshops"), "gg.deals Keyshop")]
    offers = [o for o in offers if o[0] is not None]
    if not offers:
        return None
    p, src = min(offers)
    return {"price": p, "src": src}


def row(key, t, at=None):
    sheet = t.get("sheet") or None
    gap = None
    if sheet and sheet.get("meta_low") is not None and sheet.get("gg") is not None:
        # Aufpreis von Meta (Tief) gegenüber dem günstigsten Steam-Angebot; negativ: Meta günstiger
        gap = round(sheet["meta_low"] - sheet["gg"], 2)
    o = t.get("owned") or {}
    live = _live(t, at)
    best = _pc_best(live)
    meta_now = (live.get("meta") or {}).get("price")
    return {
        "key": key, "name": t["name"], "meta_id": t.get("meta_id") or "",
        "steam_appid": t.get("steam_appid") or "", "steam_sure": bool(t.get("steam_sure")),
        "steam_doubt": t.get("steam_doubt") or "", "bundle": titles.is_bundle(t),
        "where": _where(t), "pc_label": (o.get("pc") or {}).get("label") or "",
        "meta_price": (o.get("meta") or {}).get("price"),
        "wish": bool(t.get("wish")), "crossbuy": t.get("crossbuy"),
        "sheet": sheet, "gap": gap, "note": t.get("note") or "",
        "live": live, "pc_best": best,
        # Aufpreis von Meta jetzt gegenüber dem günstigsten PC-Angebot jetzt
        "gap_now": round(meta_now - best["price"], 2) if meta_now is not None and best else None,
        "links": titles.search_links(t), "added": t.get("added") or "",
    }


def _sale(r):
    """Höchster Rabatt eines Wunschtitels gerade jetzt (Meta oder Steam), sonst 0."""
    return max((r["live"].get("meta") or {}).get("discount") or 0,
               (r["live"].get("steam") or {}).get("discount") or 0)


def view(data, at=None):
    rows = sorted((row(k, t, at) for k, t in data["titles"].items()), key=lambda r: titles.norm(r["name"]))
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
        "todo": [dict(x, row=row(x["key"], data["titles"][x["key"]], at)) for x in titles.todo(data)],
        "imports": data.get("imports") or {},
    }
