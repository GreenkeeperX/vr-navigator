# VR-Navigator

Eine Bibliothek für Meta-Quest-Spiele aus dem Meta Store und von Steam, mit Wunschliste und
der Frage: Wo kaufe ich einen Titel, bei Meta oder bei Steam?

Vorbild und Unterbau ist der [eShopKompass](https://github.com/GreenkeeperX/eshop-kompass):
Python ohne Zusatzpakete, Daten als JSON-Dateien, Oberfläche in reinem JavaScript, gehärteter
Docker-Container.

**Stand 0.3.1:** Bibliothek, Wunschliste, Konten (Steam, gg.deals, Sharenite), Zuordnung aller Titel, Meta-Lesezeichen, Importe und Live-Preise von QuestStoreDB (Meta), Steam
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

Unter **Einstellungen**, Karte Einlesen, stehen drei Wege: Konten liest jeder Abgleich
selbst, Meta kommt per Lesezeichen, alles andere als Datei. Gelöscht wird beim Einlesen nichts.

### Konten (automatisch)

- **Steam:** SteamID (die Zahl oder der Link zum Profil) und ein Steam-Schlüssel
  (kostenlos unter steamcommunity.com/dev/apikey; im Profil müssen die Spieldetails öffentlich
  sein). Dann liest jeder Abgleich deinen Besitz und deine Wunschliste, mit genauen App-IDs;
  „Steam-ID ≈“ entfällt für alles, was dort steht. Ohne Schlüssel nur die Wunschliste. Apps,
  die das Tool noch nicht kennt, prüft es im Store auf VR (höchstens 40 je Abgleich, das
  Ergebnis bleibt gespeichert); übernommen werden nur VR-Apps.
- **gg.deals-Wunschliste:** der Link aus „Wunschliste teilen“. Es zählen Titel, die das Tool
  kennt (Name, früherer Name, Name aus einem Link), und Spiele, die es im Steam-Store unter
  genau diesem Namen als VR-App findet.
- **Sharenite:** der Link zu deinem öffentlichen Profil (Playnite online, mit allen Läden wie
  Steam, GOG, Epic). Übernommen werden Spiele mit einem Schlagwort „VR“ als Besitz am PC, mit
  dem Laden als Marke; gelesen wird höchstens alle 20 Stunden.

Schlüssel und Wunschlisten-Link bleiben auf deinem Server, nicht in der Sicherung, nicht im
Protokoll, nie zurück im Browser.

**Wunschliste aus Quellen:** Ein Titel steht auf der Wunschliste, solange ihn eine Quelle führt
(Wunschliste bei Meta, Steam oder gg.deals) oder du ihn von Hand eingetragen hast. Fehlt er bei
der letzten Quelle, fällt er von deiner Wunschliste; das Protokoll nennt ihn. Titel aus der
Vergleichstabelle tragen keine Quelle und bleiben, bis du sie nimmst. Nimmst du einen Titel von
Hand von der Liste, holt dieselbe Quelle ihn erst zurück, nachdem er dort einmal fehlte. Ist
eine Wunschliste plötzlich leer, obwohl zuletzt Titel darauf standen, gilt die alte weiter.

### Meta per Lesezeichen

Meta hat keine Schnittstelle für die eigenen Käufe, und das Tool bekommt nie dein Passwort.
Stattdessen ein Lesezeichen, wie „Käufe lesen“ im eShopKompass:

1. Den Knopf „Meta lesen“ einmal in die Lesezeichenleiste ziehen (oder „Code kopieren“ und ein
   Lesezeichen von Hand anlegen).
2. Angemeldet die Transaktionen von Meta Pay, die Bestellseite für digitale Produkte oder deine
   Wunschliste im Meta Store öffnen und das Lesezeichen anklicken. Es scrollt selbst (auch in
   Listen mit eigenem Rollbalken), bis alles geladen ist.
3. Im Kasten oben rechts „Im VR-Navigator übernehmen“: Das Tool öffnet sich und übernimmt Käufe
   oder Wunschliste ohne weitere Rückfrage. Seitentext und Links stehen dabei nur in der Adresse
   hinter #, gehen also an keinen Server außer deinem eigenen Browser-Tab; das Tool entfernt sie
   sofort aus der Adresse. Was neu war, steht danach in der Karte.

Käufe: Erkannt werden auf der Bestellseite die Blöcke mit Bestellnummer, bei den Transaktionen
Titel mit Stand und Datum; Menü und Fußzeile fallen weg, erstattete, stornierte und offene Käufe
ebenso. Preise in Euro werden übernommen, andere Währungen nicht. Wunschliste: jeder Link auf
eine Store-Seite ist ein Titel, samt Meta-ID; sie ersetzt, was die Meta-Wunschliste zuletzt
sagte. „Als Datei sichern“ im Kasten lädt die Daten stattdessen herunter.

### Datei oder Text

Ein Feld für jede Datei; das Tool erkennt die Art am Aufbau und zeigt erst eine Vorschau:

- **Vergleichstabelle (CSV):** eine Zeile je Titel mit den Spalten `Spiel`, `meta`
  (Normalpreis im Meta Store), `Bestpreis` (Meta-Tief), `gg.deals best`, `Crossbuy` (Yes/No) und
  in beliebiger Spalte Links zu VRDB, QuestStoreDB, Meta oder Steam (daraus Meta-ID und
  Steam-App-ID). Die Titel landen auf der Wunschliste, solange du sie nicht besitzt.
- **Playnite (CSV):** Spiele mit Schlagwort oder Feature „VR“ und alle, deren Name schon in
  deiner Liste steht, als Besitz am PC. Mit einer Spalte `Quelle` oder `Bibliothek` ist die
  Steam-App-ID sicher, sonst gilt eine Spiel-ID unter 10 000 000 als vermutete Steam-ID („≈“).
- **gg.deals-Wunschliste (CSV)** mit einer Spalte Name und Links auf die geteilte Liste.
- **Datei des Meta-Lesezeichens** oder kopierter Text der Bestellseite.

## Titel zusammenführen

Ein Titel hat bis zu zwei Kennungen: die Meta-ID und die Steam-App-ID. Gleiche Kennung oder
gleicher Name (ohne Groß- und Kleinschreibung, Satzzeichen, ™ und ®) heißt gleicher Titel.

Namen, die sich nur durch eine Klammer am Ende oder ein „VR“ unterscheiden („Moon Rover VR“
und „Moon Rover (Bundle)“), führt das Tool nicht still zusammen. Es zeigt sie unter
Einstellungen, „Derselbe Titel?“: Ein Klick auf einen der beiden Namen führt zusammen und behält diesen Namen,
„Verschieden“ trennt sie dauerhaft. Der andere Name bleibt als zweiter Name bekannt, damit ein
späterer Import den Titel wiederfindet; dasselbe gilt nach dem Umbenennen unter „bearbeiten“.

## Zuordnung und „Zu erledigen“

Jeder Abgleich ordnet auch Titel zu, die nicht auf der Wunschliste stehen, etwa Meta-Käufe:

- **Meta-ID:** Titel ohne Meta-ID sucht das Tool bei QuestStoreDB unter all ihren Namen
  (15 Anfragen je Abgleich, Meta-Käufe zuerst). Es gilt nur ein Treffer mit genau passendem
  Namen. Trägt schon ein anderer Titel diese Meta-ID, gehen beide in einem auf.
- **Steam-ID „≈“:** Eine Steam-ID, die nur aus einem Namen stammt (Playnite, Suche), fragt das
  Tool im Steam-Store nach. Passt der Name und kann die App VR, gilt sie als sicher.
- **Namen lernen:** Die Namen, die Meta und Steam für einen Titel führen, merkt sich das Tool
  als weitere Namen. Spätere Importe und Suchen finden den Titel so auch unter dem anderen
  Namen.

Was offen bleibt, steht in den Einstellungen unter „Zu erledigen“: „Derselbe Titel?“,
Steam-IDs, die die Prüfung nicht bestätigt hat („passt“ oder „falsch“; eine falsche App schlägt
die Suche nicht wieder vor), und Titel, die QuestStoreDB nicht fand. Bundles sind dort als
solche markiert.

Von Hand: unter „bearbeiten“ eine Meta-ID (oder einen Link von Meta, QuestStoreDB oder VRDB) oder Steam-App-ID eintragen. Trägt ein anderer Titel
dieselbe ID, gehen beide in einem auf; Besitz, Wunsch, Links und Notizen bleiben erhalten.
Zusammenführen und Löschen fragen nicht vorher, der Hinweis danach bietet „Rückgängig“.

## Preise abrufen

Unter **Einstellungen**, Abgleich, startet „Jetzt abrufen“ einen Abgleich; danach läuft er nach Zeitplan (Standard
alle 6 Stunden). Erst liest er die eingerichteten Konten, dann Preise für die Wunschtitel, die du
noch nicht besitzt:

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
  „nicht mehr wünschen“ nimmt einen Titel von der Liste (mit Rückgängig).
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
