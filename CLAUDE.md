# Hinweise für die Arbeit am Repository

**Dieses Repository ist öffentlich.** Vor jedem Commit und jedem Push prüfen, dass
nirgends private Angaben stehen: nicht im Code, in Kommentaren, Tests, Beispielen, in der
README, der ROADMAP.md oder in Commit-Texten.

Nicht hinein gehören:
- Namen von Personen, auch Vornamen und Benutzernamen. Stattdessen „(Entscheidung 21.10.2026)“
  oder ohne Herkunft,
- Links oder Kennungen von Profilen, Sammlungen, Wunschlisten und Tabellen,
  API-Schlüssel,
- Hostnamen, interne Domains, IP-Adressen, Zugangsdaten,
- eigene Daten: Käufe, Bestellungen, eigene Listen und Exporte, auch einzelne Titel daraus.
  Testdaten sind erfunden.

Prüfung vor dem Push, zum Beispiel:

    git diff origin/main --stat
    git grep -n -i -E "profiles/[0-9]{10,}|share/[A-Za-z0-9-]{10,}|spreadsheets/d/|192\.168\.|@[a-z0-9-]+\.(de|com)"

Ein Treffer bei Namen fällt mit grep nicht sicher auf. Deshalb den eigenen Diff vor dem
Push lesen.

Weitere feste Regeln (wie im eShopKompass):
- nur die Python-Standardbibliothek, keine neuen Abhängigkeiten,
- Quellen schonend abrufen: Pausen, Abbruch bei 403 und 429, ehrliche Kennung,
- die Härtung des Containers bleibt,
- geschätzte oder übernommene Werte sind in der Oberfläche gekennzeichnet (violett, „Tabelle“; kein „≈“, Entscheidung 02.11.2026),
- jede Version mit Tests (`python3 -m unittest tests.test_all`), neuer Nummer in
  `app/sources.py`, aktueller README und aktueller ROADMAP.md,
- alte Datendateien müssen nach einem Update weiter laden.

## Aufbau

- `app/sources.py`: Netzabruf (`request`, `fetch`, nur öffentliche Ziele), `VERSION`
- `docs/entfernt.md`: was aus dem Code entfernt wurde, warum und wie geprüft (ab 0.10.29); nichts auf Verdacht entfernen
- `app/ruhe.py`: ab 0.10.29 Ruhezeit je Server nach 403, 429 oder Prüfseite (`block`, `until`, `active`), in `ruhe.json`,
  gilt für Abgleich und Verbindungstest; Länge `RUHE_STUNDEN` (Vorgabe 24)
- `app/eingaben.py`: ab 0.11.0 Nutzereingaben der Sammlung (`de_ign`, `own_ok`, `own_take`, `alias`, `near_no`, `r_wheel`,
  `r_vrmod`) in `eingaben.json`; beim Lesen von `collection.json` eingesetzt (`store.LOAD_HOOKS`), Entscheidungen schreiben
  nur sie (`save`), Umzug beim ersten Lesen (`migrate`); Felder und Gründe in `docs/sammlung-felder.md`
- `app/betrieb.py`: ab 0.11.2 Statuskarte „Betrieb“ (`view`, Gesamtstatus `overall`) und Leistungstest im eigenen
  Prozess mit temporärem Datenordner (`start_test`, Ergebnisse in `leistung.json`); `GET /api/betrieb`, `POST /api/leistung`
- `app/leistung.py`: ab 0.11.1 erfundene Sammlung im echten Aufbau (`synthetic`) und Messung im temporären
  Datenordner (`measure`); Ergebnisse und Verfahren in `docs/leistung.md`
- `app/sicherung.py`: ab 0.10.29 Sicherungen im Datenordner (`make`, `daily`), feldweises Einspielen mit Vorschau
  (`plan`, `restore`), monatlicher Wiederherstellungstest im temporären Ordner (`check`), Stand in `sicherung.json`
- `app/store.py`: `data.json` im Datenordner (Titel, Importe, Live-Preise), dazu
  `settings.json`, `history.json`, `sync.json` über `load_json`/`save_json`
