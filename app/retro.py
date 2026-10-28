"""Retro-Liste: eine Liste von Dateinamen (ROM-Ordner) wird zu einem Eintrag je Spiel und System
in der Sammlung (collection.json, Quelle „retro“).

Die Liste kommt aus der Ordnerwahl im Browser, aus `find` unter Linux, aus PowerShell oder
`dir /s /b` unter Windows oder als CSV „System; Titel“. Gespeichert werden nur Name, System,
Regionen, Sprachen, Zahl der Dateien und Merkmale, nie Pfade (Entscheidung 26.10.2026).

Das System kommt aus einer eindeutigen Endung, sonst aus dem innersten Ordner mit bekanntem
Namen. Region und Sprachen stehen im Dateinamen nach No-Intro und Redump; ohne Sprachangabe gilt
die Sprache der Region und ist geschätzt (≈). Ein Spiel, das in einer neuen Liste fehlt, wird
nicht gelöscht, sondern als „nicht mehr in der Liste“ markiert, bis du den Stand übernimmst.
"""
import re

from . import collection, titles

SRC = "retro"
CACHE = "retro_dat.json"     # Fassungen je System (aus No-Intro, Redump, Retool), im Datenordner
INDEX_V = 3                 # 2 (0.8.4): Produktcodes je Fassung, Titel für ähnliche Namen; 3 (0.8.6): DSiWare, Titel ohne Leerzeichen
MAX_LINES = 100000

# Endungen, die das System allein bestimmen
EXT_SYSTEM = {
    "nes": "NES", "fds": "NES", "sfc": "SNES", "smc": "SNES", "n64": "N64", "z64": "N64", "v64": "N64",
    "gb": "GB", "gbc": "GBC", "gba": "GBA", "nds": "DS", "dsi": "DS", "3ds": "3DS", "cia": "3DS",
    "vb": "VB", "min": "Pokémon Mini", "gg": "Game Gear", "sms": "Master System", "md": "Mega Drive",
    "gen": "Mega Drive", "pce": "PC Engine", "ngp": "Neo Geo Pocket", "ngc": "Neo Geo Pocket",
    "ws": "WonderSwan", "wsc": "WonderSwan", "lnx": "Lynx", "a26": "Atari 2600", "a78": "Atari 7800",
}
# Endungen, die es auf mehreren Systemen gibt: nur mit Ordner
EXT_FOLDER = {"iso", "chd", "cue", "rvz", "wbfs", "gcz", "wia", "ciso", "cso", "pbp", "pkg", "zip", "7z", "rar",
              "gdi", "cdi", "xci", "nsp", "wua", "wux", "rpx", "bin", "img", "mdf", "ccd", "elf", "dol", "wad"}
# Spielstände und Beiwerk
SKIP_SAVE = {"sav", "srm", "state", "st0", "sa1", "dsv", "mcr", "mcd", "eep", "fla", "rtc"}
SKIP_EXTRA = {"m3u", "txt", "md", "nfo", "csv", "tsv", "xlsx", "xls", "ods", "ps1", "bat", "sh", "cmd", "py",
              "jpg", "jpeg", "png", "gif", "bmp", "webp", "pdf", "dat", "xml", "json", "db", "ini", "cfg", "log",
              "exe", "dll", "url", "lnk", "ips", "bps", "ups", "xdelta", "sha1", "md5", "sfv", "htm", "html",
              "sub", "ecm", "lst"}
# Ordner, deren Inhalt nicht zählt: Archive (…_zip), Spielstände, Werkzeuge, BIOS, Sortierhilfen
_SKIP_DIR = re.compile(r"(?:_zip|^saves?|^_?sortierung|^_?tools|^_?bios|^bios|^_aussortiert|^\$recycle\.bin|"
                       r"^\.trash.*|^system volume information)$", re.I)

# Ordnernamen, kurz und genau verglichen (No-Intro-Langnamen erkennt collection.SYSTEMS)
FOLDER_SHORT = {
    "nes": "NES", "fc": "NES", "famicom": "NES", "snes": "SNES", "sfc": "SNES", "n64": "N64", "gb": "GB",
    "gbc": "GBC", "gba": "GBA", "nds": "DS", "ds": "DS", "dsi": "DS", "3ds": "3DS", "vb": "VB",
    "pm": "Pokémon Mini", "pokemini": "Pokémon Mini", "gc": "GameCube", "ngc": "GameCube", "gcn": "GameCube",
    "wii": "Wii", "wiiu": "Wii U", "psx": "PS1", "ps1": "PS1", "ps": "PS1", "ps2": "PS2", "ps3": "PS3",
    "psp": "PSP", "vita": "PS Vita", "psv": "PS Vita", "md": "Mega Drive", "genesis": "Mega Drive",
    "sms": "Master System", "gg": "Game Gear", "saturn": "Saturn", "dc": "Dreamcast", "pce": "PC Engine",
}
_EXTRA_SYSTEMS = [("Pokémon Mini", r"pok[eé]mon mini"), ("Mega Drive", r"mega ?drive|genesis"),
                  ("Master System", r"master system"), ("Game Gear", r"game ?gear"), ("Saturn", r"\bsaturn\b"),
                  ("Dreamcast", r"dreamcast"), ("PC Engine", r"pc engine|turbografx"),
                  ("Neo Geo Pocket", r"neo ?geo pocket"), ("WonderSwan", r"wonderswan"), ("Lynx", r"\blynx\b"),
                  ("Atari 2600", r"atari 2600"), ("Atari 7800", r"atari 7800")]
_EXTRA = [(n, re.compile(p, re.I)) for n, p in _EXTRA_SYSTEMS]

# Regionen nach No-Intro und Redump, mit der Sprache, die ohne Angabe gilt
REGION_LANG = {
    "World": "En", "USA": "En", "Europe": "En", "UK": "En", "Australia": "En", "Canada": "En", "Asia": "En",
    "Germany": "De", "Austria": "De", "Switzerland": "De", "France": "Fr", "Spain": "Es", "Italy": "It",
    "Netherlands": "Nl", "Sweden": "Sv", "Scandinavia": "En", "Japan": "Ja", "Korea": "Ko", "China": "Zh",
    "Taiwan": "Zh", "Hong Kong": "Zh", "Brazil": "Pt", "Portugal": "Pt", "Russia": "Ru", "Greece": "El",
    "Poland": "Pl", "Denmark": "Da", "Norway": "No", "Finland": "Fi", "Latin America": "Es",
}
# Kurze Regionen der 3DS-Dateien (E, U, J, W und Kombinationen wie JUE)
_SHORT_REGION = {"E": "Europe", "U": "USA", "J": "Japan", "W": "World", "K": "Korea", "C": "China", "T": "Taiwan",
                 "G": "Germany", "F": "France", "S": "Spain", "I": "Italy", "A": "Australia"}
