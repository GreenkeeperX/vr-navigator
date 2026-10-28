"""Konten: Besitz und Wunschliste bei Steam, Wunschliste bei gg.deals.

Hier steht nur das Lesen der Antworten und das Eintragen in data.json, ohne Netz; die Abrufe
macht sync.py (siehe docs/abrufe.md).

- Steam Web API: GetOwnedGames (mit Schlüssel) liefert App-ID und Name jedes gekauften Spiels,
  GetWishlist (ohne Schlüssel) nur App-IDs. Ob eine App VR kann, steht in den Kategorien der
  Store-Seite (appdetails); das Ergebnis merkt sich data["steam_apps"], damit jede App nur
  einmal gefragt wird.
- gg.deals: die geteilte Wunschliste (Link „Teilen“), eine Seite mit Links auf /game/<name>/.
"""
import html
import json
import re
from datetime import datetime, timezone

from . import collection, titles

# Kategorien im Steam-Store: VR Support, VR Supported, VR Only
VR_CATEGORIES = {31, 53, 54}
_STEAMID = re.compile(r"^7656\d{13}$")


def steam_id_input(s):
    """SteamID aus dem Feld der Einstellungen: die Zahl, ein Profil-Link mit Zahl oder ein Link
    mit eigenem Namen (/id/<Name>/). Liefert ("id", Zahl), ("vanity", Name) oder ("", "")."""
    s = str(s or "").strip()
    if _STEAMID.match(s):
        return "id", s
    m = re.search(r"steamcommunity\.com/profiles/(7656\d{13})", s)
    if m:
        return "id", m.group(1)
    m = re.search(r"steamcommunity\.com/id/([A-Za-z0-9_-]{2,64})", s)
    if m:
        return "vanity", m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{2,64}", s):
        return "vanity", s
    return "", ""


def _json(text, what):
    try:
        d = json.loads(text)
    except ValueError:
        raise ValueError(f"{what}: keine JSON-Antwort")
    if not isinstance(d, dict):
        raise ValueError(f"{what}: unerwartete Antwort")
    return d


def steam_vanity(text):
    r = _json(text, "Steam, Profilname").get("response") or {}
    return str(r.get("steamid") or "") if r.get("success") == 1 else ""


def steam_owned(text):
    """GetOwnedGames: [{appid, name, min, last}]. Ab 0.9.3 mit der Spielzeit in Minuten (min) und dem Tag,
    an dem du zuletzt gespielt hast (last, leer: nie oder unbekannt). Ein leeres response heißt meist:
    Spieldetails im Profil nicht öffentlich."""
    r = _json(text, "Steam, Besitz").get("response")
    if not isinstance(r, dict) or "games" not in r:
        raise ValueError("Steam, Besitz: keine Spiele in der Antwort (sind die Spieldetails im Profil öffentlich?)")
    out = []
    for g in r["games"]:
        if not isinstance(g, dict) or not g.get("appid"):
            continue
        m, t = g.get("playtime_forever"), g.get("rtime_last_played")
        last = datetime.fromtimestamp(t, timezone.utc).date().isoformat() if isinstance(t, int) and t > 0 else ""
        out.append({"appid": str(g["appid"]), "name": str(g.get("name") or ""),
                    "min": m if isinstance(m, int) and m >= 0 else None, "last": last})
    return out


def steam_play(owned):
    """Spielzeit je Steam-App aus steam_owned, für data.json: {App-ID: [Minuten, zuletzt gespielt]}. Ohne
    Minuten (Steam nennt sie nicht) fällt die App weg."""
    return {g["appid"]: [g["min"], g["last"]] for g in owned if g.get("min") is not None}


def steam_wishlist(text):
    """GetWishlist: App-IDs in der Reihenfolge deiner Wunschliste."""
    r = _json(text, "Steam, Wunschliste").get("response")
    if not isinstance(r, dict):
        raise ValueError("Steam, Wunschliste: unerwartete Antwort")
    return [str(i["appid"]) for i in r.get("items") or [] if isinstance(i, dict) and i.get("appid")]


def steam_app(text, appid):
    """appdetails ohne Filter: Name, Art und ob die App VR kann. None, wenn Steam die App nicht
    (mehr) zeigt."""
    d = _json(text, "Steam, App").get(str(appid)) or {}
    if not d.get("success") or not isinstance(d.get("data"), dict):
        return None
    a = d["data"]
    cats = {c.get("id") for c in a.get("categories") or [] if isinstance(c, dict)}
    return {"name": str(a.get("name") or ""), "type": str(a.get("type") or ""), "vr": bool(cats & VR_CATEGORIES)}