- `app/prices.py`: Preise aus QuestStoreDB-Seiten, Steam- und gg.deals-Antworten lesen (ohne Netz)
- `app/accounts.py`: Konten ohne Netz lesen und eintragen (Steam Web API, gg.deals-Wunschliste,
  Sharenite)
- `app/besitz.py`: ab 0.10.2 Besitz mit zweiter Quelle (Steam-Konto, Sharenite, gg.deals-Sammlung, Meta-Käufe),
  Widersprüche für „Zu erledigen“ (`check`), ohne Netz
- `app/sync.py`: Abgleich je Quelle (erst Konten, dann Zuordnung, ab 0.10.21 dann Stränge (ab 0.10.22 elf) gleichzeitig mit Pausen je Server, `HOSTS`), Zeitplan, Einstellungen, Verbindungstest (siehe
  `docs/abrufe.md`)
- `app/titles.py`: Namen vergleichen, Kennungen aus Links, Titel finden, anlegen, zusammenführen,
  Vorschläge für ähnliche Namen, Steam-ID prüfen, Liste „Zu erledigen“ (`todo`), Suchlinks
- `app/imports.py`: Vergleichstabelle, Playnite-CSV, gg.deals-Wunschliste (CSV), ab 0.9.9 gg.deals-Sammlung
  (Lesezeichen, Launcher je Karte, `import_ggcoll`), Meta-Bestellungen
  und Meta-Wunschliste (Lesezeichen-JSON oder Text), Meinungen (`docs/meinungen.md`),
  Erkennung der Art (`detect`);
  jeder Import aus Datei oder Text erst als Vorschau; das Lesezeichen „Meta-Käufe lesen“ übergibt
  hinter `#meta=` und übernimmt direkt (Entscheidung 21.10.2026)
- `app/retro.py`: Retro-Liste (Dateinamen aus dem ROM-Ordner oder CSV) zu einem Eintrag je Spiel und
  System, Region und Sprache aus No-Intro- und Redump-Namen, „nicht mehr in der Liste“; Fassungslisten
  (libretro-DAT, Retool) zu Gruppen und „DE fehlt“ je Spiel (`build_index`, `match`), 3DS über den
  Produktcode, ähnliche Namen zum Bestätigen (`similar`, `near_list`, `settle_near`); ab 0.8.8 Spielinfos der
  libretro-database (`parse_meta`, `meta_for`, `mark_meta`) und deine Ordner-Listen `…_ordner.csv`
  (`parse_folder_list`, `apply_folder_lists`, Widersprüche `own_list`, `settle_own`)
- `app/collection.py`: ganze Sammlung je System für die Sammlung (`collection.json`) aus dem Playnite-Export
  (Zeilen der Oberfläche: `view`, ab 0.11.1 je Spiel `row` und nur einige `rows`)
  und ab 0.8.9 deinen VR-Titeln am PC ohne Playnite-Eintrag (`sync_pcvr`), Steam-Konto (`sync_steam`),
  gg.deals-Sammlung (`sync_gg`),
  Merkmale (Mehrspieler, Spielerzahl, Genre-Gruppen, Wertung), Geheimtipp-Wert
- `app/muster.py`: Preismuster aus dem eigenen Verlauf (üblicher Steam-Rabatt je Alter, Monate mit vielen Angeboten),
  Marke „üblich −x %“ (`stats`, `usual`, `annotate`), ab 0.10.2 Steam-Angebote je Spiel (`rhythm`), ohne Netz und ohne feste Zahlen
- `app/gametdb.py`: ab 0.10.13 GameTDB (GameCube, Wii, DS, 3DS, PS3) ohne Netz: gepackte XML lesen (`parse`), Spiel über
  Spiel-ID oder Namen finden (`find`), am Spiel als `tdb` ablegen (`mark`); abgerufen in `sync._gametdb`
- `app/deku.py`: ab 0.10.14 DekuDeals ohne Netz: Suche (`search_slug`), Kasten „Details“ der Spielseite (`parse`),
  passt zum Spiel (`fits`: Name und Plattform), für welche Spiele (`wanted`); abgerufen in `sync._deku`, in der Sammlung
  `collection.merge_deku`
