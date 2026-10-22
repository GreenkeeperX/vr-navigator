"""Importe: deine Vergleichstabelle, Playnite-Export und Meta-Bestellungen.

Jeder Import läuft zweimal: erst als Vorschau (`dry=True`, ändert nichts), dann zum Übernehmen.
So siehst du vor dem Speichern, was erkannt wurde.
"""
import csv
import html
import io
import json
import re

from . import titles

MAX_ROWS = 20000


def _rows(text):
    """CSV-Zeilen; Trennzeichen Komma oder Semikolon (deutsche Tabellenprogramme)."""
    text = str(text or "").lstrip("﻿")
    head = text.split("\n", 1)[0]
    delim = ";" if head.count(";") > head.count(",") else ","
    out = []
    for i, row in enumerate(csv.reader(io.StringIO(text), delimiter=delim)):
        if i >= MAX_ROWS:
            break
        out.append([c.strip() for c in row])
    return out


def num(s):
    """Betrag aus einer Zelle: „4,2“, „12“, „19,99 €“, „1.299,00“; leer oder Text: None."""
    s = re.sub(r"[€\s]|EUR", "", str(s or ""))
    if not re.fullmatch(r"-?[\d.,]+", s):
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def yes_no(s):
    v = str(s or "").strip().casefold()
    if v in ("yes", "ja", "true", "x", "1", "y", "j"):
        return True
    if v in ("no", "nein", "false", "0", "n"):
        return False
    return None


def _col(header, *names, contains=()):
    h = [c.casefold() for c in header]
    for n in names:
        if n in h:
            return h.index(n)
    for i, c in enumerate(h):
        if any(x in c for x in contains):
            return i
    return None


def _summary(data, entries, dry, new):
    return {"dry": dry, "n": len(entries), "new": new, "entries": entries[:500]}


# ------------------------------------------------------------------ Vergleichstabelle

def parse_sheet(text):
    """Deine Vergleichstabelle: eine Zeile je Titel. Erkannt werden die Spalten Spiel (Name),
    meta (Normalpreis im Meta Store), Bestpreis (Meta-Tief), gg.deals (Bestpreis für Steam),
    Crossbuy und Links zu VRDB, QuestStoreDB, Meta oder Steam in beliebiger Spalte."""
    rows = _rows(text)
    if not rows:
        return []
    header = rows[0]
    c_name = _col(header, "spiel", "titel", "name", "title")
    c_name = 0 if c_name is None else c_name
    c_meta = _col(header, "meta", "meta-preis", "meta preis", "meta normal")
    c_low = _col(header, "bestpreis", contains=("tief", "low"))
    c_gg = _col(header, contains=("gg.deals", "ggdeals", "gg deals"))
    c_cb = _col(header, contains=("crossbuy", "cross-buy", "cross buy"))
    out = []
    for row in rows[1:]:
        name = row[c_name] if c_name < len(row) else ""
        if not name or re.match(r"https?://", name):
            continue

        def cell(c):
            return row[c] if c is not None and c < len(row) else ""
        e = {"name": name, "meta_id": "", "steam_appid": "", "links": {},
             "crossbuy": yes_no(cell(c_cb)),
             "sheet": {"meta": num(cell(c_meta)), "meta_low": num(cell(c_low)), "gg": num(cell(c_gg))}}
        for c in row:
            if not re.match(r"https?://", c):
                continue
            kind = titles.link_kind(c)
            if kind in ("vrdb", "qsdb"):
                e["links"][kind] = c
            e["meta_id"] = e["meta_id"] or titles.meta_id_from(c)
            e["steam_appid"] = e["steam_appid"] or titles.steam_id_from(c)
        if not any(v is not None for v in e["sheet"].values()):
            e["sheet"] = None
        out.append(e)
    return out


