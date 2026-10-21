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

from app import imports, library, server, sources, store, titles  # noqa: E402

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

    def test_meta_bad_json(self):
        with self.assertRaises(ValueError):
            imports.parse_meta("{kaputt")


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

    def test_guards(self):
        self.assertEqual(self.call("/api/title", {"key": "x"}, ctype="text/plain")[0], 400)
        self.assertEqual(self.call("/api/state", host="evil.example.com")[0], 421)
        self.assertEqual(self.call("/api/import", {"kind": "nope", "text": ""})[0], 400)
        self.assertEqual(self.call("/api/restore", {"data": {"titles": {"a": {}}}})[0], 400)
        self.assertTrue(server.host_allowed("nas.local:8788"))
        self.assertTrue(server.host_allowed("10.0.0.5"))
        self.assertFalse(server.host_allowed("vr.example.com", extra=""))
        self.assertTrue(server.host_allowed("vr.example.com", extra=".example.com"))


if __name__ == "__main__":
    unittest.main()