# GameCube und Wii (0.8.16): der vierte Buchstabe der Spiel-ID („RMCP01“) ist die Region
_ID_REGION = {"E": "USA", "P": "Europe", "D": "Germany", "F": "France", "S": "Spain", "I": "Italy", "J": "Japan",
              "K": "Korea", "U": "Australia", "H": "Netherlands", "X": "Europe", "Y": "Europe", "Z": "Europe"}
_GAME_ID = re.compile(r"[GRSDP][A-Z0-9]{2}[A-Z][A-Z0-9]{2}")
_PS_SERIAL = re.compile(r"S[LC][EUPJKA][SMD][-_ ]?\d{3}\.?\d{2}", re.I)
_LANG = re.compile(r"^[A-Z][a-z](?:-[A-Z][a-z]+)?$")
_ARTICLE = re.compile(r"^(.+?), (The|A|An|Der|Die|Das|Le|La|Les|Il|El)(\s+-\s+.*|:.*)?$")
_TID = re.compile(r"^[0-9A-F]{16}\s+", re.I)
_HACK = re.compile(r"\b(?:rom-?hacks?|hacks?)\b", re.I)


def _system_of_folder(name):
    n = name.strip()
    s = FOLDER_SHORT.get(n.casefold().replace(" ", "").replace("-", ""))
    if s:
        return s
    # „Nintendo - Super Nintendo Entertainment System“, „Sony - PlayStation 2“, „SNES“ …
    for sys, rx in _EXTRA:
        if rx.search(n):
            return sys
    for sys, rx in collection._SYSTEMS:
        if rx.search(n):
            return sys
    return ""


_SIZE = re.compile(r"\t(\d{1,15})\s*$")


def split_path(line):
    """Ordner und Dateiname aus einer Zeile (Linux oder Windows, absolut oder relativ). Eine Größe in Bytes hinter
    einem Tabulator (0.8.8, aus der Ordnerwahl) gehört nicht zum Namen."""
    p = _SIZE.sub("", line).strip().strip('"').replace("\\", "/")
    p = re.sub(r"^[A-Za-z]:/", "", p)
    parts = [x for x in p.split("/") if x not in ("", ".")]
    return parts[:-1], (parts[-1] if parts else "")


def article_front(title):
    """No-Intro schreibt „Legend of Pixels, The - Teil 2“; angezeigt wird „The Legend of Pixels - Teil 2“."""
    m = _ARTICLE.match(title)
    return f"{m.group(2)} {m.group(1)}{m.group(3) or ''}" if m else title


def _ps_serial(t):
    """PlayStation-Seriennummer einheitlich: „SLES_023.76“ und „SLES 02376“ werden „SLES-02376“."""
    d = re.sub(r"\D", "", t)
    return t[:4].upper() + "-" + d


def parse_name(fname):
    """Titel, Regionen, Sprachen (und ob sie nur aus der Region geschätzt sind), Merkmale und
    Kennung aus einem Dateinamen nach No-Intro oder Redump. Auch 3DS-Dateien wie
    „0004000000ABC000 Name (CTR-P-ABCP) (v0) (E).standard.cia“."""
    base = re.sub(r"\.(?:legit|piratelegit|standard|decrypted|encrypted)$", "", re.sub(r"\.[A-Za-z0-9]{1,6}$", "", fname), flags=re.I)
    tid = ""
    m = _TID.match(base)
    if m:
        tid, base = m.group(0).strip().upper(), base[m.end():]
    tags = re.findall(r"\(([^()]*)\)", base) + re.findall(r"\[([^\[\]]*)\]", base)
    title = re.sub(r"\s*[(\[].*$", "", base).strip(" -_.")
    regions, langs, flags, serial = [], [], [], ""
    for t in tags:
        parts = [p.strip() for p in t.split(",") if p.strip()]
        if parts and all(_LANG.match(p) for p in parts):
            langs = [p[:2] for p in parts]
        elif parts and all(p in REGION_LANG for p in parts):
            regions = parts
        elif re.fullmatch(r"[EUJWKCTGFSIA]{1,4}", t) and tid:
            regions = [_SHORT_REGION[c] for c in t]
        elif re.fullmatch(r"(?:CTR|KTR|NTR|TWL|AGB|DMG|CGB)-[A-Z0-9]-[A-Z0-9]{3,4}", t):
            serial = t
        elif _GAME_ID.fullmatch(t) and t[3] in _ID_REGION:
            serial = "ID-" + t[:4]      # GameCube, Wii: „[RMCP01]“
            regions = regions or [_ID_REGION[t[3]]]
        elif _PS_SERIAL.fullmatch(t):
            serial = _ps_serial(t)
        elif re.search(r"\b(?:Unl|Aftermarket|Homebrew|Pirate)\b", t, re.I):
            flags.append("homebrew")
        elif re.search(r"\b(?:Hack|T[+-]Ger|T[+-]Eng)\b", t):
            flags.append("hack")
            if re.search(r"T[+-]Ger", t):
                langs = sorted(set(langs) | {"De"})
    guess = not langs
    if guess:
        langs = sorted({REGION_LANG[r] for r in regions})
    return {"title": article_front(title), "regions": regions, "langs": sorted(set(langs)), "lang_guess": guess and bool(langs),
            "flags": sorted(set(flags)), "tid": tid, "serial": serial}