def import_sheet(data, text, dry=True):
    entries = parse_sheet(text)
    new = 0
    for e in entries:
        k = titles.find(data, e["meta_id"], e["steam_appid"], e["name"])
        e["known"] = k is not None
        new += k is None
        if dry:
            continue
        k, _ = titles.upsert(data, e["name"], e["meta_id"], e["steam_appid"])
        t = data["titles"][k]
        if e["steam_appid"]:
            t["steam_sure"] = True
        if e["crossbuy"] is not None:
            t["crossbuy"] = e["crossbuy"]
        if e["sheet"]:
            t["sheet"] = dict(e["sheet"], at=titles.now_iso())
        t["links"] = dict(t.get("links") or {}, **e["links"])
        if not t.get("owned"):
            t["wish"] = True
    if not dry:
        data["imports"]["sheet"] = {"at": titles.now_iso(), "n": len(entries), "new": new}
    return _summary(data, entries, dry, new)


# ------------------------------------------------------------------ Playnite

_VR_TAG = re.compile(r"\bvr\b", re.I)


def parse_playnite(text, data=None):
    """CSV-Export aus Playnite. Übernommen werden Spiele mit VR-Schlagwort oder -Feature, dazu
    alle, deren Name schon in deiner Liste steht. Die Steam-App-ID ist sicher, wenn eine Spalte
    Quelle oder Bibliothek „Steam“ sagt; ohne diese Spalte gilt eine Zahl als vermutete Steam-ID."""
    rows = _rows(text)
    if not rows:
        return []
    header = rows[0]
    c_name = _col(header, "name", "titel", "title")
    c_id = _col(header, "spiel-id", "game id", "gameid", "spiel id")
    c_tags = _col(header, "schlagwörter", "tags")
    c_feat = _col(header, "features")
    c_src = _col(header, "quelle", "source", "bibliothek", "library", "plattform", "platform")
    known = {titles.norm(t["name"]) for t in (data or {}).get("titles", {}).values()}
    out = []
    for row in rows[1:]:
        def cell(c):
            return row[c] if c is not None and c < len(row) else ""
        name = cell(c_name)
        if not name:
            continue
        tags = [x.strip() for x in (cell(c_tags) + "," + cell(c_feat)).split(",") if x.strip()]
        vr = any(_VR_TAG.search(x) for x in tags)
        if not vr and titles.norm(name) not in known:
            continue
        gid, src = cell(c_id), cell(c_src)
        steam, sure = "", False
        if gid.isdigit():
            if c_src is not None:
                steam, sure = (gid, True) if "steam" in src.casefold() else ("", False)
            elif int(gid) < 10_000_000:
                steam = gid           # Steam-IDs liegen darunter, GOG-IDs sind zehnstellig
        out.append({"name": name, "steam_appid": steam, "steam_sure": sure, "label": src or "PC", "vr": vr})
    return out


def import_playnite(data, text, dry=True):
    entries = parse_playnite(text, data)
    new = 0
    for e in entries:
        k = titles.find(data, "", e["steam_appid"], e["name"])
        e["known"] = k is not None
        new += k is None
        if dry:
            continue
        k, _ = titles.upsert(data, e["name"], "", e["steam_appid"])
        t = data["titles"][k]
        t["steam_sure"] = bool(t.get("steam_sure") or e["steam_sure"])
        t["owned"]["pc"] = {"src": "playnite", "label": e["label"], "at": titles.now_iso()}
    if not dry:
        data["imports"]["playnite"] = {"at": titles.now_iso(), "n": len(entries), "new": new}
    return _summary(data, entries, dry, new)


# ------------------------------------------------------------------ Meta-Bestellungen

_PRICE = re.compile(r"(?:€\s*-?\d+(?:[.,]\d{1,2})?|-?\d+(?:[.,]\d{1,2})?\s*(?:€|EUR\b))", re.I)
_MONTHS = r"(?:jan|feb|mär|mar|apr|mai|may|jun|jul|aug|sep|okt|oct|nov|dez|dec)[a-zä]*\.?"
_DATE = re.compile(
    r"\b\d{1,2}\.\s?\d{1,2}\.\s?\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b|"
    rf"\b\d{{1,2}}\.?\s+{_MONTHS}\s+\d{{4}}\b|\b{_MONTHS}\s+\d{{1,2}},?\s+\d{{4}}\b", re.I)
