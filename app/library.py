"""Ansichten: Bibliothek, Wunschliste und „Jetzt“ als Zeilen für die Oberfläche."""
import re
from datetime import datetime, timedelta, timezone

from . import lists, pcwish, prices, store, titles, trend, wheel

STALE_H = 48        # ältere Live-Preise markiert die Oberfläche als veraltet


def _where(t):
    """Wo du den Titel besitzt: meta, pc, beide oder ""."""
    o = t.get("owned") or {}
    if o.get("meta") and o.get("pc"):
        return "beide"
    return "meta" if o.get("meta") else ("pc" if o.get("pc") else "")


def _live(t, at=None):
    """Live-Preise je Quelle, mit Kennzeichen „veraltet“. Ein Meta-Angebot, dessen Ende
    vorbei ist, gilt wieder zum Normalpreis, auch wenn noch kein neuer Abruf lief."""
    at = at or datetime.now(timezone.utc)
    today, old = at.strftime("%Y-%m-%d"), (at - timedelta(hours=STALE_H)).isoformat(timespec="seconds")
    out = {}
    for src, v in (t.get("live") or {}).items():
        if not isinstance(v, dict):
            continue
        v = dict(v, stale=(v.get("at") or "") < old)
        if src == "meta":
            if v.get("price") is None:
                continue
            if v.get("until") and v["until"] < today and v.get("base") is not None:
                v.update(price=v["base"], discount=0, until="", kind="base", ended=True)
            v["at_low"] = bool(v.get("discount")) and v.get("low") is not None and v["price"] <= v["low"]
        out[src] = v
    return out


def _pc_best(live):
    """Günstigstes Angebot für die PC-Fassung: Steam selbst, ein Händler oder ein Keyshop bei
    gg.deals, was eben am günstigsten ist (Entscheidung 26.10.2026; bis 0.5.3 ohne Keyshops)."""
    g = live.get("gg") or {}
    offers = [((live.get("steam") or {}).get("price"), "Steam"),
              (g.get("retail"), "gg.deals Händler"), (g.get("keyshops"), "gg.deals Keyshop")]
    offers = [o for o in offers if o[0] is not None]
    if not offers:
        return None
    p, src = min(offers)
    return {"price": p, "src": src}


def _gg_low(g):
    """Allzeit-Tief bei gg.deals über Händler und Keyshops, mit Herkunft für das „≈“."""
    lows = [(g.get("retail_low"), "Händler"), (g.get("keyshops_low"), "Keyshops")]
    lows = [x for x in lows if isinstance(x[0], (int, float)) and x[0] > 0]
    if not lows:
        return None, ""
    low, kind = min(lows)
    return low, f"gg.deals, Allzeit-Tief ({kind})"


def _best(hist, src, ident, price, today):
    """Bestpreis der letzten 24 Monate je Shop aus dem Verlauf, dazu die Stufe des aktuellen
    Preises: best (höchstens 2 % über dem Bestpreis), usual (am üblichen Angebot) oder ""."""
    if not ident or price is None:
        return None
    rows = list((hist.get(src) or {}).get(str(ident)) or [])
    if not rows or rows[-1][1] != price:
        rows.append([today, price])
    b = prices.best_of(rows, today)
    if not b:
        return None
    if not b["full"] and b["best"] == max(p for _, p in rows if _ >= b["since"]):
        # Kurzer Verlauf ohne jede Preisänderung: noch keine Aussage über einen Bestpreis
        return dict(b, level="", over=0.0, thin=True)
    tol = 1 + prices.BEST_TOL
    level = "best" if price <= b["best"] * tol + 0.005 else \
        "usual" if b["usual"] is not None and price <= b["usual"] * tol + 0.005 else ""
    return dict(b, level=level, over=round(price - b["best"], 2))