def classify(line):
    """Eine Zeile der Liste: (System, Datei-Angaben) oder (None, Grund) zum Überspringen.
    Gründe: „save“, „extra“, „archive“ (Ordner …_zip und Ähnliches), „unknown“."""
    dirs, fname = split_path(line)
    if not fname or "." not in fname:
        return None, "extra"
    if any(_SKIP_DIR.search(d) for d in dirs):
        return None, "archive"
    ext = fname.rsplit(".", 1)[1].casefold()
    if ext in SKIP_SAVE:
        return None, "save"
    if ext in SKIP_EXTRA:
        return None, "extra"
    system = EXT_SYSTEM.get(ext, "")
    if not system:
        for d in reversed(dirs):
            system = _system_of_folder(d)
            if system:
                break
    if not system or (ext not in EXT_SYSTEM and ext not in EXT_FOLDER):
        return None, "unknown"
    info = parse_name(fname)
    # GameCube und Wii (0.8.16): Heißt die Datei nur nach der Spiel-ID („RMCP01.wbfs“ im Ordner „Titel [RMCP01]“),
    # kommt der Titel aus dem Ordner
    # (ohne Klammern nur mit einer Ziffer am Ende, sonst wäre etwa „SPIDER.iso“ eine ID)
    if _GAME_ID.fullmatch(info["title"]) and info["title"][3] in _ID_REGION and re.search(r"\d", info["title"][4:]) and dirs:
        info = dict(parse_name(dirs[-1] + ".x"), **({} if "[" in dirs[-1] else
                                                   {"serial": "ID-" + info["title"][:4], "regions": [_ID_REGION[info["title"][3]]]}))
        if not info["title"] or _system_of_folder(dirs[-1]):
            return None, "unknown"
    if not info["title"]:
        return None, "unknown"
    low = "/".join(dirs).casefold()
    if re.search(r"(?:^|/)_?extras?/homebrew(?:/|$)|(?:^|/)homebrew(?:/|$)", low):
        info["flags"] = sorted(set(info["flags"]) | {"homebrew"})
    if any(_HACK.fullmatch(d) or d.casefold() in ("rom-hacks", "romhacks") for d in dirs):
        info["flags"] = sorted(set(info["flags"]) | {"hack"})
    info["file"] = fname
    sz = _SIZE.search(line)
    if sz:
        info["size"] = int(sz.group(1))
    return system, info


def _csv_games(text):
    """CSV mit Spalten System und Titel (Name)."""
    from .imports import _col, _rows
    rows = _rows(text)
    if not rows:
        return None
    h = rows[0]
    cs, ct = _col(h, "system", "konsole", "plattform", "platform"), _col(h, "titel", "title", "name", "spiel")
    if cs is None or ct is None:
        return None
    out = []
    for r in rows[1:MAX_LINES]:
        sysname = r[cs].strip() if cs < len(r) else ""
        name = r[ct].strip() if ct < len(r) else ""
        system = _system_of_folder(sysname) if sysname else ""
        if not name:
            continue
        info = parse_name(name + ".x")
        out.append((system or None, dict(info, file=name) if system else "unknown"))
    return out


def looks_like(text):
    """Ist der Text eine Retro-Liste? Mehr als die Hälfte der ersten Zeilen sind Pfade oder
    Dateinamen mit einer Endung, die das Tool kennt."""
    lines = [x for x in str(text or "").lstrip("﻿").splitlines() if x.strip()][:60]
    if not lines:
        return False
    head = lines[0].casefold()
    if re.match(r"^\s*\"?system\"?\s*[;,]", head) and re.search(r"titel|title|name", head):
        return True
    known = EXT_SYSTEM.keys() | EXT_FOLDER | SKIP_SAVE
    hits = 0
    for x in lines:
        _, f = split_path(x)
        if "." in f and f.rsplit(".", 1)[1].casefold() in known and ("/" in x or "\\" in x or "(" in f):
            hits += 1
    return hits * 2 > len(lines)


def key(system, title):
    return f"{SRC}:{system.casefold()}:{titles.norm(title)}"


def parse(text):
    """Spiele aus einer Retro-Liste: ({Schlüssel: Spiel}, Zählung). Mehrere Dateien desselben
    Titels (Regionen, Fassungen, Discs) ergeben einen Eintrag."""
    text = str(text or "").lstrip("﻿")
    items = _csv_games(text) if re.match(r"^\s*\"?system\"?\s*[;,]", text.split("\n", 1)[0], re.I) else None
    if items is None:
        items = [classify(x) for x in text.splitlines()[:MAX_LINES] if x.strip()]
    stats = {"files": 0, "save": 0, "extra": 0, "archive": 0, "unknown": 0, "systems": {}}
    games = {}
    for system, info in items:
        if system is None:
            stats[info] += 1
            continue
        stats["files"] += 1
        k = key(system, info["title"])
        g = games.get(k)
        if g is None:
            if len(games) >= collection.MAX_GAMES:
                continue
            g = games[k] = {"name": info["title"][:200], "system": system, "src": SRC, "store": "", "id": "",
                            "mp": [], "players": 0, "genres": [], "score": None, "score_src": "",
                            "released": "", "added": "", "dev": "", "files": 0, "regions": [], "langs": [],
                            "lang_guess": True, "flags": [], "_ext": {}}
            stats["systems"][system] = stats["systems"].get(system, 0) + 1
        ext = info["file"].rsplit(".", 1)[-1].casefold()
        g["_ext"][ext] = g["_ext"].get(ext, 0) + 1
        # 0.8.12: Dateiname ohne Endung, um ihn genau in der Fassungsliste zu finden (Sprachen dann laut No-Intro)
        stem = info["file"].rsplit(".", 1)[0][:200]
        if ext != "bin" and stem not in g.setdefault("dumps", []) and len(g["dumps"]) < 8:
            g["dumps"].append(stem)
        if info.get("size"):
            g["size"] = g.get("size", 0) + info["size"]
        g["regions"] = sorted(set(g["regions"]) | set(info["regions"]))
        g["langs"] = sorted(set(g["langs"]) | set(info["langs"]))
        if info["langs"] and not info["lang_guess"]:
            g["lang_guess"] = False
        g["flags"] = sorted(set(g["flags"]) | set(info["flags"]))
        for f in ("tid", "serial"):
            if info.get(f) and not g.get(f):
                g[f] = info[f]
    for g in games.values():
        ext = g.pop("_ext")
        # Bei .cue mit .bin zählt nur die .cue (die Spuren gehören zu ihr)
        g["files"] = sum(n for e, n in ext.items() if not (e == "bin" and "cue" in ext))
        if not g["langs"]:
            g["lang_guess"] = False
    return games, stats


