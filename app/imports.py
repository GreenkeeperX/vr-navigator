"""Importe: deine Vergleichstabelle, Playnite-Export und Meta-Bestellungen.

Jeder Import läuft zweimal: erst als Vorschau (`dry=True`, ändert nichts), dann zum Übernehmen.
So siehst du vor dem Speichern, was erkannt wurde.
"""
import csv
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


def parse_meta(payload):
    """Meta-Bestellungen aus dem Lesezeichen (JSON mit Links und Seitentext) oder als
    eingefügter Text. Links auf Store-Seiten liefern Titel samt Meta-ID; ohne sie zählt jede
    Zeile, die nach Entfernen von Datum und Preis noch nach einem Namen aussieht."""
    payload = str(payload or "").strip()
    links, text = [], payload
    if payload.startswith("{"):
        try:
            obj = json.loads(payload)
        except ValueError:
            raise ValueError("Die Datei ist kein gültiges JSON aus dem Lesezeichen")
        links = obj.get("links") if isinstance(obj.get("links"), list) else []
        text = str(obj.get("text") or "")
    out, seen = [], set()
    for ln in links[:5000]:
        if not isinstance(ln, dict):
            continue
        mid = titles.meta_id_from(ln.get("href"))
        name, price = _clean_line(str(ln.get("text") or "")[:200])
        if not mid or not name or name.casefold() in _NOT_TITLE:
            continue
        if mid in seen:
            continue
        seen.add(mid)
        out.append({"name": name, "meta_id": mid, "price": price})
    if out:
        return out
    for raw in text.splitlines()[:MAX_ROWS]:
        name, price = _clean_line(raw.strip())
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


IMPORTERS = {"sheet": import_sheet, "playnite": import_playnite, "meta": import_meta}