_GG_GAME = re.compile(r'<a\b[^>]*href="(?:https://gg\.deals)?/(?:[a-z]{2}/)?game/([a-z0-9-]+)/?"[^>]*>(.*?)</a>', re.I | re.S)
_GG_PAGE = re.compile(r'[?&]page=(\d+)')


def gg_wishlist(text):
    """Geteilte Wunschliste von gg.deals: [{slug, name}] und die Zahl der Seiten. Ein Spiel hat
    oft mehrere Links (Bild und Titel); es zählt der mit Text."""
    items = {}
    for slug, inner in _GG_GAME.findall(text or ""):
        name = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", inner)).split())
        if slug not in items or (name and not items[slug]):
            items[slug] = name[:200]
    pages = max([int(x) for x in _GG_PAGE.findall(text or "")] or [1])
    return [{"slug": s, "name": n or s.replace("-", " ")} for s, n in items.items()], pages


# ------------------------------------------------------------------ Eintragen

def apply_steam(data, owned, wished, apps, stamp=None):
    """Steam-Besitz und -Wunschliste eintragen. owned: [{appid, name}] oder None (nicht
    gelesen), wished: [appid] oder None, apps: data["steam_apps"] (Name und VR je App-ID).
    Gezählt wird nur, was zu einem Titel passt oder laut Steam VR kann; der Rest bleibt außen vor.
    Liefert eine Übersicht fürs Protokoll."""
    stamp = stamp or titles.now_iso()
    out = {"owned": 0, "owned_new": [], "wish_keys": [], "wish_new": [], "unchecked": 0}
    by_id = {t.get("steam_appid"): k for k, t in data["titles"].items() if t.get("steam_appid")}

    def place(appid, name):
        """Schlüssel des passenden Titels; legt ihn an, wenn die App VR kann. None: kein VR
        oder noch nicht geprüft."""
        if appid in by_id:
            k = by_id[appid]
        else:
            info = apps.get(appid) or {}
            name = name or info.get("name") or ""
            k = titles.find(data, "", appid, name) if name else None
            if k is None:
                if appid not in apps:
                    out["unchecked"] += 1
                    return None, False
                if not info.get("vr"):
                    return None, False
                k, _ = titles.upsert(data, name, "", appid)
                by_id[appid] = k
                t = data["titles"][k]
                t["steam_appid"], t["steam_sure"] = appid, True
                return k, True
            t = data["titles"][k]
            if t.get("steam_appid") and t["steam_appid"] != appid:
                return None, False         # derselbe Name, andere App: nicht raten
            t["steam_appid"] = appid
            by_id[appid] = k
        data["titles"][k]["steam_sure"] = True
        return k, False

    for g in owned or []:
        k, new = place(g["appid"], g["name"])
        if k is None:
            continue
        t = data["titles"][k]
        titles.note_origin(t, "steam")
        if not (t.get("owned") or {}).get("pc"):
            t.setdefault("owned", {})["pc"] = {"src": "steam", "label": "Steam", "at": stamp}
            if new:
                out["owned_new"].append(t["name"])
        out["owned"] += 1
    if wished is not None:
        for appid in wished:
            k, new = place(appid, "")
            if k is not None:
                out["wish_keys"].append(k)
                if new:
                    out["wish_new"].append(data["titles"][k]["name"])
        out["wish_added"], out["wish_removed"] = titles.set_wishes(data, "steam", out["wish_keys"], stamp)
    return out


def gg_match(data, items):
    """Zu jedem Spiel einer gg.deals-Wunschliste der Schlüssel des Titels im Tool oder None:
    Name, früherer Name, Name aus einem Link oder der Name aus der gg.deals-Adresse."""
    names = {}
    for k, t in data["titles"].items():
        for x in titles.store_names(t) + list(t.get("aliases") or []):
            names.setdefault(titles.base_norm(x), k)
    return [titles.find(data, "", "", it["name"]) or names.get(titles.base_norm(it["name"]))
            or names.get(titles.base_norm((it.get("slug") or "").replace("-", " "))) for it in items]


