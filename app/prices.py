"""Preise aus den Antworten der Quellen lesen: QuestStoreDB (Meta), Steam-Store, gg.deals.

Nur Lesen, kein Netz: Die Funktionen bekommen den Text einer Antwort und liefern einfache
Werte. So lassen sie sich mit gespeicherten Beispielen prüfen. Alle Preise in Euro.
"""
import html
import json
import re
from datetime import datetime, timezone

QSDB = "https://queststoredb.com"


def _num(s):
    """„3.41 €“, „1,234.50“ → 3.41; ohne Euro-Zeichen oder Zahl: None (andere Währung)."""
    s = str(s or "")
    if "€" not in s:
        return None
    m = re.search(r"\d[\d,]*(?:\.\d+)?", s)
    return float(m.group(0).replace(",", "")) if m else None


def _ts_day(ms):
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def _clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


# ------------------------------------------------------------------ QuestStoreDB

def qsdb_game(text):
    """Titelseite /game/<name>-<Meta-ID>/: Preis, Normalpreis, Angebotsende, eigenes Tief,
    Bewertung, App-Version. Grundlage sind die strukturierten Daten (JSON-LD) und der
    Preisverlauf, den die Seite für ihr Diagramm mitliefert. None, wenn beides fehlt."""
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', text, re.S)
    if not m:
        return None
    try:
        graph = json.loads(m.group(1)).get("@graph") or []
    except ValueError:
        return None
    app = next((g for g in graph if isinstance(g, dict) and "VideoGame" in (g.get("@type") or [])
                or isinstance(g, dict) and g.get("offers")), None)
    if not app:
        return None
    offer = next((o for o in app.get("offers") or [] if o.get("priceCurrency") == "EUR"), None)
    out = {"name": html.unescape(app.get("name") or ""), "meta_id": "", "price": None, "base": None,
           "until": "", "low": None, "low_at": "", "rating": None, "ratings": None,
           "version": app.get("softwareVersion") or "", "path": ""}
    url = app.get("url") or ""
    pm = re.search(r"queststoredb\.com(/(?:game|app|bundle|add-on)/[a-z0-9-]*?-?(\d{6,})/)", url)
    if pm:
        out["path"], out["meta_id"] = pm.group(1), pm.group(2)
    if offer:
        out["meta_id"] = out["meta_id"] or str(offer.get("sku") or "")
        out["price"] = offer.get("price")
        out["base"] = (offer.get("priceSpecification") or {}).get("price") or offer.get("price")
        out["until"] = offer.get("priceValidUntil") or ""
    r = app.get("aggregateRating") or {}
    out["rating"], out["ratings"] = r.get("ratingValue"), r.get("ratingCount")
    h = re.search(r'<script id="price-history-data" type="application/json">(.*?)</script>', text, re.S)
    if h:
        try:
            pts = [p for p in json.loads(h.group(1)) if isinstance(p, dict)
                   and isinstance(p.get("y"), (int, float)) and "€" in str(p.get("f") or "")]
        except ValueError:
            pts = []
        if pts:
            low = min(pts, key=lambda p: (p["y"], -p.get("x", 0)))
            out["low"] = low["y"]
            out["low_at"] = _ts_day(low["x"]) if isinstance(low.get("x"), (int, float)) else ""
    if out["price"] is None and out["low"] is None:
        return None
    return out


