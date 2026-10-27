"""Proben für neue Quellen (0.7, Konzept „Datenbasis je Plattform“): Was liefern IGDB, die Steam-Details,
PCGamingWiki, DekuDeals, die libretro-metadat und HowLongToBeat zu je einem Spiel deiner Sammlung?
(Die UEVR-Profile sind seit 0.7.2 nicht mehr dabei: eine Browser-App ohne offene Schnittstelle.) Nur im Verbindungstest, nichts wird gespeichert. Erst nach den Ergebnissen wird
entschieden, welche Quelle welches Feld liefert (wie im eShopKompass).

Jede Probe bekommt `probe(name, url, info, headers=None, shown=None, data=None)` aus sync.diagnose:
die Funktion fragt einmal an, beachtet Pausen und Sperren und schreibt eine Zeile ins Ergebnis."""
import html
import json
import re
import unicodedata
import urllib.parse

from . import sources

STEAM = "https://store.steampowered.com"
PCGW = "https://www.pcgamingwiki.com/w/api.php"
DEKU = "https://www.dekudeals.com"
HLTB = "https://howlongtobeat.com/"
PCGW_APPID = "https://www.pcgamingwiki.com/api/appid.php"
IGDB = "https://api.igdb.com/v4/"
TWITCH = "https://id.twitch.tv/oauth2/token"
LIBRETRO_META = "https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/"

IGDB_FIELDS = ("fields name,first_release_date,genres.name,game_modes.name,platforms.name,aggregated_rating,"
               "aggregated_rating_count,total_rating,total_rating_count,summary,involved_companies.company.name,"
               "involved_companies.developer,involved_companies.publisher,multiplayer_modes.onlinemax,"
               "multiplayer_modes.offlinemax,multiplayer_modes.onlinecoop,multiplayer_modes.offlinecoop,"
               "multiplayer_modes.splitscreen; limit 2;")


def _short(text, n=120):
    """Sichtbarer Text ohne Auszeichnung, gekürzt (für Beschreibungen)."""
    t = " ".join(html.unescape(re.sub(r"<[^>]+>", " ", str(text or ""))).split())
    return t if len(t) <= n else t[:n].rstrip() + " …"


def _hours(sec):
    return f"{sec / 3600:.1f} h".replace(".", ",") if isinstance(sec, (int, float)) and sec > 0 else "–"


def samples(col):
    """Je ein Spiel aus der Sammlung: PC mit Steam-ID (das bekannteste), Konsole, Retro. Ohne Sammlung
    erfundene Vorgaben, damit die Probe trotzdem etwas zeigt."""
    games = list((col.get("games") or {}).values())
    pc = [g for g in games if (g.get("system") or "PC") == "PC" and g.get("store") == "Steam"
          and str(g.get("id") or "").isdigit()]
    pc.sort(key=lambda g: -((g.get("rev") or {}).get("n") or 0))
    con = [g for g in games if (g.get("system") or "PC") not in ("PC", "VR") and g.get("src") != "retro"]
    # Retro: ein Spiel aus No-Intro oder Redump (mit Region, ohne Homebrew und Hack), am liebsten eines,
    # dessen Fassung schon gefunden wurde (0.7.1: ein ROM-Hack fand naturgemäß nichts)
    ret = [g for g in games if g.get("src") == "retro" and g.get("regions") and not g.get("flags")]
    ret.sort(key=lambda g: (not g.get("de"), g.get("name") or ""))
    # DekuDeals kennt nur Switch, PlayStation 4 und 5 und Xbox (0.7.2: eine PS1-Suche fand naturgemäß nichts)
    deku = [g for g in con if g.get("system") in DEKU_SYSTEMS]
    return {"pc": pc[0] if pc else {"name": "Portal 2", "id": "620"},
            "console": con[0] if con else {"name": "Celeste", "system": "Vorgabe"}, "retro": ret[0] if ret else None,
            "deku": deku[0] if deku else None}