- `app/wiki.py`: ab 0.10.16 Wikidata und deutsche Wikipedia ohne Netz: Suche (`candidates`), Einträge (`entities`), Treffer
  über Plattform oder Jahr (`pick`), Einleitungen (`extracts`), am Spiel als `wiki` (`compact`); abgerufen in `sync._wiki`,
  in der Sammlung `collection.merge_wiki`
- `app/aufgaben.py`: ab 0.10.24 Aufträge zu den Listen unter „Zu erledigen“ (`items`, `task`, `tasks`) und ihre Antworten
  (`parse`, `apply`, erst als Vorschau); eingelesen in `server.import_todo`; ab 0.10.26 auch Lenkrad und VR-Mods der Sammlung
  (`r_wheel`, `r_vrmod` am Spiel in `collection.json`)
- `app/flat2vr.py`: ab 0.10.28 Flat2VR Index (Ports) und UEVR Hub (Profile) ohne Netz: lesen (`parse_ports`, `parse_uevr`),
  vorsichtig über den Namen zuordnen (`assign`), weggefallene Einträge (`removed`); abgerufen in `sync._flat2vr` mit ETag,
  in der Sammlung `collection.f2vr_match`
- `app/igdb.py`: IGDB ohne Netz (Anfragen bauen, Antworten lesen, Steam-Spiele gebündelt über die Steam-ID); abgerufen in `sync._igdb`
- `app/itad.py`: IsThereAnyDeal ohne Netz: Preise je offiziellem Laden für die PC-Wunschliste; abgerufen in `sync._itad`
- `app/mods.py`: VR per Mod ohne Netz: PCGamingWiki („VR support“) und Nexus Mods; abgerufen in `sync._pcgw`, `sync._nexus`
- `app/probes.py`: Proben neuer Quellen für den Verbindungstest (`run`), nur dort; ab 0.10.29 auch hier mit Ruhezeit je Server
- `app/trend.py`: Steam-Trend (Rezensionen der letzten 30 Tage gegen alle) und Pflege (letztes Update), ohne Netz
- `app/verlauf.py`: Preisverlauf je Titel für `GET /api/verlauf` (Normalpreis, Tief, übliche Angebote), ohne Netz
- `app/wheel.py`: Sim-Racing ohne Netz: Steam-Schlagwörter (Hinweis), Liste der Rennsimulationen (Bestätigung)
- `app/pcwish.py`: PC-Wunschliste (`pcwish.json`), Spiegel der gg.deals-Wunschliste; Zeilen mit Preisen und ab 0.8.11
  Spielinfos nach den Regeln der Sammlung (`info`); abgerufen in `sync._pcwish` und `sync._pcwish_info`
- `app/lists.py`: Wunschliste abgleichen (gekauft und noch gewünscht, im Tool entfernt, nur
  aus der Tabelle), Aktionen für ganze Gruppen, lange nicht gelesene Lesezeichen-Listen
- `app/library.py`: Zeilen für Jetzt, Wunschliste und den Reiter VR der Sammlung, ab 0.10.2 Pakete gegen Einzelpreise (`bundle_deals`)
- `app/server.py`: Webserver und JSON-Schnittstelle; ab 0.11.1 HTTP/1.1, ETag für Sammlung und Zustand, Sammlung
  ohne Beschreibung (`slim`, `POST /api/details`), Zeilen nach einer Entscheidung (`decided`, `colview_patch`)
- `app/static/`: Oberfläche, reines JavaScript ohne Build (`index.html`, `style.css`, `js/app.js`);
  Farben, Marken und Klappen nach `docs/oberflaeche.md`
- `tests/test_all.py`: alle Tests, mit `tests/ui_selbsttest.html` (Oberfläche bei 390 px in Chromium); Antworten der Quellen sind erfundene Nachbauten im echten
  Aufbau, keine gespeicherten Seiten

Lokal starten: `python3 -m app.server` (Port 8788, Daten in `./data/`, ignoriert).