def qsdb_cards(text):
    """Kacheln einer Liste (Angebote, Suche): je Titel Meta-ID, Name, Pfad, Preis, Normalpreis,
    Rabatt, Art (discount, coupon, base) und Ende des Angebots."""
    out = []
    for part in text.split('<div class="card-image-container"')[1:]:
        link = re.search(r'href="(/(?:game|app|bundle|add-on)/[a-z0-9-]*?-?(\d{6,})/)"', part)
        if not link:
            continue
        name = re.search(r'<div class="card-title">\s*<div>(.*?)</div>', part, re.S)
        kind = re.search(r'app-price-type-([a-z-]+)', part)
        amount = re.search(r'<div class="app-price-amount">(.*?)</div', part, re.S)
        spans = [_clean(s) for s in re.findall(r"<span[^>]*>(.*?)</span>", amount.group(1), re.S)] if amount else []
        price = _num(spans[0]) if spans else None
        base = _num(spans[1]) if len(spans) > 1 and spans[1] else price
        pct = re.search(r'<div class="app-price-benefit">\s*<span>\s*-(\d+)%', part)
        tag = re.search(r'<div class="app-price-benefit">\s*<span>[^<]*</span>\s*<span>([^<]*)</span>', part)
        end = re.search(r'data-countdown-timer="(\d+)"', part)
        out.append({
            "meta_id": link.group(2), "path": link.group(1),
            "name": _clean(name.group(1)) if name else "",
            "kind": kind.group(1) if kind else "", "price": price, "base": base,
            "discount": int(pct.group(1)) if pct else 0,
            "tag": _clean(tag.group(1)) if tag else "",
            "until": _ts_day(int(end.group(1)) * 1000) if end else "",
        })
    return out


def qsdb_pages(text):
    """Höchste Seitenzahl einer Liste (Links „page=N“), mindestens 1."""
    return max([1] + [int(n) for n in re.findall(r"[?&](?:amp;)?page=(\d+)", text)])


# ------------------------------------------------------------------ Steam

def steam_prices(text):
    """appdetails mit filters=price_overview, auch für mehrere IDs: {App-ID: Preise}.
    Kostenlose Titel haben kein price_overview und bekommen Preis 0; nicht (mehr) im
    deutschen Store: fehlt im Ergebnis."""
    try:
        d = json.loads(text)
    except ValueError:
        return {}
    out = {}
    for appid, v in (d or {}).items():
        if not isinstance(v, dict) or not v.get("success"):
            continue
        po = (v.get("data") or {}).get("price_overview") if isinstance(v.get("data"), dict) else None
        if not po:
            out[str(appid)] = {"price": 0.0, "base": 0.0, "discount": 0}
            continue
        if po.get("currency") != "EUR":
            continue
        out[str(appid)] = {"price": po.get("final", 0) / 100, "base": po.get("initial", 0) / 100,
                           "discount": int(po.get("discount_percent") or 0)}
    return out


def steam_search(text):
    """storesearch: Liste von {appid, name} (nur Spiele, keine Zusatzinhalte-Typen)."""
    try:
        items = json.loads(text).get("items") or []
    except (ValueError, AttributeError):
        return []
    return [{"appid": str(i.get("id")), "name": i.get("name") or ""} for i in items
            if isinstance(i, dict) and i.get("type") == "app" and i.get("id")]


# ------------------------------------------------------------------ gg.deals

def _eur(v):
    try:
        return float(str(v).replace(",", "."))
    except (TypeError, ValueError):
        return None


def gg_prices(text):
    """gg.deals-API, Preise je Steam-App-ID: {App-ID: {retail, keyshops, retail_low,
    keyshops_low, url}}. Titel ohne Eintrag bei gg.deals stehen mit null in der Antwort und
    fehlen hier. Wirft ValueError mit der Meldung der API, wenn sie einen Fehler meldet."""
    try:
        d = json.loads(text)
    except ValueError:
        raise ValueError("gg.deals: keine JSON-Antwort")
    if not isinstance(d, dict) or not d.get("success"):
        msg = (d.get("data") or {}).get("message") if isinstance(d, dict) and isinstance(d.get("data"), dict) else ""
        raise ValueError(f"gg.deals: {msg or 'Anfrage abgelehnt'}")
    out = {}
    for appid, v in (d.get("data") or {}).items():
        if not isinstance(v, dict):
            continue
        p = v.get("prices") or {}
        if p.get("currency") not in (None, "EUR"):
            continue
        out[str(appid)] = {
            "retail": _eur(p.get("currentRetail")), "keyshops": _eur(p.get("currentKeyshops")),
            "retail_low": _eur(p.get("historicalRetail")), "keyshops_low": _eur(p.get("historicalKeyshops")),
            "url": v.get("url") or "",
        }
    return out
