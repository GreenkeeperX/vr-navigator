"""Die ganze Spielesammlung für „Entdecken“ (collection.json im Datenordner), je Spiel mit System
(PC, PS4 …); ältere Dateien ohne System gelten als PC.

Quelle ist der Playnite-Export (alle Spiele, alle Läden). Je Spiel werden beim Import feste
Merkmale berechnet: Art des Mehrspielers, höchste Spielerzahl, Genre-Gruppen, Wertung mit Quelle,
Jahr und Tag der Aufnahme. Unbekanntes bleibt leer und wird nicht geraten. Filter, Sortierung und
Zufall laufen in der Oberfläche über die fertige Liste. Ein neuer Import ersetzt die Liste;
was später je Spiel abgerufen wird (Feld „rev“), bleibt erhalten.
"""
import math
import re

from . import eingaben, flat2vr, igdb, sources, titles, wheel  # eingaben: Nutzerfelder beim Lesen (0.11.0)
from . import store as datastore      # „store“ heißt hier sonst der Launcher

FILE = "collection.json"
EMPTY = {"games": {}, "at": "", "n": 0}

# Bekannte Läden, wie Playnite sie unter Quelle (oder bei manchen als Kategorie) nennt
STORES = {"steam": "Steam", "gog": "GOG", "epic": "Epic", "epic games": "Epic", "itch.io": "itch", "itch": "itch",
          "indiegala": "Indiegala", "humble": "Humble", "amazon": "Amazon", "amazon games": "Amazon",
          "ea app": "EA", "origin": "EA", "ubisoft connect": "Ubisoft", "uplay": "Ubisoft", "battle.net": "Battle.net",
          "xbox": "Xbox", "microsoft store": "Xbox", "rockstar games": "Rockstar", "legacy games": "Legacy Games",
          "oculus": "Meta", "meta": "Meta", "bethesda": "Bethesda", "riot games": "Riot",
          "playstation": "PlayStation", "psn": "PlayStation"}

# Konsolen: Spiele nur dafür zählen nicht als VR-Titel am PC (Playnite und Sharenite führen sie mit);
# in der Sammlung stehen sie unter ihrem System
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
    "Shooter": ("shooter", "fps", "third-person shooter", "shoot 'em up", "bullet hell", "twin stick shooter",
                "shoot'em up", "lightgun shooter"),
    "Action": ("action", "hack and slash/beat 'em up", "action-adventure", "beat 'em up", "hack and slash", "beat'em up"),
    "Abenteuer": ("adventure", "point-and-click", "point & click", "walking simulator"),
    "Puzzle": ("puzzle", "thinking"),
    "Plattformer": ("platform", "platformer", "metroidvania", "precision platformer"),
    "Simulation": ("simulator", "simulation", "farming sim", "life sim"),
    "Aufbau": ("city builder", "base building", "colony sim", "management", "automation", "building"),
    "Rennen": ("racing", "driving"),
    "Sport": ("sport", "sports", "hunting and fishing", "sports with animals"),
    "Kampfspiel": ("fighting",),
    "Arcade": ("arcade", "pinball"),
    "Karten und Brett": ("card & board game", "card game", "board game", "deckbuilding", "card battler", "board", "card",
                         "gambling"),
    "Horror": ("horror", "survival horror", "psychological horror"),
    "Roguelike": ("roguelike", "roguelite", "action roguelike"),
    "Survival": ("survival", "open world survival craft"),
    "Visual Novel": ("visual novel",),
    "Musik": ("music", "rhythm", "music / dancing"),
    "Quiz": ("quiz/trivia", "trivia", "quiz"),
    "Casual": ("casual", "casual game"),
    # Ab 0.8.8 für Retro (libretro, deine Ordner-Liste)
    "Party": ("party",),
    "Lernspiel": ("educational",),
}
# Ab 0.10.13 die Wörter von GameTDB, soweit oben noch nicht dabei
for _g, _ws in {"Rollenspiel": ("role-playing",), "Plattformer": ("2d platformer", "3d platformer"),
                "Shooter": ("first-person shooter", "rail shooter", "light gun shooter"), "Party": ("minigame collection", "mini games"),
                "Rennen": ("kart racing",), "Simulation": ("life simulation", "pet simulation"), "Lernspiel": ("training", "education")}.items():
    GENRES[_g] += _ws
_GENRE_OF = {w: g for g, ws in GENRES.items() for w in ws}

MAX_GAMES = 20000


def store_of(text):
    """Bekannter Laden in einer Zelle wie „Steam“ oder „Epic, Favoriten“, sonst ""."""
    for part in str(text or "").split(","):
        s = STORES.get(part.strip().casefold())
        if s:
            return s
    return ""


# Kennungen aus der PlayStation-Bibliothek von Playnite, etwa CUSA01234_00 oder NPWR01234_00
_PSN_ID = re.compile(r"^[A-Z]{4}\d{5}(?:_\d{2})?$")


def console_only(platforms, source="", gid=""):
    """Nur für Konsolen: alle genannten Plattformen sind Konsolen, oder es gibt keine Plattform und
    der Laden ist PlayStation oder die Kennung eine von PlayStation. Steht auch ein PC dabei,
    zählt das Spiel."""
    plats = [p for p in platforms if p]
    if plats:
        return not any(_PC.search(p) for p in plats) and any(_CONSOLE.search(p) for p in plats)
    return store_of(source) == "PlayStation" or bool(_PSN_ID.match(str(gid or "").strip()))


# Systeme aus der Plattform-Spalte, das genauere Muster zuerst; Namen wie Playnite sie schreibt
# („Sony PlayStation 4“, „Nintendo Game Boy Advance“, „Microsoft Xbox One“)
SYSTEMS = [
    ("PS5", r"playstation ?5|\bps ?5\b"), ("PS4", r"playstation ?4|\bps ?4\b"), ("PS3", r"playstation ?3|\bps ?3\b"),
    ("PS2", r"playstation ?2|\bps ?2\b"), ("PS Vita", r"\bvita\b"), ("PSP", r"\bpsp\b|playstation portable"),
    ("PS1", r"playstation(?! ?[2-5])|\bps ?1\b|\bpsx\b"),
    ("Xbox Series", r"xbox series"), ("Xbox One", r"xbox one"), ("Xbox 360", r"xbox 360"), ("Xbox", r"xbox"),
    ("Switch 2", r"\bswitch ?2\b"), ("Switch", r"\bswitch\b"), ("Wii U", r"wii ?u\b"), ("Wii", r"\bwii\b"), ("GameCube", r"gamecube"),
    ("N64", r"nintendo 64|\bn64\b"), ("SNES", r"super nintendo|\bsnes\b|super famicom"),
    ("NES", r"nintendo entertainment system|\bnes\b|famicom"), ("3DS", r"\b3ds\b"), ("DS", r"\bds(i)?\b"),
    ("GBA", r"game ?boy advance|\bgba\b"), ("GBC", r"game ?boy colou?r|\bgbc\b"), ("GB", r"game ?boy|\bgb\b"),
    ("VB", r"virtual boy|\bvb\b"),
]
_SYSTEMS = [(n, re.compile(p, re.I)) for n, p in SYSTEMS]
# PlayStation-Kennungen ohne Plattform: CUSA/PLAS PS4, PPSA PS5, NPWR PS3 oder Vita, sonst nur „PS“ unbestimmt.
# Die erste PlayStation heißt seit 0.6.1 „PS1“ (vorher „PS“)
# NPWR… sind Trophäenlisten: Playnite führt so Spiele von PS3 und PS Vita, ohne zu sagen, von welcher
_PSN_SYS = {"CUSA": "PS4", "PLAS": "PS4", "PPSA": "PS5", "PCSA": "PS Vita", "PCSB": "PS Vita", "PCSE": "PS Vita",
            "NPWR": "PS3 / Vita"}