def _guess(price, low, at, src):
    """Bestpreis aus fremder Quelle, wenn der eigene Verlauf noch nichts hergibt. Liegt der Preis
    jetzt darunter, gilt er selbst als Bestpreis."""
    best = min(price, low)
    level = "best" if price <= best * (1 + prices.BEST_TOL) + 0.005 else ""
    return {"best": best, "best_at": at if best == low else "", "since": "", "once": True, "usual": None,
            "full": False, "level": level, "over": round(price - best, 2), "src": src}


def _best_all(best, now):
    """Bestpreis über beide Läden: der niedrigste Bestpreis von Meta und Steam, mit Laden und
    Herkunft. Daran misst die Oberfläche jeden Laden (Entscheidung 22.10.2026): war Meta einmal
    günstiger als Steam je, ist Steam jetzt nicht am Bestpreis. Je Laden kommen Stufe und Abstand
    dazu (all_level, all_over)."""
    have = [(b["best"], shop, b.get("src") or "", b.get("best_at") or "")
            for shop, b in best.items() if b and not b.get("thin") and b.get("best") is not None]
    if not have:
        return None
    low, shop, src, at = min(have)
    tol = 1 + prices.BEST_TOL
    for s, b in best.items():
        if b and now.get(s) is not None:
            b["all_level"] = "best" if now[s] <= low * tol + 0.005 else ""
            b["all_over"] = round(max(now[s] - low, 0), 2)
            b["grade"] = grade(now[s], low)
    return {"best": low, "shop": shop, "src": src, "at": at}


# Preisgüte wie im eShopKompass: „kaufen“ am Bestpreis (bis 2 %) oder höchstens 0,50 € darüber,
# „gut“ bis 15 % oder höchstens 2 € darüber, sonst „warten“. Unter 2 € Bestpreis gilt für „kaufen“
# nur die 2 % (0,50 € wären bei 1 € schon 50 %).
GRADE_BUY_EUR, GRADE_GOOD_EUR, GRADE_GOOD_PCT, GRADE_MINI = 0.5, 2.0, 15, 2.0


def grade(price, low):
    """buy, good oder wait für einen Preis gegenüber dem Bestpreis beider Läden."""
    if low is None or low <= 0 or price is None:
        return ""
    diff = price - low
    if price <= low * (1 + prices.BEST_TOL) + 0.005 or (low >= GRADE_MINI and diff <= GRADE_BUY_EUR + 0.005):
        return "buy"
    if 100 * (price / low - 1) <= GRADE_GOOD_PCT + 1e-9 or diff <= GRADE_GOOD_EUR + 0.005:
        return "good"
    return "wait"


def _near(r):
    """Ein Laden, der den Titel gerade im Angebot hat, ist „kaufen“ oder „gut“."""
    return any((r["live"].get(s) or {}).get("discount") and (r["best"].get(s) or {}).get("grade") in ("buy", "good")
               for s in ("meta", "steam"))


