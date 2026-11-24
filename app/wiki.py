"""Wikidata und die deutsche Wikipedia (0.10.16): deutsche Beschreibung, deutscher Titel, USK oder PEGI und
Spielerzahl für die Retro-Spiele, ohne Netz.

Je Spiel sucht der Abgleich bei Wikidata nach dem Namen (`wbsearchentities`), liest die Treffer gebündelt
(`wbgetentities`, bis zu 50 je Anfrage) und nimmt den ersten, der ein Videospiel ist und zum Spiel passt: dieselbe
Plattform oder, wo Wikidata das Spiel unter einer anderen Plattform führt (etwa die Konsolenfassung), dasselbe Jahr.
Aus dem Treffer kommen USK (P914), PEGI (P908), Spielerzahl (P1873), Erscheinen (P577), die deutsche Bezeichnung und der
Artikel der deutschen Wikipedia; dessen Einleitung (`prop=extracts`, bis zu 20 je Anfrage) ist die deutsche
Beschreibung. Die Namen der Plattformen und Freigaben sind selbst Einträge bei Wikidata; ihre Bezeichnungen holt der
Abgleich einmal und merkt sie sich (`wiki.json`), feste Kennungen stehen hier nicht.

Rangfolge in der Sammlung (collection.merge_wiki): die deutsche Beschreibung von GameTDB zuerst (sie gehört zur
gefundenen Fassung), sonst die der Wikipedia vor IGDB und libretro (englisch); Freigabe nur, wo keine steht; die
Spielerzahl bestätigt oder ergänzt."""
import json
import re
import urllib.parse

from . import sources, titles

API = "https://www.wikidata.org/w/api.php"
WIKI_API = "https://de.wikipedia.org/w/api.php"
# Wikimedia bittet um eine Kennung mit Kontakt: das öffentliche Repository
HEAD = {"User-Agent": f"vr-navigator/{sources.VERSION} (+https://github.com/GreenkeeperX/vr-navigator; privates Sammlungs-Tool)"}
FILE = "wiki.json"       # Bezeichnungen der Einträge für Plattformen und Freigaben: {"labels": {Q: Name}}
V = 1
DESC_MAX = 1200
# Systeme der Sammlung und wie Wikidata die Plattform nennt (englische Bezeichnung, klein)
PLATFORMS = {
    "NES": ("nintendo entertainment system", "family computer"), "SNES": ("super nintendo entertainment system", "super famicom"),
    "N64": ("nintendo 64",), "GameCube": ("gamecube", "nintendo gamecube"), "Wii": ("wii",), "Wii U": ("wii u",),
    "GB": ("game boy",), "GBC": ("game boy color",), "GBA": ("game boy advance",), "DS": ("nintendo ds",),
    "3DS": ("nintendo 3ds",), "VB": ("virtual boy",), "Pokémon Mini": ("pokémon mini",),
    "PS1": ("playstation",), "PS2": ("playstation 2",), "PS3": ("playstation 3",), "PSP": ("playstation portable",),
    "PS Vita": ("playstation vita",), "Mega Drive": ("sega genesis", "mega drive"), "Master System": ("master system",),
    "Game Gear": ("game gear",), "Saturn": ("sega saturn",), "Dreamcast": ("dreamcast",)}
_GAME = re.compile(r"(?i)video ?game|videospiel|computerspiel")


def search_url(name):
    return API + "?" + urllib.parse.urlencode({"action": "wbsearchentities", "search": name, "language": "en", "type": "item",
                                               "limit": 7, "format": "json"})


def entities_url(qids, props="claims|labels|sitelinks"):
    return API + "?" + urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(qids), "props": props,
                                               "languages": "de|en", "sitefilter": "dewiki", "format": "json"})


def extracts_url(articles):
    return WIKI_API + "?" + urllib.parse.urlencode({"action": "query", "prop": "extracts", "exintro": 1, "explaintext": 1,
                                                    "exlimit": 20, "redirects": 1, "titles": "|".join(articles),
                                                    "format": "json", "formatversion": 2})


def query_name(g):
    """Gesucht wird unter dem Namen bei IGDB (meist der englische Titel), sonst dem Namen ohne Klammern."""
    n = (g.get("igdb") or {}).get("name") or g.get("name") or ""
    n = re.sub(r"\s*[(\[].*?[)\]]", "", n).strip()
    m = re.match(r"(.+), (The|A|An)$", n)
    return f"{m.group(2)} {m.group(1)}" if m else n


def candidates(text):
    """Q-Kennungen der Suche, deren Beschreibung ein Videospiel nennt, in der Reihenfolge der Suche."""
    out = []
    for x in json.loads(text or "{}").get("search") or []:
        if _GAME.search(str(x.get("description") or "")) and re.fullmatch(r"Q\d+", str(x.get("id") or "")):
            out.append(x["id"])
    return out[:5]