# Zeilen der Bestellseite, die kein Titel sind (deutsch und englisch)
_NOT_TITLE = {
    "bestellungen", "bestellung", "meine bestellungen", "bestelldetails", "details", "gesamt",
    "gesamtbetrag", "summe", "rechnung", "kaufdatum", "datum", "preis", "kostenlos", "gratis",
    "digitale produkte", "alle", "alle zeiträume", "anzeigen", "mehr anzeigen", "hilfe",
    "orders", "order", "my orders", "order details", "total", "subtotal", "invoice", "date",
    "price", "free", "digital products", "all time", "view", "see more", "help", "purchased",
    "gekauft", "zahlungsmethode", "payment method", "meta quest", "quest", "app", "apps",
}


def _clean_line(line):
    price = None
    m = _PRICE.search(line)
    if m:
        price = num(m.group(0))
    t = _DATE.sub(" ", _PRICE.sub(" ", line))
    t = re.sub(r"\s+", " ", t).strip(" -–—|·•:")
    return t, price


# Beträge in anderen Währungen (Käufe in einem anderen Land): erkennen und weglassen, ohne Preis
_MONEY = re.compile(r"(?:[¥$£]\s*-?[\d.,]+|-?[\d.,]*\d\s*(?:[¥$£]|JPY|USD|GBP)(?![a-z]))", re.I)
# Bestellseite: Block „Datum, Bestellnummer, GESAMT, Titel, Stand, Zu den Bestelldetails“
_ORDER = re.compile(r"^(?:bestellnummer|bestell-nr\.?|order (?:number|id|#)|order no\.?)\s*[:#]?\s*(\d{6,})$", re.I)
_TOTAL = re.compile(r"^(?:gesamt|gesamtbetrag|summe|total)\b", re.I)
# Transaktionen (Meta Pay): Block „Titel, Stand, Datum, Betrag“
_DONE = {"abgeschlossen", "gekauft", "completed", "complete", "purchased", "bezahlt", "paid"}
_UNDONE = {"erstattet", "rückerstattet", "zurückerstattet", "refunded", "storniert", "cancelled", "canceled",
           "fehlgeschlagen", "failed", "abgelehnt", "declined", "ausstehend", "pending"}


def _filler(line):
    """Zeile ohne Titel: leer, Datum, Betrag, Summe oder Stand."""
    t = _MONEY.sub(" ", line)
    name, _ = _clean_line(t)
    return not name or _TOTAL.match(line) or name.casefold() in _DONE | _UNDONE or name.casefold() in _NOT_TITLE


def _eur(line):
    if _MONEY.search(line):
        return None
    m = _PRICE.search(line)
    return num(m.group(0)) if m else None


def _meta_blocks(lines):
    """Käufe nach dem Aufbau der Seiten: Bestellseite (Bestellnummer als Anker) oder
    Transaktionen (Stand gefolgt von einem Datum). Erstattete oder abgebrochene Käufe fallen weg."""
    out, orders = [], [i for i, ln in enumerate(lines) if _ORDER.match(ln)]
    for i in orders:
        name, price, state = "", None, ""
        for ln in lines[i + 1:i + 8]:
            if _ORDER.match(ln):
                break
            if _TOTAL.match(ln):
                price = _eur(ln)
            elif not name and not _filler(ln):
                name = _clean_line(ln)[0]
            elif name and ln.casefold() in _DONE | _UNDONE:
                state = ln.casefold()
                break
        if name and state not in _UNDONE:
            out.append({"name": name, "meta_id": "", "price": price, "order": _ORDER.match(lines[i]).group(1)})
    if orders:
        return out
    for i, ln in enumerate(lines):
        st = ln.casefold()
        if st not in _DONE | _UNDONE or i == 0 or not any(_DATE.search(x) for x in lines[i + 1:i + 3]):
            continue
        if st in _UNDONE or _filler(lines[i - 1]):
            continue
        price = next((_eur(x) for x in lines[i + 1:i + 4] if _PRICE.search(x) or _MONEY.search(x)), None)
        out.append({"name": _clean_line(lines[i - 1])[0], "meta_id": "", "price": price})
    return out