DEKU_SYSTEMS = {"Switch", "Switch 2", "PS4", "PS5", "Xbox One", "Xbox Series"}
# Plattform-Kennungen von IGDB je System der Sammlung, damit die Namenssuche das richtige Spiel trifft
IGDB_PLATFORMS = {"PC": 6, "PS1": 7, "PS2": 8, "PS3": 9, "PS4": 48, "PS5": 167, "PSP": 38, "PS Vita": 46,
                  "Xbox": 11, "Xbox 360": 12, "Xbox One": 49, "Xbox Series": 169, "Switch": 130, "Wii U": 41,
                  "Wii": 5, "GameCube": 21, "N64": 4, "SNES": 19, "NES": 18, "3DS": 37, "DS": 20, "GBA": 24,
                  "GBC": 22, "GB": 33, "VB": 87, "Mega Drive": 29, "Master System": 64, "Game Gear": 35,
                  "Saturn": 32, "Dreamcast": 23}


def search_name(n):
    """Name für eine Suche: ohne Klammern, Artikel vorn, Sonderzeichen als Grundbuchstabe
    („Pokémon“ wie „Pokemon“)."""
    n = re.sub(r"\(.*?\)|\[.*?\]", "", n or "").strip()
    m = re.match(r"(.+), (The|A|An|Der|Die|Das|Le|La|Les)$", n)
    n = f"{m.group(2)} {m.group(1)}" if m else n
    return " ".join("".join(c for c in unicodedata.normalize("NFKD", n) if not unicodedata.combining(c)).split())


def steam_details_info(appid):
    """appdetails (deutsch): Kurzbeschreibung, Metacritic, Genres, VR-Kategorien, Erscheinen, Entwickler."""
    def info(text):
        d = (json.loads(text).get(str(appid)) or {})
        if not d.get("success"):
            return f"App {appid}: unbekannt"
        g = d.get("data") or {}
        cats = [c.get("description") for c in g.get("categories") or []]
        vr = [c for c in cats if c and "VR" in c]
        mc = (g.get("metacritic") or {}).get("score")
        return (f"App {appid} „{_short(g.get('name'), 40)}“: Metacritic {mc if mc is not None else 'keins'}; "
                f"Genres {[x.get('description') for x in g.get('genres') or []]}; VR {vr or 'nein'}; "
                f"erschienen {(g.get('release_date') or {}).get('date') or '?'}; Entwickler {g.get('developers') or '?'}; "
                f"Verlag {g.get('publishers') or '?'}; Deutsch {'ja' if 'Deutsch' in str(g.get('supported_languages')) else 'nein'}; "
                f"Beschreibung {len(_short(g.get('short_description'), 10000))} Zeichen: „{_short(g.get('short_description'))}“")
    return info


def pcgw_title(text):
    """Seitenname aus der Wiki-Seite, auf die appid.php umleitet."""
    m = re.search(r'"wgPageName":"([^"]+)"', text) or re.search(r"(?s)<title>(.*?)(?: - PCGamingWiki[^<]*)?</title>", text)
    return html.unescape(m.group(1)).replace("_", " ").strip() if m else ""


def pcgw_vr(text):
    """Felder der Vorlage „VR support“ aus dem Wikitext einer Seite (action=parse). Die Cargo-Abfrage
    ist seit 2026 nur angemeldet erlaubt (0.7.1: permissiondenied), die Vorlage steht im Text."""
    wt = ((json.loads(text).get("parse") or {}).get("wikitext") or {}).get("*") or ""
    m = re.search(r"(?is)\{\{\s*VR support\s*(.*?)\n\}\}", wt)
    out = {}
    for k, v in re.findall(r"(?m)^\|\s*([\w ]+?)\s*=\s*(.*?)\s*$", m.group(1) if m else ""):
        if v and not k.endswith("notes"):
            out[k] = v[:40]
    return out


