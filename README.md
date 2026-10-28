# VR-Navigator

Deine Spielesammlung über alle Systeme (PC, VR, Konsolen, Retro) und eine VR-Wunschliste mit der
Frage: Wo kaufe ich einen Titel, bei Meta oder bei Steam?

Vorbild und Unterbau ist der [eShopKompass](https://github.com/GreenkeeperX/eshop-kompass):
Python ohne Zusatzpakete, Daten als JSON-Dateien, Oberfläche in reinem JavaScript, gehärteter
Docker-Container.

**Stand 0.8.23:** Wunschliste (VR mit Abgleich gegen die Wunschlisten der Läden, PC als Spiegel der gg.deals-Wunschliste mit Preisen und Spielinfos), Jetzt für VR- und PC-Wünsche, Sammlung (alle Spiele je System als Liste mit Spalten wie im eShopKompass, dazu der Reiter VR mit deinen VR-Titeln, Mein Stand, Filter und Vorschläge, Retro-Liste aus dem ROM-Ordner mit Spielinfos aus der libretro-database und deinen Ordner-Listen), Konten (Steam, gg.deals, Sharenite), Zuordnung aller Titel, Bestpreis über beide Läden, Meinungen aus der Recherche, Meta-Lesezeichen, Importe und Live-Preise von QuestStoreDB (Meta), Steam
und gg.deals, dazu Gemessenes: Steam-Spieler und -Updates, Crossbuy, Version und Meta-Wertung von
VRDB, daraus das Urteil „wo kaufen“ je Wunschtitel.

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
- **IGDB:** Client-ID und Secret einer kostenlosen Twitch-Entwickler-App (derselbe Schlüssel wie im
  eShopKompass). Seit 0.8.0 holt jeder Abgleich damit Genre, Spieler, Wertung, Spielzeit,
  Beschreibung und Firmen für die ganze Sammlung (Steam-Spiele über die Steam-ID, die übrigen über
  Name und System).
- **Nexus Mods:** der persönliche API-Schlüssel aus dem Nexus-Konto (Einstellungen, API Keys).
  Die Abfrage geht auch ohne; mit Schlüssel fragt das Tool als dein Konto (0.7.7). Seit 0.8.1 holt
  jeder Abgleich einmal die Woche die Spieleliste von Nexus und je PC-Spiel mit Seite dort die
  beliebtesten Mods und die mit VR im Namen.

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
   Steam nach, 40 je Lauf. Ab 0.8.8 merkt es sich die Zahl, die gg.deals über der Liste nennt („We found …
   results“); stehen dort mehr Einträge, als Links zu Spielseiten da waren, sagt die Vorschau, wie viele fehlen.
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
  Datei füllt außerdem die ganze **Sammlung** mit allen Spielen außer den
  versteckten, je Spiel mit System (PC, PS4, SNES …) aus der Spalte `Plattformen`; steht auch ein
  PC dabei, gilt PC, ohne die Spalte erkennt das Tool PlayStation an Kennungen wie
  `CUSA01234_00` (PS4); Kennungen wie `NPWR01234_00` sind Trophäenlisten von PS3 oder PS Vita und
  stehen unter „PS3 / Vita“, weil Playnite die Plattform dort nicht nennt. Die Vorschau sagt es
  in einfachen Sätzen (0.7.2): „Für die Sammlung: 6 Spiele (PS1 1, PS2 2 …), alle neu. Deine anderen
  … Spiele bleiben, wie sie sind. VR-Titel: keine darin“; VR-Titel zählen für den Reiter VR und die Wunschliste. Ein neuer Export ersetzt nur die Systeme, die in ihm vorkommen: ein
  Export nur der PlayStation-Bibliothek lässt die PC-Spiele stehen. Unter VR (deine VR-Titel)
  bleiben Spiele nur für Konsolen weiter draußen.
- **gg.deals-Wunschliste (CSV)** mit einer Spalte Name und Links auf die geteilte Liste.
- **Datei des Meta-Lesezeichens** oder kopierter Text der Bestellseite.
- **Meinungen (JSON)** aus einer Recherche auf Reddit und im Web: je Titel Kurzfazit, bessere
  Fassung, Mehrspieler, Pflege, Crossbuy, Crossplay, Komfort, Warnungen und Quellen. Sie stehen
  unter dem Titel als zugeklappte Zeile „Recherche, Datum: …“; Crossbuy daraus trägt „≈“.
  Crossbuy heißt: ein Kauf im Meta Store gilt für Quest und PC-VR im Meta Store; Steam gehört
  nie dazu. Nennt die Begründung Steam, Crossplay oder nur deine Zuordnung, verwirft der Import
  den Wert und sagt es in der Vorschau. Aufbau
  in [docs/meinungen.md](docs/meinungen.md).

### Retro-Sammlung (ROM-Liste)

Unter Einstellungen, „Retro-Sammlung“, wählst du deinen ROM-Ordner. Der Browser gibt dem Tool nur
Datei- und Ordnernamen (ab 0.8.8 mit Größe und dem Inhalt deiner Ordner-Listen `…_ordner.csv`), er lädt
keine Spiele hoch; Pfade speichert das Tool nicht. Statt der
Ordnerwahl geht eine Liste per Befehl (Linux `find`, Windows PowerShell, beide in der Karte zum
Kopieren) oder eine CSV mit den Spalten `System` und `Titel`. Erst kommt die Vorschau.

- **System:** aus einer eindeutigen Endung (`.gb`, `.gba`, `.sfc`, `.nes`, `.nds`, `.cia` …), sonst
  aus dem innersten Ordner mit bekanntem Namen, etwa „SNES“, „PS1“ oder nach No-Intro
  „Nintendo - Game Boy Advance“. Endungen wie `.iso`, `.chd` oder `.rvz` brauchen den Ordner.
- **Übersprungen:** Ordner, die auf `_zip` enden, `saves`, `_Sortierung`, `_Tools`, `_BIOS`,
  Spielstände (`.sav`, `.srm` …) und Beiwerk (Bilder, Tabellen, Skripte, `.m3u`). Bei `.cue`
  mit `.bin` zählt nur die `.cue`.
- **Ein Eintrag je Titel und System:** Regionen, Fassungen und Discs desselben Titels werden
  zusammengefasst („2 Dateien, Europe, USA“). „Legend of Pixels, The“ wird zu „The Legend of Pixels“.
- **Sprache:** aus dem Dateinamen nach No-Intro und Redump, etwa `(En,Fr,De)`. Ohne Angabe gilt
  die Sprache der Region (Germany Deutsch, Europe, USA und World Englisch, Japan Japanisch) und
  steht in der Sammlung violett. In der Sammlung steht DE vor EN vor JP.
- **Deutsche Fassung:** Beim Abgleich holt das Tool je System die Fassungsliste (No-Intro,
  bei Discs Redump, über die libretro-database) und die Retool-Liste, höchstens wöchentlich. Gab
  es eine Fassung mit Deutsch und deine Datei hat keins, steht „DE fehlt“ am Spiel, darunter die
  gesuchte Fassung („gesucht: … (Germany)“). Gefunden wird sie über den Produktcode (GBA, GBC, DS),
  die Retool-Gruppe (auch bei anderem deutschen Titel) oder den gleichen Namen; ist ihr Deutsch nur
  aus der Region geschätzt, steht die Marke violett. Der Filter „Sprache“ zeigt „mit Deutsch“,
  „DE fehlt“ oder „ohne Deutsch“ (keine deutsche Fassung bekannt). Ab 0.8.12 gelten die Sprachen auch ohne
  Sprachangabe im Namen als bestätigt (nicht violett), wenn deine Datei genau so in der Fassungsliste steht:
  No-Intro nennt die Sprachen nur, wenn sie von der Sprache der Region abweichen.
- **3DS** (0.8.4): Fassungsliste von No-Intro für Module und für Download-Titel aus dem eShop. Nennt der
  Dateiname den Produktcode („… (CTR-P-ABCP) (v0) (E).cia“), gelten die Sprachen genau dieser Fassung
  laut No-Intro statt der aus der Region geschätzten (nicht mehr violett), und die Fassungen anderer
  Regionen findet das Tool über den Code auch bei anderem Titel.
- **Ähnlicher Name** (0.8.4): Steht ein Spiel nicht unter seinem Namen in der Fassungsliste, dort aber ein
  ähnlicher Titel (gleiche Wörter zu 60 %, oder einer steckt ganz im anderen), steht es unter „Zu
  erledigen“, „Retro: ähnlicher Name“. „dasselbe“: der Titel der Liste gilt fortan für dieses Spiel;
  „anderes“: der Vorschlag kommt nicht wieder. Hacks und Homebrew bekommen keinen Vorschlag. Ab 0.8.6
  müssen die Zahlen gleich sein („Teil 2“ ist ein anderes Spiel; „IV“ zählt wie „4“), und Titel, die sich
  nur in Leerzeichen unterscheiden („Moonrover“, „Moon Rover“), gelten ohne Rückfrage als gleich.
- **GameCube, Wii, PlayStation** (0.8.16): Fassungslisten von Redump. Steht im Dateinamen die Spiel-ID
  („… [RMRP01].rvz“, oder die Datei heißt nur so und liegt im Ordner „Titel [RMRP01]“, wie ihn Wii-Werkzeuge
  anlegen) oder bei PlayStation die Seriennummer („[SLES-02376]“, auch „SLES_023.76“), findet das Tool genau
  diese Fassung, ihre Sprachen und über die ID die Fassungen anderer Regionen auch bei anderem Titel. Der vierte
  Buchstabe der ID ist die Region (D Deutschland, P Europa, E USA, J Japan).
- **Genau genannte Fassung** (ab 0.8.16): Nennt ein Produktcode oder eine Spiel-ID genau eine Fassung, gelten
  deren Sprachen auch ohne Angabe in der Liste (dann die Sprache ihrer Region), wie bei genau gleichem Dateinamen.
- **IGDB mit deinem Titel** (0.8.16): Findet IGDB ein Retro-Spiel nicht unter dem Namen der Datei, sucht der
  Abgleich mit dem Titel aus deiner Ordner-Liste und vergleicht ihn auch mit den anderen Namen bei IGDB (dort
  stehen deutsche Titel meist als weiterer Name). Spiele, die vorher ohne Treffer blieben, kommen dafür einmal
  wieder dran.
- **DSiWare** (0.8.6): Beim DS liest das Tool auch die Liste der Download-Titel aus dem DSi-Shop. Spiele
  aus dem DSi-Ordner finden so ihre Fassungen statt eines ähnlichen Namens.
- **Spielinfos** (0.8.8): Beim Abgleich holt das Tool je System die Listen der libretro-database mit Genre,
  Spielerzahl, Erscheinen (Jahr, oft Monat) und Entwickler, bei PS1 und PS2 auch Verlag und eine englische
  Beschreibung. Zugeordnet wird über den Titel, Fassungen der eigenen Region zuerst. Die Listen sind groß; das
  Tool behält nur, was zu deinen Spielen passt, und fragt je System höchstens monatlich neu, früher nur, wenn ein
  Spiel noch keine Spielinfos hat. Nennt sonst keine Quelle ein Genre, gilt das von libretro als bestätigt; IGDB
  bestätigt oder ergänzt es, bei der Spielerzahl gilt IGDB zuerst. Für DS, DSiWare und 3DS hat libretro kaum
  Einträge, GameCube, Wii und Pokémon Mini gar keine; dort helfen nur IGDB und deine Ordner-Listen.
- **Deine Ordner-Listen** (0.8.8): Liegt im gewählten Ordner eine Datei `<system>_ordner.csv` (auch unter
  `…_zip/_Sortierung/`) mit den Spalten `Datei;Titel;Reihe;Sammelreihe;Genre;Untergruppe;Ordner` (dazu
  optional `Status` und `MB`), liest die Ordnerwahl sie mit. Sie ist die erste Quelle (Entscheidung
  28.10.2026): Dein Titel ist der Name in der Sammlung, dein Genre steht vorn und gilt als bestätigt
  („Jump & Run“ wird zur Genre-Gruppe Plattformer, „Brett- & Kartenspiele“ zu Karten und Brett …). Reihe,
  Untergruppe, Ordner und der Titel laut Dateiname stehen in den Einzelheiten; die Suche findet auch die Reihe.
  Die Vorschau nennt, wie viele Zeilen zu einer Datei passen, was nur in der Liste steht und welche Dateien
  in der Liste fehlen. Die Genres von libretro und IGDB kommen in der Zeile zu deinem dazu. Nennen libretro
  und IGDB beide ein ganz anderes Genre und sind sich darin einig (keine nahe Gruppe, „Jump & Run“ und
  „Action“ gelten als nah; „Party & Minispiele“ widerspricht nie), steht das Spiel unter „Zu erledigen“,
  „Retro: Genre weicht von deiner Liste ab“ (ab 0.8.12; vorher genügte eine Quelle, das traf vor allem Ordner
  nach Reihe oder Lizenz). Was nur eine Quelle anders sieht, steht in den Einzelheiten.
  „Liste gilt“ (auch für alle auf einmal) blendet den Hinweis aus, bis sich ein Wert ändert. Liest du die
  Liste später ohne Ordner-Liste ein (etwa als Text), bleiben die Angaben der letzten Ordner-Liste.
- **Größe** (0.8.8): Die Ordnerwahl schickt je Datei die Größe mit; die Einzelheiten zeigen sie bei „Dateien“.
- **Merkmale:** `_Extras/Homebrew`, `(Unl)` oder `(Aftermarket)` ergeben „Homebrew“, ein Ordner
  „ROM-Hacks“ ergibt „Hack“.
- **Neu einlesen:** Neue Spiele kommen dazu. Fehlt ein Spiel eines Systems, das in der neuen
  Liste vorkommt, wird es nicht gelöscht: oben in der Sammlung steht „Nicht mehr in der
  Retro-Liste“ mit „Stand übernehmen“ (entfernt sie) und „Behalten“. Ein Playnite-Export lässt
  die Retro-Spiele stehen und umgekehrt.

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
die Suche nicht wieder vor), Titel, die QuestStoreDB nicht fand, und Retro-Spiele mit ähnlichem
Namen in der Fassungsliste. Bundles sind dort als solche markiert.

