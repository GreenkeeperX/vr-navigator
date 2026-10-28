"""Abgleich: holt Preise für die Wunschtitel von QuestStoreDB, Steam und gg.deals.

Ablauf eines Laufs (Einzelheiten in docs/abrufe.md):
1. QuestStoreDB, Angebotsliste: alle Seiten, neueste Angebote zuerst.
2. QuestStoreDB, Titelseiten der Wunschtitel, die älter als PAGE_AGE_H sind (höchstens
   MAX_PAGES je Lauf). Fehlt der Pfad, sucht das Tool den Titel erst über die Suche.
3. Steam: fehlende App-IDs über die Store-Suche (nur bei gleichem Namen), dann die Preise in
   Paketen zu 50.
4. gg.deals, nur mit Schlüssel: Preise in Paketen zu 100.

Die Abrufe laufen ohne Sperre auf data.json; erst das Ergebnis wird unter der Sperre in die
aktuelle Fassung eingetragen. Zwischen zwei Abrufen derselben Quelle liegt PAUSE. Antwortet
eine Quelle mit 403 oder 429 oder einer Prüfseite, endet sie für diesen Lauf und ruht danach
REST_H Stunden, auch über Läufe hinweg. Nach einem kurzen Netzfehler gibt es einen zweiten
Versuch.

Das Protokoll entsteht live (STATE), die Oberfläche liest es während des Laufs; am Ende landet
es mit dem Ergebnis je Quelle und der Selbstprüfung in sync.json.
"""
import html
import json
import re
import sys
import threading
import time
import urllib.parse
from datetime import datetime, timedelta, timezone

from . import accounts, collection, igdb, itad, lists, mods, pcwish, prices, probes, retro, sources, store, titles, trend, verlauf, wheel

PAUSE = 2.0
PAGE_AGE_H = 20
MAX_SALE_PAGES = 15
MAX_PAGES = 60
MAX_SEARCH = 30
MAX_ERRORS = 5
MISS_DAYS = 7               # nicht gefundene Titel erst nach so vielen Tagen erneut suchen
SEARCH_V = 2                # Stand der Suche; ändert sie sich, gelten alte Fehlschläge nicht mehr
REST_H = 24                 # Ruhezeit einer Quelle nach Sperre oder Prüfseite
NET_RETRY = 5.0             # Pause vor dem zweiten Versuch nach einem Netzfehler
BOOT_GAP_MIN = 30           # Lauf nach dem Start nur, wenn der letzte länger her ist
LOG_LINES = 200
JUMP = 0.5                  # Selbstprüfung: Normalpreis ändert sich um mehr als 50 %
NAMES = {"steamacc": "Steam-Konto", "ggwish": "gg.deals-Wunschliste", "sharenite": "Sharenite", "qsdb": "QuestStoreDB", "steam": "Steam",
         "gg": "gg.deals", "reviews": "Steam-Rezensionen", "details": "Steam-Details",
         "rating": "Steam-Wertungen", "vrdb": "VRDB", "players": "Steam-Spieler", "active": "Aktive Spieler PC", "retro": "Retro-Fassungen",
         "igdb": "IGDB", "pcwish": "PC-Wunschliste", "pcinfo": "PC-Wunschliste, Spielinfos", "vrinfo": "VR-Titel, Spielinfos", "pcgw": "PCGamingWiki", "nexus": "Nexus Mods", "wheel": "Sim-Racing", "eshop": "eShopKompass",
         "itad": "IsThereAnyDeal"}
SHOPS = {"meta": "Meta", "steam": "Steam", "gg": "gg.deals Händler"}
QSDB_HEAD = {"Cookie": "currency=EUR"}     # Preise und Verlauf in Euro
STEAM = "https://store.steampowered.com"
GG_API = "https://api.gg.deals/v1/prices/by-steam-app-id/"
STEAM_API = "https://api.steampowered.com"
APPINFO_MAX = 40            # Store-Seiten je Lauf, um zu prüfen, ob eine App VR kann
ASSIGN_APPS = 25            # Steam-Store-Abfragen je Lauf, um Steam-IDs „≈“ zu prüfen
ASSIGN_SEARCH = 15          # QuestStoreDB-Suchen je Lauf für Titel außerhalb der Preisliste
GG_WISH_PAGES = 10
GG_PENDING = 40             # Namen je Lauf aus der per Lesezeichen gelesenen gg.deals-Wunschliste
GG_RETRY_DAYS = 7           # so lange per Lesezeichen, dann versucht der Server die gg.deals-Wunschliste wieder
SHARENITE_PAGES = 40        # 100 Spiele je Seite; ohne VR-Filter wird die ganze Liste gelesen
SHARENITE_H = 20            # Sharenite höchstens so oft lesen (Stunden)
REVIEWS_MAX = 100           # Steam-Rezensionen je Lauf für Entdecken (Bekanntheit, Geheimtipps)
REVIEWS_DAYS = 30           # so alt darf eine Rezensionszahl werden
DETAILS_MAX = 120           # Steam-Store-Daten je Lauf für Entdecken (Genres, Mehrspieler, Jahr)
DETAILS_DAYS = 90
VRDB = "https://vrdb.app"
VRDB_MAX = 30               # VRDB-Titelseiten je Lauf (Crossbuy, Version, Meta-Wertung)
VRDB_DAYS = 14
PLAYERS_MAX = 80            # Spielerzahlen je Lauf (Steam, ohne Schlüssel)
PLAYERS_H = 20              # so alt darf eine Spielerzahl werden
PEAK_DAYS = 30              # Spitze über so viele Tage
ACTIVE_MAX = 100            # PC (0.8.23): aktive Steam-Spieler je Lauf, erst PC-Wunschliste, dann Sammlung
ACTIVE_DAYS = 7             # so alt darf die Zahl aktiver Spieler eines PC-Spiels werden
NEWS_DAYS = 7               # Steam-Neuigkeiten (letztes Update) so oft neu
TREND_DAYS = 7              # Steam-Trend (Stimmen der letzten 30 Tage) so oft neu (0.8.21)
TREND_MAX = 60              # Trend-Abrufe je Lauf, je für Titel und PC-Wunschliste
SMALL_EUR, SMALL_REL = 0.5, 0.05   # Preisänderung darunter (beides) gilt im Protokoll als Schwankung
BOOT_WAIT_S = 300           # Ruhe nach dem Start (etwa nach einem Update), Entscheidung 22.10.2026
META_DAYS = 30              # Spielinfos der libretro-database (0.8.8) je System höchstens monatlich
RETRO_DAYS = 7              # Fassungslisten (No-Intro, Redump, Retool) je System höchstens wöchentlich
IGDB_DAYS = 90              # IGDB je Spiel so oft neu (0.8.0)
IGDB_MISS_DAYS = 30         # ohne Treffer erst nach so vielen Tagen neu suchen
IGDB_NAMES = 120            # Namenssuchen je Lauf (Steam-Spiele gehen gebündelt über die Steam-ID)
PCGW_MAX = 60               # PCGamingWiki-Seiten je Lauf (VR per Mod, 0.8.1), je zwei Abrufe
PCGW_DAYS = 90
NEXUS_MAX = 60              # Nexus-Mod-Abfragen je Lauf
NEXUS_DAYS = 30
NEXUS_LIST_DAYS = 7         # Spieleliste von Nexus Mods (nexus_games.json) so oft neu
WHEEL_MAX = 400             # Steam-Spiele je Lauf für die Schlagwörter (0.8.3), je Anfrage wheel.BATCH
WHEEL_DAYS = 90
WHEEL_LIST_DAYS = 30        # Liste der Rennsimulationen und Liste der Steam-Schlagwörter so oft neu
PCWISH_SEARCH = 60          # Steam-Suchen je Lauf für Spiele der PC-Wunschliste ohne Steam-ID (0.8.2, ab 0.8.24 60 statt 30)
VRINFO_MAX = 60             # VR-Titel je Lauf mit Steam-Details (0.9.4)
VRINFO_NAMES = 40           # VR-Titel ohne Steam-ID je Lauf mit IGDB-Namenssuche (0.9.4)
PCWISH_INFO = 60            # Spiele der PC-Wunschliste je Lauf mit Steam-Details und Rezensionen (0.8.11)
ITAD_PAUSE = 1.0            # IsThereAnyDeal erlaubt 1000 Abrufe je 5 Minuten; ein Lauf braucht nur wenige
ITAD_HIST = 40              # Spiele je Lauf, deren Verlauf je Laden einmal rückwirkend kommt (0.9.1)
IGDB_PAUSE = 0.3            # IGDB erlaubt 4 Anfragen je Sekunde
# Beschleunigt auffüllen (0.8.6): ein Lauf von Hand mit FAST-fachen Grenzen für die langen Warteschlangen.
# Pausen und der Abbruch bei 403 und 429 bleiben; der Lauf dauert dafür entsprechend länger.
FAST = 5
FAST_LIMITS = ("ACTIVE_MAX", "TREND_MAX", "REVIEWS_MAX", "DETAILS_MAX", "RATING_MAX", "IGDB_NAMES", "PCGW_MAX", "NEXUS_MAX", "WHEEL_MAX", "PCWISH_INFO",
               "PLAYERS_MAX", "VRDB_MAX", "PCWISH_SEARCH", "ITAD_HIST", "VRINFO_MAX", "VRINFO_NAMES")
RATING_MAX = 60             # Steam-Rezensionen je Lauf für Titel auf Wunschliste und in der Bibliothek

SETTINGS = {"gg_key": "", "auto": True, "hours": 6, "steam_key": "", "steam_id": "", "steam_wish": True, "gg_wish": "", "sharenite": "",
            "igdb_id": "", "igdb_secret": "", "nexus_key": "", "itad_key": ""}
SECRETS = ("gg_key", "steam_key", "gg_wish", "igdb_id", "igdb_secret", "nexus_key", "itad_key")      # bleiben auf dem Server, nie im Protokoll

sleep = time.sleep          # Tests setzen hier eine Attrappe ein
_old_misses = {"ignore": False}     # Fehlschläge einer früheren Suche (SEARCH_V) zählen nicht
_running = threading.Lock()
# Stand des laufenden Abgleichs, live für die Oberfläche
STATE = {"started": "", "step": "", "done": 0, "total": 0, "log": []}


def now():
    return datetime.now(timezone.utc)


def load_settings():
    s = dict(SETTINGS)
    s.update({k: v for k, v in store.load_json("settings.json", {}).items() if k in SETTINGS})
    return s


def save_settings(body):
    s = load_settings()
    if "gg_key" in body:
        s["gg_key"] = str(body["gg_key"] or "").strip()[:100]
    if "steam_key" in body:
        k = str(body["steam_key"] or "").strip()
        if k and not re.fullmatch(r"[0-9A-Fa-f]{32}", k):
            raise ValueError("Der Steam-Schlüssel hat 32 Zeichen aus 0–9 und A–F")
        s["steam_key"] = k
    if "steam_id" in body:
        v = str(body["steam_id"] or "").strip()[:200]
        if v and not accounts.steam_id_input(v)[0]:
            raise ValueError("SteamID: die 17-stellige Zahl oder der Link zu deinem Steam-Profil")
        s["steam_id"] = v
    if "steam_wish" in body:
        s["steam_wish"] = bool(body["steam_wish"])
        if not s["steam_wish"]:
            # Wird nicht mehr gepflegt (Entscheidung 22.10.2026): Steam zählt nicht mehr als Quelle
            with store.lock:
                data = store.load_data()
                if titles.drop_wish_source(data, "steam"):
                    store.save_data(data)
    if "gg_wish" in body:
        v = str(body["gg_wish"] or "").strip()[:300]
        if v and not re.match(r"https://gg\.deals/(?:[a-z]{2}/)?wishlist/share/[A-Za-z0-9_-]+/?$", v):
            raise ValueError("gg.deals: den Link aus „Wunschliste teilen“ einfügen (https://gg.deals/wishlist/share/…)")
        s["gg_wish"] = v
        st = store.load_json("sync.json", {})
        if (st.get("manual") or {}).pop("ggwish", None):
            # Neuer Link: der Server versucht es wieder selbst
            store.save_json("sync.json", st)
    if "sharenite" in body:
        v = str(body["sharenite"] or "").strip()[:300]
        m = re.match(r"https://(?:www\.)?sharenite\.link/profiles/([A-Za-z0-9_-]+)(?:/games)?/?$", v)
        if v and not m:
            raise ValueError("Sharenite: den Link zu deinem Profil einfügen (https://www.sharenite.link/profiles/…/games)")
        s["sharenite"] = f"https://www.sharenite.link/profiles/{m.group(1)}/games" if m else ""
    # IGDB (0.7): derselbe Twitch-Schlüssel wie im eShopKompass, Client-ID und Secret
    for k in ("igdb_id", "igdb_secret"):
        if k in body:
            v = str(body[k] or "").strip()
            if v and not re.fullmatch(r"[A-Za-z0-9]{20,64}", v):
                raise ValueError("IGDB: Client-ID und Secret der Twitch-App, je 30 Zeichen aus Buchstaben und Ziffern")
            s[k] = v
    # Nexus Mods (0.7.7): persönlicher API-Schlüssel aus dem Nexus-Konto (Einstellungen, API Keys)
    if "nexus_key" in body:
        v = str(body["nexus_key"] or "").strip()
        if v and not re.fullmatch(r"[A-Za-z0-9+/=_-]{20,400}", v):
            raise ValueError("Nexus Mods: den persönlichen API-Schlüssel aus dem Nexus-Konto einfügen (Buchstaben, Ziffern, + / = -)")
        s["nexus_key"] = v
    # IsThereAnyDeal (0.9.0): API-Schlüssel einer eigenen App (isthereanydeal.com, My Apps)
    if "itad_key" in body:
        v = str(body["itad_key"] or "").strip()
        if v and not re.fullmatch(r"[A-Za-z0-9_-]{20,100}", v):
            raise ValueError("IsThereAnyDeal: den API-Schlüssel deiner App einfügen (isthereanydeal.com, My Apps)")
        s["itad_key"] = v
    if "auto" in body:
        s["auto"] = bool(body["auto"])
    if "hours" in body:
        try:
            s["hours"] = min(48, max(2, int(body["hours"])))
        except (TypeError, ValueError):
            raise ValueError("Abstand in Stunden: eine Zahl von 2 bis 48")
    store.save_json("settings.json", s)
    return s


def status():
    """Letzter Lauf aus sync.json; läuft gerade einer, mit Schritt und Protokoll live."""
    st = store.load_json("sync.json", {})
    st["running"] = _running.locked()
    if st["running"]:
        st.update(started=STATE["started"], step=STATE["step"], done=STATE["done"],
                  total=STATE["total"], log=list(STATE["log"]))
    return st


def _iso(at):
    return at.isoformat(timespec="seconds")


def _ago(iso, at):
    try:
        return at - datetime.fromisoformat(iso)
    except (TypeError, ValueError):
        return None


def due(settings=None, at=None, boot=False):
    """Ist ein Lauf nach Zeitplan fällig? boot: erster Blick nach dem Start des Containers;
    dann gleich ein Lauf (etwa mit neuen Lesern nach einem Update), außer der letzte liegt
    weniger als BOOT_GAP_MIN zurück. Nach einem Fehlschlag wartet auch der Start so lange."""
    s = settings or load_settings()
    if not s["auto"]:
        return False
    last = store.load_json("sync.json", {})
    at = at or now()
    since = _ago(last.get("started"), at)
    if since is None:
        return True
    gap = timedelta(minutes=BOOT_GAP_MIN)
    if last.get("ok") is False and since < gap:
        return False
    return since >= (gap if boot else timedelta(hours=s["hours"]))


def progress(step, done=0, total=0):
    STATE.update(step=step, done=done, total=total)


class _Source:
    """Eine Quelle in einem Lauf: Pausen, Fehlerzähler, zweiter Versuch nach Netzfehler, Ende
    bei Sperre oder Prüfseite (blocked: die Quelle ruht danach)."""

    def __init__(self, name, log, headers=None, pause=None):
        self.name, self.log, self.headers = name, log, headers
        self.pause = PAUSE if pause is None else pause
        self.n = self.errors = 0
        self.stopped = ""
        self.blocked = False
        self.stats = {}

    def _stop(self, why, where):
        self.stopped, self.blocked = why, True
        self.log(f"{self.name}: {why} bei {where}, Quelle ruht {REST_H} Stunden")

    def get(self, url, shown=None, absent=(), data=None):
        """Text der Antwort, None bei Fehler. Statuscodes in absent heißen „gibt es nicht“: dann
        "" ohne Fehlerzeile (etwa Steam-Spielerzahl 404 für eine App ohne Spieler). Mit data als POST (IGDB)."""
        if self.stopped:
            return None
        if self.n:
            sleep(self.pause)
        self.n += 1
        where = shown or url
        for attempt in (1, 2):
            try:
                text = sources.fetch(url, headers=self.headers, data=data) if data is not None else sources.fetch(url, headers=self.headers)
                break
            except sources.FetchError as e:
                if e.status == 0 and attempt == 1:
                    self.log(f"{self.name}: keine Verbindung bei {where}, zweiter Versuch")
                    sleep(NET_RETRY)
                    continue
                if e.status in absent:
                    return ""
                if e.status in sources.BLOCKED:
                    self._stop(f"gesperrt (HTTP {e.status})", where)
                else:
                    self.errors += 1
                    self.log(f"{self.name}: {'HTTP ' + str(e.status) if e.status else 'keine Verbindung'} bei {where}")
                    if self.errors >= MAX_ERRORS:
                        self.stopped = f"{self.errors} Fehler"
                        self.log(f"{self.name}: zu viele Fehler, Quelle für diesen Lauf beendet")
                return None
        why = sources.challenge(text)
        if why:
            self._stop(why, where)
            return None
        return text

    def result(self):
        return {"at": titles.now_iso(), "requests": self.n, "errors": self.errors,
                "ok": not self.stopped, "msg": self.stopped, "blocked": self.blocked, **self.stats}


def _targets(data):
    """Wunschtitel, die du noch nirgends besitzt."""
    return {k: t for k, t in data["titles"].items() if t.get("wish") and not t.get("owned")}


def _missed(t, field):
    """Suche nach diesem Titel schlug vor weniger als MISS_DAYS fehl."""
    if _old_misses["ignore"]:
        return False
    return (t.get(field) or "") > (now() - timedelta(days=MISS_DAYS)).isoformat(timespec="seconds")


def _retry_day(items, field):
    """Tag, an dem die erste der übersprungenen Suchen wieder fällig ist."""
    first = min((t.get(field) or "" for t in items), default="")
    try:
        return (datetime.fromisoformat(first) + timedelta(days=MISS_DAYS)).strftime("%d.%m.")
    except ValueError:
        return "?"


def _few(names, n=12):
    """Namen fürs Protokoll, höchstens n."""
    names = list(names)
    return ", ".join(names[:n]) + (f" und {len(names) - n} weitere" if len(names) > n else "")