def meta_is_wishlist(payload):
    """Kommt die Datei des Lesezeichens von deiner Wunschliste bei Meta (statt von Käufen)?"""
    payload = str(payload or "").strip()
    if not payload.startswith("{"):
        return False
    try:
        obj = json.loads(payload)
    except ValueError:
        return False
    return isinstance(obj, dict) and (obj.get("kind") == "meta-wunschliste" or "wish" in str(obj.get("page") or "").lower())


def parse_meta_wishlist(payload):
    """Wunschliste bei Meta aus dem Lesezeichen: jeder Link auf eine Store-Seite ist ein Titel mit
    Meta-ID; Name aus dem Linktext (oder dem Bildtext)."""
    obj = json.loads(str(payload).strip())
    out, seen = [], set()
    for ln in (obj.get("links") if isinstance(obj.get("links"), list) else [])[:5000]:
        if not isinstance(ln, dict):
            continue
        mid = titles.meta_id_from(ln.get("href"))
        name = _clean_line(html.unescape(str(ln.get("text") or "")[:200]))[0]
        if not mid or mid in seen:
            continue
        if not name or name.casefold() in _NOT_TITLE:
            # Bild-Link ohne Text: der nächste Link mit derselben ID trägt meist den Namen
            continue
        seen.add(mid)
        out.append({"name": name, "meta_id": mid, "price": None})
    return out


def parse_meta(payload):
    """Meta-Bestellungen aus dem Lesezeichen (JSON mit Links und Seitentext) oder als
    eingefügter Text. Der Reihe nach: Links auf Store-Seiten (Titel samt Meta-ID), dann der
    Aufbau der Bestellseite oder der Transaktionen, zuletzt jede Zeile, die nach Entfernen von
    Datum und Preis noch nach einem Namen aussieht."""
    payload = str(payload or "").strip()
    links, text = [], payload
    if payload.startswith("{"):
        try:
            obj = json.loads(payload)
        except ValueError:
            raise ValueError("Die Datei ist kein gültiges JSON aus dem Lesezeichen")
        links = obj.get("links") if isinstance(obj.get("links"), list) else []
        text = str(obj.get("text") or "")
    text = html.unescape(text)
    out, seen = [], set()
    for ln in links[:5000]:
        if not isinstance(ln, dict):
            continue
        mid = titles.meta_id_from(ln.get("href"))
        name, price = _clean_line(html.unescape(str(ln.get("text") or "")[:200]))
        if not mid or not name or name.casefold() in _NOT_TITLE:
            continue
        if mid in seen:
            continue
        seen.add(mid)
        out.append({"name": name, "meta_id": mid, "price": price})
    if out:
        return out
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()[:MAX_ROWS]]
    lines = [x for x in lines if x]
    blocks = _meta_blocks(lines)
    if blocks:
        for e in blocks:
            n = titles.norm(e["name"])
            if n not in seen and len(e["name"]) <= 120:
                seen.add(n)
                out.append(e)
        return out
    for raw in lines:
        name, price = _clean_line(raw)
        if len(name) < 2 or len(name) > 120 or name.casefold() in _NOT_TITLE:
            continue
        if not re.search(r"[^\W\d_]", name):
            continue          # nur Zahlen und Zeichen
        n = titles.norm(name)
        if n in seen:
            continue
        seen.add(n)
        out.append({"name": name, "meta_id": "", "price": price})
    return out


def import_meta(data, payload, dry=True):
    if meta_is_wishlist(payload):
        return import_meta_wishlist(data, payload, dry)
    entries = parse_meta(payload)
    new = 0
    for e in entries:
        k = titles.find(data, e["meta_id"], "", e["name"])
        e["known"] = k is not None
        new += k is None
        if dry:
            continue
        k, _ = titles.upsert(data, e["name"], e["meta_id"], "")
        t = data["titles"][k]
        t["owned"]["meta"] = {"src": "meta", "at": titles.now_iso(), "price": e["price"]}
    if not dry:
        data["imports"]["meta"] = {"at": titles.now_iso(), "n": len(entries), "new": new}
    return _summary(data, entries, dry, new)


