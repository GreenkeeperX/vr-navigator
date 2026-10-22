"""Titel: Namen vergleichen, Kennungen aus Links lesen, Meta- und Steam-Einträge zusammenführen.

Ein Titel ist ein Eintrag mit bis zu zwei Kennungen: der Meta-ID (Quest Store) und der
Steam-App-ID. Gleiche Kennung oder gleicher Name heißt gleicher Titel. Was der Name nicht
sicher trifft, korrigierst du in der Oberfläche, indem du eine Kennung einträgst; trägt ein
anderer Titel sie schon, werden beide zusammengeführt.
"""
import functools
import re
import unicodedata
import urllib.parse
from datetime import datetime, timezone


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@functools.lru_cache(maxsize=50000)
def norm(title):
    """Titel zum Vergleichen: ohne ™ ®, Akzente, Satzzeichen und Groß-/Kleinschreibung."""
    t = re.sub(r"[™®©]", "", str(title or ""))
    t = re.sub(r"[̀-ͯ]", "", unicodedata.normalize("NFKD", t))
    t = unicodedata.normalize("NFKC", t).casefold()
    # Typografische Apostrophe: „Rover’s“ und „Rover's“ sind derselbe Titel
    t = t.replace("’", "").replace("'", "")
    return " ".join(re.sub(r"[^\w]+", " ", t).split())


def base_norm(title):
    """Wie norm, aber ohne Anhänge, die nur Fassungen unterscheiden: eine Klammer am Ende
    („Moon Rover (Bundle)“) und VR-Zusätze („Moon Rover VR“ ist „Moon Rover“)."""
    t = re.sub(r"\s*[(\[][^)\]]*[)\]]\s*$", "", str(title or ""))
    n = norm(t)
    n = re.sub(r"\s+(vr|quest|pcvr|for quest|meta quest)$", "", n)
    return n or norm(title)


_SLUG_RES = (
    re.compile(r"vrdb\.app/game/([^/?#\s]+)/\d{6,}", re.I),
    re.compile(r"queststoredb\.com/(?:game|app|add-on|bundle)/([^/?#\s]+?)-\d{6,}", re.I),
)


def store_names(t):
    """Namen, unter denen die Shops den Titel wohl führen: der eigene Name, derselbe ohne
    Klammer am Ende und, wenn ein VRDB- oder QuestStoreDB-Link da ist, der Name aus dessen
    Adresse. Der passt zur Meta-ID, auch wenn der Name aus einer Tabelle anders lautet. Zuletzt
    die weiteren Namen (aliases): frühere Namen und die, die das Tool bei Meta und Steam gelernt
    hat."""
    out = [t["name"], re.sub(r"\s*[(\[][^)\]]*[)\]]\s*$", "", t["name"])]
    if t.get("meta_id"):
        for link in (t.get("links") or {}).values():
            for rx in _SLUG_RES:
                m = rx.search(str(link or ""))
                if m:
                    out.append(m.group(1).replace("-", " "))
    out += list(t.get("aliases") or [])
    seen, names = set(), []
    for x in out:
        if x and norm(x) not in seen:
            seen.add(norm(x))
            names.append(x)
    return names


# ------------------------------------------------------------------ Kennungen aus Links

_META_RES = (
    # meta.com/experiences/123…, auch mit Sprache und Name davor
    re.compile(r"meta\.com/(?:[a-z]{2}-[a-z]{2}/)?experiences/(?:[^/?#\s]+/)?(\d{6,})", re.I),
    re.compile(r"oculus\.com/experiences/(?:quest|rift|go|app)/(?:[^/?#\s]+/)?(\d{6,})", re.I),
    # queststoredb.com/game/<slug>-<ID>/
    re.compile(r"queststoredb\.com/(?:game|app|add-on|bundle)/[^/?#\s]*?-?(\d{6,})(?=[/?#\s]|$)", re.I),
    # vrdb.app/game/<slug>/<ID>
    re.compile(r"vrdb\.app/game/[^/?#\s]+/(\d{6,})", re.I),
)
_STEAM_RE = re.compile(r"(?:store\.steampowered\.com|steamcommunity\.com|steamdb\.info)/app/(\d+)", re.I)


def meta_id_from(text):
    for rx in _META_RES:
        m = rx.search(str(text or ""))
        if m:
            return m.group(1)
    return ""


def steam_id_from(text):
    m = _STEAM_RE.search(str(text or ""))
    return m.group(1) if m else ""


def link_kind(url):
    """Art eines gespeicherten Links: vrdb, qsdb, meta, steam oder ""."""
    host = (urllib.parse.urlsplit(str(url or "")).hostname or "").lower()
    for k, h in (("vrdb", "vrdb.app"), ("qsdb", "queststoredb.com"), ("meta", "meta.com"),
                 ("meta", "oculus.com"), ("steam", "steampowered.com")):
        if host == h or host.endswith("." + h):
            return k
    return ""


