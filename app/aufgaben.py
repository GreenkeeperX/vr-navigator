"""Aufträge zu den Listen unter „Zu erledigen“ (ab 0.10.24), ohne Netz.

Je Liste, bei der eine Recherche helfen kann, ein Auftrag als Text zum Einfügen in eine Claude-Routine
oder einen Chat (`task`), wie bei den Meinungen. Die Antwort ist eine JSON-Datei mit derselben Kennung
je Eintrag; sie kommt über Einlesen zurück, erst als Vorschau (`apply` mit dry), dann übernommen. Was
nicht mehr offen ist oder keine erlaubte Antwort trägt, bleibt liegen und steht in der Vorschau.

Listen: meta (Ohne Meta-ID), steam (Steam-ID prüfen), pcid (PC-Wunsch: Steam-ID), sug (Derselbe
Titel?), near (Retro: ähnlicher Name), own (Retro: Genre weicht von deiner Liste ab); ab 0.10.26 wheel (Sim-Racing:
Lenkrad) und vrmod (VR-Mods) für Spiele der Sammlung."""
import json
import re

from . import titles

MARK = "vr-navigator-aufgaben"
BATCH = 50          # so viele Einträge je Auftrag
BATCHES = {"vrmod": 100}     # VR-Mods: nur ein Wort je Spiel, dafür viele Spiele (0.10.26)
_URL = re.compile(r"^https://\S+$")

TITLES = {"meta": "Ohne Meta-ID", "steam": "Steam-ID prüfen", "pcid": "PC-Wunsch: Steam-ID",
          "sug": "Derselbe Titel?", "near": "Retro: ähnlicher Name", "own": "Retro: Genre weicht von deiner Liste ab",
          "wheel": "Sim-Racing: Lenkrad prüfen", "vrmod": "VR-Mods prüfen"}

# Absätze je in einer Zeile, wie beim Meinungs-Auftrag (0.10.19)
INTRO = ("Hilf mir, offene Punkte in meinem Spiele-Verzeichnis zu klären. Prüfe jeden Eintrag einzeln anhand von "
         "Store-Seiten und Datenbanken. Nichts erfinden: was sich nicht belegen lässt, lässt du weg oder schreibst "
         "„unklar“ als Antwort.")
ASK = {
    "meta": ("Finde für jeden VR-Titel die Fassung im Meta Store (Quest). Die Meta-ID ist die lange Zahl in der Adresse "
             "meta.com/experiences/…/<Meta-ID>; nachsehen kannst du bei meta.com, vrdb.app oder queststoredb.com. "
             "Bei einem Bundle nenne unter „enthalten“ die Spiele darin mit ihrer Meta-ID. Gibt es das Spiel nicht "
             "für die Quest (etwa nur am PC oder ohne VR), antworte „keine“ und sag im Grund, was es stattdessen ist.",
             "die Meta-ID als Zahl, „keine“ oder „unklar“"),
    "steam": ("Prüfe für jeden VR-Titel, ob die genannte Steam-App die VR-Fassung genau dieses Spiels ist "
              "(store.steampowered.com/app/<ID>, steamdb.info). Gehört sie zu einem anderen Spiel oder zur Fassung "
              "ohne VR, nenne die richtige Steam-App-ID der VR-Fassung, wenn es eine gibt.",
              "„passt“, „falsch“ (keine VR-Fassung bei Steam), die richtige Steam-App-ID als Zahl oder „unklar“"),
    "pcid": ("Für diese PC-Spiele fand die Steam-Suche keinen genau gleichen Namen. Prüfe, welche der angebotenen "
             "Steam-Apps das Spiel ist (store.steampowered.com/app/<ID>).",
             "eine der angebotenen Steam-App-IDs, „keins“ (keine davon) oder „unklar“"),
    "sug": ("Diese Paare heißen fast gleich; einer stammt aus dem Meta Store, der andere vom PC. Prüfe, ob es "
            "dasselbe Spiel ist (nur eine andere Schreibweise oder Fassung im anderen Laden) oder zwei "
            "verschiedene Spiele. Bei „dasselbe“ nenne unter „behalten“ den Namen, der das Spiel am besten trifft.",
            "„dasselbe“, „verschieden“ oder „unklar“"),
    "near": ("Diese Retro-Spiele stehen nicht unter ihrem Namen in der No-Intro- oder Redump-Liste, dort aber ein "
             "ähnlicher Titel. Prüfe, ob es dasselbe Spiel auf demselben System ist (etwa nur eine andere "
             "Umschrift des japanischen Namens) oder ein anderes, etwa ein Nachfolger.",
             "„dasselbe“, „anderes“ oder „unklar“"),
    "own": ("Für diese Retro-Spiele nennen libretro und IGDB ein anderes Genre als meine eigene Liste. Prüfe, welches "
            "Genre das Spiel besser beschreibt (MobyGames, Wikipedia, IGDB).",
            "„liste“ (mein Genre passt), „quellen“ (das andere passt besser) oder „unklar“"),
    # 0.10.26: Spiele der Sammlung (PC)
    "wheel": ("Diese PC-Spiele tragen bei Steam Schlagwörter wie Racing oder Driving. Prüfe, ob man sie mit einem "
              "Lenkrad mit Force Feedback spielen kann (Direktantrieb wie Simagic oder Simucube über DirectInput), etwa "
              "laut Herstellerseite, PCGamingWiki, Steam-Forum oder Tests. „teilweise“ heißt: Lenkrad geht, aber ohne "
              "richtiges Force Feedback oder nur mit Umwegen.",
              "„ja“, „teilweise“, „nein“ oder „unklar“"),
    "vrmod": ("Diese PC-Spiele haben keine eigene VR-Fassung. Prüfe für jedes, ob es einen VR-Mod gibt, mit dem man es "
              "in VR spielen kann, etwa UEVR, Flat2VR, Luke Ross (R.E.A.L. VR) oder einen eigenen Mod (Flat2VR-Liste, "
              "PCGamingWiki, Nexus Mods, Reddit r/flatscreen2vr). vorpX allein zählt nicht. Bei „ja“ nenne unter „mod“ "
              "den Namen und im Grund, wie gut er ist (Bewegungssteuerung, Stand).",
              "„ja“, „nein“ oder „unklar“"),
}