def row(key, t, at=None, hist=None, data=None):
    sheet = t.get("sheet") or None
    gap = None
    if sheet and sheet.get("meta_low") is not None and sheet.get("gg") is not None:
        # Aufpreis von Meta (Tief) gegenüber dem günstigsten Steam-Angebot; negativ: Meta günstiger
        gap = round(sheet["meta_low"] - sheet["gg"], 2)
    o = t.get("owned") or {}
    live = _live(t, at)
    pc = _pc_best(live)
    cb, cb_src, cb_other = crossbuy(t)
    meta_now = (live.get("meta") or {}).get("price")
    today = (at or datetime.now(timezone.utc)).strftime("%Y-%m-%d")
    hist = hist or {}
    steam_now = (live.get("steam") or {}).get("price")
    best = {"meta": _best(hist, "meta", t.get("meta_id"), meta_now, today),
            "steam": _best(hist, "steam", t.get("steam_appid"), steam_now, today)}
    # Eigener Verlauf noch zu kurz: Allzeit-Tief einer anderen Quelle, gekennzeichnet (≈)
    gg_low, gg_src = _gg_low(live.get("gg") or {})
    for shop, now_p, low, at, src in (
            ("meta", meta_now, (live.get("meta") or {}).get("low"), (live.get("meta") or {}).get("low_at"), "QuestStoreDB, Allzeit-Tief"),
            ("steam", steam_now, gg_low, "", gg_src)):
        b = best[shop]
        if (b is None or b.get("thin")) and now_p is not None and isinstance(low, (int, float)) and low > 0:
            best[shop] = _guess(now_p, low, at or "", src)
    best_all = _best_all(best, {"meta": meta_now, "steam": steam_now})
    # Preissturz (0.8.25) wie bei den PC-Wünschen: aus dem eigenen Preisverlauf je Laden (history.json, mit dem Verlauf
    # von QuestStoreDB), der deutlichere der beiden
    drops = [dict(d, shop=shop) for shop, ident, now_p in (("meta", t.get("meta_id"), meta_now), ("steam", t.get("steam_appid"), steam_now))
             if ident and (d := pcwish.drop((hist.get(shop) or {}).get(str(ident)), now_p, today))]
    drop = max(drops, key=lambda d: d["pct"], default=None)
    return {
        "key": key, "name": t["name"], "meta_id": t.get("meta_id") or "",
        "steam_appid": t.get("steam_appid") or "", "steam_sure": bool(t.get("steam_sure")),
        "steam_doubt": t.get("steam_doubt") or "", "bundle": titles.is_bundle(t),
        "where": _where(t), "pc_label": (o.get("pc") or {}).get("label") or "",
        "meta_price": (o.get("meta") or {}).get("price"),
        "wish": bool(t.get("wish")), "wish_src": sorted(t.get("wish_src") or {}), "crossbuy": cb, "crossbuy_src": cb_src, "crossbuy_other": cb_other,
        "crossbuy_hand": t.get("crossbuy") if crossbuy_origin(t) == "Hand" else None,
        "opinion": t.get("opinion") or None, "origin": titles.origins(t, data),
        "contains": [{"key": k, "name": data["titles"][k]["name"]} for k in t.get("contains") or []
                     if data and k in data["titles"]],
        "sheet": sheet, "gap": gap, "note": t.get("note") or "",
        "live": live, "pc_best": pc, "best": {k: v for k, v in best.items() if v}, "best_all": best_all,
        # Aufpreis von Meta jetzt gegenüber dem günstigsten PC-Angebot jetzt
        "gap_now": round(meta_now - pc["price"], 2) if meta_now is not None and pc else None,
        "links": titles.search_links(t), "added": t.get("added") or "",
        "rating": rating(t), "measured": measured(t), "drop": drop,
    }


def crossbuy_origin(t):
    """Woher t["crossbuy"] stammt: gespeichert seit 0.4.8; ältere Daten haben keine Angabe, dann
    gilt sie als aus der Tabelle, wenn eine Tabellenzeile da ist (die Vergleichstabelle war bis
    dahin der einzige Weg neben dem Bearbeiten), sonst als von Hand."""
    if t.get("crossbuy") is None:
        return ""
    return t.get("crossbuy_src") or ("Tabelle" if t.get("sheet") else "Hand")


def crossbuy(t):
    """Crossbuy mit Herkunft: von Hand vor VRDB (Angabe im Store) vor der Tabelle vor der
    Recherche. Dazu, was eine schwächere Quelle anders sagt (etwa „Tabelle: nein“), sonst ""."""
    own, src = t.get("crossbuy"), crossbuy_origin(t)
    vrdb, op = (t.get("vrdb") or {}).get("crossbuy"), (t.get("opinion") or {}).get("crossbuy")
    ranked = [(own if src == "Hand" else None, "Hand"), (vrdb if isinstance(vrdb, bool) else None, "VRDB"),
              (own if src == "Tabelle" else None, "Tabelle"), (op if isinstance(op, bool) else None, "Recherche")]
    have = [(v, s) for v, s in ranked if v is not None]
    if not have:
        return None, "", ""
    cb, cb_src = have[0]
    other = next((f"{s}: {'ja' if v else 'nein'}" for v, s in have[1:] if v != cb and s != "Recherche"), "")
    return cb, cb_src, other