def system_of(platforms, source="", gid=""):
    """System eines Spiels aus den Plattformen: PC, sobald ein PC dabei ist (wie bisher in der
    Sammlung), sonst die erste erkannte Konsole. Ohne Plattform zählt eine Kennung von PlayStation
    (CUSA… ist PS4), sonst PC. Unbekannte Plattformen ergeben ebenfalls PC."""
    plats = [p for p in platforms if p]
    if plats and not any(_PC.search(p) for p in plats):
        for p in plats:
            for name, rx in _SYSTEMS:
                if rx.search(p):
                    return name
    if not plats and console_only([], source, gid):
        return _PSN_SYS.get(str(gid or "").strip()[:4].upper(), "PS")
    return "PC"


# Systeme, die nur aus der Retro-Liste kommen (siehe retro.py)
EXTRA_ORDER = ["Pokémon Mini", "Mega Drive", "Master System", "Game Gear", "Saturn", "Dreamcast", "PC Engine",
               "Neo Geo Pocket", "WonderSwan", "Lynx", "Atari 2600", "Atari 7800"]


def system_order(name):
    """Reihenfolge der Reiter: PC vorn, dann wie in SYSTEMS."""
    names = ["PC"] + [n for n, _ in SYSTEMS] + EXTRA_ORDER
    names.insert(names.index("PS3") + 1, "PS3 / Vita")
    names.insert(names.index("PS1") + 1, "PS")       # PlayStation ohne erkennbare Generation
    return names.index(name) if name in names else len(names)


def _split(s):
    return [x.strip() for x in str(s or "").split(",") if x.strip()]


def features(feats, tags):
    """Mehrspieler-Art und höchste Spielerzahl, soweit Playnite sie nennt („4 players in co-op“)."""
    words = {x.casefold() for x in feats + tags}
    mp = [k for k, ws in MP_RULES.items() if words & set(ws)]
    if mp or words & set(_MULTI) or any(_PLAYERS.match(w) for w in words):
        mp.insert(0, "multi")
    players = 0
    for w in words:
        m = _PLAYERS.match(w)
        if m:
            players = max(players, int(m.group(1)))
    # Bis 0.9.4 galt Splitscreen ohne Zahl als 2; ab 0.9.5 bleibt die Zahl offen (keine geratene Zahl)
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


def game_key(store, gid, name, system="PC"):
    if gid and store:
        return f"{store.casefold()}:{gid}"
    # ohne Kennung: der Name, bei Konsolen mit System davor (dasselbe Spiel am PC und auf der PS4)
    return "name:" + ("" if system == "PC" else system.casefold() + ":") + titles.norm(name)


def parse(text, rows=None, stats=None):
    """Alle Spiele eines Playnite-Exports mit System (versteckte bleiben draußen). rows: schon
    gelesene Zeilen; stats bekommt die Zahl je System unter „systems“ und die der
    Konsolenspiele unter „console“."""
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
        "pub": _col(h, "publisher", "publishers", "verlag", "verleger"),
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
        system = system_of(_split(cell("plat")), store, cell("id"))
        if is_ps(system):                   # 0.10.11: PlayStation kommt später aus dem ROM-Ordner, nicht aus Playnite
            if stats is not None:
                stats["ps"] = stats.get("ps", 0) + 1
            continue
        gid = cell("id")[:40]
        guess = False
        if system == "PC" and not store and re.fullmatch(r"\d{1,7}", gid):
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
        pub = _split(cell("pub"))
        if pub:
            g["pub"] = pub[0][:80]
        if system != "PC":
            g["system"] = system
        k = game_key(store, g["id"], name, system)
        if k in out:                                  # derselbe Eintrag doppelt: einer genügt
            continue
        out[k] = g
        if stats is not None:
            stats.setdefault("systems", {})[system] = stats.get("systems", {}).get(system, 0) + 1
            if system != "PC":
                stats["console"] = stats.get("console", 0) + 1
    return out


# 0.10.11 (Entscheidung 02.11.2026): PlayStation-Spiele kommen später über den ROM-Ordner (Retro-Liste); aus Playnite,
# Sharenite und der gg.deals-Sammlung nimmt die Sammlung keine, auch wenn der Export sie enthält
def is_ps(system):
    return str(system or "").startswith("PS")


def drop_ps(col):
    """PlayStation-Spiele, die nicht aus der Retro-Liste stammen (frühere Playnite-Exporte), fallen weg. Gibt ihre Zahl zurück."""
    games = col.get("games") or {}
    gone = [k for k, g in games.items() if is_ps(g.get("system")) and g.get("src") != "retro"]
    for k in gone:
        del games[k]
    if gone:
        col["n"] = len(games)
    return len(gone)


def replace(col, games, src="playnite"):
    """Neue Liste übernehmen, Abgerufenes je Spiel behalten. Ersetzt werden nur die Systeme, die
    in der neuen Liste vorkommen: ein Export nur der PlayStation-Bibliothek lässt die PC-Spiele
    stehen, ebenso die Spiele aus der Retro-Liste. Gibt die Zahl der neuen Spiele zurück."""
    old = col.get("games") or {}
    systems = {g.get("system") or "PC" for g in games.values()}
    # Spiele aus der Retro-Liste, dem eShopKompass und VR-Titel am PC (0.8.9) gehören nicht zum Playnite-Export und
    # bleiben immer stehen
    games = dict({k: g for k, g in old.items() if ((g.get("system") or "PC") not in systems or g.get("src") in ("retro", ESHOP, PCVR, STEAMACCT, GGCOLL))
                  and k not in games}, **games)
    new = 0
    for k, g in games.items():
        o = old.get(k)
        if o is None:
            new += 1
            continue
        for f in ("rev", "steam", "mark", "igdb", "pcgw", "nexus", "stag", "tdb", "deku", "wiki"):
            if f in o:
                g[f] = o[f]
    col["games"] = games
    drop_ps(col)
    col["at"] = titles.now_iso()
    col["n"] = len(games)
    col["src"] = src
    return new


ESHOP = "eshop"
ESHOP_MAX = 5000
PCVR = "pcvr"           # 0.8.9: deine VR-Titel am PC, die Playnite nicht kennt
STEAMACCT = "steamacct"  # 0.9.7: Spiele aus deinem Steam-Konto, die Playnite nicht kennt
GGCOLL = "ggcoll"        # 0.9.9: Spiele aus deiner gg.deals-Sammlung (Lesezeichen), die sonst keine Quelle kennt


def _pl(v):
    """Spielerspanne [von, bis] aus dem eShopKompass, sonst None."""
    return [int(v[0]), int(v[1])] if isinstance(v, list) and len(v) == 2 and all(isinstance(x, int) for x in v) else None


# Zeile der Ansicht „Spiele“ im eShopKompass (ab 1.7.17 unter "kv"): nur diese Felder, Text und Listen gekürzt
ESHOP_KV = ("genre", "players", "max", "coop", "modes", "gs", "paid_online", "s2", "via", "mc", "mcu", "oc", "hltb",
            "hours", "size_gb", "year", "year_ok", "year_alt", "released", "developer", "publisher", "pub_alt",
            "usk", "pegi", "langs", "nin", "read", "pack", "ed")


def _plain_json(v, depth=0):
    """Nur einfache Werte (Text, Zahl, ja/nein, Listen, Wörterbücher), gekürzt; alles andere fällt weg."""
    if v is None or isinstance(v, (bool, int, float)):
        return v
    if isinstance(v, str):
        return v[:300]
    if depth >= 3:
        return None
    if isinstance(v, list):
        return [_plain_json(x, depth + 1) for x in v[:40]]
    if isinstance(v, dict):
        return {str(k)[:40]: _plain_json(x, depth + 1) for k, x in list(v.items())[:30]}
    return None