# ------------------------------------------------------------------ Titel und Zusammenführen

def new_title(name):
    return {"name": str(name).strip(), "meta_id": "", "steam_appid": "", "steam_sure": False,
            "owned": {}, "wish": False, "crossbuy": None, "sheet": None, "links": {},
            "note": "", "added": now_iso()}


def _key(t):
    if t.get("meta_id"):
        return "meta-" + t["meta_id"]
    if t.get("steam_appid"):
        return "steam-" + t["steam_appid"]
    return "name-" + (norm(t["name"]) or "leer")


def find(data, meta_id="", steam_appid="", name=""):
    """Schlüssel des passenden Titels oder None. Kennungen gehen vor dem Namen; ein Name trifft
    nur bei gleicher Schreibweise (norm) und nur einen Titel, dessen Kennung derselben Art nicht
    widerspricht. Ähnliche Namen schlägt `suggestions` zur Bestätigung vor."""
    titles = data["titles"]
    if meta_id:
        for k, t in titles.items():
            if t.get("meta_id") == meta_id:
                return k
    if steam_appid:
        for k, t in titles.items():
            if t.get("steam_appid") == steam_appid:
                return k
    n = norm(name)
    if not n:
        return None
    for k, t in titles.items():
        if meta_id and t.get("meta_id") and t["meta_id"] != meta_id:
            continue
        if steam_appid and t.get("steam_appid") and t["steam_appid"] != steam_appid:
            continue
        if n in {norm(x) for x in [t["name"]] + list(t.get("aliases") or [])}:
            return k
    return None


def add_alias(t, name):
    """Früherer oder anderer Name eines Titels (nach Zusammenführen oder Umbenennen), damit ein
    späterer Import mit diesem Namen den Titel wiederfindet, statt ihn neu anzulegen."""
    if name and norm(name) != norm(t["name"]) and norm(name) not in {norm(x) for x in t.get("aliases") or []}:
        t.setdefault("aliases", []).append(name)


def add(data, t):
    """Neuen Titel ablegen, Schlüssel zurück. Ein belegter Schlüssel bekommt eine Nummer."""
    k, i = _key(t), 2
    while k in data["titles"]:
        k, i = f"{_key(t)}-{i}", i + 1
    data["titles"][k] = t
    return k


def merge(data, keep, gone):
    """Titel `gone` in `keep` aufgehen lassen: Kennungen, Besitz, Wunsch, Links und Notizen
    bleiben alle erhalten; bei Widerspruch gilt `keep`."""
    if keep == gone:
        return keep
    a, b = data["titles"][keep], data["titles"].pop(gone)
    for f in ("meta_id", "steam_appid"):
        a[f] = a.get(f) or b.get(f) or ""
    a["steam_sure"] = bool(a.get("steam_sure") or (b.get("steam_sure") and a["steam_appid"] == b.get("steam_appid")))
    owned = dict(b.get("owned") or {})
    owned.update(a.get("owned") or {})
    a["owned"] = owned
    a["wish"] = bool(a.get("wish") or b.get("wish"))
    ws = dict(b.get("wish_src") or {})
    ws.update(a.get("wish_src") or {})
    if ws:
        a["wish_src"] = ws
    if a.get("crossbuy") is None:
        a["crossbuy"] = b.get("crossbuy")
    if b.get("opinion") and (b["opinion"].get("at") or "") > ((a.get("opinion") or {}).get("at") or ""):
        a["opinion"] = b["opinion"]
    if b.get("sheet") and (not a.get("sheet") or (b["sheet"].get("at") or "") > (a["sheet"].get("at") or "")):
        a["sheet"] = b["sheet"]
    live = dict(b.get("live") or {})
    for src, v in (a.get("live") or {}).items():
        if (v.get("at") or "") >= ((live.get(src) or {}).get("at") or ""):
            live[src] = v
    if live:
        a["live"] = live
    links = dict(b.get("links") or {})
    links.update(a.get("links") or {})
    a["links"] = links
    notes = [x for x in (a.get("note"), b.get("note")) if x]
    a["note"] = "\n".join(dict.fromkeys(notes))
    a["added"] = min(x for x in (a.get("added"), b.get("added"), now_iso()) if x)
    for x in [b.get("name")] + list(b.get("aliases") or []):
        add_alias(a, x)
    return keep


