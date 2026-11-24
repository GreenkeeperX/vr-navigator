# Felder der Sammlung und Nutzereingaben (Bestandsaufnahme für V-2, 0.11.0)

Grundlage: der Code von 0.10.29 (wer schreibt welches Feld), gegengeprüft an den Feldnamen einer echten Sicherung
(nur die Namen der Felder, keine Inhalte und keine Zahlen daraus).

## Schlüssel und Verknüpfungen

| Schlüssel | Herkunft |
|---|---|
| `steam:<App-ID>`, `epic:…`, `gog:…`, `itch:…`, `indiegala:…`, `ubisoft:…`, `xbox:…`, `riot:…` | Playnite-Export (Laden und Kennung) |
| `name:<Name>` | Playnite ohne Kennung |
| `steam:<App-ID>` mit `src` „steamacct“ | Steam-Konto, ohne Playnite-Eintrag |
| `gg:<Slug>` mit `src` „ggcoll“ | gg.deals-Sammlung (Lesezeichen) |
| `pcvr:<Titel>` mit `src` „pcvr“ | VR-Titel am PC ohne Playnite-Eintrag; `from_vr` zeigt auf den Titel in `data.json` |
| `eshop:…` mit `src` „eshop“ | Switch-Sammlung des eShopKompass |
| `retro:<system>:<Name>` mit `src` „retro“ | Retro-Liste (ROM-Ordner) |

Diese Schlüssel halten alles zusammen: **Mein Stand** (`data.json`, `marks`, schon seit 0.6.0 außerhalb der Sammlung)
und ab 0.11.0 die Nutzereingaben (`eingaben.json`) verweisen auf sie. Die Schlüssel sind über erneute Importe stabil
(Laden und Kennung, bei Retro der normierte Name je System); ändert sich der Name eines Spiels ohne Kennung, entsteht ein
neuer Schlüssel, wie bisher.

## Felder je Spiel

**Aus Quellen und Importen** (der Abgleich oder ein Import schreibt sie neu, verloren geht dabei nichts Eigenes):
`name`, `store`, `store_guess`, `id`, `src`, `system`, `mp`, `players`, `genres`, `released`, `added`, `dev`, `pub`,
`score`, `score_src`, `critic`, `stores` (Playnite, Steam-Konto, gg.deals, eShopKompass); `files`, `regions`, `langs`,
`lang_guess`, `flags`, `size`, `tid`, `serial`, `dumps`, `gone` (Retro-Liste); `lr` (libretro), `igdb`, `rev`, `steam`,
`stag`, `play`, `pcgw`, `nexus`, `tdb` (GameTDB), `deku`, `wiki`; `pl`, `mc`, `oc`, `hours`, `usk`, `desc`, `desc_lang`,
`kv`, `ext_mine` (eShopKompass); `mark` und `info` (Altlast, nur noch weitergereicht).

**Eigene Listen, als Import** (stammen von dir, kommen aber über einen Import und werden mit dem nächsten Import
ersetzt): `own` (Zeile deiner Ordner-Liste `…_ordner.csv`), `mine` (deine Wertung in Playnite). Sie bleiben in
`collection.json`; die tägliche Sicherung hält sie.

**Abgeleitet** (aus anderen Feldern berechnet): `de` (Retro: Fassung mit Deutsch, aus den Fassungslisten und `alias`);
beim Aufbau der Ansicht ohne Speichern: Flat2VR-Ports und UEVR-Profile, Geheimtipp-Wert, VR per Mod, Merkmale.

**Nutzereingaben** (nur durch deine Entscheidung in der Oberfläche oder eine bestätigte Antwort auf einen Auftrag):