def unknown_lines(text, limit=30):
    """Dateinamen, die das Tool keinem System zuordnen kann (für die Vorschau)."""
    out = []
    for x in str(text or "").lstrip("﻿").splitlines()[:MAX_LINES]:
        if x.strip() and classify(x) == (None, "unknown"):
            out.append(split_path(x)[1][:120])
            if len(out) >= limit:
                break
    return out


def apply(col, games, dry=True, own_systems=()):
    """Neue Retro-Liste mit der Sammlung abgleichen. Spiele anderer Quellen bleiben unberührt.
    Fehlt ein Retro-Spiel eines Systems, das in der neuen Liste vorkommt, bekommt es „gone“
    (Tag), statt gelöscht zu werden; taucht es wieder auf, fällt die Marke weg.
    Gibt (neu, Namen der fehlenden) zurück."""
    old = col.get("games") or {}
    # Bis 0.6.0 hieß die erste PlayStation „PS“ (Schlüssel retro:ps:…)
    for k in [k for k, g in old.items() if g.get("src") == SRC and g.get("system") == "PS"]:
        g = old.pop(k)
        old.setdefault("retro:ps1:" + k.split(":", 2)[2], dict(g, system="PS1"))
    systems = {g["system"] for g in games.values()}
    new = [k for k in games if k not in old]
    gone = [k for k, g in old.items() if g.get("src") == SRC and g.get("system") in systems and k not in games]
    if dry:
        return len(new), sorted(old[k]["name"] for k in gone)
    day = titles.now_iso()
    for k, g in games.items():
        o = old.get(k)
        if o:
            for f in ("rev", "steam", "mark", "info", "igdb", "pcgw", "nexus", "stag", "alias", "near_no", "lr", "own_ok"):
                if f in o:
                    g[f] = o[f]
            # Ordner-Liste (0.8.8): ohne neue Liste für das System bleibt die alte, ebenso die Größe ohne Ordnerwahl
            if "own" in o and "own" not in g and g["system"] not in own_systems:
                g["own"] = o["own"]
            if "size" in o and "size" not in g:
                g["size"] = o["size"]
        old[k] = g
    for k in gone:
        old[k].setdefault("gone", day)
    col["games"] = old
    col["at"] = day
    col["n"] = len(old)
    return len(new), sorted(old[k]["name"] for k in gone)


def gone(col):
    return sorted((g["name"], g["system"]) for g in (col.get("games") or {}).values() if g.get("gone"))


def settle(col, action):
    """„Stand übernehmen“ (drop): fehlende Retro-Spiele entfernen; „keep“: Marken löschen,
    die Spiele bleiben. Gibt die Zahl der betroffenen Spiele zurück."""
    games = col.get("games") or {}
    ks = [k for k, g in games.items() if g.get("gone")]
    for k in ks:
        if action == "drop":
            del games[k]
        else:
            games[k].pop("gone", None)
    col["n"] = len(games)
    return len(ks)


# ---------------------------------------------------------------- Sprache: welche Fassungen gab es?
# Listen aller Fassungen je System: No-Intro (Module, Handhelds) und Redump (Discs), wie die
# libretro-database sie spiegelt, dazu die Retool-Listen, die Fassungen eines Spiels auch bei
# verschiedenen Titeln zusammenfassen (etwa „Mondfahrer“ in Deutschland und „Moon Rover“ in den USA).
LIBRETRO = "https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/"
RETOOL = "https://raw.githubusercontent.com/unexpectedpanda/retool-clonelists-metadata/main/clonelists/"
DATS = {
    "GB": ("no-intro", "Nintendo - Game Boy"), "GBC": ("no-intro", "Nintendo - Game Boy Color"),
    "GBA": ("no-intro", "Nintendo - Game Boy Advance"), "NES": ("no-intro", "Nintendo - Nintendo Entertainment System"),
    "SNES": ("no-intro", "Nintendo - Super Nintendo Entertainment System"), "N64": ("no-intro", "Nintendo - Nintendo 64"),
    "DS": ("no-intro", "Nintendo - Nintendo DS"), "VB": ("no-intro", "Nintendo - Virtual Boy"),
    "Pokémon Mini": ("no-intro", "Nintendo - Pokemon Mini"), "Mega Drive": ("no-intro", "Sega - Mega Drive - Genesis"),
    "Master System": ("no-intro", "Sega - Master System - Mark III"), "Game Gear": ("no-intro", "Sega - Game Gear"),
    "GameCube": ("redump", "Nintendo - GameCube"), "Wii": ("redump", "Nintendo - Wii"),
    "PS1": ("redump", "Sony - PlayStation"), "PS2": ("redump", "Sony - PlayStation 2"), "PSP": ("redump", "Sony - PlayStation Portable"),
    "3DS": ("no-intro", "Nintendo - Nintendo 3DS"),
}
# Weitere Listen desselben Systems (0.8.4): beim 3DS die Download-Titel aus dem eShop, beim DS ab 0.8.6 die
# Liste „Nintendo DSi“ (in der libretro-database die DSiWare-Titel aus dem DSi-Shop; No-Intro nennt sie „DSi (Digital)“)
EXTRA_DATS = {"3DS": ["Nintendo - Nintendo 3DS (Digital)"], "DS": ["Nintendo - Nintendo DSi"]}
_SKIP_REL = re.compile(r"\((?:Beta|Proto|Demo|Sample|Kiosk|Pirate|Debug)[^)]*\)", re.I)


def urls(system):
    """Adressen der Fassungsliste und der Retool-Liste eines Systems, None ohne Liste."""
    kind, name = DATS.get(system, (None, None))
    if not kind:
        return None
    from urllib.parse import quote
    label = "No-Intro" if kind == "no-intro" else "Redump"
    return LIBRETRO + kind + "/" + quote(name) + ".dat", RETOOL + quote(f"{name} ({label})") + ".json"


def extra_urls(system):
    from urllib.parse import quote
    kind = DATS.get(system, (None,))[0]
    return [LIBRETRO + kind + "/" + quote(n) + ".dat" for n in EXTRA_DATS.get(system, [])]


def _serial_code(serial):
    """Produktcode ohne Region: „AMRD“ und „AMRE“ sind dasselbe Spiel (letzter Buchstabe = Region).
    Redump-Codes wie „SLES-01234“ sind je Region verschieden und zählen nicht."""
    s = _serial_full(serial) or str(serial or "").strip().upper()      # DS und GBA: nur „AMRE“
    return s[:3] if re.fullmatch(r"[A-Z0-9]{4}", s) else ""


