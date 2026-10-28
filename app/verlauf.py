"""Preisverlauf je Titel (0.9.1), nach dem Vorbild des eShopKompass: je Laden die Kurve und daraus Normalpreis,
Tief mit Tag, Angebote der letzten 24 Monate, ihre übliche Dauer, Anteil der Zeit im Angebot und das letzte Angebot.

Ein Verlauf ist eine Liste [[Tag, Preis]], je Eintrag der Preis ab diesem Tag (nur Änderungen). Ein Angebot ist
jede Strecke mindestens SALE_TOL unter dem Normalpreis; Normalpreis ist der Preis, der im Zeitraum am längsten galt
(oder der Normalpreis, den der Laden jetzt nennt). Typischer Angebotspreis: der Median der Tiefstwerte je Angebot,
ab zwei Angeboten; war das letzte tiefer, gilt dieses. Ohne Netz, nichts wird gespeichert.
"""
from datetime import date, timedelta

MONTHS = 24
SALE_TOL = 0.03


def _cut(today, months=MONTHS):
    d = date.fromisoformat(today)
    y, m = divmod(d.year * 12 + d.month - 1 - months, 12)
    return date(y, m + 1, min(d.day, 28)).isoformat()


def _rows(points):
    return sorted((str(d)[:10], round(float(p), 2)) for d, p in (r for r in points or [] if isinstance(r, (list, tuple)) and len(r) == 2)
                  if d and isinstance(p, (int, float)))


def series(name, points, today, regular=None, kind=""):
    """Kennzahlen eines Verlaufs über die letzten MONTHS Monate, None ohne Punkte."""
    rows = _rows(points)
    if not rows:
        return None
    cut = _cut(today)
    before = [r for r in rows if r[0] < cut]
    win = ([(cut, before[-1][1])] if before else []) + [r for r in rows if r[0] >= cut]
    # je Strecke die Tage bis zur nächsten Änderung (die letzte bis heute)
    t1 = date.fromisoformat(today) + timedelta(days=1)
    spans = []
    for i, (d, p) in enumerate(win):
        end = date.fromisoformat(win[i + 1][0]) if i + 1 < len(win) else t1
        spans.append((d, p, max((end - date.fromisoformat(d)).days, 0)))
    if regular is None:
        held = {}
        for _, p, n in spans:
            held[p] = held.get(p, 0) + n
        regular = max(held, key=lambda p: (held[p], p))
    sales, run = [], None
    for d, p, n in spans:
        if p < regular * (1 - SALE_TOL) - 0.005:
            if run is None:
                run = {"start": d, "end": None, "low": p, "days": 0}
            run["low"] = min(run["low"], p)
            run["days"] += n
        elif run is not None:
            run["end"] = d
            sales.append(run)
            run = None
    if run is not None:
        sales.append(run)
    for s in sales:
        s["pct"] = round(100 * (1 - s["low"] / regular)) if regular else 0
    total = sum(n for _, _, n in spans) or 1
    done = sorted(s["days"] for s in sales if s["end"])
    lows = sorted(s["low"] for s in sales)
    typical = None
    if len(lows) >= 2:
        m = len(lows) // 2
        typical = lows[m] if len(lows) % 2 else round((lows[m - 1] + lows[m]) / 2, 2)
        typical = min(typical, sales[-1]["low"])
    low = min(p for _, p in win)
    return {"name": name, "kind": kind, "points": [list(r) for r in win], "regular": regular, "now": win[-1][1],
            "low": low, "low_at": max(d for d, p in win if p == low), "since": win[0][0], "full": bool(before),
            "sales": sales[-12:], "sale_count": len(sales), "typical_days": done[len(done) // 2] if done else None,
            "on_sale_pct": round(100 * sum(s["days"] for s in sales) / total), "typical": typical}


def _pack(name, out, today):
    out = [s for s in out if s]
    lows = [s["low"] for s in out]
    typ = [s["typical"] for s in out if s["typical"] is not None]
    return {"name": name, "today": today, "since": min((s["since"] for s in out), default=""),
            "series": out, "best": min(lows) if lows else None, "typical": min(typ) if typ else None}


def vr(t, hist, today=None):
    """Verlauf eines VR-Titels: Meta und Steam aus history.json, dazu der beste Preis bei gg.deals."""
    today = today or date.today().isoformat()
    L = t.get("live") or {}
    out = [series("Meta", (hist.get("meta") or {}).get(str(t.get("meta_id") or "")), today, (L.get("meta") or {}).get("base"), "meta"),
           series("Steam", (hist.get("steam") or {}).get(str(t.get("steam_appid") or "")), today, (L.get("steam") or {}).get("base"), "steam"),
           series("gg.deals (Händler und Keyshops)", (hist.get("gg") or {}).get(str(t.get("steam_appid") or "")), today, None, "gg")]
    return _pack(t.get("name") or "", out, today)


def pc(e, today=None):
    """Verlauf eines PC-Wunschs: der beste Preis bei gg.deals (eigener Verlauf ph) und je Laden von IsThereAnyDeal (sh)."""
    today = today or date.today().isoformat()
    regs = {s["s"]: s.get("r") for s in ((e.get("itad") or {}).get("shops") or [])}
    out = [series("gg.deals (Händler und Keyshops)", e.get("ph"), today, None, "gg")]
    for name, pts in sorted((e.get("sh") or {}).items()):
        out.append(series(name, pts, today, regs.get(name), "shop"))
    return _pack(e.get("name") or "", out, today)


def record_shops(e, it, day, keep_days=MONTHS * 31):
    """Preise je Laden (aus itad.prices) im Verlauf sh vermerken, nur bei Änderung; älter als keep_days fällt weg,
    der letzte Wert davor bleibt als Anfang."""
    sh = e.setdefault("sh", {})
    cut = (date.fromisoformat(day) - timedelta(days=keep_days)).isoformat()
    for s in (it or {}).get("shops") or []:
        rows = [list(r) for r in _rows(sh.get(s["s"]))]
        while len(rows) > 1 and rows[1][0] <= cut:
            rows.pop(0)
        if not rows or rows[-1][1] != s["p"]:
            rows = [r for r in rows if r[0] != day] + [[day, s["p"]]]
        sh[s["s"]] = rows


def merge_history(e, hist_rows):
    """Rückwirkender Verlauf je Laden von IsThereAnyDeal (itad.history) mit dem eigenen zusammenführen; je Tag gilt
    der eigene Wert."""
    sh = e.setdefault("sh", {})
    for name, rows in hist_rows.items():
        by_day = {d: p for d, p in rows}
        by_day.update({d: p for d, p in _rows(sh.get(name))})
        out = []
        for d in sorted(by_day):
            if not out or out[-1][1] != by_day[d]:
                out.append([d, by_day[d]])
        sh[name] = out

