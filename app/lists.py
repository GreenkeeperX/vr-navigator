"""Wunschliste abgleichen: das Tool ist die Stelle für deine Wünsche, die Wunschlisten bei Meta,
Steam und gg.deals sind Spiegel, die der Abgleich liest (Entscheidung 22.10.2026). Was sich
abrufen lässt, ordnet das Tool selbst zu; hier steht nur, was danach nicht zusammenpasst:

- table: Wunsch nur aus der alten Vergleichstabelle, auf keiner Wunschliste und nicht von Hand,
- owned: schon gekauft (Meta oder PC), steht aber noch auf einer Wunschliste,
- off: im Tool entfernt, steht aber noch auf einer Wunschliste,
- missing (bis 0.8.11): gewünscht, fehlt aber auf der Wunschliste eines Ladens, der ihn führt. Ab 0.8.12 kein Fall
  mehr, weil das Tool die Preise beider Läden ohnehin holt; die Karte nennt es weiter mit Link zum Nachtragen.

Gekauft und auf keiner Laden-Wunschliste löst `auto` im Abgleich selbst (der Wunsch ist erfüllt).

Ohne Netz; die Oberfläche bietet je Gruppe eine Aktion für alle."""

import urllib.parse
from datetime import datetime, timedelta, timezone

from . import titles

# Quellen, die der Server selbst liest, und solche, die nur das Lesezeichen bringt
LINKS = {"steam": "https://store.steampowered.com/wishlist/", "gg": "https://gg.deals/wishlist/"}
MANUAL_DAYS = 30            # so lange gilt eine per Lesezeichen gelesene Liste als aktuell


def _src_names(srcs):
    return [titles.WISH_SOURCES.get(s, s) for s in srcs if s != "hand"]


def _owned_text(t):
    o = t.get("owned") or {}
    parts = []
    if o.get("meta"):
        parts.append("bei Meta")
    if o.get("pc"):
        parts.append("am PC" + (f" ({o['pc']['label']})" if o["pc"].get("label") and o["pc"]["label"] != "PC" else ""))
    return " und ".join(parts)


def _links(t, srcs):
    """Wo du einen Titel von der Wunschliste eines Ladens nimmst: direkt die Spielseite (bei
    gg.deals ohne bekannte Seite die Suche), sonst die Wunschliste selbst."""
    out = []
    pages = {x["label"]: x["url"] for x in add_links(t)}
    for s in srcs:
        label = "Meta" if s == "meta" else titles.WISH_SOURCES.get(s, s).replace("-Wunschliste", "")
        url = pages.get(label) or LINKS.get(s)
        if url and (s == "meta" or s in LINKS):
            out.append({"label": label, "url": url})
    return out


def add_links(t, steam=True):
    """Wo du einen Titel auf die Wunschliste setzt: die Seite im Laden (Herz bei Meta und
    Steam) und bei gg.deals die Spielseite oder die Suche. steam=False: ohne Steam, wenn du die
    Steam-Wunschliste nicht pflegst."""
    out = []
    if t.get("meta_id"):
        out.append({"label": "Meta", "url": f"https://www.meta.com/experiences/{t['meta_id']}/"})
    if steam and t.get("steam_appid"):
        out.append({"label": "Steam", "url": f"https://store.steampowered.com/app/{t['steam_appid']}/"})
    gg = (t.get("links") or {}).get("gg") or ""
    out.append({"label": "gg.deals", "url": gg if gg.startswith("https://gg.deals/") else
                "https://gg.deals/search/?title=" + urllib.parse.quote_plus(t["name"])})
    return out


def missing(t, read):
    """Läden, auf deren Wunschliste ein gewünschter Titel fehlt, obwohl es ihn dort gibt:
    „meta“ (Meta-ID, die Meta-Wunschliste wurde schon gelesen) und „pc“ (Steam-ID, weder auf
    der Steam- noch auf der gg.deals-Wunschliste; nur wenn eine davon gelesen wird)."""
    ws = t.get("wish_src") or {}
    out = []
    if t.get("meta_id") and "meta" in read and "meta" not in ws:
        out.append("meta")
    if t.get("steam_appid") and read & {"steam", "gg"} and not ws.keys() & {"steam", "gg"}:
        out.append("pc")
    return out