def _ago_text(iso):
    d = _ago(iso, now())
    if d is None:
        return "?"
    h = int(d.total_seconds() // 3600)
    return f"vor {h} Stunden" if h else f"vor {int(d.total_seconds() // 60)} Minuten"


def _took(start):
    s = int(time.monotonic() - start)
    return f"{s // 60}:{s % 60:02d} min"


def _pick(cards, t):
    """Den passenden Treffer einer Suche: gleiche Meta-ID, sonst genau einer, dessen Name zu
    einem der Namen aus titles.store_names passt."""
    if t.get("meta_id"):
        hit = [c for c in cards if c["meta_id"] == t["meta_id"]]
        if hit:
            return hit[0]
    names = {titles.norm(x) for x in titles.store_names(t)}
    same = [c for c in cards if titles.norm(c["name"]) in names]
    return same[0] if len(same) == 1 else None


def _search(src, t, url, pick, budget):
    """Sucht den Titel unter jedem Namen aus titles.store_names, bis einer passt. Liefert
    (Treffer, Zahl der Suchen, ohne Treffer). ohne Treffer ist False, wenn eine Anfrage scheiterte
    oder das Budget nicht für alle Namen reichte; dann gilt die Suche nicht als fehlgeschlagen."""
    n = 0
    for name in titles.store_names(t):
        if n >= budget or src.stopped:
            return None, n, False
        n += 1
        text = src.get(url(name))
        if text is None:
            return None, n, False
        hit = pick(text)
        if hit:
            return hit, n, False
    return None, n, True


def _qsdb(targets, upd, log):
    src = _Source("QuestStoreDB", log, QSDB_HEAD)
    stamp = titles.now_iso()
    start = time.monotonic()
    # 1. Angebotsliste
    sale, pages, page = {}, 1, 1
    while page <= min(pages, MAX_SALE_PAGES):
        progress("QuestStoreDB: Angebotsliste", page, min(pages, MAX_SALE_PAGES))
        text = src.get(f"{prices.QSDB}/on_sale/?sort=-sale_start_time&page={page}")
        if text is None:
            break
        if page == 1:
            pages = prices.qsdb_pages(text)
        for c in prices.qsdb_cards(text):
            sale.setdefault(c["meta_id"], c)
        page += 1
    wished = []
    for k, t in targets.items():
        c = sale.get(t.get("meta_id") or "")
        if c and c["price"] is not None:
            wished.append(t["name"])
            u = upd.setdefault(k, {})
            u["meta"] = {"price": c["price"], "base": c["base"], "discount": c["discount"],
                         "until": c["until"], "kind": c["kind"], "at": stamp}
    # 2. Titelseiten, die älteste zuerst
    old = (now() - timedelta(hours=PAGE_AGE_H)).isoformat(timespec="seconds")
    todo = sorted((((t.get("live") or {}).get("meta") or {}).get("page_at") or "", k)
                  for k, t in targets.items())
    searches = pages_done = parsed = 0
    fresh, later, found, missed, waiting, unread = 0, 0, [], [], [], []
    due_n = min(MAX_PAGES, sum(p <= old for p, _ in todo))
    for page_at, k in todo:
        if page_at > old:
            fresh += 1
            continue
        if pages_done >= MAX_PAGES or src.stopped:
            later += 1
            continue
        progress("QuestStoreDB: Titelseiten", pages_done, due_n)
        t = targets[k]
        path = ((t.get("live") or {}).get("meta") or {}).get("path") or ""
        link = (t.get("links") or {}).get("qsdb") or ""
        if not path and link.startswith(prices.QSDB + "/"):
            path = link[len(prices.QSDB):]
        if not path:
            if _missed(t, "meta_miss"):
                waiting.append(t)
                continue
            if searches >= MAX_SEARCH:
                later += 1
                continue

            def url(name):
                return f"{prices.QSDB}/all_apps/?" + urllib.parse.urlencode({"release_status": "all", "q": name})
            hit, n, miss = _search(src, t, url, lambda text: _pick(prices.qsdb_cards(text), t), MAX_SEARCH - searches)
            searches += n
            if not hit:
                if miss:
                    upd.setdefault(k, {})["meta_miss"] = stamp
                    missed.append(t["name"])
                continue
            found.append(t["name"])
            path = hit["path"]
        text = src.get(prices.QSDB + path)
        pages_done += 1
        g = prices.qsdb_game(text) if text else None
        if not g:
            if text is not None:
                unread.append(path)
            continue
        parsed += 1
        u = upd.setdefault(k, {})
        today = now().strftime("%Y-%m-%d")
        on_sale = g["price"] is not None and g["base"] and g["price"] < g["base"]
        u["meta"] = {"price": g["price"], "base": g["base"],
                     "discount": round((1 - g["price"] / g["base"]) * 100) if on_sale else 0,
                     "until": g["until"] if on_sale and g["until"] >= today else "",
                     "kind": (u.get("meta") or {}).get("kind") or ("discount" if on_sale else "base"),
                     "low": g["low"], "low_at": g["low_at"], "rating": g["rating"],
                     "ratings": g["ratings"], "version": g["version"], "path": g["path"] or path,
                     "at": stamp, "page_at": stamp}
        if g["meta_id"]:
            u["meta_id"] = g["meta_id"]
        if g["name"]:
            u["names"] = [g["name"]]
        if g["hist"]:
            u["meta_hist"] = g["hist"]
        u["qsdb"] = prices.QSDB + (g["path"] or path)
    log(f"QuestStoreDB, Angebotsliste: {len(sale)} Angebote auf {page - 1} Seiten"
        + (f", von deiner Wunschliste ({len(wished)}): {_few(wished)}" if wished else ", keines von deiner Wunschliste"))
    log(f"QuestStoreDB, Titelseiten: {pages_done} gelesen ({parsed} lesbar), {fresh} aktuell (jünger als {PAGE_AGE_H} h)"
        + (f", {later} folgen beim nächsten Abgleich" if later else ""))
    if unread:
        log(f"QuestStoreDB, Titelseiten ohne lesbaren Preis ({len(unread)}): {_few(unread, 6)}")
    if searches or waiting:
        log(f"QuestStoreDB, Suche: {searches} Anfragen, {len(found)} Titel gefunden"
            + (f", ohne Treffer ({len(missed)}): {_few(missed)}" if missed else "")
            + (f"; {len(waiting)} ohne Treffer in den letzten {MISS_DAYS} Tagen, nächste Suche ab {_retry_day(waiting, 'meta_miss')}"
               if waiting else ""))
    log(f"QuestStoreDB: fertig nach {_took(start)}, {src.n} Anfragen" + (f", {src.errors} Fehler" if src.errors else ""))
    src.stats = {"sale": len(sale), "pages": pages_done, "parsed": parsed, "searches": searches}
    return src.result()


def _steam(targets, upd, log):
    src = _Source("Steam", log)
    stamp = titles.now_iso()
    start = time.monotonic()
    ids = {}
    searches, later, hits, missed, waiting = 0, 0, [], [], []
    for k, t in targets.items():
        if t.get("steam_appid"):
            ids[k] = t["steam_appid"]
            continue
        if _missed(t, "steam_miss"):
            waiting.append(t)
            continue
        if searches >= MAX_SEARCH or src.stopped:
            later += 1
            continue
        progress("Steam: Suche", searches, 0)
        names = {titles.norm(x) for x in titles.store_names(t)}
        wrong = set(t.get("steam_wrong") or [])

        def pick(text):
            same = [i for i in prices.steam_search(text) if titles.norm(i["name"]) in names and i["appid"] not in wrong]
            return same[0] if len(same) == 1 else None
        hit, n, miss = _search(src, t, lambda name: f"{STEAM}/api/storesearch/?"
                               + urllib.parse.urlencode({"term": name, "l": "german", "cc": "DE"}),
                               pick, MAX_SEARCH - searches)
        searches += n
        if hit:
            ids[k] = hit["appid"]
            upd.setdefault(k, {})["steam_appid"] = hit["appid"]
            hits.append(t["name"])
        elif miss:
            upd.setdefault(k, {})["steam_miss"] = stamp
            missed.append(t["name"])
    if searches or waiting or later:
        # Viele Quest-Titel gibt es auf Steam nicht; ohne Treffer ist hier der Normalfall
        log(f"Steam, Suche: {searches} Anfragen, {len(hits)} App-IDs gefunden"
            + (f" ({_few(hits)})" if hits else "")
            + (f", ohne Treffer {len(missed)}" if missed else "")
            + (f"; {len(waiting)} ohne Treffer in den letzten {MISS_DAYS} Tagen, nächste Suche ab {_retry_day(waiting, 'steam_miss')}"
               if waiting else "")
            + (f"; {later} folgen beim nächsten Abgleich" if later else ""))
    keys = list(ids)
    found, sale, none = 0, [], []
    for i in range(0, len(keys), 50):
        chunk = keys[i:i + 50]
        progress("Steam: Preise", i // 50 + 1, (len(keys) + 49) // 50)
        q = ",".join(dict.fromkeys(ids[k] for k in chunk))
        text = src.get(f"{STEAM}/api/appdetails?appids={q}&cc=de&filters=price_overview")
        if text is None:
            continue
        got = prices.steam_prices(text)
        for k in chunk:
            p = got.get(ids[k])
            if p:
                found += 1
                upd.setdefault(k, {})["steam"] = dict(p, at=stamp)
                if p.get("discount"):
                    sale.append(targets[k]["name"])
            else:
                none.append(targets[k]["name"])
    log(f"Steam, Preise: {found} Preise für {len(keys)} App-IDs"
        + (f", im Angebot ({len(sale)}): {_few(sale)}" if sale else ", keiner im Angebot")
        + (f"; ohne Preis im deutschen Store ({len(none)}): {_few(none, 6)}" if none else ""))
    log(f"Steam: fertig nach {_took(start)}, {src.n} Anfragen" + (f", {src.errors} Fehler" if src.errors else ""))
    src.stats = {"ids": len(keys), "found": found, "searches": searches}
    return src.result()


def _gg(targets, upd, key, log):
    src = _Source("gg.deals", log)
    stamp = titles.now_iso()
    ids = {}
    for k, t in targets.items():
        a = (upd.get(k) or {}).get("steam_appid") or t.get("steam_appid")
        if a:
            ids.setdefault(a, []).append(k)
    apps = list(ids)
    found, retail, keyshop, seen = 0, 0, 0, set()
    for i in range(0, len(apps), 100):
        progress("gg.deals: Preise", i // 100 + 1, (len(apps) + 99) // 100)
        q = urllib.parse.urlencode({"ids": ",".join(apps[i:i + 100]), "region": "de"})
        # Der Schlüssel steht nur in der Anfrage, nie im Protokoll
        text = src.get(f"{GG_API}?{q}&key={urllib.parse.quote(key)}", shown=f"{GG_API}?{q}")
        if text is None:
            continue
        try:
            got = prices.gg_prices(text)
        except ValueError as e:
            log(str(e))
            src.stopped = "abgelehnt"
            break
        for a, p in got.items():
            seen.add(a)
            retail += p["retail"] is not None
            keyshop += p["keyshops"] is not None
            for k in ids.get(a, []):
                found += 1
                upd.setdefault(k, {})["gg"] = dict(p, at=stamp)
    log(f"gg.deals: {found} Preise für {len(apps)} App-IDs, {retail} mit Händlerpreis, {keyshop} mit Keyshop-Preis"
        + (f", {len(apps) - len(seen)} ohne Eintrag bei gg.deals" if len(seen) < len(apps) else ""))
    src.stats = {"ids": len(apps), "found": found}
    return src.result()


def _merge_history(hist, src, ident, rows):
    """Verlauf einer Quelle (QuestStoreDB) mit dem eigenen zusammenlegen: je Tag ein Preis, der
    eigene Wert gilt, wo beide einen haben. Folgende gleiche Preise fallen weg."""
    if not ident or not rows:
        return
    by_day = {str(d): p for d, p in rows if isinstance(p, (int, float))}
    by_day.update({d: p for d, p in hist.get(src, {}).get(str(ident), [])})
    out = []
    for d in sorted(by_day):
        if not out or out[-1][1] != by_day[d]:
            out.append([d, by_day[d]])
    hist.setdefault(src, {})[str(ident)] = out


def _history(hist, src, ident, price, day):
    if not ident or price is None:
        return
    rows = hist.setdefault(src, {}).setdefault(str(ident), [])
    if not rows or rows[-1][1] != price:
        rows.append([day, price])


def apply(upd):
    """Ergebnis eines Laufs in die aktuelle data.json eintragen und den Verlauf fortschreiben.
    Titel, die es inzwischen nicht mehr gibt, fallen weg."""
    day = now().strftime("%Y-%m-%d")
    jumps = 0
    # fürs Protokoll: günstiger, teurer, neuer Tiefstpreis; Cent-Schwankungen nur gezählt
    moves = {"down": [], "up": [], "low": [], "small": []}
    with store.lock:
        data = store.load_data()
        hist = store.load_json("history.json", {})
        for k, u in upd.items():
            t = data["titles"].get(k)
            if not t:
                continue
            live = t.setdefault("live", {})
            for src in ("meta", "steam", "gg"):
                if src in u:
                    v = dict(u[src])
                    old = (live.get(src) or {}).get("base")
                    if old and v.get("base") is not None and abs(v["base"] - old) > JUMP * old:
                        jumps += 1
                    was = (live.get(src) or {}).get("price" if src != "gg" else "retail")
                    new = v.get("price" if src != "gg" else "retail")
                    if was is not None and new is not None and new != was:
                        small = abs(new - was) < SMALL_EUR and abs(new - was) < SMALL_REL * was
                        moves["small" if small else "down" if new < was else "up"].append(f"{t['name']} ({SHOPS[src]} {_eur(was)} → {_eur(new)})")
                    if src == "meta":
                        prev = live.get("meta") or {}
                        for f in ("low", "low_at", "rating", "ratings", "version", "path", "page_at"):
                            if v.get(f) is None and prev.get(f) is not None:
                                v[f] = prev[f]
                        if v.get("price") is not None and (v.get("low") is None or v["price"] < v["low"]):
                            if prev.get("low") is not None:
                                moves["low"].append(f"{t['name']} {_eur(v['price'])}")
                            v["low"], v["low_at"] = v["price"], day
                    live[src] = v
            links = t.setdefault("links", {})
            if u.get("qsdb"):
                links["qsdb"] = u["qsdb"]
            if (u.get("gg") or {}).get("url", "").startswith("https://gg.deals/"):
                links["gg"] = u["gg"]["url"]
            for f in ("meta_miss", "steam_miss"):
                if u.get(f):
                    t[f] = u[f]
            for x in u.get("names") or []:
                titles.add_alias(t, x)
            ids = {}
            if u.get("meta_id") and not t.get("meta_id"):
                ids["meta_id"] = u["meta_id"]
            if u.get("steam_appid") and not t.get("steam_appid"):
                ids["steam_appid"] = u["steam_appid"]
            if ids:
                titles.set_ids(data, k, **ids)
            _merge_history(hist, "meta", t.get("meta_id"), u.get("meta_hist"))
            _history(hist, "meta", t.get("meta_id"), (live.get("meta") or {}).get("price"), day)
            _history(hist, "steam", t.get("steam_appid"), (live.get("steam") or {}).get("price"), day)
            g = live.get("gg") or {}
            best = min([x for x in (g.get("retail"), g.get("keyshops")) if x is not None], default=None)
            _history(hist, "gg", t.get("steam_appid"), best, day)
        store.save_data(data)
        store.save_json("history.json", hist)
    sale = sum(1 for t in _targets(data).values()
               if any(((t.get("live") or {}).get(x) or {}).get("discount") for x in ("meta", "steam")))
    return {"jumps": jumps, "moves": moves, "coverage": _coverage(data), "sale": sale}


def _runs(left, per, sep=" "):
    """„(noch etwa 4 Läufe)“: wie viele Abgleiche eine Warteschlange noch braucht."""
    n = -(-left // per) if per else 0
    if n <= 1:
        return ""
    return f"{sep}noch etwa {n} Läufe" if sep == ", " else f" (noch etwa {n} Läufe)"


def _eur(v):
    return f"{v:.2f} €".replace(".", ",")


def _coverage(data):
    """Stand der Wunschliste nach dem Lauf: je Quelle, wie viele Titel einen Preis haben, und
    welche gar keinen."""
    tg = list(_targets(data).values())
    has = {s: sum(1 for t in tg if ((t.get("live") or {}).get(s) or {})) for s in ("meta", "steam", "gg")}
    bare = [t["name"] for t in tg if not any((t.get("live") or {}).get(s) for s in ("meta", "steam", "gg"))]
    return {"n": len(tg), "has": has, "bare": bare}


def summary(applied, warnings, results):
    """Eine Zeile fürs Protokoll: was für dich neu ist, dann was nicht stimmt."""
    mv, sale = applied["moves"], applied.get("sale", 0)
    news = [f"{sale} Wunschtitel im Angebot" if sale else "kein Wunschtitel im Angebot",
            f"{len(mv['down'])} günstiger" if mv["down"] else "",
            f"{len(mv['low'])} neuer Meta-Tiefstpreis" if mv["low"] else ""]
    bad = [NAMES.get(k, k) for k, r in results.items() if not r.get("ok")]
    return ("Kurz: " + ", ".join(x for x in news if x)
            + (f"; Fehler bei {', '.join(bad)}" if bad else "")
            + (f"; Selbstprüfung: {len(warnings)} Hinweis{'e' if len(warnings) > 1 else ''}" if warnings else "; alles glaubhaft"))


def self_check(results, prev, applied):
    """Ergebnisse glaubhaft? Meldet, statt still weiterzurechnen: leere Listen, wo sonst etwas
    stand, Seiten ohne lesbaren Preis, Normalpreise mit großen Sprüngen."""
    w = []
    q, pq = results.get("qsdb") or {}, prev.get("qsdb") or {}
    if q.get("ok") and q.get("sale") == 0 and (pq.get("sale") or 0) > 0:
        w.append(f"QuestStoreDB: keine Angebote erkannt (zuletzt {pq['sale']}), hat sich die Seite geändert?")
    if q.get("pages") and not q.get("parsed"):
        w.append(f"QuestStoreDB: auf {q['pages']} Titelseiten kein Preis lesbar")
    for k in ("steam", "gg"):
        r = results.get(k) or {}
        if r.get("ok") and r.get("ids") and not r.get("found"):
            w.append(f"{NAMES[k]}: kein Preis für {r['ids']} App-IDs")
    if applied.get("jumps"):
        w.append(f"{applied['jumps']} Normalpreise änderten sich um mehr als {round(JUMP * 100)} %")
    return w


def _app_checks(src, appids, apps, budget, stamp):
    """Fragt für unbekannte App-IDs die Store-Seite, ob die App VR kann (höchstens budget["apps"]
    je Lauf). Ergebnis in apps (Name, VR); Apps, die Steam nicht mehr zeigt, gelten als ohne VR."""
    n = 0
    for a in appids:
        if a in apps:
            continue
        if budget["apps"] <= 0 or src.stopped:
            break
        budget["apps"] -= 1
        n += 1
        progress("Steam: Apps prüfen", n, 0)
        text = src.get(f"{STEAM}/api/appdetails?appids={a}&cc=de&l=german")
        if text is None:
            continue
        try:
            info = accounts.steam_app(text, a)
        except ValueError:
            continue
        apps[a] = {"name": (info or {}).get("name", ""), "vr": bool(info and info["vr"]), "at": stamp}
    return n


def _steam_account(settings, log, budget):
    """Steam-Konto: Besitz (mit Schlüssel) und Wunschliste, unbekannte Apps auf VR prüfen,
    eintragen. Liefert das Ergebnis für sync.json."""
    src = _Source("Steam-Konto", log)
    start, stamp = time.monotonic(), titles.now_iso()
    key = settings["steam_key"]
    kind, val = accounts.steam_id_input(settings["steam_id"])
    sid = val if kind == "id" else ""
    if kind == "vanity":
        if not key:
            log("Steam-Konto: Für einen Profilnamen statt der Zahl braucht es den Steam-Schlüssel, nicht abgefragt")
            return dict(src.result(), ok=False, msg="Profilname ohne Schlüssel")
        text = src.get(f"{STEAM_API}/ISteamUser/ResolveVanityURL/v1/?vanityurl={urllib.parse.quote(val)}&key={key}",
                       shown=f"{STEAM_API}/ISteamUser/ResolveVanityURL/v1/?vanityurl={val}")
        sid = accounts.steam_vanity(text) if text else ""
        if not sid:
            log(f"Steam-Konto: Profilname „{val}“ nicht gefunden")
            return dict(src.result(), ok=False, msg="Profil nicht gefunden")
    owned = wished = None
    if key:
        text = src.get(f"{STEAM_API}/IPlayerService/GetOwnedGames/v1/?steamid={sid}&include_appinfo=1"
                       f"&include_played_free_games=1&key={key}",
                       shown=f"{STEAM_API}/IPlayerService/GetOwnedGames/v1/?steamid=…")
        try:
            owned = accounts.steam_owned(text) if text else None
        except ValueError as e:
            log(str(e))
    else:
        log("Steam-Konto: ohne Schlüssel nur die Wunschliste")
    if settings.get("steam_wish", True):
        text = src.get(f"{STEAM_API}/IWishlistService/GetWishlist/v1/?steamid={sid}",
                       shown=f"{STEAM_API}/IWishlistService/GetWishlist/v1/?steamid=…")
        try:
            wished = accounts.steam_wishlist(text) if text else None
        except ValueError as e:
            log(str(e))
    else:
        log("Steam-Konto: Wunschliste nicht gelesen (in den Einstellungen abgeschaltet)")
    data = store.load_data()
    if wished == [] and any("steam" in (t.get("wish_src") or {}) for t in data["titles"].values()):
        # Leer, obwohl zuletzt Titel darauf standen: eher privat gestellt als leer geräumt
        log("Steam-Konto: Wunschliste leer oder nicht öffentlich, die zuletzt gelesene gilt weiter")
        wished = None
    apps = dict(data.get("steam_apps") or {})
    have = {t.get("steam_appid") for t in data["titles"].values()}
    todo = [a for a in wished or [] if a not in have]
    todo += [g["appid"] for g in owned or [] if g["appid"] not in have
             and not titles.find(data, "", g["appid"], g["name"])]
    checked = _app_checks(src, todo, apps, budget, stamp)
    with store.lock:
        data = store.load_data()
        data["steam_apps"] = dict(data.get("steam_apps") or {}, **apps)
        res = accounts.apply_steam(data, owned, wished, data["steam_apps"], stamp)
        if owned is not None:
            # 0.9.3: Spielzeit und zuletzt gespielt je App, für Sammlung und „Liegt brach“
            data["steam_play"], data["steam_play_at"] = accounts.steam_play(owned), stamp
        store.save_data(data)
    if owned is not None:
        never = sum(1 for g in owned if g.get("min") == 0)
        log(f"Steam-Konto, Besitz: {len(owned)} Spiele, davon {res['owned']} VR-Titel, {never} nie gespielt"
            + (f", neu ({len(res['owned_new'])}): {_few(res['owned_new'])}" if res["owned_new"] else ""))
    if wished is not None:
        log(f"Steam-Konto, Wunschliste: {len(wished)} Apps, davon {len(res['wish_keys'])} VR-Titel"
            + (f"; neu auf der Wunschliste ({len(res['wish_added'])}): {_few(res['wish_added'])}" if res["wish_added"] else "")
            + (f"; nicht mehr auf der Steam-Wunschliste und damit von deiner ({len(res['wish_removed'])}): "
               f"{_few(res['wish_removed'])}" if res["wish_removed"] else ""))
    rest = res["unchecked"]
    if checked or rest:
        log(f"Steam-Konto: {checked} Apps auf VR geprüft"
            + (f", {rest} noch ungeprüft, weiter beim nächsten Abgleich{_runs(rest, APPINFO_MAX)}" if rest else ""))
    log(f"Steam-Konto: fertig nach {_took(start)}, {src.n} Anfragen" + (f", {src.errors} Fehler" if src.errors else ""))
    src.stats = {"owned": len(owned) if owned is not None else None, "wish": len(wished) if wished is not None else None,
                 "vr_owned": res["owned"], "vr_wish": len(res["wish_keys"])}
    r = src.result()
    if owned is None and wished is None:
        r.update(ok=False, msg=r["msg"] or "nichts lesbar")
    return r


def _gg_wish(settings, log, budget):
    """Geteilte Wunschliste von gg.deals lesen und eintragen. Unbekannte Namen sucht das Tool im
    Steam-Store (nur genau gleicher Name) und nimmt sie auf, wenn die App VR kann."""
    src = _Source("gg.deals-Wunschliste", log)
    start, stamp = time.monotonic(), titles.now_iso()
    url = settings["gg_wish"].rstrip("/") + "/"
    items, seen, pages, page = [], set(), 1, 1
    while page <= min(pages, GG_WISH_PAGES):
        progress("gg.deals: Wunschliste", page, pages)
        text = src.get(url + (f"?page={page}" if page > 1 else ""), shown=f"gg.deals-Wunschliste, Seite {page}")
        if text is None:
            break
        got, n = accounts.gg_wishlist(text)
        pages = max(pages, n)
        page += 1
        fresh = [i for i in got if i["slug"] not in seen]
        if not fresh:
            break
        seen.update(i["slug"] for i in fresh)
        items += fresh
    if not items:
        log("gg.deals-Wunschliste: keine Spiele erkannt" + ("" if src.stopped else
            " (Seite geändert oder Link abgelaufen? „Verbindung testen“ zeigt die Antwort)") + ", die zuletzt gelesene gilt weiter")
        return dict(src.result(), ok=False, msg=src.stopped or "nichts erkannt")
    with store.lock:
        data = store.load_data()
        res = accounts.apply_gg_wishes(data, items, stamp)
        store.save_data(data)
    pcwish.replace(items, "Server", stamp)
    added, steam_n = _gg_resolve(res["unknown"], log, budget, stamp, list(res["keys"]))
    unknown = [n for n in res["unknown"] if n not in added]
    log(f"gg.deals-Wunschliste: {len(items)} Spiele auf {page - 1} Seiten, davon {len(res['keys']) + len(added)} VR-Titel im Tool"
        + (f"; neu auf der Wunschliste ({len(res['wish_added']) + len(added)}): {_few(res['wish_added'] + added)}"
           if res["wish_added"] or added else "")
        + (f"; nicht mehr bei gg.deals und damit von deiner ({len(res['wish_removed'])}): {_few(res['wish_removed'])}"
           if res["wish_removed"] else ""))
    if unknown:
        log(f"gg.deals-Wunschliste, nicht zugeordnet (kein VR laut Steam oder nicht gefunden, {len(unknown)}): {_few(unknown)}")
    log(f"gg.deals-Wunschliste: fertig nach {_took(start)}, {src.n + steam_n} Anfragen")
    src.stats = {"items": len(items), "vr": len(res["keys"]) + len(added)}
    return src.result()


def _gg_resolve(names, log, budget, stamp, keys=None):
    """Namen von der gg.deals-Wunschliste, die das Tool nicht kennt: im Steam-Store suchen (nur
    genau gleicher Name, je Name höchstens alle MISS_DAYS Tage) und aufnehmen, wenn die App VR
    kann. keys: die übrigen Titel der Liste; dann ersetzt das Ergebnis die gg.deals-Wunschliste,
    sonst (Lesezeichen) kommen die gefundenen nur dazu. Liefert (aufgenommene Namen, Anfragen)."""
    steam = _Source("Steam", log)
    data = store.load_data()
    tried = dict(data.get("gg_tried") or {})
    old = (now() - timedelta(days=MISS_DAYS)).isoformat(timespec="seconds")
    found, todo = {}, [n for n in names if (tried.get(titles.norm(n)) or "") < old][:budget["search"]]
    for name in todo:
        budget["search"] -= 1
        text = steam.get(f"{STEAM}/api/storesearch/?" + urllib.parse.urlencode({"term": name, "l": "german", "cc": "DE"}))
        if text is None:
            break
        tried[titles.norm(name)] = stamp
        same = [i for i in prices.steam_search(text) if titles.norm(i["name"]) == titles.norm(name)]
        if len(same) == 1:
            found[same[0]["appid"]] = name
    apps = dict(data.get("steam_apps") or {})
    _app_checks(steam, list(found), apps, budget, stamp)
    added = []
    with store.lock:
        data = store.load_data()
        data["steam_apps"] = dict(data.get("steam_apps") or {}, **apps)
        data["gg_tried"] = tried
        new_keys = []
        for appid, name in found.items():
            if (apps.get(appid) or {}).get("vr"):
                k, _ = titles.upsert(data, name, "", appid)
                data["titles"][k]["steam_sure"] = True
                new_keys.append(k)
                added.append(name)
        if keys is not None and new_keys:
            titles.set_wishes(data, "gg", list(keys) + new_keys, stamp)
        elif new_keys:
            titles.add_wish(data, "gg", new_keys, stamp)
        if data.get("gg_unknown"):
            data["gg_unknown"] = [n for n in data["gg_unknown"] if n not in added and titles.norm(n) not in tried]
        store.save_data(data)
    return added, steam.n


def _gg_pending(log, budget):
    """Unbekannte Namen aus der per Lesezeichen gelesenen gg.deals-Wunschliste nachsuchen."""
    names = store.load_data().get("gg_unknown") or []
    if not names:
        return None
    stamp = titles.now_iso()
    added, n = _gg_resolve(names, log, budget, stamp)
    left = store.load_data().get("gg_unknown") or []
    log(f"gg.deals-Wunschliste (Lesezeichen): {len(names)} unbekannte Namen, {n} Anfragen bei Steam"
        + (f"; als VR-Titel aufgenommen ({len(added)}): {_few(added)}" if added else "")
        + (f"; {len(left)} folgen beim nächsten Abgleich" if left else ""))
    return {"at": stamp, "ok": True, "requests": n, "errors": 0, "msg": "", "via": "Lesezeichen"}


# Steam-Rezensionen (0.7.4): Im Test am 27.10.2026 leitete Steam die bisherige Adresse bei drei von drei Apps
# auf die Startseite um. Schickt Steam statt Daten eine Seite, versucht der Abruf die nächste Form der Adresse
# und bleibt bis zum Neustart bei der, die Daten liefert. 0.7.5: Im Test leitete Steam alle drei Formen um;
# Form 4 ist die Store-Schnittstelle der Steam Web API (IStoreBrowseService/GetItems, ohne Schlüssel), die
# je App die Zusammenfassung der Rezensionen nennt
REVIEW_Q = ["json=1&language=all&purchase_type=all&num_per_page=0&filter=summary",
            "json=1&language=all&purchase_type=all&review_type=all&num_per_page=1&filter=all&cursor=*",
            "json=1&filter=recent&language=all&num_per_page=1",
            "storebrowse"]
STOREBROWSE = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"
_rev_q = {"i": 0}


def review_url(gid, i=None):
    q = REVIEW_Q[_rev_q['i'] if i is None else i]
    if q == "storebrowse":
        return STOREBROWSE + "?" + urllib.parse.urlencode({"input_json": json.dumps(
            {"ids": [{"appid": int(gid)}], "context": {"language": "english", "country_code": "DE"},
             "data_request": {"include_reviews": True}}, separators=(",", ":"))})
    return f"{STEAM}/appreviews/{gid}?{q}"


def _rev_get(src, gid, shown):
    # Lieferte bei einem Spiel keine Form Daten (etwa eine Altersprüfung), fragt der Lauf danach je Spiel
    # nur einmal, sonst kostet jedes Spiel drei Anfragen
    text = None
    for n in range(1 if src.__dict__.get("rev_pages") else len(REVIEW_Q)):
        i = (_rev_q["i"] + n) % len(REVIEW_Q)
        text = src.get(review_url(gid, i), shown=shown)
        if text is None or text.lstrip()[:1] != "<":
            if text is not None and i != _rev_q["i"]:
                _rev_q["i"] = i
                src.log(f"{src.name}: Steam antwortet nur noch auf Form {i + 1} der Adresse, die gilt jetzt")
            return text
    src.__dict__["rev_pages"] = True
    return text


def _recent_get(src, gid):
    """Stimmen der letzten 30 Tage aus dem Bewertungsdiagramm des Steam-Stores (0.8.18) für den Trend. Schickt
    Steam statt Daten eine Seite, fragt der Lauf nicht weiter; der Trend nimmt dann die eigenen Messungen."""
    if src.__dict__.get("hist_pages") or src.stopped:
        return None
    text = src.get(f"{STEAM}/appreviewhistogram/{gid}?l=english&review_score_preference=0", shown=f"Steam-Trend {gid}")
    if text is None:
        return None
    if text.lstrip()[:1] == "<":
        src.__dict__["hist_pages"] = True
        src.log(f"{src.name}: Steam-Trend liefert eine Seite statt Daten, in diesem Lauf nur eigene Messungen")
        return None
    # Ohne lesbare Stimmen gilt das Spiel als gefragt (0.8.21), sonst fragt jeder Lauf es wieder
    return dict(trend.histogram(text) or {"up": 0, "down": 0, "miss": True}, at=titles.now_iso())


def _trend_due(entries, skip=()):
    """Schlüssel, deren Trend fällig ist (0.8.21): ab trend.MIN_ALL Rezensionen, ohne Stimmen der letzten 30 Tage oder
    älter als TREND_DAYS, die ältesten zuerst. entries: {Schlüssel: rev}."""
    old = _iso(now() - timedelta(days=TREND_DAYS))
    due = [((r.get("recent") or {}).get("at") or "", k) for k, r in entries.items()
           if k not in skip and (r.get("n") or 0) >= trend.MIN_ALL and ((r.get("recent") or {}).get("at") or "") < old]
    return [k for _, k in sorted(due)]


def _trend_fill(src, keys, gid_of, label):
    """Trend für die fälligen Schlüssel holen, höchstens TREND_MAX; {Schlüssel: recent}."""
    out = {}
    for i, k in enumerate(keys[:TREND_MAX]):
        progress(label, i, min(TREND_MAX, len(keys)))
        rc = _recent_get(src, gid_of(k))
        if rc:
            out[k] = rc
        if src.stopped or src.__dict__.get("hist_pages"):
            break
    return out


def _per_game(log, label, field, days, limit, url, parse, stale=None, get=None, want=None, order=None, src=None):
    """Abruf je Steam-Spiel der Sammlung (Entdecken): zuerst die ohne Wert, dann die ältesten;
    höchstens limit je Lauf, nach days Tagen neu. Ergebnis je Spiel unter field in
    collection.json. Liefert (Quelle, gelesen {Schlüssel: Wert}, noch offen)."""
    col = store.load_json(collection.FILE, collection.EMPTY)
    old = _iso(now() - timedelta(days=days))
    todo = sorted(((g.get(field) or {}).get("at") or "", k) for k, g in (col.get("games") or {}).items()
                  if g.get("store") == "Steam" and str(g.get("id") or "").isdigit()
                  and (not want or want(g))
                  and (((g.get(field) or {}).get("at") or "") < old or (stale and stale(g.get(field)))))
    if order:
        todo.sort(key=lambda x: (x[0], order(col["games"][x[1]])))
    quiet, src = src is not None, src or _Source(label, log)
    if not todo:
        if not quiet:
            log(f"{label}: alle aktuell" if col.get("games") else f"{label}: keine Sammlung, nichts zu tun")
        return src, None, 0
    got = {}
    batch = todo[:limit]
    for i, (_, k) in enumerate(batch):
        progress(label, i, len(batch))
        gid = col["games"][k]["id"]
        text = get(src, gid, f"{label} {gid}") if get else src.get(url(gid), shown=f"{label} {gid}")
        if text is None:
            if src.stopped:
                break
            continue
        got[k] = dict(parse(text, gid), at=titles.now_iso())
    with store.lock:
        col = store.load_json(collection.FILE, collection.EMPTY)
        for k, r in got.items():
            if k in col.get("games", {}):
                col["games"][k][field] = r
        store.save_json(collection.FILE, col)
    left = len(todo) - len(got)
    src.stats = {"read": len(got), "left": left}
    return src, got, left


def _reviews(log):
    """Steam-Rezensionen: Anzahl und Anteil positiv je Steam-Spiel, nach REVIEWS_DAYS neu. Bei
    einem vermuteten Laden bestätigt eine Antwort mit Rezensionen die Steam-ID."""
    start = time.monotonic()
    src, got, left = _per_game(
        log, "Steam-Rezensionen", "rev", REVIEWS_DAYS, REVIEWS_MAX,
        lambda gid: f"{STEAM}/appreviews/{gid}?json=1&language=all&purchase_type=all&num_per_page=0&filter=summary",
        # Statt Daten eine Store-Seite (0.7.2): etwa Spiele ab 18 ohne Anmeldung; gemerkt als „page“
        lambda text, gid: prices.steam_reviews(text) or dict({"n": None, "pct": None, "desc": ""}, **({"page": True} if text.lstrip()[:1] == "<" else {})),
        get=_rev_get)
    if got is not None:
        known = sum(1 for r in got.values() if r.get("n"))
        pages = sum(1 for r in got.values() if r.get("page"))
        log(f"Steam-Rezensionen: {len(got)} Spiele gelesen, {known} mit Rezensionen"
            + (f", bei {pages} kam eine Store-Seite statt Daten (etwa Spiele ab 18)" if pages else "")
            + (f", {left} noch offen (je Lauf {REVIEWS_MAX}{_runs(left, REVIEWS_MAX, ", ")})" if left else ", alle aktuell") + f", {_took(start)}")
    return src.result()


def _eshop(log):
    """Switch-Sammlung aus dem eShopKompass im eigenen Netz (0.7.3): eine Anfrage an ESHOP_URL/api/sammlung,
    nur lesend. Ersetzt die Switch-Spiele aus dem eShopKompass, alles andere bleibt."""
    start = time.monotonic()
    label = NAMES["eshop"]
    src = _Source(label, log)
    url = sources.eshop_url()
    text = src.get(url, shown=f"{label} (Sammlung)")
    if text is None:
        return src.result()
    try:
        d = json.loads(text)
    except ValueError:
        d = None
    if not isinstance(d, dict) or d.get("app") != "eshop-kompass" or not isinstance(d.get("games"), list):
        src.stopped = "keine Sammlung des eShopKompass"
        log(f"{label}: Antwort ist nicht die Sammlung des eShopKompass (ab Version 1.7.16)")
        return src.result()
    games = collection.from_eshop(d["games"])
    with store.lock:
        col = store.load_json(collection.FILE, collection.EMPTY)
        new, gone = collection.replace_eshop(col, games)
        store.save_json(collection.FILE, col)
    s2 = sum(1 for g in games.values() if g["system"] == "Switch 2")
    src.stats = {"read": len(games), "new": new}
    log(f"{label}: {len(games)} Spiele (Switch 2: {s2}), {new} neu" + (f", {gone} nicht mehr dabei" if gone else "")
        + f", eShopKompass {str(d.get('version') or '?')[:12]}, {_took(start)}")
    return src.result()


def _retro(log):
    """Retro-Fassungen: je System der Retro-Liste die Fassungsliste (No-Intro oder Redump aus der
    libretro-database) und die Retool-Liste, höchstens alle RETRO_DAYS Tage; dazwischen gilt die
    gespeicherte Fassung (retro_dat.json). Danach bekommt jedes Retro-Spiel „de“: deutsche
    Fassung vorhanden, fehlt (mit der gesuchten Fassung), gab es nicht oder unbekannt."""
    start = time.monotonic()
    label = NAMES["retro"]
    src = _Source(label, log)
    col = store.load_json(collection.FILE, collection.EMPTY)
    systems = sorted({g.get("system") for g in (col.get("games") or {}).values() if g.get("src") == retro.SRC})
    if not systems:
        log(f"{label}: keine Retro-Liste, nichts zu tun")
        return src.result()
    cache = store.load_json(retro.CACHE, {})
    old = _iso(now() - timedelta(days=RETRO_DAYS))
    fetched, without = [], [s for s in systems if not retro.urls(s)]
    for i, sy in enumerate(s for s in systems if retro.urls(s)):
        c = cache.get(sy) or {}
        if (c.get("at") or "") >= old and c.get("v") == retro.INDEX_V:
            continue
        progress(label, i, len(systems))
        dat_url, retool_url = retro.urls(sy)
        dat = src.get(dat_url, shown=f"Fassungsliste {sy}")
        if not dat:
            if src.stopped:
                break
            continue
        for j, u in enumerate(retro.extra_urls(sy)):
            more = src.get(u, shown=f"Fassungsliste {sy} ({j + 2})", absent=(404,))
            if more:
                dat += "\n" + more
        rt = src.get(retool_url, shown=f"Retool-Liste {sy}", absent=(404,)) or ""
        cache[sy] = {"at": titles.now_iso(), "v": retro.INDEX_V, "retool": bool(rt), "idx": retro.build_index(dat, rt)}
        fetched.append(sy)
    if fetched:
        store.save_json(retro.CACHE, cache)
    # Spielinfos (0.8.8): je System alle Listen der libretro-database, wenn ein Spiel noch keine hat oder nach META_DAYS
    meta = store.load_json(retro.META_FILE, {})
    old_meta = _iso(now() - timedelta(days=META_DAYS))
    found, metas = {}, []
    for sy in systems:
        if src.stopped or not retro.meta_urls(sy):
            continue
        m = meta.get(sy) or {}
        fresh = (m.get("at") or "") >= old_meta and m.get("v") == retro.META_V
        if fresh and all("lr" in g for g in (col.get("games") or {}).values() if g.get("src") == retro.SRC and g.get("system") == sy):
            continue
        entries = {}
        for f, u in retro.meta_urls(sy):
            text = src.get(u, shown=f"Spielinfos {sy} ({f})", absent=(404,))
            if text:
                retro.parse_meta(text, entries)
            elif src.stopped:
                break
        if src.stopped:
            break
        found[sy] = retro.meta_index(entries)
        meta[sy] = {"at": titles.now_iso(), "v": retro.META_V, "n": len(entries)}
        metas.append(sy)
    if metas:
        store.save_json(retro.META_FILE, meta)
    with store.lock:
        col = store.load_json(collection.FILE, collection.EMPTY)
        count = retro.mark_languages(col, {sy: c["idx"] for sy, c in cache.items() if sy in systems and c.get("idx")})
        got = retro.mark_meta(col, found) if found else (0, 0)
        store.save_json(collection.FILE, col)
    near = sum(1 for g in (col.get("games") or {}).values() if (g.get("de") or {}).get("near"))
    src.stats = {"read": len(fetched), "missing": count.get("missing", 0), "near": near}
    log(f"{label}: " + (f"Listen neu gelesen für {', '.join(fetched)}" if fetched else "Listen aktuell")
        + f"; Deutsch vorhanden {count.get('have', 0)}, deutsche Fassung fehlt {count.get('missing', 0)}, "
        f"keine deutsche Fassung bekannt {count.get('none', 0)}, nicht in der Liste {count.get('unknown', 0)}"
        + (f" (davon {near} mit ähnlichem Namen zum Bestätigen)" if near else "")
        + (f"; ohne Fassungsliste: {', '.join(without)}" if without else "")
        + (f"; Spielinfos (libretro) neu für {', '.join(metas)}: {got[0]} von {got[1]} Spielen gefunden" if metas else "")
        + f", {_took(start)}")
    return src.result()


def _rating(log):
    """Steam-Rezensionen für die Titel des Tools (Wunschliste, Bibliothek) mit Steam-ID, damit
    neben den Meta-Sternen die Steam-Wertung steht. Was Entdecken für dasselbe Spiel schon
    geholt hat, wird übernommen statt neu gefragt. Nach REVIEWS_DAYS neu."""
    start = time.monotonic()
    old = _iso(now() - timedelta(days=REVIEWS_DAYS))
    col = (store.load_json(collection.FILE, collection.EMPTY).get("games") or {})
    data = store.load_data()
    todo = sorted(((t.get("rev") or {}).get("at") or "", k) for k, t in data["titles"].items()
                  if str(t.get("steam_appid") or "").isdigit()
                  and (((t.get("rev") or {}).get("at") or "") < old or (t.get("rev") or {}).get("app") != str(t["steam_appid"])))
    src = _Source("Steam-Wertungen", log)
    revs = {k: t["rev"] for k, t in data["titles"].items() if t.get("rev") and str(t.get("steam_appid") or "").isdigit()}
    if not todo and not _trend_due(revs):
        log("Steam-Wertungen: alle aktuell")
        return src.result()
    got, asked = {}, 0
    for _, k in todo:
        gid = str(data["titles"][k]["steam_appid"])
        rev = (col.get("steam:" + gid) or {}).get("rev") or {}
        if (rev.get("at") or "") >= old:
            got[k] = dict(rev, app=gid)     # schon von Entdecken geholt
            continue
        if asked >= RATING_MAX:
            continue
        progress("Steam-Wertungen", asked, min(RATING_MAX, len(todo)))
        asked += 1
        text = _rev_get(src, gid, f"Steam-Wertungen {gid}")
        if text is None:
            if src.stopped:
                break
            continue
        got[k] = dict(prices.steam_reviews(text) or {"n": None, "pct": None, "desc": ""}, at=titles.now_iso(), app=gid)
        rc = _recent_get(src, gid) if (got[k].get("n") or 0) >= trend.MIN_ALL else None
        if rc:
            got[k]["recent"] = rc
    # Trend auch für Titel, deren Rezensionszahl noch frisch ist (0.8.21)
    tdue = _trend_due(revs, skip=got) if not src.stopped else []
    rec = _trend_fill(src, tdue, lambda k: str(data["titles"][k]["steam_appid"]), "Steam-Trend")
    with store.lock:
        data = store.load_data()
        for k, r in got.items():
            if k in data["titles"]:
                t = data["titles"][k]
                t["rev"] = trend.keep(t.get("rev") if (t.get("rev") or {}).get("app") == r.get("app") else None, r)
        for k, rc in rec.items():
            if (data["titles"].get(k) or {}).get("rev"):
                data["titles"][k]["rev"]["recent"] = rc
        store.save_data(data)
    left = len(todo) - len(got)
    src.stats = {"read": len(got), "left": left, "trend": len(rec)}
    log(f"Steam-Wertungen: {len(got)} Titel aktualisiert ({asked} Anfragen)"
        + (f", Trend für {len(rec)} Titel" + (f" ({len(tdue) - len(rec)} offen)" if len(tdue) > len(rec) else "") if tdue else "")
        + (f", {left} noch offen (je Lauf {RATING_MAX}{_runs(left, RATING_MAX, ", ")})" if left else ", alle aktuell") + f", {_took(start)}")
    return src.result()


def _mine(t):
    """Titel, für die sich Messwerte lohnen: Wunschliste oder Besitz."""
    return t.get("wish") or t.get("owned")


def _vrdb_url(t):
    link = (t.get("links") or {}).get("vrdb") or ""
    if link.startswith(VRDB + "/game/"):
        return link
    path = ((t.get("live") or {}).get("meta") or {}).get("path") or ""
    m = re.search(r"/(?:game|app)/([a-z0-9-]+?)-\d{6,}/", path)
    slug = m.group(1) if m else re.sub(r"[^a-z0-9]+", "-", titles.norm(t["name"])).strip("-") or "x"
    return f"{VRDB}/game/{slug}/{t['meta_id']}"


def _vrdb(log):
    """VRDB-Titelseiten für Titel mit Meta-ID: Crossbuy, Version, Meta-Wertung als Anteil 4 und 5
    Sterne. Ändert sich die Version, merkt sich das Tool den Tag (meta_ver). Nach VRDB_DAYS neu."""
    start, stamp = time.monotonic(), titles.now_iso()
    old = _iso(now() - timedelta(days=VRDB_DAYS))
    data = store.load_data()
    todo = sorted(((t.get("vrdb") or {}).get("at") or "", k) for k, t in data["titles"].items()
                  if _mine(t) and t.get("meta_id") and ((t.get("vrdb") or {}).get("at") or "") < old)
    src = _Source("VRDB", log)
    if not todo:
        log("VRDB: alle aktuell")
        return src.result()
    got = {}
    for i, (_, k) in enumerate(todo[:VRDB_MAX]):
        progress("VRDB", i, min(VRDB_MAX, len(todo)))
        t = data["titles"][k]
        text = src.get(_vrdb_url(t), shown=f"VRDB {t['meta_id']}")
        if text is None:
            if src.stopped:
                break
            got[k] = {"at": stamp, "miss": True}      # nicht gefunden: erst nach VRDB_DAYS wieder
            continue
        got[k] = dict(prices.vrdb_game(text) or {"miss": True}, at=stamp)
    today = stamp[:10]
    with store.lock:
        data = store.load_data()
        for k, r in got.items():
            t = data["titles"].get(k)
            if t is None:
                continue
            t["vrdb"] = r
            v = r.get("version") or ""
            mv = t.get("meta_ver") or {}
            if v and v != mv.get("v"):
                # erste Sicht: Tag unbekannt; danach der Tag, an dem die neue Version auftauchte
                t["meta_ver"] = {"v": v, "since": today if mv.get("v") else ""}
        store.save_data(data)
    left = len(todo) - len(got)
    found = sum(1 for r in got.values() if not r.get("miss"))
    src.stats = {"read": found, "left": left}
    log(f"VRDB: {found} Seiten gelesen, {len(got) - found} ohne Treffer"
        + (f", {left} noch offen (je Lauf {VRDB_MAX}{_runs(left, VRDB_MAX, ", ")})" if left else ", alle aktuell") + f", {_took(start)}")
    return src.result()


def _players(log):
    """Steam: Spieler gerade jetzt (Spitze über PEAK_DAYS Tage aus den eigenen Messungen) und das
    letzte Update laut Neuigkeiten des Entwicklers. Für Titel mit Steam-ID auf Wunschliste oder
    im Besitz; Spielerzahl nach PLAYERS_H Stunden, Neuigkeiten nach NEWS_DAYS Tagen neu."""
    start, stamp = time.monotonic(), titles.now_iso()
    old_p, old_n = _iso(now() - timedelta(hours=PLAYERS_H)), _iso(now() - timedelta(days=NEWS_DAYS))
    data = store.load_data()
    todo = sorted(((t.get("play") or {}).get("at") or "", k) for k, t in data["titles"].items()
                  if _mine(t) and str(t.get("steam_appid") or "").isdigit()
                  and (((t.get("play") or {}).get("at") or "") < old_p or ((t.get("news") or {}).get("at") or "") < old_n))
    src = _Source("Steam-Spieler", log)
    if not todo:
        log("Steam-Spieler: alle aktuell")
        return src.result()
    got = {}
    for i, (_, k) in enumerate(todo[:PLAYERS_MAX]):
        progress("Steam-Spieler", i, min(PLAYERS_MAX, len(todo)))
        t, gid = data["titles"][k], str(data["titles"][k]["steam_appid"])
        r = got.setdefault(k, {})
        if ((t.get("play") or {}).get("at") or "") < old_p:
            # 404: Steam kennt für diese App keine Spielerzahl (unveröffentlicht, Demo); gilt als
            # gefragt, beim nächsten Mal nach PLAYERS_H Stunden
            text = src.get(f"{STEAM_API}/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={gid}",
                           shown=f"Spieler {gid}", absent=(404,))
            if text is not None:
                r["now"] = prices.steam_players(text)
        if src.stopped:
            break
        if ((t.get("news") or {}).get("at") or "") < old_n:
            text = src.get(f"{STEAM_API}/ISteamNews/GetNewsForApp/v2/?appid={gid}&count=20&maxlength=1", shown=f"Neuigkeiten {gid}")
            if text is not None:
                n = prices.steam_news(text)
                if n is not None:
                    r["news"] = n
        if src.stopped:
            break
    today, cut = stamp[:10], (now() - timedelta(days=PEAK_DAYS)).strftime("%Y-%m-%d")
    with store.lock:
        data = store.load_data()
        for k, r in got.items():
            t = data["titles"].get(k)
            if t is None:
                continue
            if "now" in r:
                p = t.get("play") or {}
                days = {d: n for d, n in (p.get("days") or []) if isinstance(d, str) and d >= cut}
                if r["now"] is not None:
                    days[today] = max(days.get(today, 0), r["now"])
                peak = max(days.items(), key=lambda x: x[1], default=(None, None))
                t["play"] = {"now": r["now"], "at": stamp, "days": sorted(days.items()),
                             "peak": peak[1], "peak_at": peak[0], "since": min(days, default=today)}
            if "news" in r:
                t["news"] = dict(r["news"], at=stamp)
        store.save_data(data)
    left = max(0, len(todo) - len(got))
    src.stats = {"read": len(got), "left": left}
    none = sum(1 for r in got.values() if "now" in r and r["now"] is None)
    log(f"Steam-Spieler: {sum(1 for r in got.values() if r.get('now') is not None)} Spielerzahlen"
        + (f" ({none} Apps ohne Zahl bei Steam)" if none else "")
        + f", {sum(1 for r in got.values() if (r.get('news') or {}).get('date'))} Update-Daten"
        + (f", {left} noch offen{_runs(left, PLAYERS_MAX)}" if left else "") + f", {_took(start)}")
    return src.result()


def _active(log):
    """Aktive Steam-Spieler für PC-Spiele (0.8.23): gerade eben laut GetNumberOfCurrentPlayers, je Spiel unter play
    ({"now", "at"}), nach ACTIVE_DAYS Tagen neu. Erst die PC-Wunschliste (pcwish.json), mit dem Rest des Kontingents
    die Steam-Spiele der Sammlung (collection.json). Die VR-Titel misst _players öfter und mit Spitze."""
    start, old = time.monotonic(), _iso(now() - timedelta(days=ACTIVE_DAYS))
    url = lambda gid: f"{STEAM_API}/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid={gid}"
    # 404: Steam kennt für diese App keine Zahl (unveröffentlicht, Demo); gilt als gefragt
    get = lambda src, gid, shown: src.get(url(gid), shown=shown, absent=(404,))
    pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
    todo = sorted(((e.get("play") or {}).get("at") or "", k) for k, e in (pw.get("items") or {}).items()
                  if str(e.get("appid") or "").isdigit() and not e.get("kind") and ((e.get("play") or {}).get("at") or "") < old)
    src, got = _Source("Aktive Spieler PC", log), {}
    for i, (_, k) in enumerate(todo[:ACTIVE_MAX]):
        progress("Aktive Spieler PC", i, min(ACTIVE_MAX, len(todo)))
        gid = str(pw["items"][k]["appid"])
        text = get(src, gid, f"Spieler {gid}")
        if text is not None:
            got[k] = {"now": prices.steam_players(text), "at": titles.now_iso()}
        if src.stopped:
            break
    if got:
        with store.lock:
            pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
            for k, r in got.items():
                if k in (pw.get("items") or {}):
                    pw["items"][k]["play"] = r
            store.save_json(pcwish.FILE, pw)
    wleft = len(todo) - len(got)
    cgot, cleft = {}, 0
    rest = ACTIVE_MAX - len(got)
    if rest > 0 and not src.stopped:
        _, cgot, cleft = _per_game(log, "Aktive Spieler PC", "play", ACTIVE_DAYS, rest, url,
                                   lambda text, gid: {"now": prices.steam_players(text)}, get=get, src=src)
        cgot = cgot or {}
    else:
        col = store.load_json(collection.FILE, collection.EMPTY)
        cleft = sum(1 for g in (col.get("games") or {}).values() if g.get("store") == "Steam" and str(g.get("id") or "").isdigit()
                    and ((g.get("play") or {}).get("at") or "") < old)
    left = wleft + cleft
    src.stats = {"read": len(got) + len(cgot), "left": left}
    if not todo and not cgot and not left:
        log("Aktive Spieler PC: alle aktuell")
    else:
        log(f"Aktive Spieler PC: {len(got)} Wünsche, {len(cgot)} Spiele der Sammlung"
            + (f", {left} noch offen{_runs(left, ACTIVE_MAX)}" if left else ", alle aktuell") + f", {_took(start)}")
    return src.result()


def _checked(d):
    return dict(d, ok=True) if d else {"ok": False}


def _details(log):
    """Steam-Store-Daten je Steam-Spiel: Genres, Mehrspieler-Arten, Erscheinungsjahr, VR. Damit
    prüft Entdecken, was Playnite sagt (beide gleich: bestätigt). Nach DETAILS_DAYS neu."""
    start = time.monotonic()
    src, got, left = _per_game(
        log, "Steam-Details", "steam", DETAILS_DAYS, DETAILS_MAX,
        lambda gid: f"{STEAM}/api/appdetails?appids={gid}&l=german&cc=de",
        lambda text, gid: _checked(prices.steam_details(text, gid)),
        # Ältere Einträge (vor 0.7.1) ohne Beschreibung und Metacritic kommen erneut dran
        stale=lambda r: bool(r) and r.get("ok") and r.get("v", 1) < prices.DETAILS_V)
    if got is not None:
        ok = sum(1 for r in got.values() if r.get("ok"))
        log(f"Steam-Details: {len(got)} Spiele gelesen, {ok} im Store"
            + (f", {left} noch offen (je Lauf {DETAILS_MAX}{_runs(left, DETAILS_MAX, ", ")})" if left else ", alle aktuell") + f", {_took(start)}")
    return src.result()


def _own_title(g):
    """Retro (0.8.16): dein Titel aus der Ordner-Liste, wenn er vom Namen der Datei abweicht, sonst ""."""
    t = retro.article_front(str((g.get("own") or {}).get("title") or "")).strip()
    return t if g.get("src") == retro.SRC and t and titles.norm(t) != titles.norm(g.get("name") or "") else ""


def _igdb(settings, log):
    """IGDB (0.8.0): Genre, Spieler, Wertung, Spielzeit, Beschreibung und Firmen je Spiel der Sammlung, für die
    Spalten aller Reiter. Steam-Spiele gebündelt über die Steam-ID, die übrigen über Name und System
    (höchstens IGDB_NAMES je Lauf). Switch-Spiele aus dem eShopKompass bringen ihre Angaben selbst mit."""
    start = time.monotonic()
    src = _Source("IGDB", log, pause=IGDB_PAUSE)
    col = store.load_json(collection.FILE, collection.EMPTY)
    games = col.get("games") or {}
    old, old_miss = _iso(now() - timedelta(days=IGDB_DAYS)), _iso(now() - timedelta(days=IGDB_MISS_DAYS))

    def due(g):
        r = g.get("igdb")
        if g.get("src") == collection.ESHOP:
            return False
        if not r or r.get("v") != igdb.V:
            return True
        if r.get("none") and _own_title(g) and not r.get("own"):
            return True                 # 0.8.16: mit dem Titel aus deiner Ordner-Liste noch nicht gesucht
        return (r.get("at") or "") < (old_miss if r.get("none") else old)
    todo = sorted(((g.get("igdb") or {}).get("at") or "", k) for k, g in games.items() if due(g))
    # 0.8.9: Bei gleichem Stand zuerst deine VR-Titel am PC, dann abwechselnd Retro und die übrigen, damit Retro nicht
    # hinter allen PC-Spielen wartet
    seen = {}

    def turn(k):
        g = games[k]
        grp = 0 if g.get("src") == collection.PCVR else 1 if g.get("src") == retro.SRC else 2
        seen[grp] = seen.get(grp, -1) + 1
        return (0, seen[grp]) if grp == 0 else (1, seen[grp] * 2 + (grp == 2))
    todo = sorted(todo, key=lambda x: (x[0], turn(x[1])))
    if not todo:
        log("IGDB: alle aktuell" if games else "IGDB: keine Sammlung, nichts zu tun")
        return src.result()
    text = src.get(igdb.TWITCH, shown="Twitch-Anmeldung", data=igdb.token_body(settings["igdb_id"], settings["igdb_secret"]))
    tok = igdb.token(text)
    if not tok:
        if not src.stopped:
            src.stopped = "keine Anmeldung"
            log("IGDB: Twitch nimmt den Schlüssel nicht an; Client-ID und Secret in den Einstellungen prüfen")
        return src.result()
    src.headers = {"Client-ID": settings["igdb_id"], "Authorization": f"Bearer {tok}", "Accept": "application/json"}

    def ask(path, body, shown):
        t = src.get(igdb.API + path, shown=shown, data=body.encode())
        try:
            return None if t is None else json.loads(t or "[]")
        except ValueError:
            return None
    got, unlinked = {}, []
    steam = [k for _, k in todo if games[k].get("store") == "Steam" and str(games[k].get("id") or "").isdigit()
             and (games[k].get("system") or "PC") == "PC"]
    for part in igdb.chunks(steam):
        progress("IGDB, Steam-IDs", len(got), len(steam))
        ids = [games[k]["id"] for k in part]
        ext = ask("external_games", igdb.steam_query(ids), "Steam-IDs")
        if ext == []:
            ext = ask("external_games", igdb.steam_query(ids, old=True), "Steam-IDs")
        if ext is None:
            break
        of = {str(e.get("uid")): e.get("game") for e in ext if isinstance(e, dict) and e.get("game")}
        found = ask("games", igdb.games_query(sorted(set(of.values()))), "Spiele zu Steam-IDs") if of else []
        if found is None:
            break
        by = {g.get("id"): g for g in found if isinstance(g, dict)}
        for k in part:
            hit = by.get(of.get(str(games[k]["id"])))
            if hit:
                got[k] = igdb.compact(hit)
            else:
                unlinked.append(k)
    # Ohne Steam-ID, danach Steam-Spiele, die IGDB nicht mit der Steam-ID verknüpft hat: über den Namen
    names = [k for _, k in todo if k not in steam] + unlinked
    left = max(0, len(names) - IGDB_NAMES)
    tried_own = set()
    for i, k in enumerate(names[:IGDB_NAMES]):
        if src.stopped:
            break
        progress("IGDB, Namen", i, min(len(names), IGDB_NAMES))
        g, hit, res = games[k], None, None
        own = _own_title(g)
        for name, alt in [(g["name"], False)] + ([(own, True)] if own else []):
            for body in igdb.name_queries(name, g.get("system") or "PC"):
                res = ask("games", body, f"„{name[:40]}“")
                if res is None:
                    break
                hit = igdb.pick(res, name, alt)
                if hit:
                    break
            if hit or res is None:
                break
        if res is None and not hit:
            continue                    # Fehler: nicht als „kein Treffer“ merken
        got[k] = igdb.compact(hit) if hit else None
        if own:
            tried_own.add(k)
    ids = sorted({r["id"] for r in got.values() if r and r.get("id")})
    hours = {}
    for part in igdb.chunks(ids):
        if src.stopped:
            break
        t = ask("game_time_to_beats", igdb.times_query(part), "Spielzeiten")
        hours.update(igdb.times(t))
    stamp = titles.now_iso()
    with store.lock:
        col = store.load_json(collection.FILE, collection.EMPTY)
        for k, r in got.items():
            if k in col.get("games", {}):
                if r and hours.get(r["id"]):
                    r["hours"] = hours[r["id"]]
                col["games"][k]["igdb"] = dict(r, at=stamp, v=igdb.V) if r else dict({"none": True, "at": stamp, "v": igdb.V},
                                                                                      **({"own": True} if k in tried_own else {}))
        store.save_json(collection.FILE, col)
    hit = sum(1 for r in got.values() if r)
    src.stats = {"read": len(got), "found": hit, "left": left}
    log(f"IGDB: {len(got)} Spiele gelesen, {hit} gefunden ({sum(1 for k, r in got.items() if r and k in steam and k not in unlinked)} über die Steam-ID), "
        f"{sum(1 for r in got.values() if r and r.get('hours'))} mit Spielzeit"
        + (f", {left} Namen noch offen (je Lauf {IGDB_NAMES}{_runs(left, IGDB_NAMES, ', ')})" if left else "") + f", {_took(start)}")
    return src.result()


def _pcwish(settings, log):
    """PC-Wunschliste (0.8.2): Steam-ID je Spiel (erst aus dem, was das Tool kennt, dann Steam-Suche mit genau
    gleichem Namen, PCWISH_SEARCH je Lauf), dann die Preise über die gg.deals-API (mit Schlüssel)."""
    start = time.monotonic()
    pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
    items = pw.get("items") or {}
    src = _Source("PC-Wunschliste", log)
    if not items:
        log("PC-Wunschliste: noch keine gg.deals-Wunschliste gelesen")
        return src.result()
    idx = pcwish.steam_index(store.load_data(), store.load_json(collection.FILE, collection.EMPTY))
    ids, found = {}, 0
    for k, e in items.items():
        if not e.get("appid") and not e.get("kind") and idx.get(titles.norm(e["name"])):
            ids[k] = idx[titles.norm(e["name"])]
    old = _iso(now() - timedelta(days=MISS_DAYS))
    # Pakete und DLC (0.8.7) haben keine eigene App bei Steam: keine Suche, Preise nur über die Seite bei gg.deals
    # Erst die nie gesuchten, dann die am längsten nicht gesuchten; Vorschläge zur Wahl warten auf dich
    todo = sorted((k for k, e in items.items() if not e.get("appid") and not e.get("kind") and k not in ids
                   and not e.get("cand") and (e.get("tried") or "") < old), key=lambda k: items[k].get("tried") or "")
    tried, near, cand, searches = {}, {}, {}, 0
    for k in todo:
        if searches >= PCWISH_SEARCH or src.stopped:
            break
        progress("PC-Wunschliste: Steam-IDs", searches, PCWISH_SEARCH)
        name, no = items[k]["name"], set(items[k].get("no_ids") or [])
        # 0.8.24: Suche ohne störende Zeichen, sonst mit der Grundform; Treffer nach pcwish.pick
        terms = [pcwish.search_term(name)]
        base = pcwish.search_term(re.split(r"\s+[/|]\s+", pcwish.search_term(name))[0])
        base = pcwish._EDITION.sub("", base).strip()
        if base and titles.norm(base) != titles.norm(terms[0]):
            terms.append(base)
        found_here, p = {}, {}
        for term in terms:
            if searches >= PCWISH_SEARCH:
                break
            text = src.get(f"{STEAM}/api/storesearch/?" + urllib.parse.urlencode({"term": term, "l": "german", "cc": "DE"}),
                           shown=f"Steam-Suche „{term[:40]}“")
            searches += 1
            if text is None:
                break
            tried[k] = titles.now_iso()
            hits = {i["appid"]: i for i in prices.steam_search(text)}
            found_here.update(hits)
            p = pcwish.pick(name, list(found_here.values()), no)
            if p.get("appid"):
                break
        if p.get("appid"):
            ids[k] = p["appid"]
            if p["how"] == "near":
                near[k] = found_here[p["appid"]]["name"]
        elif p.get("cands"):
            cand[k] = p["cands"]
    got = {}
    if settings["gg_key"]:
        apps = {}
        for k, e in items.items():
            a = ids.get(k) or e.get("appid")
            if a:
                apps.setdefault(str(a), []).append(k)
        gg = _Source("gg.deals", log)
        al = list(apps)
        for i in range(0, len(al), 100):
            q = urllib.parse.urlencode({"ids": ",".join(al[i:i + 100]), "region": "de"})
            text = gg.get(f"{GG_API}?{q}&key={urllib.parse.quote(settings['gg_key'])}", shown=f"{GG_API}?{q}")
            if text is None:
                continue
            try:
                p = prices.gg_prices(text)
            except ValueError as e:
                log(str(e))
                break
            stamp = titles.now_iso()
            for a, v in p.items():
                for k in apps.get(a, []):
                    got[k] = dict(v, at=stamp)
        src.n += gg.n
    with store.lock:
        pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
        for k, e in (pw.get("items") or {}).items():
            if k in ids and not e.get("appid"):
                e["appid"] = ids[k]
                found += 1
                if k in near:
                    e.update(id_near=True, id_name=near[k])
            if k in cand and not e.get("appid"):
                e["cand"] = cand[k]
            if k in tried:
                e["tried"] = tried[k]
            if k in got:
                e["gg"] = got[k]
                pcwish.record(e, got[k])
        store.save_json(pcwish.FILE, pw)
    noid = sum(1 for k, e in items.items() if not e.get("appid") and k not in ids)
    log(f"PC-Wunschliste: {len(items)} Spiele, {found} Steam-IDs neu zugeordnet ({searches} Steam-Suchen"
        + (f", {len(near)} nach der Grundform des Namens" if near else "") + (f", {len(cand)} mit Vorschlägen zur Wahl" if cand else "")
        + "), "
        + (f"{len(got)} mit Preis von gg.deals" if settings["gg_key"] else "ohne gg.deals-Schlüssel keine Preise")
        + (f", {noid} ohne Steam-ID" if noid else "") + f", {_took(start)}")
    src.stats = {"items": len(items), "priced": len(got), "noid": noid}
    return src.result()


def _itad(settings, log):
    """Preise je Laden für die PC-Wunschliste (0.9.0): ITAD-Kennung je Steam-ID (einmal, nicht gefundene nach
    MISS_DAYS neu), dann die Preise aller offiziellen Läden in Deutschland, je CHUNK Spiele ein Abruf. Abgelegt je
    Spiel in pcwish.json unter itad."""
    start = time.monotonic()
    pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
    items = pw.get("items") or {}
    src = _Source("IsThereAnyDeal", log, headers=itad.headers(settings["itad_key"]), pause=ITAD_PAUSE)
    old = _iso(now() - timedelta(days=MISS_DAYS))
    ask = sorted({str(e["appid"]) for e in items.values() if e.get("appid") and not e.get("itad_id")
                  and (e.get("itad_tried") or "") < old})
    ids, tried = {}, {}
    for i in range(0, len(ask), itad.CHUNK):
        text = src.get(itad.lookup_url(), shown="Zuordnung zu Steam-IDs", data=itad.lookup_body(ask[i:i + itad.CHUNK]))
        if text is None:
            break
        try:
            got = itad.lookup(text)
        except ValueError as e:
            log(str(e))
            break
        stamp = titles.now_iso()
        for a in ask[i:i + itad.CHUNK]:
            tried[a] = stamp
            if got.get(a):
                ids[a] = got[a]
    known = {}
    for e in items.values():
        g = e.get("itad_id") or ids.get(str(e.get("appid") or ""))
        if g:
            known.setdefault(g, []).append(e)
    got, gl = {}, list(known)
    for i in range(0, len(gl), itad.CHUNK):
        if src.stopped:
            break
        text = src.get(itad.prices_url(), shown="Preise je Laden", data=json.dumps(gl[i:i + itad.CHUNK]).encode())
        if text is None:
            continue
        try:
            got.update(itad.prices(text))
        except ValueError as e:
            log(str(e))
            break
    # 0.9.1: einmal je Spiel der Verlauf je Laden der letzten 24 Monate, danach führt das Tool ihn selbst fort
    since = (now() - timedelta(days=verlauf.MONTHS * 31)).date().isoformat()
    back = {}
    for g in [g for g, es in known.items() if not any(e.get("sh_at") for e in es)][:ITAD_HIST]:
        if src.stopped:
            break
        progress("IsThereAnyDeal: Verlauf je Laden", len(back), ITAD_HIST)
        text = src.get(itad.history_url(g, since), shown="Verlauf je Laden")
        if text is None:
            continue
        try:
            back[g] = itad.history(text)
        except ValueError as e:
            log(str(e))
            break
    stamp = titles.now_iso()
    day = now().strftime("%Y-%m-%d")
    with store.lock:
        pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
        for e in (pw.get("items") or {}).values():
            a = str(e.get("appid") or "")
            if a in tried and not e.get("itad_id"):
                e["itad_tried"] = tried[a]
                if ids.get(a):
                    e["itad_id"] = ids[a]
                    e.pop("itad_tried", None)
            g = e.get("itad_id")
            if g in back:
                verlauf.merge_history(e, back[g])
                e["sh_at"] = stamp
            if g in got:
                e["itad"] = dict(got[g], at=stamp)
                verlauf.record_shops(e, got[g], day)
        store.save_json(pcwish.FILE, pw)
    shops = sum(len(v["shops"]) for v in got.values())
    log(f"IsThereAnyDeal: {len(ids)} Spiele neu zugeordnet ({len(ask)} gefragt), Preise für {len(got)} Spiele"
        f" aus {shops} Angeboten der Läden" + (f", Verlauf je Laden für {len(back)} Spiele nachgeholt" if back else "") + f", {_took(start)}")
    src.stats = {"priced": len(got), "shops": shops}
    return src.result()


def _pcwish_info(settings, log):
    """Spielinfos der PC-Wunschliste (0.8.11) über die Steam-ID: Steam-Details (Genres, Mehrspieler, Jahr, Beschreibung)
    und Rezensionen, höchstens PCWISH_INFO Spiele je Lauf, nach DETAILS_DAYS und REVIEWS_DAYS neu; mit IGDB-Schlüssel
    dazu IGDB gebündelt über die Steam-IDs (Spieler, Spielzeit, Kritiken), nach IGDB_DAYS neu. Abgelegt je Spiel in
    pcwish.json unter steam, rev und igdb."""
    start = time.monotonic()
    pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
    items = {k: e for k, e in (pw.get("items") or {}).items() if str(e.get("appid") or "").isdigit() and not e.get("kind")}
    src = _Source("PC-Wunschliste, Spielinfos", log)
    if not items:
        log("PC-Wunschliste, Spielinfos: keine Spiele mit Steam-ID")
        return src.result()
    old_d, old_r, old_i, old_n = (_iso(now() - timedelta(days=d)) for d in (DETAILS_DAYS, REVIEWS_DAYS, IGDB_DAYS, NEWS_DAYS))
    at = lambda e, f: (e.get(f) or {}).get("at") or ""
    todo = sorted((min(at(e, "steam"), at(e, "rev"), at(e, "news")), k) for k, e in items.items()
                  if at(e, "steam") < old_d or at(e, "rev") < old_r or at(e, "news") < old_n
                  or ((e.get("steam") or {}).get("ok") and (e["steam"].get("v", 1) < prices.DETAILS_V)))
    got = {}
    for i, (_, k) in enumerate(todo[:PCWISH_INFO]):
        progress("PC-Wunschliste, Spielinfos", i, min(len(todo), PCWISH_INFO))
        e, gid, r = items[k], str(items[k]["appid"]), {}
        if at(e, "steam") < old_d or (e.get("steam") or {}).get("v", 1) < prices.DETAILS_V:
            text = src.get(f"{STEAM}/api/appdetails?appids={gid}&l=german&cc=de", shown=f"Steam-Details {gid}")
            if text is not None:
                r["steam"] = dict(_checked(prices.steam_details(text, gid)), at=titles.now_iso())
        if src.stopped:
            break
        if at(e, "rev") < old_r:
            text = _rev_get(src, gid, f"Steam-Rezensionen {gid}")
            if text is not None:
                r["rev"] = trend.keep(e.get("rev"), dict(prices.steam_reviews(text) or {"n": None, "pct": None, "desc": ""}, at=titles.now_iso()))
                rc = _recent_get(src, gid) if (r["rev"].get("n") or 0) >= trend.MIN_ALL else None
                if rc:
                    r["rev"]["recent"] = rc
        if src.stopped:
            break
        # Pflege (0.8.18): letztes Update laut Neuigkeiten des Entwicklers, nach NEWS_DAYS neu
        if at(e, "news") < old_n:
            text = src.get(f"{STEAM_API}/ISteamNews/GetNewsForApp/v2/?appid={gid}&count=20&maxlength=1", shown=f"Neuigkeiten {gid}")
            n = prices.steam_news(text) if text is not None else None
            if n is not None:
                r["news"] = dict(n, at=titles.now_iso())
        if r:
            got[k] = r
        if src.stopped:
            break
    # Trend auch für Spiele, deren Rezensionszahl noch frisch ist (0.8.21)
    tdue = _trend_due({k: e["rev"] for k, e in items.items() if e.get("rev")}, skip={k for k, r in got.items() if "rev" in r}) if not src.stopped else []
    rec = _trend_fill(src, tdue, lambda k: str(items[k]["appid"]), "PC-Wunschliste, Trend")
    ig = {}
    if settings.get("igdb_id") and settings.get("igdb_secret") and not src.stopped:
        due = {k: str(e["appid"]) for k, e in items.items() if at(e, "igdb") < old_i or (e.get("igdb") or {}).get("v") != igdb.V}
        if due:
            isrc = _Source("IGDB", log, pause=IGDB_PAUSE)
            tok = igdb.token(isrc.get(igdb.TWITCH, shown="Twitch-Anmeldung", data=igdb.token_body(settings["igdb_id"], settings["igdb_secret"])))
            if tok:
                isrc.headers = {"Client-ID": settings["igdb_id"], "Authorization": f"Bearer {tok}", "Accept": "application/json"}

                def ask(path, body, shown):
                    t = isrc.get(igdb.API + path, shown=shown, data=body.encode())
                    try:
                        return None if t is None else json.loads(t or "[]")
                    except ValueError:
                        return None
                keys = list(due)
                for part in igdb.chunks(keys):
                    ids = [due[k] for k in part]
                    ext = ask("external_games", igdb.steam_query(ids), "Steam-IDs der PC-Wunschliste")
                    if ext == []:
                        ext = ask("external_games", igdb.steam_query(ids, old=True), "Steam-IDs der PC-Wunschliste")
                    if ext is None:
                        break
                    of = {str(x.get("uid")): x.get("game") for x in ext if isinstance(x, dict) and x.get("game")}
                    found = ask("games", igdb.games_query(sorted(set(of.values()))), "Spiele zu Steam-IDs") if of else []
                    if found is None:
                        break
                    by = {g.get("id"): g for g in found if isinstance(g, dict)}
                    hours = igdb.times(ask("game_time_to_beats", igdb.times_query(sorted(by)), "Spielzeiten")) if by else {}
                    stamp = titles.now_iso()
                    for k in part:
                        hit = by.get(of.get(due[k]))
                        c = igdb.compact(hit) if hit else None
                        if c and hours.get(c["id"]):
                            c["hours"] = hours[c["id"]]
                        ig[k] = dict(c, at=stamp, v=igdb.V) if c else {"none": True, "at": stamp, "v": igdb.V}
            src.n += isrc.n
    with store.lock:
        pw = store.load_json(pcwish.FILE, pcwish.EMPTY)
        for k, e in (pw.get("items") or {}).items():
            e.update(got.get(k) or {})
            if k in rec and e.get("rev"):
                e["rev"]["recent"] = rec[k]
            if k in ig:
                e["igdb"] = ig[k]
        store.save_json(pcwish.FILE, pw)
    left = max(0, len(todo) - len(got))
    src.stats = {"read": len(got), "left": left, "igdb": sum(1 for r in ig.values() if r.get("id")), "trend": len(rec)}
    log(f"PC-Wunschliste, Spielinfos: {len(got)} Spiele bei Steam gelesen"
        + (f", Trend für {len(rec)}" + (f" ({len(tdue) - len(rec)} offen)" if len(tdue) > len(rec) else "") if tdue else "")
        + (f", IGDB {src.stats['igdb']} von {len(ig)} gefunden" if ig else "")
        + (f", {left} noch offen (je Lauf {PCWISH_INFO}{_runs(left, PCWISH_INFO, ', ')})" if left else ", alle aktuell") + f", {_took(start)}")
    return src.result()


def _vr_info(settings, log):
    """Spielinfos der VR-Titel (0.9.4) wie bei der PC-Wunschliste: Steam-Details über die Steam-ID (Genres,
    Mehrspieler, Jahr, Beschreibung), höchstens VRINFO_MAX je Lauf, nach DETAILS_DAYS neu; mit IGDB-Schlüssel IGDB
    gebündelt über die Steam-IDs, Titel ohne Steam-ID über den Namen (höchstens VRINFO_NAMES je Lauf). Abgelegt je
    Titel in data.json unter sdet und igdb; die Zeile rechnet sie wie die Sammlung zusammen (library.info)."""
    start = time.monotonic()
    data = store.load_data()
    src = _Source("VR-Titel, Spielinfos", log)
    old_d, old_i, old_m = (_iso(now() - timedelta(days=d)) for d in (DETAILS_DAYS, IGDB_DAYS, IGDB_MISS_DAYS))
    at = lambda t, f: (t.get(f) or {}).get("at") or ""
    sid = lambda t: str(t.get("steam_appid") or "")
    # Gilt nur für die Steam-ID, zu der sie gelesen wurden (app); eine geänderte ID liest neu
    moved = lambda t, f: (t.get(f) or {}).get("app", sid(t)) != sid(t)
    todo = sorted((at(t, "sdet"), k) for k, t in data["titles"].items() if sid(t).isdigit() and not t.get("contains")
                  and (at(t, "sdet") < old_d or moved(t, "sdet") or ((t.get("sdet") or {}).get("ok") and t["sdet"].get("v", 1) < prices.DETAILS_V)))
    got = {}
    for i, (_, k) in enumerate(todo[:VRINFO_MAX]):
        progress("VR-Titel, Spielinfos", i, min(len(todo), VRINFO_MAX))
        gid = sid(data["titles"][k])
        text = src.get(f"{STEAM}/api/appdetails?appids={gid}&l=german&cc=de", shown=f"Steam-Details {gid}")
        if text is not None:
            got[k] = dict(_checked(prices.steam_details(text, gid)), at=titles.now_iso(), app=gid)
        if src.stopped:
            break
    ig, names_left = {}, 0
    if settings.get("igdb_id") and settings.get("igdb_secret") and not src.stopped:
        def due(t):
            r = t.get("igdb") or {}
            return (r.get("v") != igdb.V or moved(t, "igdb") or at(t, "igdb") < (old_m if r.get("none") else old_i)) and not t.get("contains")
        by_id = {k: sid(t) for k, t in data["titles"].items() if sid(t).isdigit() and due(t)}
        by_name = sorted((at(t, "igdb"), k) for k, t in data["titles"].items() if not sid(t).isdigit() and due(t))
        if by_id or by_name:
            isrc = _Source("IGDB", log, pause=IGDB_PAUSE)
            tok = igdb.token(isrc.get(igdb.TWITCH, shown="Twitch-Anmeldung", data=igdb.token_body(settings["igdb_id"], settings["igdb_secret"])))
            if tok:
                isrc.headers = {"Client-ID": settings["igdb_id"], "Authorization": f"Bearer {tok}", "Accept": "application/json"}

                def ask(path, body, shown):
                    t = isrc.get(igdb.API + path, shown=shown, data=body.encode())
                    try:
                        return None if t is None else json.loads(t or "[]")
                    except ValueError:
                        return None
                stamp, found_all = titles.now_iso(), {}
                for part in igdb.chunks(list(by_id)):
                    ids = [by_id[k] for k in part]
                    ext = ask("external_games", igdb.steam_query(ids), "Steam-IDs der VR-Titel")
                    if ext == []:
                        ext = ask("external_games", igdb.steam_query(ids, old=True), "Steam-IDs der VR-Titel")
                    if ext is None:
                        break
                    of = {str(x.get("uid")): x.get("game") for x in ext if isinstance(x, dict) and x.get("game")}
                    found = ask("games", igdb.games_query(sorted(set(of.values()))), "Spiele zu Steam-IDs") if of else []
                    if found is None:
                        break
                    by = {g.get("id"): g for g in found if isinstance(g, dict)}
                    for k in part:
                        found_all[k] = by.get(of.get(by_id[k]))
                names = [k for _, k in by_name]
                names_left = max(0, len(names) - VRINFO_NAMES)
                for i, k in enumerate(names[:VRINFO_NAMES]):
                    if isrc.stopped:
                        break
                    progress("IGDB, VR-Titel", i, min(len(names), VRINFO_NAMES))
                    name, hit, res = data["titles"][k]["name"], None, None
                    for body in igdb.name_queries(name, "VR"):
                        res = ask("games", body, f"„{name[:40]}“")
                        if res is None:
                            break
                        hit = igdb.pick(res, name)
                        if hit:
                            break
                    if res is None and not hit:
                        continue
                    found_all[k] = hit
                hit_ids = sorted({g["id"] for g in found_all.values() if g and g.get("id")})
                hours = {}
                for part in igdb.chunks(hit_ids):
                    hours.update(igdb.times(ask("game_time_to_beats", igdb.times_query(part), "Spielzeiten")) or {})
                for k, hit in found_all.items():
                    c = igdb.compact(hit) if hit else None
                    if c and hours.get(c["id"]):
                        c["hours"] = hours[c["id"]]
                    ig[k] = dict(c, at=stamp, v=igdb.V) if c else {"none": True, "at": stamp, "v": igdb.V}
                    ig[k]["app"] = sid(data["titles"][k])
            src.n += isrc.n
    with store.lock:
        data = store.load_data()
        for k, r in got.items():
            if k in data["titles"]:
                data["titles"][k]["sdet"] = r
        for k, r in ig.items():
            if k in data["titles"]:
                data["titles"][k]["igdb"] = r
        store.save_data(data)
    left = max(0, len(todo) - len(got))
    src.stats = {"read": len(got), "left": left + names_left, "igdb": sum(1 for r in ig.values() if r.get("id"))}
    log(f"VR-Titel, Spielinfos: {len(got)} bei Steam gelesen"
        + (f", IGDB {src.stats['igdb']} von {len(ig)} gefunden" if ig else "")
        + (f", {left} noch offen bei Steam (je Lauf {VRINFO_MAX}{_runs(left, VRINFO_MAX, ', ')})" if left else "")
        + (f", {names_left} Namen noch offen bei IGDB" if names_left else "")
        + ("" if left or names_left else ", alle aktuell") + f", {_took(start)}")
    return src.result()


def _pc_no_vr(g):
    return (g.get("system") or "PC") == "PC" and not (g.get("steam") or {}).get("vr")


def _fame(g):
    return -((g.get("rev") or {}).get("n") or 0)       # bekannte Spiele zuerst: dort gibt es eher Mods


def _pcgw(log):
    """PCGamingWiki (0.8.1): Vorlage „VR support“ je Steam-Spiel, über die Steam-ID (appid.php leitet auf die
    Seite, dann der Wikitext). „hackable“ heißt VR per Mod. Ab 0.9.5 für alle PC-Spiele (vorher nur ohne
    eingebautes VR), dazu die Spielerzahlen je Art aus „Network/Multiplayer“; ältere Einträge liest er neu."""
    start = time.monotonic()

    def get(src, gid, shown):
        page = src.get(mods.appid_url(gid), shown=shown, absent=(404,))
        if page is None:
            return None
        t = mods.title(page)
        if not t:
            return ""
        return src.get(mods.parse_url(t), shown=f"{shown} ({t[:40]})")
    src, got, left = _per_game(log, "PCGamingWiki", "pcgw", PCGW_DAYS, PCGW_MAX, None,
                               lambda text, gid: dict(mods.pcgw(text) if text else {"ok": True, "page": False}, v=mods.V),
                               stale=lambda r: (r or {}).get("v", 1) < mods.V,
                               get=get, want=lambda g: (g.get("system") or "PC") == "PC", order=_fame)
    if got is not None:
        hack = sum(1 for r in got.values() if r.get("mod"))
        log(f"PCGamingWiki: {len(got)} Spiele gelesen, {sum(1 for r in got.values() if r.get('page'))} mit Seite, {hack} mit VR per Mod, {sum(1 for r in got.values() if r.get('pl'))} mit Spielerzahl"
            + (f", {left} noch offen (je Lauf {PCGW_MAX}{_runs(left, PCGW_MAX, ', ')})" if left else ", alle aktuell") + f", {_took(start)}")
    return src.result()


def _nexus(settings, log):
    """Nexus Mods (0.8.1): einmal die Woche die Spieleliste, dann je PC-Spiel mit Seite dort die beliebtesten Mods
    und die mit VR im Namen. Mit persönlichem Schlüssel als Kopfzeile apikey."""
    start = time.monotonic()
    head = {"Content-Type": "application/json", "Accept": "application/json"}
    if settings.get("nexus_key"):
        head["apikey"] = settings["nexus_key"]
    src = _Source("Nexus Mods", log, headers=head, pause=1.0)
    col = store.load_json(collection.FILE, collection.EMPTY)
    old = _iso(now() - timedelta(days=NEXUS_DAYS))
    todo = sorted((((g.get("nexus") or {}).get("at") or ""), _fame(g), k) for k, g in (col.get("games") or {}).items()
                  if _pc_no_vr(g) and g.get("src") != "retro" and ((g.get("nexus") or {}).get("at") or "") < old)
    if not todo:
        log("Nexus Mods: alle aktuell" if col.get("games") else "Nexus Mods: keine Sammlung, nichts zu tun")
        return src.result()
    cache = store.load_json("nexus_games.json", {})
    if not cache.get("games") or (cache.get("at") or "") < _iso(now() - timedelta(days=NEXUS_LIST_DAYS)):
        games, total, raw = [], None, 0
        for page in range(mods.GAMES_PAGES):
            r = mods.games_page(src.get(mods.GQL, shown=f"Spieleliste Seite {page + 1}", data=mods.games_query(raw)))
            if r is None:
                break
            games += r[0]
            total = r[1]
            raw += r[2]
            if not r[2] or raw >= total:
                break
        if games and total is not None and raw >= total:
            cache = {"at": titles.now_iso(), "games": games}
            store.save_json("nexus_games.json", cache)
        elif not cache.get("games"):
            if not src.stopped:
                src.stopped = "Spieleliste nicht lesbar"
                log("Nexus Mods: die Spieleliste kam nicht vollständig, nichts zugeordnet")
            return src.result()
    idx = mods.index(cache["games"])
    got, asked = {}, 0
    for _, _, k in todo:
        if src.stopped:
            break
        g = col["games"][k]
        hit = mods.find(idx, (g.get("igdb") or {}).get("name") or g["name"]) or mods.find(idx, g["name"])
        if not hit:
            got[k] = {"none": True}
            continue
        if asked >= NEXUS_MAX:
            continue
        progress("Nexus Mods", asked, NEXUS_MAX)
        asked += 1
        m = mods.mods(src.get(mods.GQL, shown=f"Mods zu „{hit['name'][:40]}“", data=mods.mods_query(hit["dom"])))
        if m is None:
            continue
        got[k] = dict(m, dom=hit["dom"], name=hit["name"], n=hit["mods"])
    stamp = titles.now_iso()
    with store.lock:
        col = store.load_json(collection.FILE, collection.EMPTY)
        for k, r in got.items():
            if k in col.get("games", {}):
                col["games"][k]["nexus"] = dict(r, at=stamp, v=mods.V)
        store.save_json(collection.FILE, col)
    found = [r for r in got.values() if not r.get("none")]
    left = sum(1 for _, _, k in todo if k not in got)
    src.stats = {"read": len(got), "found": len(found), "left": left}
    log(f"Nexus Mods: {len(cache['games'])} Spiele in der Liste, {len(found)} deiner Spiele neu gelesen, "
        f"{sum(1 for r in found if r.get('vr'))} mit Mods mit VR im Namen"
        + (f", {left} noch offen (je Lauf {NEXUS_MAX}{_runs(left, NEXUS_MAX, ', ')})" if left else "") + f", {_took(start)}")
    return src.result()


def _wheel(log):
    """Sim-Racing (0.8.3): zwei Listen von Rennspielen für Lenkräder (Bestätigung, je alle WHEEL_LIST_DAYS Tage
    eine Anfrage: Simucube-Forum, ab 0.8.5 SimHub) und die Steam-Schlagwörter (Hinweis), gebündelt über
    IStoreBrowseService/GetItems: zuerst die VR-Titel des Tools (0.8.5), dann die Steam-Spiele der Sammlung."""
    start = time.monotonic()
    label = NAMES["wheel"]
    src = _Source(label, log)
    old_list = _iso(now() - timedelta(days=WHEEL_LIST_DAYS))
    wl = store.load_json(wheel.LIST_FILE, {})
    changed = False
    force = wl.get("v") != wheel.V      # neuer Leser (0.8.6): gespeicherte Listen neu lesen statt 30 Tage warten
    if force or (wl.get("at") or "") < old_list:
        names = wheel.game_list(src.get(wheel.LIST, shown=wheel.LIST_NAME) or "")
        if len(names) >= 20:            # weniger heißt: die Seite sah anders aus, alte Liste behalten
            wl.update(at=titles.now_iso(), names=names, v=wheel.V)
            changed = True
        elif not src.stopped:
            log(f"{label}: {wheel.LIST_NAME} nicht lesbar ({len(names)} Namen), "
                + (f"die vom {wl['at'][:10]} gilt weiter" if wl.get("names") else "ohne diese Bestätigung"))
    sh = wl.get("simhub") or {}
    if (force or (sh.get("at") or "") < old_list) and not src.stopped:
        r = wheel.simhub(src.get(wheel.SIMHUB, shown=wheel.SIMHUB_NAME) or "")
        if len(r["apps"]) >= 20 or len(r["names"]) >= 20:
            wl["simhub"] = dict(r, at=titles.now_iso())
            changed = True
        elif not src.stopped:
            log(f"{label}: {wheel.SIMHUB_NAME} nicht lesbar ({len(r['apps'])} Steam-IDs, {len(r['names'])} Namen), "
                + (f"die vom {sh['at'][:10]} gilt weiter" if sh.get("at") else "ohne diese Bestätigung"))
    if changed:
        store.save_json(wheel.LIST_FILE, wl)
    col = store.load_json(collection.FILE, collection.EMPTY)
    data = store.load_data()
    old = _iso(now() - timedelta(days=WHEEL_DAYS))
    stale = lambda x: ((x.get("stag") or {}).get("at") or "") < old
    todo = [("t", k, str(t["steam_appid"])) for k, t in sorted(data["titles"].items(), key=lambda kv: (kv[1].get("stag") or {}).get("at") or "")
            if str(t.get("steam_appid") or "").isdigit() and stale(t)]
    todo += [("g", k, str(g["id"])) for _, k, g in sorted(((g.get("stag") or {}).get("at") or "", k, g) for k, g in (col.get("games") or {}).items()
             if (g.get("system") or "PC") == "PC" and g.get("store") == "Steam" and str(g.get("id") or "").isdigit() and stale(g))]
    left_all = len(todo)
    todo = todo[:WHEEL_MAX]
    got = {}
    if todo:
        tl = store.load_json(wheel.TAGS_FILE, {})
        if (tl.get("at") or "") < old_list:
            known = wheel.tag_list(src.get(wheel.TAGLIST, shown="Liste der Steam-Schlagwörter") or "")
            if known:
                tl = {"at": titles.now_iso(), "tags": {str(k): v for k, v in known.items()}}
                store.save_json(wheel.TAGS_FILE, tl)
        known = {int(k): v for k, v in (tl.get("tags") or {}).items()}
        apps = list(dict.fromkeys(a for _, _, a in todo))
        tags = {}
        for i in range(0, len(apps), wheel.BATCH):
            progress(label, i, len(apps))
            part = apps[i:i + wheel.BATCH]
            r = wheel.items(src.get(wheel.items_url(part), shown=f"Steam-Schlagwörter {i + 1}–{i + len(part)}") or "")
            if r is None:
                if src.stopped:
                    break
                continue
            stamp = titles.now_iso()
            for a in part:
                tags[a] = {"tags": [n.strip() for n in wheel.names(r.get(a) or [], known) if n.strip()][:12], "at": stamp, "v": wheel.V}
        got = {(kind, k): tags[a] for kind, k, a in todo if a in tags}
        with store.lock:
            col = store.load_json(collection.FILE, collection.EMPTY)
            for (kind, k), r in got.items():
                if kind == "g" and k in col.get("games", {}):
                    col["games"][k]["stag"] = r
            store.save_json(collection.FILE, col)
            data = store.load_data()
            for (kind, k), r in got.items():
                if kind == "t" and k in data["titles"]:
                    data["titles"][k]["stag"] = r
            store.save_data(data)
    games = col.get("games") or {}
    match = wheel.matcher(wl)
    pc = [g for g in games.values() if (g.get("system") or "PC") == "PC" and g.get("src") != "retro"]
    hint = sum(1 for x in pc + list(data["titles"].values()) if wheel.hint((x.get("stag") or {}).get("tags") or []))
    sure = sum(1 for g in pc if match(g.get("id") if g.get("store") == "Steam" else "", (g.get("igdb") or {}).get("name"), g["name"]))
    sure_vr = sum(1 for t in data["titles"].values() if match(t.get("steam_appid"), t["name"]))
    left = left_all - len(got)
    sh = wl.get("simhub") or {}
    src.stats = {"read": len(got), "list": len(wl.get("names") or []), "simhub": len(sh.get("apps") or []), "hint": hint,
                 "sure": sure + sure_vr, "left": left}
    log(f"{label}: Listen der Rennspiele mit {len(wl.get('names') or [])} (Simucube-Forum) und {len(sh.get('names') or [])} Spielen "
        f"(SimHub, {len(sh.get('apps') or [])} mit Steam-ID), darin {sure_vr} VR-Titel und {sure} Spiele der Sammlung; "
        f"Steam-Schlagwörter für {len(got)} Spiele gelesen, {hint} mit Hinweis auf Sim-Racing"
        + (f", {left} noch offen" if left else "") + f", {_took(start)}")
    return src.result()


def _sharenite(settings, log):
    """PC-Bibliothek aus einem öffentlichen Sharenite-Profil (Playnite online, alle Läden). Liest
    erst Seite 1 für die Kennungen der VR-Schlagwörter, dann nur die gefilterte Liste; fehlt der
    Filter, die ganze Liste und sortiert selbst aus."""
    src = _Source("Sharenite", log)
    start, stamp = time.monotonic(), titles.now_iso()
    base = settings["sharenite"]
    text = src.get(base + "?sort=name_asc", shown="Sharenite, Seite 1")
    if text is None:
        return src.result()
    games, total, vr_tags = accounts.sharenite_page(text)
    if vr_tags:
        q = "&".join("tag_ids%5B%5D=" + urllib.parse.quote(v) for v in vr_tags)
        games, page = [], 1
        while page <= SHARENITE_PAGES:
            progress("Sharenite: VR-Spiele", page, 0)
            text = src.get(f"{base}?{q}&sort=name_asc&page={page}", shown=f"Sharenite, VR-Spiele Seite {page}")
            got = accounts.sharenite_page(text)[0] if text else []
            if not got:
                break
            games += got
            page += 1
            if len(got) < 100:
                break
        how = f"gefiltert nach {len(vr_tags)} VR-Schlagwörtern"
    else:
        pages = min(SHARENITE_PAGES, -(-(total or 100) // 100))
        for page in range(2, pages + 1):
            progress("Sharenite: Seiten", page, pages)
            text = src.get(f"{base}?sort=name_asc&page={page}", shown=f"Sharenite, Seite {page}")
            if text is None:
                break
            games += accounts.sharenite_page(text)[0]
        how = f"ganze Liste, {pages} Seiten"
    if not games:
        log("Sharenite: keine Spiele erkannt (Profil privat oder Seite geändert? „Verbindung testen“ zeigt die Antwort)")
        return dict(src.result(), ok=False, msg=src.stopped or "nichts erkannt")
    with store.lock:
        data = store.load_data()
        known, new = accounts.apply_sharenite(data, games, stamp)
        store.save_data(data)
    vr = sum(g["vr"] for g in games)
    shops = sorted({g["source"] for g in games if g["vr"] and g["source"]})
    log(f"Sharenite: {total if total is not None else '?'} Spiele im Profil, {vr} mit VR-Schlagwort ({how})"
        + (f", aus {', '.join(shops)}" if shops else "") + f"; {known} schon im Tool"
        + (f", neu als Besitz am PC ({len(new)}): {_few(new)}" if new else ""))
    log(f"Sharenite: fertig nach {_took(start)}, {src.n} Anfragen")
    src.stats = {"games": total, "vr": vr, "new": len(new)}
    return src.result()


def _assign(log, budget, rest):
    """Zuordnung für alle Titel, auch gekaufte: Steam-IDs, die nur aus einem Namen stammen,
    im Store prüfen (Name und VR), und Titel ohne Meta-ID außerhalb der Preisliste bei
    QuestStoreDB suchen. Gefundene Namen merkt sich der Titel als weitere Namen. Was offen
    bleibt, zeigt die Liste „Zu erledigen“ (titles.todo)."""
    start, stamp = time.monotonic(), titles.now_iso()
    data = store.load_data()
    targets = _targets(data)
    # 1. Steam-IDs „≈“
    unsure = {k: t["steam_appid"] for k, t in data["titles"].items() if t.get("steam_appid") and not t.get("steam_sure")}
    apps = dict(data.get("steam_apps") or {})
    checked = 0
    if unsure and not rest.get("steam"):
        steam = _Source("Steam", log)
        checked = _app_checks(steam, list(dict.fromkeys(unsure.values())), apps, budget, stamp)
        if steam.blocked:
            rest["steam"] = _iso(now() + timedelta(hours=REST_H))
    # 2. Meta-ID suchen, gekaufte bei Meta zuerst
    todo = [(not (t.get("owned") or {}).get("meta"), bool(t.get("steam_appid")), titles.norm(t["name"]), k)
            for k, t in data["titles"].items()
            if k not in targets and not t.get("meta_id") and not (t.get("links") or {}).get("qsdb")]
    todo.sort()
    waiting = [k for *_, k in todo if _missed(data["titles"][k], "meta_miss")]
    queue = [k for *_, k in todo if k not in waiting]
    hits, missed, searches = {}, [], 0
    if queue and not rest.get("qsdb"):
        src = _Source("QuestStoreDB", log, QSDB_HEAD)
        for k in queue:
            if searches >= ASSIGN_SEARCH or src.stopped:
                break
            t = data["titles"][k]
            progress("Zuordnung: QuestStoreDB", searches, ASSIGN_SEARCH)

            def url(name):
                return f"{prices.QSDB}/all_apps/?" + urllib.parse.urlencode({"release_status": "all", "q": name})
            hit, n, miss = _search(src, t, url, lambda text: _pick(prices.qsdb_cards(text), t), ASSIGN_SEARCH - searches)
            searches += n
            if hit and hit.get("meta_id"):
                hits[k] = hit
            elif miss:
                missed.append(k)
        if src.blocked:
            rest["qsdb"] = _iso(now() + timedelta(hours=REST_H))
    # Eintragen
    sure, doubt, found, merged = [], [], [], 0
    with store.lock:
        data = store.load_data()
        data["steam_apps"] = dict(data.get("steam_apps") or {}, **apps)
        for k, appid in unsure.items():
            t = data["titles"].get(k)
            if not t or t.get("steam_appid") != appid or t.get("steam_sure"):
                continue
            ok, why = titles.steam_verdict(t, data["steam_apps"].get(appid))
            if ok:
                t["steam_sure"] = True
                t.pop("steam_doubt", None)
                titles.add_alias(t, data["steam_apps"][appid]["name"])
                sure.append(t["name"])
            elif ok is False:
                if t.get("steam_doubt") != why:
                    doubt.append(f"{t['name']} ({why})")
                t["steam_doubt"] = why
        for k in missed:
            if k in data["titles"]:
                data["titles"][k]["meta_miss"] = stamp
        for k, hit in hits.items():
            t = data["titles"].get(k)
            if not t or t.get("meta_id"):
                continue
            n = len(data["titles"])
            k = titles.set_ids(data, k, meta_id=hit["meta_id"])
            merged += n - len(data["titles"])
            t = data["titles"][k]
            t.pop("meta_miss", None)
            if hit.get("path"):
                t.setdefault("links", {})["qsdb"] = prices.QSDB + hit["path"]
            titles.add_alias(t, hit.get("name"))
            found.append(t["name"])
        wish_back = lists.undo_auto(data)
        store.save_data(data)
        left = titles.todo(data)
    if wish_back:
        log(f"Wunschliste: wieder gewünscht, steht unter „Gekauft, noch auf der Wunschliste“ ({len(wish_back)}): {_few(wish_back)}")
    if unsure:
        log(f"Zuordnung, Steam-IDs „≈“: {len(unsure)} ungeprüft, {checked} Apps im Store gefragt"
            + (f"; bestätigt ({len(sure)}): {_few(sure)}" if sure else "")
            + (f"; passt nicht ({len(doubt)}): {_few(doubt, 6)}" if doubt else ""))
    if searches or waiting:
        log(f"Zuordnung, Meta-ID bei QuestStoreDB: {searches} Anfragen für Titel außerhalb der Preisliste"
            + (f", gefunden ({len(found)}): {_few(found)}" if found else ", nichts gefunden")
            + (f", davon {merged} mit einem vorhandenen Eintrag zusammengeführt" if merged else "")
            + (f"; ohne Treffer {len(missed)}" if missed else "")
            + (f"; {len(queue) - len(found) - len(missed)} folgen beim nächsten Abgleich" if len(queue) > len(found) + len(missed) else "")
            + (f"; {len(waiting)} ohne Treffer in den letzten {MISS_DAYS} Tagen" if waiting else ""))
    log(f"Zuordnung: fertig nach {_took(start)}" + (f", {len(left)} Fälle unter „Zu erledigen“" if left else ", nichts offen"))


def run(only=None, boot=False, by_hand=False, fast=False):
    """Ein Lauf. only: Menge der Quellen (qsdb, steam, gg), sonst alle. fast: Grenzen je Lauf mal FAST
    (nur von Hand). Läuft schon einer, kommt False zurück."""
    if not _running.acquire(blocking=False):
        return False
    limits = {k: globals()[k] for k in FAST_LIMITS}
    try:
        if fast:
            globals().update({k: v * FAST for k, v in limits.items()})
        prev = store.load_json("sync.json", {})
        st = {"started": _iso(now()), "log": [], "sources": dict(prev.get("sources") or {}),
              "rest": {k: v for k, v in (prev.get("rest") or {}).items() if v > _iso(now())}}
        STATE.update(started=st["started"], step="Start", done=0, total=0, log=st["log"])

        def log(msg):
            # Zeit in UTC, die Oberfläche zeigt sie in der Zeit des Browsers
            st["log"].append(f"{now().strftime('%H:%M:%S')} {msg}")
            del st["log"][:-LOG_LINES]
            print(msg, flush=True)

        begun = time.monotonic()
        settings = load_settings()
        log(f"VR-Navigator {sources.VERSION}, Abgleich "
            + ("von Hand" if by_hand else "nach dem Start" if boot else "nach Zeitplan")
            + (", nur " + ", ".join(NAMES[x] for x in NAMES if x in only) if only else "")
            + (f", beschleunigt (je Quelle bis zu {FAST}-mal so viele Abrufe, Pausen wie sonst)" if fast else ""))
        _old_misses["ignore"] = prev.get("search_v") != SEARCH_V
        if _old_misses["ignore"] and prev:
            log("Suche geändert: Titel ohne Treffer werden diesmal neu gesucht")
        upd, results = {}, {}

        def do(name, fn):
            if only and name not in only:
                return
            if st["rest"].get(name):
                until = datetime.fromisoformat(st["rest"][name])
                log(f"{NAMES[name]}: ruht nach einer Sperre bis {until.strftime('%d.%m. %H:%M')} UTC, nicht abgefragt")
                results[name] = {"at": titles.now_iso(), "ok": False, "msg": "ruht", "until": st["rest"][name],
                                 "requests": 0, "errors": 0}
                return
            progress(NAMES[name])
            try:
                results[name] = fn()
            except Exception as e:          # ein Fehler im Lesen soll die anderen Quellen nicht aufhalten
                log(f"{NAMES[name]}: unerwarteter Fehler ({type(e).__name__}), Einzelheiten im Protokoll des Containers")
                print(f"Fehler beim Abgleich {name}:", e, file=sys.stderr)
                results[name] = {"at": titles.now_iso(), "ok": False, "msg": type(e).__name__}
            if results[name].get("blocked"):
                st["rest"][name] = _iso(now() + timedelta(hours=REST_H))
                results[name]["until"] = st["rest"][name]

        # Erst die Konten (Besitz, Wunschlisten), damit neue Wunschtitel gleich Preise bekommen
        budget = {"apps": APPINFO_MAX, "search": 15}
        if settings["steam_id"]:
            do("steamacc", lambda: _steam_account(settings, log, budget))
        # gg.deals zeigt dem Server oft eine Prüfseite von Cloudflare; dann liest das Lesezeichen
        # die Wunschliste im Browser, und der Abgleich sucht nur die unbekannten Namen nach
        manual = st["manual"] = dict(prev.get("manual") or {})
        if st["rest"].pop("ggwish", None):
            manual["ggwish"] = _iso(now())          # Sperre aus einer Version vor 0.3.4
        if settings["gg_wish"] and manual.get("ggwish") and manual["ggwish"] < _iso(now() - timedelta(days=GG_RETRY_DAYS)):
            # Einmal die Woche ein neuer Versuch: Cloudflare lässt den Server manchmal wieder durch
            manual.pop("ggwish")
            log(f"gg.deals-Wunschliste: neuer Versuch über den Server (seit {GG_RETRY_DAYS} Tagen per Lesezeichen)")
        if settings["gg_wish"] and not manual.get("ggwish"):
            do("ggwish", lambda: _gg_wish(settings, log, budget))
            if (results.get("ggwish") or {}).get("blocked"):
                manual["ggwish"] = _iso(now())
                st["rest"].pop("ggwish", None)
                results["ggwish"] = dict(results["ggwish"], ok=True, manual=True, msg="per Lesezeichen", until=None)
                log("gg.deals-Wunschliste: gg.deals lässt den Server nicht durch (Prüfseite von Cloudflare). Lies die "
                    f"Wunschliste mit dem Lesezeichen „Seite lesen“ auf gg.deals; der Server versucht es in {GG_RETRY_DAYS} Tagen "
                    "wieder oder sofort, wenn du den Link neu speicherst.")
        if store.load_data().get("gg_unknown") and (not only or "ggwish" in only):
            # eigenes Kontingent: eine lange Wunschliste soll in wenigen Läufen durch sein
            r = _gg_pending(log, {"apps": GG_PENDING, "search": GG_PENDING})
            if r and "ggwish" not in results:
                results["ggwish"] = dict(r, manual=bool(manual.get("ggwish")))
        elif settings["gg_wish"] and manual.get("ggwish") and "ggwish" not in results:
            last = (store.load_data().get("imports") or {}).get("ggwish") or {}
            log("gg.deals-Wunschliste: nur per Lesezeichen" + (f", zuletzt gelesen {_ago_text(last['at'])}" if last.get("at") else ", noch nie gelesen"))
            results["ggwish"] = {"at": titles.now_iso(), "ok": True, "manual": True, "msg": "per Lesezeichen",
                                 "requests": 0, "errors": 0}
        if not only or "pcwish" in only:
            do("pcwish", lambda: _pcwish(settings, log))
        if settings["itad_key"] and (not only or "itad" in only):
            do("itad", lambda: _itad(settings, log))
        if any(st["rest"].get(x) for x in ("details", "reviews")) and (not only or "pcinfo" in only):
            log("PC-Wunschliste, Spielinfos: Steam ruht nach einer Sperre, nicht abgefragt")
        else:
            do("pcinfo", lambda: _pcwish_info(settings, log))
            do("vrinfo", lambda: _vr_info(settings, log))
        if settings["sharenite"]:
            last = ((prev.get("sources") or {}).get("sharenite") or {})
            fresh = last.get("ok") and (last.get("at") or "") > _iso(now() - timedelta(hours=SHARENITE_H))
            if fresh and not by_hand and not only:
                results["sharenite"] = last
                log(f"Sharenite: zuletzt gelesen {_ago_text(last['at'])}, wieder nach {SHARENITE_H} Stunden")
            else:
                do("sharenite", lambda: _sharenite(settings, log))
        if not only or any(x in only for x in ("qsdb", "steam")):
            progress("Zuordnung")
            try:
                # eigenes Kontingent, damit eine lange Steam-Wunschliste die Prüfung nicht aufbraucht
                _assign(log, {"apps": ASSIGN_APPS, "search": 0}, st["rest"])
            except Exception as e:
                log(f"Zuordnung: unerwarteter Fehler ({type(e).__name__}), Einzelheiten im Protokoll des Containers")
                print("Fehler bei der Zuordnung:", e, file=sys.stderr)
        targets = _targets(store.load_data())
        log(f"Preise für {len(targets)} Wunschtitel, die du noch nicht besitzt")
        do("qsdb", lambda: _qsdb(targets, upd, log))
        do("steam", lambda: _steam(targets, upd, log))
        if settings["gg_key"]:
            do("gg", lambda: _gg(targets, upd, settings["gg_key"], log))
        else:
            log("gg.deals: kein Schlüssel eingetragen, nicht abgefragt")
        # VR-Titel am PC ohne Playnite-Eintrag (0.8.9) als Spiele der Sammlung, damit die Abrufe danach sie mitnehmen
        try:
            with store.lock:
                col = store.load_json(collection.FILE, collection.EMPTY)
                new, gone = collection.sync_pcvr(col, store.load_data())
                store.save_json(collection.FILE, col)
            if new or gone:
                log(f"Sammlung: VR-Titel am PC ohne Playnite-Eintrag {new} neu" + (f", {gone} entfallen" if gone else ""))
        except Exception as e:
            log(f"Sammlung: VR-Titel am PC nicht abgeglichen ({type(e).__name__})")
        if not only or "reviews" in only:
            do("reviews", lambda: _reviews(log))
        if not only or "details" in only:
            do("details", lambda: _details(log))
        if not only or "rating" in only:
            do("rating", lambda: _rating(log))
        if settings["igdb_id"] and settings["igdb_secret"] and (not only or "igdb" in only):
            do("igdb", lambda: _igdb(settings, log))
        if not only or "pcgw" in only:
            do("pcgw", lambda: _pcgw(log))
        if not only or "nexus" in only:
            do("nexus", lambda: _nexus(settings, log))
        if not only or "wheel" in only:
            do("wheel", lambda: _wheel(log))
        if not only or "players" in only:
            do("players", lambda: _players(log))
        if not only or "active" in only:
            do("active", lambda: _active(log))
        if not only or "vrdb" in only:
            do("vrdb", lambda: _vrdb(log))
        if not only or "retro" in only:
            do("retro", lambda: _retro(log))
        if sources.eshop_url() and (not only or "eshop" in only):
            do("eshop", lambda: _eshop(log))
        progress("Speichern")
        applied = apply(upd)
        st["sources"].update(results)
        st["warnings"] = self_check(results, prev.get("sources") or {}, applied)
        mv = applied["moves"]
        if any(mv.values()):
            log("Preise: " + "; ".join(x for x in (
                f"günstiger ({len(mv['down'])}): {_few(mv['down'], 8)}" if mv["down"] else "",
                f"teurer ({len(mv['up'])}): {_few(mv['up'], 8)}" if mv["up"] else "",
                f"neuer Meta-Tiefstpreis ({len(mv['low'])}): {_few(mv['low'], 8)}" if mv["low"] else "",
                f"kleine Schwankungen unter {_eur(SMALL_EUR)} ({len(mv['small'])})" if mv["small"] else "") if x))
        else:
            log("Preise: keine Änderung seit dem letzten Abgleich")
        cov = applied["coverage"]
        log(f"Stand: {cov['n']} Wunschtitel, mit Preis bei Meta {cov['has']['meta']}, Steam {cov['has']['steam']}, "
            f"gg.deals {cov['has']['gg']}" + (f"; ohne jeden Preis ({len(cov['bare'])}): {_few(cov['bare'])}" if cov["bare"] else ""))
        for w in st["warnings"]:
            log("Selbstprüfung: " + w)
        if not st["warnings"]:
            log("Selbstprüfung: alles glaubhaft")
        st["ok"] = all(r.get("ok") for r in results.values())
        st["finished"] = st["done"] = _iso(now())
        if not _old_misses["ignore"] or not only:
            st["search_v"] = SEARCH_V
        log(f"fertig nach {_took(begun)}, {len(upd)} Titel aktualisiert" + ("" if st["ok"] else ", mit Fehlern"))
        # Kurzfassung als zweite Zeile, damit das Wichtigste oben steht
        if st["log"]:
            st["log"].insert(1, st["log"][-1][:9] + summary(applied, st["warnings"], results))
            del st["log"][:-LOG_LINES]
        store.save_json("sync.json", st)
        return True
    finally:
        globals().update(limits)
        STATE.update(step="", done=0, total=0)
        _running.release()


def start(only=None, fast=False):
    """Lauf im Hintergrund starten. False, wenn schon einer läuft."""
    if _running.locked():
        return False
    threading.Thread(target=run, args=(only,), kwargs={"by_hand": True, "fast": bool(fast)}, daemon=True).start()
    return True


def scheduler():
    """Prüft jede Minute, ob ein Lauf nach Zeitplan fällig ist. Erster Blick BOOT_WAIT_S nach
    dem Start: dann ein Lauf, wenn der letzte über BOOT_GAP_MIN zurückliegt (siehe due)."""
    time.sleep(BOOT_WAIT_S)
    boot = True
    while True:
        try:
            if due(boot=boot) and not _running.locked():
                run(boot=boot)
        except Exception as e:
            print("Zeitplan:", e, file=sys.stderr)
        boot = False
        time.sleep(60)


def diagnose():
    """Verbindung testen: jede Quelle einmal abfragen und beschreiben, was zurückkommt (Status,
    Server, Kodierung, was die Leser erkennen). Nimmt, wo es geht, einen Titel deiner
    Wunschliste. Speichert nichts; der gg.deals-Schlüssel erscheint nie im Ergebnis."""
    data = store.load_data()
    settings = load_settings()
    key = settings["gg_key"]
    targets = list(_targets(data).values())
    lines = [f"VR-Navigator {sources.VERSION}, Test vom {now().strftime('%d.%m.%Y %H:%M')} UTC"]
    hosts = set()

    def probe(name, url, info, headers=None, shown=None, data=None):
        host = urllib.parse.urlsplit(url).hostname
        if host in hosts:
            sleep(PAUSE)
        hosts.add(host)
        r = sources.request(url, headers=headers, data=data)
        if r["error"]:
            lines.append(f"{name}: keine Verbindung ({r['error']})")
            return None
        moved = r.get("final") and r["final"] != url and urllib.parse.urlsplit(r["final"])[:3] != urllib.parse.urlsplit(url)[:3]
        head = (f"{name}: HTTP {r['status']}, Server {r['server'] or '?'}, Kodierung {r['enc'] or 'keine'}, {len(r['text'])} Zeichen"
                + (f", umgeleitet nach {urllib.parse.urlsplit(r['final']).path or '/'}" if moved else ""))
        why = sources.challenge(r["text"])
        if why or r["status"] >= 400:
            lines.append(head + (f", {why}" if why else "") + (", gesperrt" if r["status"] in sources.BLOCKED else "")
                         + f". Anfang: {' '.join(r['text'][:160].split())}")
            return None
        try:
            lines.append(f"{head}, {info(r['text'])}")
        except Exception as e:     # ein Lesefehler soll nicht den ganzen Test abbrechen
            lines.append(f"{head}, nicht auswertbar ({type(e).__name__}: {e})")
        return r["text"]

    def sale_info(text):
        cards = prices.qsdb_cards(text)
        return f"{len(cards)} Angebote erkannt, {prices.qsdb_pages(text)} Seiten" + (
            f", erstes: {cards[0]['name']} {cards[0]['price']} € statt {cards[0]['base']} €" if cards else "")
    sale = probe("QuestStoreDB, Angebotsliste", f"{prices.QSDB}/on_sale/?sort=-sale_start_time", sale_info, QSDB_HEAD)

    t = next((t for t in targets if t.get("meta_id") or (t.get("links") or {}).get("qsdb")), targets[0] if targets else None)
    name = t["name"] if t else "vr"
    hit = {}

    def search_info(text):
        cards = prices.qsdb_cards(text)
        h = _pick(cards, t) if t else (cards[0] if cards else None)
        if h:
            hit.update(h)
        return f"{len(cards)} Treffer für „{name}“" + (f", passend: {h['name']} (Meta-ID {h['meta_id']})" if h else ", keiner passt eindeutig")
    q = urllib.parse.urlencode({"release_status": "all", "q": name})
    probe("QuestStoreDB, Suche", f"{prices.QSDB}/all_apps/?{q}", search_info, QSDB_HEAD)

    path = ((t or {}).get("live") or {}).get("meta", {}).get("path") or hit.get("path") or ""
    link = ((t or {}).get("links") or {}).get("qsdb") or ""
    if not path and link.startswith(prices.QSDB + "/"):
        path = link[len(prices.QSDB):]
    if not path and sale:
        path = next((c["path"] for c in prices.qsdb_cards(sale)), "")

    def game_info(text):
        g = prices.qsdb_game(text)
        if not g:
            return "kein Preis lesbar (strukturierte Daten fehlen)"
        return (f"„{g['name']}“, Preis {g['price']} €, Normalpreis {g['base']} €"
                + (f" bis {g['until']}" if g["until"] and g["price"] != g["base"] else "")
                + (f", Tief {g['low']} € am {g['low_at']}" if g["low"] is not None else ", ohne Preisverlauf")
                + (f", Version {g['version']}" if g["version"] else ""))
    if path:
        probe("QuestStoreDB, Titelseite", prices.QSDB + path, game_info, QSDB_HEAD)
    else:
        lines.append("QuestStoreDB, Titelseite: kein Pfad bekannt, nicht angefragt")

    st = next((t for t in targets if t.get("steam_appid")), None)
    appid = st["steam_appid"] if st else "10"

    def steam_info(text):
        p = prices.steam_prices(text).get(appid)
        return (f"App {appid}: {p['price']} € statt {p['base']} €, −{p['discount']} %" if p and p["discount"]
                else f"App {appid}: {p['price']} €" if p and p["price"] else f"App {appid}: kostenlos oder ohne Preis" if p else f"App {appid}: kein Preis im deutschen Store")
    if sources.eshop_url():
        def eshop_info(text):
            d = json.loads(text)
            gs = d.get("games") if isinstance(d, dict) and d.get("app") == "eshop-kompass" else None
            return (f"Sammlung mit {len(gs)} Spielen, eShopKompass {str(d.get('version') or '?')[:12]}" if isinstance(gs, list)
                    else "Antwort ist nicht die Sammlung des eShopKompass (ab 1.7.16)")
        probe("eShopKompass (eigenes Netz)", sources.eshop_url(), eshop_info)
    else:
        lines.append("eShopKompass: nicht eingerichtet (ESHOP_URL im Stack, siehe README)")
    probe("Steam, Preise", f"{STEAM}/api/appdetails?appids={appid}&cc=de&filters=price_overview", steam_info)
    sname = (st or t or {}).get("name") or "vr"
    probe("Steam, Suche", f"{STEAM}/api/storesearch/?" + urllib.parse.urlencode({"term": sname, "l": "german", "cc": "DE"}),
          lambda text: f"{len(prices.steam_search(text))} Treffer für „{sname}“")

    # Rezensionen an Spielen der Sammlung (0.7.2: drei verschiedene, das bekannteste, eins aus der Mitte und
    # eins ohne gelesenen Wert). Statt Daten liefert Steam manchmal eine Store-Seite, etwa bei Spielen ab 18
    # ohne Anmeldung; das zeigt der Test mit Titel und Ziel der Umleitung
    col = store.load_json(collection.FILE, collection.EMPTY)
    sg = sorted((g for g in (col.get("games") or {}).values() if g.get("store") == "Steam" and str(g.get("id") or "").isdigit()),
                key=lambda g: -((g.get("rev") or {}).get("n") or 0))
    picks = [g for g in (sg[:1] + sg[len(sg) // 2:len(sg) // 2 + 1] + [g for g in sg if not (g.get("rev") or {}).get("n")][:1])]
    rapps = list(dict.fromkeys(str(g["id"]) for g in picks)) or [appid]
    def rev_info(rapp, form):
        def info(text):
            r = prices.steam_reviews(text)
            if r:
                return (f"App {rapp}, Form {form}: {r['n']} Rezensionen, {r['pct']} % positiv ({r['desc'] or 'ohne Text'})" if r["n"]
                        else f"App {rapp}, Form {form}: Steam kennt die App, noch keine Rezensionen")
            t = re.search(r"(?s)<title>(.*?)</title>", text)
            return (f"App {rapp}, Form {form}: Store-Seite statt Daten" + (f" („{' '.join(html.unescape(t.group(1)).split())[:80]}“)" if t else "")
                    if text.lstrip()[:1] == "<" else f"App {rapp}, Form {form}: Antwort nicht lesbar. Anfang: {' '.join(text[:200].split())}")
        return info
    sb = REVIEW_Q.index("storebrowse")
    for rapp in rapps:
        probe("Steam, Rezensionen", review_url(rapp, 0), rev_info(rapp, 1))
        probe("Steam, Rezensionen", review_url(rapp, sb), rev_info(rapp, sb + 1))
    # 0.7.4: am ersten Spiel jede Form der Adresse, damit klar ist, welche Steam noch beantwortet
    for i in range(1, sb):
        probe("Steam, Rezensionen", review_url(rapps[0], i), rev_info(rapps[0], i + 1))

    def hist_info(text):
        h = trend.histogram(text)
        if h:
            return f"App {rapps[0]}: {h['up'] + h['down']} Rezensionen in den letzten 30 Tagen, {h['up']} positiv"
        return "Store-Seite statt Daten" if text.lstrip()[:1] == "<" else f"Antwort nicht lesbar. Anfang: {' '.join(text[:200].split())}"
    probe("Steam, Trend", f"{STEAM}/appreviewhistogram/{rapps[0]}?l=english&review_score_preference=0", hist_info)

    if not key:
        lines.append("gg.deals: kein Schlüssel eingetragen, nicht angefragt")
    else:
        def gg_info(text):
            try:
                got = prices.gg_prices(text)
            except ValueError as e:
                return f"{e}. Anfang: {' '.join(text[:200].split())}"
            p = got.get(appid)
            if not p:
                return f"Schlüssel angenommen, für App {appid} kein Eintrag. Anfang: {' '.join(text[:200].split())}"

            def eur(v):
                return "keins" if v is None else f"{v} €"
            return (f"Schlüssel angenommen, App {appid}: Händler {eur(p['retail'])} (Tief {eur(p['retail_low'])}), "
                    f"Keyshops {eur(p['keyshops'])} (Tief {eur(p['keyshops_low'])})")
        q = urllib.parse.urlencode({"ids": appid, "region": "de"})
        probe("gg.deals, Preise", f"{GG_API}?{q}&key={urllib.parse.quote(key)}", gg_info, shown=f"{GG_API}?{q}")
    # IsThereAnyDeal (0.9.0): Zuordnung der Steam-ID, dann die Preise je Laden
    if not settings["itad_key"]:
        lines.append("IsThereAnyDeal: kein Schlüssel eingetragen, nicht angefragt")
    else:
        ih, gid = itad.headers(settings["itad_key"]), {}

        def itad_look(text):
            got = itad.lookup(text)
            gid["id"] = got.get(str(appid)) or ""
            return f"App {appid}: " + ("ITAD-Kennung gefunden" if gid["id"] else "keine ITAD-Kennung")

        def itad_info(text):
            p = itad.prices(text).get(gid["id"])
            if not p:
                return f"für App {appid} keine Preise. Anfang: {' '.join(text[:200].split())}"
            top = ", ".join(f"{s['s']} {s['p']} €" + (f" (−{s['c']} %)" if s["c"] else "") for s in p["shops"][:4])
            return (f"App {appid}: {len(p['shops'])} Läden" + (f", günstigste: {top}" if top else "")
                    + (f", Tief {p['low']} €" if p["low"] is not None else ""))
        if probe("IsThereAnyDeal, Zuordnung", itad.lookup_url(), itad_look, ih, data=itad.lookup_body([appid])) and gid.get("id"):
            probe("IsThereAnyDeal, Preise", itad.prices_url(), itad_info, ih, data=json.dumps([gid["id"]]).encode())
    # Konten, soweit eingerichtet
    kind, val = accounts.steam_id_input(settings["steam_id"])
    if kind == "id":
        if settings["steam_key"]:
            probe("Steam-Konto, Besitz", f"{STEAM_API}/IPlayerService/GetOwnedGames/v1/?steamid={val}&include_appinfo=1&key={settings['steam_key']}",
                  lambda text: f"{len(accounts.steam_owned(text))} Spiele", shown=f"{STEAM_API}/IPlayerService/GetOwnedGames/v1/")
        probe("Steam-Konto, Wunschliste", f"{STEAM_API}/IWishlistService/GetWishlist/v1/?steamid={val}",
              lambda text: f"{len(accounts.steam_wishlist(text))} Apps")
    elif kind == "vanity":
        lines.append("Steam-Konto: Profilname eingetragen, der Test braucht die Zahl (wird beim Abgleich aufgelöst)")
    if settings["gg_wish"]:
        def ggw_info(text):
            items, pages = accounts.gg_wishlist(text)
            return (f"{len(items)} Spiele erkannt, {pages} Seiten" + (f", erstes: {items[0]['name']}" if items else "")
                    + ("" if items else f". Anfang: {' '.join(re.sub(r'<[^>]+>', ' ', text)[:300].split())}"))
        probe("gg.deals-Wunschliste", settings["gg_wish"], ggw_info, shown="gg.deals-Wunschliste")
    if settings["sharenite"]:
        def sn_info(text):
            games, total, vr_tags = accounts.sharenite_page(text)
            return (f"{total if total is not None else '?'} Spiele im Profil, {len(games)} Zeilen auf Seite 1, "
                    f"{len(vr_tags)} VR-Schlagwörter im Filter" + (f", erstes: {games[0]['name']} ({games[0]['source'] or 'ohne Laden'})" if games else
                    f". Anfang: {' '.join(re.sub(r'<[^>]+>', ' ', text)[:300].split())}"))
        probe("Sharenite", settings["sharenite"] + "?sort=name_asc", sn_info)
    rsys = sorted({g.get("system") for g in (col.get("games") or {}).values() if g.get("src") == retro.SRC and retro.urls(g.get("system"))})
    if rsys:
        def dat_info(text):
            idx = retro.build_index(text)
            return f"{len(idx['rel'])} Fassungen, davon {sum(1 for r in idx['rel'] if 'De' in r[1].split(','))} mit Deutsch"
        def retool_info(text):
            obj = json.loads(text)
            return f"{len(obj.get('variants') or [])} Gruppen, Stand {(obj.get('description') or {}).get('lastUpdated', '?')}"
        dat_url, retool_url = retro.urls(rsys[0])
        probe(f"Fassungsliste {rsys[0]} (libretro)", dat_url, dat_info)
        probe(f"Retool-Liste {rsys[0]}", retool_url, retool_info)
    else:
        lines.append("Retro-Fassungen: keine Retro-Liste, nicht angefragt")
    probes.run(probe, lines, col, settings, sleep)
    for secret in (key, settings["steam_key"], settings["gg_wish"], settings["igdb_id"], settings["igdb_secret"], settings["nexus_key"], settings["itad_key"]):
        if secret:
            lines = [x.replace(secret, "…").replace(urllib.parse.quote(secret), "…") for x in lines]
    return lines
