"""Die ganze PC-Sammlung für „Entdecken“ (collection.json im Datenordner).

Quelle ist der Playnite-Export (alle Spiele, alle Läden). Je Spiel werden beim Import feste
Merkmale berechnet: Art des Mehrspielers, höchste Spielerzahl, Genre-Gruppen, Wertung mit Quelle,
Jahr und Tag der Aufnahme. Unbekanntes bleibt leer und wird nicht geraten. Filter, Sortierung und
Zufall laufen in der Oberfläche über die fertige Liste. Ein neuer Import ersetzt die Liste;
was später je Spiel abgerufen wird (Feld „rev“), bleibt erhalten.
"""
import math
import re

from . import titles

FILE = "collection.json"
EMPTY = {"games": {}, "at": "", "n": 0}

# Bekannte Läden, wie Playnite sie unter Quelle (oder bei manchen als Kategorie) nennt
STORES = {"steam": "Steam", "gog": "GOG", "epic": "Epic", "epic games": "Epic", "itch.io": "itch", "itch": "itch",
          "indiegala": "Indiegala", "humble": "Humble", "amazon": "Amazon", "amazon games": "Amazon",
          "ea app": "EA", "origin": "EA", "ubisoft connect": "Ubisoft", "uplay": "Ubisoft", "battle.net": "Battle.net",
          "xbox": "Xbox", "microsoft store": "Xbox", "rockstar games": "Rockstar", "legacy games": "Legacy Games",
          "oculus": "Meta", "meta": "Meta", "bethesda": "Bethesda", "riot games": "Riot",
          "playstation": "PlayStation", "psn": "PlayStation"}

# Konsolen: Spiele nur dafür gehören nicht in die PC-Sammlung (Playnite und Sharenite führen sie mit)
_PC = re.compile(r"\bpc\b|windows|linux|mac ?os|steamos", re.I)
_CONSOLE = re.compile(r"playstation|\bps ?[1-5]\b|\bpsvr|\bvita\b|\bpsp\b|xbox|nintendo|\bswitch\b|\bwii", re.I)

# Mehrspieler-Art aus Features und Schlagwörtern (klein geschrieben)
MP_RULES = {
    "online": ("online multi-player", "online multiplayer", "online pvp", "online co-op", "supports online co-op",
               "massively multiplayer online (mmo)", "massively multiplayer", "battle royale", "mmo", "mmorpg",
               "cross-platform multiplayer", "online coop"),
    "coop": ("co-operative", "co-op", "online co-op", "supports online co-op", "local co-op", "supports couch co-op",
             "online coop", "coop", "couch co-op", "lan co-op"),
    "couch": ("supports couch co-op", "local co-op", "local multi-player", "local multiplayer", "shared/split screen",
              "split screen", "supports split-screen", "split screen pvp", "couch co-op"),
    "split": ("split screen", "supports split-screen", "shared/split screen", "split screen pvp"),
    "lan": ("supports lan or system-link play", "lan", "lan co-op", "lan pvp"),
    "mmo": ("massively multiplayer online (mmo)", "massively multiplayer", "mmo", "mmorpg"),
}
# Allgemein „Mehrspieler“: das Wort selbst oder jede der Arten oben
_MULTI = ("multiplayer", "multi-player", "pvp", "online pvp")
MP_LABEL = {"multi": "Mehrspieler", "online": "Online", "coop": "Koop", "couch": "Lokal", "split": "Splitscreen",
            "lan": "LAN", "mmo": "MMO"}
_PLAYERS = re.compile(r"^(\d{1,3}) players? in co-?op$")

# Genre-Gruppen: aus den Genres (IGDB) und einer kleinen Auswahl an Schlagwörtern
GENRES = {
    "Strategie": ("strategy", "turn-based strategy (tbs)", "real time strategy (rts)", "tactical", "4x",
                  "grand strategy", "turn-based tactics", "tower defense"),
    "Rollenspiel": ("role-playing (rpg)", "rpg", "jrpg", "action rpg", "crpg"),
    "Shooter": ("shooter", "fps", "third-person shooter", "shoot 'em up", "bullet hell", "twin stick shooter"),
    "Action": ("action", "hack and slash/beat 'em up", "action-adventure", "beat 'em up", "hack and slash"),
    "Abenteuer": ("adventure", "point-and-click", "point & click", "walking simulator"),
    "Puzzle": ("puzzle",),
    "Plattformer": ("platform", "platformer", "metroidvania", "precision platformer"),
    "Simulation": ("simulator", "simulation", "farming sim", "life sim"),
    "Aufbau": ("city builder", "base building", "colony sim", "management", "automation", "building"),
    "Rennen": ("racing", "driving"),
    "Sport": ("sport", "sports"),
    "Kampfspiel": ("fighting",),
    "Arcade": ("arcade",),
    "Karten und Brett": ("card & board game", "card game", "board game", "deckbuilding", "card battler"),
    "Horror": ("horror", "survival horror", "psychological horror"),
    "Roguelike": ("roguelike", "roguelite", "action roguelike"),
    "Survival": ("survival", "open world survival craft"),
    "Visual Novel": ("visual novel",),
    "Musik": ("music", "rhythm"),
    "Quiz": ("quiz/trivia", "trivia"),
    "Casual": ("casual",),
}
_GENRE_OF = {w: g for g, ws in GENRES.items() for w in ws}