def import_meta_wishlist(data, payload, dry=True):
    """Deine Wunschliste bei Meta. Sie ersetzt, was die Meta-Wunschliste zuletzt sagte: Titel, die
    dort fehlen, verlieren diese Quelle (siehe titles.set_wishes)."""
    entries = parse_meta_wishlist(payload)
    if not entries:
        raise ValueError("Keine Titel auf der Wunschliste erkannt. Bitte die Seite neu laden und noch einmal versuchen")
    new, keys = 0, []
    for e in entries:
        k = titles.find(data, e["meta_id"], "", e["name"])
        e["known"] = k is not None
        new += k is None
        if not dry:
            k, _ = titles.upsert(data, e["name"], e["meta_id"], "")
            keys.append(k)
    res = _summary(data, entries, dry, new)
    if not dry:
        res["wish_added"], res["wish_removed"] = titles.set_wishes(data, "meta", keys)
        data["imports"]["metawish"] = {"at": titles.now_iso(), "n": len(entries), "new": new}
    res["what"] = "Meta-Wunschliste"
    return res


# ------------------------------------------------------------------ gg.deals-Wunschliste als CSV

def parse_ggwish(text):
    """Wunschliste von gg.deals als Tabelle (Spalte Name), etwa aus einem eigenen Export."""
    rows = _rows(text)
    if not rows:
        return []
    c = _col(rows[0], "name", "titel", "spiel", "title")
    c = 0 if c is None else c
    out, seen = [], set()
    for row in rows[1:]:
        name = row[c] if c < len(row) else ""
        if name and not re.match(r"https?://", name) and titles.norm(name) not in seen:
            seen.add(titles.norm(name))
            out.append({"name": name, "slug": ""})
    return out


def import_ggwish(data, text, dry=True):
    from . import accounts
    items = parse_ggwish(text)
    entries = []
    for it in items:
        entries.append({"name": it["name"], "known": titles.find(data, "", "", it["name"]) is not None})
    res = _summary(data, entries, dry, 0)
    if not dry:
        r = accounts.apply_gg_wishes(data, items)
        res.update(wish_added=r["wish_added"], wish_removed=r["wish_removed"], unknown=r["unknown"])
        data["imports"]["ggwish"] = {"at": titles.now_iso(), "n": len(items), "new": 0}
    res["what"] = "gg.deals-Wunschliste"
    res["note"] = "Es zählen nur Titel, die das Tool schon kennt; ob ein unbekanntes Spiel VR kann, lässt sich ohne Steam-ID nicht prüfen."
    return res


# ------------------------------------------------------------------ Meinungen (Recherche)

OPINION_MARK = "vr-navigator-meinungen"
OPINION_TEXT = {"fazit": 600, "fassung_grund": 400, "mehrspieler_stand": 300, "pflege": 400,
                "komfort": 300, "warnungen": 400, "crossbuy_grund": 300}
OPINION_ENUM = {"fassung": ("quest", "pc", "gleich", ""), "mehrspieler": ("lebendig", "ruhig", "tot", "keiner", "")}


def parse_opinions(obj):
    """Datei mit recherchierten Meinungen, je Titel: Kurzfazit, bessere Fassung (quest, pc,
    gleich) mit Grund, Mehrspieler (lebendig, ruhig, tot, keiner) mit Stand, Pflege, Crossbuy
    laut Store und Community, Komfort, Warnungen, Quellen mit Datum. Unbekannte Felder fallen weg,
    Texte werden gekürzt, Links nur mit http(s)."""
    if not isinstance(obj, dict) or obj.get("app") != OPINION_MARK or not isinstance(obj.get("titles"), list):
        raise ValueError("Keine Meinungen-Datei")
    stand = str(obj.get("stand") or "")[:10]
    out = []
    for e in obj["titles"][:2000]:
        if not isinstance(e, dict) or not str(e.get("name") or "").strip():
            continue
        o = {"name": str(e["name"]).strip()[:200], "meta_id": re.sub(r"\D", "", str(e.get("meta_id") or ""))[:20],
             "steam_appid": re.sub(r"\D", "", str(e.get("steam_appid") or ""))[:12],
             "stand": str(e.get("stand") or stand)[:10]}
        for f, n in OPINION_TEXT.items():
            o[f] = str(e.get(f) or "").strip()[:n]
        for f, allowed in OPINION_ENUM.items():
            v = str(e.get(f) or "").strip().casefold()
            o[f] = v if v in allowed else ""
        o["crossbuy"] = e.get("crossbuy") if e.get("crossbuy") in (True, False) else None
        o["quellen"] = [{"url": str(q["url"])[:500], "titel": str(q.get("titel") or "")[:200], "datum": str(q.get("datum") or "")[:10]}
                        for q in (e.get("quellen") or [])[:12]
                        if isinstance(q, dict) and re.match(r"https?://", str(q.get("url") or ""))]
        out.append(o)
    return out