def lists_read(data, settings=None):
    """Welche Wunschlisten das Tool liest: meta (einmal per Lesezeichen gelesen), steam (SteamID
    eingetragen), gg (Link oder Lesezeichen)."""
    imp, s = data.get("imports") or {}, settings or {}
    return ({"meta"} if imp.get("metawish") else set()) | ({"steam"} if s.get("steam_id") and s.get("steam_wish", True) else set()) | \
        ({"gg"} if s.get("gg_wish") or imp.get("ggwish") else set())


def auto(data):
    """Was sich ohne Rückfrage klären lässt (0.8.12), direkt in data; liefert die Namen. Gekauft und auf keiner
    Wunschliste eines Ladens, nicht von Hand gewünscht: Der Wunsch ist erfüllt und fällt weg (stammte aus einer
    Liste, die du nicht mehr pflegst, oder aus der alten Tabelle)."""
    done = []
    for t in data["titles"].values():
        ws = t.get("wish_src") or {}
        if t.get("wish") and t.get("owned") and not t.get("wish_keep") and not ws:
            t["wish"] = False
            t.setdefault("wish_done", titles.now_iso())
            done.append(t["name"])
    return done


def check(data, settings=None):
    """Abweichungen zwischen den Wunschlisten und dem Tool: [{key, name, kind, why, srcs, links}]."""
    out = []
    steam = (settings or {}).get("steam_wish", True)
    for k, t in data["titles"].items():
        ws = [s for s in (t.get("wish_src") or {}) if s != "hand"]
        off = list(t.get("wish_off") or [])
        owned = bool(t.get("owned"))
        item = {"key": k, "name": t["name"]}
        # 0.8.12: Bei Meta gekauft mit Crossbuy gilt auch am PC; dann ist die gg.deals- oder Steam-Wunschliste erledigt
        cb_done = (t.get("owned") or {}).get("meta") and t.get("crossbuy") is True and ws and not set(ws) - {"gg", "steam"}
        if t.get("wish") and owned and not t.get("wish_keep") and not cb_done:
            where = _owned_text(t)
            why = f"gekauft {where}" + (f", steht noch auf: {', '.join(_src_names(ws))}" if ws else ", steht noch auf deiner Wunschliste im Tool")
            out.append(dict(item, kind="owned", why=why, srcs=ws, links=_links(t, ws)))
        elif t.get("wish") and not t.get("wish_src") and not owned:
            why = "nur aus der alten Tabelle" if t.get("sheet") is not None else \
                "nur von der Steam-Wunschliste" if "steamwish" in (t.get("origin") or {}) and not steam else "ohne Quelle"
            out.append(dict(item, kind="table", why=why + ", auf keiner Wunschliste", srcs=[], links=add_links(t, steam)))
        elif not t.get("wish") and off:
            out.append(dict(item, kind="off", why=f"im Tool entfernt, steht noch auf: {', '.join(_src_names(off))}",
                            srcs=off, links=_links(t, off)))
    order = {"owned": 0, "off": 1, "missing": 2, "table": 3}
    return sorted(out, key=lambda x: (order[x["kind"]], titles.norm(x["name"])))


def stale(data, now=None):
    """Listen, die nur das Lesezeichen bringt und die lange nicht gelesen wurden:
    [{src, label, at}] mit at = "" für noch nie."""
    now = now or datetime.now(timezone.utc)
    old = (now - timedelta(days=MANUAL_DAYS)).isoformat(timespec="seconds")
    imp = data.get("imports") or {}
    out = []
    for src, label in (("metawish", "Meta-Wunschliste"), ("meta", "Meta-Käufe")):
        at = (imp.get(src) or {}).get("at") or ""
        if at < old:
            out.append({"src": src, "label": label, "at": at})
    return out


def apply(data, kind, keys):
    """Eine Aktion für Titel einer Gruppe. keep: als Wunsch von Hand behalten (table) oder trotz
    Besitz behalten (owned); drop: von der Wunschliste nehmen; wish: wieder wünschen (off).
    Liefert die Zahl der geänderten Titel."""
    n = 0
    for k in keys:
        t = data["titles"].get(k)
        if not t:
            continue
        if kind == "keep":
            if t.get("owned"):
                t["wish_keep"] = True
            else:
                titles.wish_by_hand(t, True)
        elif kind == "drop":
            titles.wish_by_hand(t, False)
            t.pop("wish_keep", None)
        elif kind == "wish":
            titles.wish_by_hand(t, True)
        elif kind == "ok":
            # Gewollt nur auf einer Wunschliste (etwa nur die PC-Fassung): kein Hinweis mehr
            t["wish_lists_ok"] = True
        else:
            raise ValueError("Unbekannte Aktion")
        n += 1
    return n
