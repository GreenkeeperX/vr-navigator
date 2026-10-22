# VR-Navigator

Eine Bibliothek für Meta-Quest-Spiele aus dem Meta Store und von Steam, mit Wunschliste und
der Frage: Wo kaufe ich einen Titel, bei Meta oder bei Steam?

Vorbild und Unterbau ist der [eShopKompass](https://github.com/GreenkeeperX/eshop-kompass):
Python ohne Zusatzpakete, Daten als JSON-Dateien, Oberfläche in reinem JavaScript, gehärteter
Docker-Container.

**Stand 0.2.7:** Bibliothek, Wunschliste, Importe und Live-Preise von QuestStoreDB (Meta), Steam
und gg.deals. Crossbuy aus VRDB, Updates, Spielerzahlen und das Urteil „wo kaufen“ folgen (siehe
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

Unter **Einstellungen**, Karte Importe, stehen drei Wege. Jeder klappt einzeln und nennt
zugeklappt, wann er zuletzt lief und was er fand. Jeder Import zeigt erst eine Vorschau und speichert erst nach „übernehmen“.

1. **Vergleichstabelle (CSV):** eine Zeile je Titel. Erkannt werden die Spalten `Spiel`, `meta`
   (Normalpreis im Meta Store), `Bestpreis` (Meta-Tief), `gg.deals best` (bester Preis für die
   Steam-Fassung), `Crossbuy` (Yes/No) und in beliebiger Spalte Links zu VRDB, QuestStoreDB,
   Meta oder Steam. Aus den Links liest das Tool die Meta-ID bzw. Steam-App-ID. Die Titel landen
   auf der Wunschliste, solange du sie nicht besitzt.
2. **Meta-Bestellungen:** Meta hat keine Schnittstelle für die eigenen Käufe, und das Tool
   bekommt nie dein Passwort. Stattdessen ein Lesezeichen, wie „Käufe lesen“ im eShopKompass:
   1. Den Knopf „Meta-Käufe lesen“ einmal in die Lesezeichenleiste ziehen (oder „Code kopieren“
      und ein Lesezeichen von Hand anlegen).
   2. Angemeldet die Transaktionen von Meta Pay im Kontenzentrum oder die Bestellseite für
      digitale Produkte öffnen und das Lesezeichen anklicken. Es scrollt selbst (auch in Listen
      mit eigenem Rollbalken), bis alle Käufe geladen sind.
   3. Im Kasten oben rechts „Im VR-Navigator übernehmen“: Das Tool öffnet sich und übernimmt die
      Käufe ohne weitere Rückfrage. Seitentext und Links stehen dabei nur in der Adresse hinter #,
      gehen also an keinen Server außer deinem eigenen Browser-Tab; das Tool entfernt sie sofort
      aus der Adresse. Was neu war, steht danach in der Karte.

   „Als Datei sichern“ im Kasten lädt stattdessen `meta-bestellungen.json` herunter; die Datei
   (oder kopierter Seitentext) geht unten in der Karte, dann erst mit Vorschau.

   Das Lesezeichen funktioniert auch auf der Seite „Transaktionen“ von Meta Pay im
   Kontenzentrum. Erkannt werden auf der Bestellseite die Blöcke mit Bestellnummer, bei den
   Transaktionen Titel mit Stand und Datum; Menü und Fußzeile fallen weg, erstattete,
   stornierte und offene Käufe ebenso. Preise in Euro werden übernommen, andere Währungen
   nicht. Links auf Store-Seiten liefern zusätzlich die Meta-ID; ohne sie sucht der Abgleich
   den Titel per Namen. Kopierter Seitentext geht auch: einfügen statt Datei.
3. **Playnite (CSV):** der CSV-Export der Bibliothek. Übernommen werden Spiele mit einem
   Schlagwort oder Feature „VR“ und alle, deren Name schon in deiner Liste steht; sie gelten
   als Besitz am PC. Mit einer Spalte `Quelle` oder `Bibliothek` ist die Steam-App-ID sicher.
   Ohne sie gilt eine Spiel-ID unter 10 000 000 als vermutete Steam-ID und ist mit „≈“
   markiert.

## Titel zusammenführen

Ein Titel hat bis zu zwei Kennungen: die Meta-ID und die Steam-App-ID. Gleiche Kennung oder
gleicher Name (ohne Groß- und Kleinschreibung, Satzzeichen, ™ und ®) heißt gleicher Titel.

Namen, die sich nur durch eine Klammer am Ende oder ein „VR“ unterscheiden („Moon Rover VR“
und „Moon Rover (Bundle)“), führt das Tool nicht still zusammen. Es zeigt sie unter
Einstellungen, „Derselbe Titel?“: Ein Klick auf einen der beiden Namen führt zusammen und behält diesen Namen,
„Verschieden“ trennt sie dauerhaft. Der andere Name bleibt als zweiter Name bekannt, damit ein
späterer Import den Titel wiederfindet; dasselbe gilt nach dem Umbenennen unter „bearbeiten“.

Von Hand: unter „bearbeiten“ eine Meta-ID oder Steam-App-ID eintragen. Trägt ein anderer Titel
dieselbe ID, gehen beide in einem auf; Besitz, Wunsch, Links und Notizen bleiben erhalten.
Zusammenführen und Löschen fragen nicht vorher, der Hinweis danach bietet „Rückgängig“.

## Preise abrufen

Unter **Einstellungen**, Abgleich, startet „Jetzt abrufen“ einen Abgleich; danach läuft er nach Zeitplan (Standard
alle 6 Stunden). Abgefragt werden nur Wunschtitel, die du noch nicht besitzt:

- **QuestStoreDB** für Meta: Angebotsliste, Titelseiten (Preis, Angebotsende, Tiefstpreis,
  Bewertung, App-Version). Fehlt die Meta-ID, sucht das Tool den Titel per Namen.
- **Steam-Store:** Preise in Euro. Fehlt die Steam-App-ID, sucht das Tool im Store nach genau
  demselben Namen.
- **gg.deals:** bester Preis bei Händlern und in Keyshops. Dafür einen kostenlosen Schlüssel von
  gg.deals unter Einstellungen eintragen. Er bleibt auf dem Server.

Oben steht, wie alt die Preise sind und wann der nächste Abgleich kommt; während eines Laufs
der Schritt mit Fortschritt. „Aktualisieren“ startet einen Lauf sofort.

Die Karte Abgleich zeigt je Quelle Ergebnis und Anzahl der Abrufe, darunter:

- **Verbindung testen:** fragt jede Quelle einmal an und beschreibt, was zurückkommt (Status,
  Server und was die Leser erkennen); „Ergebnis kopieren“ für eine Rückfrage. Speichert nichts.
- **Protokoll** (klappbar, zu außer nach Fehlern): live während des Laufs, zum Kopieren.

Nach einer Sperre (403, 429 oder Prüfseite) ruht eine Quelle 24 Stunden. Probleme stehen als
Hinweis über den Ansichten, jeweils mit „Protokoll öffnen“: noch kein Abgleich, eine ruhende
Quelle, Auffälligkeiten der Selbstprüfung, Fehler im letzten Lauf. Einzelheiten in
[docs/abrufe.md](docs/abrufe.md).

## Ansichten

- **Jetzt:** Wunschtitel, die gerade bei Meta oder Steam reduziert sind, der größte Rabatt
  zuerst, mit Ende des Angebots und „Tiefstpreis“, wenn es bei Meta nie günstiger war.
- **Wunschliste:** Was du bei Meta oder am PC schon besitzt, steht unten in der zugeklappten
  Gruppe „Schon im Besitz“, etwa wenn du ein PC-Spiel zusätzlich für die Quest willst.
  Je Titel Meta jetzt (mit Rabatt und Ende), Meta-Tief, Steam, gg.deals (Händler / Keyshops)
  und der Abstand: Meta jetzt minus günstigstes PC-Angebot jetzt; Plus heißt PC günstiger.
  Jeder Wert trägt Quelle und Zeitpunkt, ältere als zwei Tage sind violett markiert. Ohne Abruf
  gelten die Werte der Tabelle, gekennzeichnet mit „Tabelle“ und Datum (Abstand dort: Meta-Tief
  minus gg.deals). Dazu Crossbuy, Besitz auf der anderen Plattform und Links: Meta, VRDB,
  QuestStoreDB, Steam sowie fertige Suchen auf Reddit und Google nach „Quest vs Steam“.
  Was du dort findest, gehört in die Notiz.
- **Bibliothek:** alles, was du besitzt, in Gruppen „Bei Meta und am PC“, „Nur bei Meta“,
  „Nur am PC“, mit Suche.

Farben haben je eine Bedeutung: Rabatt blau, ★ und „Tiefstpreis“ Gold, Prüfen und Veraltetes
violett, Grün für das, was für einen Kauf spricht (Crossbuy, Meta günstiger), Rot nur für den
Betrag, um den Meta teurer ist. Gruppen und Karten klappen, der Browser merkt sich, was du
zuklappst; „alle aufklappen · alle zuklappen“ steht darüber, eine Suche öffnet alles. Das
Suchfeld leert × oder Esc. Oben rechts: hell, dunkel oder wie das Gerät. Regeln für Änderungen:
[docs/oberflaeche.md](docs/oberflaeche.md).

## Sicherung

Unter Einstellungen, Sicherung: alle Titel, Notizen und Zuordnungen als eine JSON-Datei herunterladen
und wieder einspielen. Die Datei enthält deine Käufe; sie gehört nicht ins Repository. Der
gg.deals-Schlüssel und der Preisverlauf (`history.json`) sind nicht darin.

## Betrieb und Sicherheit

- Der Server nimmt nur JSON-Anfragen bis 1 MB an (Importe und Sicherungen bis 50 MB) und
  antwortet nur unter IP-Adressen, Namen ohne Punkt, Namen im eigenen Netz und Namen aus
  `ALLOWED_HOSTS` (Schutz gegen DNS-Rebinding).
- Fremde Texte (Titel, Notizen, Links) werden in der Oberfläche nie als HTML ausgeführt; Links
  sind nur mit http und https klickbar.
- Abrufe laufen über `sources.request`: ehrliche Kennung, nur öffentliche Ziele, Grenzen für
  Zeit und Größe, Pausen zwischen zwei Abrufen, 24 Stunden Ruhe nach 403, 429 oder Prüfseite.
- `AUTO_SYNC=0` schaltet den Zeitplan ab (etwa für einen zweiten Testcontainer).
- Daten liegen in `data.json` im Datenordner. Eine kaputte Datei bleibt als
  `data.json.kaputt-<Zeit>` liegen und wird im Protokoll des Containers gemeldet.

## Prüfen

    python3 -m unittest tests.test_all

Die Tests nutzen erfundene Beispiele im Format der echten Exporte.