def _serial_full(serial):
    """Produktcode mit Region („AMKP“): genau eine Fassung, deren Sprachen die Fassungsliste nennt. 3DS und DSi
    „CTR-P-AMKP“ (0.8.4); ab 0.8.16 GameCube „DL-DOL-GW7P-EUR“, Wii „RVL-RJ2P-EUR-B0“ und die Spiel-ID aus dem
    Dateinamen („ID-RJ2P“), PlayStation „SLES-02376“ (dort ganz, die Nummer gilt nur für eine Region)."""
    s = str(serial or "").strip().upper()
    m = re.fullmatch(r"(?:CTR|KTR|NTR|TWL)-[A-Z]-([A-Z0-9]{4})|(?:DL-DOL|RVL)-([A-Z0-9]{4})-[A-Z]{3}(?:-[A-Z0-9]+)?|ID-([A-Z0-9]{4})", s)
    if m:
        return next(x for x in m.groups() if x)
    return s if re.fullmatch(r"S[LC][EUPJKA][SMD]-\d{5}", s) else ""


def build_index(dat_text, retool_text=""):
    """Fassungen eines Systems aus einer libretro-DAT und der Retool-Liste. Fassungen gehören zu
    einer Gruppe, wenn sie denselben Titel, denselben Produktcode oder dieselbe Retool-Gruppe
    haben. Ergebnis: {"rel": [[Name, Sprachen, geschätzt]], "grp": {Titel: Gruppe},
    "mem": {Gruppe: [Fassungen]}, "via": {Gruppe: „code“/„retool“/„name“}, "code": {Produktcode: Gruppe},
    "ser": {Produktcode mit Region: Fassung}, "tn": {Titel: Titel wie geschrieben},
    "sq": {Titel ohne Leerzeichen: Gruppe} (0.8.6: „Moonrover“ ist „Moon Rover“)}."""
    rels, parent = [], {}

    def find(x):
        while parent.setdefault(x, x) != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b, why):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
            joined[ra] = joined.get(ra, set()) | joined.pop(rb, set()) | {why}
    joined = {}
    retool, tn, ser = {}, {}, {}
    if retool_text:
        import json
        try:
            obj = json.loads(retool_text)
        except ValueError:
            obj = {}
        for g in (obj.get("variants") or []) if isinstance(obj, dict) else []:
            for t in g.get("titles") or []:
                term = str(t.get("searchTerm") or "")
                if term and "(" not in term and not t.get("filters"):
                    retool[titles.norm(article_front(term))] = "g:" + str(g.get("group") or term)
    # Je Spiel der Name aus „game ( name …“ (0.8.6): In der DSi-Liste heißen viele Dateien nur „00000000“, und
    # Discs mit mehreren Spuren zählen so als eine Fassung
    for m in re.finditer(r'(?ms)^game \(\s*name "([^"]+)"(.*?)^\)', str(dat_text or "")):
        name = m.group(1)
        if _SKIP_REL.search(name):
            continue
        info = parse_name(name)
        if not info["title"]:
            continue
        sm = re.search(r'serial "([^"]*)"', m.group(2))
        i = len(rels)
        rels.append([name, ",".join(info["langs"]), 1 if info["lang_guess"] else 0])
        t = "t:" + titles.norm(info["title"])
        tn.setdefault(t[2:], info["title"][:120])
        full = _serial_full(sm.group(1) if sm else "")
        if full:
            ser.setdefault(full, i)
        union(t, "r:" + str(i), "name")
        code = _serial_code(sm.group(1) if sm else "")
        if code:
            union(t, "c:" + code, "code")
        rg = retool.get(t[2:])
        if rg:
            union(t, rg, "retool")
    grp, mem, codes = {}, {}, {}
    for x in list(parent):
        r = find(x)
        if x.startswith("t:"):
            grp[x[2:]] = r
        elif x.startswith("c:"):
            codes[x[2:]] = r
        elif x.startswith("r:"):
            mem.setdefault(r, []).append(int(x[2:]))
    via = {r: ("code" if "code" in w else "retool" if "retool" in w else "name") for r, w in joined.items() if r in mem}
    sq = {}
    for t, r in grp.items():
        sq.setdefault(_squash(t), r)
    return {"rel": rels, "grp": grp, "mem": mem, "via": via, "code": codes, "ser": ser, "tn": tn, "sq": sq}


def _squash(n):
    return n.replace(" ", "")


def _de_rank(rel):
    """Beste deutsche Fassung zuerst: Deutsch ausdrücklich genannt, dann Germany, dann Europe."""
    name, langs, guess = rel
    return (guess, "(Germany" not in name, "Europe" not in name, len(langs), name)


_NAMES = {}     # Namen aller Fassungen einer Liste, nur im Speicher: {id(Index): (Index, Namen)}


def _names(idx):
    hit = _NAMES.get(id(idx))
    if hit and hit[0] is idx:
        return hit[1]
    names = {r[0] for r in idx.get("rel") or []}
    if len(_NAMES) > 40:
        _NAMES.clear()
    _NAMES[id(idx)] = (idx, names)
    return names


