"""VR per Mod (0.8.1): PCGamingWiki und Nexus Mods für PC-Spiele, ohne Netz.

PCGamingWiki führt je Spiel die Vorlage „VR support“; „hackable“ bei einer Brille heißt: VR geht mit einem
Mod oder Werkzeug (UEVR, VorpX …). Nexus Mods liefert die Spielseite, die beliebtesten Mods und Mods mit VR
im Namen; das ist nur ein Hinweis (violett), denn ein Name sagt nicht, dass der Mod VR bringt.
Den Abruf machen sync._pcgw und sync._nexus.
"""
import json
import re
import urllib.parse

from . import titles
from .probes import NEXUS_GQL, PCGW, PCGW_APPID, pcgw_title, pcgw_vr, search_name

V = 2                       # 2: dazu Spielerzahlen aus „Network/Multiplayer“ (0.9.5)
HEADSETS = {"htc vive": "HTC Vive", "oculus rift": "Oculus Rift", "windows mixed reality": "Windows Mixed Reality",
            "osvr": "OSVR", "openxr": "OpenXR", "steamvr": "SteamVR", "oculusvr": "Oculus"}
GAMES_PAGE = 100            # erbetene Spiele je Seite; Nexus liefert höchstens 80 (Verbindungstest 0.8.4),
GAMES_PAGES = 150           # deshalb weiter um so viele, wie kamen
VR_NAME = re.compile(r"(?i)\bvr\b|uevr|vorpx|virtual reality|\bopenxr\b|\bvrik\b")
_TAIL = re.compile(r"(?i)\s*[-:–]?\s*\b(legacy|enhanced|remastered|definitive edition|game of the year edition|goty|"
                   r"complete edition|special edition|anniversary edition)$")


def appid_url(appid):
    return PCGW_APPID + "?" + urllib.parse.urlencode({"appid": appid})


def parse_url(title):
    return PCGW + "?" + urllib.parse.urlencode({"action": "parse", "page": title, "prop": "wikitext", "format": "json", "redirects": 1})


def title(text):
    return pcgw_title(text or "")


# Arten der Vorlage „Network/Multiplayer“ zu den Arten der Sammlung (collection.MP_LABEL)
MP_PLAY = {"local play": "couch", "lan play": "lan", "online play": "online"}


def _most(v):
    """Höchste Zahl aus „4“, „2-8“, „64+“; 0 ohne Zahl."""
    return max([int(x) for x in re.findall(r"\d{1,3}", str(v or ""))] or [0])


def pcgw(text):
    """Knappe Fassung der Vorlage „VR support“: welche Brillen per Mod gehen, ob VR schon eingebaut ist, vorpX.
    Ab 0.9.5 dazu „Network/Multiplayer“: je Art (lokal, LAN, online) ob es sie gibt (mp), die Spielerzahl (pl)
    und ob es dort Koop gibt (coop)."""
    try:
        f = pcgw_vr(text)
        m = pcgw_vr(text, "Network/Multiplayer")
    except (ValueError, AttributeError):
        return {"ok": False}
    val = lambda v: str(v).strip().casefold()
    on = [k for k in MP_PLAY if val(m.get(k, "")) in ("true", "limited")]
    return {"ok": True, "page": True,
            "mod": [n for k, n in HEADSETS.items() if val(f.get(k, "")) == "hackable"],
            "native": [n for k, n in HEADSETS.items() if val(f.get(k, "")) == "true"],
            "vorpx": val(f.get("vorpx", "")) == "true",
            "mp": [MP_PLAY[k] for k in on],
            "pl": {MP_PLAY[k]: _most(m.get(k + " players")) for k in on if _most(m.get(k + " players")) > 1},
            "coop": [MP_PLAY[k] for k in on if "co-op" in val(m.get(k + " modes", ""))]}


def games_query(offset):
    return json.dumps({"query": "query($o:Int!){games(count:%d,offset:$o){totalCount nodes{id domainName name modCount}}}" % GAMES_PAGE,
                      "variables": {"o": offset}}).encode()


def games_page(text):
    """(Spiele, Gesamtzahl, Zahl der Einträge der Seite) einer Seite der Spieleliste; None bei einer Fehlerantwort."""
    try:
        d = json.loads(text or "{}")
    except ValueError:
        return None
    g = (d.get("data") or {}).get("games") if isinstance(d, dict) and not d.get("errors") else None
    if not isinstance(g, dict):
        return None
    nodes = [{"dom": str(n.get("domainName") or ""), "name": str(n.get("name") or "")[:200], "mods": int(n.get("modCount") or 0)}
             for n in g.get("nodes") or [] if isinstance(n, dict) and n.get("domainName")]
    return nodes, int(g.get("totalCount") or 0), len(g.get("nodes") or [])


def keys(name):
    """Namen zum Vergleich: wie geschrieben, ohne Klammern, ohne Zusätze wie „Legacy“."""
    plain = search_name(name)
    return {k for k in (titles.norm(name), titles.norm(plain), titles.norm(_TAIL.sub("", plain))) if k}


def index(games):
    out = {}
    for g in games:
        for k in keys(g["name"]):
            if k not in out or g["mods"] > out[k]["mods"]:
                out[k] = g
    return out


def find(idx, name):
    for k in keys(name):
        if k in idx:
            return idx[k]
    return None


def mods_query(dom):
    q = ("query($d:String!){top:mods(filter:{gameDomainName:{value:$d}},sort:{endorsements:{direction:DESC}},count:3)"
         "{nodes{name endorsements downloads modId}} vr:mods(filter:{gameDomainName:{value:$d},name:{value:\"*VR*\",op:WILDCARD}},"
         "sort:{endorsements:{direction:DESC}},count:10){totalCount nodes{name endorsements downloads modId}} "
         "vx:mods(filter:{gameDomainName:{value:$d},name:{value:\"*vorp*\",op:WILDCARD}},sort:{endorsements:{direction:DESC}},count:3)"
         "{nodes{name endorsements downloads modId}}}")
    return json.dumps({"query": q, "variables": {"d": dom}}).encode()


def mods(text):
    """Beliebteste Mods und Mods mit VR im Namen (geprüft auf ganze Wörter: „VRAM“ zählt nicht)."""
    try:
        d = json.loads(text or "{}")
    except ValueError:
        return None
    if not isinstance(d, dict) or d.get("errors") or not isinstance(d.get("data"), dict):
        return None
    m = d["data"]
    pick = lambda b: [{"name": str(x.get("name") or "")[:80], "id": int(x.get("modId") or 0), "end": int(x.get("endorsements") or 0)}
                      for x in ((b or {}).get("nodes") or []) if isinstance(x, dict) and x.get("modId")]
    vr = [x for x in pick(m.get("vr")) + pick(m.get("vx")) if VR_NAME.search(x["name"])]
    vr = list({x["id"]: x for x in sorted(vr, key=lambda x: -x["end"])}.values())[:3]
    return {"top": pick(m.get("top")), "vr": vr}


def mod_url(dom, mid):
    return f"https://www.nexusmods.com/{dom}/mods/{int(mid)}"


def game_url(dom):
    return f"https://www.nexusmods.com/games/{dom}"


GQL = NEXUS_GQL
