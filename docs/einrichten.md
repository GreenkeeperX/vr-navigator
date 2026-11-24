# Einrichten, Zuordnung, Wunschliste und Preise

Aus der README ausgelagert (0.11.2), unverändert. Kurzfassung in der [README](../README.md).

## Einrichten

Unter **Einstellungen**, Karte Einlesen, stehen drei Wege: Konten liest jeder Abgleich
selbst, Meta kommt per Lesezeichen, alles andere als Datei. Gelöscht wird beim Einlesen nichts.

### Konten (automatisch)

- **Steam:** SteamID (die Zahl oder der Link zum Profil) und ein Steam-Schlüssel
  (kostenlos unter steamcommunity.com/dev/apikey; im Profil müssen die Spieldetails öffentlich
  sein). Dann liest jeder Abgleich deinen Besitz und deine Wunschliste, mit genauen App-IDs;
  „Steam-ID ungeprüft“ entfällt für alles, was dort steht. Ohne Schlüssel nur die Wunschliste. Pflegst
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
- **Flat2VR Index und UEVR Hub** (0.10.28): ohne Konto und Schlüssel. Die Daten des Flat2VR Index stehen unter
  CC0 1.0 (github.com/jrejaud/awesome-flat2vr), der UEVR Hub sammelt Profile der Community (uevr-profiles.github.io);
  das Tool liest nur Namen und Angaben und verlinkt Ports und Profile, es lädt nichts davon herunter.

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
   liest es alle Seiten bis zur höchsten Seitenzahl der Seitenleiste (ab 0.10.9 höchstens 200, vorher 30;
   mit kurzer Pause dazwischen; lehnt gg.deals mit 403 oder 429 ab, hört es auf und sagt es). Mehr Einträge je Seite
   bei gg.deals (96 statt 48) heißt weniger Seiten. Es nimmt auch Pakete, Bundles und DLC mit; übernommen werden nur Spiele,
   der Rest steht mit Zahl und Namen im Ergebnis. Unbekannte Namen daraus sucht der Abgleich bei
   Steam nach, 40 je Lauf. Ab 0.8.8 merkt es sich die Zahl, die gg.deals über der Liste nennt („We found …
   results“); stehen dort mehr Einträge, als Links zu Spielseiten da waren, sagt die Vorschau, wie viele fehlen.
   Ab 0.9.9 ebenso auf deiner Sammlung bei gg.deals (`gg.deals/collection/`): je Spiel zusätzlich das Umfeld der
   Karte (Text, Titel und Symbole), daraus erkennt das Tool den Launcher; der Name des Spiels zählt dabei nicht mit.
   Ab 0.10.9 (Lesezeichen Fassung 10) gibt es davon nur die Namen der Launcher weiter, damit auch große Sammlungen
   in die Adresse passen.
   In die Sammlung PC kommt nur, was keine andere Quelle unter demselben Namen führt.
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
  Epic steht), sonst gilt eine Spiel-ID unter 10 000 000 als vermutete Steam-ID („ungeprüft“). Dieselbe
  Datei füllt außerdem die ganze **Sammlung** mit allen Spielen außer den
  versteckten, je Spiel mit System (PC, PS4, SNES …) aus der Spalte `Plattformen`; steht auch ein
  PC dabei, gilt PC, ohne die Spalte erkennt das Tool PlayStation an Kennungen wie
  `CUSA01234_00` (PS4); Kennungen wie `NPWR01234_00` sind Trophäenlisten von PS3 oder PS Vita und
  stehen unter „PS3 / Vita“, weil Playnite die Plattform dort nicht nennt. Die Vorschau sagt es
  in einfachen Sätzen (0.7.2): „Für die Sammlung: 6 Spiele (PS1 1, PS2 2 …), alle neu. Deine anderen
  … Spiele bleiben, wie sie sind. VR-Titel: keine darin“; VR-Titel zählen für den Reiter VR und die Wunschliste. Ein neuer Export ersetzt nur die Systeme, die in ihm vorkommen: ein
  Export nur der Nintendo-Bibliothek lässt die PC-Spiele stehen. Unter VR (deine VR-Titel)
  bleiben Spiele nur für Konsolen weiter draußen. Ab 0.10.11 (Entscheidung 02.11.2026) nimmt die Sammlung aus
  Playnite keine PlayStation-Spiele mehr, auch wenn der Export sie enthält: sie kommen später aus dem ROM-Ordner
  (Retro-Liste). Schon übernommene fallen beim nächsten Abgleich weg; die Vorschau nennt ihre Zahl.