def match(g, idx):
    """Gab es das Spiel mit Deutsch? {"st": have (deine Datei hat Deutsch), missing (es gab eine
    Fassung mit Deutsch, deine hat keins; alt: die gesuchte Fassung), none (keine deutsche Fassung
    bekannt), unknown (nicht in der Liste; near: ein ähnlicher Titel zum Bestätigen)}, dazu via (code, retool,
    name, alias) und guess, wenn das Deutsch der gesuchten Fassung nur aus der Region geschätzt ist; langs und rel,
    wenn der Produktcode die Fassung genau nennt."""
    # 3DS (0.8.4): Der Produktcode im Dateinamen („CTR-P-AMKP“) nennt genau die Fassung; deren Sprachen laut
    # No-Intro gelten statt der aus der Region geschätzten
    exact = {}
    si = (idx.get("ser") or {}).get(_serial_full(g.get("serial")))
    if si is not None and si < len(idx.get("rel") or []):
        langs = [x for x in idx["rel"][si][1].split(",") if x]
        # 0.8.16: auch ohne Sprachangabe in der Liste, denn No-Intro und Redump nennen sie nur, wenn sie von der Region abweicht
        if langs:
            exact = {"langs": langs, "rel": idx["rel"][si][0][:200]}
    # 0.8.12: Steht eine deiner Dateien genau so in der Fassungsliste, gelten ihre Sprachen laut No-Intro (dort fehlt die
    # Angabe nur, wenn die Fassung allein die Sprache ihrer Region hat); sonst bleiben sie aus der Region geschätzt
    if not exact and g.get("lang_guess") and g.get("dumps") and set(g["dumps"]) & _names(idx):
        exact = {"dat": True}
    mine = g.get("langs") or []
    if ("De" in mine and (not g.get("lang_guess") or exact.get("dat"))) or "De" in (exact.get("langs") or mine):
        return dict({"st": "have"}, **exact)
    code = _serial_code(g.get("serial"))
    r = (idx.get("code") or {}).get(code) if code else None
    mine_t = g.get("alias") or titles.norm(g.get("name") or "")
    r = r or (idx.get("grp") or {}).get(mine_t) or (idx.get("sq") or {}).get(_squash(mine_t))
    members = (idx.get("mem") or {}).get(r) if r else None
    if not members:
        out = {"st": "unknown"}
        near = None if g.get("alias") or g.get("flags") else similar(g.get("name") or "", idx)
        if near and titles.norm(near) != (g.get("near_no") or ""):
            out["near"] = near
        return dict(out, **exact)
    rels = [idx["rel"][i] for i in members if i < len(idx["rel"])]
    de = sorted((x for x in rels if "De" in x[1].split(",")), key=_de_rank)
    via = "code" if code and (idx.get("code") or {}).get(code) == r else "alias" if g.get("alias") else (idx.get("via") or {}).get(r, "name")
    if not de:
        return dict({"st": "none"}, **exact)
    return dict({"st": "missing", "alt": de[0][0][:200], "guess": bool(de[0][2]), "via": via}, **exact)


_WORD = re.compile(r"[a-z0-9]+")


