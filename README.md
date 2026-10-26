# VR-Navigator

Eine Bibliothek für Meta-Quest-Spiele aus dem Meta Store und von Steam, mit Wunschliste und
der Frage: Wo kaufe ich einen Titel, bei Meta oder bei Steam?

Vorbild und Unterbau ist der [eShopKompass](https://github.com/GreenkeeperX/eshop-kompass):
Python ohne Zusatzpakete, Daten als JSON-Dateien, Oberfläche in reinem JavaScript, gehärteter
Docker-Container.

**Stand 0.5.4:** Bibliothek, Wunschliste mit Abgleich gegen die Wunschlisten der Läden, Entdecken (die ganze PC-Sammlung filtern und Vorschläge ziehen), Konten (Steam, gg.deals, Sharenite), Zuordnung aller Titel, Bestpreis über beide Läden, Meinungen aus der Recherche, Meta-Lesezeichen, Importe und Live-Preise von QuestStoreDB (Meta), Steam
und gg.deals, dazu Gemessenes: Steam-Spieler und -Updates, Crossbuy, Version und Meta-Wertung von
VRDB. Das Urteil „wo kaufen“ folgt (siehe [ROADMAP](ROADMAP.md)).

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
  „Steam-ID ≈“ entfällt für alles, was dort steht. Ohne Schlüssel nur die Wunschliste. Pflegst
  du am PC nur die gg.deals-Wunschliste, schalte „Steam-Wunschliste lesen“ ab: Steam zählt dann
  nicht mehr als Quelle, Hinweise und Links zum Nachtragen nennen nur noch gg.deals, und ein
  Wunsch, der nur von Steam kam, bleibt und steht unter „Wunschliste abgleichen“. Apps,
  die das Tool noch nicht kennt, prüft es im Store auf VR (höchstens 40 je Abgleich, das
  Ergebnis bleibt gespeichert); übernommen werden nur VR-Apps.
- **gg.deals-Wunschliste:** der Link aus „Wunschliste teilen“. Es zählen Titel, die das Tool
  kennt (Name, früherer Name, Name aus einem Link), und Spiele, die es im Steam-Store unter
  genau diesem Namen als VR-App findet. Zeigt gg.deals dem Server eine Prüfseite (Cloudflare),
  liest das Tool die Liste mit dem Lesezeichen „Seite lesen“ auf gg.deals und versucht es nach
  sieben Tagen wieder selbst, sofort, wenn du den Link neu speicherst. Unbekannte Namen sucht der nächste
  Abgleich nach.
- **Sharenite:** der Link zu deinem öffentlichen Profil (Playnite online, mit allen Läden wie
  Steam, GOG, Epic). Übernommen werden Spiele mit einem Schlagwort „VR“ als Besitz am PC, mit
  dem Laden als Marke; gelesen wird höchstens alle 20 Stunden. Spiele nur für Konsolen (alle
  Plattformen PlayStation, Xbox oder Nintendo, oder Laden PlayStation ohne Plattform) zählen
  nicht als Besitz am PC; gibt es dasselbe Spiel auch für den PC, zählt dieser Eintrag.

Schlüssel und Wunschlisten-Link bleiben auf deinem Server, nicht in der Sicherung, nicht im
Protokoll, nie zurück im Browser.

**Wunschliste aus Quellen:** Ein Titel steht auf der Wunschliste, solange ihn eine Quelle führt
(Wunschliste bei Meta, Steam oder gg.deals) oder du ihn von Hand eingetragen hast. Fehlt er bei
der letzten Quelle, fällt er von deiner Wunschliste; das Protokoll nennt ihn. Titel aus der
Vergleichstabelle tragen keine Quelle und bleiben, bis du sie nimmst. Nimmst du einen Titel von
Hand von der Liste, holt dieselbe Quelle ihn erst zurück, nachdem er dort einmal fehlte. Ist
eine Wunschliste plötzlich leer, obwohl zuletzt Titel darauf standen, gilt die alte weiter.

### Meta und gg.deals per Lesezeichen

Meta hat keine Schnittstelle für die eigenen Käufe, gg.deals lässt den Server nicht an die
Wunschliste, und das Tool bekommt nie dein Passwort. Stattdessen ein Lesezeichen, wie „Käufe
lesen“ im eShopKompass:

1. Den Knopf „Seite lesen“ einmal in die Lesezeichenleiste ziehen (oder „Code kopieren“ und ein
   Lesezeichen von Hand anlegen).
2. Angemeldet die Transaktionen von Meta Pay, die Bestellseite für digitale Produkte oder deine
   Wunschliste im Meta Store öffnen und das Lesezeichen anklicken. Es scrollt selbst (auch in
   Listen mit eigenem Rollbalken), bis alles geladen ist. Auf deiner Wunschliste bei gg.deals
   liest es alle Seiten bis zur höchsten Seitenzahl der Seitenleiste (höchstens 30, mit kurzer
   Pause dazwischen). Es nimmt auch Pakete, Bundles und DLC mit; übernommen werden nur Spiele,
   der Rest steht mit Zahl und Namen im Ergebnis. Unbekannte Namen daraus sucht der Abgleich bei
   Steam nach, 40 je Lauf.
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

Ein Feld für jede Datei; das Tool erkennt die Art am Aufbau und zeigt erst eine Vorschau mit
der erkannten Art. Liegt es daneben, wählst du die Art unter „Art“. Passt gar nichts sicher, liest
es den Text als Meta-Bestellseite; findet es dort keinen einzigen Preis, meldet es das, statt
still nichts zu übernehmen:

- **Vergleichstabelle (CSV):** eine Zeile je Titel mit den Spalten `Spiel`, `meta`
  (Normalpreis im Meta Store), `Bestpreis` (Meta-Tief), `gg.deals best`, `Crossbuy` (Yes/No) und
  in beliebiger Spalte Links zu VRDB, QuestStoreDB, Meta oder Steam (daraus Meta-ID und
  Steam-App-ID). Die Titel landen auf der Wunschliste, solange du sie nicht besitzt.
- **Playnite (CSV):** Spiele mit Schlagwort oder Feature „VR“ und alle, deren Name schon in
  deiner Liste steht, als Besitz am PC. Mit einer Spalte `Quelle` oder `Bibliothek` ist die
  Steam-App-ID sicher (ebenso, wenn unter `Kategorien` ein bekannter Laden wie Steam, GOG oder
  Epic steht), sonst gilt eine Spiel-ID unter 10 000 000 als vermutete Steam-ID („≈“). Dieselbe
  Datei füllt außerdem die ganze Sammlung für **Entdecken** mit allen Spielen außer den
  versteckten; ein neuer Export ersetzt sie. Spiele nur für Konsolen bleiben draußen, in
  Bibliothek und Sammlung: erkannt an der Spalte `Plattformen` (steht auch ein PC dabei, zählen
  sie) oder, ohne sie, an Kennungen der PlayStation-Bibliothek wie `CUSA01234_00`. Ein Export nur
  der PlayStation-Bibliothek ändert daher nichts; die Sammlung bleibt dann stehen.
- **gg.deals-Wunschliste (CSV)** mit einer Spalte Name und Links auf die geteilte Liste.
- **Datei des Meta-Lesezeichens** oder kopierter Text der Bestellseite.
- **Meinungen (JSON)** aus einer Recherche auf Reddit und im Web: je Titel Kurzfazit, bessere
  Fassung, Mehrspieler, Pflege, Crossbuy, Crossplay, Komfort, Warnungen und Quellen. Sie stehen
  unter dem Titel als zugeklappte Zeile „Recherche, Datum: …“; Crossbuy daraus trägt „≈“.
  Crossbuy heißt: ein Kauf im Meta Store gilt für Quest und PC-VR im Meta Store; Steam gehört
  nie dazu. Nennt die Begründung Steam, Crossplay oder nur deine Zuordnung, verwirft der Import
  den Wert und sagt es in der Vorschau. Aufbau
  in [docs/meinungen.md](docs/meinungen.md).

## Titel zusammenführen

Ein Titel hat bis zu zwei Kennungen: die Meta-ID und die Steam-App-ID. Gleiche Kennung oder
gleicher Name (ohne Groß- und Kleinschreibung, Satzzeichen, ™ und ®) heißt gleicher Titel.

Namen, die sich nur durch eine Klammer am Ende oder ein „VR“ unterscheiden („Moon Rover VR“
und „Moon Rover (Bundle)“), führt das Tool nicht still zusammen. Es zeigt sie unter
Einstellungen, „Derselbe Titel?“: Ein Klick auf einen der beiden Namen führt zusammen und behält diesen Namen,
„Verschieden“ trennt sie dauerhaft. Der andere Name bleibt als zweiter Name bekannt, damit ein
späterer Import den Titel wiederfindet; dasselbe gilt nach dem Umbenennen unter „bearbeiten“.

## Herkunft und Bundles

Jeder Titel weiß, woher er kommt: Vergleichstabelle mit Zeile, Playnite, Meta-Käufe,
Meta-, Steam- oder gg.deals-Wunschliste, Steam-Besitz, Sharenite, von Hand oder ein Bundle.
Das steht unter „bearbeiten“ und bei jedem Fall unter „Zu erledigen“. Titel aus der Zeit vor
0.3.4 zeigen eine vermutete Herkunft („≈“), abgeleitet aus Besitz, Wunschquellen und dem
Zeitpunkt der Importe.

Bei einem Bundle trägst du unter „bearbeiten“ die Spiele darin ein, je Feld ein Name oder Link,
„+ Spiel“ fügt ein Feld an. Jedes Spiel wird ein eigener Titel mit dem Bundle als Herkunft;
besitzt du das Bundle, besitzt du die Spiele auf derselben Seite. Ein Bundle mit Inhalt fällt
aus „Ohne Meta-ID“ heraus.

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

## Wunschliste abgleichen

Deine Wünsche führt das Tool; die Wunschlisten bei Meta, Steam und gg.deals sind Spiegel, die
der Abgleich liest (Steam und gg.deals selbst, Meta per Lesezeichen). Steht ein Titel auf einer
davon, ist er gewünscht; fehlt er überall, fällt er von der Liste. Was danach nicht
zusammenpasst, steht unter „Zu erledigen“, je Gruppe mit einer Aktion für alle:

- **Gekauft, noch auf der Wunschliste:** du besitzt ihn (Meta-Käufe, Steam-Konto, Sharenite,
  Playnite). Links führen zur Liste im Laden, wo er noch steht; „von der Wunschliste“ nimmt ihn
  im Tool weg, „behalten“, wenn du die Fassung im anderen Laden willst.
- **Im Tool entfernt, im Laden noch gewünscht:** der Hinweis geht, sobald der Laden ihn nicht
  mehr führt; „wieder wünschen“ holt ihn zurück.
- **Fehlt auf einer Laden-Wunschliste:** gewünscht, aber in einem Laden, der den Titel führt,
  nicht auf deiner Wunschliste (Meta: Meta-ID und die Meta-Wunschliste wurde gelesen; PC:
  Steam-ID und weder auf der Steam- noch auf der gg.deals-Wunschliste). „+ Meta“, „+ Steam“ und
  „+ gg.deals“ öffnen die Seite, auf der du ihn mit einem Klick einträgst (bei gg.deals die
  Spielseite oder die Suche); der nächste Abgleich ordnet ihn dann zu. „so lassen“, wenn du nur
  eine Fassung willst.
- **Nur aus der alten Tabelle:** der Wunsch steht auf keiner Wunschliste. Die Tabelle wird nicht
  mehr gepflegt; am schnellsten trägst du ihn mit denselben Links im Laden ein, „behalten“ führt
  ihn im Tool weiter (von Hand), „entfernen“ nimmt ihn weg. Hat das Tool die Meta-Wunschliste noch
  nie (oder vor über 30 Tagen) gelesen, steht davor der Hinweis, sie zuerst zu lesen: was dort
  steht, ordnet es selbst zu. Die Seite deiner Wunschliste merkt es sich beim ersten Lesen und
  verlinkt sie dann.

In der Wunschliste weist eine Zeile oben darauf hin. Wie im eShopKompass trägt jede Karte eine
Marke, wenn der Titel auf keiner Laden-Wunschliste steht („auf keiner Laden-Wunschliste“, mit
„· Tabelle“, wenn er nur aus der Tabelle kommt) oder in einem Laden fehlt („fehlt auf Wunschliste:
Meta“), daneben die Links zum Eintragen. Die Klappe jeder Karte nennt, woher der Wunsch kommt.

Beim Lesen der Meta-Wunschliste zählen nur Links auf Apps (keine Rubriken wie „Startseite“), der
Name kommt ohne Marke („Beliebter Artikel“), Wertung und Rubriken aus der Kachel. Namen aus
einem früheren Lesen mit Wertung darin berichtigt das nächste Lesen, und Einträge, die nur eine
frühere Meta-Wunschliste angelegt hat und die dort fehlen, fallen weg. Jede Aktion
lässt sich im Hinweis danach zurücknehmen. Das Tool schreibt in keinen Laden.

Von Hand: unter „bearbeiten“ eine Meta-ID (oder einen Link von Meta, QuestStoreDB oder VRDB) oder Steam-App-ID eintragen. Trägt ein anderer Titel
dieselbe ID, gehen beide in einem auf; Besitz, Wunsch, Links und Notizen bleiben erhalten.
Zusammenführen und Löschen fragen nicht vorher, der Hinweis danach bietet „Rückgängig“.

## Preise abrufen

Unter **Einstellungen**, Abgleich, startet „Jetzt abrufen“ einen Abgleich; danach läuft er nach Zeitplan (Standard
alle 6 Stunden; die Zeile „automatisch alle … Stunden“ oben in der Karte speichert sofort).
Die Einstellungen folgen dem Weg der Daten: „Zu erledigen“ (nur wenn etwas offen ist),
Einlesen, Abgleich, Sicherung. Erst liest er die eingerichteten Konten, dann Preise für die Wunschtitel, die du
noch nicht besitzt:

- **QuestStoreDB** für Meta: Angebotsliste, Titelseiten (Preis, Angebotsende, Preisverlauf,
  Bewertung, App-Version). Fehlt die Meta-ID, sucht das Tool den Titel per Namen.
- **Steam-Store:** Preise in Euro. Fehlt die Steam-App-ID, sucht das Tool im Store nach genau
  demselben Namen.
- **gg.deals:** bester Preis bei Händlern und in Keyshops. Dafür einen kostenlosen Schlüssel von
  gg.deals unter Einstellungen, Einlesen, „Konten und Schlüssel“ eintragen. Er bleibt auf dem Server.

Oben steht, wie alt die Preise sind und wann der nächste Abgleich kommt; während eines Laufs
der Schritt mit Fortschritt. „Aktualisieren“ startet einen Lauf sofort.

Die Karte Abgleich zeigt je Quelle Ergebnis und Anzahl der Abrufe, darunter:

- **Verbindung testen:** fragt jede Quelle einmal an und beschreibt, was zurückkommt (Status,
  Server und was die Leser erkennen); „Ergebnis kopieren“ für eine Rückfrage. Speichert nichts.
- **Protokoll** (klappbar, zu außer nach Fehlern): live während des Laufs, zum Kopieren. Die
  zweite Zeile fasst zusammen („Kurz: 4 Wunschtitel im Angebot, 2 günstiger; alles glaubhaft“).
  Warteschlangen nennen die Läufe bis zum Ende („noch etwa 12 Läufe“), Cent-Schwankungen unter
  0,50 € und 5 % stehen nur als Zahl da, Apps ohne Spielerzahl bei Steam ebenso.

Nach einer Sperre (403, 429 oder Prüfseite) ruht eine Quelle 24 Stunden. Probleme stehen als
Hinweis über den Ansichten, jeweils mit „Protokoll öffnen“: noch kein Abgleich, eine ruhende
Quelle, Auffälligkeiten der Selbstprüfung, Fehler im letzten Lauf. Einzelheiten in
[docs/abrufe.md](docs/abrufe.md).

## Ansichten

- **Jetzt:** Wunschtitel, die gerade bei Meta oder Steam reduziert sind und dabei nah am
  Bestpreis beider Läden liegen, mit den Grenzen des eShopKompass: „kaufen“ bis 2 % oder 0,50 €
  darüber (unter 2 € Bestpreis nur die 2 %), „gut“ bis 15 % oder 2 € darüber. Die übrigen
  Angebote stehen zugeklappt darunter („Reduziert, aber noch weit über dem Bestpreis“). Sortiert
  nach Nähe zum Bestpreis, nach Rabatt oder Wertung, mit Ende des Angebots. Jeder Titel als Karte wie in der
  Wunschliste.
- **Wunschliste:** Was du bei Meta oder am PC schon besitzt, steht unten in der zugeklappten
  Gruppe „Schon im Besitz“, etwa wenn du ein PC-Spiel zusätzlich für die Quest willst.
  „nicht mehr wünschen“ (in der Klappe unter der Karte) nimmt einen Titel von der Liste (mit Rückgängig);
  „+ Titel“ in der Werkzeugzeile trägt einen von Hand ein.
  Je Titel eine Karte mit festem Aufbau:
  - **Kopf:** Name, Crossbuy-Marke mit Herkunft (siehe unten), Besitz, Bundle, „Steam-ID ≈“.
  - **Preise:** zwei feste Felder, Meta links, Steam rechts; fehlt ein Laden, bleibt sein Feld grau
    mit „kein Preis“. Je Feld Preis, Rabatt und Ende, darunter der Abstand zum **Bestpreis**
    beider Läden, dem niedrigsten Preis von Meta oder Steam der letzten 24 Monate: rot „+3,50 € über
    Bestpreis“ mit Betrag, Laden und Prozent (jeder Aufpreis rot), gold „★ Bestpreis“
    (bis 2 % darüber). Kommt der Bestpreis aus dem anderen Laden, steht klein darunter der
    Tiefstpreis des Ladens selbst („Steam-Tief 12 €“ oder „jetzt“); so sieht Steam nicht golden
    aus, wenn Meta einmal günstiger war. Dazu „übliches Angebot“ (so tief wie in mindestens zwei
    getrennten Angeboten). Für Meta reicht der Verlauf von QuestStoreDB Jahre
    zurück, für Steam zählt der eigene Verlauf; ohne jede Preisänderung steht „Bestpreis noch
    offen“. Ist der eigene Verlauf noch zu kurz, gilt das Allzeit-Tief einer anderen Quelle, mit
    „≈“: bei Meta von QuestStoreDB, bei Steam das niedrigste Angebot laut gg.deals, Händler und
    Keyshops. Ist ein Angebot bei gg.deals günstiger als Steam, steht es im Steam-Feld. Der günstigere Laden
    (gegen das günstigste PC-Angebot, Keyshops eingeschlossen) bekommt ab 1 € Unterschied einen grünen
    Rahmen und den Betrag („5 € günstiger“). Der Abrufzeitpunkt steht nur da, wenn ein Preis älter
    als zwei Tage ist.
  - **Fakten** in einem festen Raster (Name links, Wert rechts, in jeder Karte gleich): Wertung beider Läden auf einer Skala (Steam: Anteil positiver
    Rezensionen ab 50, darunter nur die Zahl; Meta: Anteil der 4- und 5-Sterne-Bewertungen laut
    VRDB, sonst Sterne × 20 über QuestStoreDB mit „≈“; ab 5 Punkten Abstand der bessere grün mit
    „Meta +8“), Steam-Spieler gerade jetzt mit der Spitze aus den eigenen Messungen der letzten
    30 Tage, das letzte Steam-Update laut Entwickler-Meldungen und die Meta-Version mit dem Tag,
    an dem das Tool sie zuerst sah.
  - **Recherche** violett gestrichelt mit „≈“, weil sie nicht vom Tool gemessen ist; die Notiz.
  - **Klappe** (zugeklappt), ihre Zeile nennt den Inhalt, etwa „Bestpreise · gg.deals · Links ·
    bearbeiten“: Bestpreise je Laden mit Datum und Quelle, gg.deals (Händler, Keyshop,
    Allzeit-Tief), die Werte deiner Tabelle, Links (Meta, VRDB, QuestStoreDB, Steam, fertige
    Suchen auf Reddit und Google nach „Quest vs Steam“), „bearbeiten“.

  Ohne Abruf gelten die Werte der Tabelle, gekennzeichnet mit „Tabelle“ und Datum (Differenz
  dort: Meta-Tief minus gg.deals). Am Desktop stehen Preise und Fakten nebeneinander.
  Werkzeugzeile in Jetzt, Wunschliste und Bibliothek: Suche, „Sortieren“ (Name, „Nah am
  Bestpreis“, Rabatt, Wertung, „Neu“), das Menü „Filter“ mit Häkchen (Crossbuy, Im Angebot,
  Am Bestpreis, Gut bewertet: die bessere Wertung ab 85) und „?“ für die Legende der Farben und
  Zeichen. Gewählte Filter stehen darunter als Marken mit ×.
- **Crossbuy und Herkunft:** Crossbuy kommt von Hand, von VRDB (Angabe im Meta Store), aus deiner
  Tabelle oder aus der Recherche, in dieser Rangfolge. Die Marke zeigt die Herkunft: ohne
  Zeichen von Hand oder VRDB, „Crossbuy · Tabelle“ aus der Tabelle, „Crossbuy ≈“ aus der
  Recherche; „ohne Crossbuy“ ist grau. Widersprechen sich Quellen, gilt die stärkere und die
  andere steht violett daneben („Tabelle: nein“). Unter „bearbeiten“ heißt „automatisch“: keine
  eigene Angabe. Titel aus der Zeit vor 0.4.8 ohne gespeicherte Herkunft gelten als „Tabelle“,
  wenn eine Tabellenzeile da ist, sonst als von Hand.
- **Bibliothek:** alles, was du besitzt, in Gruppen „Bei Meta und am PC“, „Nur bei Meta“,
  „Nur am PC“, mit Suche, Wertungen wie in der Wunschliste, Sortierung nach Name, Wertung oder
  „Neu“ und den Filtern „Crossbuy“ und „Gut bewertet“; je Titel Kopf, Fakten und die Klappe. Meta-Sterne gibt es dort nur für Titel,
  deren QuestStoreDB-Seite schon gelesen wurde (etwa weil sie auf der Wunschliste standen).
- **Entdecken:** die ganze PC-Sammlung aus dem Playnite-Export, nicht nur VR. Filter nach
  Mehrspieler-Art (Menü mit Häkchen; mehrere gewählt: alle müssen passen: Mehrspieler, Online,
  Koop, Lokal, Splitscreen, LAN, MMO), Genre (Menü mit Suche und Häkchen, umschaltbar zwischen
  „eines davon“ und „alle“; die Zahl hinter einem Genre zählt, was mit den übrigen Filtern übrig
  bliebe), Spielerzahl, Laden, Steam-Wertung und „über zwei Jahre in der Sammlung“; gewählte
  Mehrspieler-Arten und Genres stehen als Marken mit × darunter; sortiert nach Wertung, Geheimtipp, Bekanntheit, neu in der Sammlung, Jahr, Name
  oder Zufall. Die Suche findet Name, Entwickler und Genre. Die Liste lädt beim Scrollen weiter.
  Mischungen (eine Zeile, am Handy seitlich wischbar) setzen Filter mit einem Klick: „Koop zu zweit“, „Couch-Abend“, „Große Runde“,
  „Geheimtipps“, „Gut, lange her“; ein zweiter Klick nimmt sie zurück. „Überrasch mich“ zieht
  drei Spiele aus dem, was die Filter zeigen (gut bewertete kommen öfter), „Wilde Mischung“
  würfelt dazu eine Mehrspieler-Art und ein Genre; „Schließen“ blendet die Vorschläge aus.
  Filter und Zufall stehen in der Adresse (`#entdecken?…`), eine Mischung lässt sich so als
  Lesezeichen merken.
  Merkmale stammen aus Playnite: Mehrspieler aus `Features` und Schlagwörtern, die höchste
  Spielerzahl aus „N Players in Co-Op“ (Splitscreen ohne Zahl: zwei; unbekannt zählt beim
  Filter „ab 2“ als zwei), Genres in etwa 20 Gruppen. Ein Laden, der nur aus der Kennung
  vermutet ist, trägt „≈“. Bei Steam-Spielen gleicht der Abgleich Genres, Mehrspieler-Arten und
  Jahr mit den Steam-Store-Daten ab (80 je Lauf): was Playnite und Steam beide sagen, steht ohne
  Zeichen, was nur eine Quelle sagt, bleibt drin und trägt „≈“ (Steam kennt nur grobe Genres,
  Puzzle oder Horror etwa nicht). Spiele ohne Abgleich tragen „nur Playnite“, Steam-Spiele mit
  VR die Marke „VR“. Die Wertung kommt nur aus Steam-Rezensionen (ab 50, Anteil positiv),
  die der Abgleich nach und nach holt (100 je Lauf, siehe [docs/abrufe.md](docs/abrufe.md));
  die Community- und Expertenwertung aus Playnite zählt nicht (Entscheidung 22.10.2026: zu
  unzuverlässig). Die Zahl der Rezensionen zeigt die Bekanntheit. Der Geheimtipp-Wert
  G = (Wertung − 70) / 30 · (1 − log10(Rezensionen + 1) / 5) ist hoch bei guter Wertung und
  wenigen Rezensionen; die Marke „Geheimtipp“ steht ab 0,2.

Farben haben je eine Bedeutung: Rabatt blau, ★ und „Bestpreis“ Gold, Prüfen, Veraltetes und
Recherche violett, Grün für das, was für dich spricht (günstigerer Laden, Crossbuy, bessere
Wertung), Rot für den Aufpreis über dem Bestpreis, Grau für Eigenschaften ohne Wertung („ohne
Crossbuy“). Gruppen und Karten klappen, der Browser merkt sich, was du
zuklappst; „alle aufklappen · alle zuklappen“ steht darüber, eine Suche öffnet alles. Das
Suchfeld leert × oder Esc. Oben rechts: hell, dunkel oder wie das Gerät. Regeln für Änderungen:
[docs/oberflaeche.md](docs/oberflaeche.md).

## Sicherung

Unter Einstellungen, Sicherung: alle Titel, Notizen und Zuordnungen als eine JSON-Datei herunterladen
und wieder einspielen, dazu die Sammlung für Entdecken (`collection.json`; Sicherungen ohne
Sammlung lassen die vorhandene stehen). Die Datei enthält deine Käufe; sie gehört nicht ins Repository. Der
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