def from_eshop(items):
    """Spiele aus der Sammlung des eShopKompass (/api/sammlung) als Einträge der Sammlung, Schlüssel
    eshop:<slug>. Nur, was dort steht; was fehlt oder nicht passt, fällt weg."""
    out = {}
    for e in items[:ESHOP_MAX] if isinstance(items, list) else []:
        if not isinstance(e, dict) or not str(e.get("slug") or "").strip() or not str(e.get("title") or "").strip():
            continue
        slug = re.sub(r"[^a-z0-9-]", "", str(e["slug"]).lower())[:120]
        txt = lambda k, n=200: str(e.get(k) or "").strip()[:n]
        num = lambda k: e[k] if isinstance(e.get(k), (int, float)) and not isinstance(e.get(k), bool) else None
        off, loc, on = _pl(e.get("offline")), _pl(e.get("local")), _pl(e.get("online"))
        mp = [x for x, ok in (("couch", off and off[1] > 1), ("online", on and on[1] > 1 or e.get("online_any") is True),
                              ("coop", e.get("coop") is True)) if ok]
        mine = e.get("mine") if isinstance(e.get("mine"), dict) else {}
        out[f"{ESHOP}:{slug}"] = {
            "name": txt("title"), "system": "Switch 2" if e.get("system") == "Switch 2" else "Switch", "src": ESHOP,
            "store": "Nintendo", "id": slug, "genres": [str(x)[:40] for x in e.get("genres") or [] if isinstance(x, str)][:12],
            "mp": (["multi"] if mp else []) + mp, "players": int(e["max"]) if isinstance(e.get("max"), int) else 0,
            "pl": {k: v for k, v in (("offline", off), ("local", loc), ("online", on)) if v},
            "mc": num("mc"), "oc": num("oc"), "hours": num("hours"), "released": txt("released", 10),
            "dev": txt("developer"), "pub": txt("publisher"), "usk": txt("usk", 4), "desc": txt("desc", 1200),
            "desc_lang": "en" if e.get("desc_lang") == "en" else "de",
            "langs": [str(x)[:20] for x in e.get("langs") or [] if isinstance(x, str)][:40],
            "added": txt("bought", 10),
            "kv": {k: _plain_json(v) for k, v in (e.get("kv") if isinstance(e.get("kv"), dict) else {}).items() if k in ESHOP_KV},
            "ext_mine": {k: v for k, v in mine.items() if k in ("s", "fav", "ign") and isinstance(v, (str, bool))}}
    return out


def replace_eshop(col, games):
    """Die Spiele des eShopKompass ersetzen; alle anderen bleiben. Gibt (neu, entfallen) zurück."""
    old = col.get("games") or {}
    before = {k for k, g in old.items() if g.get("src") == ESHOP}
    for k in before - set(games):
        old.pop(k)
    old.update(games)
    col["games"] = old
    col["n"] = len(old)
    col["eshop_at"] = titles.now_iso()
    return len(set(games) - before), len(before - set(games))


def link(k, g):
    if g.get("store") == "Steam" and str(g.get("id") or "").isdigit():
        return f"https://store.steampowered.com/app/{g['id']}/"
    if g.get("src") == GGCOLL and re.fullmatch(r"[a-z0-9-]{1,150}", str(g.get("id") or "")):
        return f"https://gg.deals/game/{g['id']}/"
    if g.get("store") == "GOG":
        return "https://www.gog.com/de/games?query=" + re.sub(r"\s+", "%20", re.sub(r"[^\w\s-]", "", g["name"]))
    return ""


def gem(g):
    """Geheimtipp-Wert G von 0 bis 1: gute Wertung w, wenig Bekanntheit n (Steam-Rezensionen).
    G = (w - 70) / 30 * (1 - log10(n + 1) / 5), 0 unter 70 oder ab 100.000 Rezensionen. Nur mit
    mindestens 50 Rezensionen; sonst 0 und zweiter Wert True (noch keine Aussage). Die
    Wertungen aus Playnite zählen nicht (Entscheidung 22.10.2026: zu unzuverlässig)."""
    rev = g.get("rev") or {}
    n = rev.get("n") if isinstance(rev.get("n"), int) else None
    w = rev.get("pct")
    if n is None or n < 50 or w is None:
        return 0.0, True
    if w < 70:
        return 0.0, False
    return round((w - 70) / 30 * max(0.0, 1 - math.log10(n + 1) / 5), 2), False


STEAM_CAN = {"Action", "Strategie", "Rollenspiel", "Casual", "Rennen", "Sport", "Abenteuer", "Simulation"}


def check(r, st):
    """Playnite mit den Steam-Details abgleichen. Was beide sagen, gilt als bestätigt (gc, mpc,
    year_ok); was nur eine Quelle sagt, bleibt drin und wird in der Oberfläche mit ≈ markiert.
    Genres, die Steam gar nicht kennt (Puzzle, Horror …), kann Steam weder bestätigen noch
    widerlegen: sie stehen in gx. src: „steam“ (abgeglichen) oder „playnite“ (nur eine Quelle)."""
    r["src"], r["gc"], r["gx"], r["mpc"], r["year_ok"], r["vr"] = "playnite", [], [], [], False, False
    if not st.get("ok"):
        return
    r["src"], r["vr"], r["guess"] = "steam", bool(st.get("vr")), False
    sg, sm = set(st.get("genres") or []), set(st.get("mp") or [])
    r["gc"] = [x for x in r["genres"] if x in sg]
    r["gx"] = [x for x in r["genres"] if x not in STEAM_CAN]
    r["genres"] = r["genres"] + sorted(sg - set(r["genres"]))
    r["mpc"] = [x for x in r["mp"] if x in sm]
    r["mp"] = r["mp"] + [x for x in MP_LABEL if x in sm and x not in r["mp"]]
    # Einzelheiten (0.7.1): Steam vor Playnite bei Entwickler und Verlag
    if st.get("xp"):
        r["xp"] = {"on": True, "with": [], "src": "Steam"}       # 0.10.0: Kategorie „Plattformübergreifender Mehrspielermodus“
    r.update(mc=st.get("mc"), desc=st.get("desc") or "", sdate=st.get("date") or "",
             slangs=st.get("langs") or 0, sde=st.get("de"))
    if st.get("devs"):
        r["dev"] = ", ".join(st["devs"])
    if st.get("pubs"):
        r["pub"] = ", ".join(st["pubs"])
    y = st.get("year") or ""
    r["year_ok"], r["syear"] = bool(y) and y == r["year"], y
    if y and not r["year"]:
        r["year"] = y                   # nur Steam kennt das Jahr: übernommen, ≈


def merge_pcgw(r, pc):
    """PCGamingWiki (0.9.5): Spieler je Art aus „Network/Multiplayer“ (lokal, LAN, online). Nennen IGDB und
    PCGamingWiki dieselbe Zahl, gilt sie als bestätigt; sonst gilt PCGamingWiki (am PC gepflegt), IGDBs Zahl
    bleibt als dritter Wert für den Tooltip. Die Arten zählen wie bei Steam und IGDB zum Abgleich."""
    if not pc.get("page"):
        return
    # Crossplay (0.10.0): PCGamingWiki nennt auch die Plattformen; sagt Steam ja und PCGamingWiki nein, steht der Widerspruch da
    sx = r.get("xp")
    if pc.get("xp") is True:
        r["xp"] = {"on": True, "with": pc.get("xpw") or [], "src": "PCGamingWiki, Steam" if sx else "PCGamingWiki"}
    elif pc.get("xp") is False:
        r["xp"] = dict(sx, doubt="PCGamingWiki: kein Crossplay") if sx else {"on": False, "with": [], "src": "PCGamingWiki"}
    kinds = list(pc.get("mp") or []) + (["coop"] if pc.get("coop") else [])
    if kinds:
        r["srcs"] = r.get("srcs", []) + ["PCGamingWiki"]
        r["mpc"] = list(dict.fromkeys((r.get("mpc") or []) + [x for x in r["mp"] if x in kinds + ["multi"]]))
        r["mp"] = (["multi"] if "multi" not in r["mp"] else []) + r["mp"] + [x for x in kinds if x not in r["mp"]]
    plm = r.setdefault("plm", {})
    for m, n in (pc.get("pl") or {}).items():
        if not isinstance(n, int) or n < 2:
            continue
        old = plm.get(m)
        plm[m] = [n, "IGDB, PCGamingWiki"] if old and old[0] == n else [n, "PCGamingWiki"] + ([old[0]] if old else [])
    if plm:
        top = max(v[0] for v in plm.values())
        r["players"] = top
        r["pl_src"] = ", ".join(sorted({x for v in plm.values() if v[0] == top for x in v[1].split(", ")}))