- **gg.deals-Wunschliste (CSV)** mit einer Spalte Name und Links auf die geteilte Liste.
- **Datei des Meta-Lesezeichens** oder kopierter Text der Bestellseite.
- **Meinungen (JSON)** aus einer Recherche auf Reddit und im Web: je Titel Kurzfazit, bessere
  Fassung, Mehrspieler, Pflege, Crossbuy, Crossplay, Komfort, Warnungen und Quellen. Sie stehen
  unter dem Titel als zugeklappte Zeile „Recherche, Datum: …“; Crossbuy daraus steht violett.
  Crossbuy heißt: ein Kauf im Meta Store gilt für Quest und PC-VR im Meta Store; Steam gehört
  nie dazu. Nennt die Begründung Steam, Crossplay oder nur deine Zuordnung, verwirft der Import
  den Wert und sagt es in der Vorschau. Aufbau
  in [docs/meinungen.md](meinungen.md).

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
  No-Intro nennt die Sprachen nur, wenn sie von der Sprache der Region abweichen. Ab 0.10.12 listet „Zu erledigen“
  alle Spiele mit „DE fehlt“; „ignorieren“ blendet die Marke aus (das Spiel zählt dann als „ohne Deutsch“, auch nach
  neuem Einlesen der Retro-Liste), „wieder melden“ in den Einzelheiten holt sie zurück.
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
  „Liste gilt“ (auch für alle auf einmal) blendet den Hinweis aus, bis sich ein Wert ändert. Ab 0.9.6 nimmt
  „Quellen gelten“ (auch für alle) im Tool das Genre, in dem libretro und IGDB einig sind, statt deinem; deine
  Ordner-Liste bleibt, wie sie ist, dein Genre steht in den Einzelheiten mit „deins gilt“ zum Zurücknehmen. Liest du die
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
0.3.4 zeigen eine vermutete Herkunft („vermutet“), abgeleitet aus Besitz, Wunschquellen und dem
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
- **Steam-ID „ungeprüft“:** Eine Steam-ID, die nur aus einem Namen stammt (Playnite, Suche), fragt das
  Tool im Steam-Store nach. Passt der Name und kann die App VR, gilt sie als sicher.
- **Namen lernen:** Die Namen, die Meta und Steam für einen Titel führen, merkt sich das Tool
  als weitere Namen. Spätere Importe und Suchen finden den Titel so auch unter dem anderen
  Namen.

Was offen bleibt, steht in den Einstellungen unter „Zu erledigen“: „Derselbe Titel?“,
Steam-IDs, die die Prüfung nicht bestätigt hat („passt“ oder „falsch“; eine falsche App schlägt
die Suche nicht wieder vor), Titel, die QuestStoreDB nicht fand, und Retro-Spiele mit ähnlichem
Namen in der Fassungsliste. Bundles sind dort als solche markiert. Ab 0.9.2 dazu „Meinung fehlt“:
VR-Wünsche ohne Recherche. „Auftrag kopieren“ gibt einen fertigen Auftrag mit Namen, Meta- und
Steam-ID und dem verlangten Aufbau aus; du fügst ihn in eine Claude-Routine oder einen Chat ein und
liest die Antwort als Meinungen-Datei ein (siehe [docs/meinungen.md](meinungen.md)).

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
- **IsThereAnyDeal** (ab 0.9.0, für die PC-Wunschliste): Preise jedes offiziellen Ladens (Steam, GOG, Epic, Humble
  und weitere) in Deutschland, mit Tief je Laden. Dafür auf isthereanydeal.com unter My Apps eine App anlegen und
  ihren API-Schlüssel unter „Konten und Schlüssel“ eintragen. Keyshops kommen weiter von gg.deals.

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

Nach einer Sperre (403, 429 oder Prüfseite) ruht ihr Server 24 Stunden, für alle Quellen, die ihn fragen (ab 0.10.29).
Ein Neustart mitten im Abgleich verliert weder Protokoll noch Ruhezeiten; der Lauf gilt dann als unterbrochen und
läuft bald neu. Probleme stehen als
Hinweis über den Ansichten, jeweils mit „Protokoll öffnen“: noch kein Abgleich, eine ruhende
Quelle, Auffälligkeiten der Selbstprüfung, Fehler im letzten Lauf. Einzelheiten in
[docs/abrufe.md](abrufe.md).
