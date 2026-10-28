"""Sim-Racing (0.8.3): passt ein PC-Spiel zum Lenkrad? Ohne Netz.

Zwei Quellen (Entscheidung 27.10.2026, „Beides“): Steam-Schlagwörter sind ein Hinweis (violett), denn
„Racing“ heißt nicht, dass ein Lenkrad mit Force Feedback geht. Bestätigung ist eine Liste der
Rennsimulationen für Direktantriebe: Die Kompatibilitätsliste zu Simagic liegt hinter einer Bot-Prüfung, also
die offene Liste im Forum von Simucube (Granite Devices), als Rohtext. Simagic und Simucube sind beides
Direktantriebe mit Force Feedback über DirectInput; was dort läuft, läuft auch mit Simagic. Ab 0.8.5 dazu die
Liste „Supported Games“ von SimHub (Abschnitt Racing), die laufend gepflegt wird; ihre Bilder tragen die Steam-ID
im Dateinamen, darüber passt die Zuordnung ohne Namensvergleich.
Den Abruf macht sync._wheel.
"""
import html
import json
import re
import urllib.parse

from . import titles
from .probes import search_name

V = 2                       # Stand des Lesers; ändert er sich, liest der Abgleich beide Listen neu (0.8.6)
LIST = "https://community.granitedevices.com/raw/5645"
LIST_NAME = "Liste der Rennsimulationen (Simucube-Forum)"
LIST_FILE = "wheel_list.json"
SIMHUB = "https://www.simhubdash.com/supported-games/"
SIMHUB_NAME = "SimHub, unterstützte Rennspiele"
TAGS_FILE = "steam_tags.json"
GETITEMS = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"
TAGLIST = "https://api.steampowered.com/IStoreService/GetTagList/v1/?language=english"
BATCH = 50                  # Apps je Anfrage an GetItems
TOP = 10                    # nur die stärksten Schlagwörter zählen
# Feste Kennungen, falls die Liste der Schlagwörter nicht kommt (Steam ändert sie nicht)
KNOWN = {599: "Simulation", 699: "Racing", 1644: "Driving", 1100687: "Automobile Sim"}
SIM = {"automobile sim", "simulation"}
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
    """Schlagwörter, die auf Sim-Racing deuten: unter den stärksten zehn ein Rennen („Racing“, „Driving“) und
    eine Simulation („Automobile Sim“, „Simulation“). „Automobile Sim“ allein reicht nicht (0.8.5: ein
    Open-World-Spiel mit Autos trug es weit oben). Leer, wenn nichts passt."""
    top = [n for n in tag_names[:TOP] if n]
    low = {n.casefold() for n in top}
    if low & RACE and low & SIM:
        return [n for n in top if n.casefold() in SIM | RACE]
    return []


_SKIP = re.compile(r"(?i)https?://|\bwiki\b|\blist\b|\bedit\b|\bthis\b|\bthe following\b|[.!?,:;]$")
# Kopf eines Beitrags im Rohtext von Discourse: „Name | 2021-12-15 11:01:45 UTC | #1“
_POST = re.compile(r"^.*\|\s*\d{4}-\d\d-\d\d[ T][\d:]+\s*UTC\s*\|\s*#(\d+)\s*$")


def game_list(text):
    """Namen aus dem Rohtext der Liste: eine Zeile je Spiel, nur aus dem ersten Beitrag (die Antworten sind
    Gespräch), ohne Einleitung (Sätze, Links) und ohne Köpfe der Beiträge."""
    lines = (text or "").splitlines()
    heads = [(i, int(m.group(1))) for i, m in ((i, _POST.match(x.strip())) for i, x in enumerate(lines)) if m]
    if heads:
        start = next((i for i, n in heads if n == 1), heads[0][0])
        end = next((i for i, _ in heads if i > start), len(lines))
        lines = lines[start + 1:end]
    out = []
    for line in lines:
        n = line.strip().strip("*-• ").strip()
        if 2 <= len(n) <= 70 and not _SKIP.search(n) and not n.startswith(("#", "[", ">", "<")) and not re.fullmatch(r"-{3,}", n):
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


def _plain(html_text):
    t = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", html_text)
    t = re.sub(r"(?i)<br\s*/?>|</(p|div|li|h\d|figcaption|span|a|td)>", "\n", t)
    return html.unescape(re.sub(r"<[^>]+>", " ", t))


def simhub(text):
    """Abschnitt „Racing“ der SimHub-Seite: Steam-IDs aus den Bildnamen („…/244210-300x140.jpg“) und die Namen
    darunter (ohne Zusätze wie „(PC only)“). Leer, wenn der Abschnitt fehlt."""
    text = text or ""
    m = re.search(r"(?i)>\s*Racing\s*<", text)
    if not m:
        return {"apps": [], "names": []}
    end = re.search(r"(?i)>\s*Flight simulators?\s*<|>\s*Others\s*<", text[m.end():])
    sec = text[m.end():m.end() + end.start() + 1] if end else text[m.end():]
    sec = sec[sec.find(">") + 1:]           # Rest der Überschrift „Racing“
    sec = sec[:sec.rfind("<")] if end else sec
    apps = re.findall(r"/uploads/\d{4}/\d\d/(\d{3,8})-\d+x\d+\.(?:jpe?g|png|webp)", sec)
    names = []
    for line in _plain(sec).splitlines():
        n = " ".join(line.split())
        if 2 <= len(n) <= 70 and not _SKIP.search(n):
            names.append(n)
    return {"apps": list(dict.fromkeys(apps)), "names": list(dict.fromkeys(names))}


def matcher(wl):
    """Prüfung gegen beide Listen aus wheel_list.json: f(Steam-ID, Namen …) → Quellen, in denen das Spiel steht."""
    sc = index(wl.get("names") or [])
    sh = wl.get("simhub") or {}
    sh_idx, sh_apps = index(sh.get("names") or []), set(sh.get("apps") or [])

    def f(appid, *names_):
        out = []
        if (appid and str(appid) in sh_apps) or (sh_idx and find(sh_idx, *names_)):
            out.append("SimHub")
        if sc and find(sc, *names_):
            out.append("Simucube-Forum")
        return out
    return f


def row(match, appid, stag, *names_):
    """Angabe für eine Zeile: {"src": [Listen], "tags": [Schlagwörter]} oder None."""
    srcs = match(appid, *names_)
    tags = hint((stag or {}).get("tags") or [])
    return {"src": srcs, "tags": tags} if srcs or tags else None
