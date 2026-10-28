"""IsThereAnyDeal (0.9.0): Preise je offiziellem Laden für die PC-Wunschliste, ohne Netz gelesen.

Die gg.deals-API nennt nur den günstigsten Händler und Keyshop; die Liste aller Läden steht dort nur auf der
Spielseite hinter Cloudflare. IsThereAnyDeal liefert sie über eine offene Schnittstelle mit persönlichem
Schlüssel (isthereanydeal.com, My Apps): erst die ITAD-Kennung zur Steam-ID, dann die Preise je Laden für
Deutschland. Der Schlüssel geht als Kopfzeile mit, nie in der Adresse.
"""
import json

API = "https://api.isthereanydeal.com"
STEAM_SHOP = 61
CHUNK = 200         # so viele Kennungen nimmt ein Abruf


def headers(key):
    return {"ITAD-API-Key": key, "Content-Type": "application/json", "Accept": "application/json"}


def lookup_url():
    return f"{API}/lookup/id/shop/{STEAM_SHOP}/v1"


def lookup_body(appids):
    return json.dumps([f"app/{a}" for a in appids]).encode()


def lookup(text):
    """Antwort auf lookup_body: {Steam-ID: ITAD-Kennung oder ""}."""
    d = json.loads(text)
    if not isinstance(d, dict):
        raise ValueError("IsThereAnyDeal: Antwort der Zuordnung ist keine Liste von Kennungen")
    out = {}
    for k, v in d.items():
        if isinstance(k, str) and k.startswith("app/"):
            out[k[4:]] = v if isinstance(v, str) else ""
    return out


def prices_url():
    return f"{API}/games/prices/v3?country=DE&deals=false"


def _amount(m):
    v = (m or {}).get("amount") if isinstance(m, dict) else None
    return round(float(v), 2) if isinstance(v, (int, float)) else None


def prices(text):
    """Antwort auf die Preise: {ITAD-Kennung: {"shops": [{"s", "id", "p", "r", "c", "lo", "u", "x"}], "low", "low1"}}.
    Je Laden der Preis jetzt (p), normal (r), Rabatt in Prozent (c), das Tief dort (lo), der Link (u) und das
    Angebotsende (x); low ist das Tief über alle Läden, low1 das der letzten zwölf Monate. Nur Euro."""
    d = json.loads(text)
    if not isinstance(d, list):
        raise ValueError("IsThereAnyDeal: Antwort der Preise ist keine Liste")
    out = {}
    for g in d:
        if not isinstance(g, dict) or not isinstance(g.get("id"), str):
            continue
        shops = []
        for x in g.get("deals") or []:
            if not isinstance(x, dict):
                continue
            p = _amount(x.get("price"))
            cur = (x.get("price") or {}).get("currency")
            if p is None or cur not in (None, "EUR"):
                continue
            shop = x.get("shop") or {}
            shops.append({"s": str(shop.get("name") or "?")[:40], "id": shop.get("id"), "p": p, "r": _amount(x.get("regular")),
                          "c": x.get("cut") if isinstance(x.get("cut"), int) else 0, "lo": _amount(x.get("storeLow")),
                          "u": x.get("url") if str(x.get("url") or "").startswith("https://") else "",
                          "x": str(x.get("expiry") or "")[:25]})
        shops.sort(key=lambda s: (s["p"], s["s"]))
        hl = g.get("historyLow") or {}
        out[g["id"]] = {"shops": shops, "low": _amount(hl.get("all")), "low1": _amount(hl.get("y1"))}
    return out


def shop_rows(it, low, near):
    """Läden einer Zeile der PC-Wunschliste: nach Preis, mit near (höchstens near über dem Tief low)."""
    rows = []
    for s in (it or {}).get("shops") or []:
        r = dict(s)
        r["near"] = low is not None and s["p"] <= low * (1 + near) + 0.005
        rows.append(r)
    return rows
