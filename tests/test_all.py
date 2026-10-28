import json
from datetime import datetime, timezone
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ["DATA_DIR"] = tempfile.mkdtemp()

from app import accounts, collection, imports, library, lists, prices, retro, server, sources, store, sync, titles  # noqa: E402

# Erfundene Beispiele im Format der eigenen Vergleichstabelle und der Exporte; keine echten Daten
SHEET = """Spiel,Aufschlag,gg.deals best,Bestpreis,Gutschein,,Vergleich,meta,Rabatt,Crossbuy,https://queststoredb.com/on_sale/
Sky Garden,-2,6,4,"4,2","0,2","-1,8",7,40%,Yes,https://vrdb.app/game/sky-garden/1111111111111111
Laser Tennis,3,"12,5","15,5",18,,,30,48%,No,https://queststoredb.com/game/laser-tennis-2222222222222222/
Moon Rover (Bundle-Fassung),,,8,,,,10,20%,No,
Nur ein Name,,,,,,,,,,
,,,,,,,,,,
"""

PLAYNITE = """﻿Name,Sortiername,Kategorien,Spiel-ID,Schlagwörter,Features
Sky Garden,,,3000001,"VR, Puzzle",Single Player
Flat Racer,,,3000002,"Racing",Single Player
Moon Rover VR,,,3000003,"Asymmetric VR",
Laser Tennis,,,3000004,"Sports",
Epic Thing,,,0123456789abcdef0123456789abcdef,"VR",
"""

META_JSON = json.dumps({"kind": "meta-bestellungen", "links": [
    {"href": "https://www.meta.com/de-de/experiences/sky-garden/1111111111111111/", "text": "Sky Garden"},
    {"href": "https://www.meta.com/experiences/3333333333333333/", "text": "Deep Dive 19,99 €"},
    {"href": "https://www.meta.com/experiences/3333333333333333/", "text": "Deep Dive"},
    {"href": "https://www.meta.com/help/", "text": "Hilfe"},
    {"href": "https://www.meta.com/experiences/4444444444444444/", "text": ""},
], "text": "egal"})

META_TEXT = """Meine Bestellungen
Sky Garden
12. Okt. 2025
7,99 €
Deep Dive    19,99 €
Gesamt
21.10.2026
"""


def empty():
    return json.loads(json.dumps(store.EMPTY_DATA))


