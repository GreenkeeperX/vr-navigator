"""Preise aus den Antworten der Quellen lesen: QuestStoreDB (Meta), Steam-Store, gg.deals.

Nur Lesen, kein Netz: Die Funktionen bekommen den Text einer Antwort und liefern einfache
Werte. So lassen sie sich mit gespeicherten Beispielen prüfen. Alle Preise in Euro.
"""
import html
import json
import re
from datetime import date, datetime, timezone

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
           "version": app.get("softwareVersion") or "", "path": "", "hist": []}
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
            out["hist"] = [[_ts_day(p["x"]), p["y"]] for p in sorted(
                (p for p in pts if isinstance(p.get("x"), (int, float))), key=lambda p: p["x"])]
            low = min(pts, key=lambda p: (p["y"], -p.get("x", 0)))
            out["low"] = low["y"]
            out["low_at"] = _ts_day(low["x"]) if isinstance(low.get("x"), (int, float)) else ""
    if out["price"] is None and out["low"] is None:
        return None
    return out


BEST_MONTHS = 24
BEST_TOL = 0.02         # bis 2 % darüber zählt als „am Bestpreis“ oder „am üblichen Angebot“


def best_of(hist, today, months=BEST_MONTHS):
    """Bestpreis aus einem Verlauf [[Tag, Preis]] (je Eintrag der Preis ab diesem Tag) über die
    letzten `months` Monate. Liefert {best, best_at, since, once, usual} oder None:
    best ist der niedrigste Preis (best_at der letzte Tag damit), since der Beginn des
    Zeitraums (später als vor 24 Monaten, wenn der Verlauf kürzer ist; full ist dann False). once: der Bestpreis kam
    nur in einem einzigen Zeitraum vor. usual: der niedrigste Preis, der in mindestens zwei
    getrennten Zeiträumen galt (bis 2 % darüber), das übliche Angebot; None ohne Wiederholung."""
    d = date.fromisoformat(today)
    y, m = divmod(d.year * 12 + d.month - 1 - months, 12)
    cut = date(y, m + 1, min(d.day, 28)).isoformat()
    rows = sorted((str(d), float(p)) for d, p in (r for r in hist or [] if isinstance(r, (list, tuple)) and len(r) == 2)
                  if d and isinstance(p, (int, float)))
    if not rows:
        return None
    before = [r for r in rows if r[0] < cut]
    win = ([(cut, before[-1][1])] if before else []) + [r for r in rows if r[0] >= cut]

    def episodes(limit):
        n, inside = 0, False
        for _, p in win:
            hit = p <= limit * (1 + BEST_TOL) + 0.005
            n += hit and not inside
            inside = hit
        return n
    best = min(p for _, p in win)
    usual = next((p for p in sorted({p for _, p in win}) if episodes(p) >= 2), None)
    return {"best": best, "best_at": max(d for d, p in win if p == best), "since": win[0][0],
            "once": episodes(best) < 2, "usual": usual, "full": bool(before)}


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


def steam_reviews(text):
    """appreviews mit num_per_page=0: Zahl der Rezensionen und Anteil positiv in Prozent.
    None, wenn Steam die App nicht kennt oder die Antwort nicht passt."""
    try:
        d = json.loads(text)
    except ValueError:
        return None
    # Store-Schnittstelle (0.7.5, IStoreBrowseService/GetItems): Zusammenfassung je App
    items = (d.get("response") or {}).get("store_items") if isinstance(d, dict) and isinstance(d.get("response"), dict) else None
    if isinstance(items, list):
        it = items[0] if items and isinstance(items[0], dict) and items[0].get("success") == 1 else None
        if it is None:
            return None
        r = ((it.get("reviews") or {}).get("summary_filtered") or {})
        n = r.get("review_count") if isinstance(r.get("review_count"), int) else 0
        pct = r.get("percent_positive") if isinstance(r.get("percent_positive"), int) and n else None
        return {"n": n, "pct": pct, "desc": str(r.get("review_score_label") or "")[:40]}
    q = d.get("query_summary") if isinstance(d, dict) and d.get("success") == 1 else None
    if not isinstance(q, dict) or not isinstance(q.get("total_reviews"), int):
        return None
    n, pos = q["total_reviews"], int(q.get("total_positive") or 0)
    out = {"n": n, "pct": round(100 * pos / n) if n else None, "desc": str(q.get("review_score_desc") or "")[:40]}
    if n and isinstance(q.get("total_positive"), int):
        out["pos"] = pos      # genaue Zahl für den Trend aus eigenen Messungen (0.8.18)
    return out


# Feste Kennungen der Steam-Store-Daten (gleich in jeder Sprache)
STEAM_GENRES = {"1": "Action", "2": "Strategie", "3": "Rollenspiel", "4": "Casual", "9": "Rennen", "18": "Sport",
                "25": "Abenteuer", "28": "Simulation"}
STEAM_MP = {"multi": {1, 9, 20, 24, 27, 36, 37, 38, 39, 44, 47, 48, 49}, "online": {20, 27, 36, 38},
            "coop": {9, 38, 39, 48}, "couch": {24, 37, 39, 44}, "split": {24, 37, 39}, "lan": {47, 48}, "mmo": {20}}
STEAM_VR = {31, 53, 54}


DETAILS_V = 2