def upsert(data, name, meta_id="", steam_appid=""):
    """Titel finden oder anlegen; fehlende Kennungen werden ergänzt. Liefert (Schlüssel, neu)."""
    k = find(data, meta_id, steam_appid, name)
    if k is None:
        t = new_title(name)
        t["meta_id"], t["steam_appid"] = meta_id or "", steam_appid or ""
        return add(data, t), True
    t = data["titles"][k]
    for field, val in (("meta_id", meta_id), ("steam_appid", steam_appid)):
        if not val or t.get(field):
            continue
        # Trägt ein zweiter Titel die neue Kennung schon (erst Meta, dann Steam importiert),
        # fallen beide zusammen
        other = next((k2 for k2, t2 in data["titles"].items() if k2 != k and t2.get(field) == val), None)
        if other:
            merge(data, k, other)
        t[field] = val
    return k, False


# ------------------------------------------------------------------ Wunschliste aus Quellen

WISH_SOURCES = {"meta": "Meta-Wunschliste", "steam": "Steam-Wunschliste", "gg": "gg.deals-Wunschliste",
                "hand": "von Hand"}


def set_wishes(data, src, keys, stamp=None):
    """Die Wunschliste einer Quelle übernehmen. keys: Titel, die dort stehen. Sie kommen auf die
    Wunschliste (auch wenn du sie schon besitzt; die Oberfläche zeigt sie dann gesondert).
    Wer die Quelle trug und dort fehlt, verliert sie; ohne Quelle fällt er von der Wunschliste.
    Titel ganz ohne Quellenangabe (aus der Tabelle, vor 0.3) bleiben, wie sie sind.
    Hast du einen Titel von Hand entfernt (wish_off), holt ihn dieselbe Quelle erst zurück,
    nachdem er dort einmal gefehlt hat. Liefert (dazu, entfernt) als Namenslisten."""
    stamp = stamp or now_iso()
    keys = set(keys)
    added, removed = [], []
    for k, t in data["titles"].items():
        ws = dict(t.get("wish_src") or {})
        off = list(t.get("wish_off") or [])
        if k in keys:
            if src in off:
                continue
            ws.setdefault(src, stamp)
            if not t.get("wish"):
                t["wish"] = True
                added.append(t["name"])
        else:
            if src in off:
                off.remove(src)
            if src in ws:
                del ws[src]
                if not ws and t.get("wish"):
                    t["wish"] = False
                    removed.append(t["name"])
        if ws:
            t["wish_src"] = ws
        else:
            t.pop("wish_src", None)
        if off:
            t["wish_off"] = off
        else:
            t.pop("wish_off", None)
    return added, removed


def wish_by_hand(t, on):
    """Wunsch von Hand setzen oder nehmen. Beim Nehmen merkt sich der Titel die Quellen, die ihn
    führten, damit der nächste Abgleich ihn nicht gleich zurückholt."""
    ws = dict(t.get("wish_src") or {})
    if on:
        t["wish"] = True
        ws["hand"] = now_iso()
        t["wish_src"] = ws
        t.pop("wish_off", None)
    else:
        t["wish"] = False
        off = [s for s in ws if s != "hand"]
        if off:
            t["wish_off"] = sorted(set(off) | set(t.get("wish_off") or []))
        t.pop("wish_src", None)


def suggestions(data):
    """Paare, die wohl derselbe Titel sind, aber nicht sicher: gleicher Name ohne Klammer- und
    VR-Zusatz, einer nur mit Meta-, der andere nur mit Steam- oder PC-Seite. Verglichen werden
    auch die Namen aus VRDB- und QuestStoreDB-Links (store_names) und alles ohne Leerzeichen
    („Sky-Glider“ ist „SkyGlider“), so findet ein Tabellentitel
    mit abweichendem Namen seinen Meta-Kauf. Abgelehnte Paare (data["not_same"]) kommen nicht wieder."""
    rejected = {tuple(sorted(p)) for p in data.get("not_same") or [] if isinstance(p, list) and len(p) == 2}
    by_base = {}
    for k, t in data["titles"].items():
        for b in dict.fromkeys(base_norm(x).replace(" ", "") for x in store_names(t)):
            by_base.setdefault(b, []).append(k)
    out, seen = [], set()
    for keys in by_base.values():
        for i, a in enumerate(keys):
            for b in keys[i + 1:]:
                ta, tb = data["titles"][a], data["titles"][b]
                pair = tuple(sorted((a, b)))
                if a == b or pair in rejected or pair in seen:
                    continue
                seen.add(pair)
                if (ta.get("meta_id") and tb.get("meta_id")) or (ta.get("steam_appid") and tb.get("steam_appid")):
                    continue          # zwei Kennungen derselben Art: sicher verschiedene Einträge
                out.append({"a": a, "b": b, "a_name": ta["name"], "b_name": tb["name"]})
    return out