## Wunschliste abgleichen

Deine Wünsche führt das Tool; die Wunschlisten bei Meta, Steam und gg.deals sind Spiegel, die
der Abgleich liest (Steam und gg.deals selbst, Meta per Lesezeichen). Steht ein Titel auf einer
davon, ist er gewünscht; fehlt er überall, fällt er von der Liste. Was danach nicht
zusammenpasst, steht unter „Zu erledigen“, je Gruppe mit einer Aktion für alle:

- **Gekauft, noch auf der Wunschliste:** du besitzt ihn (Meta-Käufe, Steam-Konto, Sharenite,
  Playnite). Links führen zur Liste im Laden, wo er noch steht; „von der Wunschliste“ nimmt ihn
  im Tool weg, „behalten“, wenn du die Fassung im anderen Laden willst. Das entscheidest immer du
  (Entscheidung 28.10.2026): Von 0.8.13 bis 0.8.16 nahm der Abgleich gekaufte Titel ohne Laden-Wunschliste
  selbst weg; ab 0.8.17 sind sie wieder gewünscht und stehen hier (Protokoll „Wunschliste: wieder gewünscht …“).
  Bei Meta mit Crossbuy gekauft nennt der Grund „Crossbuy, gilt auch am PC“.
- **Im Tool entfernt, im Laden noch gewünscht:** der Hinweis geht, sobald der Laden ihn nicht
  mehr führt; „wieder wünschen“ holt ihn zurück.