def apply_gg_wishes(data, items, stamp=None):
    """Wunschliste von gg.deals eintragen. Ohne Steam-ID lässt sich nicht prüfen, ob ein Spiel VR
    kann; deshalb zählen nur Titel, die das Tool schon kennt (Name, früherer Name oder Name
    aus einem Link). Die übrigen nennt das Protokoll."""
    keys, unknown = [], []
    for it, k in zip(items, gg_match(data, items)):
        if k:
            keys.append(k)
        else:
            unknown.append(it["name"])
    added, removed = titles.set_wishes(data, "gg", keys, stamp)
    return {"keys": keys, "unknown": unknown, "wish_added": added, "wish_removed": removed}


# ------------------------------------------------------------------ Sharenite (Playnite online)

_SN_ROW = re.compile(r'<tr\b[^>]*\bid="game_[^"]*"[^>]*>(.*?)</tr>', re.I | re.S)
_SN_NAME = re.compile(r"<strong[^>]*>(.*?)</strong>", re.I | re.S)
_SN_PILL = re.compile(r'class="games-value-pill games-value-pill--(source|tag|category|platform)(?![^"]*--muted)[^"]*"[^>]*>([^<]+)<', re.I)
_SN_OPTION = re.compile(r'<option\b[^>]*value="([^"]+)"[^>]*>([^<]+)</option>', re.I)
_SN_TOTAL = re.compile(r"Total games listed:\s*([\d.,]+)", re.I)
_VR = re.compile(r"\bvr\b|virtual reality", re.I)


def _txt(s):
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", s)).split())


def sharenite_page(text):
    """Eine Seite der Spieleliste eines Sharenite-Profils: [{name, source, tags, vr}], dazu die
    Gesamtzahl der Spiele (oder None) und die Kennungen der Schlagwörter mit „VR“ im Namen aus
    dem Suchformular (damit sich die Liste auf VR-Spiele filtern lässt)."""
    games = []
    for row in _SN_ROW.findall(text or ""):
        m = _SN_NAME.search(row)
        name = _txt(m.group(1)) if m else ""
        if not name:
            continue
        pills = {}
        for kind, val in _SN_PILL.findall(row):
            pills.setdefault(kind.lower(), [])
            v = _txt(val)
            if v and v not in pills[kind.lower()]:
                pills[kind.lower()].append(v)
        tags = pills.get("tag", []) + pills.get("category", [])
        source = (pills.get("source") or [""])[0]
        games.append({"name": name[:200], "source": source, "platforms": pills.get("platform", []),
                      "tags": tags, "vr": any(_VR.search(x) for x in tags),
                      "console": collection.console_only(pills.get("platform", []), source)})
    m = _SN_TOTAL.search(text or "")
    total = int(re.sub(r"\D", "", m.group(1))) if m else None
    vr_tags = [v for v, label in _SN_OPTION.findall(text or "") if _VR.search(_txt(label)) and v != "__none__"]
    return games, total, vr_tags


def apply_sharenite(data, games, stamp=None):
    """VR-Spiele aus Sharenite als Besitz am PC eintragen, mit dem Laden als Marke (Steam, GOG,
    Epic …). Wie beim Playnite-Import zählen Spiele mit VR-Schlagwort und alle, deren Name das
    Tool schon kennt. Liefert (bekannt, neu als Namen)."""
    stamp = stamp or titles.now_iso()
    known, new = 0, []
    for g in games:
        k = titles.find(data, "", "", g["name"])
        if g.get("console"):
            # Nur für Konsole (etwa PS4): kein Besitz am PC. Ein früher so eingetragener Besitz
            # fällt weg; hast du das Spiel auch am PC, trägt es der PC-Eintrag wieder ein.
            pc = ((data["titles"].get(k) or {}).get("owned") or {}).get("pc") if k else None
            if pc and pc.get("src") == "sharenite" and collection.store_of(pc.get("label")) == "PlayStation":
                del data["titles"][k]["owned"]["pc"]
            continue
        if k is None and not g["vr"]:
            continue
        if k is None:
            k, _ = titles.upsert(data, g["name"])
            new.append(g["name"])
        else:
            known += 1
        t = data["titles"][k]
        titles.note_origin(t, "sharenite", g["source"])
        pc = (t.get("owned") or {}).get("pc")
        if not pc or pc.get("src") in ("playnite", "sharenite"):
            t.setdefault("owned", {})["pc"] = {"src": "sharenite", "label": g["source"] or "PC", "at": stamp}
    return known, new