def merge_igdb(r, ig):
    """IGDB (0.8.0) in eine Zeile, mit fester Rangfolge je Feld. Was IGDB und eine andere Quelle beide sagen,
    gilt als bestätigt (gc, mpc wie beim Abgleich mit Steam); was nur eine sagt, zeigt die Oberfläche violett.
    - Wertung: Steam-Rezensionen (ab 50), sonst IGDB-Kritiken (ab 3), sonst IGDB gesamt (ab 10); Ersatz ist
      IGDB gesamt und am PC jede IGDB-Wertung
    - Spielzeit: IGDB (normal, sonst eilig)
    - Spieler: IGDB (höchste Zahl online oder an einer Konsole), sonst Playnite (Ersatz)
    - Genre und Mehrspieler: alle Quellen zusammen, bestätigt, was zwei nennen
    - Beschreibung, Jahr, Entwickler, Verlag: Steam, sonst IGDB (Beschreibung auf Englisch)"""
    r["ig"], r["srcs"] = True, r.get("srcs", []) + ["IGDB"]
    ig_g = genres(ig.get("genres") or [], [])
    # Kennt sonst keine Quelle Genres (Konsolen, Retro), widerspricht niemand: dann gilt IGDB als bestätigt
    r["gc"] = list(dict.fromkeys((r.get("gc") or []) + [x for x in r["genres"] if x in ig_g] + (ig_g if not r["genres"] else [])))
    r["genres"] = r["genres"] + [x for x in ig_g if x not in r["genres"]]
    ig_m = igdb.mp_kinds(ig)
    r["mpc"] = list(dict.fromkeys((r.get("mpc") or []) + [x for x in r["mp"] if x in ig_m] + (ig_m if not r["mp"] else [])))
    r["mp"] = r["mp"] + [x for x in ig_m if x not in r["mp"]]
    # Spieler je Art (0.9.5): online, lokal, Koop online, Koop lokal; als [Zahl, Quelle]
    plm = r.setdefault("plm", {})
    for m, f in (("online", "on"), ("couch", "off"), ("coop_on", "coop_on_n"), ("coop_off", "coop_off_n")):
        if (ig.get(f) or 0) > 1:
            plm[m] = [int(ig[f]), "IGDB"]
    n = max(ig.get("on") or 0, ig.get("off") or 0)
    if n > 1:
        r["players"], r["pl_src"] = n, "IGDB"
    elif r["players"]:
        r["pl_src"] = "Playnite"
    if r["score"] is None:
        if ig.get("crit") is not None:
            r.update(score=ig["crit"], score_src="IGDB Kritik", score_n=ig.get("crit_n") or 0)
        elif ig.get("total") is not None:
            r.update(score=ig["total"], score_src="IGDB gesamt", score_n=ig.get("total_n") or 0, score_alt=True)
        if r["score"] is not None and r["system"] == "PC":
            r["score_alt"] = True           # am PC zählt Steam zuerst, IGDB ist Ersatz
    if ig.get("crit") is not None and r["score_src"] != "IGDB Kritik":
        r["icrit"] = ig["crit"]
    h = ig.get("hours") or {}
    if h.get("h"):
        r.update(hours=h["h"], hours_all=h.get("all"), hours_n=h.get("n") or 0, hours_src="IGDB")
    if not r.get("desc") and ig.get("desc"):
        r["desc"], r["desc_lang"], r["desc_src"] = ig["desc"], "en", "IGDB"
    if not r["year"] and ig.get("year"):
        r["year"], r["year_src"] = ig["year"], "IGDB"
    if ig.get("year") and r.get("src") != "steam":
        r["year_ok"] = r["year"] == ig["year"]
    r["iyear"] = ig.get("year") or ""
    # 0.10.12: genauer Tag von IGDB, wenn sonst keiner da ist und das Jahr passt (Erschienen in den Einzelheiten)
    if not r.get("rel") and ig.get("date") and ig["date"][:4] == r["year"]:
        r["rel"] = ig["date"]
    if not r["dev"] and ig.get("dev"):
        r["dev"] = ig["dev"]
    if not r["pub"] and ig.get("pub"):
        r["pub"] = ig["pub"]
    if ig.get("name") and titles.norm(ig["name"]) != titles.norm(r["name"]):
        r["iname"] = ig["name"]


_VR_NAME = re.compile(r"(?i)(?<![\w-])VR(?![\w-])")


def vr_name(name):
    """Nennt der Name VR als eigenes Wort („Moon Rover VR“, nicht „Revolver“)? Nur ein Hinweis."""
    return bool(_VR_NAME.search(name or ""))


def _pcvr_wanted(col, data):
    """Deine VR-Titel am PC, die Playnite nicht kennt (am PC gekauft oder bei Meta mit Crossbuy), als Spiele der
    Sammlung: {„pcvr:<Titel>“: Spiel}. Wie in _pc_vr gleicht das Tool über Steam-ID und Namen ab."""
    from . import library
    ids, names = set(), set()
    for g in (col.get("games") or {}).values():
        if g.get("src") in (PCVR, "retro", ESHOP) or (g.get("system") or "PC") != "PC":
            continue
        if g.get("store") == "Steam" and str(g.get("id") or "").isdigit():
            ids.add(str(g["id"]))
        names.add(titles.base_norm(g["name"]))
    out = {}
    for k, t in data["titles"].items():
        o = t.get("owned") or {}
        if not (o.get("pc") or (o.get("meta") and library.crossbuy(t)[0])) or titles.is_bundle(t):
            continue
        sid = str(t.get("steam_appid") or "")
        if (sid and sid in ids) or titles.base_norm(t["name"]) in names:
            continue
        label = (o.get("pc") or {}).get("label") or ("Meta (Crossbuy)" if not o.get("pc") else "PC")
        out["pcvr:" + k] = {"name": t["name"], "system": "PC", "src": PCVR, "store": label, "id": sid if sid.isdigit() else "",
                            "from_vr": k, "added": t.get("added") or "", "mp": [], "players": 0, "genres": [],
                            "released": "", "dev": "", "pub": ""}
    return out


def sync_pcvr(col, data):
    """VR-Titel am PC ohne Playnite-Eintrag als eigene Spiele in collection.json (0.8.9), damit Steam-Details,
    Rezensionen, IGDB, PCGamingWiki und Nexus sie wie jedes Spiel abrufen. Abgerufenes bleibt; kennt Playnite den
    Titel inzwischen oder gilt er nicht mehr, fällt er weg. Gibt (neu, entfallen) zurück."""
    games = col.setdefault("games", {})
    want = _pcvr_wanted(col, data)
    gone = [k for k, g in games.items() if g.get("src") == PCVR and k not in want]
    for k in gone:
        del games[k]
    new = 0
    for k, g in want.items():
        o = games.get(k)
        if o is None:
            new += 1
        else:
            for f in ("rev", "steam", "mark", "igdb", "pcgw", "nexus", "stag", "tdb", "deku", "wiki"):
                if f in o:
                    g[f] = o[f]
        games[k] = g
    col["n"] = len(games)
    return new, len(gone)