def measured(t):
    """Vom Tool selbst gemessene Kaufgründe: Spieler bei Steam (jetzt und Spitze aus den eigenen
    Messungen), letztes Steam-Update, Meta-Version und seit wann, Spielmodi laut VRDB."""
    p, n, v, mv = t.get("play") or {}, t.get("news") or {}, t.get("vrdb") or {}, t.get("meta_ver") or {}
    out = {}
    if p.get("at"):
        out["players"] = {"now": p.get("now"), "peak": p.get("peak"), "since": p.get("since") or "", "at": p["at"]}
    if n.get("date"):
        out["update"] = {"date": n["date"], "title": n.get("title") or "", "care": trend.care(n["date"])}
    if mv.get("v"):
        out["meta_ver"] = {"v": mv["v"], "since": mv.get("since") or ""}
    if v.get("modes"):
        out["modes"] = v["modes"]
    return out


def rating(t):
    """Wertungen je Laden: Meta-Sterne (über QuestStoreDB) und Steam-Anteil positiv. Steam erst
    ab 50 Rezensionen wie in Entdecken; darunter nur die Zahl. score: 0 bis 100 zum Sortieren
    (Sterne mal 20), der bessere der beiden."""
    m, vd = ((t.get("live") or {}).get("meta") or {}), t.get("vrdb") or {}
    meta = None
    if isinstance(m.get("rating"), (int, float)) and 0 < m["rating"] <= 5:
        meta = {"stars": round(float(m["rating"]), 1), "n": m.get("ratings") if isinstance(m.get("ratings"), int) else None}
    if isinstance(vd.get("pos"), (int, float)) and vd.get("stars"):
        # Anteil 4 und 5 Sterne laut VRDB: passt zu Steams Anteil positiver Rezensionen
        meta = {"stars": vd["stars"], "n": vd.get("n") or (meta or {}).get("n"), "pos": round(vd["pos"])}
    rev = t.get("rev") or {}
    steam = None
    if isinstance(rev.get("n"), int) and rev["n"] > 0:
        steam = {"pct": rev.get("pct") if rev["n"] >= 50 else None, "n": rev["n"]}
        tr = trend.trend(rev)
        if tr:
            steam["trend"] = tr
    vals = ([meta.get("pos", meta["stars"] * 20)] if meta else []) + ([steam["pct"]] if steam and steam["pct"] is not None else [])
    score = round(max(vals)) if vals else None
    return {"meta": meta, "steam": steam, "score": score}


# Wo kaufen (0.8.15): erst was die Läden unterscheidet, dann der Preis. Jeder Grund zählt für einen
# Laden (Gewicht w); wer mindestens einen Punkt vorn liegt, gewinnt, sonst „egal“. Was nur aus der
# Recherche kommt, zählt halb und steht als unsicher da (≈). Grenzen siehe ROADMAP („groß“: 40 % und 8 €)
WB_BIG_PCT, WB_BIG_EUR = 40, 8.0       # großer Preisabstand
WB_MID_PCT, WB_MID_EUR = 20, 3.0       # spürbarer Preisabstand
WB_META_EUR = 1.0                      # Meta günstiger ab so viel
WB_RATE = 8                            # Punkte Abstand der Wertungen
WB_MP_LOW = 20                         # Steam-Spieler (Spitze) darunter: auf Steam wenig los
WB_STALE_DAYS = 365                    # eine Fassung so viel länger ohne Update
_MP = re.compile(r"(?i)multiplayer|co-op|pvp|massively")


