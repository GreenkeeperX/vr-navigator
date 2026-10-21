# VR-Navigator

Eine Bibliothek für Meta-Quest-Spiele aus dem Meta Store und von Steam, mit Wunschliste und
der Frage: Wo kaufe ich einen Titel, bei Meta oder bei Steam?

Vorbild und Unterbau ist der [eShopKompass](https://github.com/GreenkeeperX/eshop-kompass):
Python ohne Zusatzpakete, Daten als JSON-Dateien, Oberfläche in reinem JavaScript, gehärteter
Docker-Container.

**Stand 0.1:** Bibliothek, Wunschliste und Importe. Preise stammen noch aus der eigenen
Vergleichstabelle; Live-Preise, Crossbuy, Updates und Spielerzahlen folgen (siehe
[ROADMAP](ROADMAP.md)).

## Starten

Jeder Push auf `main` lässt die Tests laufen und baut danach das Image
`ghcr.io/OWNER/vr-navigator:latest` (zusätzlich mit Versionsnummer und kurzem Commit). Die
`docker-compose.yml` zeigt den Betrieb als unprivilegierter Benutzer mit schreibgeschütztem
Dateisystem.

    docker compose up -d

Danach `http://<server>:8788` öffnen. Der Port liegt neben dem des eShopKompass (8787), beide
laufen nebeneinander. Ohne Docker: `python3 -m app.server` (Python 3.10+, Daten in `./data/`).

## Einrichten

Unter **Import** stehen drei Wege. Jeder Import zeigt erst eine Vorschau und speichert erst
nach „übernehmen“.

1. **Vergleichstabelle (CSV):** eine Zeile je Titel. Erkannt werden die Spalten `Spiel`, `meta`
   (Normalpreis im Meta Store), `Bestpreis` (Meta-Tief), `gg.deals best` (bester Preis für die
   Steam-Fassung), `Crossbuy` (Yes/No) und in beliebiger Spalte Links zu VRDB, QuestStoreDB,
   Meta oder Steam. Aus den Links liest das Tool die Meta-ID bzw. Steam-App-ID. Die Titel landen
   auf der Wunschliste, solange du sie nicht besitzt.
2. **Meta-Bestellungen:** Meta hat keine Schnittstelle für die eigenen Käufe, und das Tool
   bekommt nie dein Passwort. Stattdessen:
   1. Den Knopf „Meta-Bestellungen sichern“ in die Lesezeichenleiste ziehen.
   2. Angemeldet die Bestellseite für digitale Produkte öffnen und ganz nach unten scrollen.
   3. Das Lesezeichen anklicken. Es lädt `meta-bestellungen.json` herunter: alle Links und den
      Text der Seite. Es schickt nichts an einen Server.
   4. Die Datei im Tool auswählen, Vorschau prüfen, übernehmen.

   Links auf Store-Seiten liefern Titel samt Meta-ID. Ohne solche Links zählt jede Zeile, die
   nach Entfernen von Datum und Preis noch nach einem Namen aussieht. Kopierter Seitentext geht
   auch: einfügen statt Datei.
3. **Playnite (CSV):** der CSV-Export der Bibliothek. Übernommen werden Spiele mit einem
   Schlagwort oder Feature „VR“ und alle, deren Name schon in deiner Liste steht; sie gelten
   als Besitz am PC. Mit einer Spalte `Quelle` oder `Bibliothek` ist die Steam-App-ID sicher.
   Ohne sie gilt eine Spiel-ID unter 10 000 000 als vermutete Steam-ID und ist mit „≈“
   markiert.

## Titel zusammenführen

Ein Titel hat bis zu zwei Kennungen: die Meta-ID und die Steam-App-ID. Gleiche Kennung oder
gleicher Name (ohne Groß- und Kleinschreibung, Satzzeichen, ™ und ®) heißt gleicher Titel.

Namen, die sich nur durch eine Klammer am Ende oder ein „VR“ unterscheiden („Moon Rover VR“
und „Moon Rover (Bundle)“), führt das Tool nicht still zusammen. Es zeigt sie unter Import,
„Derselbe Titel?“, mit den Knöpfen „Zusammenführen“ und „Verschieden“.

Von Hand: unter „bearbeiten“ eine Meta-ID oder Steam-App-ID eintragen. Trägt ein anderer Titel
dieselbe ID, gehen beide in einem auf; Besitz, Wunsch, Links und Notizen bleiben erhalten.

## Ansichten

- **Wunschliste:** je Titel Meta-Normalpreis, Meta-Tief, gg.deals-Bestpreis und der Abstand
  (Meta-Tief minus gg.deals; Plus heißt Steam günstiger). Die Preise tragen „Tabelle“ und das
  Datum des Imports. Dazu Crossbuy, Besitz auf der anderen Plattform und Links: Meta, VRDB,
  QuestStoreDB, Steam sowie fertige Suchen auf Reddit und Google nach „Quest vs Steam“.
  Was du dort findest, gehört in die Notiz.
- **Bibliothek:** alles, was du besitzt, mit „Meta“, „PC“ oder beidem, Filter und Suche.

## Sicherung

Unter Import, Sicherung: alle Titel, Notizen und Zuordnungen als eine JSON-Datei herunterladen
und wieder einspielen. Die Datei enthält deine Käufe; sie gehört nicht ins Repository.

## Betrieb und Sicherheit

- Der Server nimmt nur JSON-Anfragen bis 1 MB an (Importe und Sicherungen bis 50 MB) und
  antwortet nur unter IP-Adressen, Namen ohne Punkt, Namen im eigenen Netz und Namen aus
  `ALLOWED_HOSTS` (Schutz gegen DNS-Rebinding).
- Fremde Texte (Titel, Notizen, Links) werden in der Oberfläche nie als HTML ausgeführt; Links
  sind nur mit http und https klickbar.
- Spätere Abrufe laufen über `sources.request`: ehrliche Kennung, nur öffentliche Ziele,
  Grenzen für Zeit und Größe.
- Daten liegen in `data.json` im Datenordner. Eine kaputte Datei bleibt als
  `data.json.kaputt-<Zeit>` liegen und wird im Protokoll des Containers gemeldet.

## Prüfen

    python3 -m unittest tests.test_all

Die Tests nutzen erfundene Beispiele im Format der echten Exporte.
