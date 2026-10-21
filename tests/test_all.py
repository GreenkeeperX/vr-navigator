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

from app import imports, library, prices, server, sources, store, sync, titles  # noqa: E402

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
        self.assertEqual(r["pc_best"], {"price": 11.0, "src": "gg.deals Keyshop"})
        self.assertEqual(r["gap_now"], 8.99)
        # Zweiter Lauf: Titelseiten sind frisch, also nur Angebotsliste und Steam
        net.calls.clear()
        sync.run()
        self.assertFalse(any("/game/" in u for u in net.calls))

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