- **Fehlt auf einer Laden-Wunschliste** (bis 0.8.11; ab 0.8.12 nur noch als Marke an der Karte, weil das
  Tool die Preise beider Läden ohnehin holt): gewünscht, aber in einem Laden, der den Titel führt,
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

Unter **Einstellungen**, Abgleich, startet „Aktualisieren“ einen Abgleich (wie der Knopf oben); danach läuft er nach Zeitplan (Standard
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

**Beschleunigt auffüllen** (0.8.6, nur von Hand): ein Lauf, in dem jede lange Warteschlange (Steam-Details
und -Rezensionen, Steam-Wertungen, IGDB, PCGamingWiki, Nexus Mods, Steam-Schlagwörter, Spielerzahlen,
VRDB) fünfmal so viele Spiele schafft wie sonst. Gedacht für das erste Auffüllen einer großen Sammlung.
Die Pausen zwischen zwei Abrufen und der Abbruch bei 403 und 429 bleiben, darum dauert so ein Lauf
etwa eine Stunde. Der Zeitplan läuft danach normal weiter.

Die Karte Abgleich zeigt je Quelle Ergebnis und Anzahl der Abrufe, darunter:

- **Verbindung testen:** fragt jede Quelle einmal an und beschreibt, was zurückkommt (Status,
  Server und was die Leser erkennen); „Ergebnis kopieren“ für eine Rückfrage. Speichert nichts.
  Seit 0.8.0 läuft der Test auf dem Server weiter und die Seite fragt alle zwei Sekunden nach; ein
  Proxy davor bricht ihn so nicht mehr mit „Fehler 504“ ab.
  Seit 0.7.0 fragt er auch die Kandidaten für die Datenbasis je Plattform an, je mit einem Spiel
  deiner Sammlung (PC, Konsole, Retro): Steam-Details (Metacritic, Beschreibung, VR-Kategorien),
  PCGamingWiki (VR-Felder, auch per Mod), UEVR-Profile, DekuDeals (Wertung, HowLongToBeat,
  Beschreibung für Konsolen), HowLongToBeat, libretro-metadat (Genre, Spieler, Jahr, Entwickler)
  und mit Schlüssel IGDB (Genre, Spieler, Wertung, Spielzeit, Beschreibung, Firmen). Welche
  Quelle welches Feld liefert, wird nach den Ergebnissen entschieden. Seit 0.7.1 schlägt die Probe
  bei PCGamingWiki zuerst die Tabellen nach, fragt IGDB beim PC-Spiel über die Steam-ID, nimmt als
  Retro-Spiel eines aus No-Intro oder Redump (kein Hack) und ohne Konsolenspiel eine Vorgabe. Seit
  0.7.2 liest er PCGamingWiki über die Seite des Spiels (Cargo ist gesperrt), lässt die UEVR-Profile
  weg, fragt DekuDeals nur zu Switch, PS4, PS5 und Xbox und sucht bei IGDB mit Plattform und ohne
  Sonderzeichen. Die Steam-Rezensionen prüft er an drei Spielen der Sammlung und sagt, wenn Steam
  statt Daten eine Seite schickt.
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
  nach Nähe zum Bestpreis, nach Rabatt oder Wertung, mit Ende des Angebots. Jeder Titel als Zeile wie in der
  Wunschliste (bis 0.8.21 als Karte). Ab 0.8.11 darunter auch die PC-Wünsche, die höchstens 5 % über dem bisherigen Tief bei gg.deals
  liegen, als Liste wie unter Wunschliste, PC; die Reiter „Alle, PC, VR“ (ab 0.8.17, vorher ein Schalter, jetzt an
  derselben Stelle wie in Wunschliste und Sammlung) zeigen beide oder nur eine Seite.
- **Spaltenreihenfolge** (ab 0.8.19, Entscheidung 28.10.2026): links, wonach du entscheidest, rechts das Nachschlagen.
  Sammlung: Spiel, (Sprache bei Retro), Wertung, Genre, Spielzeit, Mehrspieler, Spieler, Jahr, Rezensionen, Launcher;
  Reiter VR: Spiel, Besitz, Meta, Steam, Spieler, Update, Crossbuy, Recherche.
  Ab 0.8.23 (Entscheidung 28.10.2026) gilt in allen Tabellen eine Reihenfolge: Spiel, Wertung, Rezensionen, Genre,
  Spielzeit, max. Spieler, Aktiv, Sprache, Launcher oder System, Jahr ganz rechts. Wunschliste PC: Preis und zum Tief
  vorn; Wunschliste VR: Wo, Meta, Steam und zum Bestpreis vorn, dahinter Wertung, Rezensionen, Aktiv, Update; Reiter VR:
  Wertung, Rezensionen, Aktiv, Update, Crossbuy, Besitz, Recherche; Switch: Wertung, Genre, Spielzeit, max. Spieler, Jahr.
  Mehrspieler ist keine Spalte mehr: die Arten stehen im Tooltip von „max. Spieler“ (ohne Zahl „2+“, laut Steam ohne
  Mehrspieler „1“), in den Einzelheiten und im Filter Mehrspieler (auch in der Wunschliste PC). „Aktiv“ heißt überall
  die Zahl der Steam-Spieler gerade eben, für PC-Spiele (Wunschliste, Sammlung) wöchentlich gemessen. Der Reiter VR
  zeigt die Wertung der Fassung, die du besitzt (bei beiden die bessere); ist die andere mindestens 8 Punkte besser,
  steht sie klein daneben („M 92“). Gleich benannte Spalten sind überall gleich breit.
- **Wunschliste** (0.8.2, vorher „VR-Wunschliste“) mit den Unterreitern PC und VR (ab 0.8.7 PC zuerst, wie in der
  Sammlung). **PC** spiegelt deine gg.deals-Wunschliste (gepflegt wird sie dort), ab 0.8.7 mit Paketen und DLC
  (Marke „Paket“, „DLC“; Preis über den Link zur Seite bei gg.deals, die API kennt nur Steam-Apps) und ohne die
  VR-Spiele, die unter VR stehen. Nennt nur der Name VR („… VR“), steht ein violettes „VR“ als Hinweis. Je Spiel der günstigste Preis jetzt (Händler
  oder Keyshop, als Link zu gg.deals) und wie weit er über dem bisherigen Tief liegt: grün „am Tief“ (bis 2 %),
  sonst rot der Betrag. Ab 0.8.17 wie im eShopKompass: Händler, Keyshop und das Tief stehen im Tooltip des
  Preises und in den Einzelheiten statt in eigenen Spalten; dazu die Spalten Spieler und Jahr. Reihenfolge:
  Spiel, Preis, zum Tief, Wertung, Genre, Spielzeit, Mehrspieler (mit Spielerzahl, ab 0.8.19), Jahr. „Nah am Tief“ (Jetzt) heißt höchstens 5 % darüber.
  Ab 0.8.18 merkt sich das Tool den Preisverlauf je Spiel; liegt der Preis jetzt deutlich unter dem üblichen (mindestens
  25 % und 3 € unter dem Median der letzten 90 Tage), steht grün „Preissturz“ am Namen. Das gilt für Händler und
  Keyshop gleich, denn Keyshops sind oft günstiger als ein Steam-Sale. Dazu Trend und Pflege wie unten. Die Steam-ID kommt aus dem, was das Tool kennt, sonst aus der
  Steam-Suche nach genau gleichem Namen (30 je Abgleich); ohne gg.deals-Schlüssel gibt es keine Preise.
  Ab 0.8.11 mit Spielinfos wie in der Sammlung: Spalten Wertung (Steam-Rezensionen ab 50, sonst IGDB grau und
  kursiv), Spielzeit (IGDB) und Genre (Steam und IGDB, violett nur eine Quelle); ein Klick auf den Namen zeigt
  Mehrspieler, Spieler, Erscheinen, Entwickler, Rezensionen, das Tief je Art, die Beschreibung und die Links zu
  gg.deals und Steam. Sortieren auch nach Wertung und Spielzeit. Die Infos holt der Abgleich über die Steam-ID,
  60 Spiele je Lauf (Pakete und DLC bekommen keine).
  „schon in der Sammlung“ markiert Spiele, die du schon besitzt. **VR**: Was du bei Meta oder am PC schon besitzt, steht unten in der zugeklappten
  Gruppe „Schon im Besitz“, etwa wenn du ein PC-Spiel zusätzlich für die Quest willst.
  „nicht mehr wünschen“ (in der Klappe unter der Karte) nimmt einen Titel von der Liste (mit Rückgängig);
  „+ Titel“ in der Werkzeugzeile trägt einen von Hand ein.
  Ab 0.8.22 (Entscheidung 28.10.2026) stehen die VR-Wünsche als Tabelle wie unter PC: Spiel (mit Crossbuy,
  SimRacing und kurz „keine Liste“ oder „fehlt: Meta“), Wo (Urteil „wo kaufen“), Meta, Steam (Preis mit Rabatt,
  als Link zum Laden), zum Bestpreis (grün „am Bestpreis“, sonst rot der Abstand), Wertung mit Trend, Rezensionen, Aktiv (bis 0.8.22 „Spieler“),
  Update. Ein Klick auf den Namen klappt darunter die bisherige Karte als Einzelheiten auf. Jetzt zeigt die
  VR-Angebote in derselben Tabelle.
  Je Titel eine Karte mit festem Aufbau (ab 0.8.22 die Einzelheiten einer Zeile):
  - **Kopf:** Name, „wo kaufen“, Crossbuy-Marke mit Herkunft (siehe unten), Besitz, Bundle, „Steam-ID ≈“.
  - **Wo kaufen** (ab 0.8.15): für jeden Wunschtitel, den du noch nicht hast, der Laden, für den mehr
    spricht, und dahinter das Preisurteil dort („Meta kaufen“, „Steam warten“, „Laden egal, gut“). Gezählt
    wird nur Gemessenes: nur ein Laden führt ihn (entscheidet), Crossbuy (2 für Meta), ein großer
    Preisabstand von mindestens 40 % und 8 € (2), je 1 für Mehrspieler mit weniger als 20 Spielern auf
    Steam (Spitze; spricht für Meta), 8 Punkte bessere Wertung, eine um ein Jahr jüngere Pflege (letztes
    Steam-Update gegen die Meta-Version), spürbar günstiger (Steam 20 % und 3 €, Meta ab 1 €). Die
    Recherche („Quest-“ oder „PC-Fassung besser“) zählt halb und steht violett mit „≈“. Wer mindestens
    einen Punkt vorn liegt, gewinnt, sonst ist der Laden egal. Die Gründe stehen in der Zeile „Wo“, die
    für den anderen Laden grau.
  - **Preise:** zwei feste Felder, Meta links, Steam rechts; fehlt ein Laden, bleibt sein Feld grau
    mit „kein Preis“. Je Feld Preis, Rabatt und Ende, darunter der Abstand zum **Bestpreis**
    beider Läden, dem niedrigsten Preis von Meta oder Steam der letzten 24 Monate: rot „+3,50 € über
    Bestpreis“ mit Betrag, Laden und Prozent (jeder Aufpreis rot), gold „★ Bestpreis“
    (bis 2 % darüber). Neben dem Laden steht das Urteil wie im eShopKompass: grün „kaufen“ (bis
    2 % oder 0,50 € über dem Bestpreis beider Läden), grün umrandet „gut“ (bis 15 % oder 2 €). Kommt der Bestpreis aus dem anderen Laden, steht klein darunter der
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
    Ab 0.8.18 **Trend und Pflege**: Sind die Steam-Rezensionen der letzten 30 Tage mindestens 8 Punkte besser oder
    schlechter als insgesamt, steht neben der Steam-Wertung ein grüner ↗ oder roter ↘ Pfeil (Zahlen im Tooltip, in den
    Fakten „Trend: fallend (60 % gegen 92 %)“). Über ein Jahr ohne Update heißt „ruht“ (grau). Dasselbe gilt in der
    Wunschliste PC und im Reiter VR der Sammlung (Spalten Steam und Update). Ab 0.8.21 frischt der Abgleich den Trend
    wöchentlich auf, je Lauf bis zu 60 Titel und 60 PC-Wünsche. Woher die Zahlen kommen, steht in
    `docs/abrufe.md` (Trend und Pflege).
  - **Recherche** violett gestrichelt mit „≈“, weil sie nicht vom Tool gemessen ist; die Notiz.
  - **Klappe** (zugeklappt), ihre Zeile nennt den Inhalt, etwa „Bestpreise · gg.deals · Links ·
    bearbeiten“: Bestpreise je Laden mit Datum und Quelle, gg.deals (Händler, Keyshop,
    Allzeit-Tief), die Werte deiner Tabelle, Links (Meta, VRDB, QuestStoreDB, Steam, fertige
    Suchen auf Reddit und Google nach „Quest vs Steam“), „bearbeiten“.

  Ohne Abruf gelten die Werte der Tabelle, gekennzeichnet mit „Tabelle“ und Datum (Differenz
  dort: Meta-Tief minus gg.deals). Am Desktop stehen Preise und Fakten nebeneinander.
  Werkzeugzeile in Jetzt und Wunschliste: Suche, „Sortieren“ (Name, „Nah am
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
- **Sammlung** (bis 0.5.5 „Entdecken“): die ganze Sammlung aus dem Playnite-Export, der Retro-Liste und
  (ab 0.7.3, mit `ESHOP_URL`) der Switch-Sammlung des eShopKompass, mit einem Reiter je
  System („Alle“ vorn, nur bei mehr als einem System aus Playnite und Retro-Liste, dann PC, VR
  und die Konsolen mit Zahl). Beim Öffnen gilt PC; der gewählte Reiter ist in der Farbe seiner
  Familie unterstrichen (Nintendo rot, PlayStation blau, PC grün, VR türkis).
  Aufbau wie „Spiele“ im eShopKompass (0.6.0): je Spiel eine Zeile mit Spalten, die nur
  erscheinen, wenn ein Spiel im Reiter dafür einen Wert hat (Spieler, Mehrspieler, Wertung,
  Rezensionen, Sprache, Genre, Jahr, Launcher; die Spalte Launcher zeigt am PC Steam, Epic, GOG …,
  bei Konsolen unter „Alle“ das System). Genres stehen einzeilig, seltene zuerst (je seltener in
  der Sammlung, desto weiter vorn, bei Gleichstand nach dem Alphabet, „Sonstiges“ zuletzt); was
  nicht passt, zählt „+n weitere“ (Tooltip mit den Namen), die Einzelheiten zeigen alle. Ein Klick auf einen
  Spaltenkopf sortiert (Wertungen und Zahlen zuerst absteigend), der zweite andersherum, der dritte
  zurück zur gewählten Sortierung. Die Wertung ist von Rot über Gelb nach Grün eingefärbt (50 bis
  95 %), Genres stehen als farbige Blasen (verwandte Genres in ähnlichem Farbton, violett bleibt
  frei). Ein Klick auf den Namen klappt die Einzelheiten auf: Die Genres der Zeile laufen nach
  unten weiter (Name und Spalten bleiben dabei, wo sie sind), darunter steht nur, was keine Spalte
  zeigt: bei Steam-Spielen die Wertung als Zahl wie im eShopKompass („Steam 97 % · Metacritic 96“,
  Steams Worte und die Zahl der Rezensionen im Tooltip; 0.7.2), das genaue Erscheinen (Entwickler und Verlag im Tooltip) und die Sprachen („Deutsch
  und 12 weitere Sprachen“, rot „ohne Deutsch“), bei Retro-Spielen Sprachen, gesuchte Fassung und
  Dateien; unter Mein Stand die Kurzbeschreibung aus dem Steam-Store auf Deutsch (0.7.1; vier
  Zeilen, ein Klick zeigt alles). „alle aufklappen“ öffnet alle Spiele der Liste, solange es
  höchstens 150 sind (sonst grau, der Tooltip sagt, wie viele es sind; 0.7.4). Die Reiter oben
  zeigen Alle, PC, VR, PlayStation, Nintendo und Weitere (alle übrigen Systeme); ein Klick
  auf eine Familie zeigt alle ihre Spiele und klappt rechts daneben ihre Konsolen aus (PS1 bis PS5,
  Switch 2, 3DS …; 0.7.4). Switch und Switch 2 stehen in einem Reiter „Switch 2“, der Filter
  „System“ trennt sie wieder; die Switch-Spiele zeigen Spalten, Marken und Einzelheiten wie „Spiele“
  im eShopKompass (ab eShopKompass 1.7.17), „im eShopKompass“ öffnet das Spiel dort aufgeklappt
  (0.7.5), mit dessen Filtern Spielweise, Spielzeit und USK (0.7.6). Alle übrigen Reiter füllt seit
  0.8.0 IGDB mit fester Rangfolge je Feld: Wertung am PC Steam (ab 50 Rezensionen), sonst IGDB grau
  und kursiv; auf Konsolen und Retro IGDB-Kritiken, sonst die IGDB-Gesamtwertung grau und kursiv.
  Spielzeit von IGDB (normal, sonst eilig; komplett im Tooltip), Spieler von IGDB, sonst Playnite
  (violett). Genres und Mehrspieler aus allen Quellen; was nur eine nennt, während eine andere etwas
  anderes sagt, ist violett. Ohne Steam-Beschreibung steht die englische von IGDB da. **VR per Mod**
  (0.8.1): Sagt PCGamingWiki bei einer Brille „hackable“, trägt das PC-Spiel die Marke „VR per Mod“;
  hat Nexus Mods nur Mods mit VR im Namen oder geht es mit vorpX, steht „VR-Mod“ (ein Hinweis, türkis
  gestrichelt; bis 0.8.19 mit „?“). Der Filter „VR per Mod“ zeigt beide. Die Einzelheiten nennen die Brillen und verlinken die
  Nexus-Seite, die beliebtesten Mods und die VR-Mods. **Lenkrad** (0.8.3, Sim-Racing): Steht ein
  PC-Spiel oder ein VR-Titel (ab 0.8.5, auch auf der Wunschliste) in einer Liste der Rennspiele, trägt es
  die Marke „Lenkrad“: die Liste „Supported Games“ von SimHub (ab 0.8.5, über die Steam-ID) oder die
  offene Liste der Rennsimulationen aus dem Simucube-Forum (Direktantriebe mit Force Feedback; was dort
  läuft, läuft auch mit Simagic). Deuten nur die Steam-Schlagwörter darauf (unter den ersten zehn ein
  Rennen, „Racing“ oder „Driving“, und eine Simulation, „Automobile Sim“ oder „Simulation“), steht
  violett „Lenkrad?“ (ein Hinweis). Die Kompatibilitätsliste zu Simagic selbst liegt hinter einer
  Bot-Prüfung und wird deshalb nicht abgerufen. Filter „Lenkrad“, Zeile „Sim-Racing“ in den Einzelheiten.
  Ab 0.8.12 heißt die Marke „SimRacing“ (ab 0.8.20 wie „VR“ und „Geheimtipp“ nur umrandet in ihrer Farbe; aus Steam-Schlagwörtern allein gestrichelt, ohne „?“), dazu im Reiter PC
  ein Filter „VR“ neben „SimRacing“ und „VR per Mod“.
  Über der Liste steht kurz die Zahl
  der Spiele, die Herkunft der Angaben klappt auf,
  daneben ab der Spalte Spieler **Mein Stand** (Backlog ○, angefangen ▷, durchgespielt ✓,
  Favorit ★; steht in allen Reitern an derselben Stelle, die Zeile springt beim Setzen nicht), der
  hinter dem Namen steht, sich filtern lässt („Mein Stand“, Mischung „Aus dem Backlog“) und in
  der Sicherung steckt. Am Handy stehen die Werte je Spiel untereinander.
  **VR** (bis 0.5.8 der Reiter „Bibliothek“): alle VR-Titel, die du bei Meta oder am PC hast,
  mit den Spalten Besitz, Crossbuy (Herkunft im Tooltip, „T“ aus der Tabelle, violett „Recherche“
  aus der Recherche), Meta- und Steam-Wertung, Steam-Spieler jetzt, letztes Update und Recherche. Filter
  Besitz, Wertung, Mein Stand und Crossbuy. Die Einzelheiten zeigen dieselben Fakten, Recherche
  und Klappe (Links, bearbeiten) wie die Wunschliste. Unter „Alle“ stehen VR-Titel nicht, am PC
  meist ohnehin unter PC.
  Filter, Mischungen und Zufall gelten im gewählten Reiter; unter „Alle“ trägt ein Konsolenspiel
  sein System als Marke. Steam-Abgleich und Steam-Wertung gibt es nur für PC-Spiele. Filter nach
  Mehrspieler-Art (Menü mit Häkchen; mehrere gewählt: alle müssen passen: Mehrspieler, Online,
  Koop, Lokal, Splitscreen, LAN, MMO), Genre (Menü mit Suche und Häkchen, umschaltbar zwischen
  „eines davon“ und „alle“; die Zahl hinter einem Genre zählt, was mit den übrigen Filtern übrig
  bliebe), Spielerzahl, Launcher, Steam-Wertung und „über zwei Jahre in der Sammlung“; gewählte
  Mehrspieler-Arten und Genres stehen als Marken mit × darunter; sortiert nach Wertung, Geheimtipp, Bekanntheit, neu in der Sammlung, Jahr, Name
  oder Zufall. Die Suche findet Name, Entwickler, Verlag und Genre; Erscheinungsdatum, Entwickler und
  Verlag stehen im Tooltip am Jahr wie im eShopKompass. Die Liste lädt beim Scrollen weiter.
  Mischungen (eine Zeile, am Handy seitlich wischbar) setzen Filter mit einem Klick: „Koop zu zweit“, „Couch-Abend“, „Große Runde“,
  „Geheimtipps“, „Gut, lange her“; ein zweiter Klick nimmt sie zurück. „Überrasch mich“ zieht
  drei Spiele aus dem, was die Filter zeigen (gut bewertete kommen öfter), „Wilde Mischung“
  würfelt dazu eine Mehrspieler-Art und ein Genre; „Schließen“ blendet die Vorschläge aus.
  Filter und Zufall stehen in der Adresse (`#sammlung?…`, alte Lesezeichen mit `#entdecken?…`
  gelten weiter), eine Mischung lässt sich so als Lesezeichen merken.
  Merkmale stammen aus Playnite: Mehrspieler aus `Features` und Schlagwörtern, die höchste
  Spielerzahl aus „N Players in Co-Op“ (Splitscreen ohne Zahl: zwei; unbekannt zählt beim
  Filter „ab 2“ als zwei), Genres in etwa 20 Gruppen. Ein Launcher, der nur aus der Kennung
  vermutet ist, steht violett. Bei Steam-Spielen gleicht der Abgleich Genres, Mehrspieler-Arten und
  Jahr mit den Steam-Store-Daten ab (80 je Lauf): was Playnite und Steam beide sagen, steht ohne
  Zeichen, was nur eine Quelle sagt, bleibt drin und steht violett, der Tooltip nennt die Quelle
  (seit 0.6.1 statt „≈“; Steam kennt nur grobe Genres,
  Puzzle oder Horror etwa nicht). Die Einzelheiten nennen, ob ein Spiel schon abgeglichen ist;
  Spiele mit VR tragen die türkise Marke „VR“: laut Steam-Details, als VR-Titel im Tool oder laut VR-Prüfung im
  Steam-Store (ab 0.8.7); nennt nur der Name VR, ist die Marke violett. Ab 0.8.7 stehen unter PC auch deine
  VR-Titel am PC, die Playnite nicht kennt (am PC gekauft oder bei Meta mit Crossbuy). Ab 0.8.9 sind sie eigene
  Spiele der Sammlung und bekommen wie alle Steam-Details, Rezensionen, IGDB, PCGamingWiki und Nexus Mods; kennt
  Playnite einen davon später, fällt der eigene Eintrag weg. Die Suche gilt je Reiter
  und leert sich beim Wechsel. „herunterladen“ gibt die gefilterte Liste mit den gezeigten Spalten und Mein Stand
  als CSV aus, aufgeklappte Spiele mit ihren Einzelheiten; ⧉ am Spaltenkopf „Spiel“ kopiert alle Titel der Liste. PlayStation-Spiele der ersten Generation
  stehen unter PS1 (bis 0.6.0 „PS“). Die Wertung kommt nur aus Steam-Rezensionen (ab 50, Anteil positiv),
  die der Abgleich nach und nach holt (100 je Lauf, siehe [docs/abrufe.md](docs/abrufe.md));
  die Community- und Expertenwertung aus Playnite zählt nicht (Entscheidung 22.10.2026: zu
  unzuverlässig). Die Zahl der Rezensionen zeigt die Bekanntheit. Der Geheimtipp-Wert
  G = (Wertung − 70) / 30 · (1 − log10(Rezensionen + 1) / 5) ist hoch bei guter Wertung und
  wenigen Rezensionen; die Marke „Geheimtipp“ (grün umrandet) steht ab 0,4 (bis 0.8.11 ab 0,2, das traf zu viele Spiele, um noch ein Tipp zu sein).

Farben haben je eine Bedeutung: Rabatt blau, ★ und „Bestpreis“ Gold, Prüfen, Veraltetes und
Recherche violett, Grün für das, was für dich spricht (günstigerer Laden, Crossbuy, bessere
Wertung), Rot für den Aufpreis über dem Bestpreis, Grau für Eigenschaften ohne Wertung („ohne
Crossbuy“). Ausnahmen wie im eShopKompass: die Familienfarben der System-Reiter, die farbigen
Genre-Blasen und die Wertung als Farbton in der Sammlung. Gruppen und Karten klappen, der Browser merkt sich, was du
zuklappst; „alle aufklappen · alle zuklappen“ steht darüber, eine Suche öffnet alles. Das
Suchfeld leert × oder Esc. Oben rechts: hell, dunkel oder wie das Gerät; im Dunkeln ist die
Schrift gedeckt, hell bleiben nur Name, Überschriften, aktiver Reiter und große Preise (0.7.2). Regeln für Änderungen:
[docs/oberflaeche.md](docs/oberflaeche.md).

## Sicherung

Unter Einstellungen, Sicherung, drei Knöpfe wie im eShopKompass: „Sicherung herunterladen“ (alle
Titel, Notizen, Zuordnungen und Mein Stand als eine JSON-Datei, dazu die Sammlung,
`collection.json`, und ab 0.8.7 die PC-Wunschliste, `pcwish.json`), „Sicherung einlesen“ (ersetzt alles; Sicherungen ohne Sammlung lassen die
vorhandene stehen, Sicherungen vor 0.6.0 ohne Mein Stand laden weiter) und „Abgleichsdaten
herunterladen“ (Stand und Protokoll des Abgleichs, Preisverlauf und Einstellungen ohne Schlüssel und
Konten, zum Nachprüfen; zum Einlesen nicht nötig). Die Sicherung enthält deine Käufe; sie gehört
nicht ins Repository. Schlüssel, Konten und der Preisverlauf (`history.json`) sind nicht darin.

## Betrieb und Sicherheit

- Der Server nimmt nur JSON-Anfragen bis 1 MB an (Importe und Sicherungen bis 50 MB) und
  antwortet nur unter IP-Adressen, Namen ohne Punkt, Namen im eigenen Netz und Namen aus
  `ALLOWED_HOSTS` (Schutz gegen DNS-Rebinding).
- Fremde Texte (Titel, Notizen, Links) werden in der Oberfläche nie als HTML ausgeführt; Links
  sind nur mit http und https klickbar.
- Abrufe laufen über `sources.request`: ehrliche Kennung, nur öffentliche Ziele, Grenzen für
  Zeit und Größe, Pausen zwischen zwei Abrufen, 24 Stunden Ruhe nach 403, 429 oder Prüfseite.
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
- Ein Abgleich dauert länger, solange die Warteschlangen (Steam-Details, PCGamingWiki, IGDB) noch gefüllt
  werden; das Protokoll nennt die verbleibenden Läufe. Danach liest jeder Lauf nur noch, was veraltet ist.
- Daten liegen in `data.json` im Datenordner. Eine kaputte Datei bleibt als
  `data.json.kaputt-<Zeit>` liegen und wird im Protokoll des Containers gemeldet.

## Prüfen

    python3 -m unittest tests.test_all

Die Tests nutzen erfundene Beispiele im Format der echten Exporte.