MAX_GAMES = 20000


def store_of(text):
    """Bekannter Laden in einer Zelle wie „Steam“ oder „Epic, Favoriten“, sonst ""."""
    for part in str(text or "").split(","):
        s = STORES.get(part.strip().casefold())
        if s:
            return s
    return ""


def console_only(platforms, source=""):
    """Nur für Konsolen: alle genannten Plattformen sind Konsolen, oder es gibt keine Plattform und
    der Laden ist PlayStation. Steht auch ein PC dabei, zählt das Spiel."""
    plats = [p for p in platforms if p]
    if plats:
        return not any(_PC.search(p) for p in plats) and any(_CONSOLE.search(p) for p in plats)
    return store_of(source) == "PlayStation"


def _split(s):
    return [x.strip() for x in str(s or "").split(",") if x.strip()]


def features(feats, tags):
    """Mehrspieler-Art und höchste Spielerzahl. Splitscreen ohne Zahl gilt als mindestens 2."""
    words = {x.casefold() for x in feats + tags}
    mp = [k for k, ws in MP_RULES.items() if words & set(ws)]
    if mp or words & set(_MULTI) or any(_PLAYERS.match(w) for w in words):
        mp.insert(0, "multi")
    players = 0
    for w in words:
        m = _PLAYERS.match(w)
        if m:
            players = max(players, int(m.group(1)))
    if not players and ("couch" in mp or "split" in mp):
        players = 2
    return mp, players


def genres(gen, tags):
    out = []
    for w in gen + tags:
        g = _GENRE_OF.get(w.casefold())
        if g and g not in out:
            out.append(g)
    return out


def _score(s):
    s = str(s or "").strip()
    if not re.fullmatch(r"\d{1,3}", s):
        return None
    v = int(s)
    return v if 0 <= v <= 100 else None


def _date(s):
    """Tag als JJJJ-MM-TT aus „25.03.2020“, „2020-03-25“ oder „2020“ (dann nur das Jahr)."""
    s = str(s or "").strip()
    m = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)
    if m:
        return f"{m.group(3)}-{int(m.group(2)):02d}-{int(m.group(1)):02d}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return m.group(0)
    m = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)   # englisch: Monat/Tag/Jahr
    if m:
        return f"{m.group(3)}-{int(m.group(1)):02d}-{int(m.group(2)):02d}"
    m = re.fullmatch(r"(\d{4})", s)
    return m.group(1) if m else ""


def game_key(store, gid, name):
    if gid and store:
        return f"{store.casefold()}:{gid}"
    return "name:" + titles.norm(name)


def parse(text, rows=None):
    """Alle Spiele eines Playnite-Exports (versteckte bleiben draußen). rows: schon gelesene Zeilen."""
    from .imports import _col, _rows
    rows = rows if rows is not None else _rows(text)
    if not rows:
        return []
    h = rows[0]
    col = {
        "name": _col(h, "name", "titel", "title"),
        "id": _col(h, "spiel-id", "game id", "gameid", "spiel id"),
        "src": _col(h, "quelle", "source", "bibliothek", "library", "plattform", "platform"),
        "cat": _col(h, "kategorien", "categories"),
        "tags": _col(h, "schlagwörter", "tags"),
        "feat": _col(h, "features"),
        "gen": _col(h, "genres", "genre"),
        "comm": _col(h, "communitywertung", "community score"),
        "crit": _col(h, "expertenwertung", "critic score"),
        "user": _col(h, "nutzerwertung", "user score"),
        "rel": _col(h, "erscheinungsdatum", "release date"),
        "add": _col(h, "hinzugefügt", "added"),
        "dev": _col(h, "entwickler", "developers"),
        "hid": _col(h, "versteckt", "hidden"),
        "plat": _col(h, "plattformen", "platforms", "plattform", "platform"),
    }
    out = {}
    for row in rows[1:MAX_GAMES + 1]:
        def cell(k):
            c = col[k]
            return row[c].strip() if c is not None and c < len(row) else ""
        name = cell("name")
        if not name or cell("hid").casefold() in ("true", "ja", "1", "wahr"):
            continue
        store = store_of(cell("src")) or store_of(cell("cat"))
        if console_only(_split(cell("plat")), store):
            continue
        gid = cell("id")[:40]
        guess = False
        if not store and re.fullmatch(r"\d{1,7}", gid):
            store, guess = "Steam", True    # wie beim VR-Import: kleine Zahl ohne Laden ist vermutlich Steam
        tags, feats = _split(cell("tags")), _split(cell("feat"))
        mp, players = features(feats, tags)
        comm, crit = _score(cell("comm")), _score(cell("crit"))
        score, src = (comm, "Community") if comm is not None else (crit, "Kritik") if crit is not None else (None, "")
        g = {"name": name[:200], "store": store, "store_guess": guess, "id": gid if store else "",
             "mp": mp, "players": players, "genres": genres(_split(cell("gen")), tags)[:4],
             "score": score, "score_src": src, "critic": crit, "mine": _score(cell("user")),
             "released": _date(cell("rel")), "added": _date(cell("add")), "dev": _split(cell("dev"))[:1]}
        g["dev"] = g["dev"][0][:80] if g["dev"] else ""
        k = game_key(store, g["id"], name)
        if k in out:                                  # derselbe Eintrag doppelt: einer genügt
            continue
        out[k] = g
    return out