def sync_steam(col, data):
    """Spiele aus deinem Steam-Konto (GetOwnedGames, data["steam_play"]), die weder Playnite noch die VR-Titel am PC
    kennen, als eigene Spiele unter „steam:<App-ID>“ (0.9.7), damit die Sammlung nicht vom Stand des letzten
    Playnite-Exports abhängt. Abgerufenes bleibt; kennt Playnite die App inzwischen oder steht sie nicht mehr im
    Konto, fällt der Eintrag weg. Ohne gelesenes Konto bleibt alles, wie es ist. Gibt (neu, entfallen) zurück."""
    games = col.setdefault("games", {})
    sp = data.get("steam_play") or {}
    if not sp:
        return 0, 0
    names = data.get("steam_apps") or {}
    known = {str(g.get("id")) for k, g in games.items() if g.get("src") != STEAMACCT
             and str(g.get("id") or "").isdigit() and (g.get("store") == "Steam" or g.get("src") == PCVR)}
    vr = {str(t.get("steam_appid")) for t in data["titles"].values() if t.get("steam_appid")}
    gone = [k for k, g in games.items() if g.get("src") == STEAMACCT and (str(g.get("id")) not in sp or str(g.get("id")) in known)]
    for k in gone:
        del games[k]
    new = 0
    for app, v in sp.items():
        k = "steam:" + app
        if app in known or app in vr or (k in games and games[k].get("src") != STEAMACCT):
            continue
        name = (v[2] if len(v) > 2 else "") or (names.get(app) or {}).get("name") or ""
        if not name:
            continue
        if k not in games:
            new += 1
            games[k] = {"name": name[:200], "store": "Steam", "id": app, "src": STEAMACCT, "mp": [], "players": 0,
                        "genres": [], "released": "", "added": "", "dev": "", "pub": ""}
        else:
            games[k]["name"] = name[:200]
    col["n"] = len(games)
    return new, len(gone)


# 0.10.10: gg.deals führt in der Sammlung auch Konsolenspiele, erkennbar am Zusatz „(PS4)“, „(PS4 & PS5)“, „(Xbox …)“
# oder „(Switch)“ hinter dem Namen; die gehören nicht in die Sammlung PC
_GG_CONSOLE = re.compile(r"\((?:PS ?[1-5]|PS Vita|PSP|Xbox|Switch|Nintendo)\b[^()]*\)\s*$")


def gg_console(name):
    return bool(_GG_CONSOLE.search(str(name or "")))


def sync_gg(col, data):
    """Spiele aus deiner gg.deals-Sammlung (data["gg_coll"], Lesezeichen „Seite lesen“, 0.9.9) unter „gg:<Slug>“, wenn
    weder Playnite noch das Steam-Konto noch die VR-Titel am PC sie unter demselben Namen führen. gg.deals führt
    Spiele aus Steam, GOG, Epic und weiteren Launchern zusammen; der Launcher kommt aus der Karte auf der Seite.
    Steht ein Spiel nicht mehr in der Sammlung oder kennt es inzwischen eine andere Quelle, fällt es weg.
    Ohne gelesene Sammlung bleibt alles, wie es ist. Gibt (neu, entfallen) zurück."""
    games = col.setdefault("games", {})
    gc = data.get("gg_coll") or {}
    if not isinstance(gc.get("items"), list):
        return 0, 0
    other = {titles.norm(g.get("name") or "") for g in games.values()
             if g.get("src") != GGCOLL and (g.get("system") or "PC") == "PC" and g.get("src") not in ("retro", ESHOP)}
    want = {}
    for it in gc["items"]:
        n = titles.norm(it.get("name") or "")
        if not n or n in other or gg_console(it.get("name")) or not re.fullmatch(r"[a-z0-9-]{1,150}", str(it.get("slug") or "")):
            continue
        stores = [x for x in it.get("stores") or [] if isinstance(x, str)]
        want["gg:" + it["slug"]] = {"name": str(it["name"])[:200], "store": stores[0] if stores else "", "stores": stores[:6],
                                    "id": it["slug"], "src": GGCOLL, "mp": [], "players": 0, "genres": [], "released": "",
                                    "added": "", "dev": "", "pub": ""}
    gone = [k for k, g in games.items() if g.get("src") == GGCOLL and k not in want]
    for k in gone:
        del games[k]
    new = 0
    for k, g in want.items():
        o = games.get(k)
        if o is None:
            new += 1
        elif o.get("src") != GGCOLL:
            continue
        else:
            g = dict(o, **{f: g[f] for f in ("name", "store", "stores", "id", "src")})   # Abgerufenes bleibt
        games[k] = g
    col["n"] = len(games)
    return new, len(gone)


def _vr_ctx(data):
    """Was _vr_tag braucht, einmal je Aufbau (0.11.1): Steam-IDs und Namen deiner VR-Titel, VR-Prüfung im Store."""
    return (data.get("steam_apps") or {},
            {str(t["steam_appid"]): k for k, t in data["titles"].items() if str(t.get("steam_appid") or "").isdigit()},
            {titles.base_norm(t["name"]): k for k, t in data["titles"].items()})


def _vr_tag(r, ctx):
    """VR am PC für eine Zeile (siehe _pc_vr). Gibt die Steam-ID zurück (auch ""), None für Zeilen, die nicht zählen."""
    if r["system"] != "PC" or r.get("retro") or r.get("eshop"):
        return None
    apps, t_ids, t_names = ctx
    sid = r["key"][6:] if r["key"].startswith("steam:") else r.get("steam_id") or ""
    if r.get("from_vr"):
        r.update(vr=True, vr_src="VR-Titel im Tool")
    elif r.get("vr"):
        r["vr_src"] = "Steam"
    elif sid and sid in t_ids:
        r.update(vr=True, vr_src="VR-Titel im Tool")
    elif sid and (apps.get(sid) or {}).get("vr"):
        r.update(vr=True, vr_src="VR-Prüfung im Steam-Store")
    elif titles.base_norm(r["name"]) in t_names:
        r.update(vr=True, vr_src="VR-Titel im Tool (Name)")
    elif vr_name(r["name"]):
        r.update(vr=True, vr_guess=True, vr_src="nur der Name")
    return sid


def _pc_vr(rows, data, wmatch=None):
    """VR am PC (0.8.7): Steam-Spiele der Sammlung, die das Tool als VR kennt (VR-Titel oder VR-Prüfung im Store),
    tragen „VR“; nennt nur der Name VR, ist das ein Hinweis (vr_guess). Dazu kommen deine VR-Titel am PC, die
    Playnite nicht kennt: am PC gekauft (Steam, Epic …) oder bei Meta mit Crossbuy (Entscheidung 28.10.2026)."""
    from . import library
    ctx = _vr_ctx(data)
    seen_ids, seen_names = set(), set()
    for r in rows:
        sid = _vr_tag(r, ctx)
        if sid is None:
            continue
        seen_ids.add(sid)
        seen_names.add(titles.base_norm(r["name"]))
    extra = []
    for k, t in data["titles"].items():
        o = t.get("owned") or {}
        cb = library.crossbuy(t)[0]
        if not (o.get("pc") or (o.get("meta") and cb)) or titles.is_bundle(t):
            continue
        sid = str(t.get("steam_appid") or "")
        if (sid and sid in seen_ids) or titles.base_norm(t["name"]) in seen_names:
            continue
        store = (o.get("pc") or {}).get("label") or ("Meta (Crossbuy)" if not o.get("pc") else "PC")
        rev = t.get("rev") or {}
        n = rev.get("n") if isinstance(rev.get("n"), int) else None
        r = {"key": "pcvr:" + k, "name": t["name"], "system": "PC", "store": store, "guess": False, "mp": [],
             "players": 0, "genres": [], "score": rev.get("pct") if n is not None and n >= 50 else None,
             "score_src": "Steam" if n is not None and n >= 50 else "", "reviews": n, "year": "", "added": t.get("added") or "",
             "dev": "", "pub": "", "rel": "", "desc": "", "gem": 0, "gem_guess": True, "srcs": ["VR-Titel im Tool"],
             "url": f"https://store.steampowered.com/app/{sid}/" if sid.isdigit() else "",
             "vr": True, "vr_src": "VR-Titel im Tool", "from_vr": k}
        # Lenkrad (0.8.8): auch die VR-Titel ohne Playnite-Eintrag, über Steam-ID und Namen
        w = wheel.row(wmatch, sid, None, t["name"]) if wmatch else None
        if w:
            r["wheel"] = w
        extra.append(r)
    return extra


