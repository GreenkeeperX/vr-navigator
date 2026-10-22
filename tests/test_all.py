import json
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

from app import accounts, collection, imports, library, prices, server, sources, store, sync, titles  # noqa: E402

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
        self.assertEqual((rows["Comet Chase"]["crossbuy"], rows["Comet Chase"]["crossbuy_src"]), (True, ""))


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

    def test_replace_keeps_fetched_and_gem(self):
        col = json.loads(json.dumps(collection.EMPTY))
        self.assertEqual(collection.replace(col, collection.parse(COLLECTION)), 4)
        col["games"]["steam:3000103"]["rev"] = {"n": 300, "pct": 92, "at": "2026-10-01"}
        self.assertEqual(collection.replace(col, collection.parse(COLLECTION)), 0)
        self.assertEqual(col["games"]["steam:3000103"]["rev"]["n"], 300)
        self.assertEqual(collection.gem(col["games"]["steam:3000103"]), (0.37, False))
        self.assertEqual(collection.gem(col["games"]["steam:3000101"]), (0.12, True))   # mit Expertenwertung bekannter
        self.assertEqual(collection.gem(col["games"]["epic:abc123def"]), (0.07, True))
        col["games"]["epic:abc123def"]["score"] = 69
        self.assertEqual(collection.gem(col["games"]["epic:abc123def"]), (0.0, True))   # unter 70
        v = collection.view(col)
        self.assertEqual(v["n"], 4)
        self.assertEqual([r["name"] for r in v["games"]], ["Fleet Night", "Harbor Heist", "Quiet Garden", "Sofa Smash"])
        self.assertEqual(v["games"][1]["url"], "https://store.steampowered.com/app/3000101/")
        self.assertIn("Puzzle", v["genres"])

    def test_server_import_export_restore(self):
        store.DATA_DIR = tempfile.mkdtemp()
        data = store.load_data()
        res = server.import_collection(data, COLLECTION, dry=True)
        self.assertEqual(res, {"n": 4, "new": 4, "console": 0})
        self.assertNotIn("collection", data["imports"])
        server.import_collection(data, COLLECTION, dry=False)
        self.assertEqual(data["imports"]["collection"]["n"], 4)
        self.assertEqual(server.import_collection(data, COLLECTION, dry=True)["new"], 0)
        col = store.load_json(collection.FILE, collection.EMPTY)
        self.assertEqual(len(col["games"]), 4)


class TestLibrary(unittest.TestCase):
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
        res = json.loads(self.call("/api/title/delete", {"key": key})[1])
        self.assertNotIn(key, [r["key"] for r in res["wishlist"]])
        self.assertEqual(res["undo"][key]["note"], "bleibt erhalten")
        res = json.loads(self.call("/api/title/restore", {"titles": res["undo"]})[1])
        self.assertIn(key, [r["key"] for r in res["wishlist"]])
        self.assertIsNone(json.loads(self.call("/api/title/delete", {"key": "gibt-es-nicht"})[1])["undo"])
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
        # Keyshops zählen nicht für das PC-Angebot
        self.assertEqual(r["pc_best"], {"price": 14.99, "src": "Steam"})
        self.assertEqual(r["gap_now"], 5.0)
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
        self.assertFalse(any("/game/" in u for u in net.calls))

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
        self.assertEqual(rows["steam:3000101"]["score_src"], "Community")   # unter 50 Rezensionen
        self.assertIn("reviews", store.load_json("sync.json", {})["sources"])
        self.assertIsNone(prices.steam_reviews('{"success": 2}'))
        self.assertEqual(prices.steam_reviews('{"success": 1, "query_summary": {"total_reviews": 0}}')["pct"], None)

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

        def fake_request(url, ua=None, timeout=25, encoding="", headers=None):
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
        # Playnite-Export mit Plattformen: Sammlung und VR-Import lassen reine Konsolenspiele weg
        csv_text = ("Name,Spiel-ID,Schlagwörter,Plattformen\nDeep Dive,CUSA00001_00,VR,Sony PlayStation 4\n"
                    "Sky Garden,3000001,VR,\"PC (Windows), Sony PlayStation 4\"\n")
        self.assertEqual([e["name"] for e in imports.parse_playnite(csv_text)], ["Sky Garden"])
        self.assertEqual([g["name"] for g in collection.parse(csv_text).values()], ["Sky Garden"])
        # Export der PlayStation-Bibliothek ohne Plattformen: an den Kennungen erkannt; die
        # Sammlung bleibt dann stehen
        ps = "Name,Spiel-ID,Schlagwörter\nDeep Dive,CUSA00001_00,VR\nComet Chase,NPWR00002_00,\n"
        self.assertEqual(imports.parse_playnite(ps), [])
        stats = {}
        self.assertEqual(collection.parse(ps, stats=stats), {})
        self.assertEqual(stats, {"console": 2})
        store.DATA_DIR = tempfile.mkdtemp()
        data = store.load_data()
        server.import_collection(data, COLLECTION, dry=False)
        self.assertEqual(server.import_collection(data, ps, dry=False), {"n": 0, "new": 0, "console": 2, "kept": 4})
        self.assertEqual(len(store.load_json(collection.FILE, {})["games"]), 4)

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
                     "low": 9.99, "low_at": "2026-01-01", "at": now},
            "steam": {"price": 14.99, "base": 24.99, "discount": 40, "at": "2020-01-01T00:00:00+00:00"}}
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
        store.save_json(collection.FILE, col)
        data["imports"]["collection"] = {"at": now, "n": len(col["games"]), "new": 0}
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