| Feld | Bedeutung | geändert über |
|---|---|---|
| `de_ign` | „DE fehlt“ ignoriert (Tag) | Zu erledigen, `POST /api/retro/de` |
| `own_ok` | Widersprüche zur Ordner-Liste bestätigt („Liste gilt“) | `POST /api/retro/own`, Auftrag „Retro Genre“ |
| `own_take` | „Quellen gelten“ statt deines Genres | `POST /api/retro/own` (`take`) |
| `alias` | „dieselbe Fassung“: Titel der Fassungsliste gilt für dieses Spiel | `POST /api/retro/near` (`ok`), Auftrag „Retro ähnlich“ |
| `near_no` | „nicht dieselbe Fassung“: Vorschlag kommt nicht wieder | `POST /api/retro/near`, Auftrag „Retro ähnlich“ |
| `r_wheel` | Recherche Lenkrad (Antwort auf einen Auftrag, nach Vorschau übernommen) | Einlesen, Auftrag „Lenkrad“ |
| `r_vrmod` | Recherche VR-Mods (ebenso) | Einlesen, Auftrag „VR-Mods“ |

„Stand übernehmen“ und „behalten“ bei Retro-Spielen, die in der Liste fehlen (`POST /api/retro/gone`), sind keine
dauerhafte Eingabe: „Stand übernehmen“ löscht die Spiele, „behalten“ löscht die Marke `gone`; beides ändert die
Sammlung selbst und bleibt so.

## Befund: Recherchen gingen verloren (behoben in 0.11.0)

`collection.replace` (neuer Playnite-Export) und die Abgleiche, die Einträge neu bauen (`sync_pcvr`, `sync_steam`),
übernahmen nur eine feste Liste von Feldern (`rev`, `steam`, `igdb` …), nicht `r_wheel` und `r_vrmod`. Ein neuer
Playnite-Export löschte also die übernommenen Recherchen zu Lenkrad und VR-Mods (nachgestellt mit erfundenen Daten). Mit
der eigenen Datei für Nutzereingaben kann das nicht mehr passieren: Kein Import und kein Abgleich schreibt sie.

## Ablage ab 0.11.0

- `collection.json` bleibt die große, abgleichsgesteuerte Datei und enthält weiter auch die Nutzerfelder (eine ältere
  Version liest sie so, und ein Rückschritt auf 0.10.28 verliert nichts). Maßgeblich sind sie dort nicht mehr.
- `eingaben.json` (klein): `{"v": 1, "games": {Schlüssel: {Feld: Wert}}, "migrated": {...}}`, nur die Felder der
  Tabelle oben. Beim Lesen der Sammlung (`store.load_json("collection.json")`, also an jeder Stelle im Code) werden die
  Nutzerfelder aus `collection.json` entfernt und die aus `eingaben.json` eingesetzt; die Oberfläche bekommt die
  Sammlung zusammengeführt wie bisher.
- Eine Entscheidung in der Oberfläche schreibt nur `eingaben.json` (wenige KB), nicht mehr die ganze Sammlung. Ausnahme:
  „dieselbe Fassung“ rechnet die Fassung (`de`) sofort neu und schreibt deshalb beides.
- Einträge für Spiele, die es nicht mehr gibt, bleiben in `eingaben.json` stehen: Kommt das Spiel wieder (etwa nach
  einem neuen Export), gilt die Entscheidung wieder.

## Umzug (Migration)

Beim ersten Lesen ohne `eingaben.json`:

1. Sicherung des ganzen Stands unter `sicherungen/` (`…-vor-umbau.json.gz`), nur wenn es eine Sammlung gibt.
2. Alle Nutzerfelder aus `collection.json` sammeln, `eingaben.json` schreiben, wieder lesen und Feld für Feld mit der
   Sammlung vergleichen (Zahl der Spiele, Zahl der Felder, Inhalte).
3. Nur wenn alles übereinstimmt, gilt die neue Datei; das Ergebnis steht unter `migrated` (Zeitpunkt, Version, Zahl
   der Spiele und Felder, Name der Sicherung). Sonst wird sie wieder entfernt, das Protokoll des Containers nennt den
   Grund, und die Sammlung arbeitet weiter wie vorher (Nutzerfelder aus `collection.json`).
4. Gibt es `eingaben.json` schon, passiert nichts (wiederholbar ohne Wirkung). `collection.json` wird beim Umzug nicht
   verändert.

Sicherungen enthalten ab 0.11.0 `eingaben`; ältere Sicherungen ohne diesen Teil bringen die Nutzerfelder in ihrer
Sammlung mit, und das Einspielen übernimmt sie daraus.