def items(kind, data, near=None, own=None, pc_ids=None, games=None):
    """Offene Einträge einer Liste in der Form für den Auftrag: [{id, name, …}] ohne Herkunft und Besitz. games: Zeilen
    der Sammlung (collection.view) für Lenkrad und VR-Mods."""
    if kind in ("meta", "steam"):
        out = []
        for x in titles.todo(data):
            if x["kind"] != kind:
                continue
            t = data["titles"][x["key"]]
            e = {"id": x["key"], "name": x["name"]}
            if kind == "meta":
                if t.get("steam_appid"):
                    e["steam_appid"] = t["steam_appid"]
                if titles.is_bundle(t):
                    e["bundle"] = True
            else:
                e["steam_appid"], e["hinweis"] = x["steam_appid"], x["why"]
            out.append(e)
        return out
    if kind == "pcid":
        return [{"id": x["key"], "name": x["name"],
                 "angeboten": [{"steam_appid": x["appid"], "name": x["steam"]}] if x["kind"] == "near"
                 else [{"steam_appid": c["appid"], "name": c.get("name") or ""} for c in x["cands"]]}
                for x in pc_ids or []]
    if kind == "sug":
        return [{"id": f"{x['a']}|{x['b']}", "a": x["a_name"], "b": x["b_name"]} for x in titles.suggestions(data)]
    if kind == "near":
        return [{"id": x["key"], "name": x["name"], "system": x["system"], "aehnlich": x["near"]} for x in near or []]
    if kind == "own":
        return [{"id": x["key"], "name": x["name"], "system": x["system"], "mein_genre": x["diff"][0]["own"],
                 "andere": "; ".join(d["other"] for d in x["diff"])} for x in own or []]
    if kind == "wheel":
        return [{"id": g["key"], "name": g["name"], "schlagwoerter": ", ".join(g["wheel"]["tags"])}
                for g in games or [] if g.get("system") == "PC" and g.get("wheel") and not g["wheel"]["src"]
                and not g.get("wheel_r")]
    if kind == "vrmod":
        rows = [g for g in games or [] if g.get("system") == "PC" and not g.get("retro") and not g.get("vr")
                and not g.get("vrmod") and not g.get("vrmod_r") and not g.get("f2vr") and not g.get("uevr")]   # 0.10.28: Port oder Profil schon bekannt
        # die besser bewerteten zuerst: dort lohnt ein Mod am ehesten
        rows.sort(key=lambda g: (-(g.get("score") or 0), titles.norm(g["name"])))
        return [{"id": g["key"], "name": g["name"]} for g in rows]
    raise ValueError("unbekannte Liste")


