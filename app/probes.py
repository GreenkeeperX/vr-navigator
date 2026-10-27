"""Proben für neue Quellen (0.7, Konzept „Datenbasis je Plattform“): Was liefern IGDB, die Steam-Details,
PCGamingWiki, DekuDeals, die libretro-metadat, HowLongToBeat und die UEVR-Profile zu je einem Spiel
deiner Sammlung? Nur im Verbindungstest, nichts wird gespeichert. Erst nach den Ergebnissen wird
entschieden, welche Quelle welches Feld liefert (wie im eShopKompass).

Jede Probe bekommt `probe(name, url, info, headers=None, shown=None, data=None)` aus sync.diagnose:
die Funktion fragt einmal an, beachtet Pausen und Sperren und schreibt eine Zeile ins Ergebnis."""
import html
import json
import re
import urllib.parse

from . import sources

STEAM = "https://store.steampowered.com"
PCGW = "https://www.pcgamingwiki.com/w/api.php"
DEKU = "https://www.dekudeals.com"
HLTB = "https://howlongtobeat.com/"
UEVR = "https://uevr-profiles.com/"
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
    ret = [g for g in games if g.get("src") == "retro"]
    return {"pc": pc[0] if pc else {"name": "Portal 2", "id": "620"},
            "console": con[0] if con else None, "retro": ret[0] if ret else None}


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


def pcgw_fields_info(text):
    d = json.loads(text).get("cargofields") or {}
    return f"{len(d)} Felder: " + ", ".join(sorted(d))[:600] if d else f"keine Felder. Anfang: {' '.join(text[:160].split())}"


def pcgw_rows(text):
    return [r.get("title") or {} for r in json.loads(text).get("cargoquery") or []]


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


def metadat_info(name):
    """Eine metadat-Datei (genre, maxusers, releaseyear) der libretro-database: Zahl der Einträge, und
    was sie zum Spiel der Sammlung sagt."""
    want = re.sub(r"[^a-z0-9]+", " ", (name or "").casefold()).strip()

    def info(text):
        entries = re.findall(r'(?s)game \(\s*(.*?)\n\)', text)
        hit = ""
        for e in entries:
            m = re.search(r'(?:comment|name) "([^"]+)"', e)
            n = re.sub(r"\(.*?\)|\[.*?\]", "", m.group(1) if m else "")
            if want and re.sub(r"[^a-z0-9]+", " ", n.casefold()).strip() == want:
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
    for label, n in names:
        games, err = ask("games", f'search {json.dumps(n, ensure_ascii=False)}; {IGDB_FIELDS}')
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

    # PCGamingWiki (Cargo, offen): welche VR-Felder gibt es, und was steht beim Spiel (auch VR per Mod)?
    vrf = []

    def fields_info(t):
        vrf.extend(sorted(json.loads(t).get("cargofields") or {}))
        return pcgw_fields_info(t)
    probe("PCGamingWiki, VR-Felder", PCGW + "?" + urllib.parse.urlencode(
        {"action": "cargofields", "table": "VR_support", "format": "json"}), fields_info)
    page = {}

    def game_info(text):
        rows = pcgw_rows(text)
        if rows:
            page.update(rows[0])
        return (f"{len(rows)} Treffer für App {appid}" + (f": „{rows[0].get('page')}“, Entwickler {rows[0].get('Developers') or '?'}, "
                f"Verlag {rows[0].get('Publishers') or '?'}, Genres {rows[0].get('Genres') or '?'}" if rows else ""))
    probe("PCGamingWiki, Spiel", PCGW + "?" + urllib.parse.urlencode({
        "action": "cargoquery", "tables": "Infobox_game", "format": "json", "limit": 1,
        "fields": "Infobox_game._pageName=page,Infobox_game._pageID=id,Infobox_game.Developers,Infobox_game.Publishers,Infobox_game.Genres",
        "where": f'Infobox_game.Steam_AppID HOLDS "{appid}"'}), game_info)
    if page.get("id") and vrf:
        # Felder aus der Probe davor, so passt die Abfrage auch nach einer Änderung des Wikis
        probe("PCGamingWiki, VR des Spiels", PCGW + "?" + urllib.parse.urlencode({
            "action": "cargoquery", "tables": "VR_support", "format": "json", "limit": 1,
            "fields": ",".join(f"VR_support.{f}" for f in vrf[:40] if re.fullmatch(r"\w+", f)),
            "where": f'VR_support._pageID = {int(page["id"])}'}),
            lambda t: "; ".join(f"{k} {v}" for k, v in (pcgw_rows(t) or [{}])[0].items()) or "keine VR-Zeile")

    # UEVR-Profile: Unreal-Spiele, die per Mod in VR laufen
    probe("UEVR-Profile", UEVR, uevr_info)

    # DekuDeals: Wertung, Spielzeit (HowLongToBeat) und Beschreibung für Konsolenspiele
    if con:
        slug = {}

        def search_info(t):
            slug["s"] = deku_search_slug(t)
            return f"erster Treffer „{slug['s'] or 'keiner'}“"
        probe("DekuDeals, Suche", f"{DEKU}/search?" + urllib.parse.urlencode({"q": con["name"]}), search_info)
        if slug.get("s"):
            probe("DekuDeals, Spiel", f"{DEKU}/items/{slug['s']}", deku_item_info)
    else:
        lines.append("DekuDeals: kein Konsolenspiel in der Sammlung, nicht angefragt")

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

    names = [("PC", pc["name"])] + ([("Konsole", con["name"])] if con else []) + ([("Retro", ret["name"])] if ret else [])
    igdb(lines, keys, names, sleep)
