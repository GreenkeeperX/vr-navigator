"""IGDB im Abgleich (0.8.0): Spielinfos für die ganze Sammlung, einheitlich über alle Plattformen.

Steam-Spiele über die Steam-ID, gebündelt (bis 400 je Anfrage), alle anderen über Name und System wie
in der Probe (app/probes.py). Hier steht nur Lesen und Bauen der Anfragen, ohne Netz; den Abruf macht
sync._igdb. Gespeichert wird je Spiel unter „igdb“ in collection.json eine knappe Fassung (`compact`).
"""
import json
import re
import urllib.parse
from datetime import datetime, timezone

from . import titles
from .probes import IGDB_PLATFORMS, search_name

API = "https://api.igdb.com/v4/"
TWITCH = "https://id.twitch.tv/oauth2/token"
V = 1               # Stand der knappen Fassung; ändert er sich, liest der Abgleich alles neu
CHUNK = 400         # Kennungen je Anfrage (IGDB erlaubt bis 500 Treffer)
FIELDS = ("fields name,first_release_date,genres.name,game_modes.name,aggregated_rating,aggregated_rating_count,"
          "total_rating,total_rating_count,summary,involved_companies.company.name,involved_companies.developer,"
          "involved_companies.publisher,multiplayer_modes.onlinemax,multiplayer_modes.offlinemax,"
          "multiplayer_modes.onlinecoop,multiplayer_modes.offlinecoop,multiplayer_modes.splitscreen,"
          "multiplayer_modes.lancoop,multiplayer_modes.platform;")
CRIT_MIN = 3        # Kritiken, ab denen die Kritiker-Wertung zählt
TOTAL_MIN = 10      # Bewertungen, ab denen die Gesamtwertung zählt


def token_body(cid, secret):
    return urllib.parse.urlencode({"client_id": cid, "client_secret": secret, "grant_type": "client_credentials"}).encode()


def token(text):
    try:
        return (json.loads(text or "{}") or {}).get("access_token") or None
    except (ValueError, AttributeError):
        return None


def chunks(items, n=CHUNK):
    return [items[i:i + n] for i in range(0, len(items), n)]


def steam_query(appids, old=False):
    """Steam-IDs zu IGDB-Spielen. old: Feldname der Schnittstelle vor 2025 (category statt external_game_source)."""
    uids = ",".join(json.dumps(str(a)) for a in appids)
    return f"fields game,uid; where uid = ({uids}) & {'category' if old else 'external_game_source'} = 1; limit 500;"


def games_query(ids):
    return f"{FIELDS} where id = ({','.join(str(int(i)) for i in ids)}); limit 500;"


def times_query(ids):
    return f"fields game_id,hastily,normally,completely,count; where game_id = ({','.join(str(int(i)) for i in ids)}); limit 500;"


def name_queries(name, system):
    """Anfragen für die Namenssuche, in dieser Reihenfolge (wie die Probe seit 0.7.5): wie geschrieben mit
    Plattform, ohne Sonderzeichen, ohne Satzzeichen, nur der Teil nach dem Doppelpunkt, ohne Plattform,
    zuletzt der Name als Teilstück bis zum ersten Sonderzeichen."""
    plat = IGDB_PLATFORMS.get(system)
    flat = " ".join(re.sub(r"[^\w\s]", " ", search_name(name)).split())
    tail = search_name(name).split(":", 1)[1].strip() if ":" in name else ""
    tries = [(name, plat), (search_name(name), plat), (flat, plat)] + ([(tail, plat)] if tail else []) + ([(flat, None)] if plat else [])
    out = [f"search {json.dumps(q, ensure_ascii=False)}; {FIELDS} " + (f"where platforms = ({p}); limit 5;" if p else "limit 5;")
           for q, p in dict.fromkeys(t for t in tries if t[0].strip())]
    raw = (name.split(":", 1)[1] if ":" in name else name).strip()
    part = re.match(r"[A-Za-z0-9 '&.-]*", raw).group(0).strip()
    if len(part) >= 6 and part != raw:
        out.append(f"{FIELDS} where name ~ *{json.dumps(part)}*" + (f" & platforms = ({plat})" if plat else "") + "; limit 5;")
    return out


def _words(n):
    return set(titles.norm(search_name(n)).split())


