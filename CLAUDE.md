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
- geschätzte oder übernommene Werte sind in der Oberfläche gekennzeichnet (≈, „Tabelle“),
- jede Version mit Tests (`python3 -m unittest tests.test_all`), neuer Nummer in
  `app/sources.py`, aktueller README und aktueller ROADMAP.md,
- alte Datendateien müssen nach einem Update weiter laden.

## Aufbau

- `app/sources.py`: Netzabruf (`request`, `fetch`, nur öffentliche Ziele), `VERSION`
- `app/store.py`: `data.json` im Datenordner (Titel, Importe, Live-Preise), dazu
  `settings.json`, `history.json`, `sync.json` über `load_json`/`save_json`
- `app/prices.py`: Preise aus QuestStoreDB-Seiten, Steam- und gg.deals-Antworten lesen (ohne Netz)
- `app/accounts.py`: Konten ohne Netz lesen und eintragen (Steam Web API, gg.deals-Wunschliste,
  Sharenite)
- `app/sync.py`: Abgleich je Quelle (erst Konten, dann Zuordnung, dann Preise), Zeitplan, Einstellungen, Verbindungstest (siehe
  `docs/abrufe.md`)
- `app/titles.py`: Namen vergleichen, Kennungen aus Links, Titel finden, anlegen, zusammenführen,
  Vorschläge für ähnliche Namen, Steam-ID prüfen, Liste „Zu erledigen“ (`todo`), Suchlinks
- `app/imports.py`: Vergleichstabelle, Playnite-CSV, gg.deals-Wunschliste (CSV), Meta-Bestellungen
  und Meta-Wunschliste (Lesezeichen-JSON oder Text), Meinungen (`docs/meinungen.md`),
  Erkennung der Art (`detect`);
  jeder Import aus Datei oder Text erst als Vorschau; das Lesezeichen „Meta-Käufe lesen“ übergibt
  hinter `#meta=` und übernimmt direkt (Entscheidung 21.10.2026)
- `app/library.py`: Zeilen für Jetzt, Wunschliste und Bibliothek
- `app/server.py`: Webserver und JSON-Schnittstelle
- `app/static/`: Oberfläche, reines JavaScript ohne Build (`index.html`, `style.css`, `js/app.js`);
  Farben, Marken und Klappen nach `docs/oberflaeche.md`
- `tests/test_all.py`: alle Tests, mit `tests/ui_selbsttest.html` (Oberfläche bei 390 px in Chromium); Antworten der Quellen sind erfundene Nachbauten im echten
  Aufbau, keine gespeicherten Seiten

Lokal starten: `python3 -m app.server` (Port 8788, Daten in `./data/`, ignoriert).