_ROMAN = {"ii": "2", "iii": "3", "iv": "4", "v": "5", "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}


def _words(n):
    return {_ROMAN.get(w, w) for w in _WORD.findall(n)} - {"the", "a", "an", "of", "der", "die", "das", "and", "und", "3d"}


def _numbers(words):
    return {w for w in words if w.isdigit()}


_INV = {}       # Wörter je Titel einer Fassungsliste, nur im Speicher: {id(Index): (Index, Wörter)}


def _inverted(idx):
    hit = _INV.get(id(idx))
    if hit and hit[0] is idx:
        return hit[1]
    inv = {}
    for k in idx.get("tn") or {}:
        for w in _words(k):
            inv.setdefault(w, []).append(k)
    if len(_INV) > 40:
        _INV.clear()
    _INV[id(idx)] = (idx, inv)
    return inv


def similar(name, idx):
    """Ähnlichster Titel der Fassungsliste, wenn es keinen gleichen gibt: gleiche Wörter zu mindestens 60 %
    (Jaccard) oder ein Titel steckt mit mindestens zwei Wörtern ganz im anderen. Zahlen müssen gleich sein
    (0.8.6: „Teil 2“ ist ein anderes Spiel als „Teil“; römische Zahlen zählen als Zahl). Nur ein Vorschlag zum
    Bestätigen in „Zu erledigen“, nie von allein."""
    tn = idx.get("tn") or {}
    if not tn:
        return None
    inv = _inverted(idx)
    mine = _words(titles.norm(name))
    if not mine:
        return None
    cands = {k for w in mine for k in inv.get(w, ())[:400]}
    best, score = None, 0.0
    nums = _numbers(mine)
    for k in cands:
        other = _words(k)
        if _numbers(other) != nums:
            continue
        j = len(mine & other) / len(mine | other)
        inside = min(len(mine), len(other)) >= 2 and (mine <= other or other <= mine)
        sc = max(j, 0.7 if inside else 0.0)
        if sc > score or (sc == score and best and k < best):
            best, score = k, sc
    return tn[best] if best and score >= 0.6 else None


def mark_languages(col, indexes):
    """Ergebnis von match je Retro-Spiel unter „de“ speichern. indexes: {System: Index}.
    Gibt die Zahl je Ergebnis zurück."""
    count = {}
    for g in (col.get("games") or {}).values():
        if g.get("src") != SRC:
            continue
        idx = indexes.get(g.get("system"))
        if idx is None and "De" not in (g.get("langs") or []):
            g.pop("de", None)
            continue
        g["de"] = match(g, idx or {})
        count[g["de"]["st"]] = count.get(g["de"]["st"], 0) + 1
    return count


def near_list(col):
    """Retro-Spiele ohne Treffer in der Fassungsliste, aber mit ähnlichem Titel dort (für „Zu erledigen“)."""
    out = [{"key": k, "name": g["name"], "system": g.get("system") or "", "near": g["de"]["near"]}
           for k, g in (col.get("games") or {}).items() if g.get("src") == SRC and (g.get("de") or {}).get("near")]
    return sorted(out, key=lambda x: (x["system"], titles.norm(x["name"])))


def settle_near(col, key, ok, idx):
    """Vorschlag aus „Zu erledigen“: ok heißt dieselbe Fassung (der Titel der Liste gilt fortan für dieses
    Spiel), sonst kommt dieser Vorschlag nicht wieder. Danach gleich neu zuordnen."""
    g = (col.get("games") or {}).get(key)
    near = ((g or {}).get("de") or {}).get("near")
    if not near:
        raise ValueError("kein Vorschlag für dieses Spiel")
    g["alias" if ok else "near_no"] = titles.norm(near)
    if idx:
        g["de"] = match(g, idx)
    else:
        g["de"] = {"st": "unknown"}
    return g


# ---------------------------------------------------------------- Spielinfos aus der libretro-database (0.8.8)
# Je System und Feld eine Liste (metadat/genre, maxusers, releaseyear, releasemonth, developer). Bei PS1 und PS2
# steht alles in der Entwickler-Liste, mit englischer Beschreibung. Die Listen sind groß; das Tool behält nur, was
# zu den eigenen Spielen passt („lr“ am Spiel), und fragt je System höchstens alle META_DAYS Tage neu.
META_FILE = "retro_meta.json"
META_V = 1
META_FIELDS = ("genre", "maxusers", "releaseyear", "releasemonth", "developer")
_META_KEYS = {"genre": "genre", "users": "users", "releaseyear": "year", "releasemonth": "month",
              "releaseday": "day", "developer": "dev", "publisher": "pub", "description": "desc"}
_META_LINE = re.compile(r'^\s*(\w+)\s+(?:"(.*)"|(\S+))\s*$', re.M)


def meta_urls(system):
    """[(Feld, Adresse)] der Spielinfos eines Systems, mit den weiteren Listen (DSiWare, 3DS-Downloads)."""
    from urllib.parse import quote
    kind, name = DATS.get(system, (None, None))
    if not kind:
        return []
    return [(f, LIBRETRO + f + "/" + quote(n) + ".dat") for n in [name] + EXTRA_DATS.get(system, []) for f in META_FIELDS]


def parse_meta(text, into=None):
    """Einträge einer metadat-Liste in into sammeln: {Name der Fassung: {Feld: Wert}}. Dieselbe Fassung aus
    mehreren Listen wird ein Eintrag (die Entwickler-Liste schreibt „Pixel Kart: Turbo“, die anderen „Pixel Kart - Turbo“)."""
    into = {} if into is None else into
    for m in re.finditer(r'(?ms)^game \(\s*(.*?)^\)', str(text or "")):
        body = m.group(1)
        nm = re.search(r'^\s*(?:comment|name) "([^"]+)"', body, re.M)
        if not nm or _SKIP_REL.search(nm.group(1)):
            continue
        e = into.setdefault(titles.norm(nm.group(1)), {"n": nm.group(1)[:200]})
        for k, quoted, bare in _META_LINE.findall(body):
            f, v = _META_KEYS.get(k), (quoted or bare).strip()
            if f and v and f not in e:
                e[f] = v[:1200] if f == "desc" else v[:120]
    return into


def meta_index(entries):
    """Fassungen je Titel: {Titel: [Einträge]}, dazu Titel ohne Leerzeichen."""
    by, sq = {}, {}
    for e in entries.values():
        info = parse_name(e["n"] + ".x")
        t = titles.norm(info["title"])
        if t:
            by.setdefault(t, []).append(dict(e, r=info["regions"]))
            sq.setdefault(_squash(t), t)
    return {"t": by, "sq": sq}


def _meta_rank(e, regions):
    return (not set(e["r"]) & set(regions), "Europe" not in e["r"], -len(e), e["n"])


def meta_for(g, idx):
    """Spielinfos zu einem Retro-Spiel: Titel (dein Titel aus der Ordner-Liste, ein bestätigter ähnlicher Name, der
    Titel aus dem Dateinamen), gleiche Region zuerst. {} heißt: nicht gefunden."""
    by = idx.get("t") or {}
    own = titles.norm((g.get("own") or {}).get("title") or "")
    hits = []
    for t in (g.get("alias"), titles.norm(g.get("name") or ""), own):
        if t and not hits:
            hits = by.get(t) or by.get((idx.get("sq") or {}).get(_squash(t)) or "") or []
    if not hits:
        return {}
    hits = sorted(hits, key=lambda e: _meta_rank(e, g.get("regions") or []))
    out = {"n": hits[0]["n"]}
    for f in ("genre", "users", "year", "month", "day", "dev", "pub", "desc"):
        v = next((e[f] for e in hits if e.get(f)), "")
        if v:
            out[f] = v
    try:
        out["users"] = max(0, min(int(out.get("users") or 0), 99))
    except ValueError:
        out["users"] = 0
    if not out["users"]:
        out.pop("users")
    y = out.pop("year", "")
    if re.fullmatch(r"(19|20)\d\d", y):
        mo, d = out.pop("month", ""), out.pop("day", "")
        out["rel"] = y + (f"-{int(mo):02d}" if mo.isdigit() and 1 <= int(mo) <= 12 else "")
        if len(out["rel"]) > 4 and d.isdigit() and 1 <= int(d) <= 31:
            out["rel"] += f"-{int(d):02d}"
    out.pop("month", None), out.pop("day", None)
    if out.get("genre"):
        out["genre"] = [x.strip() for x in out["genre"].split(",") if x.strip()][:4]
    return out


def mark_meta(col, indexes):
    """Spielinfos je Retro-Spiel unter „lr“ speichern. indexes: {System: meta_index}. Gibt (gefunden, gesamt) zurück."""
    got = n = 0
    for g in (col.get("games") or {}).values():
        if g.get("src") != SRC or g.get("system") not in indexes:
            continue
        g["lr"] = meta_for(g, indexes[g["system"]])
        n += 1
        got += bool(g["lr"])
    return got, n


# ---------------------------------------------------------------- Deine Ordner-Listen (0.8.8)
# „<system>_ordner.csv“ unter „_Sortierung“: Datei;Titel;Reihe;Sammelreihe;Genre;Untergruppe;Ordner, beim 3DS dazu
# Status;TitleID;Liegt in;MB. Sie sind die erste Quelle (Entscheidung 28.10.2026): Titel und Genre daraus gelten vor
# Dateiname, libretro und IGDB. Wo andere Quellen widersprechen, steht es unter „Zu erledigen“.
OWN_COLS = {"title": ("titel", "title"), "series": ("reihe",), "coll": ("sammelreihe",), "genre": ("genre",),
            "sub": ("untergruppe",), "folder": ("ordner",), "status": ("status",), "mb": ("mb",)}
# Deine Genres auf die Genre-Gruppen des Tools
OWN_GENRE = {"jump & run": "Plattformer", "action & arcade": "Action", "sport": "Sport", "rennspiele": "Rennen",
             "rollenspiele": "Rollenspiel", "shooter": "Shooter", "adventure": "Abenteuer", "simulation": "Simulation",
             "puzzle": "Puzzle", "brett- & kartenspiele": "Karten und Brett", "kampfspiele": "Kampfspiel",
             "party & minispiele": "Party", "musik & rhythmus": "Musik", "flipper": "Arcade", "strategie": "Strategie",
             "lernspiele": "Lernspiel"}


def is_folder_list(path):
    return bool(re.search(r"(?:^|[/\\])[^/\\]*_ordner\.csv$", str(path or ""), re.I))


def parse_folder_list(path, text):
    """Eine Ordner-Liste: [(Schlüssel des Spiels, System, Angaben)]. Das System kommt aus der Endung der Datei, sonst
    aus dem Ordner, in dem die Liste liegt (ohne „…_zip“ und „_Sortierung“)."""
    from .imports import _col, _rows
    rows = _rows(str(text or "").lstrip("﻿"))
    if not rows:
        return []
    h = rows[0]
    cf = _col(h, "datei", "file", "dateiname")
    if cf is None:
        return []
    cols = {f: _col(h, *names) for f, names in OWN_COLS.items()}
    dirs = [d for d in split_path(path)[0] if not _SKIP_DIR.search(d)]
    out = []
    for r in rows[1:MAX_LINES]:
        fname = r[cf].strip() if cf < len(r) else ""
        if not fname:
            continue
        system, info = classify("/".join(dirs + [fname]))
        if system is None:
            continue
        own = {}
        for f, c in cols.items():
            v = r[c].strip() if c is not None and c < len(r) else ""
            if v:
                own[f] = v[:200]
        try:
            own["mb"] = round(float(own["mb"].replace(",", ".")), 1) if own.get("mb") else None
        except ValueError:
            own["mb"] = None
        if own.get("mb") is None:
            own.pop("mb", None)
        out.append((key(system, info["title"]), system, dict(own, file=fname[:200])))
    return out


def apply_folder_lists(games, lists):
    """Ordner-Listen in die gelesenen Spiele (games aus parse). Ein Spiel mit mehreren Zeilen nimmt die erste. Gibt
    {"systems", "rows", "matched", "extra": Zeilen ohne Datei, "missing": Spiele ohne Zeile} zurück."""
    rows = []
    for path, text in lists:
        rows += parse_folder_list(path, text)
    systems = sorted({s for _, s, _ in rows})
    matched, extra = set(), []
    for k, s, own in rows:
        g = games.get(k)
        if g is None:
            extra.append(own.get("title") or own["file"])
            continue
        if k not in matched:
            g["own"] = own
            matched.add(k)
    missing = sorted(g["name"] for k, g in games.items() if g["system"] in systems and k not in matched)
    return {"systems": systems, "rows": len(rows), "matched": len(matched), "extra": sorted(extra), "missing": missing}


# Genre-Gruppen, die einander nahe sind: Ein Widerspruch ist es erst, wenn keine Familie übereinstimmt
# („Jump & Run“ und „Action“ passen, „Puzzle“ und „Rennen“ nicht)
_FAMILY = {"Action": "akt", "Plattformer": "akt", "Shooter": "akt", "Kampfspiel": "akt", "Arcade": "akt",
           "Abenteuer": "akt rpg", "Rollenspiel": "rpg", "Strategie": "rpg sim", "Simulation": "sim", "Aufbau": "sim",
           "Sport": "sport", "Rennen": "sport", "Puzzle": "denk", "Karten und Brett": "denk", "Quiz": "denk",
           "Casual": "denk party", "Party": "party", "Lernspiel": "denk", "Musik": "party"}


def _fam(groups):
    return {f for x in groups for f in _FAMILY.get(x, "").split()}


def _same_title(a, b):
    c = lambda t: _squash(titles.norm(article_front(str(t or "").replace("_", " "))))
    return c(a) == c(b)


def own_genre(g):
    return OWN_GENRE.get(((g.get("own") or {}).get("genre") or "").casefold())


def own_conflicts(g, strict=True):
    """Wo andere Quellen beim Genre deiner Ordner-Liste widersprechen: [(Feld, deins, anderes, Quelle)]. Nur, wenn keine
    nahe Genre-Gruppe übereinstimmt. Einen anderen Titel (etwa deinen deutschen) zeigen die Einzelheiten, er ist kein
    Widerspruch.

    Ab 0.8.12 (Entscheidung 28.10.2026, nach Durchsicht aller Fälle): Deine Ordner sortieren oft nach Reihe, Lizenz oder
    Sammlung von Minispielen, die Genres der anderen Quellen kommen in der Zeile ohnehin dazu. Für „Zu erledigen“ (strict)
    zählt deshalb nur, was libretro und IGDB beide anders sagen und worin sie sich einig sind; „Party & Minispiele“
    widerspricht nie. Ohne strict jede einzelne Abweichung, für die Einzelheiten."""
    from . import collection
    own = g.get("own") or {}
    mine = _fam([own_genre(g)])
    if not mine or "party" in mine:
        return []
    other = []
    for src, raw in (("libretro", (g.get("lr") or {}).get("genre") or []), ("IGDB", (g.get("igdb") or {}).get("genres") or [])):
        fam = _fam(collection.genres(raw, []))
        if fam and not fam & mine:
            other.append((src, raw, fam))
    if not strict:
        return [("genre", own["genre"], ", ".join(raw), src) for src, raw, _ in other]
    if len(other) == 2 and other[0][2] & other[1][2]:
        return [("genre", own["genre"], "; ".join(f"{src}: {', '.join(raw)}" for src, raw, _ in other), "libretro und IGDB")]
    return []


def _conflict_id(c):
    return titles.norm(f"{c[0]} {c[1]} {c[2]} {c[3]}")[:200]


def own_list(col):
    """Retro-Spiele, bei denen andere Quellen deiner Ordner-Liste widersprechen (für „Zu erledigen“); was du schon
    mit „Liste gilt“ bestätigt hast, fehlt."""
    out = []
    for k, g in (col.get("games") or {}).items():
        if g.get("src") != SRC or not g.get("own") or g.get("gone"):
            continue
        ok = set(g.get("own_ok") or [])
        cs = [c for c in own_conflicts(g) if _conflict_id(c) not in ok]
        if cs:
            out.append({"key": k, "name": g["own"].get("title") or g["name"], "system": g.get("system") or "",
                        "diff": [{"f": c[0], "own": c[1], "other": c[2], "src": c[3]} for c in cs]})
    return sorted(out, key=lambda x: (x["system"], titles.norm(x["name"])))


def settle_own(col, key):
    """„Liste gilt“: die jetzigen Widersprüche dieses Spiels nicht mehr zeigen (ändert sich ein Wert, kommt es wieder)."""
    g = (col.get("games") or {}).get(key)
    if not g or not g.get("own"):
        raise ValueError("kein Spiel aus deiner Ordner-Liste")
    g["own_ok"] = sorted(set(g.get("own_ok") or []) | {_conflict_id(c) for c in own_conflicts(g)})[:20]
    return g