def deku_item_info(text):
    """Kasten „Details“ einer DekuDeals-Artikelseite: Bezeichnung und Wert, dazu die Beschreibung."""
    vis = " ".join(html.unescape(re.sub(r"(?s)<script.*?</script>|<style.*?</style>|<[^>]+>", " ", text)).split())
    labels = ("Release date", "Genres?", "Number of players", "Developers?", "Publishers?", "Metacritic",
              "OpenCritic", "How Long To Beat", "Platforms?", "Play modes")
    rx = re.compile(r"(?<![\w-])(" + "|".join(labels) + r")\s*:")
    hits = list(rx.finditer(vis))
    vals = {m.group(1): vis[m.end():hits[i + 1].start() if i + 1 < len(hits) else m.end() + 80].strip()[:80]
            for i, m in enumerate(hits)}
    desc = re.search(r'<meta[^>]+(?:property|name)="(?:og:)?description"[^>]+content="([^"]*)"', text)
    return ("; ".join(f"{k}: {v}" for k, v in vals.items()) or "keine Angaben im Kasten Details") + (
        f"; Beschreibung „{_short(desc.group(1))}“" if desc else "; keine Beschreibung")


def uevr_info(text):
    title = re.search(r"(?s)<title>(.*?)</title>", text)
    links = set(re.findall(r'href="(/games?/[^"#?]+)', text))
    api = sorted(set(re.findall(r"/api/[A-Za-z0-9/_-]+", text)))[:5]
    return (f"Titel „{_short(title.group(1) if title else '', 60)}“, {len(links)} Spiel-Links, "
            f"Hinweise auf eine Schnittstelle: {api or 'keine'}")


def deku_search_slug(text):
    m = re.search(r'href="/items/([a-z0-9-]+)"', text)
    return m.group(1) if m else ""


def _plain(n):
    """Name zum Vergleichen: ohne Klammern, „Legend of Pixels, The“ wie „The Legend of Pixels“."""
    n = re.sub(r"\(.*?\)|\[.*?\]", "", n or "").strip()
    m = re.match(r"(.+), (The|A|An|Der|Die|Das|Le|La|Les)$", n)
    n = f"{m.group(2)} {m.group(1)}" if m else n
    return re.sub(r"[^a-z0-9]+", " ", n.casefold()).strip()


def metadat_info(name):
    """Eine metadat-Datei (genre, maxusers, releaseyear) der libretro-database: Zahl der Einträge, und
    was sie zum Spiel der Sammlung sagt."""
    want = _plain(name)

    def info(text):
        entries = re.findall(r'(?s)game \(\s*(.*?)\n\)', text)
        hit = ""
        for e in entries:
            m = re.search(r'(?:comment|name) "([^"]+)"', e)
            if want and _plain(m.group(1) if m else "") == want:
                hit = " ".join(x for x in e.split() if x)[:160]
                break
        return f"{len(entries)} Einträge" + (f"; zu „{name[:40]}“: {hit}" if hit else f"; „{(name or '')[:40]}“ nicht gefunden" if name else "")
    return info