def _days(a, b):
    try:
        return (datetime.fromisoformat(a[:10]) - datetime.fromisoformat(b[:10])).days
    except (TypeError, ValueError):
        return None


def _eur(x):
    x = round(x, 2)
    return (f"{x:.0f}" if x == int(x) else f"{x:.2f}".replace(".", ",")) + " €"


def where_buy(r):
    """Urteil „wo kaufen“ für einen Wunschtitel, den du noch nicht hast: {"shop": meta, steam oder egal,
    "grade": Preisurteil dort, "why": [{"shop", "text", "w", "guess"}]}; None ohne beide Läden."""
    if r["where"] or not r["wish"]:
        return None
    L, m = r["live"], r["measured"]
    has_m, has_s = bool(r["meta_id"] or L.get("meta")), bool(r["steam_appid"] or L.get("steam"))
    why = []

    def add(shop, text, w=1, guess=False):
        why.append({"shop": shop, "text": text, "w": w / 2 if guess else w, "guess": guess})
    if has_m != has_s:
        add("meta" if has_m else "steam", "bei Steam nicht gefunden" if has_m else "bei Meta nicht gefunden", 9)
    if r["crossbuy"] is True:
        add("meta", "Crossbuy: ein Kauf für Quest und PC", 2, r["crossbuy_src"] == "Recherche")
    pl = m.get("players") or {}
    peak = pl.get("peak") if pl.get("peak") is not None else pl.get("now")
    if _MP.search(m.get("modes") or "") and has_s and peak is not None and peak < WB_MP_LOW:
        add("meta", f"Mehrspieler, auf Steam wenig los (Spitze {peak})")
    rt = r["rating"]
    mp = ((rt.get("meta") or {}).get("pos") if (rt.get("meta") or {}).get("pos") is not None
          else round(rt["meta"]["stars"] * 20) if rt.get("meta") else None)
    sp = (rt.get("steam") or {}).get("pct")
    if mp is not None and sp is not None and abs(mp - sp) >= WB_RATE:
        add("meta" if mp > sp else "steam", f"besser bewertet ({mp} gegen {sp} %)" if mp > sp else f"besser bewertet ({sp} gegen {mp} %)")
    # Trend (0.8.26): fällt oder steigt die Steam-Wertung der letzten 30 Tage deutlich, zählt das halb; er sagt etwas
    # über die Steam-Fassung jetzt, aber oft auch über das Spiel in beiden Läden
    tr = (rt.get("steam") or {}).get("trend") or {}
    if has_m and has_s and tr.get("dir") in ("up", "down"):
        add("steam" if tr["dir"] == "up" else "meta", f"Steam-Wertung {'steigt' if tr['dir'] == 'up' else 'fällt'} "
            f"({tr['recent']} % in den letzten 30 Tagen, sonst {tr['all']} %)", 0.5)
    up, mv = (m.get("update") or {}).get("date"), (m.get("meta_ver") or {}).get("since")
    d = _days(up, mv) if up and mv else None
    if d is not None and abs(d) >= WB_STALE_DAYS:
        add("steam" if d > 0 else "meta", "Steam-Fassung jünger gepflegt" if d > 0 else "Meta-Fassung jünger gepflegt")
    op = r["opinion"] or {}
    if op.get("fassung") == "quest":
        add("meta", "Recherche: Quest-Fassung besser", 1, True)
    elif op.get("fassung") == "pc" and r["crossbuy"] is not True:
        add("steam", "Recherche: PC-Fassung besser", 1, True)
    pm, ps = (L.get("meta") or {}).get("price"), (L.get("steam") or {}).get("price")
    if pm is not None and ps is not None and pm > 0:
        diff = pm - ps
        if diff > 0 and 100 * diff / pm >= WB_BIG_PCT and diff >= WB_BIG_EUR:
            add("steam", f"{_eur(diff)} günstiger ({round(100 * diff / pm)} %)", 2)
        elif diff > 0 and 100 * diff / pm >= WB_MID_PCT and diff >= WB_MID_EUR:
            add("steam", f"{_eur(diff)} günstiger ({round(100 * diff / pm)} %)")
        elif diff <= -WB_META_EUR:
            add("meta", f"{_eur(-diff)} günstiger")
    if not why and not (has_m and has_s):
        return None
    pts = {s: sum(x["w"] for x in why if x["shop"] == s) for s in ("meta", "steam")}
    shop = "meta" if pts["meta"] - pts["steam"] >= 1 else "steam" if pts["steam"] - pts["meta"] >= 1 else "egal"
    B = r["best"]
    if shop == "egal":
        gs = [(B.get(s) or {}).get("grade") or "" for s in ("meta", "steam")]
        pg = "buy" if "buy" in gs else "good" if "good" in gs else "wait" if "wait" in gs else ""
    else:
        pg = (B.get(shop) or {}).get("grade") or ""
    why.sort(key=lambda x: (x["shop"] != shop, -x["w"]))
    return {"shop": shop, "grade": pg, "why": why}