def merge_retro(r, g):
    """Retro (0.8.8): Spielinfos aus der libretro-database, dann deine Ordner-Liste als erste Quelle.
    - libretro: Genre und Spielerzahl wie IGDB (bestätigt, was beide sagen; nennt sonst niemand ein Genre, gilt es),
      Erscheinen, Entwickler, Verlag, Beschreibung (englisch) nur, wo nichts anderes steht
    - Ordner-Liste: dein Titel ist der Name, dein Genre steht vorn und gilt als bestätigt; Reihe, Untergruppe und
      Ordner stehen in den Einzelheiten. Widerspricht libretro oder IGDB beim Genre, nennt es own_diff"""
    lr = g.get("lr") or {}
    if lr:
        r["srcs"] = r["srcs"] + ["libretro"]
        lg = genres(lr.get("genre") or [], [])
        r["gc"] = list(dict.fromkeys((r.get("gc") or []) + [x for x in r["genres"] if x in lg] + (lg if not r["genres"] else [])))
        r["genres"] = r["genres"] + [x for x in lg if x not in r["genres"]]
        r["lgen"] = lr.get("genre") or []
        if lr.get("users"):
            if r.get("pl_src") == "IGDB" and r["players"] == lr["users"]:
                r["pl_ok"] = True
            elif not r["players"] or r.get("pl_src") != "IGDB":
                r["players"], r["pl_src"] = lr["users"], "libretro"
        rel = lr.get("rel") or ""
        if rel:
            if r["year"]:
                r["year_ok"] = r["year"] == rel[:4]
            else:
                r.update(year=rel[:4], year_src="libretro", rel=rel)
            r["lyear"] = rel[:4]
        for f in ("dev", "pub"):
            if lr.get(f) and not r.get(f):
                r[f] = lr[f]
        if lr.get("desc") and not r.get("desc"):
            r["desc"], r["desc_lang"], r["desc_src"] = lr["desc"], "en", "libretro"
        r["lname"] = lr.get("n") or ""
    own = g.get("own") or {}
    if own:
        r["srcs"] = ["Ordner-Liste"] + r["srcs"]
        from . import retro
        t = retro.article_front(own.get("title") or "")
        if t and t != r["name"]:
            r["fname"], r["name"] = r["name"], t[:200]
        mg = retro.own_genre(g)
        if mg and retro.own_taken(g):
            # 0.9.6 „Quellen gelten“: libretro und IGDB einig, dein Genre fällt aus der Zeile (steht in den Einzelheiten)
            r["own_taken"] = mg
            r["genres"] = [x for x in r["genres"] if x != mg] or r["genres"]
            r["gc"] = [x for x in (r.get("gc") or []) if x != mg]
        elif mg:
            r["genres"] = [mg] + [x for x in r["genres"] if x != mg]
            r["gc"] = [mg] + [x for x in (r.get("gc") or []) if x != mg]
        r["own"] = {k: own[k] for k in ("series", "coll", "genre", "sub", "folder", "status", "mb") if own.get(k) not in (None, "")}
        ok = set(g.get("own_ok") or [])
        diff = [] if retro.own_conflicts(g) and all(retro._conflict_id(c) in ok for c in retro.own_conflicts(g)) else retro.own_conflicts(g, strict=False)
        if diff:
            r["own_diff"] = [{"own": c[1], "other": c[2], "src": c[3]} for c in diff]
    if g.get("size"):
        r["size"] = g["size"]


def merge_tdb(r, t):
    """GameTDB (0.10.13) für GameCube, Wii, DS und 3DS:
    - Beschreibung auf Deutsch vor IGDB und libretro (beide englisch); englisch von GameTDB nur, wo keine steht
    - Genre und Spielerzahl wie libretro: bestätigt, was zwei Quellen sagen, sonst Ersatz
    - Erscheinen, Entwickler, Verlag nur, wo nichts steht; ein anderes Jahr nennt tyear
    - neu: deutscher Titel (dtitle, wenn er anders heißt), USK oder PEGI, Sprachen der gefundenen Fassung"""
    r["srcs"] = r["srcs"] + ["GameTDB"]
    r["tdb_id"] = t.get("id") or ""
    if t.get("desc") and (t.get("desc_lang") == "de" or not r.get("desc")):
        r["desc"], r["desc_lang"], r["desc_src"] = t["desc"], t.get("desc_lang") or "en", "GameTDB"
    tg = genres(t.get("genre") or [], [])
    if tg:
        r["gc"] = list(dict.fromkeys((r.get("gc") or []) + [x for x in r["genres"] if x in tg] + (tg if not r["genres"] else [])))
        r["genres"] = r["genres"] + [x for x in tg if x not in r["genres"]]
    p = t.get("players") or 0
    if p:
        if r.get("players") == p and r.get("pl_src") in ("IGDB", "libretro"):
            r["pl_lr"] = bool(r.get("pl_ok")) and r["pl_src"] == "IGDB"     # libretro hatte IGDB schon bestätigt
            r["pl_ok"] = r["pl_tdb"] = True
        elif not r.get("players"):
            r["players"], r["pl_src"] = p, "GameTDB"
    if t.get("online"):
        r["tdb_online"] = t["online"]
    d = t.get("date") or ""
    if d:
        if not r.get("year"):
            r.update(year=d[:4], year_src="GameTDB")
        elif r["year"] != d[:4]:
            r["tyear"] = d[:4]
        if not r.get("rel") and d[:4] == r["year"]:
            r["rel"] = d
    for f in ("dev", "pub"):
        if t.get(f) and not r.get(f):
            r[f] = t[f]
    if t.get("de_t") and titles.norm(t["de_t"]) != titles.norm(r["name"]):
        r["dtitle"] = t["de_t"]
    if t.get("rating"):
        r["age"], r["age_src"] = t["rating"], "GameTDB"
    if t.get("langs"):
        r["tdb_langs"] = t["langs"]


def merge_wiki(r, w):
    """Wikidata und deutsche Wikipedia (0.10.16) für Retro-Spiele:
    - deutsche Beschreibung, wo keine deutsche steht (die von GameTDB gehört zur gefundenen Fassung und geht vor)
    - deutscher Titel, wo GameTDB keinen nennt; USK oder PEGI, wo keine Freigabe steht
    - Spielerzahl: bestätigt, was andere sagen (pl_wd), sonst Ersatz; ein anderes Jahr nennt wyear"""
    r["srcs"] = r["srcs"] + ["Wikidata"]
    r["wd"] = w.get("q") or ""
    if w.get("de"):
        r["wp"] = w["de"]
    if w.get("desc") and r.get("desc_lang") != "de":
        if r.get("desc") and r.get("desc_src"):
            r["desc_en_src"] = r["desc_src"]
        r["desc"], r["desc_lang"], r["desc_src"] = w["desc"], "de", "Wikipedia"
    if w.get("t") and not r.get("dtitle") and titles.norm(w["t"]) != titles.norm(r["name"]):
        r["dtitle"], r["dtitle_src"] = w["t"], "Wikidata"
    if w.get("age") and not r.get("age"):
        r["age"], r["age_src"] = w["age"], "Wikidata"
    p = w.get("players") or 0
    if p:
        if r.get("players") == p:
            r["pl_wd"] = True
        elif not r.get("players"):
            r["players"], r["pl_src"] = p, "Wikidata"
    y = w.get("year") or ""
    if y:
        if not r.get("year"):
            r.update(year=y, year_src="Wikidata")
        elif r["year"] != y:
            r["wyear"] = y