def replace(col, games, src="playnite"):
    """Neue Liste übernehmen, Abgerufenes je Spiel behalten. Gibt die Zahl der neuen Spiele zurück."""
    old = col.get("games") or {}
    new = 0
    for k, g in games.items():
        o = old.get(k)
        if o is None:
            new += 1
            continue
        for f in ("rev", "mark"):
            if f in o:
                g[f] = o[f]
    col["games"] = games
    col["at"] = titles.now_iso()
    col["n"] = len(games)
    col["src"] = src
    return new


def link(k, g):
    if g.get("store") == "Steam" and str(g.get("id") or "").isdigit():
        return f"https://store.steampowered.com/app/{g['id']}/"
    if g.get("store") == "GOG":
        return "https://www.gog.com/de/games?query=" + re.sub(r"\s+", "%20", re.sub(r"[^\w\s-]", "", g["name"]))
    return ""


def gem(g):
    """Geheimtipp-Wert G von 0 bis 1: gute Wertung w, wenig Bekanntheit n (Steam-Rezensionen).
    G = (w - 70) / 30 * (1 - log10(n + 1) / 5), 0 unter 70 oder ab 100.000 Rezensionen. Ohne
    Rezensionszahl geschätzt (zweiter Wert True): mit Expertenwertung gilt das Spiel als
    bekannter (Faktor 0,2), ohne als eher unbekannt (0,5)."""
    rev = g.get("rev") or {}
    n = rev.get("n") if isinstance(rev.get("n"), int) else None
    w = rev.get("pct") if n is not None and n >= 50 and rev.get("pct") is not None else g.get("score")
    if w is None or w < 70:
        return 0.0, n is None
    if n is not None:
        return (round((w - 70) / 30 * max(0.0, 1 - math.log10(n + 1) / 5), 2), False)
    return round((w - 70) / 30 * (0.2 if g.get("critic") is not None else 0.5), 2), True


def view(col):
    """Zeilen für die Oberfläche, kurz gehalten (bis zu einige tausend Spiele)."""
    rows = []
    for k, g in (col.get("games") or {}).items():
        r = {"key": k, "name": g["name"], "store": g.get("store") or "", "guess": bool(g.get("store_guess")), "mp": g.get("mp") or [],
             "players": g.get("players") or 0, "genres": g.get("genres") or [], "score": g.get("score"),
             "score_src": g.get("score_src") or "", "year": (g.get("released") or "")[:4],
             "added": g.get("added") or "", "dev": g.get("dev") or "", "url": link(k, g)}
        r["gem"], r["gem_guess"] = gem(g)
        rev = g.get("rev") or {}
        r["reviews"] = rev.get("n") if isinstance(rev.get("n"), int) else None
        if r["reviews"] is not None and r["reviews"] >= 50 and rev.get("pct") is not None:
            # Wertung von Steam, sobald genug Rezensionen da sind; Playnite bleibt Rückfall
            r["score"], r["score_src"] = rev["pct"], "Steam"
        if r["guess"] and r["reviews"]:
            r["guess"] = False              # Steam kennt die App und hat Rezensionen: Laden bestätigt
        rows.append(r)
    rows.sort(key=lambda r: titles.norm(r["name"]))
    return {"at": col.get("at") or "", "n": len(rows), "games": rows, "mp_label": MP_LABEL,
            "genres": sorted({x for r in rows for x in r["genres"]})}


def summary(col):
    return {"at": col.get("at") or "", "n": col.get("n") or len(col.get("games") or {})}