def igdb(lines, keys, names, sleep):
    """IGDB mit Twitch-Schlüssel: Treffer je Name mit Genre, Spielmodi, Wertung, Beschreibung, Firmen;
    zum ersten Treffer die Spielzeit (game_time_to_beats). Der Schlüssel steht nie in der Ausgabe."""
    cid, secret = keys.get("igdb_id", ""), keys.get("igdb_secret", "")
    if not (cid and secret):
        lines.append("IGDB: kein Schlüssel eingetragen (Einstellungen, Konten und Schlüssel), nicht angefragt")
        return
    r = sources.request(TWITCH, data=urllib.parse.urlencode(
        {"client_id": cid, "client_secret": secret, "grant_type": "client_credentials"}).encode())
    try:
        token = json.loads(r["text"] or "{}").get("access_token") if not r["error"] else None
    except ValueError:
        token = None
    if not token:
        lines.append(f"IGDB: kein Zugang (Twitch HTTP {r['status']}{', ' + r['error'] if r['error'] else ''})")
        return
    head = {"Client-ID": cid, "Authorization": f"Bearer {token}", "Accept": "application/json"}

    def ask(path, body):
        sleep(1)
        r = sources.request(IGDB + path, data=body.encode(), headers=head)
        if r["error"] or r["status"] != 200:
            return None, f"HTTP {r['status']} {r['error']} {' '.join(r['text'][:120].split())}".strip()
        try:
            return json.loads(r["text"] or "[]"), ""
        except ValueError:
            return None, "Antwort nicht lesbar"
    for label, n, *rest in names:
        games, err = None, ""
        if rest and rest[0]:
            # PC (0.7.1): über die Steam-ID statt den Namen („… Legacy“ fand die Suche nicht)
            ext, err = ask("external_games", f'fields game,uid; where uid = "{rest[0]}" & external_game_source = 1; limit 1;')
            if not ext:
                ext, err = ask("external_games", f'fields game,uid; where uid = "{rest[0]}" & category = 1; limit 1;')
            gid = (ext or [{}])[0].get("game")
            if gid:
                games, err = ask("games", f"{IGDB_FIELDS.replace('limit 2;', '')} where id = {int(gid)};")
                label += " über Steam-ID"
        # Name (0.7.2): erst wie geschrieben mit Plattform, dann ohne Sonderzeichen, zuletzt ohne Plattform
        plat = IGDB_PLATFORMS.get(rest[1]) if len(rest) > 1 else None
        tries = [(n, plat), (search_name(n), plat)] + ([(search_name(n), None)] if plat else [])
        for q, pl in dict.fromkeys(tries):
            if games:
                break
            games, err = ask("games", f'search {json.dumps(q, ensure_ascii=False)}; '
                             + IGDB_FIELDS.replace("limit 2;", f"where platforms = ({pl}); limit 2;" if pl else "limit 2;"))
            if games and (q, pl) != tries[0]:
                label += f" (gesucht als „{q[:40]}“{'' if pl else ', ohne Plattform'})"
        if games is None:
            lines.append(f"IGDB, {label} „{n[:40]}“: {err}")
            if "403" in err or "429" in err:
                return
            continue
        if not games:
            lines.append(f"IGDB, {label} „{n[:40]}“: keine Treffer")
            continue
        g = games[0]
        comp = g.get("involved_companies") or []
        dev = [c["company"]["name"] for c in comp if c.get("developer") and isinstance(c.get("company"), dict)]
        pub = [c["company"]["name"] for c in comp if c.get("publisher") and isinstance(c.get("company"), dict)]
        mp = [{k: v for k, v in m.items() if k != "id"} for m in g.get("multiplayer_modes") or []]
        tt, err = ask("game_time_to_beats", f"fields hastily,normally,completely,count; where game_id = {int(g.get('id') or 0)};")
        t = (tt or [{}])[0] if tt else {}
        lines.append(
            f"IGDB, {label} „{n[:40]}“: {len(games)} Treffer, erster „{_short(g.get('name'), 50)}“; "
            f"Genres {[x.get('name') for x in g.get('genres') or []]}; Modi {[x.get('name') for x in g.get('game_modes') or []]}; "
            f"Mehrspieler {str(mp)[:160]}; Plattformen {[x.get('name') for x in g.get('platforms') or []][:6]}; "
            f"Wertung Kritik {round(g['aggregated_rating']) if g.get('aggregated_rating') else '–'} ({g.get('aggregated_rating_count') or 0}), "
            f"gesamt {round(g['total_rating']) if g.get('total_rating') else '–'} ({g.get('total_rating_count') or 0}); "
            f"Entwickler {dev or '?'}; Verlag {pub or '?'}; "
            + (f"Spielzeit eilig {_hours(t.get('hastily'))}, normal {_hours(t.get('normally'))}, komplett {_hours(t.get('completely'))} "
               f"({t.get('count') or 0} Angaben)" if t else f"Spielzeit {'keine' if tt is not None else err}")
            + f"; Beschreibung „{_short(g.get('summary'))}“")


