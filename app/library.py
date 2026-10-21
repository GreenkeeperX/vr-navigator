"""Ansichten: Bibliothek und Wunschliste als Zeilen für die Oberfläche."""
from . import titles


def _where(t):
    """Wo du den Titel besitzt: meta, pc, beide oder ""."""
    o = t.get("owned") or {}
    if o.get("meta") and o.get("pc"):
        return "beide"
    return "meta" if o.get("meta") else ("pc" if o.get("pc") else "")


def row(key, t):
    sheet = t.get("sheet") or None
    gap = None
    if sheet and sheet.get("meta_low") is not None and sheet.get("gg") is not None:
        # Aufpreis von Meta (Tief) gegenüber dem günstigsten Steam-Angebot; negativ: Meta günstiger
        gap = round(sheet["meta_low"] - sheet["gg"], 2)
    o = t.get("owned") or {}
    return {
        "key": key, "name": t["name"], "meta_id": t.get("meta_id") or "",
        "steam_appid": t.get("steam_appid") or "", "steam_sure": bool(t.get("steam_sure")),
        "where": _where(t), "pc_label": (o.get("pc") or {}).get("label") or "",
        "meta_price": (o.get("meta") or {}).get("price"),
        "wish": bool(t.get("wish")), "crossbuy": t.get("crossbuy"),
        "sheet": sheet, "gap": gap, "note": t.get("note") or "",
        "links": titles.search_links(t), "added": t.get("added") or "",
    }


def view(data):
    rows = sorted((row(k, t) for k, t in data["titles"].items()), key=lambda r: titles.norm(r["name"]))
    owned = [r for r in rows if r["where"]]
    wish = [r for r in rows if r["wish"]]
    return {
        "library": owned,
        "wishlist": wish,
        "counts": {"all": len(rows), "owned": len(owned), "wish": len(wish),
                   "meta": sum(r["where"] in ("meta", "beide") for r in rows),
                   "pc": sum(r["where"] in ("pc", "beide") for r in rows),
                   "both": sum(r["where"] == "beide" for r in rows)},
        "suggestions": titles.suggestions(data),
        "imports": data.get("imports") or {},
    }