def task(kind, rows, today=None):
    """Auftrag als Text, höchstens BATCH Einträge; leer, wenn nichts offen ist."""
    rows = rows[:BATCHES.get(kind, BATCH)]
    if not rows:
        return ""
    ask, answer = ASK[kind]
    today = today or titles.now_iso()[:10]
    extra = {"meta": ', "enthalten": [{"name": "…", "meta_id": "…"}]', "sug": ', "behalten": "…"', "vrmod": ', "mod": "…"'}.get(kind, "")
    return f"""{INTRO}

{ask}

Einträge ({len(rows)}, Liste „{TITLES[kind]}“):
[
{",\n".join(json.dumps(r, ensure_ascii=False) for r in rows)}
]

Antworte nur mit einer JSON-Datei in diesem Aufbau; „id“ genau wie oben übernehmen:
{{"app": "{MARK}", "liste": "{kind}", "stand": "{today}", "antworten": [{{"id": "…", "name": "…", "antwort": "…", "grund": "…", "quellen": ["https://…"]{extra}}}]}}

antwort: {answer}. grund: ein Satz, woran du es festmachst. quellen: nur https-Links, die du gelesen hast.{" Jeder Eintrag bekommt eine Antwort, auch „nein“ (dann reichen id und antwort): so weiß das Tool, was geprüft ist." if kind == "vrmod" else ""}
"""


def tasks(data, near=None, own=None, pc_ids=None, today=None, games=None):
    """Aufträge aller Listen mit offenen Einträgen: {liste: Text}."""
    out = {}
    for kind in ASK:
        text = task(kind, items(kind, data, near, own, pc_ids, games), today)
        if text:
            out[kind] = text
    return out


def parse(text):
    """Antwort lesen: (liste, [{id, name, antwort, grund, quellen, enthalten, behalten}])."""
    try:
        obj = json.loads(str(text or "").lstrip("﻿"))
    except ValueError:
        raise ValueError("Die Antwort ist kein gültiges JSON")
    if not isinstance(obj, dict) or obj.get("app") != MARK:
        raise ValueError("Das ist keine Antwort auf einen Auftrag aus „Zu erledigen“")
    kind = str(obj.get("liste") or "")
    if kind not in ASK:
        raise ValueError("Unbekannte Liste in der Antwort")
    out = []
    for a in obj.get("antworten") or []:
        if not isinstance(a, dict) or not str(a.get("id") or "").strip():
            continue
        inc = []
        for x in a.get("enthalten") or []:
            mid = str((x or {}).get("meta_id") or "").strip() if isinstance(x, dict) else ""
            if mid.isdigit() and 6 <= len(mid) <= 20:
                inc.append({"name": str(x.get("name") or "")[:200], "meta_id": mid})
        out.append({"id": str(a["id"]).strip()[:300], "name": str(a.get("name") or "")[:200],
                    "antwort": str(a.get("antwort") if a.get("antwort") is not None else "").strip()[:40],
                    "grund": str(a.get("grund") or "").strip()[:400],
                    "quellen": [u for u in (str(q).strip() for q in a.get("quellen") or [] if isinstance(q, str)) if _URL.match(u)][:5],
                    "enthalten": inc[:40], "behalten": str(a.get("behalten") or "").strip()[:200],
                    "mod": str(a.get("mod") or "").strip()[:120]})
    return kind, out


def _decide(kind, a, row):
    """(was, Text für die Vorschau) oder (None, warum liegen geblieben)."""
    v = a["antwort"].casefold()
    if kind == "meta" and a["enthalten"] and row.get("bundle"):
        return ("bundle", a["enthalten"]), "Bundle mit " + ", ".join(x["name"] or x["meta_id"] for x in a["enthalten"])
    if v in ("", "unklar"):
        return None, "unklar"
    if kind == "meta":
        if v.isdigit() and 6 <= len(v) <= 20:
            return ("meta_id", v), f"Meta-ID {v}"
        if v == "keine":
            return ("none", a["grund"]), "keine Quest-Fassung"
    elif kind == "steam":
        if v == "passt":
            return ("ok", None), f"Steam {row['steam_appid']} passt"
        if v == "falsch":
            return ("wrong", None), f"Steam {row['steam_appid']} entfernen"
        if v.isdigit() and v != row["steam_appid"]:
            return ("other", v), f"Steam {v} statt {row['steam_appid']}"
        if v == row["steam_appid"]:
            return ("ok", None), f"Steam {v} passt"
    elif kind == "pcid":
        offered = [c["steam_appid"] for c in row["angeboten"]]
        if v in offered:
            return ("id", v), f"Steam {v}"
        if v in ("keins", "keine", "falsch"):
            return ("id", ""), "keine der angebotenen"
        if v.isdigit():
            return None, f"Steam {v} stand nicht zur Wahl"
    elif kind == "sug":
        if v == "dasselbe":
            keep_b = titles.norm(a["behalten"]) == titles.norm(row["b"]) and titles.norm(a["behalten"]) != titles.norm(row["a"])
            return ("same", keep_b), f"dasselbe, als „{row['b'] if keep_b else row['a']}“"
        if v == "verschieden":
            return ("diff", None), "verschieden"
    elif kind == "near":
        if v == "dasselbe":
            return ("near", True), f"dasselbe wie „{row['aehnlich']}“"
        if v == "anderes":
            return ("near", False), "anderes Spiel"
    elif kind == "wheel":
        if v in ("ja", "teilweise", "nein"):
            return ("wheel", v), {"ja": "Lenkrad mit Force Feedback", "teilweise": "Lenkrad nur teilweise", "nein": "kein Lenkrad"}[v]
    elif kind == "vrmod":
        if v == "ja":
            return ("vrmod", True), "VR per Mod" + (f": {a['mod']}" if a["mod"] else "")
        if v == "nein":
            return ("vrmod", False), "kein VR-Mod"
    elif kind == "own":
        if v == "liste":
            return ("own", False), f"dein Genre gilt ({row['mein_genre']})"
        if v == "quellen":
            return ("own", True), "Genre der Quellen gilt"
    return None, f"Antwort „{a['antwort'][:40]}“ passt nicht zur Liste"