def set_ids(data, key, meta_id=None, steam_appid=None):
    """Kennungen von Hand setzen ("" löscht). Trägt ein anderer Titel die Kennung, geht er in
    diesem auf. Liefert den Schlüssel, unter dem der Titel danach steht."""
    t = data["titles"][key]
    for field, val in (("meta_id", meta_id), ("steam_appid", steam_appid)):
        if val is None:
            continue
        val = str(val).strip()
        if val and not val.isdigit():
            raise ValueError(f"{'Meta-ID' if field == 'meta_id' else 'Steam-App-ID'} besteht nur aus Ziffern")
        if val:
            for k2, t2 in list(data["titles"].items()):
                if k2 != key and t2.get(field) == val:
                    merge(data, key, k2)
        old = t.get(field) or ""
        t[field] = val
        if field == "steam_appid":
            t["steam_sure"] = bool(val)
            t.pop("steam_doubt", None)
            if old and not val:
                # Von Hand entfernt: die Steam-Suche schlägt diese App nicht wieder vor
                t["steam_wrong"] = sorted(set(t.get("steam_wrong") or []) | {old})
    return key


# ------------------------------------------------------------------ Zuordnung

_BUNDLE = re.compile(r"\b(bundle|pack|collection)\b", re.I)


def is_bundle(t):
    return bool(_BUNDLE.search(t.get("name") or ""))


def names_match(t, other):
    """Passt ein Name aus einem Shop zu einem der Namen des Titels (ohne Klammer- und VR-Zusatz)?"""
    b = base_norm(other)
    return bool(b) and b in {base_norm(x) for x in store_names(t)}


def steam_verdict(t, info):
    """Steam-ID prüfen, die nur aus einem Namen stammt (Playnite, Suche). info: Eintrag aus
    data["steam_apps"] (Name und VR laut Store) oder None, wenn noch nicht gefragt.
    Liefert (sicher, Grund): (True, "") passt; (False, Grund) passt nicht; (None, "") ungeprüft."""
    if not info:
        return None, ""
    name = info.get("name") or ""
    if not name:
        return False, "Steam zeigt die App im deutschen Store nicht"
    if not info.get("vr"):
        return False, f"laut Steam ohne VR: {name}"
    if not names_match(t, name):
        return False, f"Name bei Steam: {name}"
    return True, ""


def todo(data):
    """Was das Tool nicht selbst klären konnte, je Titel mit Grund: Steam-IDs, die die Prüfung
    nicht bestätigt hat, und Titel, die QuestStoreDB unter keinem ihrer Namen fand (Meta-Käufe
    ohne Meta-ID und Titel ganz ohne Kennung)."""
    out = []
    for k, t in data["titles"].items():
        if t.get("steam_appid") and not t.get("steam_sure") and t.get("steam_doubt"):
            out.append({"key": k, "name": t["name"], "kind": "steam", "steam_appid": t["steam_appid"],
                        "why": t["steam_doubt"]})
        if t.get("meta_miss") and not t.get("meta_id") and \
                ((t.get("owned") or {}).get("meta") or not t.get("steam_appid")):
            why = "bei QuestStoreDB nicht gefunden, gesucht als " + ", ".join(f"„{x}“" for x in store_names(t)[:4])
            if is_bundle(t):
                why = "Bundle: " + why + ". Trag die enthaltenen Spiele einzeln ein oder die Meta-ID des Bundles"
            out.append({"key": k, "name": t["name"], "kind": "meta", "why": why,
                        "owned_meta": bool((t.get("owned") or {}).get("meta"))})
    return sorted(out, key=lambda x: (x["kind"] != "steam", norm(x["name"])))


# ------------------------------------------------------------------ Anzeige

def search_links(t):
    """Links zum Nachschlagen: Shops, Datenbanken und Meinungen (Reddit, Google)."""
    name = t["name"]
    q = urllib.parse.quote_plus
    out = []
    links = t.get("links") or {}
    if t.get("meta_id"):
        out.append(("Meta", f"https://www.meta.com/experiences/{t['meta_id']}/"))
    if links.get("qsdb"):
        out.append(("QuestStoreDB", links["qsdb"]))
    if links.get("vrdb"):
        out.append(("VRDB", links["vrdb"]))
    if t.get("steam_appid"):
        out.append(("Steam", f"https://store.steampowered.com/app/{t['steam_appid']}/"))
    if links.get("gg"):
        out.append(("gg.deals", links["gg"]))
    out.append(("Reddit", f"https://www.reddit.com/search/?q={q(name + ' quest vs steam')}"))
    out.append(("Google", f"https://www.google.com/search?q={q(name + ' VR Quest oder Steam reddit')}"))
    return [{"label": a, "url": b} for a, b in out]