def steam_details(text, appid):
    """appdetails einer App: Genre-Gruppen, Mehrspieler-Arten aus den Kategorien, Erscheinungsjahr,
    VR, Zahl der Empfehlungen. None, wenn Steam die App nicht (mehr) liefert."""
    try:
        v = (json.loads(text) or {}).get(str(appid)) or {}
    except (ValueError, AttributeError):
        return None
    d = v.get("data") if v.get("success") else None
    if not isinstance(d, dict):
        return None
    cats = set()
    for c in d.get("categories") or []:
        try:
            cats.add(int(c.get("id")))
        except (TypeError, ValueError, AttributeError):
            pass
    gids = [str(g.get("id")) for g in d.get("genres") or [] if isinstance(g, dict)]
    m = re.search(r"(19|20)\d\d", str((d.get("release_date") or {}).get("date") or ""))
    if "29" in gids:
        cats.add(20)                    # Genre „Massively Multiplayer“ zählt wie die Kategorie MMO
    # Ab 0.7.1 (v 2) auch für die Einzelheiten: Metacritic, Kurzbeschreibung, Erscheinen, Firmen, Sprachen
    langs = [x for x in re.split(r"\s*,\s*", re.sub(r"<[^>]+>|\*", "", str(d.get("supported_languages") or ""))) if x.strip()]
    try:
        mc = int((d.get("metacritic") or {}).get("score"))
    except (TypeError, ValueError):
        mc = None
    desc = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", str(d.get("short_description") or ""))).split())
    names = lambda k: [str(x)[:80] for x in d.get(k) or [] if isinstance(x, str) and x.strip()][:3]
    return {"type": str(d.get("type") or ""), "name": str(d.get("name") or "")[:200],
            "genres": [STEAM_GENRES[x] for x in gids if x in STEAM_GENRES],
            "mp": [k for k, ids in STEAM_MP.items() if cats & ids], "vr": bool(cats & STEAM_VR),
            "year": m.group(0) if m else "",
            "recs": int(((d.get("recommendations") or {}).get("total")) or 0),
            "mc": mc, "desc": desc[:400], "date": str((d.get("release_date") or {}).get("date") or "")[:30],
            "devs": names("developers"), "pubs": names("publishers"), "langs": len(langs),
            "de": any(x.strip().casefold() in ("deutsch", "german") for x in langs), "v": DETAILS_V}


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


def steam_players(text):
    """GetNumberOfCurrentPlayers: Spieler gerade jetzt, None ohne gültige Antwort."""
    try:
        r = (json.loads(text) or {}).get("response") or {}
    except (ValueError, AttributeError):
        return None
    n = r.get("player_count")
    return n if r.get("result") == 1 and isinstance(n, int) and n >= 0 else None


_UPDATE = re.compile(r"\b(update|patch|hotfix|version|v\d+(?:\.\d+)+|release notes?|changelog)\b", re.I)


def steam_news(text):
    """GetNewsForApp: jüngste Meldung des Entwicklers, die nach Update klingt ({date, title}),
    oder {} wenn keine dabei ist; None ohne gültige Antwort."""
    try:
        items = ((json.loads(text) or {}).get("appnews") or {}).get("newsitems")
    except (ValueError, AttributeError):
        return None
    if not isinstance(items, list):
        return None
    best = {}
    for it in items:
        if not isinstance(it, dict) or not isinstance(it.get("date"), int):
            continue
        if it.get("feedname") != "steam_community_announcements" or not _UPDATE.search(str(it.get("title") or "")):
            continue
        if it["date"] > best.get("ts", 0):
            day = datetime.fromtimestamp(it["date"], timezone.utc).strftime("%Y-%m-%d")
            best = {"ts": it["date"], "date": day, "title": html.unescape(str(it.get("title") or ""))[:160]}
    best.pop("ts", None)
    return best


def _vrdb_text(page):
    t = re.sub(r"<script.*?</script>|<style.*?</style>|<!--.*?-->", "", page, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", "|", t))
    return re.sub(r"(\|\s*)+", "|", re.sub(r"\s+", " ", t))


def vrdb_game(page):
    """VRDB-Titelseite: Crossbuy, Version, Spielmodi, Meta-Wertung (Sterne, Anzahl, Anteil 4 und
    5 Sterne). None, wenn die Seite keinen dieser Werte trägt."""
    t = _vrdb_text(page)

    def field(name):
        m = re.search(r"\|" + re.escape(name) + r":\|([^|]{1,200})\|", t)
        return m.group(1).strip() if m else ""
    cb = field("Is Cross-Buy").lower()
    share = {}
    for m in re.finditer(r'aria-label="\d+% of reviews are (\d) stars?"[^>]*?aria-valuenow="([\d.]+)"', page):
        share.setdefault(int(m.group(1)), float(m.group(2)))
    stars = re.search(r"\|(\d(?:\.\d)?)\|[A-Za-z ]{0,40}\|([\d,.]+) ratings\|", t)
    out = {"crossbuy": True if cb == "yes" else False if cb == "no" else None,
           "version": field("Version")[:60], "modes": field("Game modes")[:120],
           "stars": float(stars.group(1)) if stars else None,
           "n": int(re.sub(r"[,.]", "", stars.group(2))) if stars else None,
           "pos": round(share.get(5, 0) + share.get(4, 0)) if len(share) >= 2 else None}
    if out["crossbuy"] is None and not out["version"] and out["pos"] is None:
        return None
    return out