def run(probe, lines, col, keys, sleep):
    """Alle Proben nacheinander. probe: siehe oben; keys: igdb_id, igdb_secret."""
    s = samples(col)
    pc, con, ret = s["pc"], s["console"], s["retro"]
    appid = str(pc.get("id"))
    lines.append(f"Neue Quellen (Probe, nichts gespeichert): PC „{pc['name'][:40]}“, Konsole "
                 + (f"„{con['name'][:40]}“ ({con.get('system')})" if con else "keins in der Sammlung")
                 + ", Retro " + (f"„{ret['name'][:40]}“ ({ret.get('system')})" if ret else "keins in der Sammlung"))
    probe("Steam, Details", f"{STEAM}/api/appdetails?appids={appid}&cc=de&l=german", steam_details_info(appid))

    # PCGamingWiki (0.7.2): Cargo ist gesperrt, also Seite über die Steam-ID (appid.php leitet um), dann der
    # Wikitext mit der Vorlage „VR support“ (auch VR per Mod: vorpX, UEVR …)
    title = {}

    def page_info(t):
        title["t"] = pcgw_title(t)
        return f"Seite „{title['t']}“" if title["t"] else f"keine Seite für App {appid}"
    probe("PCGamingWiki, Seite", PCGW_APPID + "?" + urllib.parse.urlencode({"appid": appid}), page_info)
    if title.get("t"):
        probe("PCGamingWiki, VR", PCGW + "?" + urllib.parse.urlencode(
            {"action": "parse", "page": title["t"], "prop": "wikitext", "format": "json", "redirects": 1}),
            lambda t: "; ".join(f"{k} {v}" for k, v in pcgw_vr(t).items()) or "keine Angaben zu VR")

    # DekuDeals: Wertung, Spielzeit (HowLongToBeat) und Beschreibung für Konsolenspiele (ohne Konsolenspiel
    # in der Sammlung mit einer Vorgabe)
    deku = s["deku"]
    if deku:
        slug = {}

        def search_info(t):
            slug["s"] = deku_search_slug(t)
            return f"erster Treffer „{slug['s'] or 'keiner'}“"
        probe(f"DekuDeals, Suche ({deku.get('system')})", f"{DEKU}/search?" + urllib.parse.urlencode({"q": search_name(deku["name"])}), search_info)
        if slug.get("s"):
            probe("DekuDeals, Spiel", f"{DEKU}/items/{slug['s']}", deku_item_info)
    else:
        lines.append("DekuDeals: kein Spiel für Switch, PS4, PS5 oder Xbox in der Sammlung, nicht angefragt")

    # HowLongToBeat direkt: nur erreichbar oder nicht (die Suche hat keine offene Schnittstelle)
    probe("HowLongToBeat", HLTB, lambda t: f"erreichbar, {'Seite mit Suche' if 'search' in t.casefold() else 'ohne Suchfeld'}")

    # libretro-database, metadat: Genre, Spielerzahl, Jahr für Retro-Spiele
    if ret:
        from . import retro
        kind, dat = retro.DATS.get(ret.get("system"), (None, None))
        if dat:
            for k in ("genre", "maxusers", "releaseyear", "developer"):
                probe(f"libretro {k} ({ret.get('system')})", LIBRETRO_META + k + "/" + urllib.parse.quote(dat) + ".dat",
                      metadat_info(ret["name"]))
        else:
            lines.append(f"libretro metadat: keine Liste für {ret.get('system')}")
    else:
        lines.append("libretro metadat: keine Retro-Liste, nicht angefragt")

    names = [("PC", pc["name"], appid), ("Konsole", con["name"], None, con.get("system"))] + (
        [("Retro", ret["name"], None, ret.get("system"))] if ret else [])
    igdb(lines, keys, names, sleep)