def apply(text, data, near=None, own=None, pc_ids=None, dry=True, act=None, games=None):
    """Antwort auf einen Auftrag prüfen und, ohne dry, übernehmen. Was in data.json gehört (meta, steam, sug),
    trägt diese Funktion ein; die übrigen Listen (pcid, near, own, ab 0.10.26 wheel und vrmod) gehen an
    act(kind, key, value), das der Server mit der Sammlung und der PC-Wunschliste ausführt. Liefert die Übersicht für die Vorschau."""
    kind, answers = parse(text)
    open_rows = {r["id"]: r for r in items(kind, data, near, own, pc_ids, games)}
    entries, skipped, done = [], [], set()
    for a in answers:
        row = open_rows.get(a["id"])
        label = a["name"] or a["id"]
        if row is None or a["id"] in done:
            skipped.append(f"{label} (nicht offen)")
            continue
        do, what = _decide(kind, a, row)
        name = row.get("name") or f"{row.get('a')} ↔ {row.get('b')}"
        if do is None:
            skipped.append(f"{name} ({what})")
            continue
        done.add(a["id"])
        entries.append({"name": name, "known": True, "what": what, "grund": a["grund"], "quellen": a["quellen"]})
        if dry:
            continue
        op, val = do
        if kind == "meta":
            t = data["titles"].get(a["id"])
            if t is None:
                continue
            if op == "meta_id":
                titles.set_ids(data, a["id"], meta_id=val)
            elif op == "bundle":
                titles.set_bundle(data, a["id"], [f"https://www.meta.com/experiences/{x['meta_id']}/" for x in val])
            else:
                t["meta_none"] = {"why": val or "laut Recherche keine Quest-Fassung", "at": titles.now_iso()}
        elif kind == "steam":
            t = data["titles"].get(a["id"])
            if t is None:
                continue
            if op == "ok":
                t["steam_sure"] = t["steam_hand"] = True      # wie „passt“ von Hand
                t.pop("steam_doubt", None)
            else:
                titles.set_ids(data, a["id"], steam_appid="" if op == "wrong" else val)
                if op == "other":
                    t = data["titles"].get(a["id"]) or t
                    t["steam_sure"] = False      # die neue ID prüft der nächste Abgleich im Steam-Store
        elif kind == "sug":
            ka, kb = a["id"].split("|", 1)
            if ka not in data["titles"] or kb not in data["titles"]:
                continue
            if op == "same":
                keep, gone = (kb, ka) if val else (ka, kb)
                titles.merge(data, keep, gone)
            else:
                pair = sorted([ka, kb])
                data.setdefault("not_same", [])
                if pair not in data["not_same"]:
                    data["not_same"].append(pair)
        elif kind in ("wheel", "vrmod") and act:
            rec = {"grund": a["grund"], "quellen": a["quellen"], "at": titles.now_iso()}
            rec.update({"v": val} if kind == "wheel" else {"ok": val, "mod": a["mod"] if val else ""})
            act(kind, a["id"], rec)
        elif act:
            act(kind, a["id"], val)
    return {"dry": dry, "n": len(entries), "new": 0, "entries": entries, "todo": kind, "what": f"Antworten zu „{TITLES[kind]}“",
            "attach": False, "skipped": skipped}