def import_opinions(data, text, dry=True):
    """Meinungen zu Titeln, die das Tool kennt (Kennung oder Name). Neue Titel legt die Datei
    nicht an. Crossbuy aus der Recherche gilt nur, wo du ihn nicht selbst gesetzt hast."""
    items = parse_opinions(json.loads(text))
    entries, unknown = [], []
    for o in items:
        k = titles.find(data, o["meta_id"], o["steam_appid"], o["name"])
        if k is None:
            unknown.append(o["name"])
            continue
        entries.append({"name": data["titles"][k]["name"], "known": True})
        if dry:
            continue
        t = data["titles"][k]
        rec = {f: v for f, v in o.items() if f not in ("name", "meta_id", "steam_appid") and v not in ("", None, [])}
        rec["at"] = titles.now_iso()
        t["opinion"] = rec
    res = _summary(data, entries, dry, 0)
    if not dry:
        data["imports"]["opinions"] = {"at": titles.now_iso(), "n": len(entries), "new": 0}
    res["what"] = "Meinungen"
    if unknown:
        res["note"] = f"Nicht zugeordnet ({len(unknown)}): " + ", ".join(unknown[:20]) + (" …" if len(unknown) > 20 else "")
    return res


# ------------------------------------------------------------------ Eine Datei, egal welche

KINDS = {"sheet": "Vergleichstabelle", "playnite": "Playnite-Export", "meta": "Meta-Käufe",
         "ggwish": "gg.deals-Wunschliste", "opinions": "Meinungen"}


def detect(text):
    """Welche Art von Datei? Am Aufbau erkannt: JSON des Lesezeichens, Playnite-CSV an
    Sortiername/Schlagwörtern/Spiel-ID, die Vergleichstabelle an Spiel/Bestpreis/gg.deals/Crossbuy,
    eine gg.deals-Wunschliste an Links auf geteilte Wunschlisten. Sonst Seitentext von Meta."""
    t = str(text or "").lstrip("\ufeff").strip()
    if not t:
        raise ValueError("Nichts zum Einlesen")
    if t.startswith("{") or t.startswith("["):
        try:
            obj = json.loads(t)
        except ValueError:
            raise ValueError("Die Datei sieht nach JSON aus, ist aber keins")
        if isinstance(obj, dict) and str(obj.get("kind") or "").startswith("meta"):
            return "meta"
        if isinstance(obj, dict) and obj.get("app") == OPINION_MARK:
            return "opinions"
        if isinstance(obj, dict) and obj.get("app") == "vr-navigator":
            raise ValueError("Das ist eine Sicherung des VR-Navigators; die spielst du unter Sicherung ein")
        raise ValueError("Diese JSON-Datei kennt das Tool nicht")
    rows = _rows(t)[:4]
    header = [c.casefold() for c in rows[0]] if rows else []
    if len(header) >= 2:
        if any("gg.deals/wishlist" in c or "gg.deals/de/wishlist" in c for r in rows for c in r):
            return "ggwish"
        if any(h in header for h in ("sortiername", "sorting name", "schlagwörter", "tags", "features",
                                     "spiel-id", "game id", "gameid")):
            return "playnite"
        if any(h in ("spiel", "bestpreis", "crossbuy", "meta") or "gg.deals" in h for h in header):
            return "sheet"
    return "meta"


def import_auto(data, text, dry=True):
    kind = detect(text)
    res = IMPORTERS[kind](data, text, dry=dry)
    res["kind"] = kind
    res.setdefault("what", KINDS[kind])
    return res


IMPORTERS = {"sheet": import_sheet, "playnite": import_playnite, "meta": import_meta, "ggwish": import_ggwish,
             "opinions": import_opinions}