def _sale(r):
    """Höchster Rabatt eines Wunschtitels gerade jetzt (Meta oder Steam), sonst 0."""
    return max((r["live"].get("meta") or {}).get("discount") or 0,
               (r["live"].get("steam") or {}).get("discount") or 0)


def view(data, at=None, hist=None, settings=None):
    rows = sorted((row(k, t, at, hist, data) for k, t in data["titles"].items()), key=lambda r: titles.norm(r["name"]))
    # Sim-Racing (0.8.5): auch die VR-Titel, denn Rennsimulationen spielt man oft in VR
    wmatch = wheel.matcher(store.load_json(wheel.LIST_FILE, {}))
    for r in rows:
        t = data["titles"][r["key"]]
        w = wheel.row(wmatch, t.get("steam_appid"), t.get("stag"), t["name"])
        if w:
            r["wheel"] = w
    owned = [r for r in rows if r["where"]]
    # Die Wunschliste führt auch Titel, die du inzwischen besitzt; die Oberfläche blendet sie
    # aus, solange du sie nicht ausdrücklich zeigen lässt (owned_wish zählt sie)
    wish = [r for r in rows if r["wish"]]
    for r in wish:
        r["buy"] = where_buy(r)
    read = lists.lists_read(data, settings)
    for r in wish:
        t = data["titles"][r["key"]]
        r["wish_missing"] = [] if r["where"] or t.get("wish_lists_ok") else lists.missing(t, read)
        if r["wish_missing"]:
            r["add_links"] = lists.add_links(t, (settings or {}).get("steam_wish", True))
    # Jetzt: nur Angebote, die nah am Bestpreis beider Läden liegen; die übrigen zählt now_far
    sale = sorted((r for r in wish if not r["where"] and _sale(r)), key=lambda r: (-_sale(r), titles.norm(r["name"])))
    now = [r for r in sale if _near(r)]
    far = [r for r in sale if not _near(r)]
    return {
        "now": now, "now_far": far,
        "library": owned,
        "wishlist": wish,
        "counts": {"all": len(rows), "now": len(now), "owned": len(owned), "wish": sum(not r["where"] for r in wish),
                   "owned_wish": sum(bool(r["where"]) for r in wish),
                   "meta": sum(r["where"] in ("meta", "beide") for r in rows),
                   "pc": sum(r["where"] in ("pc", "beide") for r in rows),
                   "both": sum(r["where"] == "beide" for r in rows)},
        "suggestions": titles.suggestions(data),
        # Mit der Zeile, damit „bearbeiten“ auch Titel öffnet, die weder Besitz noch Wunsch sind
        "todo": [dict(x, row=row(x["key"], data["titles"][x["key"]], at, hist, data)) for x in titles.todo(data)],
        "imports": data.get("imports") or {},
        "lists": lists.check(data, settings), "lists_stale": lists.stale(data, at),
    }