class TestTitles(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(titles.norm("Rover’s Moon Trip™"), titles.norm("rovers moon trip"))
        self.assertEqual(titles.norm("Pokémon: X!"), "pokemon x")
        self.assertEqual(titles.base_norm("Moon Rover (Bundle-Fassung)"), titles.base_norm("Moon Rover VR"))

    def test_ids_from_links(self):
        self.assertEqual(titles.meta_id_from("https://www.meta.com/de-de/experiences/x/1234567890/"), "1234567890")
        self.assertEqual(titles.meta_id_from("https://queststoredb.com/game/moon-rover-6666666666666666/"), "6666666666666666")
        self.assertEqual(titles.meta_id_from("https://vrdb.app/game/moon-rover/5555555555555555?ratingPeriod=all"), "5555555555555555")
        self.assertEqual(titles.meta_id_from("https://www.meta.com/help/"), "")
        self.assertEqual(titles.steam_id_from("https://store.steampowered.com/app/3000009/Moon_Rover/"), "3000009")
        self.assertEqual(titles.link_kind("https://evil.example/vrdb.app"), "")

    def test_set_ids_merges(self):
        d = empty()
        a, _ = titles.upsert(d, "Sky Garden", meta_id="1")
        b, _ = titles.upsert(d, "Himmelsgarten", steam_appid="2")
        d["titles"][b]["owned"]["pc"] = {"src": "hand"}
        d["titles"][b]["note"] = "PC-Fassung schöner"
        titles.set_ids(d, a, steam_appid="2")
        self.assertEqual(list(d["titles"]), [a])
        t = d["titles"][a]
        self.assertEqual((t["meta_id"], t["steam_appid"]), ("1", "2"))
        self.assertIn("pc", t["owned"])
        self.assertEqual(t["note"], "PC-Fassung schöner")
        with self.assertRaises(ValueError):
            titles.set_ids(d, a, meta_id="abc")

    def test_upsert_joins_when_second_id_known(self):
        d = empty()
        a, _ = titles.upsert(d, "Sky Garden", meta_id="1")
        b, _ = titles.upsert(d, "Sky Garden PC", steam_appid="2")
        k, new = titles.upsert(d, "Sky Garden", meta_id="1", steam_appid="2")
        self.assertFalse(new)
        self.assertEqual(k, a)
        self.assertNotIn(b, d["titles"])

    def test_name_conflict_with_other_id(self):
        d = empty()
        titles.upsert(d, "Sky Garden", meta_id="1")
        k, new = titles.upsert(d, "Sky Garden", meta_id="9")
        self.assertTrue(new)
        self.assertEqual(len(d["titles"]), 2)


    def test_merged_and_renamed_names_still_match(self):
        # Nach „Zusammenführen“ oder Umbenennen findet ein späterer Import den Titel unter dem
        # alten Namen wieder, statt ihn doppelt anzulegen
        d = empty()
        a, _ = titles.upsert(d, "Moon Rover", steam_appid="42")
        b, _ = titles.upsert(d, "Moon Rover VR")
        titles.merge(d, a, b)
        self.assertEqual(titles.find(d, name="Moon Rover VR"), a)
        res = imports.import_meta(d, "Bestellnummer 9000000000000001\nGESAMT 1,99 €\nMoon Rover VR\nGekauft", dry=False)
        self.assertEqual(res["new"], 0)
        self.assertEqual(len(d["titles"]), 1)


class TestImports(unittest.TestCase):
    def test_num(self):
        self.assertEqual(imports.num("4,2"), 4.2)
        self.assertEqual(imports.num("1.299,00 €"), 1299.0)
        self.assertEqual(imports.num("12.5"), 12.5)
        self.assertIsNone(imports.num(""))
        self.assertIsNone(imports.num("86%"))

    def test_sheet(self):
        d = empty()
        prev = imports.import_sheet(d, SHEET, dry=True)
        self.assertEqual(prev["n"], 4)
        self.assertEqual(d["titles"], {})                 # Vorschau ändert nichts
        res = imports.import_sheet(d, SHEET, dry=False)
        self.assertEqual(res["new"], 4)
        t = d["titles"]["meta-1111111111111111"]
        self.assertEqual(t["sheet"]["meta"], 7.0)
        self.assertEqual(t["sheet"]["meta_low"], 4.0)
        self.assertEqual(t["sheet"]["gg"], 6.0)
        self.assertTrue(t["crossbuy"])
        self.assertTrue(t["wish"])
        self.assertEqual(t["links"]["vrdb"], "https://vrdb.app/game/sky-garden/1111111111111111")
        lt = d["titles"]["meta-2222222222222222"]
        self.assertEqual(lt["sheet"]["gg"], 12.5)
        self.assertIs(lt["crossbuy"], False)
        self.assertIn("qsdb", lt["links"])
        only = d["titles"][titles.find(d, name="Nur ein Name")]
        self.assertIsNone(only["sheet"])
        # Zweiter Import legt nichts doppelt an
        self.assertEqual(imports.import_sheet(d, SHEET, dry=False)["new"], 0)
        self.assertEqual(len(d["titles"]), 4)

    def test_playnite_only_vr_and_known(self):
        d = empty()
        imports.import_sheet(d, SHEET, dry=False)
        res = imports.import_playnite(d, PLAYNITE, dry=False)
        names = [e["name"] for e in res["entries"]]
        # VR-Schlagwort, Asymmetric VR, schon bekannt (Laser Tennis), ohne Flat Racer
        self.assertEqual(names, ["Sky Garden", "Moon Rover VR", "Laser Tennis", "Epic Thing"])
        sky = d["titles"]["meta-1111111111111111"]
        self.assertEqual(sky["steam_appid"], "3000001")
        self.assertFalse(sky["steam_sure"])                # ohne Quellenspalte nur vermutet
        self.assertEqual(sky["owned"]["pc"]["label"], "PC")
        epic = d["titles"][titles.find(d, name="Epic Thing")]
        self.assertEqual(epic["steam_appid"], "")          # keine Zahl: keine Steam-ID
        # Moon Rover VR und „Moon Rover (Bundle-Fassung)“: nur ein Vorschlag, kein stilles Zusammenführen
        sug = titles.suggestions(d)
        self.assertEqual(len(sug), 1)
        self.assertEqual({sug[0]["a_name"], sug[0]["b_name"]}, {"Moon Rover (Bundle-Fassung)", "Moon Rover VR"})
        d["not_same"] = [sorted([sug[0]["a"], sug[0]["b"]])]
        self.assertEqual(titles.suggestions(d), [])

    def test_playnite_source_column(self):
        csv_text = "Name;Spiel-ID;Schlagwörter;Quelle\nSky Garden;3000001;VR;Steam\nOther;1207658930;VR;GOG\n"
        es = imports.parse_playnite(csv_text)
        self.assertEqual([(e["steam_appid"], e["steam_sure"], e["label"]) for e in es],
                         [("3000001", True, "Steam"), ("", False, "GOG")])

    def test_meta_bookmarklet(self):
        d = empty()
        imports.import_sheet(d, SHEET, dry=False)
        res = imports.import_meta(d, META_JSON, dry=False)
        self.assertEqual([(e["name"], e["meta_id"], e["price"]) for e in res["entries"]],
                         [("Sky Garden", "1111111111111111", None), ("Deep Dive", "3333333333333333", 19.99)])
        self.assertEqual(res["new"], 1)
        sky = d["titles"]["meta-1111111111111111"]
        self.assertIn("meta", sky["owned"])
        v = library.view(d)
        self.assertIn("Sky Garden", [r["name"] for r in v["library"]])

    def test_meta_text(self):
        es = imports.parse_meta(META_TEXT)
        self.assertEqual([(e["name"], e["price"]) for e in es], [("Sky Garden", None), ("Deep Dive", 19.99)])

    def test_meta_order_page(self):
        # Erfundene Bestellseite im echten Aufbau: Menü, Blöcke mit Bestellnummer, Fußzeile
        text = "\n".join(["Zum Hauptinhalt", "Meta Quest", "Bestellungen und Rücksendungen", "Galerie", "Abmelden",
                          "Digitale Produkte", "Käufe",
                          "25.09.2026", "Bestellnummer 9000000000000001", "GESAMT 6,99\u00a0€", "Sky Garden", "Gekauft",
                          "Zu den Bestelldetails",
                          "26.09.2026", "Bestellnummer 9000000000000002", "GESAMT 3.500\u00a0¥", "Moon Rover: Mirror &amp; Dust",
                          "Gekauft", "Zu den Bestelldetails",
                          "27.09.2026", "Bestellnummer 9000000000000003", "GESAMT 9,99\u00a0€", "Laser Tennis", "Erstattet",
                          "Zu den Bestelldetails",
                          "Meta Store", "Ray-Ban Meta-Brillen", "Datenschutzrichtlinie", "©2026 Meta."])
        es = imports.parse_meta(json.dumps({"kind": "meta-bestellungen", "links": [
            {"href": "https://www.meta.com/order/digital/9000000000000001/", "text": "Zu den Bestelldetails"}], "text": text}))
        self.assertEqual([(e["name"], e["price"]) for e in es],
                         [("Sky Garden", 6.99), ("Moon Rover: Mirror & Dust", None)])

    def test_meta_transactions(self):
        # Erfundene Transaktionen (Meta Pay): Titel, Stand, Datum, Betrag
        text = "\n".join(["Meta-Konto", "Meta Pay", "Transaktionen", "Alle", "Spiele", "Sonstige",
                          "Sky Garden", "Abgeschlossen", "25.09.2026", "6,99\u00a0€",
                          "Deep Dive", "Abgeschlossen", "12. Feb. 2025", "1.794\u00a0¥",
                          "Laser Tennis", "Erstattet", "12. Feb. 2025", "9,99\u00a0€"])
        es = imports.parse_meta(text)
        self.assertEqual([(e["name"], e["price"]) for e in es], [("Sky Garden", 6.99), ("Deep Dive", None)])

    def test_meta_bad_json(self):
        with self.assertRaises(ValueError):
            imports.parse_meta("{kaputt")


    def test_origin_and_bundle(self):
        """Herkunft je Titel (mit Zeile der Tabelle, für alte Daten vermutet) und Bundle-Inhalt."""
        d = empty()
        imports.import_sheet(d, SHEET, dry=False)
        t = d["titles"][titles.find(d, "", "", "Nur ein Name")]
        self.assertEqual([(o["label"], o["detail"], o["guess"]) for o in titles.origins(t, d)],
                         [("Vergleichstabelle", "Zeile 5", False)])
        old = dict(t)
        old.pop("origin")
        self.assertEqual([(o["src"], o["guess"]) for o in titles.origins(old, d)], [("sheet", True)])
        b = titles.find(d, "", "", "Moon Rover (Bundle-Fassung)")
        d["titles"][b]["owned"] = {"meta": {"src": "meta"}}
        d["titles"][b]["meta_miss"] = titles.now_iso()
        self.assertIn(b, [x["key"] for x in titles.todo(d)])
        keys = titles.set_bundle(d, b, ["Comet Chase", "https://vrdb.app/game/orbit-golf/5555555555555555", " "])
        self.assertEqual([d["titles"][k]["name"] for k in keys], ["Comet Chase", "orbit golf"])
        og = d["titles"][keys[1]]
        self.assertEqual((og["meta_id"], og["owned"]["meta"]["src"]), ("5555555555555555", "bundle"))
        self.assertEqual(og["origin"]["bundle"]["detail"], "Moon Rover (Bundle-Fassung)")
        self.assertNotIn(b, [x["key"] for x in titles.todo(d)])
        r = library.row(b, d["titles"][b], data=d)
        self.assertEqual([x["name"] for x in r["contains"]], ["Comet Chase", "orbit golf"])
        with self.assertRaises(ValueError):
            titles.set_bundle(d, b, ["https://example.org/kein-spiel"])

    def test_ggpage_and_guess(self):
        """gg.deals-Wunschliste aus dem Lesezeichen; unklare Dateien melden sich statt still nichts."""
        d = empty()
        k, _ = titles.upsert(d, "Orbit Golf")
        payload = json.dumps({"kind": "gg-wunschliste", "hv": 5, "items": [
            {"slug": "orbit-golf", "name": "Orbit Golf"}, {"slug": "comet-chase", "name": ""},
            {"slug": "../boese", "name": "x"}]})
        self.assertEqual(imports.detect(payload), "meta")
        res = imports.import_auto(d, payload, dry=True)
        self.assertEqual([(e["name"], e["known"]) for e in res["entries"]], [("Orbit Golf", True), ("comet chase", False)])
        imports.import_auto(d, payload, dry=False)
        self.assertEqual(set(d["titles"][k]["wish_src"]), {"gg"})
        self.assertEqual(d["gg_unknown"], ["comet chase"])
        self.assertEqual(d["imports"]["ggwish"]["via"], "Lesezeichen")
        with self.assertRaises(ValueError) as e:
            imports.import_auto(d, "Irgendwas;Ganz;Anderes\n1;2;3\n", dry=True)
        self.assertIn("Art", str(e.exception))
        res = imports.import_auto(d, SHEET, dry=True)
        self.assertEqual((res["kind"], res["guess"]), ("sheet", False))
        # Lesezeichen 7: Pakete und DLC kommen mit, übernommen werden nur Spiele, einmal je Slug
        payload = json.dumps({"kind": "gg-wunschliste", "hv": 7, "items": [
            {"kind": "game", "slug": "orbit-golf", "name": ""}, {"kind": "game", "slug": "orbit-golf", "name": "Orbit Golf"},
            {"kind": "pack", "slug": "sky-bundle", "name": "Sky Bundle"}, {"kind": "dlc", "slug": "orbit-golf-holes", "name": "Mehr Löcher"}]})
        res = imports.import_auto(d, payload, dry=True)
        self.assertEqual([e["name"] for e in res["entries"]], ["Orbit Golf"])
        self.assertEqual(res["gg"], {"raw": 4, "games": 1, "dups": 1, "other": {"pack": 1, "dlc": 1}})
        self.assertIn("1 Pakete (Sky Bundle); 1 DLC (Mehr Löcher)", res["note"])

    def test_opinions(self):
        """Meinungen-Datei: erkannt, nur bekannte Titel, Crossbuy nur ohne eigenen Wert."""
        d = empty()
        a, _ = titles.upsert(d, "Orbit Golf", steam_appid="3000040")
        b, _ = titles.upsert(d, "Comet Chase")
        d["titles"][b]["crossbuy"] = True
        doc = {"app": "vr-navigator-meinungen", "stand": "2026-10-22", "titles": [
            {"name": "Anderer Name", "steam_appid": "3000040", "fazit": "Ruhig und schön.", "fassung": "PC",
             "mehrspieler": "ruhig", "crossbuy": False, "unbekannt": "weg",
             "quellen": [{"url": "https://example.org/a", "titel": "Test"}, {"url": "javascript:alert(1)"}]},
            {"name": "Comet Chase", "crossbuy": False, "fassung": "besser"},
            {"name": "Nebula Drift", "fazit": "fehlt im Tool"}]}
        text = json.dumps(doc)
        self.assertEqual(imports.detect(text), "opinions")
        res = imports.import_auto(d, text, dry=True)
        self.assertEqual((res["n"], res["what"]), (2, "Meinungen"))
        self.assertIn("Nebula Drift", res["note"])
        self.assertNotIn("opinion", d["titles"][a])
        imports.import_auto(d, text, dry=False)
        o = d["titles"][a]["opinion"]
        self.assertEqual((o["fassung"], o["mehrspieler"], o["stand"]), ("pc", "ruhig", "2026-10-22"))
        self.assertNotIn("unbekannt", o)
        self.assertEqual([q["url"] for q in o["quellen"]], ["https://example.org/a"])
        self.assertNotIn("fassung", d["titles"][b]["opinion"])
        rows = {r["name"]: r for r in library.view(d)["wishlist"] + [library.row(k, t) for k, t in d["titles"].items()]}
        self.assertEqual((rows["Orbit Golf"]["crossbuy"], rows["Orbit Golf"]["crossbuy_src"]), (False, "Recherche"))
        self.assertEqual((rows["Comet Chase"]["crossbuy"], rows["Comet Chase"]["crossbuy_src"]), (True, "Hand"))

    def test_lists(self):
        """Wunschliste abgleichen: gekauft und noch gewünscht, im Tool entfernt und im Laden noch
        gewünscht, Wunsch nur aus der Tabelle; Aktionen und wann ein Hinweis von selbst geht."""
        d = empty()
        a, _ = titles.upsert(d, "Orbit Golf", steam_appid="3000040")
        b, _ = titles.upsert(d, "Comet Chase")
        c, _ = titles.upsert(d, "Harbor Heist", meta_id="1234567890123456")
        e, _ = titles.upsert(d, "Quiet Garden")
        titles.set_wishes(d, "gg", [a, c])
        titles.set_wishes(d, "steam", [a])
        d["titles"][a]["owned"] = {"pc": {"src": "steam", "label": "Steam", "at": "2026-10-01"}}
        d["titles"][b].update(wish=True, sheet={"at": "2026-10-01"})
        d["titles"][e]["wish"] = True
        titles.wish_by_hand(d["titles"][c], False)
        got = {x["name"]: x for x in lists.check(d)}
        self.assertEqual({n: x["kind"] for n, x in got.items()},
                         {"Orbit Golf": "owned", "Harbor Heist": "off", "Comet Chase": "table", "Quiet Garden": "table"})
        self.assertIn("gg.deals-Wunschliste, Steam-Wunschliste", got["Orbit Golf"]["why"])
        self.assertEqual([l["label"] for l in got["Orbit Golf"]["links"]], ["gg.deals", "Steam"])
        # Links direkt zum Spiel, bei gg.deals ohne bekannte Seite die Suche
        self.assertEqual([l["url"] for l in got["Orbit Golf"]["links"]],
                         ["https://gg.deals/search/?title=Orbit+Golf", "https://store.steampowered.com/app/3000040/"])
        self.assertEqual(library._gg_low({"retail_low": 9.0, "keyshops_low": 6.5}), (6.5, "gg.deals, Allzeit-Tief (Keyshops)"))
        self.assertIn("nur aus der alten Tabelle", got["Comet Chase"]["why"])
        # „behalten“: Wunsch von Hand, der Hinweis geht; trotz Besitz behalten ebenso
        lists.apply(d, "keep", [b, a])
        self.assertEqual(d["titles"][b]["wish_src"].keys(), {"hand"})
        self.assertTrue(d["titles"][a]["wish_keep"])
        # Eine Liste im Laden führt den Titel: der Tabellen-Hinweis geht von selbst
        titles.set_wishes(d, "meta", [e])
        self.assertEqual({x["name"] for x in lists.check(d)}, {"Harbor Heist"})
        # Im Laden entfernt: der Hinweis geht beim nächsten Abgleich
        titles.set_wishes(d, "gg", [a])
        self.assertEqual(lists.check(d), [])
        self.assertRaises(ValueError, lists.apply, d, "egal", [a])
        # Fehlt auf einer Laden-Wunschliste: Meta-ID, Meta-Wunschliste gelesen, dort nicht
        d["imports"] = {"metawish": {"at": "2026-10-22"}}
        f, _ = titles.upsert(d, "Sofa Smash", meta_id="2345678901234567", steam_appid="3000050")
        titles.set_wishes(d, "gg", [a, f])
        got = [x for x in lists.check(d, {"gg_wish": "x"}) if x["kind"] == "missing"]
        self.assertEqual([(x["name"], x["srcs"]) for x in got], [("Sofa Smash", ["meta"])])
        self.assertEqual([l["label"] for l in got[0]["links"]], ["Meta"])
        self.assertIn("gg.deals/search/?title=Sofa+Smash", lists.add_links(d["titles"][f])[-1]["url"])
        lists.apply(d, "ok", [f])
        self.assertFalse([x for x in lists.check(d, {"gg_wish": "x"}) if x["kind"] == "missing"])
        st = lists.stale(d, datetime(2026, 10, 22, tzinfo=timezone.utc))
        self.assertEqual([x["src"] for x in st], ["meta"])

    def test_opinion_crossbuy_needs_evidence(self):
        """Crossbuy gilt nur im Meta Store: eine Begründung mit Steam, Crossplay oder der eigenen
        Zuordnung ist kein Beleg und fällt weg; Crossplay steht als eigenes Feld."""
        d = empty()
        a, _ = titles.upsert(d, "Orbit Golf")
        b, _ = titles.upsert(d, "Comet Chase")
        c, _ = titles.upsert(d, "Harbor Heist")
        doc = {"app": "vr-navigator-meinungen", "titles": [
            {"name": "Orbit Golf", "crossbuy": False, "crossbuy_grund": "Zwischen Meta und Steam nirgends bestätigt."},
            {"name": "Comet Chase", "crossbuy": False, "crossbuy_grund": "Laut deiner Zuordnung kein Crossbuy."},
            {"name": "Harbor Heist", "crossbuy": True, "crossbuy_grund": "Store-Seite nennt Quest und Rift.",
             "crossplay": True, "crossplay_grund": "Quest und PC in einer Lobby."}]}
        res = imports.import_auto(d, json.dumps(doc), dry=False)
        self.assertIn("Crossbuy ohne Beleg verworfen (2)", res["note"])
        self.assertNotIn("crossbuy", d["titles"][a]["opinion"])
        self.assertNotIn("crossbuy", d["titles"][b]["opinion"])
        o = d["titles"][c]["opinion"]
        self.assertEqual((o["crossbuy"], o["crossplay"], o["crossplay_grund"]), (True, True, "Quest und PC in einer Lobby."))
        self.assertNotIn("crossbuy_dropped", o)
        self.assertEqual(library.row(c, d["titles"][c])["crossbuy_src"], "Recherche")


# Erfundene Sammlung im Aufbau eines Playnite-Exports (alle Spiele, alle Läden)
COLLECTION = """\ufeffName,Sortiername,Kategorien,Spiel-ID,Schlagwörter,Features,Genres,Erscheinungsdatum,Hinzugefügt,Communitywertung,Expertenwertung,Nutzerwertung,Entwickler,Versteckt
Harbor Heist,,Steam,3000101,"co-op, heist","Multiplayer, Co-Operative, Supports Online Co-Op, 4 Players in Co-Op",Shooter,12.03.2019,01.02.2020 10:00:00,88,81,,Kite Works,False
Sofa Smash,,Epic,abc123def,"local multiplayer","Supports Couch Co-Op, Split Screen","Fighting, Arcade",2021,05.06.2025 12:00:00,74,,,Pillow Games,False
Quiet Garden,,,3000103,"relaxing, Puzzle",Single Player,"Puzzle, Indie",01.01.2023,01.01.2023 08:00:00,95,,,Moss Studio,False
Hidden Tower,,GOG,1207650001,"roguelike","",Role-playing (RPG),2018,,61,70,,,True
Fleet Night,,itch.io,,"","Supports LAN or System-Link Play, Massively Multiplayer Online (MMO)",Strategy,,,,,,,False
"""


class TestCollection(unittest.TestCase):
    def test_parse(self):
        g = collection.parse(COLLECTION)
        self.assertEqual(sorted(g), ["epic:abc123def", "name:fleet night", "steam:3000101", "steam:3000103"])
        h = g["steam:3000101"]
        self.assertEqual(h["mp"], ["multi", "online", "coop"])
        self.assertEqual((h["players"], h["genres"], h["score"], h["score_src"], h["critic"]), (4, ["Shooter"], 88, "Community", 81))
        self.assertEqual((h["released"], h["added"], h["dev"], h["store_guess"]), ("2019-03-12", "2020-02-01", "Kite Works", False))
        self.assertNotIn("pub", h)                                 # Export ohne Spalte Publisher
        p = collection.parse("Name,Spiel-ID,Quelle,Entwickler,Publisher\nOrbit Golf,3000201,Steam,Kite Works,Paper Moon\n")
        self.assertEqual(p["steam:3000201"]["pub"], "Paper Moon")
        self.assertEqual(collection.view({"games": p})["games"][0]["pub"], "Paper Moon")
        s = g["epic:abc123def"]
        self.assertEqual(s["mp"], ["multi", "coop", "couch", "split"])
        self.assertEqual(s["players"], 2)                      # Splitscreen ohne Zahl: zwei
        self.assertEqual(s["genres"], ["Kampfspiel", "Arcade"])
        q = g["steam:3000103"]
        self.assertTrue(q["store_guess"])                      # Zahl ohne Laden: vermutlich Steam
        self.assertEqual((q["mp"], q["players"], q["genres"]), ([], 0, ["Puzzle"]))
        f = g["name:fleet night"]                              # ohne Kennung: Schlüssel aus dem Namen
        self.assertEqual((f["store"], f["mp"], f["score"]), ("itch", ["multi", "online", "lan", "mmo"], None))
        # versteckte Spiele fehlen, Steam-ID im VR-Import sicher, wenn der Laden als Kategorie dasteht
        es = imports.parse_playnite("Name,Kategorien,Spiel-ID,Schlagwörter\nSky Garden,Steam,3000001,VR\n")
        self.assertEqual((es[0]["steam_appid"], es[0]["steam_sure"], es[0]["label"]), ("3000001", True, "Steam"))

    def test_systems(self):
        """Jedes Spiel mit System aus der Plattform-Spalte; PC, sobald ein PC dabei ist. Alte
        Dateien ohne System gelten als PC; ein neuer Import ersetzt nur seine Systeme."""
        so = collection.system_of
        self.assertEqual([so(["Sony PlayStation 4"]), so(["Sony PlayStation 2"]), so(["Sony PlayStation"]),
                          so(["Nintendo Game Boy Advance"]), so(["Nintendo Game Boy Color"]), so(["Nintendo Game Boy"]),
                          so(["Nintendo 3DS"]), so(["Nintendo DS"]), so(["Nintendo Super Nintendo Entertainment System"]),
                          so(["Nintendo Entertainment System"]), so(["Nintendo 64"]), so(["Nintendo GameCube"]),
                          so(["Nintendo Wii"]), so(["Nintendo Wii U"]), so(["Nintendo Virtual Boy"]), so(["Microsoft Xbox One"])],
                         ["PS4", "PS2", "PS1", "GBA", "GBC", "GB", "3DS", "DS", "SNES", "NES", "N64", "GameCube",
                          "Wii", "Wii U", "VB", "Xbox One"])
        self.assertEqual([so(["PC (Windows)", "Sony PlayStation 4"]), so([]), so(["Amiga"]), so([], "PlayStation", "PPSA00001_00")],
                         ["PC", "PC", "PC", "PS5"])
        text = ("Name,Spiel-ID,Quelle,Plattformen,Features\n"
                "Orbit Golf,3000040,Steam,PC (Windows),\n"
                "Orbit Golf,,,Sony PlayStation 4,\"Local Co-Op\"\n"
                "Pixel Kart,,,Nintendo Super Nintendo Entertainment System,\n"
                "Pixel Kart,,,Nintendo Super Nintendo Entertainment System,\n")
        stats = {}
        g = collection.parse(text, stats=stats)
        self.assertEqual(sorted(g), ["name:ps4:orbit golf", "name:snes:pixel kart", "steam:3000040"])
        self.assertEqual(stats["systems"], {"PC": 1, "PS4": 1, "SNES": 1})
        self.assertNotIn("system", g["steam:3000040"])        # PC bleibt wie in alten Dateien ohne Feld
        # ohne Laden und mit kleiner Zahl als Kennung: Steam vermutet, aber nur am PC
        self.assertEqual(collection.parse("Name,Spiel-ID,Plattformen\nDeep Dive,12345,Sony PlayStation 4\n")["name:ps4:deep dive"]["store"], "")
        # alte Datei ohne System: alles PC; Reiter in der Reihenfolge PC, dann Konsolen
        old = {"games": {"steam:3000001": {"name": "Sky Garden", "store": "Steam", "id": "3000001"}}}
        self.assertEqual(collection.view(old)["games"][0]["system"], "PC")
        col = json.loads(json.dumps(old))
        collection.replace(col, collection.parse("Name,Plattformen\nRetro Run,Nintendo Super Nintendo Entertainment System\n"))
        self.assertEqual(collection.view(col)["systems"], [["PC", 1], ["SNES", 1]])    # nur SNES dazu
        collection.replace(col, g)                             # ein Export mit PC ersetzt die PC-Spiele
        self.assertEqual(collection.view(col)["systems"], [["PC", 1], ["PS4", 1], ["SNES", 1]])
        self.assertEqual(sorted(col["games"]), ["name:ps4:orbit golf", "name:snes:pixel kart", "steam:3000040"])

    def test_retro(self):
        """Retro-Liste: System aus Endung, sonst aus dem Ordner; Region und Sprache aus dem Namen;
        Archiv-Ordner, Spielstände und Beiwerk zählen nicht; ein Eintrag je Titel und System."""
        text = "\n".join([
            "ROMs/Nintendo - Game Boy/gb/Jump & Run/Moon Rover (Europe) (En,Fr,De).gb",
            "ROMs/Nintendo - Game Boy/gb/Jump & Run/Moon Rover (USA).gb",
            "ROMs/Nintendo - Game Boy/gb_zip/Moon Rover (Europe) (En,Fr,De).zip",
            "ROMs/Nintendo - Game Boy/gb/saves/Moon Rover (Europe).sav",
            "ROMs/Nintendo - Game Boy/gb/_Extras/Homebrew/Tiny Tennis (World) (Aftermarket) (Unl).gb",
            "ROMs/Nintendo - Super Nintendo Entertainment System/snes/Legend of Pixels, The (Germany).sfc",
            "ROMs/Nintendo - Super Nintendo Entertainment System/snes/Star Hop (Japan).sfc",
            "ROMs/Nintendo - Nintendo 3DS/3ds/Puzzle/0004000000ABC000 Comet Chase (CTR-P-ABCP) (v0) (E).standard.cia",
            "D:\\Spiele\\Retro\\PS1\\Harbor Heist (Europe) (Disc 1).chd",
            "D:\\Spiele\\Retro\\PS1\\Harbor Heist (Europe) (Disc 2).chd",
            "D:\\Spiele\\Retro\\Neu\\Comet Chase.iso",
            "ROMs/Spiele-Liste.xlsx"])
        self.assertTrue(retro.looks_like(text))
        self.assertFalse(retro.looks_like(PLAYNITE))
        self.assertEqual(imports.detect(SHEET), "sheet")
        games, st = retro.parse(text)
        self.assertEqual(sorted(games), ["retro:3ds:comet chase", "retro:gb:moon rover", "retro:gb:tiny tennis",
                                         "retro:ps1:harbor heist", "retro:snes:star hop", "retro:snes:the legend of pixels"])
        self.assertEqual((st["files"], st["archive"], st["save"], st["extra"], st["unknown"]), (8, 2, 0, 1, 1))    # saves/ zählt wie ein Archiv-Ordner
        self.assertEqual(retro.unknown_lines(text), ["Comet Chase.iso"])
        mr = games["retro:gb:moon rover"]
        self.assertEqual((mr["files"], mr["regions"], mr["langs"], mr["lang_guess"]), (2, ["Europe", "USA"], ["De", "En", "Fr"], False))
        lp = games["retro:snes:the legend of pixels"]
        self.assertEqual((lp["name"], lp["langs"], lp["lang_guess"]), ("The Legend of Pixels", ["De"], True))    # aus der Region: ≈
        self.assertEqual(games["retro:snes:star hop"]["langs"], ["Ja"])
        self.assertEqual(games["retro:gb:tiny tennis"]["flags"], ["homebrew"])
        cc = games["retro:3ds:comet chase"]
        self.assertEqual((cc["regions"], cc["tid"], cc["serial"]), (["Europe"], "0004000000ABC000", "CTR-P-ABCP"))
        self.assertEqual(games["retro:ps1:harbor heist"]["files"], 2)
        self.assertNotIn("Spiele", json.dumps(games))                  # keine Pfade in den Daten
        # Sammlung von 0.6.0: die erste PlayStation hieß „PS“, wird beim Einlesen zu PS1, ohne Doppel
        c0 = {"games": {"retro:ps:harbor heist": {"name": "Harbor Heist", "system": "PS", "src": retro.SRC, "info": {"x": 1}}}}
        retro.apply(c0, {k: g for k, g in games.items() if g["system"] == "PS1"}, dry=False)
        self.assertEqual(list(c0["games"]), ["retro:ps1:harbor heist"])
        self.assertEqual((c0["games"]["retro:ps1:harbor heist"]["system"], c0["games"]["retro:ps1:harbor heist"]["info"]), ("PS1", {"x": 1}))
        # CSV „System; Titel“
        g2, _ = retro.parse("System;Titel\nSNES;Star Hop (Japan)\nGame Boy Advance;Orbit Golf\n")
        self.assertEqual(sorted(g2), ["retro:gba:orbit golf", "retro:snes:star hop"])
        # Sammlung: Playnite und Retro nebeneinander; fehlt ein Spiel, wird es markiert statt gelöscht
        col = json.loads(json.dumps(collection.EMPTY))
        collection.replace(col, collection.parse("Name,Plattformen\nStar Hop,Nintendo Super Nintendo Entertainment System\n"))
        self.assertEqual(retro.apply(col, games, dry=True), (6, []))
        self.assertEqual(retro.apply(col, games, dry=False)[0], 6)
        self.assertEqual(len(col["games"]), 7)                         # Playnite-Eintrag bleibt eigener Eintrag
        collection.replace(col, collection.parse("Name,Plattformen\nOther Game,Nintendo Super Nintendo Entertainment System\n"))
        self.assertIn("retro:snes:star hop", col["games"])             # Playnite-Import lässt Retro stehen
        less, _ = retro.parse("\n".join(text.splitlines()[5:]))       # ohne die Game-Boy-Zeilen
        self.assertEqual(retro.apply(col, less, dry=True), (0, []))    # GB fehlt ganz: kein System der Liste
        fewer = {k: v for k, v in games.items() if k != "retro:snes:star hop"}
        self.assertEqual(retro.apply(col, fewer, dry=False), (0, ["Star Hop"]))
        self.assertEqual(retro.gone(col), [("Star Hop", "SNES")])
        v = {r["key"]: r for r in collection.view(col)["games"]}
        self.assertTrue(v["retro:snes:star hop"]["gone"])
        self.assertEqual(v["retro:gb:moon rover"]["files"], 2)
        fresh = lambda: {k: v for k, v in retro.parse(text)[0].items() if k != "retro:snes:star hop"}
        retro.apply(col, retro.parse(text)[0], dry=False)              # taucht wieder auf: Marke fällt weg
        self.assertFalse(retro.gone(col))
        retro.apply(col, fresh(), dry=False)
        self.assertEqual(retro.settle(col, "keep"), 1)                 # behalten: Spiel bleibt, Marke weg
        self.assertFalse(retro.gone(col))
        self.assertIn("retro:snes:star hop", col["games"])
        retro.apply(col, fresh(), dry=False)
        self.assertEqual(retro.settle(col, "drop"), 1)
        self.assertNotIn("retro:snes:star hop", col["games"])

    def test_retro_languages(self):
        """Gab es eine Fassung mit Deutsch? Fassungen eines Spiels über Produktcode (AMRE/AMRD),
        Retool-Gruppe oder gleichen Namen; Beta-Fassungen zählen nicht."""
        idx = retro.build_index(RETRO_DAT, RETRO_RETOOL)
        self.assertEqual(len(idx["rel"]), 7)
        g = lambda name, langs: {"name": name, "langs": langs}
        self.assertEqual(retro.match(g("Moon Rover", ["En"]), idx),
                         {"st": "missing", "alt": "Mondfahrer (Germany)", "guess": True, "via": "code"})
        self.assertEqual(retro.match(g("Star Hop", ["En"]), idx),
                         {"st": "missing", "alt": "Sternhuepfer (Europe) (En,Fr,De)", "guess": False, "via": "retool"})
        self.assertEqual(retro.match(g("The Legend of Pixels", ["En"]), idx)["via"], "name")
        self.assertEqual(retro.match(g("Pixel Kart", ["En"]), idx), {"st": "none"})
        self.assertEqual(retro.match(g("Mondfahrer", ["De"]), idx), {"st": "have"})
        self.assertEqual(retro.match(g("Comet Chase", ["En"]), idx), {"st": "unknown"})
        # ohne Retool-Liste bleibt die Umbenennung unerkannt
        self.assertEqual(retro.match(g("Star Hop", ["En"]), retro.build_index(RETRO_DAT))["st"], "none")
        self.assertTrue(retro.urls("GBA")[1].endswith("Game%20Boy%20Advance%20%28No-Intro%29.json"))
        self.assertIn("/metadat/redump/", retro.urls("PS1")[0])
        self.assertIsNone(retro.urls("Wii U"))
        col = {"games": {}}
        retro.apply(col, retro.parse("GBA/Moon Rover (USA).gba\nGBA/Pixel Kart (USA, Europe).gba\n3DS/Comet Chase (E).cia\n")[0], dry=False)
        self.assertEqual(retro.mark_languages(col, {"GBA": idx}), {"missing": 1, "none": 1})
        v = {r["name"]: r for r in collection.view(col)["games"]}
        self.assertEqual(v["Moon Rover"]["de"]["alt"], "Mondfahrer (Germany)")
        self.assertIsNone(v["Comet Chase"]["de"])

    def test_retro_3ds_and_near(self):
        """3DS (0.8.4): Fassung über den Produktcode im Dateinamen, Sprachen dann laut No-Intro; Gruppe über den
        Code auch bei anderem Titel. Ähnliche Namen nur als Vorschlag, bestätigt gilt der Titel der Liste."""
        dat = ('game (\n\tname "Moon Rover 3D (Europe) (En,Fr,De)"\n\trom ( name "Moon Rover 3D (Europe) (En,Fr,De).3ds" serial "CTR-P-AMQP" )\n)\n'
               'game (\n\tname "Moon Rover 3D (USA)"\n\trom ( name "Moon Rover 3D (USA).3ds" serial "CTR-P-AMQE" )\n)\n'
               'game (\n\tname "Pixel Garden Deluxe (Europe) (En,Fr,De)"\n\trom ( name "Pixel Garden Deluxe (Europe) (En,Fr,De).3ds" serial "CTR-P-BPGP" )\n)\n')
        digital = 'game (\n\tname "Tiny Tennis Tour (Europe) (eShop)"\n\trom ( name "Tiny Tennis Tour (Europe) (eShop).3ds" serial "CTR-N-JTTP" )\n)\n'
        idx = retro.build_index(dat + "\n" + digital)
        col = {"games": {}}
        retro.apply(col, retro.parse("3DS/0004000000AB1200 Moon Rover 3D (CTR-P-AMQP) (v0) (E).standard.cia\n"
                                     "3DS/0004000000AB1300 Mondrover (CTR-P-AMQE) (v0) (U).cia\n"
                                     "3DS/Pixel Garden (E).3ds\n3DS/Comet Chase (E).3ds\n")[0], dry=False)
        games = col["games"]
        self.assertEqual(games["retro:3ds:moon rover 3d"]["serial"], "CTR-P-AMQP")
        retro.mark_languages(col, {"3DS": idx})
        self.assertEqual(games["retro:3ds:moon rover 3d"]["de"]["st"], "have")
        self.assertEqual(games["retro:3ds:moon rover 3d"]["de"]["langs"], ["De", "En", "Fr"])
        self.assertEqual(games["retro:3ds:mondrover"]["de"], {"st": "missing", "alt": "Moon Rover 3D (Europe) (En,Fr,De)", "guess": False, "via": "code"})
        self.assertEqual(games["retro:3ds:pixel garden"]["de"], {"st": "unknown", "near": "Pixel Garden Deluxe"})
        self.assertNotIn("near", games["retro:3ds:comet chase"]["de"])
        v = {r["name"]: r for r in collection.view(col)["games"]}
        self.assertEqual((v["Moon Rover 3D"]["langs"], v["Moon Rover 3D"]["lang_guess"]), (["De", "En", "Fr"], False))
        self.assertEqual([x["near"] for x in retro.near_list(col)], ["Pixel Garden Deluxe"])
        # bestätigen: der Titel der Liste gilt, der Vorschlag ist weg; ablehnen: kommt nicht wieder
        g = retro.settle_near(col, "retro:3ds:pixel garden", True, idx)
        self.assertEqual(g["de"]["st"], "have" if "De" in g["langs"] else "missing")
        self.assertEqual(retro.near_list(col), [])
        col2 = {"games": {"retro:3ds:pixel": {"name": "Pixel Garden", "system": "3DS", "src": "retro", "langs": ["En"],
                                              "de": {"st": "unknown", "near": "Pixel Garden Deluxe"}}}}
        retro.settle_near(col2, "retro:3ds:pixel", False, idx)
        self.assertEqual(col2["games"]["retro:3ds:pixel"]["de"], {"st": "unknown"})
        # Liste der Download-Titel beim 3DS
        self.assertIn("Nintendo%203DS%20%28Digital%29.dat", retro.extra_urls("3DS")[0])
        self.assertIn("Nintendo%20DSi.dat", retro.extra_urls("DS")[0])

    def test_retro_dsiware_and_names(self):
        """0.8.6: DSiWare-Liste mit Dateinamen „00000000“ (der Name des Spiels gilt), Titel ohne Leerzeichen gleich,
        ähnliche Namen nur bei gleichen Zahlen (römisch wie arabisch)."""
        dat = ('game (\n\tname "Moon Rover (Europe) (En,Fr,De)"\n\tserial "KMRP"\n'
               '\trom ( name "00000000" size 1 crc 00000001 serial "KMRP" )\n)\n'
               'game (\n\tname "Mega Comet Zero (USA, Europe)"\n\trom ( name "Mega Comet Zero (USA, Europe).nds" size 1 )\n)\n'
               'game (\n\tname "Mega Comet Zero 2 (Europe)"\n\trom ( name "Mega Comet Zero 2 (Europe).nds" size 1 )\n)\n'
               'game (\n\tname "Pixel Garden (Europe)"\n\trom ( name "Pixel Garden (Europe).nds" size 1 )\n)\n'
               'game (\n\tname "Star Hop IV - Heimweg (Europe) (De)"\n\trom ( name "Star Hop IV - Heimweg (Europe) (De).nds" size 1 )\n)\n')
        idx = retro.build_index(dat)
        self.assertEqual(len(idx["rel"]), 5)
        self.assertNotIn("00000000", idx["grp"])
        g = lambda n: {"name": n, "langs": ["En"], "lang_guess": False}
        self.assertEqual(retro.match(g("Moon Rover"), idx)["st"], "missing")
        self.assertEqual(retro.match(g("MegaComet Zero"), idx)["st"], "none")                 # ohne Leerzeichen gleich
        self.assertEqual(retro.match(g("Pixel Garden 2"), idx), {"st": "unknown"})            # andere Zahl, kein Vorschlag
        self.assertEqual(retro.match(g("Mega Comet Zero 3"), idx), {"st": "unknown"})
        self.assertEqual(retro.match(g("Star Hop 4 Heimweg"), idx)["near"], "Star Hop IV - Heimweg")
        self.assertEqual(retro.extra_urls("GBA"), [])

    def test_replace_keeps_fetched_and_gem(self):
        col = json.loads(json.dumps(collection.EMPTY))
        self.assertEqual(collection.replace(col, collection.parse(COLLECTION)), 4)
        col["games"]["steam:3000103"]["rev"] = {"n": 300, "pct": 92, "at": "2026-10-01"}
        self.assertEqual(collection.replace(col, collection.parse(COLLECTION)), 0)
        self.assertEqual(col["games"]["steam:3000103"]["rev"]["n"], 300)
        self.assertEqual(collection.gem(col["games"]["steam:3000103"]), (0.37, False))
        # ohne Rezensionen keine Aussage; Wertungen aus Playnite zählen nicht
        self.assertEqual(collection.gem(col["games"]["steam:3000101"]), (0.0, True))
        col["games"]["steam:3000101"]["rev"] = {"n": 40, "pct": 95}
        self.assertEqual(collection.gem(col["games"]["steam:3000101"]), (0.0, True))    # unter 50 Rezensionen
        col["games"]["steam:3000101"]["rev"] = {"n": 400, "pct": 69}
        self.assertEqual(collection.gem(col["games"]["steam:3000101"]), (0.0, False))   # unter 70 %
        del col["games"]["steam:3000101"]["rev"]
        v = collection.view(col)
        self.assertEqual(v["n"], 4)
        self.assertEqual([r["name"] for r in v["games"]], ["Fleet Night", "Harbor Heist", "Quiet Garden", "Sofa Smash"])
        self.assertEqual(v["games"][1]["url"], "https://store.steampowered.com/app/3000101/")
        self.assertIn("Puzzle", v["genres"])

    def test_server_import_export_restore(self):
        store.DATA_DIR = tempfile.mkdtemp()
        data = store.load_data()
        res = server.import_collection(data, COLLECTION, dry=True)
        self.assertEqual(res, {"n": 4, "new": 4, "console": 0, "systems": {"PC": 4}, "kept": 0})
        self.assertNotIn("collection", data["imports"])
        server.import_collection(data, COLLECTION, dry=False)
        self.assertEqual(data["imports"]["collection"]["n"], 4)
        self.assertEqual(server.import_collection(data, COLLECTION, dry=True)["new"], 0)
        col = store.load_json(collection.FILE, collection.EMPTY)
        self.assertEqual(len(col["games"]), 4)


class TestLibrary(unittest.TestCase):
    def test_best_fallback(self):
        """Ohne eigenen Verlauf gilt das Allzeit-Tief einer anderen Quelle als Bestpreis (≈)."""
        d = empty()
        k, _ = titles.upsert(d, "Comet Chase", steam_appid="3000030", meta_id="1234567890123456")
        now = "2026-10-20T10:00:00+00:00"
        d["titles"][k].update(wish=True, live={
            "meta": {"price": 20.0, "base": 20.0, "low": 10.0, "low_at": "2025-12-24", "at": now},
            "steam": {"price": 12.0, "base": 24.0, "discount": 50, "at": now},
            "gg": {"retail": 12.0, "retail_low": 12.0, "at": now}})
        at = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
        r = library.row(k, d["titles"][k], at=at, hist={}, data=d)
        self.assertEqual((r["best"]["meta"]["best"], r["best"]["meta"]["level"], r["best"]["meta"]["over"]), (10.0, "", 10.0))
        self.assertIn("QuestStoreDB", r["best"]["meta"]["src"])
        self.assertEqual((r["best"]["steam"]["best"], r["best"]["steam"]["level"]), (12.0, "best"))
        # mit eigenem Verlauf (mit Preiswechsel) zählt der, ohne Quelle
        hist = {"steam": {"3000030": [["2025-01-01", 24.0], ["2025-06-01", 9.0], ["2025-06-10", 24.0]]}}
        r = library.row(k, d["titles"][k], at=at, hist=hist, data=d)
        self.assertEqual((r["best"]["steam"]["best"], r["best"]["steam"].get("src")), (9.0, None))

    def test_grade_and_now(self):
        """Preisgüte wie im eShopKompass; Jetzt zeigt nur Angebote mit „kaufen“ oder „gut“."""
        g = library.grade
        self.assertEqual([g(10.2, 10), g(10.5, 10), g(11.5, 10), g(12.0, 10), g(13.0, 10), g(1.5, 1.0), g(None, 1)],
                         ["buy", "buy", "good", "good", "wait", "good", ""])
        d = empty()
        now = "2026-10-20T10:00:00+00:00"
        for name, app, price in (("Comet Chase", "3000030", 12.0), ("Orbit Golf", "3000040", 30.0)):
            k, _ = titles.upsert(d, name, steam_appid=app)
            d["titles"][k].update(wish=True, live={"steam": {"price": price, "base": 40.0, "discount": 50, "at": now},
                                                   "gg": {"retail": price, "retail_low": 10.0, "at": now}})
        v = library.view(d, at=datetime(2026, 10, 20, 12, tzinfo=timezone.utc), hist={})
        self.assertEqual(([r["name"] for r in v["now"]], [r["name"] for r in v["now_far"]]), (["Comet Chase"], ["Orbit Golf"]))

    def test_best_all(self):
        """Bestpreis über beide Läden: war Meta einmal günstiger, ist Steam jetzt nicht am Bestpreis."""
        d = empty()
        k, _ = titles.upsert(d, "Comet Chase", steam_appid="3000030", meta_id="1234567890123456")
        now = "2026-10-20T10:00:00+00:00"
        d["titles"][k].update(wish=True, live={
            "meta": {"price": 30.0, "base": 30.0, "low": 15.0, "low_at": "2025-12-24", "at": now},
            "steam": {"price": 18.0, "base": 40.0, "discount": 55, "at": now},
            "gg": {"retail": 18.0, "retail_low": 18.0, "at": now}})
        at = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
        r = library.row(k, d["titles"][k], at=at, hist={}, data=d)
        self.assertEqual((r["best_all"]["best"], r["best_all"]["shop"]), (15.0, "meta"))
        self.assertIn("QuestStoreDB", r["best_all"]["src"])
        self.assertEqual(r["best"]["steam"]["level"], "best")
        self.assertEqual((r["best"]["steam"]["all_level"], r["best"]["steam"]["all_over"]), ("", 3.0))
        self.assertEqual((r["best"]["meta"]["all_level"], r["best"]["meta"]["all_over"]), ("", 15.0))
        d["titles"][k]["live"]["steam"]["price"] = 14.0
        r = library.row(k, d["titles"][k], at=at, hist={}, data=d)
        self.assertEqual((r["best_all"]["shop"], r["best"]["steam"]["all_level"]), ("steam", "best"))
        d["titles"][k]["live"] = {}
        self.assertIsNone(library.row(k, d["titles"][k], at=at, hist={}, data=d)["best_all"])

    def test_crossbuy_origin(self):
        """Crossbuy mit Herkunft: von Hand vor VRDB vor Tabelle vor Recherche; ältere Daten ohne
        Angabe gelten mit Tabellenzeile als Tabelle. Widerspruch: der stärkere gilt, der andere
        steht daneben."""
        d = empty()
        k, _ = titles.upsert(d, "Comet Chase")
        t = d["titles"][k]
        t.update(crossbuy=False, sheet={"meta": 9.99, "at": "2026-10-21T10:00:00+00:00"})
        self.assertEqual(library.crossbuy(t), (False, "Tabelle", ""))
        t["opinion"] = {"crossbuy": True}
        self.assertEqual(library.crossbuy(t), (False, "Tabelle", ""))       # Recherche zählt nicht als Widerspruch
        t["vrdb"] = {"crossbuy": True}
        self.assertEqual(library.crossbuy(t), (True, "VRDB", "Tabelle: nein"))
        t.update(crossbuy=False, crossbuy_src="Hand")
        self.assertEqual(library.crossbuy(t), (False, "Hand", "VRDB: ja"))
        t.update(crossbuy=None, crossbuy_src=None, sheet=None, vrdb={})
        self.assertEqual(library.crossbuy(t), (True, "Recherche", ""))
        t.update(crossbuy=True, opinion=None)
        self.assertEqual(library.crossbuy(t), (True, "Hand", ""))           # alte Daten ohne Tabelle: von Hand
        imports.import_sheet(d, SHEET, dry=False)
        self.assertTrue(all(x.get("crossbuy_src") == "Tabelle" for x in d["titles"].values()
                            if x.get("crossbuy") is not None and x["name"] != "Comet Chase"))

    def test_gap_and_where(self):
        d = empty()
        imports.import_sheet(d, SHEET, dry=False)
        imports.import_playnite(d, PLAYNITE, dry=False)
        imports.import_meta(d, META_JSON, dry=False)
        v = library.view(d)
        sky = next(r for r in v["wishlist"] if r["name"] == "Sky Garden")
        self.assertEqual(sky["gap"], -2.0)                 # Meta-Tief 4 gegen gg.deals 6
        self.assertEqual(sky["where"], "beide")
        self.assertEqual(v["counts"]["both"], 1)
        # Besessene Wunschtitel zählen getrennt; die Oberfläche blendet sie aus
        self.assertEqual(v["counts"]["owned_wish"], 2)    # Sky Garden (beide), Laser Tennis (PC)
        self.assertEqual(v["counts"]["wish"], 2)
        labels = [l["label"] for l in sky["links"]]
        self.assertEqual(labels[:2], ["Meta", "VRDB"])
        self.assertIn("Reddit", labels)


class TestSources(unittest.TestCase):
    def test_blocked_target(self):
        self.assertEqual(sources.blocked_target("file:///etc/passwd"), "nur http und https")
        self.assertEqual(sources.blocked_target("http://127.0.0.1:8788/"), "Adresse nicht öffentlich")
        self.assertEqual(sources.blocked_target("https://user:pw@example.com/"), "Adresse mit Zugangsdaten")

    def test_version(self):
        self.assertRegex(sources.VERSION, r"^\d+\.\d+\.\d+$")


class TestServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        store.DATA_DIR = tempfile.mkdtemp()
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def call(self, path, body=None, ctype="application/json", host=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data, method="POST" if body is not None else "GET")
        if body is not None:
            req.add_header("Content-Type", ctype)
        if host:
            req.add_header("Host", host)
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_flow(self):
        code, page = self.call("/")
        self.assertEqual(code, 200)
        self.assertIn(b"VR-Navigator", page)
        self.assertEqual(self.call("/js/app.js")[0], 200)
        self.assertEqual(self.call("/../app/server.py")[0], 404)
        code, raw = self.call("/api/import", {"kind": "sheet", "text": SHEET, "dry": True})
        self.assertEqual(json.loads(raw)["n"], 4)
        self.assertEqual(json.loads(self.call("/api/state")[1])["counts"]["all"], 0)
        code, raw = self.call("/api/import", {"kind": "sheet", "text": SHEET, "dry": False})
        st = json.loads(raw)["state"]
        self.assertEqual(st["counts"]["wish"], 4)
        key = "meta-1111111111111111"
        code, raw = self.call("/api/title", {"key": key, "note": "Reddit: Quest-Fassung gleichwertig", "owned_meta": True})
        st = json.loads(raw)
        self.assertEqual(st["counts"]["meta"], 1)
        self.call("/api/title", {"key": key, "name": "Sky Garden Neu"})
        st = json.loads(self.call("/api/import", {"kind": "meta", "text": "Bestellnummer 9000000000000001\nGESAMT 1,99 €\nSky Garden\nGekauft", "dry": True})[1])
        self.assertEqual(st["new"], 0)
        self.call("/api/title", {"key": key, "name": "Sky Garden"})
        code, raw = self.call("/api/title", {"key": key, "steam_appid": "x1"})
        self.assertEqual(code, 400)
        code, raw = self.call("/api/title/new", {"name": "Neu", "link": "https://store.steampowered.com/app/42/"})
        self.assertIn("steam-42", [r["key"] for r in json.loads(raw)["wishlist"]])
        code, raw = self.call("/api/export")
        backup = json.loads(raw)
        self.assertEqual(len(backup["data"]["titles"]), 5)
        self.call("/api/title/delete", {"key": "steam-42"})
        code, raw = self.call("/api/restore", {"data": backup["data"]})
        self.assertEqual(json.loads(raw)["counts"]["all"], 5)

    def test_retro_import(self):
        text = ("ROMs/SNES/Star Hop (USA).sfc\nROMs/SNES/Pixel Kart (Europe) (En,De).sfc\n"
                "ROMs/GBA/Orbit Golf (Germany).gba\nROMs/snes_zip/Star Hop (USA).zip\n")
        n0 = json.loads(self.call("/api/collection")[1])["n"]
        code, body = self.call("/api/import", {"kind": "auto", "text": text, "dry": True})
        p = json.loads(body)
        self.assertEqual((code, p["kind"], p["n"], p["new"], p["systems"]), (200, "retro", 3, 3, {"SNES": 2, "GBA": 1}))
        self.assertEqual(json.loads(self.call("/api/collection")[1])["n"], n0)      # Vorschau speichert nichts
        p = json.loads(self.call("/api/import", {"kind": "retro", "text": text, "dry": False})[1])
        self.assertEqual(p["state"]["imports"]["retro"]["n"], 3)
        p = json.loads(self.call("/api/import", {"kind": "retro", "text": text.split("\n", 1)[1], "dry": False})[1])
        self.assertEqual((p["gone"], p["state"]["imports"]["retro"]["gone"]), (["Star Hop"], 1))
        code, body = self.call("/api/retro/gone", {"action": "drop"})
        self.assertEqual((code, json.loads(body)["changed"], json.loads(body)["collection"]["n"]), (200, 1, n0 + 2))
        self.assertEqual(self.call("/api/retro/gone", {"action": "nope"})[0], 400)
        self.assertEqual(self.call("/api/import", {"kind": "retro", "text": "nur Text", "dry": True})[0], 400)

    def test_collection(self):
        code, body = self.call("/api/import", {"kind": "auto", "text": COLLECTION, "dry": False})
        self.assertEqual(code, 200)
        self.assertEqual(json.loads(body)["collection"]["n"], 4)
        code, body = self.call("/api/collection")
        self.assertEqual(json.loads(body)["n"], 4)
        backup = json.loads(self.call("/api/export")[1])
        self.assertEqual(len(backup["collection"]["games"]), 4)
        # Sicherung von vor 0.4.0 ohne Sammlung: die vorhandene bleibt
        self.assertEqual(self.call("/api/restore", {"data": backup["data"]})[0], 200)
        self.assertEqual(json.loads(self.call("/api/collection")[1])["n"], 4)
        backup["collection"]["games"] = {"x": {"name": "Erfunden"}, "y": "kaputt"}
        self.call("/api/restore", {"data": backup["data"], "collection": backup["collection"]})
        self.assertEqual(json.loads(self.call("/api/collection")[1])["n"], 1)

    def test_marks(self):
        # Mein Stand (0.6.0): je Spiel gespeichert, in der Sicherung, Zurücknehmen löscht den Eintrag
        code, body = self.call("/api/mark", {"key": "steam:3000001", "k": "s", "v": "started"})
        self.assertEqual((code, json.loads(body)["marks"]["steam:3000001"]), (200, {"s": "started"}))
        self.call("/api/mark", {"key": "steam:3000001", "k": "fav", "v": True})
        self.assertEqual(json.loads(self.call("/api/state")[1])["marks"]["steam:3000001"], {"s": "started", "fav": True})
        backup = json.loads(self.call("/api/export")[1])
        self.assertEqual(backup["data"]["marks"]["steam:3000001"]["s"], "started")
        self.call("/api/mark", {"key": "steam:3000001", "k": "s", "v": None})
        self.call("/api/mark", {"key": "steam:3000001", "k": "fav", "v": False})
        self.assertNotIn("steam:3000001", json.loads(self.call("/api/state")[1])["marks"])
        self.assertEqual(self.call("/api/mark", {"key": "x", "k": "s", "v": "nie"})[0], 400)
        self.assertEqual(self.call("/api/mark", {"key": "", "k": "s", "v": "done"})[0], 400)
        # Sicherung von vor 0.6.0 ohne marks lädt weiter
        del backup["data"]["marks"]
        self.assertEqual(self.call("/api/restore", {"data": backup["data"]})[0], 200)
        self.assertEqual(json.loads(self.call("/api/state")[1])["marks"], {})

    def test_abgleich_download(self):
        # Abgleichsdaten zum Nachprüfen: nie Schlüssel oder Konten
        sync.save_settings({"gg_key": "geheim-erfunden-1234", "sharenite": "https://www.sharenite.link/profiles/erfunden/games"})
        code, raw = self.call("/api/abgleich")
        self.assertEqual(code, 200)
        self.assertNotIn(b"geheim-erfunden", raw)
        self.assertNotIn(b"sharenite.link", raw)
        self.assertIn("hours", json.loads(raw)["settings"])
        sync.save_settings({"gg_key": "", "sharenite": ""})

    def test_diag_runs_in_background(self):
        """Verbindungstest (0.8.0): POST startet, GET liefert den Stand, ein zweiter Start läuft nicht doppelt."""
        gate, calls = threading.Event(), []

        def slow():
            calls.append(1)
            gate.wait(5)
            return ["Zeile eins"]
        old, sync.diagnose = sync.diagnose, slow
        try:
            first = json.loads(self.call("/api/diag", {})[1])
            self.assertTrue(first["running"])
            self.assertTrue(json.loads(self.call("/api/diag", {})[1])["running"])
            gate.set()
            for _ in range(50):
                d = json.loads(self.call("/api/diag")[1])
                if not d["running"]:
                    break
                threading.Event().wait(0.05)
            self.assertEqual(d["lines"], ["Zeile eins"])
            self.assertEqual(d["id"], first["id"])
            self.assertEqual(len(calls), 1)
        finally:
            sync.diagnose = old

    def test_nexus_key(self):
        """Nexus-Schlüssel (0.7.7): bleibt auf dem Server, die Oberfläche sieht nur, dass er da ist."""
        fake = "ErfundenNexus0123456789--AbCdEfGh+/=="
        with self.assertRaises(ValueError):
            sync.save_settings({"nexus_key": "kein Schlüssel!"})
        sync.save_settings({"nexus_key": fake})
        try:
            code, raw = self.call("/api/state")
            self.assertEqual(code, 200)
            self.assertNotIn(fake.encode(), raw)
            self.assertTrue(json.loads(raw)["settings"]["nexus_set"])
            self.assertNotIn(fake.encode(), self.call("/api/abgleich")[1])
        finally:
            sync.save_settings({"nexus_key": ""})
        self.assertFalse(server.settings_view()["nexus_set"])

    def test_delete_and_merge_can_be_undone(self):
        old_dir, store.DATA_DIR = store.DATA_DIR, tempfile.mkdtemp()
        try:
            self._undo()
        finally:
            store.DATA_DIR = old_dir

    def _undo(self):
        code, raw = self.call("/api/title/new", {"name": "Weg und zurück"})
        key = [r["key"] for r in json.loads(raw)["wishlist"] if r["name"] == "Weg und zurück"][0]
        self.call("/api/title", {"key": key, "note": "bleibt erhalten"})
        # Crossbuy: „ja“ von Hand gilt, „automatisch“ nimmt die eigene Angabe zurück
        self.call("/api/title", {"key": key, "crossbuy": True})
        self.assertEqual(library.crossbuy(store.load_data()["titles"][key])[:2], (True, "Hand"))
        self.call("/api/title", {"key": key, "crossbuy": None})
        self.assertIsNone(store.load_data()["titles"][key].get("crossbuy"))
        res = json.loads(self.call("/api/title/delete", {"key": key})[1])
        self.assertNotIn(key, [r["key"] for r in res["wishlist"]])
        self.assertEqual(res["undo"][key]["note"], "bleibt erhalten")
        res = json.loads(self.call("/api/title/restore", {"titles": res["undo"]})[1])
        self.assertIn(key, [r["key"] for r in res["wishlist"]])
        self.assertIsNone(json.loads(self.call("/api/title/delete", {"key": "gibt-es-nicht"})[1])["undo"])
        # Wunschliste abgleichen: eine Aktion für mehrere Titel, mit Rückgängig
        res = json.loads(self.call("/api/wishes", {"kind": "drop", "keys": [key]})[1])
        self.assertEqual(res["changed"], 1)
        self.assertNotIn(key, [r["key"] for r in res["wishlist"]])
        res = json.loads(self.call("/api/title/restore", {"titles": res["undo"]})[1])
        self.assertIn(key, [r["key"] for r in res["wishlist"]])
        self.assertIn("lists", res)
        # Zusammenführen: beide Einträge kommen zurück, wie sie waren
        self.call("/api/title/new", {"name": "Zwilling A"})
        st = json.loads(self.call("/api/title/new", {"name": "Zwilling B"})[1])
        a, b = (next(r["key"] for r in st["wishlist"] if r["name"] == n) for n in ("Zwilling A", "Zwilling B"))
        res = json.loads(self.call("/api/merge", {"keep": a, "gone": b})[1])
        self.assertNotIn(b, [r["key"] for r in res["wishlist"]])
        res = json.loads(self.call("/api/title/restore", {"titles": res["undo"]})[1])
        self.assertEqual({a, b} - {r["key"] for r in res["wishlist"]}, set())
        for bad in ({}, {"x": {}}, {"a": {"name": "1"}, "b": {"name": "2"}, "c": {"name": "3"}}, "nein"):
            self.assertEqual(self.call("/api/title/restore", {"titles": bad})[0], 400)

    def test_guards(self):
        self.assertEqual(self.call("/api/title", {"key": "x"}, ctype="text/plain")[0], 400)
        self.assertEqual(self.call("/api/state", host="evil.example.com")[0], 421)
        self.assertEqual(self.call("/api/import", {"kind": "nope", "text": ""})[0], 400)
        self.assertEqual(self.call("/api/restore", {"data": {"titles": {"a": {}}}})[0], 400)
        self.assertTrue(server.host_allowed("nas.local:8788"))
        self.assertTrue(server.host_allowed("10.0.0.5"))
        self.assertFalse(server.host_allowed("vr.example.com", extra=""))
        self.assertTrue(server.host_allowed("vr.example.com", extra=".example.com"))

    def test_settings_key_stays_on_server(self):
        code, raw = self.call("/api/settings", {"gg_key": "geheim-1234567890abcd", "hours": 1})
        self.assertEqual(code, 200)
        st = json.loads(raw)["settings"]
        self.assertTrue(st["gg_key_set"])
        self.assertEqual(st["hours"], 2)                  # untere Grenze
        self.assertNotIn("geheim", raw.decode())
        code, raw = self.call("/api/export")
        self.assertNotIn("geheim", raw.decode())
        self.assertEqual(self.call("/api/settings", {"hours": "viele"})[0], 400)
        self.call("/api/settings", {"gg_key": ""})
        # Steam-Schlüssel und Wunschlisten-Link bleiben ebenso auf dem Server
        code, raw = self.call("/api/settings", {"steam_key": "ab" * 16, "steam_id": "76561190000000001",
                                                "gg_wish": "https://gg.deals/wishlist/share/AbCdEfGh12345/",
                                                "sharenite": "https://www.sharenite.link/profiles/beispiel"})
        self.assertEqual(code, 200)
        st = json.loads(raw)["settings"]
        self.assertTrue(st["steam_key_set"] and st["gg_wish_set"])
        self.assertEqual(st["sharenite"], "https://www.sharenite.link/profiles/beispiel/games")
        self.assertNotIn("abababab", raw.decode())
        self.assertNotIn("AbCdEfGh", raw.decode())
        self.assertEqual(self.call("/api/settings", {"steam_key": "kurz"})[0], 400)
        self.assertEqual(self.call("/api/settings", {"gg_wish": "https://example.com/x"})[0], 400)
        self.call("/api/settings", {"steam_key": "", "steam_id": "", "gg_wish": "", "sharenite": ""})


# Erfundene Antworten im Aufbau der echten Quellen (QuestStoreDB, Steam, gg.deals)
def qsdb_game_html(name, meta_id, price, base, until="", hist=()):
    offers = [{"@type": "Offer", "priceCurrency": cur, "sku": meta_id, "price": price * f,
               **({"priceSpecification": {"price": base * f, "priceCurrency": cur}, "priceValidUntil": until}
                  if price != base else {})} for cur, f in (("USD", 1.2), ("EUR", 1))]
    ld = {"@graph": [{"@type": ["SoftwareApplication", "VideoGame"], "name": name,
                      "url": f"https://queststoredb.com/game/{titles.norm(name).replace(' ', '-')}-{meta_id}/",
                      "offers": offers, "softwareVersion": "1.2.3",
                      "aggregateRating": {"ratingValue": 4.2, "ratingCount": 80}},
                     {"@type": "BreadcrumbList"}]}
    pts = [{"x": x, "y": y, "f": f"{y:.2f}\u00a0\u20ac"} for x, y in hist]
    return (f'<html><script type="application/ld+json">{json.dumps(ld)}</script>'
            f'<script id="price-history-data" type="application/json">{json.dumps(pts)}</script></html>')


def qsdb_card(name, meta_id, price, base=None, kind="discount", tag="", end=None, path="game"):
    slug = titles.norm(name).replace(" ", "-")
    benefit = (f'<div class="app-price-benefit"><span>-{round((1 - price / base) * 100)}%</span>'
               f'<span>{tag}</span></div>') if base else ""
    timer = f'<span class="card-info-timer" data-countdown-timer="{end}"></span>' if end else ""
    return f"""<div class="card-image-container" data-x="1">
      <a href="https://www.meta.com/experiences/{meta_id}/"></a>
      <a href="/{path}/{slug}-{meta_id}/"><div class="card-title">
        <div>
          {name}
        </div></div></a></div>
      <div class="card-info-bar">{timer}
      <div class="app-price-container app-price-type-{kind}">{benefit}
        <div class="app-price-amount"><span class=" ">
          {price:.2f} €</span>
          <span>{f"{base:.2f} €" if base else ""}</span></div></div></div>"""


def qsdb_list(*cards, pages=1):
    nav = "".join(f'<a href="?sort=-sale_start_time&amp;page={i}">{i}</a>' for i in range(1, pages + 1))
    return "<html>" + "".join(cards) + nav + "</html>"


class TestPrices(unittest.TestCase):
    def test_best_of(self):
        """Bestpreis aus 24 Monaten: ein einmaliges Tief und das übliche Angebot daneben."""
        hist = [["2023-01-01", 5.0], ["2024-01-01", 30.0], ["2025-03-01", 15.0], ["2025-03-10", 30.0],
                ["2025-11-01", 12.0], ["2025-11-08", 30.0], ["2026-03-01", 15.2], ["2026-03-08", 30.0]]
        b = prices.best_of(hist, "2026-10-22")
        self.assertEqual((b["best"], b["best_at"], b["once"], b["usual"]), (12.0, "2025-11-01", True, 15.0))
        self.assertEqual(b["since"], "2024-10-22")         # das Tief von 2023 liegt davor
        self.assertIsNone(prices.best_of([], "2026-10-22"))
        lvl = lambda p: library._best({"meta": {"1": hist}}, "meta", "1", p, "2026-10-22")
        self.assertEqual(lvl(12.2)["level"], "best")
        self.assertEqual(lvl(15.0)["level"], "usual")
        self.assertEqual((lvl(30.0)["level"], lvl(30.0)["over"]), ("", 18.0))
        # QuestStoreDB-Verlauf und eigener Verlauf: je Tag ein Preis, der eigene gilt
        h = {"meta": {"1": [["2026-10-20", 9.0]]}}
        sync._merge_history(h, "meta", "1", [["2026-01-01", 20.0], ["2026-10-20", 8.0], ["2026-10-21", 9.0]])
        self.assertEqual(h["meta"]["1"], [["2026-01-01", 20.0], ["2026-10-20", 9.0]])

    def test_qsdb_game(self):
        g = prices.qsdb_game(qsdb_game_html("Sky Garden", "1111111111111111", 4.49, 8.99, "2026-11-02",
                                            [(1700000000000, 8.99), (1750000000000, 3.99), (1790000000000, 4.49)]))
        self.assertEqual((g["meta_id"], g["price"], g["base"], g["until"]), ("1111111111111111", 4.49, 8.99, "2026-11-02"))
        self.assertEqual((g["low"], g["low_at"]), (3.99, "2025-06-15"))
        self.assertEqual((g["rating"], g["ratings"], g["version"]), (4.2, 80, "1.2.3"))
        self.assertEqual(g["path"], "/game/sky-garden-1111111111111111/")
        g = prices.qsdb_game(qsdb_game_html("Deep Dive", "3333333333333333", 9.99, 9.99))
        self.assertEqual((g["price"], g["base"], g["until"], g["low"]), (9.99, 9.99, "", None))
        self.assertIsNone(prices.qsdb_game("<html>keine Daten</html>"))

    def test_qsdb_cards(self):
        html = qsdb_list(qsdb_card("Sky Garden", "1111111111111111", 4.49, 8.99, tag="lowest", end=1793170800),
                         qsdb_card("Paint Tool", "5555555555555555", 7.99, 9.99, kind="coupon", tag="coupon", path="app"),
                         qsdb_card("Moon Rover &amp; Friends", "6666666666666666", 12.0, path="bundle", kind="base"),
                         pages=7)
        c = prices.qsdb_cards(html)
        self.assertEqual(len(c), 3)
        self.assertEqual((c[0]["price"], c[0]["base"], c[0]["discount"], c[0]["tag"], c[0]["until"]),
                         (4.49, 8.99, 50, "lowest", "2026-10-28"))
        self.assertEqual((c[1]["kind"], c[1]["discount"]), ("coupon", 20))
        self.assertEqual((c[2]["name"], c[2]["price"], c[2]["base"], c[2]["discount"]), ("Moon Rover & Friends", 12.0, 12.0, 0))
        self.assertEqual(prices.qsdb_pages(html), 7)
        self.assertEqual(prices._num("12.50 $"), None)

    def test_steam(self):
        got = prices.steam_prices(json.dumps({
            "3000001": {"success": True, "data": {"price_overview": {"currency": "EUR", "initial": 1999, "final": 999, "discount_percent": 50}}},
            "3000002": {"success": True, "data": []},
            "3000003": {"success": False},
            "3000004": {"success": True, "data": {"price_overview": {"currency": "USD", "initial": 1, "final": 1}}}}))
        self.assertEqual(got, {"3000001": {"price": 9.99, "base": 19.99, "discount": 50},
                               "3000002": {"price": 0.0, "base": 0.0, "discount": 0}})
        hits = prices.steam_search(json.dumps({"items": [{"type": "app", "id": 3000001, "name": "Sky Garden"},
                                                         {"type": "sub", "id": 9, "name": "Paket"}]}))
        self.assertEqual(hits, [{"appid": "3000001", "name": "Sky Garden"}])

    def test_gg(self):
        got = prices.gg_prices(json.dumps({"success": True, "data": {
            "3000001": {"title": "Sky Garden", "url": "https://gg.deals/game/sky-garden/",
                        "prices": {"currentRetail": "7.49", "currentKeyshops": "5.10", "historicalRetail": "4.99",
                                   "historicalKeyshops": None, "currency": "EUR"}},
            "3000002": None}}))
        self.assertEqual(got["3000001"]["keyshops"], 5.1)
        self.assertIsNone(got["3000001"]["keyshops_low"])
        self.assertNotIn("3000002", got)
        with self.assertRaisesRegex(ValueError, "Invalid key"):
            prices.gg_prices(json.dumps({"success": False, "data": {"message": "Invalid key"}}))


# Erfundene Fassungsliste im Aufbau der libretro-DATs (No-Intro) und eine Retool-Liste dazu
RETRO_DAT = """clrmamepro (
	name "Nintendo - Game Boy Advance"
)

game (
	name "Moon Rover (USA)"
	region "USA"
	serial "AMRE"
	rom ( name "Moon Rover (USA).gba" size 4194304 crc 00000001 serial "AMRE" )
)

game (
	name "Mondfahrer (Germany)"
	region "Germany"
	serial "AMRD"
	rom ( name "Mondfahrer (Germany).gba" size 4194304 crc 00000002 serial "AMRD" )
)

game (
	name "Star Hop (USA)"
	rom ( name "Star Hop (USA).gba" size 4194304 crc 00000003 )
)

game (
	name "Sternhuepfer (Europe) (En,Fr,De)"
	rom ( name "Sternhuepfer (Europe) (En,Fr,De).gba" size 4194304 crc 00000004 )
)

game (
	name "Sternhuepfer (Europe) (En,Fr,De) (Beta)"
	rom ( name "Sternhuepfer (Europe) (En,Fr,De) (Beta).gba" size 4194304 crc 00000005 )
)

game (
	name "Pixel Kart (USA, Europe)"
	rom ( name "Pixel Kart (USA, Europe).gba" size 4194304 crc 00000006 serial "APKE" )
)

game (
	name "Legend of Pixels, The (Europe) (En,Fr,De)"
	rom ( name "Legend of Pixels, The (Europe) (En,Fr,De).gba" size 4194304 crc 00000007 )
)

game (
	name "Legend of Pixels, The (USA)"
	rom ( name "Legend of Pixels, The (USA).gba" size 4194304 crc 00000008 )
)
"""
RETRO_RETOOL = json.dumps({"description": {"name": "Nintendo - Game Boy Advance (No-Intro)", "lastUpdated": "2026-01-01"},
                           "variants": [{"group": "Star Hop", "titles": [{"searchTerm": "Star Hop"}, {"searchTerm": "Sternhuepfer"}]}]})


class FakeNet:
    """Attrappe für sources.fetch: Antworten nach Teil der Adresse, merkt sich jeden Abruf."""

    def __init__(self, answers):
        self.answers, self.calls = answers, []

    def __call__(self, url, timeout=25, ua=None, headers=None):
        self.calls.append(url)
        for part, ans in self.answers.items():
            if part in url:
                if isinstance(ans, int):
                    raise sources.FetchError(url, ans)
                return ans
        raise sources.FetchError(url, 404)


class TestSync(unittest.TestCase):
    def setUp(self):
        store.DATA_DIR = tempfile.mkdtemp()
        self._fetch, self._sleep = sources.fetch, sync.sleep
        sync.sleep = lambda s: None

    def tearDown(self):
        sources.fetch, sync.sleep = self._fetch, self._sleep

    def seed(self):
        d = empty()
        imports.import_sheet(d, SHEET, dry=False)
        # Deep Dive: nur Name, wird über die Suchen gefunden
        k, _ = titles.upsert(d, "Deep Dive")
        d["titles"][k]["wish"] = True
        store.save_data(d)
        return d

    def test_run(self):
        self.seed()
        sync.save_settings({"gg_key": "geheim-1234567890abcd"})
        sources.fetch = net = FakeNet({
            "/on_sale/": qsdb_list(qsdb_card("Laser Tennis", "2222222222222222", 9.0, 30.0, end=1793170800)),
            "/game/sky-garden-1111111111111111/": qsdb_game_html("Sky Garden", "1111111111111111", 7.0, 7.0, hist=[(1700000000000, 3.5)]),
            "/game/laser-tennis-2222222222222222/": qsdb_game_html("Laser Tennis", "2222222222222222", 9.0, 30.0, "2026-10-28",
                                                                    [(1700000000000, 30.0), (1792000000000, 9.0)]),
            "q=Deep+Dive": qsdb_list(qsdb_card("Deep Dive", "3333333333333333", 19.99, kind="base"),
                                     qsdb_card("Deep Dive Demo", "3333333333333334", 0.0, kind="base")),
            "/game/deep-dive-3333333333333333/": qsdb_game_html("Deep Dive", "3333333333333333", 19.99, 19.99),
            "q=Sky+Garden": qsdb_list(qsdb_card("Sky Garden", "1111111111111111", 7.0, kind="base")),
            "all_apps": qsdb_list(),
            "storesearch/?term=Deep+Dive": json.dumps({"items": [{"type": "app", "id": 3000009, "name": "Deep Dive"}]}),
            "storesearch": json.dumps({"items": []}),
            "appdetails": json.dumps({"3000009": {"success": True, "data": {"price_overview": {
                "currency": "EUR", "initial": 1999, "final": 1499, "discount_percent": 25}}}}),
            "api.gg.deals": json.dumps({"success": True, "data": {"3000009": {"url": "https://gg.deals/game/deep-dive/",
                                        "prices": {"currentRetail": "14.99", "currentKeyshops": "11.00", "currency": "EUR"}}}}),
        })
        self.assertTrue(sync.run())
        d = store.load_data()
        by = {t["name"]: t for t in d["titles"].values()}
        lt = by["Laser Tennis"]["live"]["meta"]
        self.assertEqual((lt["price"], lt["base"], lt["discount"], lt["low"]), (9.0, 30.0, 70, 9.0))
        self.assertEqual(by["Sky Garden"]["live"]["meta"]["low"], 3.5)
        dd = by["Deep Dive"]
        self.assertEqual((dd["meta_id"], dd["steam_appid"]), ("3333333333333333", "3000009"))
        self.assertEqual(dd["links"]["qsdb"], "https://queststoredb.com/game/deep-dive-3333333333333333/")
        self.assertEqual(dd["links"]["gg"], "https://gg.deals/game/deep-dive/")
        self.assertEqual(dd["live"]["steam"]["price"], 14.99)
        self.assertEqual(dd["live"]["gg"]["keyshops"], 11.0)
        st = sync.status()
        self.assertTrue(all(x["ok"] for x in st["sources"].values()))
        self.assertFalse(any("geheim" in line for line in st["log"]))
        self.assertTrue(any("key=geheim" in u for u in net.calls))
        hist = store.load_json("history.json", {})
        self.assertEqual(hist["meta"]["2222222222222222"][-1][1], 9.0)
        self.assertEqual(hist["gg"]["3000009"][-1][1], 11.0)
        # Ansicht: Deep Dive bei Steam reduziert, Laser Tennis bei Meta
        v = library.view(d)
        self.assertEqual([r["name"] for r in v["now"]], ["Laser Tennis", "Deep Dive"])
        r = next(r for r in v["wishlist"] if r["name"] == "Deep Dive")
        # Das günstigste PC-Angebot zählt, auch aus einem Keyshop (Entscheidung 26.10.2026)
        self.assertEqual(r["pc_best"], {"price": 11.0, "src": "gg.deals Keyshop"})
        self.assertEqual(r["gap_now"], 8.99)
        # Bestpreis aus dem Verlauf: Meta mit dem Verlauf von QuestStoreDB, Steam aus dem eigenen
        v = library.view(store.load_data(), hist=store.load_json("history.json", {}))
        lt = next(r for r in v["wishlist"] if r["name"] == "Laser Tennis")
        self.assertEqual(lt["best"]["meta"]["best"], 9.0)
        self.assertEqual(lt["best"]["meta"]["level"], "best")
        self.assertLess(lt["best"]["meta"]["since"], "2025-01-01")
        dd2 = next(r for r in v["wishlist"] if r["name"] == "Deep Dive")
        self.assertEqual(dd2["best"]["steam"]["since"], sync.now().strftime("%Y-%m-%d"))
        # Zweiter Lauf: Titelseiten sind frisch, also nur Angebotsliste und Steam
        net.calls.clear()
        sync.run()
        self.assertFalse(any("queststoredb.com/game/" in u for u in net.calls))

    def test_search_by_link_name(self):
        """Tabellenname weicht vom Store ab: Suche unter dem Namen aus dem VRDB-Link, Treffer über
        die Meta-ID. Fehlschläge einer älteren Suche (search_v) zählen nicht."""
        d = empty()
        k, _ = titles.upsert(d, "Sternfahrt (Fassung aus der Tabelle)", meta_id="4444444444444444")
        t = d["titles"][k]
        t.update(wish=True, meta_miss=titles.now_iso(), steam_miss=titles.now_iso())
        t["links"]["vrdb"] = "https://vrdb.app/game/star-ride/4444444444444444"
        o, _ = titles.upsert(d, "Star Ride")
        d["titles"][o]["owned"] = {"meta": {"src": "meta"}}
        store.save_data(d)
        self.assertEqual(titles.store_names(t), ["Sternfahrt (Fassung aus der Tabelle)", "Sternfahrt", "star ride"])
        self.assertEqual([(x["a_name"], x["b_name"]) for x in titles.suggestions(d)],
                         [("Sternfahrt (Fassung aus der Tabelle)", "Star Ride")])
        del d["titles"][o]              # die Zuordnung gekaufter Titel prüft test_assign
        store.save_data(d)
        store.save_json("sync.json", {"started": "2026-10-20T10:00:00+00:00", "search_v": 1})
        sources.fetch = net = FakeNet({
            "q=star+ride": qsdb_list(qsdb_card("Star Ride", "4444444444444444", 12.0, kind="base")),
            "all_apps": qsdb_list(),
            "/game/star-ride-4444444444444444/": qsdb_game_html("Star Ride", "4444444444444444", 12.0, 12.0),
            "storesearch": json.dumps({"items": []}),
            "/on_sale/": qsdb_list(),
        })
        sync.run()
        searches = [u for u in net.calls if "all_apps" in u]
        self.assertEqual(len(searches), 3)          # voller Name, ohne Klammer, Name aus dem Link
        t = store.load_data()["titles"][k]
        self.assertEqual(t["live"]["meta"]["price"], 12.0)
        log = "\n".join(sync.status()["log"])
        self.assertIn("Suche geändert", log)
        self.assertIn("QuestStoreDB, Suche: 3 Anfragen, 1 Titel gefunden", log)
        self.assertIn("Abgleich nach Zeitplan", log)
        self.assertIn("Preise für 1 Wunschtitel", log)
        self.assertIn("Stand: 1 Wunschtitel, mit Preis bei Meta 1", log)
        # Nächster Lauf: neue Suche gilt, der Steam-Fehlschlag wartet seine 7 Tage ab
        net.calls.clear()
        sync.run()
        self.assertFalse(any("storesearch" in u for u in net.calls))
        self.assertIn("nächste Suche ab", "\n".join(sync.status()["log"]))

    def test_price_moves_in_log(self):
        d = empty()
        k, _ = titles.upsert(d, "Laser Tennis", meta_id="2222222222222222")
        d["titles"][k].update(wish=True, live={"meta": {"price": 10.0, "base": 10.0, "low": 9.0}})
        store.save_data(d)
        got = sync.apply({k: {"meta": {"price": 8.0, "base": 10.0}}})
        self.assertEqual(got["moves"]["down"], ["Laser Tennis (Meta 10,00 € → 8,00 €)"])
        self.assertEqual(got["moves"]["low"], ["Laser Tennis 8,00 €"])
        self.assertEqual(got["coverage"]["has"]["meta"], 1)

    def test_assign(self):
        """Zuordnung für gekaufte Titel: Meta-ID über die Suche (mit Zusammenführen), Steam-IDs
        „≈“ im Store prüfen, Namen lernen, Rest unter „Zu erledigen“."""
        d = empty()
        a, _ = titles.upsert(d, "Star Ride")
        d["titles"][a]["owned"] = {"meta": {"src": "meta"}}
        b, _ = titles.upsert(d, "Sternfahrt", meta_id="4444444444444444")
        for name in ("Nebula Drift", "Moon Rover Bundle"):
            k, _ = titles.upsert(d, name)
            d["titles"][k]["owned"] = {"meta": {"src": "meta"}}
        g, _ = titles.upsert(d, "Orbit Golf", steam_appid="3000040")
        c, _ = titles.upsert(d, "Comet Chase", steam_appid="3000030")
        for k in (g, c):
            d["titles"][k]["owned"] = {"pc": {"src": "playnite", "label": "Steam"}}
        store.save_data(d)
        sources.fetch = net = FakeNet({
            "q=Star+Ride": qsdb_list(qsdb_card("Star Ride", "4444444444444444", 12.0, kind="base")),
            "all_apps": qsdb_list(),
            "appids=3000040&cc=de&l=german": steam_app_json(3000040, "Orbit Golf VR", True),
            "appids=3000030&cc=de&l=german": steam_app_json(3000030, "Comet Chase", False),
            "/on_sale/": qsdb_list(), "storesearch": json.dumps({"items": []}),
        })
        sync.run()
        d = store.load_data()
        by = {t["name"]: (k, t) for k, t in d["titles"].items()}
        k, t = by["Star Ride"]
        self.assertEqual(t["meta_id"], "4444444444444444")
        self.assertNotIn("Sternfahrt", by)
        self.assertIn("Sternfahrt", t["aliases"])
        self.assertTrue(t["links"]["qsdb"].endswith("4444444444444444/"))
        self.assertTrue(by["Orbit Golf"][1]["steam_sure"])
        self.assertIn("Orbit Golf VR", by["Orbit Golf"][1]["aliases"])
        self.assertEqual(by["Comet Chase"][1]["steam_doubt"], "laut Steam ohne VR: Comet Chase")
        todo = {x["name"]: x for x in library.view(d)["todo"]}
        self.assertEqual(set(todo), {"Comet Chase", "Nebula Drift", "Moon Rover Bundle"})
        self.assertEqual(todo["Comet Chase"]["kind"], "steam")
        self.assertTrue(todo["Moon Rover Bundle"]["why"].startswith("Bundle:"))
        log = "\n".join(sync.status()["log"])
        self.assertIn("Zuordnung, Steam-IDs „≈“: 2 ungeprüft, 2 Apps im Store gefragt; bestätigt (1): Orbit Golf", log)
        self.assertIn("gefunden (1): Star Ride, davon 1 mit einem vorhandenen Eintrag zusammengeführt", log)
        self.assertIn("3 Fälle unter „Zu erledigen“", log)
        # Zweiter Lauf: Fehlschläge warten, gefragte Apps kommen aus dem Speicher
        net.calls.clear()
        sync.run()
        self.assertFalse(any("all_apps" in u or "appdetails" in u for u in net.calls))
        # Von Hand: Steam-ID falsch, die Suche schlägt sie nicht wieder vor
        ck = by["Comet Chase"][0]
        server.edit_title({"key": ck, "steam_appid": ""})
        t = store.load_data()["titles"][ck]
        self.assertEqual(t["steam_wrong"], ["3000030"])
        self.assertNotIn("steam_doubt", t)
        gk = by["Orbit Golf"][0]
        d = store.load_data()
        d["titles"][gk]["steam_sure"] = False
        store.save_data(d)
        server.edit_title({"key": gk, "steam_sure": True})
        self.assertTrue(store.load_data()["titles"][gk]["steam_sure"])

    def test_reviews(self):
        col = json.loads(json.dumps(collection.EMPTY))
        collection.replace(col, collection.parse(COLLECTION))
        col["games"]["steam:3000101"]["rev"] = {"n": 10, "pct": 90, "at": titles.now_iso()}   # frisch: kein Abruf
        store.save_json(collection.FILE, col)
        ans = json.dumps({"success": 1, "query_summary": {"num_reviews": 0, "review_score": 8, "review_score_desc": "Very Positive",
                                                          "total_positive": 276, "total_negative": 24, "total_reviews": 300}})
        net = FakeNet({"appreviews/3000103": ans})
        sources.fetch = net
        sync.run(only={"reviews"})
        self.assertEqual(len(net.calls), 1)
        self.assertIn("num_per_page=0", net.calls[0])
        g = store.load_json(collection.FILE, {})["games"]
        self.assertEqual((g["steam:3000103"]["rev"]["n"], g["steam:3000103"]["rev"]["pct"]), (300, 92))
        self.assertEqual(g["steam:3000101"]["rev"]["n"], 10)
        rows = {r["key"]: r for r in collection.view({"games": g})["games"]}
        q = rows["steam:3000103"]
        self.assertEqual((q["score"], q["score_src"], q["reviews"], q["guess"], q["gem"], q["gem_guess"]),
                         (92, "Steam", 300, False, 0.37, False))
        self.assertEqual((rows["steam:3000101"]["score"], rows["steam:3000101"]["reviews"]), (None, 10))   # unter 50 Rezensionen
        self.assertIn("reviews", store.load_json("sync.json", {})["sources"])
        self.assertIsNone(prices.steam_reviews('{"success": 2}'))
        self.assertEqual(prices.steam_reviews('{"success": 1, "query_summary": {"total_reviews": 0}}')["pct"], None)
        # 0.7.5: Store-Schnittstelle (IStoreBrowseService/GetItems)
        sb = {"response": {"store_items": [{"appid": 3000101, "success": 1, "reviews": {"summary_filtered": {
            "review_count": 1234, "percent_positive": 91, "review_score": 8, "review_score_label": "Very Positive"}}}]}}
        self.assertEqual(prices.steam_reviews(json.dumps(sb)), {"n": 1234, "pct": 91, "desc": "Very Positive"})
        self.assertEqual(prices.steam_reviews('{"response": {"store_items": [{"appid": 1, "success": 1}]}}'), {"n": 0, "pct": None, "desc": ""})
        self.assertIsNone(prices.steam_reviews('{"response": {"store_items": [{"appid": 1, "success": 2}]}}'))
        self.assertIn("IStoreBrowseService", sync.review_url("3000101", 3))

    def test_retro_source(self):
        """Fassungslisten je System der Retro-Liste, danach wöchentlich; „de“ je Spiel."""
        col = {"games": {}}
        retro.apply(col, retro.parse("GBA/Moon Rover (USA).gba\nGBA/Star Hop (USA).gba\nVB/Tiny Tennis (World).vb\n")[0], dry=False)
        store.save_json(collection.FILE, col)
        net = FakeNet({"no-intro/Nintendo%20-%20Game%20Boy%20Advance.dat": RETRO_DAT,
                       "Game%20Boy%20Advance%20%28No-Intro%29.json": RETRO_RETOOL})
        sources.fetch = net
        sync.run(only={"retro"})
        self.assertEqual(len(net.calls), 3)                     # GBA: Liste und Retool; VB: Liste fehlt (404), Retool nicht gefragt
        g = store.load_json(collection.FILE, {})["games"]
        self.assertEqual((g["retro:gba:moon rover"]["de"]["st"], g["retro:gba:star hop"]["de"]["via"]), ("missing", "retool"))
        self.assertTrue(store.load_json(retro.CACHE, {})["GBA"]["retool"])
        res = store.load_json("sync.json", {})["sources"]["retro"]
        self.assertEqual((res["read"], res["missing"]), (1, 2))
        net.calls.clear()
        sync.run(only={"retro"})
        self.assertEqual([c for c in net.calls if "Advance" in c], [])   # GBA frisch: nicht neu gelesen
        self.assertEqual(store.load_json(collection.FILE, {})["games"]["retro:gba:moon rover"]["de"]["st"], "missing")

    def test_details(self):
        """Steam-Details gleichen Playnite ab: was beide sagen, ist bestätigt, der Rest bleibt mit ≈."""
        col = json.loads(json.dumps(collection.EMPTY))
        collection.replace(col, collection.parse(COLLECTION))
        store.save_json(collection.FILE, col)
        app = {"3000101": {"success": True, "data": {
            "type": "game", "name": "Harbor Heist", "release_date": {"date": "12 Mar, 2019"},
            "genres": [{"id": "1", "description": "Action"}, {"id": "23", "description": "Indie"}],
            "categories": [{"id": 1}, {"id": 9}, {"id": 54}], "recommendations": {"total": 1234},
            "metacritic": {"score": 84}, "short_description": "Ein <b>Raubzug</b> im Hafen.", "developers": ["Kite Works"],
            "publishers": ["Paper Moon"], "supported_languages": "Englisch<strong>*</strong>, Deutsch, Französisch"}}}
        net = FakeNet({"appids=3000101&l=german": json.dumps(app), "appids=3000103&l=german": '{"3000103": {"success": false}}'})
        sources.fetch = net
        sync.run(only={"details"})
        self.assertEqual(len(net.calls), 2)
        g = store.load_json(collection.FILE, {})["games"]
        self.assertEqual((g["steam:3000101"]["steam"]["mp"], g["steam:3000101"]["steam"]["vr"]), (["multi", "coop"], True))
        self.assertFalse(g["steam:3000103"]["steam"]["ok"])
        rows = {r["key"]: r for r in collection.view({"games": g})["games"]}
        h = rows["steam:3000101"]
        self.assertEqual((h["src"], h["vr"], h["year"], h["year_ok"]), ("steam", True, "2019", True))
        self.assertEqual((h["mp"], h["mpc"]), (["multi", "online", "coop"], ["multi", "coop"]))   # Online nur laut Playnite
        self.assertEqual((h["genres"], h["gc"]), (["Shooter", "Action"], []))                      # Action nur laut Steam
        # Einzelheiten (0.7.1): Metacritic, Beschreibung ohne HTML, Sprachen, Steam vor Playnite bei den Firmen
        self.assertEqual((h["mc"], h["desc"], h["slangs"], h["sde"], h["pub"], h["sdate"]),
                         (84, "Ein Raubzug im Hafen.", 3, True, "Paper Moon", "12 Mar, 2019"))
        q = rows["steam:3000103"]                               # Steam kennt die App nicht: bleibt vermutet
        self.assertEqual((q["src"], q["guess"]), ("playnite", True))
        self.assertEqual(rows["epic:abc123def"]["src"], "playnite")
        # ein neuer Import behält die Details, ein zweiter Lauf fragt nicht erneut
        col = store.load_json(collection.FILE, {})
        collection.replace(col, collection.parse(COLLECTION))
        self.assertTrue(col["games"]["steam:3000101"]["steam"]["ok"])
        store.save_json(collection.FILE, col)
        sync.run(only={"details"})
        self.assertEqual(len(net.calls), 2)
        # Einträge von vor 0.7.1 (ohne v) kommen erneut dran, auch wenn sie frisch sind
        col = store.load_json(collection.FILE, {})
        col["games"]["steam:3000101"]["steam"].pop("v")
        store.save_json(collection.FILE, col)
        sync.run(only={"details"})
        self.assertEqual(len(net.calls), 3)
        self.assertIsNone(prices.steam_details("kein json", "1"))

    def test_rating(self):
        """Steam-Wertung für Titel des Tools; was Entdecken schon hat, wird übernommen."""
        d = empty()
        a, _ = titles.upsert(d, "Comet Chase")
        b, _ = titles.upsert(d, "Harbor Heist")
        c, _ = titles.upsert(d, "Ohne Steam")
        d["titles"][a].update(wish=True, steam_appid="3000030", live={"meta": {"rating": 4.46, "ratings": 120, "price": 9.99}})
        d["titles"][b].update(wish=True, steam_appid="3000101")
        store.save_data(d)
        col = json.loads(json.dumps(collection.EMPTY))
        collection.replace(col, collection.parse(COLLECTION))
        col["games"]["steam:3000101"]["rev"] = {"n": 400, "pct": 91, "at": titles.now_iso()}
        store.save_json(collection.FILE, col)
        ans = json.dumps({"success": 1, "query_summary": {"total_positive": 30, "total_negative": 10, "total_reviews": 40}})
        sources.fetch = net = FakeNet({"appreviews/3000030": ans})
        sync.run(only={"rating"})
        self.assertEqual(len(net.calls), 1)                     # 3000101 kam aus der Sammlung
        t = store.load_data()["titles"]
        self.assertEqual((t[a]["rev"]["n"], t[a]["rev"]["app"], t[b]["rev"]["pct"]), (40, "3000030", 91))
        ra, rb, rc = (library.rating(t[k]) for k in (a, b, c))
        self.assertEqual(ra, {"meta": {"stars": 4.5, "n": 120}, "steam": {"pct": None, "n": 40}, "score": 90})
        self.assertEqual((rb["steam"], rb["score"]), ({"pct": 91, "n": 400}, 91))
        self.assertEqual(rc, {"meta": None, "steam": None, "score": None})
        sync.run(only={"rating"})                                # frisch: kein neuer Abruf
        self.assertEqual(len(net.calls), 1)
        d = store.load_data()
        d["titles"][a]["steam_appid"] = "3000031"                # andere Steam-ID: neu fragen
        store.save_data(d)
        sync.run(only={"rating"})
        self.assertEqual(len(net.calls), 2)

    def test_eshop_collection(self):
        """Switch-Sammlung aus dem eShopKompass (0.7.3): nur mit ESHOP_URL, genau diese eine Adresse im
        eigenen Netz, ersetzt nur die eigenen Einträge, Playnite-Switch-Spiele gleichen Namens fallen weg."""
        old = os.environ.pop("ESHOP_URL", None)
        try:
            sources.fetch = net = FakeNet({})
            sync.run(only={"eshop"})
            self.assertEqual(net.calls, [])                       # ohne Umgebungsvariable keine Anfrage
            os.environ["ESHOP_URL"] = "http://127.0.0.1:8787/"
            self.assertEqual(sources.eshop_url(), "http://127.0.0.1:8787/api/sammlung")
            self.assertEqual(sources.blocked_target("http://127.0.0.1:8787/api/sammlung"), "")
            self.assertEqual(sources.blocked_target("http://127.0.0.1:8787/api/export"), "Adresse nicht öffentlich")
            self.assertEqual(sources.blocked_target("http://127.0.0.1:8788/api/sammlung"), "Adresse nicht öffentlich")
            col = json.loads(json.dumps(collection.EMPTY))
            collection.replace(col, {"name:moon racer": {"name": "Moon Racer", "system": "Switch", "mp": [], "genres": []},
                                     "steam:3000101": {"name": "Harbor Heist", "system": "PC", "store": "Steam", "id": "3000101",
                                                       "mp": [], "genres": []}})
            col["games"]["eshop:alt"] = {"name": "Alt", "system": "Switch", "src": "eshop"}
            store.save_json(collection.FILE, col)
            ans = {"app": "eshop-kompass", "version": "1.7.16", "games": [
                {"slug": "moon-racer", "title": "Moon Racer", "system": "Switch", "genres": ["Rennspiel"], "max": 4,
                 "offline": [1, 4], "online": [1, 8], "coop": False, "mc": 81, "hours": 6.5, "released": "2021-05-04",
                 "desc": "Rennen auf dem Mond.", "langs": ["english", "german"], "mine": {"s": "done", "fav": True},
                 "kv": {"players": {"offline": {"v": [1, 4], "ok": False, "alt": [1, 2]}}, "mcu": 7.9, "hltb": {"main": 6.5},
                        "url": "https://example.org/", "pack": {"title": "Moon Bundle", "filled": ["mc"]}}},
                {"slug": "pixel-garden-nintendo-switch-2-edition", "title": "Pixel Garden", "system": "Switch 2", "oc": 77,
                 "desc_lang": "en", "desc": "A garden."},
                {"title": "ohne Slug"}, "kaputt"]}
            sources.fetch = net = FakeNet({"/api/sammlung": json.dumps(ans)})
            sync.run(only={"eshop"})
            self.assertEqual(net.calls, ["http://127.0.0.1:8787/api/sammlung"])
            col = store.load_json(collection.FILE, collection.EMPTY)
            self.assertNotIn("eshop:alt", col["games"])
            self.assertIn("steam:3000101", col["games"])
            v = collection.view(col)
            rows = {r["key"]: r for r in v["games"]}
            self.assertNotIn("name:moon racer", rows)            # dasselbe Spiel aus Playnite
            m = rows["eshop:moon-racer"]
            self.assertEqual((m["score"], m["score_src"], m["hours"], m["mine"], m["players"]), (81, "Metacritic", 6.5, {"s": "done", "fav": True}, 4))
            self.assertEqual(m["mp"], ["multi", "couch", "online"])
            p = rows["eshop:pixel-garden-nintendo-switch-2-edition"]
            self.assertEqual((p["system"], p["score"], p["score_src"], p["desc_lang"]), ("Switch 2", 77, "OpenCritic", "en"))
            # 0.7.5: Switch und Switch 2 in einem Reiter, sw1 merkt das Switch-1-Spiel
            self.assertEqual((dict(v["systems"]).get("Switch 2"), "Switch" in dict(v["systems"])), (2, False))
            self.assertEqual((m["system"], m.get("sw1"), p.get("sw1")), ("Switch 2", True, None))
            # 0.7.5: die Zeile der Ansicht „Spiele“ (kv), nur bekannte Felder
            self.assertEqual(m["kv"]["players"]["offline"]["alt"], [1, 2])
            self.assertEqual((m["kv"]["mcu"], m["kv"]["pack"]["title"], "url" in m["kv"], p["kv"]), (7.9, "Moon Bundle", False, {}))
            self.assertIn("eShopKompass: 2 Spiele (Switch 2: 1)", "\n".join(sync.status()["log"]))
            # Eine Antwort, die nicht vom eShopKompass kommt, ändert nichts
            sources.fetch = FakeNet({"/api/sammlung": json.dumps({"games": []})})
            sync.run(only={"eshop"})
            self.assertEqual(len([k for k in store.load_json(collection.FILE, collection.EMPTY)["games"] if k.startswith("eshop:")]), 2)
            # Ein neuer Playnite-Export lässt die Switch-Spiele aus dem eShopKompass stehen
            col = store.load_json(collection.FILE, collection.EMPTY)
            collection.replace(col, {"name:other": {"name": "Other", "system": "Switch", "mp": [], "genres": []}})
            self.assertIn("eshop:moon-racer", col["games"])
        finally:
            os.environ.pop("ESHOP_URL", None)
            if old is not None:
                os.environ["ESHOP_URL"] = old

    def test_vrdb_and_players(self):
        """VRDB: Crossbuy, Version (mit Tag des Wechsels), Meta-Wertung als Anteil 4 und 5 Sterne.
        Steam: Spieler jetzt mit Spitze, letztes Update aus den Meldungen."""
        def vrdb_page(version, cb="Yes"):
            bar = lambda n, v: (f'<div aria-label="{round(v)}% of reviews are {n} stars" role="progressbar" value="{v}" '
                                f'aria-valuemin="0" aria-valuemax="100" aria-valuenow="{v}"></div>')
            return ("<html><body><script>var x = 1;</script><h2>Ratings and reviews</h2><span>4.3</span><span>Very Positive</span>"
                    f"<span>1,234 ratings</span>{bar(5, 60.4)}{bar(4, 20.2)}{bar(3, 9.1)}{bar(2, 4.3)}{bar(1, 6.0)}"
                    "<dl><dt>Game modes:</dt><dd>Multiplayer, Single User</dd><dt>Is Cross-Buy:</dt>"
                    f"<dd>{cb}</dd><dt>Version:</dt><dd>{version}</dd></dl></body></html>")
        d = empty()
        a, _ = titles.upsert(d, "Comet Chase", meta_id="1234567890123456", steam_appid="3000030")
        b, _ = titles.upsert(d, "Harbor Heist", meta_id="1234567890123457")
        c, _ = titles.upsert(d, "Nicht gewünscht", meta_id="1234567890123458")
        d["titles"][a].update(wish=True, links={"vrdb": "https://vrdb.app/game/comet-chase/1234567890123456"})
        d["titles"][b].update(owned={"meta": {"src": "meta"}})
        store.save_data(d)
        news = json.dumps({"appnews": {"appid": 3000030, "newsitems": [
            {"title": "Sommerfest im Spiel", "date": 1792000000, "feedname": "steam_community_announcements"},
            {"title": "Patch 1.2 ist da", "date": 1791000000, "feedname": "steam_community_announcements"},
            {"title": "Update 2.0", "date": 1793000000, "feedname": "pc_gamer"}]}})
        sources.fetch = net = FakeNet({"comet-chase/1234567890123456": vrdb_page("1.4.0_123"),
                                       "GetNumberOfCurrentPlayers": '{"response": {"player_count": 42, "result": 1}}',
                                       "GetNewsForApp": news})
        sync.run(only={"vrdb", "players"})
        t = store.load_data()["titles"]
        self.assertEqual((t[a]["vrdb"]["crossbuy"], t[a]["vrdb"]["pos"], t[a]["vrdb"]["n"], t[a]["meta_ver"]), (True, 81, 1234, {"v": "1.4.0_123", "since": ""}))
        self.assertTrue(t[b]["vrdb"]["miss"])                    # Seite fehlt: erst in 14 Tagen wieder
        self.assertNotIn("vrdb", t[c])                           # weder Wunsch noch Besitz
        self.assertTrue(any("vrdb.app/game/harbor-heist/1234567890123457" in u for u in net.calls))
        self.assertEqual((t[a]["play"]["now"], t[a]["play"]["peak"], t[a]["news"]["title"]), (42, 42, "Patch 1.2 ist da"))
        r = library.row(a, t[a], data={"titles": t})
        self.assertEqual((r["crossbuy"], r["crossbuy_src"], r["rating"]["meta"]["pos"], r["rating"]["score"]), (True, "VRDB", 81, 81))
        self.assertEqual((r["measured"]["players"]["now"], r["measured"]["update"]["date"], r["measured"]["meta_ver"]["v"]),
                         (42, "2026-10-03", "1.4.0_123"))
        # neue Version: Tag des Wechsels; Spitze bleibt, auch wenn jetzt weniger spielen
        d = store.load_data()
        d["titles"][a]["vrdb"]["at"] = d["titles"][a]["play"]["at"] = "2000-01-01T00:00:00+00:00"
        store.save_data(d)
        net.answers.update({"comet-chase/1234567890123456": vrdb_page("1.5.0_130", "No"),
                            "GetNumberOfCurrentPlayers": '{"response": {"player_count": 7, "result": 1}}'})
        sync.run(only={"vrdb", "players"})
        t = store.load_data()["titles"]
        self.assertEqual(t[a]["meta_ver"], {"v": "1.5.0_130", "since": sync.now().strftime("%Y-%m-%d")})
        self.assertEqual((t[a]["play"]["now"], t[a]["play"]["peak"], t[a]["vrdb"]["crossbuy"]), (7, 42, False))
        # 404: Steam hat für die App keine Spielerzahl; zählt still, ohne Fehler, gilt als gefragt
        d = store.load_data()
        d["titles"][a]["play"]["at"] = "2000-01-01T00:00:00+00:00"
        store.save_data(d)
        net.answers["GetNumberOfCurrentPlayers"] = 404
        sync.run(only={"players"})
        st, t = sync.status(), store.load_data()["titles"]
        self.assertIsNone(t[a]["play"]["now"])
        self.assertEqual((t[a]["play"]["peak"], st["sources"]["players"]["errors"]), (42, 0))
        log = "\n".join(st["log"])
        self.assertIn("1 Apps ohne Zahl bei Steam", log)
        self.assertNotIn("HTTP 404", log)
        self.assertIn("Kurz: kein Wunschtitel im Angebot", st["log"][1])
        self.assertIsNone(prices.steam_players('{"response": {"result": 42}}'))
        self.assertEqual(prices.steam_news('{"appnews": {"newsitems": []}}'), {})

    def test_ggwish_manual(self):
        """gg.deals sperrt den Server: Wunschliste ab dann per Lesezeichen, unbekannte Namen
        sucht der Abgleich nach; ein neu gespeicherter Link versucht es wieder."""
        self.seed()
        sync.save_settings({"gg_wish": "https://gg.deals/wishlist/share/AbCdEf123/"})
        sources.fetch = net = FakeNet({"wishlist/share": 403, "/on_sale/": qsdb_list(), "all_apps": qsdb_list(),
                                       "storesearch/?term=Comet+Chase": json.dumps({"items": [{"type": "app", "id": 3000030, "name": "Comet Chase"}]}),
                                       "appids=3000030&cc=de&l=german": steam_app_json(3000030, "Comet Chase", True),
                                       "storesearch": json.dumps({"items": []}), "appdetails": "{}"})
        sync.run()
        st = sync.status()
        self.assertTrue(st["sources"]["ggwish"]["manual"])
        self.assertNotIn("ggwish", st.get("rest") or {})
        self.assertIn("Lesezeichen", "\n".join(st["log"]))
        d = store.load_data()
        d["gg_unknown"] = ["Comet Chase"]
        store.save_data(d)
        net.calls.clear()
        sync.run()
        self.assertFalse(any("wishlist/share" in u for u in net.calls))
        d = store.load_data()
        cc = next(t for t in d["titles"].values() if t["name"] == "Comet Chase")
        self.assertEqual((cc["steam_appid"], set(cc["wish_src"])), ("3000030", {"gg"}))
        self.assertEqual(d["gg_unknown"], [])
        # nach einer Woche versucht es der Server wieder selbst
        st = store.load_json("sync.json", {})
        st["manual"]["ggwish"] = "2026-01-01T00:00:00+00:00"
        store.save_json("sync.json", st)
        net.calls.clear()
        sync.run()
        self.assertTrue(any("wishlist/share" in u for u in net.calls))
        self.assertIn("neuer Versuch", "\n".join(sync.status()["log"]))
        self.assertGreater(store.load_json("sync.json", {})["manual"]["ggwish"], "2026-01-02")
        sync.save_settings({"gg_wish": "https://gg.deals/wishlist/share/Neu1/"})
        self.assertNotIn("ggwish", store.load_json("sync.json", {}).get("manual") or {})

    def test_accounts_in_run(self):
        """Steam-Konto, gg.deals-Wunschliste und Sharenite vor den Preisen."""
        self.seed()
        sync.save_settings({"steam_id": "76561190000000001", "steam_key": "cd" * 16,
                            "gg_wish": "https://gg.deals/wishlist/share/AbCdEf123/",
                            "sharenite": "https://www.sharenite.link/profiles/beispiel/games"})
        sources.fetch = net = FakeNet({
            "GetOwnedGames": steam_owned_json(("3000005", "Sky Garden"), ("3000020", "Star Ride"), ("3000021", "Flat Racer")),
            "GetWishlist": steam_wish_json("3000030"),
            "appids=3000020&cc=de&l=german": steam_app_json(3000020, "Star Ride", True),
            "appids=3000021&cc=de&l=german": steam_app_json(3000021, "Flat Racer", False),
            "appids=3000030&cc=de&l=german": steam_app_json(3000030, "Comet Chase", True),
            "appids=3000040&cc=de&l=german": steam_app_json(3000040, "Orbit Golf", True),
            "wishlist/share/AbCdEf123/?page=2": gg_wish_html("Laser Tennis"),
            "wishlist/share/AbCdEf123/": gg_wish_html("Laser Tennis", "Orbit Golf", "Flat Racer", pages=2),
            "storesearch/?term=Orbit+Golf": json.dumps({"items": [{"type": "app", "id": 3000040, "name": "Orbit Golf"}]}),
            "tag_ids%5B%5D=t-vr&sort=name_asc&page=1": sharenite_html([("Nebula Drift", "GOG", ["VR"])]),
            "sharenite.link/profiles/beispiel/games?sort=name_asc": sharenite_html([("Flat Racer", "Steam", [])], total=300,
                                                                                   vr_tags=[("t-vr", "VR")]),
            "/on_sale/": qsdb_list(), "all_apps": qsdb_list(), "storesearch": json.dumps({"items": []}),
            "appdetails": "{}",
        })
        sync.run(by_hand=True)
        d = store.load_data()
        by = {t["name"]: t for t in d["titles"].values()}
        self.assertEqual(by["Sky Garden"]["owned"]["pc"]["label"], "Steam")
        self.assertTrue(by["Star Ride"]["steam_sure"])
        self.assertNotIn("Flat Racer", by)
        self.assertEqual(by["Comet Chase"]["wish_src"].keys(), {"steam"})
        self.assertEqual(set(by["Orbit Golf"]["wish_src"]), {"gg"})
        self.assertIn("gg", by["Laser Tennis"]["wish_src"])
        self.assertEqual(by["Nebula Drift"]["owned"]["pc"], dict(by["Nebula Drift"]["owned"]["pc"], src="sharenite", label="GOG"))
        log = "\n".join(sync.status()["log"])
        self.assertIn("Steam-Konto, Besitz: 3 Spiele, davon 2 VR-Titel", log)
        self.assertIn("gg.deals-Wunschliste: 3 Spiele auf 2 Seiten", log)
        self.assertIn("Sharenite: 300 Spiele im Profil, 1 mit VR-Schlagwort", log)
        self.assertFalse(any("cdcdcdcd" in line or "AbCdEf123" in line for line in sync.status()["log"]))
        self.assertTrue(all(sync.status()["sources"][k]["ok"] for k in ("steamacc", "ggwish", "sharenite")))
        # Zweiter Lauf nach Zeitplan: Sharenite ruht, Comet Chase fällt von der Steam-Wunschliste
        net.answers["GetWishlist"] = steam_wish_json("3000005")
        net.calls.clear()
        sync.run()
        self.assertFalse(any("sharenite" in u for u in net.calls))
        by = {t["name"]: t for t in store.load_data()["titles"].values()}
        self.assertFalse(by["Comet Chase"]["wish"])
        self.assertIn("von deiner (1): Comet Chase", "\n".join(sync.status()["log"]))
        # Steam-Wunschliste abgeschaltet: nicht mehr abgefragt, Steam zählt nicht mehr als Quelle;
        # ein Wunsch nur von dort bleibt, steht aber ohne Quelle zum Nachtragen bei gg.deals da
        def by_name(n):
            return next(t for t in store.load_data()["titles"].values() if t["name"] == n)
        net.answers["GetWishlist"] = steam_wish_json("3000030")
        sync.run(by_hand=True)
        self.assertEqual(set(by_name("Comet Chase")["wish_src"]), {"steam"})
        sync.save_settings({"steam_wish": False})
        t = by_name("Comet Chase")
        self.assertTrue(t["wish"])
        self.assertNotIn("wish_src", t)
        settings = sync.load_settings()
        got = {x["name"]: x for x in lists.check(store.load_data(), settings)}
        self.assertIn("nur von der Steam-Wunschliste", got["Comet Chase"]["why"])
        self.assertEqual([l["label"] for l in got["Comet Chase"]["links"]], ["gg.deals"])
        net.calls.clear()
        sync.run(by_hand=True)
        self.assertFalse(any("GetWishlist" in u for u in net.calls))
        self.assertTrue(any("GetOwnedGames" in u for u in net.calls))
        self.assertIn("Wunschliste nicht gelesen", "\n".join(sync.status()["log"]))

    def test_blocked_source_stops(self):
        self.seed()
        sources.fetch = net = FakeNet({"queststoredb.com": 429, "storesearch": json.dumps({"items": []}),
                                       "appdetails": "{}"})
        sync.run()
        st = sync.status()["sources"]
        self.assertFalse(st["qsdb"]["ok"])
        self.assertTrue(st["steam"]["ok"])
        self.assertEqual(sum("queststoredb.com" in u for u in net.calls), 1)
        self.assertTrue(st["qsdb"]["until"])
        # Suche ohne Treffer: eine Woche Ruhe; QuestStoreDB ruht nach der Sperre auch im nächsten Lauf
        net.calls.clear()
        sync.run()
        self.assertFalse(any("storesearch" in u for u in net.calls))
        self.assertFalse(any("queststoredb.com" in u for u in net.calls))
        st = sync.status()
        self.assertEqual(st["sources"]["qsdb"]["msg"], "ruht")
        self.assertTrue(any("ruht nach einer Sperre" in line for line in st["log"]))
        self.assertFalse(st["ok"])

    def test_challenge_page_counts_as_block(self):
        self.seed()
        page = "<html><title>Just a moment...</title><script>window._cf_chl_opt={}</script></html>"
        sources.fetch = net = FakeNet({"queststoredb.com": page, "storesearch": json.dumps({"items": []}),
                                       "appdetails": "{}"})
        sync.run()
        st = sync.status()["sources"]["qsdb"]
        self.assertEqual((st["ok"], st["msg"], st["blocked"]), (False, "Prüfseite von Cloudflare", True))
        self.assertEqual(sum("queststoredb.com" in u for u in net.calls), 1)
        self.assertEqual(sources.challenge("<script src='/cdn-cgi/challenge-platform/x.js'></script>"), "")

    def test_network_error_gets_second_try(self):
        calls = []

        def flaky(url, timeout=25, ua=None, headers=None):
            calls.append(url)
            if len(calls) == 1:
                raise sources.FetchError(url, 0, "Zeitüberschreitung")
            return "ok"
        sources.fetch = flaky
        lines = []
        src = sync._Source("Test", lines.append)
        self.assertEqual(src.get("https://example.com/a"), "ok")
        self.assertEqual(len(calls), 2)
        self.assertIn("zweiter Versuch", lines[0])

    def test_due_after_boot_and_failure(self):
        from datetime import datetime, timedelta, timezone
        at = datetime(2026, 10, 21, 12, tzinfo=timezone.utc)
        self.assertEqual(sync.BOOT_WAIT_S, 300)                              # Ruhe nach dem Start: 5 min
        self.assertTrue(sync.due(at=at))                                     # noch nie gelaufen
        store.save_json("sync.json", {"started": (at - timedelta(hours=2)).isoformat(), "ok": True})
        self.assertFalse(sync.due(at=at))                                    # Zeitplan: erst nach 6 h
        self.assertTrue(sync.due(at=at, boot=True))                          # nach dem Start gleich
        store.save_json("sync.json", {"started": (at - timedelta(minutes=10)).isoformat(), "ok": False})
        self.assertFalse(sync.due(at=at, boot=True))                         # gerade fehlgeschlagen
        store.save_json("sync.json", {"started": (at - timedelta(minutes=10)).isoformat(), "ok": True})
        self.assertFalse(sync.due(at=at, boot=True))                         # gerade erst gelaufen

    def test_self_check(self):
        w = sync.self_check({"qsdb": {"ok": True, "sale": 0, "pages": 3, "parsed": 0},
                             "steam": {"ok": True, "ids": 4, "found": 0}},
                            {"qsdb": {"sale": 90}}, {"jumps": 2})
        text = " | ".join(w)
        self.assertIn("keine Angebote erkannt (zuletzt 90)", text)
        self.assertIn("auf 3 Titelseiten kein Preis lesbar", text)
        self.assertIn("Steam: kein Preis für 4 App-IDs", text)
        self.assertIn("2 Normalpreise", text)
        self.assertEqual(sync.self_check({"qsdb": {"ok": True, "sale": 12, "pages": 2, "parsed": 2}}, {}, {}), [])

    def test_igdb_sync(self):
        """IGDB im Abgleich (0.8.0): Steam-Spiele gebündelt über die Steam-ID, andere über den Namen, ein
        falscher Treffer zählt nicht, Spielzeit dazu; die Zeile bekommt Werte nach Rangfolge."""
        from app import igdb
        store.save_json(collection.FILE, {"games": {
            "steam:3000101": {"name": "Harbor Heist", "store": "Steam", "id": "3000101", "mp": [], "players": 0, "genres": ["Action"]},
            "steam:3000102": {"name": "Unknown Moth", "store": "Steam", "id": "3000102", "mp": [], "players": 0, "genres": []},
            "name:ps1:moon wars masters of randern": {"name": "Moon Wars: Masters of Rändern", "system": "PS1", "mp": [], "players": 0, "genres": []},
            "name:ps2:star hop": {"name": "Star Hop", "system": "PS2", "mp": [], "players": 0, "genres": []},
            "eshop:orbit-golf": {"name": "Orbit Golf", "system": "Switch 2", "src": "eshop", "id": "orbit-golf"}}, "n": 5})
        harbor = {"id": 5, "name": "Harbor Heist", "genres": [{"name": "Shooter"}, {"name": "Adventure"}], "game_modes": [{"name": "Multiplayer"}],
                  "multiplayer_modes": [{"onlinemax": 4, "onlinecoop": True}], "aggregated_rating": 81.4, "aggregated_rating_count": 5,
                  "summary": "A heist.", "first_release_date": 1552348800,
                  "involved_companies": [{"developer": True, "company": {"name": "Kite Works"}}]}
        moon = {"id": 7, "name": "Moon Wars: Masters of Rändern", "genres": [{"name": "Fighting"}], "multiplayer_modes": [{"offlinemax": 2}],
                "total_rating": 55.2, "total_rating_count": 14}
        calls = []

        def fake(url, timeout=25, ua=None, headers=None, data=None):
            body = (data or b"").decode()
            calls.append((url, body, dict(headers or {})))
            if "twitch" in url:
                return json.dumps({"access_token": "tok"})
            if url.endswith("external_games"):
                return json.dumps([{"game": 5, "uid": "3000101"}])
            if url.endswith("game_time_to_beats"):
                return json.dumps([{"game_id": 5, "normally": 25200, "completely": 36000, "count": 12}])
            if "where id = (5)" in body:
                return json.dumps([harbor])
            if "Masters of R" in body and "name ~" in body:
                return json.dumps([moon])
            if "Star Hop" in body:
                return json.dumps([{"id": 9, "name": "Star Hop Galaxy Racing Deluxe"}])
            return "[]"
        sources.fetch = fake
        settings = dict(sync.SETTINGS, igdb_id="a" * 30, igdb_secret="b" * 30)
        logs = []
        r = sync._igdb(settings, logs.append)
        self.assertTrue(r["ok"])
        self.assertEqual(sum(1 for u, b, h in calls if u.endswith("external_games")), 1)
        self.assertIn('"3000101","3000102"', next(b for u, b, h in calls if u.endswith("external_games")))
        self.assertFalse(any("Orbit Golf" in b for u, b, h in calls))
        self.assertEqual(next(h for u, b, h in calls if "api.igdb" in u)["Authorization"], "Bearer tok")
        col = store.load_json(collection.FILE, collection.EMPTY)["games"]
        self.assertEqual(col["steam:3000101"]["igdb"]["hours"]["h"], 7.0)
        self.assertTrue(col["steam:3000102"]["igdb"]["none"])
        self.assertEqual(col["name:ps1:moon wars masters of randern"]["igdb"]["id"], 7)
        self.assertTrue(col["name:ps2:star hop"]["igdb"]["none"])       # falsches Spiel zählt nicht
        self.assertIn("4 Spiele gelesen, 2 gefunden (1 über die Steam-ID), 1 mit Spielzeit", "\n".join(logs))
        self.assertNotIn("a" * 30, "\n".join(logs))
        # zweiter Lauf: nichts zu tun
        calls.clear()
        sync._igdb(settings, logs.append)
        self.assertEqual(calls, [])
        rows = {x["key"]: x for x in collection.view(store.load_json(collection.FILE, collection.EMPTY))["games"]}
        h, m = rows["steam:3000101"], rows["name:ps1:moon wars masters of randern"]
        self.assertEqual((h["score"], h["score_src"], h["score_alt"]), (81, "IGDB Kritik", True))
        self.assertEqual((h["hours"], h["players"], h["pl_src"]), (7.0, 4, "IGDB"))
        self.assertEqual(h["genres"], ["Action", "Shooter", "Abenteuer"])
        self.assertEqual(h["gc"], [])
        self.assertIn("online", h["mp"])
        self.assertEqual((h["desc"], h["desc_src"], h["year"], h["dev"]), ("A heist.", "IGDB", "2019", "Kite Works"))
        self.assertEqual((m["score"], m["score_src"], m.get("score_alt")), (55, "IGDB gesamt", True))
        self.assertEqual((m["genres"], m["gc"], m["players"]), (["Kampfspiel"], ["Kampfspiel"], 2))
        self.assertIn("couch", m["mpc"])
        self.assertEqual(rows["name:ps2:star hop"].get("ig"), None)
        # Ohne Schlüssel bei Twitch: Problem, keine IGDB-Anfrage
        store.save_json(collection.FILE, {"games": {"name:ps2:x": {"name": "X Game", "system": "PS2"}}})
        calls.clear()
        sources.fetch = lambda url, timeout=25, ua=None, headers=None, data=None: (calls.append(url), "{}")[1]
        r = sync._igdb(settings, logs.append)
        self.assertFalse(r["ok"])
        self.assertEqual(len(calls), 1)
        self.assertEqual(igdb.pick([{"name": "Portal 2"}], "Portal"), None)

    def test_vr_per_mod(self):
        """VR per Mod (0.8.1): PCGamingWiki über die Steam-ID, Nexus-Spieleliste einmal, dann Mods je Spiel."""
        from app import mods
        store.save_json(collection.FILE, {"games": {
            "steam:3000101": {"name": "Harbor Heist", "store": "Steam", "id": "3000101", "rev": {"n": 900}},
            "steam:3000102": {"name": "Rally Moth", "store": "Steam", "id": "3000102", "rev": {"n": 50}},
            "steam:3000103": {"name": "Comet Chase VR", "store": "Steam", "id": "3000103", "steam": {"ok": True, "vr": True}},
            "gog:77": {"name": "Paper Lantern Legacy", "store": "GOG", "id": "77"},
            "name:ps2:star hop": {"name": "Star Hop", "system": "PS2"}}, "n": 5})
        wiki = {"3000101": ("Harbor_Heist", "{{VR support\n|htc vive = hackable\n|oculus rift = hackable\n|vorpx = true\n|steamvr = false\n}}\n"),
                "3000102": ("Rally_Moth", "{{VR support\n|htc vive = false\n}}\n")}
        calls = []

        def fake(url, timeout=25, ua=None, headers=None, data=None):
            calls.append((url, (data or b"").decode(), dict(headers or {})))
            if "appid.php" in url:
                gid = url.split("appid=")[1]
                return f'<script>RLCONF={{"wgPageName":"{wiki[gid][0]}"}};</script>' if gid in wiki else "<html></html>"
            if "action=parse" in url:
                page = next(v for v in wiki.values() if v[0].replace("_", "+") in url or v[0].replace("_", " ") in urllib.parse.unquote_plus(url))
                return json.dumps({"parse": {"wikitext": {"*": page[1]}}})
            if "nexusmods" in url:
                q = json.loads(data)
                if "games(" in q["query"]:
                    # Nexus liefert weniger als erbeten (0.8.5): hier ein Spiel je Seite
                    nodes = [{"id": 1, "domainName": "harborheist", "name": "Harbor Heist", "modCount": 42},
                             {"id": 2, "domainName": "paperlantern", "name": "Paper Lantern", "modCount": 3}]
                    o = q["variables"]["o"]
                    return json.dumps({"data": {"games": {"totalCount": 2, "nodes": nodes[o:o + 1]}}})
                return json.dumps({"data": {"top": {"nodes": [{"name": "Better Boats", "endorsements": 310, "modId": 1}]},
                                            "vr": {"totalCount": 2, "nodes": [{"name": "VRAM Saver", "endorsements": 50, "modId": 3},
                                                                              {"name": "Harbor VR Fix", "endorsements": 12, "modId": 2}]},
                                            "vx": {"nodes": []}}})
            raise sources.FetchError(url, 404)
        sources.fetch = fake
        logs = []
        self.assertTrue(sync._pcgw(logs.append)["ok"])
        self.assertFalse(any("3000103" in u for u, d, h in calls))       # VR eingebaut: nicht gefragt
        self.assertIn("PCGamingWiki: 2 Spiele gelesen, 2 mit Seite, 1 mit VR per Mod", "\n".join(logs))
        self.assertTrue(sync._nexus(dict(sync.SETTINGS, nexus_key="k" * 30), logs.append)["ok"])
        self.assertEqual([json.loads(d)["variables"]["o"] for u, d, h in calls if "games(" in d], [0, 1])
        self.assertTrue(all(h.get("apikey") == "k" * 30 for u, d, h in calls if "nexusmods" in u))
        col = store.load_json(collection.FILE, collection.EMPTY)["games"]
        self.assertEqual(col["gog:77"]["nexus"]["dom"], "paperlantern")     # „Legacy“ fällt beim Vergleich weg
        self.assertTrue(col["steam:3000102"]["nexus"]["none"])
        self.assertNotIn("nexus", col["name:ps2:star hop"])
        self.assertEqual([m["name"] for m in col["steam:3000101"]["nexus"]["vr"]], ["Harbor VR Fix"])   # VRAM zählt nicht
        rows = {x["key"]: x for x in collection.view({"games": col})["games"]}
        self.assertEqual(rows["steam:3000101"]["vrmod"], ["HTC Vive", "Oculus Rift"])
        self.assertTrue(rows["steam:3000101"]["vorpx"])
        self.assertEqual(rows["gog:77"]["nexus"]["n"], 3)
        self.assertNotIn("vrmod", rows["steam:3000102"])
        # zweiter Lauf: Liste aus dem Zwischenspeicher, nichts mehr zu tun
        calls.clear()
        sync._nexus(dict(sync.SETTINGS), logs.append)
        self.assertEqual(calls, [])
        self.assertEqual(mods.mod_url("harborheist", 2), "https://www.nexusmods.com/harborheist/mods/2")

    def test_sim_racing(self):
        """Sim-Racing (0.8.3): Liste der Rennsimulationen bestätigt, Steam-Schlagwörter (gebündelt) sind ein Hinweis."""
        from app import wheel
        store.save_json(collection.FILE, {"games": {
            "steam:3200001": {"name": "Rally Moth", "store": "Steam", "id": "3200001"},
            "steam:3200002": {"name": "Truck Lanes", "store": "Steam", "id": "3200002"},
            "steam:3200003": {"name": "Harbor Heist", "store": "Steam", "id": "3200003"},
            "gog:88": {"name": "Moon Racer Edition", "store": "GOG", "id": "88"},
            "name:ps4:rally moth": {"name": "Rally Moth", "system": "PS4"}}, "n": 5})
        raw = "Erfundene Einleitung.\nThis is a Wiki post now, anyone can edit.\n" + "\n".join(
            ["Rally Moth", "Moon Racer Edition"] + [f"Erfundene Rennsimulation {i}" for i in range(20)])
        tags = {"response": {"tags": [{"tagid": 599, "name": "Simulation"}, {"tagid": 1644, "name": "Driving"}, {"tagid": 19, "name": "Action"}]}}
        # SimHub (0.8.5): Bilder mit der Steam-ID im Namen, Namen darunter; Flugsimulationen zählen nicht
        simhub = ('<h2>Supported Games</h2><h3>Racing</h3>'
                  '<figure><img src="https://www.simhubdash.com/wp-content/uploads/2020/03/3200009-300x140.jpg" alt=""><figcaption>Comet Kart VR (PC only)</figcaption></figure>'
                  + "".join(f'<figure><img src="https://www.simhubdash.com/wp-content/uploads/2019/01/39000{i:02d}-300x140.jpg"><figcaption>Erfundenes Rennen {i}</figcaption></figure>' for i in range(20))
                  + '<h3>Flight simulators</h3><figure><img src="https://www.simhubdash.com/wp-content/uploads/2019/01/3200003-300x140.jpg"><figcaption>Harbor Heist</figcaption></figure>')
        data = store.load_data()
        data["titles"]["comet"] = dict(titles.new_title("Comet Kart VR"), steam_appid="3200009", wish=True)
        store.save_data(data)
        items = {"response": {"store_items": [{"appid": 3200001, "tags": [{"tagid": 19, "weight": 10}]},
                                              {"appid": 3200002, "tags": [{"tagid": 1644, "weight": 300}, {"tagid": 599, "weight": 200}]},
                                              {"appid": 3200003, "tagids": [19]}]}}
        calls = []

        def fake(url, timeout=25, ua=None, headers=None):
            calls.append(url)
            if "granitedevices" in url:
                return raw
            if "simhubdash" in url:
                return simhub
            if "GetTagList" in url:
                return json.dumps(tags)
            if "GetItems" in url:
                return json.dumps(items)
            raise sources.FetchError(url, 404)
        sources.fetch = fake
        logs = []
        self.assertTrue(sync._wheel(logs.append)["ok"])
        self.assertEqual(sum("GetItems" in u for u in calls), 1)                 # alle vier Apps in einer Anfrage
        self.assertIn("3200009", next(u for u in calls if "GetItems" in u))      # auch der VR-Titel
        self.assertIn("Listen der Rennspiele mit 22 (Simucube-Forum) und 21 Spielen (SimHub, 21 mit Steam-ID), darin 1 VR-Titel und 2 Spiele der Sammlung", "\n".join(logs))
        self.assertIn("Steam-Schlagwörter für 4 Spiele gelesen, 1 mit Hinweis auf Sim-Racing", "\n".join(logs))
        col = store.load_json(collection.FILE, collection.EMPTY)["games"]
        self.assertEqual(col["steam:3200002"]["stag"]["tags"], ["Driving", "Simulation"])
        rows = {x["key"]: x for x in collection.view({"games": col})["games"]}
        self.assertEqual(rows["steam:3200001"]["wheel"], {"src": ["Simucube-Forum"], "tags": []})
        self.assertEqual(rows["steam:3200002"]["wheel"], {"src": [], "tags": ["Driving", "Simulation"]})
        self.assertEqual(rows["gog:88"]["wheel"]["src"], ["Simucube-Forum"])
        self.assertNotIn("wheel", rows["steam:3200003"])                        # nur unter „Flight simulators“
        lib = {r["key"]: r for r in library.view(store.load_data())["wishlist"]}
        self.assertEqual(lib["comet"]["wheel"]["src"], ["SimHub"])               # VR-Titel über die Steam-ID
        self.assertNotIn("wheel", rows["steam:3200003"])
        self.assertNotIn("wheel", rows["name:ps4:rally moth"])                  # nur PC
        self.assertEqual(wheel.hint(["Racing", "Action"]), [])                  # Rennen allein reicht nicht
        self.assertEqual(wheel.hint(["Open World", "Action", "Automobile Sim", "Shooter"]), [])   # Autos allein reichen nicht
        self.assertEqual(wheel.hint(["Racing", "Automobile Sim"]), ["Racing", "Automobile Sim"])
        raw2 = ("Erfundener Name | 2021-12-15 11:01:45 UTC | #1\n\nHi,\nRally Moth \nMoon Racer Edition\n\n-------------------------\n\n"
                "Anderer Name | 2022-01-02 10:00:00 UTC | #2\n\nPixel Kart\n")
        self.assertEqual(wheel.game_list(raw2), ["Rally Moth", "Moon Racer Edition"])     # nur der erste Beitrag
        # zweiter Lauf: alles aktuell, kein Abruf
        calls.clear()
        sync._wheel(logs.append)
        self.assertEqual(calls, [])
        # Liste mit altem Leser (0.8.6): beide Listen gleich neu, nicht erst nach 30 Tagen
        wl = store.load_json(wheel.LIST_FILE, {})
        wl.pop("v")
        store.save_json(wheel.LIST_FILE, wl)
        sync._wheel(logs.append)
        self.assertEqual(sum(wheel.LIST in u or wheel.SIMHUB in u for u in calls), 2)
        self.assertEqual(store.load_json(wheel.LIST_FILE, {})["v"], wheel.V)

    def test_fast_run(self):
        """Beschleunigt auffüllen (0.8.6): Grenzen je Lauf mal FAST nur in diesem Lauf, danach wie vorher."""
        seen, old = [], sync._details
        sync._details = lambda log: seen.append((sync.DETAILS_MAX, sync.IGDB_NAMES)) or {"ok": True, "at": "x"}
        try:
            self.assertTrue(sync.run(only={"details"}, by_hand=True, fast=True))
            self.assertIn("beschleunigt", store.load_json("sync.json", {})["log"][0])
            self.assertTrue(sync.run(only={"details"}, by_hand=True))
        finally:
            sync._details = old
        self.assertEqual(seen[0], (120 * sync.FAST, 120 * sync.FAST))
        self.assertEqual(seen[1], (120, 120))

    def test_pc_wishlist(self):
        """PC-Wunschliste (0.8.2): ganze gg.deals-Liste, Steam-ID aus der Sammlung oder der Steam-Suche, Preise über
        die gg.deals-API; eine neue Liste behält, was schon bekannt ist."""
        from app import pcwish
        store.save_json(collection.FILE, {"games": {"steam:3100001": {"name": "Harbor Heist", "store": "Steam", "id": "3100001"}}})
        sync.save_settings({"gg_key": "geheim-1234567890abcd"})
        added, gone = pcwish.replace([{"slug": "harbor-heist", "name": "Harbor Heist"}, {"slug": "rally-moth", "name": "Rally Moth"},
                                      {"slug": "night-tram", "name": "Night Tram"}], "Lesezeichen")
        self.assertEqual((len(added), gone), (3, []))
        gg = {"success": True, "data": {
            "3100001": {"url": "https://gg.deals/game/harbor-heist/", "prices": {"currentRetail": "20.00", "currentKeyshops": "15.50",
                                                                                 "historicalRetail": "18.00", "historicalKeyshops": "15.00", "currency": "EUR"}},
            "3100002": {"url": "https://gg.deals/game/rally-moth/", "prices": {"currentRetail": "9.99", "currentKeyshops": None,
                                                                               "historicalRetail": "4.99", "historicalKeyshops": None, "currency": "EUR"}}}}
        net = FakeNet({"storesearch/?term=Rally": json.dumps({"items": [{"id": 3100002, "name": "Rally Moth", "type": "app"}]}),
                       "storesearch/?term=Night": json.dumps({"items": [{"id": 3100009, "name": "Night Tram Deluxe", "type": "app"}]}),
                       "api.gg.deals": json.dumps(gg)})
        sources.fetch = net
        logs = []
        self.assertTrue(sync._pcwish(sync.load_settings(), logs.append)["ok"])
        self.assertIn("3 Spiele, 2 Steam-IDs neu zugeordnet (2 Steam-Suchen), 2 mit Preis von gg.deals, 1 ohne Steam-ID", "\n".join(logs))
        self.assertNotIn("geheim-1234567890abcd", "\n".join(logs))
        self.assertFalse(any("Harbor" in u for u in net.calls if "storesearch" in u))     # aus der Sammlung
        v = {r["slug"]: r for r in pcwish.view(store.load_data())["rows"]}
        self.assertEqual((v["harbor-heist"]["best"], v["harbor-heist"]["best_from"], v["harbor-heist"]["low"]), (15.5, "Keyshop", 15.0))
        self.assertTrue(v["harbor-heist"]["near"])
        self.assertTrue(v["harbor-heist"]["owned"])
        self.assertEqual(v["rally-moth"]["over"], 1.002)
        self.assertEqual(v["night-tram"]["appid"], "")
        # neue Liste: Bekanntes bleibt, Fehlendes fällt weg
        added, gone = pcwish.replace([{"slug": "rally-moth", "name": "Rally Moth"}], "Server")
        self.assertEqual((added, sorted(gone)), ([], ["Harbor Heist", "Night Tram"]))
        self.assertEqual(store.load_json(pcwish.FILE, pcwish.EMPTY)["items"]["rally-moth"]["appid"], "3100002")
        sync.save_settings({"gg_key": ""})

    def test_diagnose(self):
        self.seed()
        sync.save_settings({"gg_key": "geheim-1234567890abcd"})
        sale = qsdb_list(qsdb_card("Laser Tennis", "2222222222222222", 9.0, 30.0, end=1793170800), pages=3)
        answers = [
            ("/on_sale/", 200, sale),
            ("all_apps", 200, qsdb_list(qsdb_card("Laser Tennis", "2222222222222222", 9.0, 30.0))),
            ("/game/laser-tennis", 200, qsdb_game_html("Laser Tennis", "2222222222222222", 9.0, 30.0, "2026-10-28",
                                                        [(1700000000000, 30.0), (1792000000000, 9.0)])),
            ("appdetails", 200, json.dumps({"10": {"success": True, "data": []}})),
            ("storesearch", 200, json.dumps({"items": []})),
            ("api.gg.deals", 403, "<html><title>Just a moment...</title>cf_chl_opt</html>"),
        ]
        seen = []

        def fake_request(url, ua=None, timeout=25, encoding="", headers=None, data=None):
            seen.append(url)
            for part, code, text in answers:
                if part in url:
                    return {"url": url, "status": code, "text": text, "enc": "gzip", "server": "nginx", "error": ""}
            return {"url": url, "status": 0, "text": "", "enc": "", "server": "", "error": "unbekannt"}
        old = sources.request
        sources.request = fake_request
        try:
            lines = sync.diagnose()
        finally:
            sources.request = old
        text = "\n".join(lines)
        self.assertIn("1 Angebote erkannt, 3 Seiten", text)
        self.assertIn("1 Treffer für „Sky Garden“, keiner passt eindeutig", text)
        self.assertIn("Tief 9.0 € am", text)
        self.assertIn("App 10: kostenlos oder ohne Preis", text)
        self.assertIn("gg.deals, Preise: HTTP 403", text)
        self.assertIn("Prüfseite von Cloudflare", text)
        self.assertNotIn("geheim", text)
        self.assertTrue(any("key=geheim" in u for u in seen))

    def test_probes(self):
        """Proben der neuen Quellen (0.7): erfundene Antworten im echten Aufbau, nichts wird gespeichert,
        der IGDB-Schlüssel steht nie im Ergebnis."""
        from app import probes
        col = {"games": {
            "steam:3000101": {"name": "Harbor Heist", "store": "Steam", "id": "3000101", "rev": {"n": 900}, "genres": ["Action", "Abenteuer", "Racing"]},
            "steam:3000102": {"name": "Tiny Tennis", "store": "Steam", "id": "3000102", "rev": {"n": 5}},
            "steam:3000103": {"name": "Rally Moth", "store": "Steam", "id": "3000103", "rev": {"n": 50}, "genres": ["Rennen"]},
            "name:orbit golf": {"name": "Orbit Golf", "system": "PS4", "store": "PlayStation"},
            "retro:snes:star hop": {"name": "Star Hop", "system": "SNES", "src": "retro", "regions": ["Europe"]},
            "retro:snes:pixel hack": {"name": "Pixel Hack", "system": "SNES", "src": "retro", "regions": ["USA"], "flags": ["hack"]}}}
        self.assertEqual([x and x["name"] for x in probes.samples(col).values()], ["Rally Moth", "Harbor Heist", "Orbit Golf", "Star Hop", "Orbit Golf"])
        self.assertEqual(probes.search_name("Moon Räcer: Édition Spéciale (Europe)"), "Moon Racer: Edition Speciale")
        details = {"3000101": {"success": True, "data": {"name": "Harbor Heist", "metacritic": {"score": 84},
                   "genres": [{"description": "Action"}], "categories": [{"description": "VR-Unterstützung"}],
                   "release_date": {"date": "12. März 2019"}, "developers": ["Kite Works"], "publishers": ["Paper Moon"],
                   "supported_languages": "Englisch, Deutsch", "short_description": "Ein <b>Raubzug</b> im Hafen."}}}
        deku = ('<html><head><meta content="Golf im Orbit." property="og:description"></head><body>'
                '<li>Genres: Sports</li><li>Metacritic: 81 7.9</li><li>How Long To Beat: Main Story 6 hours</li></body></html>')
        meta = 'clrmamepro ( name "x" )\n\ngame (\n\tcomment "Star Hop (Europe)"\n\tgenre "Platform"\n)\n\ngame (\n\tcomment "Moon Rover (USA)"\n\tgenre "Racing"\n)\n'
        answers = [("appdetails", 200, json.dumps(details)),
                   ("api/appid.php?appid=3000101", 200, '<script>RLCONF={"wgPageName":"Harbor_Heist","wgTitle":"Harbor Heist"};</script>'),
                   ("action=parse", 200, json.dumps({"parse": {"wikitext": {"*": "==VR support==\n{{VR support\n|native 3d = false\n|vorpx = true\n|vorpx modes = G3D\n|vorpx notes = \n|3rd space gaming vest =\n|3rd space gaming vest notes =\n|openxr = \n|steamvr = false\n}}\n"
                                                                                  "==Input==\n{{Input\n|controller support = true\n|steering wheel support = [[Glossary:Wheel|true]]<ref>Test</ref>\n|steering wheel support notes = nur Logitech\n|force feedback = unknown\n}}\n"}}})),
                   ("api/appid.php?appid=3000103", 200, '<script>RLCONF={"wgPageName":"Rally_Moth","wgTitle":"Rally Moth"};</script>'),
                   ("dekudeals.com/search", 200, '<a href="/items/orbit-golf-deluxe-party">Orbit Golf Deluxe Party</a>'
                                                 '<a class="main-link" href="https://www.dekudeals.com/items/orbit-golf?format=digital">Orbit Golf</a>'),
                   ("api.nexusmods.com", 200, None),
                   ("GetTagList", 200, json.dumps({"response": {"tags": [{"tagid": 699, "name": "Racing"}, {"tagid": 599, "name": "Simulation"},
                                                                         {"tagid": 19, "name": "Action"}]}})),
                   ("GetItems", 200, json.dumps({"response": {"store_items": [
                       {"appid": 3000103, "tags": [{"tagid": 599, "weight": 80}, {"tagid": 699, "weight": 120}]},
                       {"appid": 3000101, "tagids": [19]}]}})),
                   ("granitedevices", 200, "Hier eine Liste der Simulationen.\nThis is a Wiki post now, anyone can edit.\n\n"
                                           + "\n".join(["Rally Moth", "Moon Racer Edition"] + [f"Erfundene Rennsimulation {i}" for i in range(20)])),
                   ("simhubdash", 200, '<h3>Racing</h3><figure><img src="/wp-content/uploads/2018/09/3000103-300x140.jpg"><figcaption>Rally Moth (PC only)</figcaption></figure><h3>Flight simulators</h3>'),
                   ("dekudeals.com/items/orbit-golf", 200, deku),
                   ("howlongtobeat", 200, "<input placeholder='search'>"),
                   ("metadat/", 200, meta),
                   ("id.twitch.tv", 200, json.dumps({"access_token": "tok"})),
                   ("v4/external_games", 200, json.dumps([{"game": 5, "uid": "3000101"}])),
                   ("v4/games", 200, json.dumps([{"id": 5, "name": "Harbor Heist", "genres": [{"name": "Shooter"}],
                                                  "aggregated_rating": 82.4, "aggregated_rating_count": 6,
                                                  "summary": "A heist.", "involved_companies": [{"developer": True, "company": {"name": "Kite Works"}}]}])),
                   ("game_time_to_beats", 200, json.dumps([{"hastily": 18000, "normally": 25200, "completely": 36000, "count": 12}]))]
        seen, lines = [], []

        def nexus_answer(data):
            q = json.loads(data)
            if "games(count" in q["query"]:
                return {"data": {"games": {"totalCount": 2, "nodes": [{"domainName": "harborheist"}, {"domainName": "starhop"}]}}}
            if "games(" in q["query"]:
                found = q["variables"]["n"] == "*Harbor Heist*"
                return {"data": {"games": {"nodes": [{"id": 9, "domainName": "harborheist", "name": "Harbor Heist", "modCount": 42}] if found else []}}}
            return {"data": {"top": {"totalCount": 42, "nodes": [{"name": "Better Boats", "endorsements": 310, "downloads": 9000, "modId": 1}]},
                             "vr": {"totalCount": 1, "nodes": [{"name": "Harbor VR Fix", "endorsements": 12, "downloads": 400, "modId": 2}]}}}

        heads = []

        def fake_request(url, ua=None, timeout=25, encoding="", headers=None, data=None):
            seen.append((url, data))
            heads.append((url, dict(headers or {})))
            for part, code, text in answers:
                if part in url:
                    if text is None:
                        text = json.dumps(nexus_answer(data))
                    return {"url": url, "status": code, "text": text, "enc": "", "server": "x", "error": ""}
            return {"url": url, "status": 0, "text": "", "enc": "", "server": "", "error": "unbekannt"}

        def probe(name, url, info, headers=None, shown=None):
            r = sources.request(url)
            lines.append(f"{name}: {info(r['text'])}")
            return r["text"]
        old = sources.request
        sources.request = fake_request
        try:
            probes.run(probe, lines, col, {"igdb_id": "a" * 30, "igdb_secret": "b" * 30, "nexus_key": "n" * 40}, lambda s: None)
        finally:
            sources.request = old
        text = "\n".join(lines)
        self.assertIn("Metacritic 84", text)
        self.assertIn("VR ['VR-Unterstützung']", text)
        self.assertIn("Beschreibung 21 Zeichen: „Ein Raubzug im Hafen.“", text)
        self.assertIn("Seite „Harbor Heist“", text)
        self.assertIn("native 3d false; vorpx true; vorpx modes G3D; steamvr false", text)
        self.assertNotIn("vest", text)
        self.assertEqual(sum("action=parse" in u for u, d in seen), 1)
        self.assertNotIn("PCGamingWiki, Lenkrad", text)
        self.assertIn("Steam, Schlagwörter (Liste): 3 Schlagwörter; Racing 699, Driving fehlt, Simulation 599", text)
        self.assertIn("„Rally Moth“: Racing, Simulation → Hinweis Sim-Racing; „Harbor Heist“: Action → kein Hinweis", text)
        self.assertIn("Liste der Rennsimulationen (Simucube-Forum): 22 Spiele, etwa Rally Moth, Moon Racer Edition", text)
        self.assertIn("Rennspiel „Rally Moth“ drin", text)
        self.assertIn("SimHub, unterstützte Rennspiele: 1 Rennspiele, 1 mit Steam-ID im Bild, etwa Rally Moth (PC only); Rennspiel „Rally Moth“ drin", text)
        self.assertTrue(all(h.get("apikey") == "n" * 40 for u, h in heads if "nexusmods" in u))
        self.assertNotIn("n" * 40, text)
        self.assertIn("Nexus Mods (mit Schlüssel), Spiel „Harbor Heist“: „Harbor Heist“, 42 Mods, Seite https://www.nexusmods.com/games/harborheist", text)
        self.assertIn("Nexus Mods, Spieleliste: 2 auf Seite 1, 2 insgesamt", text)
        self.assertIn("Nexus Mods, beliebt: „Better Boats“ (310 Empfehlungen, 9000 Downloads)", text)
        self.assertIn("Nexus Mods, mit VR im Namen (1): „Harbor VR Fix“", text)
        self.assertTrue(any("page=Harbor+Heist" in u for u, d in seen))
        self.assertFalse(any("uevr" in u or "cargo" in u for u, d in seen))
        self.assertIn("IGDB, PC über Steam-ID", text)
        self.assertIn("DekuDeals, Suche (PS4)", text)
        self.assertIn("erster Treffer „orbit-golf“", text)
        self.assertIn("Metacritic: 81 (Nutzer 7.9)", text)
        self.assertIn("Beschreibung „Golf im Orbit.“", text)
        self.assertIn("2 Einträge; zu „Star Hop“", text)
        self.assertIn("Spielzeit eilig 5,0 h, normal 7,0 h, komplett 10,0 h (12 Angaben)", text)
        self.assertIn("Entwickler ['Kite Works']", text)
        self.assertNotIn("a" * 30, text)
        self.assertTrue(any("game_id = 5" in (d or b"").decode() for u, d in seen))
        # 0.7.5: findet die Suche nichts, der Name als Teilstück bis zum ersten Sonderzeichen
        seen.clear(); lines.clear()
        answers[:] = [a for a in answers if a[0] not in ("v4/games", "v4/external_games")] + [("v4/games", 200, "[]")]
        sources.request = fake_request
        try:
            probes.igdb(lines, {"igdb_id": "a" * 30, "igdb_secret": "b" * 30}, [("Konsole", "Moon Wars: Masters of Rändern", None, "PS1")], lambda s: None)
        finally:
            sources.request = old
        bodies = [(d or b"").decode() for u, d in seen if "v4/games" in u]
        self.assertIn('where name ~ *"Masters of R"* & platforms = (7); limit 2;', bodies[-1])
        self.assertIn("keine Treffer", lines[-1])

    def test_review_form_fallback(self):
        """Schickt Steam bei den Rezensionen eine Seite statt Daten, gilt die nächste Form der Adresse (0.7.4)."""
        asked, logs = [], []

        class Src:
            name = "Steam-Wertungen"
            log = staticmethod(logs.append)

            def get(self, url, shown=None):
                asked.append(url)
                return '{"success": 1}' if "filter=all" in url else "<html>Willkommen bei Steam!</html>"
        old = dict(sync._rev_q)
        try:
            self.assertEqual(sync._rev_get(Src(), "3000101", "x"), '{"success": 1}')
            self.assertEqual(len(asked), 2)
            self.assertEqual(sync._rev_q["i"], 1)
            self.assertIn("Form 2", logs[0])
            sync._rev_get(Src(), "3000102", "x")
            self.assertEqual(len(asked), 3)
            self.assertEqual(len(logs), 1)
            pages = Src()
            pages.get = lambda url, shown=None: asked.append(url) or "<html></html>"
            sync._rev_get(pages, "3000103", "x")
            sync._rev_get(pages, "3000104", "x")
            self.assertEqual(len(asked), 3 + 4 + 1)
        finally:
            sync._rev_q.update(old)

    def test_sale_ended_and_due(self):
        from datetime import datetime, timezone
        t = titles.new_title("Sky Garden")
        t["live"] = {"meta": {"price": 4.0, "base": 8.0, "discount": 50, "until": "2026-01-01", "low": 4.0,
                              "at": "2026-01-01T00:00:00+00:00"}}
        r = library.row("x", t, at=datetime(2026, 1, 5, tzinfo=timezone.utc))
        self.assertEqual((r["live"]["meta"]["price"], r["live"]["meta"]["discount"]), (8.0, 0))
        self.assertTrue(r["live"]["meta"]["stale"])
        self.assertFalse(r["live"]["meta"]["at_low"])
        self.assertTrue(sync.due())
        sync.save_settings({"auto": False})
        self.assertFalse(sync.due())

    def test_merge_keeps_newer_live(self):
        d = empty()
        a, _ = titles.upsert(d, "Sky Garden", meta_id="1111111111111111")
        b, _ = titles.upsert(d, "Sky Garden VR", steam_appid="3000001")
        d["titles"][a]["live"] = {"meta": {"price": 5.0, "at": "2026-10-01T00:00:00+00:00"}}
        d["titles"][b]["live"] = {"steam": {"price": 6.0, "at": "2026-10-02T00:00:00+00:00"},
                                  "meta": {"price": 4.0, "at": "2026-10-03T00:00:00+00:00"}}
        titles.merge(d, a, b)
        self.assertEqual(d["titles"][a]["live"]["meta"]["price"], 4.0)
        self.assertEqual(d["titles"][a]["live"]["steam"]["price"], 6.0)


# Erfundene Antworten im Aufbau von Steam Web API, gg.deals-Wunschliste und Sharenite
def steam_owned_json(*games):
    return json.dumps({"response": {"game_count": len(games), "games": [{"appid": int(a), "name": n} for a, n in games]}})


def steam_wish_json(*appids):
    return json.dumps({"response": {"items": [{"appid": int(a), "priority": i} for i, a in enumerate(appids)]}})


def steam_app_json(appid, name, vr):
    cats = [{"id": 2, "description": "Einzelspieler"}] + ([{"id": 54, "description": "Nur VR"}] if vr else [])
    return json.dumps({str(appid): {"success": True, "data": {"type": "game", "name": name, "categories": cats}}})


def gg_wish_html(*names, pages=1):
    rows = "".join(f'<div class="game-item"><a href="/game/{titles.norm(n).replace(" ", "-")}/"><img alt=""></a>'
                   f'<a class="title" href="https://gg.deals/game/{titles.norm(n).replace(" ", "-")}/"><span>{n}</span></a></div>'
                   for n in names)
    nav = "".join(f'<a href="?page={i}">{i}</a>' for i in range(2, pages + 1))
    return f"<html><body>{rows}{nav}</body></html>"


def sharenite_html(games, total=None, vr_tags=()):
    opts = '<select name="tag_ids[]" multiple><option value="__none__">No tags</option>' + "".join(
        f'<option value="{v}">{label}</option>' for v, label in vr_tags) + '<option value="t-x">Puzzle</option></select>'
    rows = ""
    for i, (name, src, tags, *plat) in enumerate(games):
        pills = f'<span class="games-value-pill games-value-pill--source">{src}</span>' + "".join(
            f'<span class="games-value-pill games-value-pill--tag">{t}</span>' for t in tags) + "".join(
            f'<span class="games-value-pill games-value-pill--platform">{p}</span>' for p in (plat[0] if plat else []))
        rows += (f'<tr id="game_{i:04d}"><td><div class="d-flex"><strong>{name}</strong></div></td>'
                 f'<td class="d-lg-table-cell d-xxl-none"><div class="games-meta-stack">{pills}'
                 f'<span class="games-value-pill games-value-pill--category games-value-pill--muted">No categories</span></div></td>'
                 f'<td class="d-none d-xxl-table-cell">{pills}</td></tr>')
    return f'<html>{opts}<p class="games-list-total">Total games listed: {total or len(games)}</p><table><tbody>{rows}</tbody></table></html>'


class TestAccounts(unittest.TestCase):
    def test_parsers(self):
        self.assertEqual(accounts.steam_id_input("https://steamcommunity.com/profiles/76561190000000001/"), ("id", "76561190000000001"))
        self.assertEqual(accounts.steam_id_input("https://steamcommunity.com/id/beispiel/"), ("vanity", "beispiel"))
        self.assertEqual(accounts.steam_id_input("x y"), ("", ""))
        self.assertEqual(accounts.steam_owned(steam_owned_json(("3000001", "Sky Garden"))), [{"appid": "3000001", "name": "Sky Garden"}])
        with self.assertRaises(ValueError):
            accounts.steam_owned(json.dumps({"response": {}}))     # Spieldetails privat
        self.assertEqual(accounts.steam_wishlist(steam_wish_json("3000009", "3000010")), ["3000009", "3000010"])
        self.assertEqual(accounts.steam_app(steam_app_json(3000009, "Deep Dive", True), "3000009"),
                         {"name": "Deep Dive", "type": "game", "vr": True})
        self.assertFalse(accounts.steam_app(steam_app_json(3000010, "Flat Racer", False), "3000010")["vr"])
        items, pages = accounts.gg_wishlist(gg_wish_html("Sky Garden", "Flat Racer", pages=3))
        self.assertEqual([i["name"] for i in items], ["Sky Garden", "Flat Racer"])
        self.assertEqual(pages, 3)
        games, total, tags = accounts.sharenite_page(sharenite_html(
            [("Sky Garden", "Steam", ["VR", "Puzzle"]), ("Flat Racer", "GOG", [])], total=250, vr_tags=[("t-vr", "VR"), ("t-avr", "Asymmetric VR")]))
        self.assertEqual(total, 250)
        self.assertEqual(tags, ["t-vr", "t-avr"])
        self.assertEqual([(g["name"], g["source"], g["vr"]) for g in games], [("Sky Garden", "Steam", True), ("Flat Racer", "GOG", False)])

    def test_console_games_left_out(self):
        self.assertTrue(collection.console_only(["Sony PlayStation 4"]))
        self.assertFalse(collection.console_only(["Sony PlayStation 4", "PC (Windows)"]))
        self.assertTrue(collection.console_only([], "PlayStation"))
        self.assertFalse(collection.console_only([], "Steam"))
        # Sharenite: PS4-Fassung fällt weg, ein früher daraus eingetragener Besitz ebenso;
        # dasselbe Spiel zusätzlich am PC zählt
        d = empty()
        k, _ = titles.upsert(d, "Comet Chase")
        d["titles"][k]["owned"] = {"pc": {"src": "sharenite", "label": "PlayStation"}}
        games = accounts.sharenite_page(sharenite_html([
            ("Comet Chase", "PlayStation", ["VR"], ["Sony PlayStation 4"]),
            ("Deep Dive", "PlayStation", ["VR"], ["Sony PlayStation 4"]),
            ("Sky Garden", "PlayStation", ["VR"], ["Sony PlayStation 4"]),
            ("Sky Garden", "Steam", ["VR"], ["PC (Windows)"])]))[0]
        self.assertEqual([g["console"] for g in games], [True, True, True, False])
        accounts.apply_sharenite(d, games)
        self.assertNotIn("pc", d["titles"][k]["owned"])
        self.assertIsNone(titles.find(d, name="Deep Dive"))
        self.assertEqual(d["titles"][titles.find(d, name="Sky Garden")]["owned"]["pc"]["label"], "Steam")
        # Playnite-Export mit Plattformen: der VR-Import lässt reine Konsolenspiele weg, die
        # Sammlung führt sie unter ihrem System (seit 0.5.5)
        csv_text = ("Name,Spiel-ID,Schlagwörter,Plattformen\nDeep Dive,CUSA00001_00,VR,Sony PlayStation 4\n"
                    "Sky Garden,3000001,VR,\"PC (Windows), Sony PlayStation 4\"\n")
        self.assertEqual([e["name"] for e in imports.parse_playnite(csv_text)], ["Sky Garden"])
        self.assertEqual(sorted((g["name"], g.get("system", "PC")) for g in collection.parse(csv_text).values()),
                         [("Deep Dive", "PS4"), ("Sky Garden", "PC")])
        # Export der PlayStation-Bibliothek ohne Plattformen: an den Kennungen erkannt (CUSA… ist
        # PS4, NPWR… eine Trophäenliste von PS3 oder Vita, sonst nur PS); er ersetzt nur die Konsolenspiele, die PC-Sammlung bleibt stehen
        ps = "Name,Spiel-ID,Schlagwörter\nDeep Dive,CUSA00001_00,VR\nComet Chase,NPWR00002_00,\nStar Hop,XXXX00003_00,\n"
        self.assertEqual(imports.parse_playnite(ps), [])
        stats = {}
        self.assertEqual({g["name"]: g["system"] for g in collection.parse(ps, stats=stats).values()},
                         {"Deep Dive": "PS4", "Comet Chase": "PS3 / Vita", "Star Hop": "PS"})
        self.assertEqual(stats, {"console": 3, "systems": {"PS4": 1, "PS3 / Vita": 1, "PS": 1}})
        self.assertLess(collection.system_order("PS3 / Vita"), collection.system_order("PS2"))
        store.DATA_DIR = tempfile.mkdtemp()
        data = store.load_data()
        server.import_collection(data, COLLECTION, dry=False)
        self.assertEqual(server.import_collection(data, ps, dry=False),
                         {"n": 3, "new": 3, "console": 3, "systems": {"PS4": 1, "PS3 / Vita": 1, "PS": 1}, "kept": 4})
        self.assertEqual(len(store.load_json(collection.FILE, {})["games"]), 7)

    def test_wishes_from_sources(self):
        d = empty()
        a, _ = titles.upsert(d, "Sky Garden")
        b, _ = titles.upsert(d, "Laser Tennis")
        c, _ = titles.upsert(d, "Moon Rover")
        d["titles"][c]["wish"] = True                       # aus der Tabelle, ohne Quelle
        self.assertEqual(titles.set_wishes(d, "steam", [a, b]), (["Sky Garden", "Laser Tennis"], []))
        titles.set_wishes(d, "gg", [a])
        # Laser Tennis fällt bei Steam weg: keine Quelle mehr, also von der Wunschliste
        self.assertEqual(titles.set_wishes(d, "steam", [a]), ([], ["Laser Tennis"]))
        self.assertTrue(d["titles"][a]["wish"] and d["titles"][c]["wish"])
        # Von Hand genommen: dieselbe Quelle holt ihn erst zurück, nachdem er dort einmal fehlte
        titles.wish_by_hand(d["titles"][a], False)
        titles.set_wishes(d, "steam", [a])
        self.assertFalse(d["titles"][a]["wish"])
        titles.set_wishes(d, "steam", [])
        titles.set_wishes(d, "steam", [a])
        self.assertTrue(d["titles"][a]["wish"])

    def test_apply_steam(self):
        d = empty()
        imports.import_sheet(d, SHEET, dry=False)
        apps = {"3000020": {"name": "Star Ride", "vr": True}, "3000021": {"name": "Flat Racer", "vr": False}}
        res = accounts.apply_steam(d, [{"appid": "3000005", "name": "Sky Garden"}, {"appid": "3000020", "name": "Star Ride"},
                                       {"appid": "3000021", "name": "Flat Racer"}, {"appid": "3000022", "name": "Unbekannt"}],
                                   ["3000023"], apps)
        by = {t["name"]: t for t in d["titles"].values()}
        self.assertEqual((by["Sky Garden"]["steam_appid"], by["Sky Garden"]["steam_sure"]), ("3000005", True))
        self.assertEqual(by["Sky Garden"]["owned"]["pc"]["label"], "Steam")
        self.assertIn("Star Ride", by)
        self.assertNotIn("Flat Racer", by)
        self.assertEqual(res["owned_new"], ["Star Ride"])
        self.assertEqual(res["unchecked"], 2)               # eine gekaufte, eine gewünschte App ohne Prüfung

    def test_detect_and_meta_wishlist(self):
        self.assertEqual(imports.detect(SHEET), "sheet")
        self.assertEqual(imports.detect(PLAYNITE), "playnite")
        self.assertEqual(imports.detect(META_JSON), "meta")
        self.assertEqual(imports.detect(META_TEXT), "meta")
        self.assertEqual(imports.detect("Nr.,Name,Quelle\n1,Sky Garden,https://gg.deals/wishlist/share/AbC123/\n"), "ggwish")
        with self.assertRaises(ValueError):
            imports.detect(json.dumps({"app": "vr-navigator", "data": {}}))
        d = empty()
        imports.import_sheet(d, SHEET, dry=False)
        wish = json.dumps({"kind": "meta-wunschliste", "page": "/my/wishlist/", "links": [
            {"href": "https://www.meta.com/experiences/5555555555555555/", "text": ""},
            {"href": "https://www.meta.com/experiences/5555555555555555/", "text": "Star Ride"},
            {"href": "https://www.meta.com/experiences/1111111111111111/", "text": "Sky Garden"}]})
        res = imports.import_auto(d, wish, dry=False)
        self.assertEqual((res["kind"], res["what"], res["n"], res["new"]), ("meta", "Meta-Wunschliste", 2, 1))
        by = {t["name"]: t for t in d["titles"].values()}
        self.assertEqual(by["Star Ride"]["meta_id"], "5555555555555555")
        self.assertIn("meta", by["Sky Garden"]["wish_src"])
        # Kacheln wie im Meta Store: Marke, Name, Wertung mit Rubriken, Preis; Rubrik-Links zählen
        # nicht. Ein früher mit Wertung im Namen angelegter Titel wird berichtigt, ein nur von der
        # Wunschliste angelegter Eintrag, der dort fehlt, fällt weg
        d["titles"]["alt"] = {"name": "Star Ride\n4,5 (1.645) • Spiele", "meta_id": "7777777777777777", "wish": True,
                              "wish_src": {"meta": "2026-10-01"}, "origin": {"metawish": {"at": "2026-10-01"}}}
        d["titles"]["rubrik"] = {"name": "Startseite", "meta_id": "8888888888888888", "wish": True,
                                 "wish_src": {"meta": "2026-10-01"}, "origin": {"metawish": {"at": "2026-10-01"}}}
        wish = json.dumps({"kind": "meta-wunschliste", "page": "/de-de/experiences/section/1234567890123/", "links": [
            {"href": "https://www.meta.com/de-de/experiences/section/1234567890123/#main", "text": "Zum Hauptinhalt"},
            {"href": "https://www.meta.com/de-de/experiences/view/8888888888888888/", "text": "Startseite"},
            {"href": "https://www.meta.com/de-de/experiences/star-ride/7777777777777777/",
             "text": "Beliebter Artikel\nStar Ride\n4,5 (1.645) • Spiele • Shooter • Action\n19,99 €"},
            {"href": "https://www.meta.com/de-de/experiences/sky-garden/1111111111111111/",
             "text": "Top-Bewertung Sky Garden 4,8 (53.492) • Spiele • Sport Kostenlos"}]})
        self.assertEqual([(e["name"], e["price"]) for e in imports.parse_meta_wishlist(wish)],
                         [("Star Ride", 19.99), ("Sky Garden", None)])
        res = imports.import_auto(d, wish, dry=False)
        # „Star Ride“ aus dem ersten Lesen (andere ID) steht nicht mehr dort und fällt mit weg
        self.assertEqual((d["titles"]["alt"]["name"], res["dropped"]), ("Star Ride", 2))
        self.assertNotIn("rubrik", d["titles"])
        self.assertEqual(d["imports"]["metawish"]["page"], "/de-de/experiences/section/1234567890123/")
        # gg.deals-Wunschliste als CSV: nur bekannte Titel zählen
        res = imports.import_auto(d, "Nr.,Name,Quelle\n1,Laser Tennis,https://gg.deals/wishlist/share/AbC123/\n2,Flat Racer,\n", dry=False)
        self.assertEqual(res["unknown"], ["Flat Racer"])
        self.assertIn("gg", by["Laser Tennis"]["wish_src"])


class TestUi(unittest.TestCase):
    """Oberfläche ohne Zusatzpakete: Jede Adresse, die app.js ruft, gibt es; die dunklen Farben
    stehen in style.css zweimal gleich (wie das Gerät und Wahl „Dunkel“)."""
    STATIC = os.path.join(os.path.dirname(__file__), "..", "app", "static")

    def read(self, name):
        with open(os.path.join(self.STATIC, name), encoding="utf-8") as f:
            return f.read()

    def test_every_api_path_exists(self):
        import re
        js = self.read("js/app.js") + self.read("index.html")
        paths = set(re.findall(r'"(/api/[a-z_/]+)"', js))
        self.assertGreater(len(paths), 8)
        with open(os.path.join(os.path.dirname(__file__), "..", "app", "server.py"), encoding="utf-8") as f:
            src = f.read()
        for p in paths:
            self.assertIn(f'"{p}"', src, f"{p} fehlt im Server")

    def test_dark_tokens_match(self):
        import re
        css = self.read("style.css")
        auto = re.search(r"@media \(prefers-color-scheme: dark\)\{:root:not\(\[data-theme=light\]\)\{([^}]*)\}\}", css)
        chosen = re.search(r":root\[data-theme=dark\]\{color-scheme:dark;([^}]*)\}", css)
        self.assertTrue(auto and chosen)
        tokens = lambda block: dict(re.findall(r"(--[\w-]+):\s*([^;]+);", block))
        self.assertGreater(len(tokens(auto.group(1))), 10)
        self.assertEqual(tokens(auto.group(1)), tokens(chosen.group(1)))
        self.assertIn('localStorage.getItem("vn.theme")', self.read("index.html"))

    def test_colors_have_one_meaning(self):
        # Farbregeln aus docs/oberflaeche.md: Rabatt blau (deal), Tiefstpreis Gold mit ★ (best),
        # prüfen violett (warn); grün nicht für Rabatte
        js = self.read("js/app.js")
        self.assertNotIn('class="b go">−', js)
        self.assertIn('class="b deal">−', js)
        self.assertIn('class="star"', js)
        self.assertNotIn("--meta", self.read("style.css"))

    def test_mobile_selftest(self):
        """Alle Reiter bei 390 px in Chromium: nichts scrollt seitlich, kein Skriptfehler, jedes
        Bedienelement hat einen Namen, Klappen und Suche wirken. Ohne Chromium übersprungen, in
        GitHub Actions ein Fehler."""
        import glob
        import html
        import re
        import shutil
        import subprocess
        from datetime import datetime, timezone
        browser = os.environ.get("CHROME_BIN") or next((shutil.which(n) for n in (
            "chromium", "chromium-browser", "google-chrome", "google-chrome-stable") if shutil.which(n)), None) \
            or next(iter(sorted(glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome"))), None)
        if not browser:
            if os.environ.get("CI"):
                self.fail("kein Chromium gefunden, Oberflächentest in CI nicht übersprungen")
            self.skipTest("kein Chromium gefunden")
        store.DATA_DIR = tempfile.mkdtemp()
        data = store.load_data()
        imports.IMPORTERS["sheet"](data, SHEET, dry=False)
        imports.IMPORTERS["playnite"](data, PLAYNITE, dry=False)
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        k = next(k for k, t in data["titles"].items() if t["name"] == "Laser Tennis")
        data["titles"][k]["live"] = {
            "meta": {"price": 9.99, "base": 29.99, "discount": 67, "kind": "discount", "until": "2099-01-01",
                     "low": 9.99, "low_at": "2026-01-01", "at": now, "rating": 4.6, "ratings": 1234567},
            "steam": {"price": 14.99, "base": 24.99, "discount": 40, "at": "2020-01-01T00:00:00+00:00"}}
        data["titles"][k]["rev"] = {"n": 1234567, "pct": 93, "at": now, "app": "3000001"}
        data["titles"][k].update(play={"now": 123456, "peak": 234567, "since": "2026-10-01", "at": now, "days": []},
                                 news={"date": "2026-09-01", "title": "Patch " + "sehr lang " * 20, "at": now},
                                 meta_ver={"v": "12.345.678_9999999", "since": "2026-10-10"},
                                 vrdb={"pos": 88, "stars": 4.4, "n": 4321, "crossbuy": True, "at": now})
        data["titles"][k]["note"] = "Reddit: " + "sehr lange Notiz ohne Leerzeichen " * 3 + "x" * 120
        data["titles"][k]["opinion"] = {"stand": "2026-10-22", "fassung": "pc", "mehrspieler": "lebendig",
                                        "fazit": "Schnelles Tennis mit vielen Gegnern, " * 4, "crossbuy": True,
                                        "quellen": [{"url": "https://example.org/" + "x" * 80, "datum": "2026-10-01"}]}
        # Zu erledigen: eine zweifelhafte Steam-ID und ein Bundle ohne Meta-ID
        s, _ = titles.upsert(data, "Comet Chase", steam_appid="3000030")
        data["titles"][s].update(owned={"pc": {"src": "playnite", "label": "Steam"}},
                                 steam_doubt="Name bei Steam: Comet Chase Deluxe Soundtrack und weitere Inhalte")
        b, _ = titles.upsert(data, "Moon Rover Ultimate Collection Bundle mit sehr langem Namen")
        data["titles"][b].update(owned={"meta": {"src": "meta"}}, meta_miss=now)
        col = json.loads(json.dumps(collection.EMPTY))
        collection.replace(col, collection.parse(COLLECTION + "Ein ausgesprochen langer Spielname ohne jede Pause"
                                                 "UndNochMehrBuchstaben,,Steam,3000199,,Multiplayer,Puzzle,2020,,90,,,,False\n"))
        collection.replace(col, collection.parse("Name,Spiel-ID,Quelle,Plattformen,Features,Genres\n"
                                                 "Harbor Heist,CUSA00101_00,PlayStation,Sony PlayStation 4,\"Local Co-Op\",Shooter\n"
                                                 "Pixel Kart,,,Nintendo Super Nintendo Entertainment System,,Racing\n"))
        rg, _ = retro.parse("ROMs/GB/Moon Rover (Europe) (En,Fr,De).gb\nROMs/GB/Moon Rover (USA).gb\n"
                            "ROMs/GB/_Extras/Homebrew/Tiny Tennis (World) (Unl).gb\nROMs/SNES/Star Hop (Japan).sfc\n"
                            "ROMs/SNES/Ein sehr langer Retro-Titel mit vielen Wörtern und noch mehr Wörtern (USA).sfc\n")
        retro.apply(col, rg, dry=False)
        retro.apply(col, {k: g for k, g in retro.parse("ROMs/SNES/Star Hop (Japan).sfc\n")[0].items()}, dry=False)
        for g in col["games"].values():
            if g["name"].startswith("Ein sehr langer"):
                g["de"] = {"st": "missing", "alt": "Ein sehr langer deutscher Retro-Titel mit noch mehr Wörtern (Germany) (Rev 1)", "guess": True, "via": "retool"}
        store.save_json(collection.FILE, col)
        data["imports"]["collection"] = {"at": now, "n": len(col["games"]), "new": 0}
        data["imports"]["retro"] = {"at": now, "n": 4, "new": 0, "files": 5, "gone": 1}
        store.save_data(data)
        with open(os.path.join(os.path.dirname(__file__), "ui_selbsttest.html"), encoding="utf-8") as f:
            probe_page = f.read().encode()

        class Handler(server.Handler):
            def do_GET(self):
                if self.path == "/selbsttest":
                    self._send(200, probe_page, "text/html; charset=utf-8")
                    return
                return server.Handler.do_GET(self)
        srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            out = subprocess.run([browser, "--headless", "--no-sandbox", "--disable-gpu", "--virtual-time-budget=30000",
                                  "--window-size=800,900", "--dump-dom",
                                  f"http://127.0.0.1:{srv.server_address[1]}/selbsttest"],
                                 capture_output=True, text=True, timeout=120)
        finally:
            srv.shutdown()
            srv.server_close()
        m = re.search(r'<pre id="out">(.*?)</pre>', out.stdout, re.S)
        self.assertTrue(m, "Selbsttest lieferte kein Ergebnis: " + out.stderr[-300:])
        res = json.loads(html.unescape(m.group(1)))
        self.assertEqual(res["errors"], [])
        views = res["views"]
        self.assertTrue(views.pop("probe")["wide"], "Der Prüfer erkennt einen zu breiten Kasten nicht")
        self.assertGreaterEqual(len(views), 8)
        for name, v in views.items():
            self.assertLessEqual(v["width"], v["view"], f"{name} scrollt seitlich: {v['wide']}")
            self.assertEqual(v["wide"], [], name)
            self.assertEqual(v["unnamed"], [], f"{name}: Bedienelement ohne Namen")
            self.assertGreater(v["chars"], 150, f"{name} zeigt fast nichts")
        self.assertEqual(views["wish"]["open"], [True, False])        # im Besitz startet zu
        self.assertEqual(views["wish:suche"]["open"], [True, True])   # Suche öffnet alles
        self.assertEqual(views["wish:zu"]["open"], [False, False])
        self.assertTrue(views["settings"]["open"] and not any(views["settings:zu"]["open"]))
        self.assertTrue(views["now"]["nav"], "Reiterleiste am Handy ohne weichen Rand")


if __name__ == "__main__":
    unittest.main()
