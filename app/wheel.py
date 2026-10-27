"""Sim-Racing (0.8.3): passt ein PC-Spiel zum Lenkrad? Ohne Netz.

Zwei Quellen (Entscheidung 27.10.2026, „Beides“): Steam-Schlagwörter sind ein Hinweis (violett), denn
„Racing“ heißt nicht, dass ein Lenkrad mit Force Feedback geht. Bestätigung ist eine Liste der
Rennsimulationen für Direktantriebe: Die Kompatibilitätsliste zu Simagic liegt hinter einer Bot-Prüfung, also
die offene Liste im Forum von Simucube (Granite Devices), als Rohtext. Simagic und Simucube sind beides
Direktantriebe mit Force Feedback über DirectInput; was dort läuft, läuft auch mit Simagic.
Den Abruf macht sync._wheel.
"""
import json
import re
import urllib.parse

from . import titles
from .probes import search_name

V = 1
LIST = "https://community.granitedevices.com/raw/5645"
LIST_NAME = "Liste der Rennsimulationen (Simucube-Forum)"
LIST_FILE = "wheel_list.json"
TAGS_FILE = "steam_tags.json"
GETITEMS = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"
TAGLIST = "https://api.steampowered.com/IStoreService/GetTagList/v1/?language=english"
BATCH = 50                  # Apps je Anfrage an GetItems
TOP = 12                    # nur die stärksten Schlagwörter zählen
# Feste Kennungen, falls die Liste der Schlagwörter nicht kommt (Steam ändert sie nicht)
KNOWN = {599: "Simulation", 699: "Racing", 1644: "Driving", 1100687: "Automobile Sim"}
SIM = {"sim racing", "automobile sim"}
RACE = {"racing", "driving"}


def items_url(appids):
    return GETITEMS + "?" + urllib.parse.urlencode({"input_json": json.dumps(
        {"ids": [{"appid": int(a)} for a in appids], "context": {"language": "english", "country_code": "DE"},
         "data_request": {"include_tag_count": 20}}, separators=(",", ":"))})


def tag_list(text):
    """{Kennung: Name} aus GetTagList; leer, wenn die Antwort nicht passt."""
    try:
        tags = ((json.loads(text or "{}") or {}).get("response") or {}).get("tags") or []
    except (ValueError, AttributeError):
        return {}
    out = {}
    for t in tags:
        try:
            out[int(t["tagid"])] = str(t["name"])[:60]
        except (KeyError, TypeError, ValueError):
            pass
    return out


def items(text):
    """{Steam-ID: [Kennungen der Schlagwörter, stärkste zuerst]} aus GetItems; None bei einer Fehlerantwort."""
    try:
        d = (json.loads(text or "{}") or {}).get("response")
    except (ValueError, AttributeError):
        return None
    if not isinstance(d, dict):
        return None
    out = {}
    for it in d.get("store_items") or []:
        if not isinstance(it, dict) or not it.get("appid"):
            continue
        tags = [t for t in it.get("tags") or [] if isinstance(t, dict) and t.get("tagid")]
        if tags:
            ids = [int(t["tagid"]) for t in sorted(tags, key=lambda t: -int(t.get("weight") or 0))]
        else:
            ids = [int(x) for x in it.get("tagids") or [] if str(x).isdigit()]
        out[str(it["appid"])] = ids[:20]
    return out


def names(ids, known):
    return [known.get(i) or KNOWN.get(i) or "" for i in ids]


def hint(tag_names):
    """Schlagwörter, die auf Sim-Racing deuten: „Sim Racing“ oder „Automobile Sim“ oder Rennen mit
    „Simulation“. Leer, wenn nichts passt."""
    top = [n for n in tag_names[:TOP] if n]
    low = [n.casefold() for n in top]
    if any(n in SIM for n in low) or ("simulation" in low and any(n in RACE for n in low)):
        return [n for n in top if n.casefold() in SIM | RACE | {"simulation"}]
    return []


_SKIP = re.compile(r"(?i)https?://|\bwiki\b|\blist\b|\bedit\b|\bthis\b|\bthe following\b|[.!?]$")


def game_list(text):
    """Namen aus dem Rohtext der Liste: eine Zeile je Spiel, ohne Einleitung (Sätze, Links)."""
    out = []
    for line in (text or "").splitlines():
        n = line.strip().strip("*-• ").strip()
        if 2 <= len(n) <= 70 and not _SKIP.search(n) and not n.startswith(("#", "[", ">", "<")):
            out.append(n)
    return list(dict.fromkeys(out))


def keys(name):
    plain = search_name(name)
    return {k for k in (titles.norm(name), titles.norm(plain)) if k}


def index(names_):
    return {k: n for n in names_ for k in keys(n)}


def find(idx, *names_):
    for name in names_:
        for k in keys(name or ""):
            if k in idx:
                return idx[k]
    return None