def merge_deku(r, d):
    """DekuDeals (0.10.14), zweite Quelle für PC und Konsolen:
    - Spielzeit laut HowLongToBeat vor IGDB (wie im eShopKompass); IGDB bleibt im Tooltip (ihours)
    - Metacritic, wo Steam keine nennt; OpenCritic neu (oc)
    - Spieler, Genre, Erscheinen: bestätigt, was andere sagen (pl_deku, gc), sonst Ersatz; ein anderes Jahr nennt dyear
    - USK, PEGI oder ESRB, wo GameTDB keine nennt; Deutsch, wo Steam nichts sagt (sde)"""
    r["srcs"] = r["srcs"] + ["DekuDeals"]
    r["deku_slug"] = d.get("slug") or ""
    h = d.get("hltb") or {}
    main = h.get("main") or h.get("solo")
    if main:
        if r.get("hours") and r.get("hours_src") == "IGDB":
            r["ihours"] = r["hours"]
        r.update(hours=main, hours_src="HowLongToBeat", hltb=h)
    if d.get("mc") is not None:
        if r.get("mc") is None:
            r["mc"], r["mc_src"] = d["mc"], "DekuDeals"
        elif r["mc"] == d["mc"]:
            r["mc_ok"] = True
    if d.get("oc") is not None:
        r["oc"] = d["oc"]
    pl = d.get("players") or {}
    p = max([v[1] for v in pl.values() if isinstance(v, list) and len(v) == 2] or [0])
    if p:
        if r.get("players") == p:
            r["pl_deku"] = True
        elif not r.get("players"):
            r["players"], r["pl_src"] = p, "DekuDeals"
    dg = genres(d.get("genre") or [], [])
    if dg:
        r["gc"] = list(dict.fromkeys((r.get("gc") or []) + [x for x in r["genres"] if x in dg] + (dg if not r["genres"] else [])))
        r["genres"] = r["genres"] + [x for x in dg if x not in r["genres"]]
    rel = d.get("released") or ""
    if rel:
        if not r.get("year"):
            r.update(year=rel[:4], year_src="DekuDeals")
        elif r["year"] != rel[:4]:
            r["dyear"] = rel[:4]
        if not r.get("rel") and rel[:4] == r["year"]:
            r["rel"] = rel
    for f in ("dev", "pub"):
        if d.get(f) and not r.get(f):
            r[f] = d[f]
    if d.get("age") and not r.get("age"):
        r["age"], r["age_src"] = d["age"], "DekuDeals"
    if d.get("langs") and r.get("sde") is None:
        r["sde"] = any(x.lower().startswith("german") for x in d["langs"])
        r["sde_src"] = "DekuDeals"


def f2vr_items(col):
    """Spiele der Sammlung für flat2vr.assign (0.10.28): Namen laut Playnite, Steam und IGDB, System, Jahr und ob
    VR schon eingebaut ist (Steam sagt VR, oder es ist dein VR-Titel am PC). Ohne eShopKompass-Spiele."""
    out = []
    for k, g in (col.get("games") or {}).items():
        if g.get("src") == ESHOP:
            continue
        st, ig = g.get("steam") or {}, g.get("igdb") or {}
        out.append({"key": k, "names": [g.get("name"), st.get("name"), ig.get("name")], "system": g.get("system") or "PC",
                    "year": (g.get("released") or "")[:4] or st.get("year") or ig.get("year") or "",
                    "vr": bool(st.get("vr")) or g.get("src") == PCVR})
    return out


def f2vr_match(col):
    """Ports und UEVR-Profile je Spiel der Sammlung aus flat2vr.json und uevr.json (0.10.28)."""
    ports = (datastore.load_json(flat2vr.PORTS_FILE, {}) or {}).get("ports") or []
    uevr = (datastore.load_json(flat2vr.UEVR_FILE, {}) or {}).get("games") or []
    if not ports and not uevr:
        return {}, 0
    return flat2vr.assign(f2vr_items(col), ports, uevr, lambda q: system_of([q]))


def view(col, data=None):
    """Zeilen für die Oberfläche, kurz gehalten (bis zu einige tausend Spiele). Mit data kommen die VR-Titel am PC
    dazu (0.8.7)."""
    wmatch = wheel.matcher(datastore.load_json(wheel.LIST_FILE, {}))
    f2vr, _ = f2vr_match(col)
    rows = [row(k, g, data, wmatch, f2vr) for k, g in (col.get("games") or {}).items()]
    return _finish(rows, col, data, wmatch)


def rows(col, data, keys):
    """Nur die Zeilen der genannten Spiele, wie view sie baut (0.11.1): nach einer Entscheidung ändert sich nur ihre
    Zeile. {Schlüssel: Zeile}; Spiele, die es nicht gibt, fehlen. Ob eine Zeile in der Ansicht steht (doppelte Einträge
    fallen weg), entscheidet view; eine Entscheidung ändert daran nichts."""
    games = col.get("games") or {}
    keys = [k for k in dict.fromkeys(keys) if isinstance(games.get(k), dict)]
    if not keys:
        return {}
    wmatch = wheel.matcher(datastore.load_json(wheel.LIST_FILE, {}))
    f2vr, _ = f2vr_match(col)
    ctx = _vr_ctx(data) if data is not None else None
    out = {}
    for k in keys:
        r = row(k, games[k], data, wmatch, f2vr)
        if ctx:
            _vr_tag(r, ctx)
        out[k] = r
    return out


