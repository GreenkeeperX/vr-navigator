# VR-Navigator

Deine Spielesammlung über alle Systeme (PC, VR, Konsolen, Retro) und eine VR-Wunschliste mit der
Frage: Wo kaufe ich einen Titel, bei Meta oder bei Steam?

Vorbild und Unterbau ist der [eShopKompass](https://github.com/GreenkeeperX/eshop-kompass):
Python ohne Zusatzpakete, Daten als JSON-Dateien, Oberfläche in reinem JavaScript, gehärteter
Docker-Container.

**Stand 0.11.3:** Wunschliste (VR mit Abgleich gegen die Wunschlisten der Läden, PC als Spiegel der
gg.deals-Wunschliste), Jetzt (was gerade nah am Tief ist), Sammlung über alle Systeme mit Retro-Liste aus dem
ROM-Ordner, Mein Stand, Filter und Vorschläge, Konten (Steam, gg.deals, Sharenite), Live-Preise von QuestStoreDB
(Meta), Steam und gg.deals, Messwerte (Spieler, Updates, Crossbuy, Wertungen) und daraus das Urteil „wo kaufen“.
Was sich je Version geändert hat: [docs/neu.md](docs/neu.md).

## Starten

Jeder Push auf `main` lässt die Tests laufen und baut danach das Image
`ghcr.io/OWNER/vr-navigator:latest` (zusätzlich mit Versionsnummer und kurzem Commit). Die
`docker-compose.yml` zeigt den Betrieb als unprivilegierter Benutzer mit schreibgeschütztem
Dateisystem.

    docker compose up -d

Danach `http://<server>:8788` öffnen. Der Port liegt neben dem des eShopKompass (8787), beide
laufen nebeneinander. Ohne Docker: `python3 -m app.server` (Python 3.12 oder neuer, Daten in `./data/`).

## Einrichten

Unter **Einstellungen**, Karte Einlesen; gelöscht wird beim Einlesen nichts.

- **Konten** liest jeder Abgleich selbst: Steam (SteamID und Schlüssel), gg.deals-Wunschliste (geteilter Link),
  Sharenite, dazu Schlüssel für IGDB, Nexus Mods und IsThereAnyDeal. Schlüssel und Links bleiben auf deinem Server.
- **Meta und gg.deals per Lesezeichen**: „Seite lesen“ einmal in die Lesezeichenleiste ziehen und auf der
  Bestellseite, der Wunschliste oder der gg.deals-Sammlung anklicken. Das Tool bekommt nie ein Passwort.
- **Datei oder Text**: Playnite-Export, Vergleichstabelle, gg.deals-CSV, Meinungen; immer erst als Vorschau.
- **Retro-Sammlung**: Dateiliste deines ROM-Ordners; Region und Sprache kommen aus den Dateinamen, „DE fehlt“ aus
  den Fassungslisten.

Danach ordnet jeder Abgleich die Titel zu und holt Preise und Messwerte. Was das Tool nicht selbst entscheiden
kann, steht unter „Zu erledigen“. Alles Weitere (Zusammenführen, Herkunft, Wunschliste abgleichen, Preise):
[docs/einrichten.md](docs/einrichten.md); welche Quelle wann gefragt wird: [docs/abrufe.md](docs/abrufe.md).

## Nutzung

- **Jetzt**: Wunschtitel, die gerade nah am Tief sind, VR und PC.
- **Wunschliste**: VR mit Urteil „wo kaufen“ (Meta oder Steam), PC mit Preisen je Laden.
- **Sammlung**: alle Spiele je System mit Spalten, Filtern, Suche, Mein Stand und Vorschlägen.
- **Einstellungen**: Zu erledigen, Einlesen, Abgleich, Sicherung und die Statuskarte „Betrieb“.

Einzelheiten zu jeder Ansicht: [docs/ansichten.md](docs/ansichten.md); Farben und Marken:
[docs/oberflaeche.md](docs/oberflaeche.md).

## Sicherung

Unter Einstellungen, Sicherung, drei Knöpfe wie im eShopKompass: „Sicherung herunterladen“ (alle
Titel, Notizen, Zuordnungen und Mein Stand als eine JSON-Datei, dazu die Sammlung,
`collection.json`, und ab 0.8.7 die PC-Wunschliste, `pcwish.json`), „Sicherung einlesen“ und „Abgleichsdaten
herunterladen“ (Stand und Protokoll des Abgleichs, Preisverlauf und Einstellungen ohne Schlüssel und
Konten, zum Nachprüfen; zum Einlesen nicht nötig). Die Sicherung enthält deine Käufe; sie gehört
nicht ins Repository. Schlüssel, Konten und der Preisverlauf (`history.json`) sind nicht darin.

**Einlesen** (ab 0.10.29) zeigt erst, was sich ändert (Titel, Mein Stand, Sammlung, PC-Wunschliste je mit der Zahl jetzt
und in der Sicherung), und spielt erst nach der Bestätigung ein. Übernommen wird feldweise: Was die Sicherung nicht
enthält (etwa die Sammlung in Sicherungen vor 0.4.0 oder Mein Stand vor 0.6.0), bleibt wie es ist; was nicht die
erwartete Form hat oder keinen Namen trägt, wird ausgelassen und in der Vorschau genannt; Zahlen ohne Wert (NaN,
unendlich) lehnt der Server ab. Vorher sichert er den jetzigen Stand.

**Deine Entscheidungen zur Sammlung** (ab 0.11.0: „DE fehlt“ ignorieren, „Liste gilt“, „dieselbe Fassung“,
übernommene Recherchen zu Lenkrad und VR-Mods) stehen in einer eigenen kleinen Datei, `eingaben.json`. Ein Haken schreibt
nur sie, nicht mehr die ganze Sammlung, und kein Import und kein Abgleich kann sie löschen (vorher löschte ein neuer
Playnite-Export die übernommenen Recherchen). Beim ersten Start von 0.11.0 zieht der Server sie aus `collection.json`
um, nach einer Sicherung und mit Prüfung; `collection.json` bleibt dabei unverändert. Einzelheiten in
[docs/sammlung-felder.md](docs/sammlung-felder.md).

**Sicherungen im Datenordner** (ab 0.10.29): Einmal am Tag (und vor jedem Einspielen) legt der Server dieselbe
Sicherung gepackt unter `sicherungen/` im Datenordner ab, es bleiben die 14 neuesten. Einmal im Monat packt er die
jüngste in einen temporären Ordner aus, liest sie wie beim Einspielen und rechnet die Ansichten damit durch
(Wiederherstellungstest); die echten Dateien bleiben dabei unberührt. Ergebnis und letzte Sicherung stehen in
`sicherung.json`.

## Betrieb und Sicherheit

- Der Server nimmt nur JSON-Anfragen bis 1 MB an (Importe und Sicherungen bis 50 MB) und
  antwortet nur unter IP-Adressen, Namen ohne Punkt, Namen im eigenen Netz und Namen aus
  `ALLOWED_HOSTS` (Schutz gegen DNS-Rebinding).
- Fremde Texte (Titel, Notizen, Links) werden in der Oberfläche nie als HTML ausgeführt; Links
  sind nur mit http und https klickbar.
- Abrufe laufen über `sources.request`: ehrliche Kennung, nur öffentliche Ziele, Grenzen für
  Zeit und Größe, Pausen zwischen zwei Abrufen, nach 403, 429 oder Prüfseite 24 Stunden Ruhe für den ganzen Server
  (ab 0.10.29, `RUHE_STUNDEN` ändert die Länge).
- `GET /healthz` (ab 0.10.29) ist das Lebenszeichen für den `HEALTHCHECK` im Image: Version, Datenordner beschreibbar,
  läuft ein Abgleich; es liest keine großen Dateien.
- **Statuskarte „Betrieb“** (ab 0.11.2, unten in den Einstellungen): zugeklappt nur der Gesamtstatus („alles in
  Ordnung“, Hinweise violett, Probleme rot mit Grund), aufgeklappt Quellen, ruhende Server, die letzten Läufe und
  Sperren, letzte Sicherung, letzter Wiederherstellungstest, Daten, Speicher, freier Platz und Version. Der
  **Leistungstest** dort läuft nur auf Klick und nie während eines Abgleichs, in einem eigenen Prozess mit erfundenen
  Daten in einem temporären Ordner, ohne Netz; deine Daten bleiben unberührt (`docs/leistung.md`).
- `AUTO_SYNC=0` schaltet den Zeitplan ab (etwa für einen zweiten Testcontainer).
- **Switch-Sammlung aus dem eShopKompass** (ab 0.7.3, Entscheidung 27.10.2026): Mit `ESHOP_URL`
  (etwa `http://eshop-kompass:8787`) liest jeder Abgleich einmal `ESHOP_URL/api/sammlung` des
  eShopKompass (ab 1.7.16). Das ist die einzige Ausnahme von „nur öffentliche Ziele“: genau diese eine
  Adresse, nur lesend, nur über die Umgebungsvariable im Stack, nie aus der Oberfläche. Am
  einfachsten stehen beide Container in einem gemeinsamen Docker-Netz und der VR-Navigator
  erreicht den eShopKompass über den Containernamen; der eShopKompass nimmt Namen ohne Punkt an.
  `ESHOP_LINK` (optional) ist die Adresse des eShopKompass für Links im Browser. Ohne `ESHOP_URL`
  fragt der VR-Navigator nichts an.
- Die Sammlung rechnet der Server gleich nach dem Start einmal und hält sie bereit, bis sich
  `collection.json`, `data.json` oder die Liste der Rennsimulationen ändert (ab 0.8.14); die Seite lädt
  sie kurz nach dem Öffnen im Hintergrund vor. Der Wechsel in den Reiter wartet dann nicht mehr.
  Ab 0.11.1 rechnet eine Entscheidung nur die Zeilen der betroffenen Spiele neu, die Beschreibung kommt erst beim
  Aufklappen, und unveränderte Antworten schickt der Server nicht noch einmal (ETag); Messung in `docs/leistung.md`.
- Ein Abgleich dauert länger, solange die Warteschlangen (Steam-Details, PCGamingWiki, IGDB) noch gefüllt
  werden; das Protokoll nennt die verbleibenden Läufe. Danach liest jeder Lauf nur noch, was veraltet ist.
- Daten liegen in `data.json` im Datenordner. Eine kaputte Datei bleibt als
  `data.json.kaputt-<Zeit>` liegen und wird im Protokoll des Containers gemeldet.

## Prüfen

    python3 -m unittest tests.test_all

Die Tests nutzen erfundene Beispiele im Format der echten Exporte.

## Dokumentation

- [docs/neu.md](docs/neu.md): was ist neu, je Version
- [docs/einrichten.md](docs/einrichten.md): Einrichten, Zuordnung, Wunschliste abgleichen, Preise
- [docs/ansichten.md](docs/ansichten.md): die Ansichten im Einzelnen
- [docs/abrufe.md](docs/abrufe.md): Quellen, Abrufe, Ruhezeiten, Dateien im Datenordner
- [docs/sammlung-felder.md](docs/sammlung-felder.md): Felder der Sammlung und deine Eingaben
- [docs/leistung.md](docs/leistung.md): Messungen und Leistungstest
- [docs/oberflaeche.md](docs/oberflaeche.md): Regeln für Farben, Marken und Klappen
- [docs/meinungen.md](docs/meinungen.md): Meinungen aus der Recherche
- [docs/entfernt.md](docs/entfernt.md): was aus dem Code entfernt wurde und warum