def pick(games, name):
    """Der passende Treffer oder None: gleicher Name, sonst einer, dessen Name den gesuchten enthält oder
    umgekehrt („007 - Everything or Nothing“ und „James Bond 007: Everything or Nothing“), sonst einer mit
    weitgehend gleichen Wörtern. Ein beliebiger erster Treffer zählt nicht (falsches Spiel ist schlimmer als keins)."""
    want = titles.norm(search_name(name))
    ws = _words(name)
    best, best_q = None, 0.0
    for g in games or []:
        if not isinstance(g, dict) or not g.get("name"):
            continue
        have = titles.norm(g["name"])
        if have == want:
            return g
        hs = set(have.split())
        if min(len(ws), len(hs)) >= 3 and (ws <= hs or hs <= ws):
            q = 0.9
        else:
            q = len(ws & hs) / len(ws | hs) if ws | hs else 0
        if q > best_q:
            best, best_q = g, q
    return best if best_q >= 0.6 else None


def _year(ts):
    try:
        return str(datetime.fromtimestamp(int(ts), timezone.utc).year) if ts else ""
    except (TypeError, ValueError, OverflowError, OSError):
        return ""


def compact(g):
    """Knappe Fassung eines IGDB-Spiels für collection.json."""
    mm = [m for m in g.get("multiplayer_modes") or [] if isinstance(m, dict)]
    num = lambda k: max([int(m.get(k) or 0) for m in mm] or [0])
    comp = [c for c in g.get("involved_companies") or [] if isinstance(c, dict) and isinstance(c.get("company"), dict)]
    out = {"id": int(g.get("id") or 0), "name": str(g.get("name") or "")[:200],
           "genres": [str(x.get("name"))[:40] for x in g.get("genres") or [] if isinstance(x, dict)][:8],
           "modes": [str(x.get("name"))[:60] for x in g.get("game_modes") or [] if isinstance(x, dict)][:8],
           "on": num("onlinemax"), "off": num("offlinemax"),
           "coop_on": any(m.get("onlinecoop") for m in mm), "coop_off": any(m.get("offlinecoop") for m in mm),
           "split": any(m.get("splitscreen") for m in mm), "lan": any(m.get("lancoop") for m in mm),
           "year": _year(g.get("first_release_date")),
           "desc": " ".join(str(g.get("summary") or "").split())[:900],
           "dev": next((c["company"].get("name") for c in comp if c.get("developer")), "") or "",
           "pub": next((c["company"].get("name") for c in comp if c.get("publisher")), "") or ""}
    if g.get("aggregated_rating") and (g.get("aggregated_rating_count") or 0) >= CRIT_MIN:
        out["crit"], out["crit_n"] = round(g["aggregated_rating"]), int(g["aggregated_rating_count"])
    if g.get("total_rating") and (g.get("total_rating_count") or 0) >= TOTAL_MIN:
        out["total"], out["total_n"] = round(g["total_rating"]), int(g["total_rating_count"])
    return out


def times(rows):
    """Spielzeit je IGDB-Spiel in Stunden: normal, sonst eilig; dazu komplett und die Zahl der Angaben."""
    out = {}
    for t in rows or []:
        if not isinstance(t, dict) or not t.get("game_id"):
            continue
        h = lambda k: round(t[k] / 3600, 1) if isinstance(t.get(k), (int, float)) and t[k] > 0 else None
        main = h("normally") or h("hastily")
        if main:
            out[int(t["game_id"])] = {"h": main, "all": h("completely"), "n": int(t.get("count") or 0)}
    return out


def mp_kinds(ig):
    """Mehrspieler-Arten (wie collection.MP_LABEL) aus Spielmodi und Mehrspieler-Angaben."""
    modes = {m.casefold() for m in ig.get("modes") or []}
    out = []
    if ig.get("on", 0) > 1 or ig.get("coop_on"):
        out.append("online")
    if "co-operative" in modes or ig.get("coop_on") or ig.get("coop_off"):
        out.append("coop")
    if ig.get("off", 0) > 1 or ig.get("coop_off") or ig.get("split"):
        out.append("couch")
    if ig.get("split"):
        out.append("split")
    if ig.get("lan"):
        out.append("lan")
    if "massively multiplayer online (mmo)" in modes:
        out.append("mmo")
    if out or "multiplayer" in modes or "battle royale" in modes:
        out.insert(0, "multi")
    return out