def row(k, g, data, wmatch, f2vr):
    """Eine Zeile der Sammlung aus einem Spiel (ab 0.11.1 eigene Funktion, vorher Teil von view)."""
    r = {"key": k, "name": g["name"], "system": g.get("system") or "PC", "store": g.get("store") or "", "guess": bool(g.get("store_guess")), "mp": g.get("mp") or [],
         "players": g.get("players") or 0, "genres": g.get("genres") or [], "score": None,
         "score_src": "", "year": (g.get("released") or "")[:4],
         "added": g.get("added") or "", "dev": g.get("dev") or "", "pub": g.get("pub") or "",
         "rel": g.get("released") or "", "url": link(k, g)}
    if g.get("src") == ESHOP:
        # eShopKompass (0.7.3): Wertung Metacritic, sonst OpenCritic; Mein Stand von dort, nur lesend
        sc, src = (g["mc"], "Metacritic") if g.get("mc") is not None else (g.get("oc"), "OpenCritic") if g.get("oc") is not None else (None, "")
        r.update(eshop=True, score=sc, score_src=src, hours=g.get("hours"), desc=g.get("desc") or "",
                 desc_lang=g.get("desc_lang") or "de", usk=g.get("usk") or "", langs=g.get("langs") or [],
                 pl=g.get("pl") or {}, mine=g.get("ext_mine") or {}, slug=g.get("id") or "", kv=g.get("kv") or {})
        return _sw(r)
    if g.get("src") == "retro":
        r.update(retro=True, langs=g.get("langs") or [], lang_guess=bool(g.get("lang_guess")),
                 regions=g.get("regions") or [], files=g.get("files") or 0, flags=g.get("flags") or [],
                 gone=bool(g.get("gone")), de=g.get("de") or None)
        if g.get("de_ign") and (g.get("de") or {}).get("st") == "missing":
            r["de"] = dict(g["de"], ign=g["de_ign"])      # 0.10.12: „DE fehlt“ ignoriert
        if (g.get("de") or {}).get("langs"):
            # 3DS (0.8.4): Sprachen der Fassung laut No-Intro, gefunden über den Produktcode
            r.update(langs=g["de"]["langs"], lang_guess=False)
        elif (g.get("de") or {}).get("dat"):
            r.update(lang_guess=False, lang_dat=True)     # 0.8.12: Datei genau so in der Fassungsliste
    r["gem"], r["gem_guess"] = gem(g)
    rev = g.get("rev") or {}
    if g.get("src") == PCVR:
        # VR-Titel am PC (0.8.9): Wertung von Steam über das Spiel selbst, sonst die des VR-Titels
        if not rev and data is not None:
            rev = (data["titles"].get(g.get("from_vr")) or {}).get("rev") or {}
        r.update(from_vr=g.get("from_vr"), steam_id=str(g.get("id") or ""))
        if not r["url"] and str(g.get("id") or "").isdigit():
            r["url"] = f"https://store.steampowered.com/app/{g['id']}/"
    r["reviews"] = rev.get("n") if isinstance(rev.get("n"), int) else None
    r["rdesc"] = rev.get("desc") or ""
    # Aktiv (0.8.23): Steam-Spieler gerade eben; VR-Titel am PC aus der Messung des VR-Titels
    play = g.get("play") or {}
    if g.get("src") == PCVR and data is not None:
        play = (data["titles"].get(g.get("from_vr")) or {}).get("play") or play
    if isinstance(play.get("now"), int):
        r["active"] = {"now": play["now"], "at": play.get("at") or ""}
    if r["reviews"] is not None and r["reviews"] >= 50 and rev.get("pct") is not None:
        # Wertung nur von Steam, sobald genug Rezensionen da sind
        r["score"], r["score_src"] = rev["pct"], "Steam"
    if r["guess"] and r["reviews"]:
        r["guess"] = False              # Steam kennt die App und hat Rezensionen: Laden bestätigt
    check(r, g.get("steam") or {})
    r["srcs"] = ["Playnite"] + (["Steam"] if r["src"] == "steam" else []) if not r.get("retro") else ["Retro-Liste"]
    if g.get("src") == STEAMACCT:
        r["srcs"][0] = "Steam-Konto"
    if g.get("src") == GGCOLL:
        r["srcs"][0] = "gg.deals-Sammlung"
        r["stores"] = g.get("stores") or []
    if g.get("src") == PCVR:
        r["srcs"][0] = "VR-Titel im Tool"
        r.update(vr=True, vr_src="VR-Titel im Tool")
    ig = g.get("igdb") or {}
    if ig.get("id"):
        merge_igdb(r, ig)
    if r.get("retro"):
        merge_retro(r, g)
    if (g.get("tdb") or {}).get("id"):
        merge_tdb(r, g["tdb"])
    if (g.get("wiki") or {}).get("q"):
        merge_wiki(r, g["wiki"])
    if (g.get("deku") or {}).get("slug"):
        merge_deku(r, g["deku"])
    # VR per Mod (0.8.1): PCGamingWiki „hackable“, vorpX; Nexus Mods mit Spielseite und Mods
    pc, nx = g.get("pcgw") or {}, g.get("nexus") or {}
    merge_pcgw(r, pc)
    if pc.get("mod"):
        r["vrmod"] = pc["mod"]
    if pc.get("vorpx"):
        r["vorpx"] = True
    if nx.get("dom"):
        r["nexus"] = {"dom": nx["dom"], "n": nx.get("n") or 0, "top": nx.get("top") or [], "vr": nx.get("vr") or []}
    # Sim-Racing (0.8.3): in einer Liste der Rennspiele bestätigt, Steam-Schlagwörter nur ein Hinweis
    if r["system"] == "PC" and not r.get("retro"):
        w = wheel.row(wmatch, g.get("id") if g.get("store") == "Steam" else "", g.get("stag"), (g.get("igdb") or {}).get("name"), g["name"])
        # 0.10.26: Recherche zum Lenkrad (aufgaben.py); „nein“ nimmt den Hinweis aus den Schlagwörtern weg
        rw = g.get("r_wheel") or {}
        if rw.get("v") and w:
            r["wheel_r"] = rw
            if rw["v"] == "nein" and not w["src"]:
                w = None
            elif rw["v"] in ("ja", "teilweise"):
                w = dict(w, r=rw["v"])
        if w:
            r["wheel"] = w
    # 0.10.26: Recherche zu VR-Mods (auch „nein“, damit das Spiel nicht wieder in den Auftrag kommt)
    if g.get("r_vrmod"):
        r["vrmod_r"] = g["r_vrmod"]
    # 0.10.28: VR-Ports laut Flat2VR Index (gefüllte Marke) und UEVR-Profile laut UEVR Hub (Hinweis)
    fx = f2vr.get(k)
    if fx and fx.get("ports"):
        r["f2vr"] = flat2vr.row_ports(fx["ports"])
    if fx and fx.get("uevr"):
        r["uevr"] = fx["uevr"]
    # Spielzeit und zuletzt gespielt laut Steam-Konto (0.9.3)
    sid = str(g.get("id") or "") if g.get("store") == "Steam" or g.get("src") == PCVR else ""
    sp = ((data or {}).get("steam_play") or {}).get(sid) if sid else None
    if sp:
        r["pt"], r["lp"] = sp[0], sp[1]
    return _sw(r)


def _sw(r):
    # Switch und Switch 2 in einem Reiter „Switch 2“ (0.7.5, Entscheidung 27.10.2026: alle Switch-Spiele laufen
    # auf der Switch 2); sw1 merkt, dass es ein Switch-1-Spiel ist (Filter „System“)
    if r["system"] == "Switch":
        r["system"], r["sw1"] = "Switch 2", True
    return r


def _finish(rows, col, data, wmatch):
    """Was view über alle Zeilen hinweg tut: doppelte Einträge weglassen, VR-Titel am PC, Reihenfolge, Listen."""
    # Kommt die Switch-Sammlung aus dem eShopKompass, fallen Switch-Spiele aus Playnite mit demselben Namen weg
    esh = {titles.norm(r["name"]) for r in rows if r.get("eshop")}
    if esh:
        rows = [r for r in rows if r.get("eshop") or not (r["system"].startswith("Switch") and titles.norm(r["name"]) in esh)]
    # Playnite führt manche Spiele zweimal, einmal ohne Launcher und Kennung (0.9.7): der Eintrag ohne fällt weg,
    # wenn es dasselbe Spiel im selben System mit Launcher gibt
    named = {(r["system"], titles.norm(r["name"])) for r in rows if r["store"]}
    rows = [r for r in rows if r["store"] or not r["key"].startswith("name:") or (r["system"], titles.norm(r["name"])) not in named]
    # gg.deals-Sammlung (0.9.9): nur, was keine andere Quelle unter demselben Namen führt
    pcn = {titles.norm(r["name"]) for r in rows if r["system"] == "PC" and not r["key"].startswith("gg:")}
    rows = [r for r in rows if not r["key"].startswith("gg:") or titles.norm(r["name"]) not in pcn]
    if data is not None:
        rows += _pc_vr(rows, data, wmatch)
    rows.sort(key=lambda r: titles.norm(r["name"]))
    systems = {}
    for r in rows:
        systems[r["system"]] = systems.get(r["system"], 0) + 1
    return {"at": col.get("at") or "", "n": len(rows), "games": rows, "mp_label": MP_LABEL,
            "eshop_at": col.get("eshop_at") or "", "eshop_link": sources.eshop_link(),
            "genres": sorted({x for r in rows for x in r["genres"]}),
            "systems": [[n, systems[n]] for n in sorted(systems, key=system_order)]}


def summary(col):
    return {"at": col.get("at") or "", "n": col.get("n") or len(col.get("games") or {})}