def _vals(claims, p):
    """Werte einer Eigenschaft, bevorzugte zuerst, ohne veraltete."""
    cs = [c for c in claims.get(p) or [] if c.get("rank") != "deprecated"]
    cs.sort(key=lambda c: c.get("rank") != "preferred")
    out = []
    for c in cs:
        v = ((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v, dict) and "id" in v:
            out.append(v["id"])
        elif isinstance(v, dict) and "amount" in v:
            out.append(v["amount"])
        elif isinstance(v, dict) and "time" in v:
            out.append(v["time"])
        elif v is not None:
            out.append(v)
    return out


def entity(e):
    """Was von einem Eintrag gebraucht wird: {q, t (deutsche Bezeichnung), en, de (Artikel), plat, usk, pegi, players, years}."""
    claims = e.get("claims") or {}
    labels = e.get("labels") or {}
    players = []
    for a in _vals(claims, "P1873"):
        try:
            players.append(int(float(str(a))))
        except ValueError:
            pass
    years = sorted({m.group(1) for t in _vals(claims, "P577") if (m := re.match(r"[+-](\d{4})", str(t)))})
    return {"q": e.get("id") or "", "t": (labels.get("de") or {}).get("value") or "", "en": (labels.get("en") or {}).get("value") or "",
            "de": ((e.get("sitelinks") or {}).get("dewiki") or {}).get("title") or "",
            "plat": _vals(claims, "P400"), "usk": _vals(claims, "P914")[:1], "pegi": _vals(claims, "P908")[:1],
            "players": max([p for p in players if 0 < p < 100] or [0]), "years": years}


def entities(text):
    return {q: entity(e) for q, e in (json.loads(text or "{}").get("entities") or {}).items() if "missing" not in e}


def label_map(text):
    """Bezeichnungen (englisch, sonst deutsch) der Einträge für Plattformen und Freigaben."""
    out = {}
    for q, e in (json.loads(text or "{}").get("entities") or {}).items():
        lb = e.get("labels") or {}
        out[q] = ((lb.get("en") or lb.get("de") or {}).get("value") or "")[:80]
    return out


def needs_labels(ents, labels):
    return sorted({q for e in ents.values() for q in e["plat"] + e["usk"] + e["pegi"] if q not in labels})


def _plat_ok(e, system, labels):
    want = PLATFORMS.get(system) or ()
    names = [labels.get(q, "").lower() for q in e["plat"]]
    return any(n == w or n == "nintendo " + w for n in names for w in want)


def pick(qids, ents, g, labels):
    """Der erste Treffer, der passt: dieselbe Plattform; sonst ein Treffer ohne andere Plattform oder mit demselben Jahr."""
    year = (g.get("released") or "")[:4] or str((g.get("igdb") or {}).get("year") or "") or str((g.get("lr") or {}).get("year") or "")
    for q in qids:
        e = ents.get(q)
        if e and _plat_ok(e, g.get("system") or "", labels):
            return e, "plat"
    for q in qids:
        e = ents.get(q)
        if e and year and year in e["years"]:
            return e, "year"
    return None, ""


def _rating(qs, labels, org):
    """„USK ab 12“, „USK 12“, „PEGI 7“ → [ORG, „12“]."""
    for q in qs:
        m = re.search(r"(\d{1,2})", labels.get(q, ""))
        if m and org.lower() in labels.get(q, "").lower():
            return [org, m.group(1)]
    return None


def extracts(text):
    """{Artikel: Einleitung}; auch unter dem angefragten Namen, wenn die Wikipedia weiterleitet."""
    q = json.loads(text or "{}").get("query") or {}
    back = {}
    for x in (q.get("normalized") or []) + (q.get("redirects") or []):
        back.setdefault(x.get("to"), []).append(x.get("from"))
    out = {}
    for p in q.get("pages") or []:
        ex = " ".join(str(p.get("extract") or "").split())
        if not ex or p.get("missing"):
            continue
        ex = short(ex)
        t = p.get("title") or ""
        out[t] = ex
        for f in back.get(t, []):
            out[f] = ex
            for f2 in back.get(f, []):
                out[f2] = ex
    return out


def short(text, n=DESC_MAX):
    """Höchstens n Zeichen, am Satzende gekürzt."""
    if len(text) <= n:
        return text
    cut = text[:n]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    return (cut[:end + 1] if end > n // 3 else cut.rstrip() + " …")


def compact(e, via, labels, desc=""):
    out = {"q": e["q"], "via": via}
    if e["t"] and titles.norm(e["t"]) != titles.norm(e["en"]):
        out["t"] = e["t"][:200]
    if e["de"]:
        out["de"] = e["de"][:200]
    if desc:
        out["desc"] = desc
    age = _rating(e["usk"], labels, "USK") or _rating(e["pegi"], labels, "PEGI")
    if age:
        out["age"] = age
    if e["players"]:
        out["players"] = e["players"]
    if e["years"]:
        out["year"] = e["years"][0]
    return out


def wanted(g):
    """Retro-Spiele aller Systeme."""
    return g.get("src") == "retro"
