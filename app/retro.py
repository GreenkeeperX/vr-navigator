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
INDEX_V = 1
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
    "wii": "Wii", "wiiu": "Wii U", "psx": "PS", "ps1": "PS", "ps": "PS", "ps2": "PS2", "ps3": "PS3",
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


def split_path(line):
    """Ordner und Dateiname aus einer Zeile (Linux oder Windows, absolut oder relativ)."""
    p = line.strip().strip('"').replace("\\", "/")
    p = re.sub(r"^[A-Za-z]:/", "", p)
    parts = [x for x in p.split("/") if x not in ("", ".")]
    return parts[:-1], (parts[-1] if parts else "")


def article_front(title):
    """No-Intro schreibt „Legend of Pixels, The - Teil 2“; angezeigt wird „The Legend of Pixels - Teil 2“."""
    m = _ARTICLE.match(title)
    return f"{m.group(2)} {m.group(1)}{m.group(3) or ''}" if m else title


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
    if not info["title"]:
        return None, "unknown"
    low = "/".join(dirs).casefold()
    if re.search(r"(?:^|/)_?extras?/homebrew(?:/|$)|(?:^|/)homebrew(?:/|$)", low):
        info["flags"] = sorted(set(info["flags"]) | {"homebrew"})
    if any(_HACK.fullmatch(d) or d.casefold() in ("rom-hacks", "romhacks") for d in dirs):
        info["flags"] = sorted(set(info["flags"]) | {"hack"})
    info["file"] = fname
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


def apply(col, games, dry=True):
    """Neue Retro-Liste mit der Sammlung abgleichen. Spiele anderer Quellen bleiben unberührt.
    Fehlt ein Retro-Spiel eines Systems, das in der neuen Liste vorkommt, bekommt es „gone“
    (Tag), statt gelöscht zu werden; taucht es wieder auf, fällt die Marke weg.
    Gibt (neu, Namen der fehlenden) zurück."""
    old = col.get("games") or {}
    systems = {g["system"] for g in games.values()}
    new = [k for k in games if k not in old]
    gone = [k for k, g in old.items() if g.get("src") == SRC and g.get("system") in systems and k not in games]
    if dry:
        return len(new), sorted(old[k]["name"] for k in gone)
    day = titles.now_iso()
    for k, g in games.items():
        o = old.get(k)
        if o:
            for f in ("rev", "steam", "mark", "info"):
                if f in o:
                    g[f] = o[f]
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
    "PS": ("redump", "Sony - PlayStation"), "PS2": ("redump", "Sony - PlayStation 2"), "PSP": ("redump", "Sony - PlayStation Portable"),
}
_SKIP_REL = re.compile(r"\((?:Beta|Proto|Demo|Sample|Kiosk|Pirate|Debug)[^)]*\)", re.I)


def urls(system):
    """Adressen der Fassungsliste und der Retool-Liste eines Systems, None ohne Liste."""
    kind, name = DATS.get(system, (None, None))
    if not kind:
        return None
    from urllib.parse import quote
    label = "No-Intro" if kind == "no-intro" else "Redump"
    return LIBRETRO + kind + "/" + quote(name) + ".dat", RETOOL + quote(f"{name} ({label})") + ".json"


def _serial_code(serial):
    """Produktcode ohne Region: „AMRD“ und „AMRE“ sind dasselbe Spiel (letzter Buchstabe = Region).
    Redump-Codes wie „SLES-01234“ sind je Region verschieden und zählen nicht."""
    s = str(serial or "").strip().upper()
    return s[:3] if re.fullmatch(r"[A-Z0-9]{4}", s) else ""


def build_index(dat_text, retool_text=""):
    """Fassungen eines Systems aus einer libretro-DAT und der Retool-Liste. Fassungen gehören zu
    einer Gruppe, wenn sie denselben Titel, denselben Produktcode oder dieselbe Retool-Gruppe
    haben. Ergebnis: {"rel": [[Name, Sprachen, geschätzt]], "grp": {Titel: Gruppe},
    "mem": {Gruppe: [Fassungen]}, "via": {Gruppe: „code“/„retool“/„name“}}."""
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
    retool = {}
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
    for m in re.finditer(r'rom \( name "([^"]+)"([^)]*)', str(dat_text or "")):
        fname = m.group(1)
        if _SKIP_REL.search(fname):
            continue
        info = parse_name(fname)
        if not info["title"]:
            continue
        sm = re.search(r'serial "([^"]*)"', m.group(2))
        name = re.sub(r"\.[A-Za-z0-9]{1,6}$", "", fname)
        i = len(rels)
        rels.append([name, ",".join(info["langs"]), 1 if info["lang_guess"] else 0])
        t = "t:" + titles.norm(info["title"])
        union(t, "r:" + str(i), "name")
        code = _serial_code(sm.group(1) if sm else "")
        if code:
            union(t, "c:" + code, "code")
        rg = retool.get(t[2:])
        if rg:
            union(t, rg, "retool")
    grp, mem = {}, {}
    for x in list(parent):
        r = find(x)
        if x.startswith("t:"):
            grp[x[2:]] = r
        elif x.startswith("r:"):
            mem.setdefault(r, []).append(int(x[2:]))
    via = {r: ("code" if "code" in w else "retool" if "retool" in w else "name") for r, w in joined.items() if r in mem}
    return {"rel": rels, "grp": grp, "mem": mem, "via": via}


def _de_rank(rel):
    """Beste deutsche Fassung zuerst: Deutsch ausdrücklich genannt, dann Germany, dann Europe."""
    name, langs, guess = rel
    return (guess, "(Germany" not in name, "Europe" not in name, len(langs), name)


def match(g, idx):
    """Gab es das Spiel mit Deutsch? {"st": have (deine Datei hat Deutsch), missing (es gab eine
    Fassung mit Deutsch, deine hat keins; alt: die gesuchte Fassung), none (keine deutsche Fassung
    bekannt), unknown (nicht in der Liste)}, dazu via (code, retool, name) und guess, wenn das
    Deutsch der gesuchten Fassung nur aus der Region geschätzt ist."""
    if "De" in (g.get("langs") or []):
        return {"st": "have"}
    r = (idx.get("grp") or {}).get(titles.norm(g.get("name") or ""))
    members = (idx.get("mem") or {}).get(r) if r else None
    if not members:
        return {"st": "unknown"}
    rels = [idx["rel"][i] for i in members if i < len(idx["rel"])]
    de = sorted((x for x in rels if "De" in x[1].split(",")), key=_de_rank)
    if not de:
        return {"st": "none"}
    return {"st": "missing", "alt": de[0][0][:200], "guess": bool(de[0][2]), "via": (idx.get("via") or {}).get(r, "name")}


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
