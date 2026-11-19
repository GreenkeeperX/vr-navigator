"""Flat-to-VR (0.10.28): VR-Ports aus dem Flat2VR Index und UEVR-Profile aus dem UEVR Hub, ohne Netz.

Flat2VR Index: eine Datei je Port, gesammelt in data/ports.json (CC0 1.0). Ein Port ist ein eigener VR-Mod, ein
Source-Port mit VR oder ein Profil für ein VR-Werkzeug, mit Stand (alpha bis stable, aufgegeben), Plattform
(PCVR, Quest ohne PC, beides), Steuerung und Version.
UEVR Hub: repo.json mit allen gesammelten UEVR-Profilen (dieselbe Datei lädt die Seite des Hubs). Ein Profil
heißt nur „es gibt eines“, nicht „es läuft gut“; deshalb steht es als Hinweis da (gestrichelt).

Beide Dateien nennen keine Steam-ID. Zugeordnet wird deshalb vorsichtig über den Namen (`assign`):
- ein Zusatz in Klammern muss passen: ein Jahr gegen das Erscheinungsjahr, ein System („GameCube“) gegen das
  System des Spiels, alles andere („Remake“) nur gegen einen Namen, der ihn auch trägt;
- ohne Systemzusatz nur Spiele der Sammlung PC;
- passen zwei Spiele desselben Systems zum selben Namen, bekommt keines den Eintrag;
- Spiele mit eingebautem VR bekommen keinen.
Abgerufen in sync._flat2vr; die Dateien flat2vr.json und uevr.json liegen im Datenordner, die Sammlung bleibt unberührt.
"""
import json
import re
from urllib.parse import parse_qs, urlparse

from . import titles

V = 1
PORTS = "https://raw.githubusercontent.com/jrejaud/awesome-flat2vr/HEAD/data/ports.json"
PORTS_HOME = "https://github.com/jrejaud/awesome-flat2vr"
PORTS_NAME = "Flat2VR Index"
UEVR = "https://raw.githubusercontent.com/uevr-profiles/repo/main/repo.json"
UEVR_HOME = "https://uevr-profiles.github.io/"
UEVR_NAME = "UEVR Hub"
PORTS_FILE = "flat2vr.json"
UEVR_FILE = "uevr.json"
MIN_PORTS = 20              # weniger Einträge heißt: die Datei sah anders aus, alte Liste behalten
MIN_UEVR = 50
REMOVED_KEEP = 50           # so viele entfernte Einträge bleiben zum Nachsehen

CATS = {"mod": "VR-Mod", "source-port": "Source-Port", "profile": "Profil"}
PLATS = {"pcvr": "PCVR", "standalone": "Quest ohne PC", "both": "PCVR und Quest ohne PC"}
CTLS = {"6dof": "Bewegungssteuerung (6DOF)", "3dof": "3DOF", "gamepad": "Gamepad", "mixed": "gemischt"}
STATES = {"alpha": "Alpha", "beta": "Beta", "stable": "stabil", "abandoned": "aufgegeben"}
_YEAR_PC = re.compile(r"(?i)^(19[7-9]\d|20[0-4]\d)(?:\s+pc(?:\s+port)?)?$")     # „1999“, „2002 PC“, „2024 PC port“
_QUAL = re.compile(r"^(.*\S)\s*\(([^()]+)\)\s*$")


def _https(u):
    """Nur https-Links mit Host; alles andere wird leer (kein javascript:, keine Adressen mit Zugangsdaten)."""
    u = str(u or "").strip()
    try:
        p = urlparse(u)
    except ValueError:
        return ""
    return u[:500] if p.scheme == "https" and p.hostname and not p.username and not p.password else ""


def _s(v, n=120):
    return " ".join(str(v or "").split())[:n]


def _date(v):
    v = str(v or "")[:10]
    return v if re.match(r"^\d{4}-\d{2}-\d{2}$", v) else ""


def parse_ports(text):
    """Knappe Ports aus data/ports.json; None, wenn die Datei kein Liste von Ports ist."""
    try:
        d = json.loads(text or "")
    except ValueError:
        return None
    if not isinstance(d, list):
        return None
    out = []
    for p in d:
        if not isinstance(p, dict) or not isinstance(p.get("games"), list) or not _s(p.get("name")):
            continue
        games = [_s(g, 160) for g in p["games"] if isinstance(g, str) and _s(g)]
        slug = re.sub(r"[^a-z0-9-]", "", str(p.get("slug") or "").lower())[:80] or titles.norm(p["name"]).replace(" ", "-")
        if not games:
            continue
        bugs = [_s(b, 160) for b in (p.get("known_bugs") or []) if isinstance(b, str) and _s(b)]
        out.append({"slug": slug, "name": _s(p["name"]), "games": games[:8],
                    "cat": p.get("category") if p.get("category") in CATS else "",
                    "plat": p.get("platform") if p.get("platform") in PLATS else "",
                    "ctl": p.get("controls") if p.get("controls") in CTLS else "",
                    "st": p.get("status") if p.get("status") in STATES else "",
                    "ver": _s(p.get("version"), 40), "vdate": _date(p.get("version_date")),
                    "dl": _https(p.get("download_url")), "src": _https(p.get("source_url")), "home": _https(p.get("homepage")),
                    "by": [_s(a.get("name"), 60) for a in (p.get("authors") or []) if isinstance(a, dict) and _s(a.get("name"))][:3],
                    "price": _s(p.get("price"), 80), "bugs": bugs[:5], "bugs_n": len(bugs),
                    "hs": [_s(h, 40) for h in (p.get("headsets") or []) if isinstance(h, str)][:6],
                    "chk": _date(p.get("last_checked"))})
    return out


def _profile_dir(p):
    """Ordner des Profils im Repository des Hubs (zum Ansehen), aus dem Link der Download-Hilfe."""
    try:
        u = (parse_qs(urlparse(str(p.get("downloadUrl") or "")).query).get("url") or [""])[0]
    except ValueError:
        return ""
    return u if re.match(r"^https://github\.com/uevr-profiles/repo/tree/main/[\w/-]{1,120}$", u) else ""


def parse_uevr(text):
    """UEVR-Profile je Spiel zusammengefasst: Zahl, 6DOF oder 3DOF, Bewegungssteuerung, jüngstes Datum, Autoren und
    der Ordner des jüngsten Profils. None, wenn die Datei keine Liste ist."""
    try:
        d = json.loads((text or "").lstrip("﻿"))
    except ValueError:
        return None
    if not isinstance(d, list):
        return None
    games = {}
    for p in d:
        if not isinstance(p, dict) or not _s(p.get("gameName")):
            continue
        name = _s(p["gameName"], 160)
        k = titles.norm(name)
        if not k:
            continue
        tags = {str(t).strip().casefold() for t in (p.get("tags") or []) if isinstance(t, str)}
        date = _date(p.get("modifiedDate") or p.get("createdDate") or "")
        g = games.setdefault(k, {"name": name, "n": 0, "dof": "", "mc": False, "date": "", "by": [], "dir": ""})
        g["n"] += 1
        if "6dof" in tags:
            g["dof"] = "6dof"
        elif "3dof" in tags and not g["dof"]:
            g["dof"] = "3dof"
        g["mc"] = g["mc"] or "motion controls" in tags
        a = _s(p.get("authorName"), 60)
        if a and a not in g["by"] and len(g["by"]) < 3:
            g["by"].append(a)
        if date >= g["date"]:
            g["date"] = date
            g["dir"] = _profile_dir(p) or g["dir"]
    return sorted(games.values(), key=lambda g: titles.norm(g["name"]))


def _split(name, sys_of):
    """(Name ohne Zusatz, Art des Zusatzes, Wert): Art "" ohne Zusatz, "year", "sys" oder "exact" (der Zusatz
    gehört zum Namen, etwa „Remake“)."""
    m = _QUAL.match(name)
    if not m:
        return name, "", ""
    q = m.group(2).strip()
    if q.casefold() in ("pc", "windows", "pc port"):
        return m.group(1), "", ""
    y = _YEAR_PC.match(q)
    if y:
        return m.group(1), "year", y.group(1)
    s = sys_of(q) if sys_of else ""
    if s and s != "PC":
        return m.group(1), "sys", s
    return name, "exact", ""


def _wants(names, sys_of):
    """Je Name einer Quelle (mit „ / “ getrennte Spiele einzeln) die Bedingung zum Zuordnen: (Schlüssel, System, Jahr)."""
    out = []
    for n in names:
        for part in re.split(r"\s+/\s+", n):
            base, kind, val = _split(part.strip(), sys_of)
            k = titles.norm(base)
            if k:
                out.append((k, val if kind == "sys" else "PC", val if kind == "year" else ""))
    return out


def assign(items, ports, uevr, sys_of=None):
    """Ports und UEVR-Profile zu Spielen der Sammlung. items: Dicts mit key, names (Name, Steam- und IGDB-Name),
    system, year und vr (eingebautes VR). Ergebnis: {key: {"ports": [...], "uevr": {...}}} und die Zahl der
    Namen, die mehr als ein Spiel trafen (nicht zugeordnet)."""
    idx = {}
    for it in items:
        sysname = it.get("system") or "PC"
        for k in {titles.norm(n) for n in it.get("names") or [] if n}:
            if k:
                idx.setdefault((sysname, k), []).append(it)
    out, amb = {}, set()

    def put(want, field, val):
        k, sysname, year = want
        hits = idx.get((sysname, k)) or []
        if year:
            hits = [h for h in hits if str(h.get("year") or "") == year]
        if len(hits) > 1:
            amb.add((sysname, k))
            return
        if hits and not hits[0].get("vr"):
            slot = out.setdefault(hits[0]["key"], {})
            if field == "ports":
                if all(p["slug"] != val["slug"] for p in slot.get("ports", [])):
                    slot.setdefault("ports", []).append(val)
            else:
                slot.setdefault("uevr", val)

    for p in ports or []:
        for w in _wants(p["games"], sys_of):
            put(w, "ports", p)
    for g in uevr or []:
        for w in _wants([g["name"]], sys_of):
            if w[1] == "PC":
                put(w, "uevr", g)
    return out, len(amb)


def row_ports(ports):
    """Was die Oberfläche je Port braucht (ohne Spieleliste und Autorenlinks)."""
    keep = ("slug", "name", "cat", "plat", "ctl", "st", "ver", "vdate", "dl", "src", "home", "by", "price", "bugs", "bugs_n", "chk")
    return [{k: p.get(k) for k in keep} for p in ports]


def removed(old, new, key):
    """Einträge aus old, die in new fehlen (key: Feld, das sie unterscheidet)."""
    have = {x.get(key) for x in new or []}
    return [x for x in old or [] if x.get(key) not in have]
