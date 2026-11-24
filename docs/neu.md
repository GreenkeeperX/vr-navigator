# Was ist neu

Neueste Version zuerst. Bis 0.10.28 standen diese Einträge oben in der README; sie sind hier unverändert gesammelt.

## 0.11.3

Die README ist kurz (Zweck, Start, Einrichten, Nutzung, Betrieb); Einzelheiten stehen in `docs/` (diese Datei,
[einrichten.md](einrichten.md), [ansichten.md](ansichten.md)). Nach einem Update steht oben einmal, was neu ist
(„verstanden“ blendet es aus). Scheitert das Vorrechnen der Ansichten im Hintergrund, steht der Fehler im Protokoll
des Containers (vorher still), und der Server versucht es erst nach einer Minute wieder.

## 0.11.2

Statuskarte „Betrieb“ als letzte Karte der Einstellungen: zugeklappt nur der Gesamtstatus (grün alles in Ordnung,
violett Hinweise, rot Probleme, jeweils mit Grund), aufgeklappt Quellen, ruhende Server, die letzten Läufe und Sperren,
letzte Sicherung, letzter Wiederherstellungstest, Daten, Speicher, freier Platz und Version. Dort auch der
Leistungstest: nur auf Klick, nie während eines Abgleichs, mit erfundenen Daten in einem eigenen Prozess, ohne Netz.

## 0.11.1

Schneller nach einer Entscheidung: „DE fehlt“ ignorieren, „Liste gilt“ und „dieselbe Fassung“ rechnen nur die
betroffenen Spiele neu (0,17 statt 0,85 s mit 8000 erfundenen Spielen). Die Sammlung lädt ohne Beschreibungen (die
kommen beim Aufklappen) und wird nicht noch einmal übertragen, wenn sie sich nicht geändert hat. Messung in
[leistung.md](leistung.md).

## 0.11.0

Deine Entscheidungen zur Sammlung stehen in einer eigenen kleinen Datei (`eingaben.json`). Ein neuer Playnite-Export
löscht die übernommenen Recherchen zu Lenkrad und VR-Mods nicht mehr. Der Umzug geschieht beim ersten Start, nach einer
Sicherung und mit Prüfung; siehe [sammlung-felder.md](sammlung-felder.md).

## 0.10.29

Nach einer Sperre (403, 429, Prüfseite) ruht der ganze Server 24 Stunden, auch für den Verbindungstest, und das
übersteht einen Neustart. Der Abgleich speichert nach jeder Quelle und holt einen unterbrochenen Lauf nach. Täglich eine
Sicherung im Datenordner, monatlich ein Wiederherstellungstest. „Sicherung einlesen“ zeigt erst eine Vorschau und spielt
feldweise ein. `/healthz` für den Docker-Healthcheck.

## Stand 0.10.28

Wunschliste (VR mit Abgleich gegen die Wunschlisten der Läden, PC als Spiegel der gg.deals-Wunschliste mit Preisen und Spielinfos), Jetzt für VR- und PC-Wünsche, Sammlung (alle Spiele je System als Liste mit Spalten wie im eShopKompass, dazu der Reiter VR mit deinen VR-Titeln, Mein Stand, Filter und Vorschläge, Retro-Liste aus dem ROM-Ordner mit Spielinfos aus der libretro-database und deinen Ordner-Listen), Konten (Steam, gg.deals, Sharenite), Zuordnung aller Titel, Tief über beide Läden, Meinungen aus der Recherche, Meta-Lesezeichen, Importe und Live-Preise von QuestStoreDB (Meta), Steam
und gg.deals, dazu Gemessenes: Steam-Spieler und -Updates, Crossbuy, Version und Meta-Wertung von
VRDB, daraus das Urteil „wo kaufen“ je Wunschtitel.

## 0.10.28

Flat-to-VR. Einmal am Tag liest der Abgleich den Flat2VR Index (VR-Ports für Flachbildspiele, offene
Daten unter CC0 1.0) und den UEVR Hub (gesammelte UEVR-Profile), jeweils nur, wenn sich die Datei geändert hat. Hat ein
PC-Spiel deiner Sammlung einen Port, trägt es die Marke „VR per Mod“; die Einzelheiten nennen je Port Stand (Alpha, Beta,
stabil, aufgegeben), PCVR oder Quest ohne PC, Steuerung, Version mit Datum und bekannte Fehler, mit Link zum Ersteller
und dem Prüfdatum im Tooltip. Gibt es nur ein UEVR-Profil, steht der Hinweis „VR-Mod“ (gestrichelt), denn ein Profil
heißt nicht, dass das Spiel gut läuft; die Einzelheiten nennen Zahl der Profile, 6DOF oder 3DOF, Bewegungssteuerung und
verlinken Profil und Hub. Zugeordnet wird vorsichtig über den Namen: Ein Zusatz in Klammern muss passen (Jahr, System,
„Remake“), und passen zwei Spiele zum selben Namen, bekommt keines den Eintrag. Fällt ein Port aus der Quelle, sagt das
Protokoll, an welchem Spiel er hing. Spiele mit Port oder Profil fallen aus dem Auftrag „VR-Mods prüfen“.

## 0.10.27

Zwei Filter mehr in der Sammlung. Das Menü „Erschienen“ grenzt nach dem Erscheinungsjahr ein: „ab 2020“
zeigt 2020 und neuer, „vor 2015“ alles bis 2014, beides zusammen einen Zeitraum; Spiele ohne Jahr fallen dann heraus,
das Menü nennt ihre Zahl. Im Menü „Genre“ hat jede Zeile den Schalter „ohne“: Spiele mit diesem Genre verschwinden aus
der Liste, auch zusammen mit gewählten Genres. Ausgeschlossene Genres stehen rot und durchgestrichen im Menü, die Zahl
dahinter nennt, wie viele Spiele gerade ausgeblendet sind; unter den Filtern stehen sie als rote Marken „ohne … ×“.
Beide Filter gelten in jedem Reiter der Sammlung, auch unter VR, und stehen im Link der Ansicht.

## 0.10.26

Sagt die Recherche bei einem gekauften VR-Titel „zweitkauf“ (die Fassung im anderen Laden lohnt
zusätzlich), holt der Abgleich auch dessen Preise, und „Jetzt“ zeigt die andere Fassung mit der violetten Marke
„Zweitkauf Steam“ oder „Zweitkauf Meta“, sobald sie im Angebot nah am Tief ist. Unter „Zu erledigen“ zwei Recherchen
zur Sammlung: „Sim-Racing: Lenkrad prüfen“ für Rennspiele, die nur Steam-Schlagwörter nennen (Lenkrad mit Force
Feedback ja, teilweise oder nein; „nein“ nimmt den Hinweis weg), und „VR-Mods“ für Spiele ohne VR-Fassung und ohne
Mod laut PCGamingWiki, je Auftrag 100, die besser bewerteten zuerst (UEVR, Flat2VR, Luke Ross …). Treffer stehen
violett als „VR per Mod“ in der Sammlung und zählen im Filter VR-Mod; geprüfte Spiele kommen nicht wieder.

## 0.10.25

Der Meinungs-Auftrag nimmt nach den Wünschen auch deine VR-Sammlung, solange du ein Spiel nur in einem
Laden hast (im Auftrag „gekauft“). Neu gefragt ist dort „zweitkauf“: ob sich die Fassung im anderen Laden zusätzlich
lohnt, etwa wegen besserer Technik, mehr Inhalt oder lebendigerer Lobbys. Die Einzelheiten zeigen dann „andere Fassung
lohnt zusätzlich“ mit Grund. Das Protokoll der Zuordnung zählt fehlende Meinungen nicht mehr als offene Fälle.

## 0.10.24

Jede Liste unter „Zu erledigen“ lässt sich als CSV-Datei herunterladen, alle zusammen mit „alles
herunterladen“. Wo eine Recherche helfen kann (Ohne Meta-ID, Steam-ID prüfen, PC-Wunsch: Steam-ID, Derselbe Titel?,
Retro: ähnlicher Name, Retro: Genre weicht ab), gibt es dazu „Auftrag kopieren“ wie bei den Meinungen, mit bis zu 50
Einträgen. Die Antwort der KI ist eine JSON-Datei mit derselben Kennung je Eintrag; unter Einlesen, „Datei oder Text“
zeigt das Tool erst, was es mit jeder Antwort täte (Meta-ID eintragen, Steam-ID bestätigen oder entfernen, Paar
zusammenführen, Genre der Quellen nehmen …), samt Grund und Quellen, und übernimmt erst auf Klick. Unklare Antworten
und Einträge, die nicht mehr offen sind, bleiben liegen. Antwortet die Recherche bei „Ohne Meta-ID“ mit „keine“
(keine Quest-Fassung), verschwindet der Titel aus der Liste. Besitz-Widersprüche, Wunschlisten-Gruppen und „DE fehlt“
gibt es nur zum Herunterladen: Dafür muss jemand in deine Konten schauen, oder das Tool weiß schon mehr als eine Recherche.

## 0.10.23

Das Steam-Konto hängt eine App nur noch an einen Titel, wenn sie laut Steam VR kann, auch bei
gleichem Namen. Bisher kam so etwa die Fassung ohne VR oder ein gleichnamiges neues Spiel an einen VR-Titel, samt
„gekauft am PC“. Solche Zuordnungen löst der nächste Abgleich: Steam-ID und Steam-Besitz fallen weg, die App kommt an
diesen Titel nicht wieder, das Protokoll nennt die Titel. Von Hand gesetzte oder unter „Zu erledigen“ bestätigte
Steam-IDs bleiben.

## 0.10.22

Elf statt sieben Stränge. Quellen verschiedener Server, die nicht voneinander abhängen, warten nicht mehr
aufeinander (IGDB, PCGamingWiki und Nexus Mods, DekuDeals und Wikidata, QuestStoreDB und VRDB laufen je für sich); ein
Lauf dauert damit etwa so lange wie seine längste Quelle. Pausen und Abfragen je Server bleiben gleich.

## 0.10.21

„Aktualisieren“ ist schneller. Nach Konten und Zuordnung laufen die Quellen in sieben Strängen
gleichzeitig (Steam-Laden, PC-Wunschliste, Meta, Steam-Spieler, Spielinfos, Sim-Racing und Retro, DekuDeals und
Wikidata). An jeden Server geht trotzdem nur ein Abruf zur Zeit, mit derselben Pause wie bisher, auch wenn zwei Quellen
denselben Server nutzen. Im Protokoll steht jede Quelle als ein Block, sobald sie fertig ist; was noch läuft, steht darunter
unter „läuft gerade“, und eine Zeile „Stränge“ nennt am Ende, wie lange jeder Strang brauchte.

## 0.10.20

Auch die Vorschau des Meinungs-Imports sagt, wie viele Spiele gefunden wurden und bei welchen eine
bisherige Meinung ersetzt wird, statt „davon 0 neu“.

## 0.10.19

Der kopierte Auftrag für die Recherche hat jeden Absatz in einer Zeile, ohne Umbrüche mitten im Satz.

## 0.10.18

Nach dem Meinungs-Import steht „n Spiele haben jetzt eine Meinung“ statt „0 neu angelegt“; der
Import hängt Meinungen nur an Titel, die das Tool schon kennt, und nennt nicht zugeordnete.

## 0.10.17

Der Auftrag an die Recherche fragt zusätzlich, wie das Spiel auf der Quest 3 und am PC läuft, welche
Fassung den neueren Stand hat (auch Meta-PC gegen Steam), wie lebendig die Lobbys je Plattform sind, ob es Deutsch gibt
und wie groß der Umfang ist. Aktuellere Fassung und lebendigere Lobbys zählen halb in „wo kaufen“. Mehrspieler-Titel
kommen nach sechs Monaten wieder in den Auftrag.

## 0.10.16

Wikidata und die deutsche Wikipedia im Abgleich für alle Retro-Spiele, bis 100 je Lauf: deutsche
Beschreibung (Einleitung des Wikipedia-Artikels, wo GameTDB keine deutsche hat), deutscher Titel, USK oder PEGI, wo keine
Freigabe steht, Spielerzahl zur Bestätigung. Ein Treffer zählt nur als Videospiel mit derselben Plattform oder, wo
Wikidata nur eine andere Fassung führt, demselben Jahr. In der Sammlung steht der Filter Mehrspieler neben „max.
Spieler“ (Genre davor); der PC-Preis ist nicht mehr fett, wie die VR-Preise.

## 0.10.15

Unter Einstellungen, „Zu erledigen“ führt jeder Name zu den Einzelheiten des Spiels: VR-Titel auf die
Wunschliste VR (sonst in die Sammlung, Reiter VR), PC-Wünsche auf die Wunschliste PC, Retro-Spiele in ihr System der
Sammlung; die Zeile ist aufgeklappt, gesucht wird nach dem Namen. Schneller: Der Server rechnet Zustand und Sammlung nach
jedem Abgleich und Import vorab und hält sie bereit, bis sich eine Datei ändert; die Wunschliste PC zeigt wie die
Sammlung erst 100 Zeilen und lädt beim Scrollen nach; Preise und Daten formatiert die Oberfläche ohne Neuaufbau je Wert.

## 0.10.14

DekuDeals als zweite Quelle für die Sammlung (PC, PlayStation 4 und 5, Xbox, Switch):
je Spiel die Suche und die Spielseite, höchstens 30 Spiele je Lauf, bekannte zuerst, alle vier Monate neu. Ein Treffer
zählt nur mit gleichem Namen und der richtigen Plattform (am PC „Steam“). Daraus kommen die Spielzeit laut
HowLongToBeat (vor IGDB, IGDB bleibt im Tooltip), OpenCritic, Metacritic wo Steam keine nennt, USK oder PEGI, Deutsch
wo Steam nichts sagt; Spieler, Genre und Jahr werden bestätigt oder ergänzt, ein anderes Jahr steht violett.

## 0.10.13

GameTDB im Abgleich für GameCube, Wii, DS, 3DS und PS3, einmal im Monat je Datenbank. Damit gibt es
deutsche Beschreibungen, deutsche Titel, USK oder PEGI, Spielerzahl, Genre und Erscheinen; gefunden wird über die
Spiel-ID im Dateinamen, sonst über den Namen. PS3 bekommt die Fassungsliste von Redump („DE fehlt“). Der
Verbindungstest probiert zusätzlich Wikidata und die deutsche Wikipedia als Quelle für alle übrigen Systeme.

## 0.10.12

Unter Einstellungen, „Zu erledigen“ stehen alle Retro-Spiele mit „DE fehlt“ je System, mit
„ignorieren“ einzeln, je System oder für alle; die Marke verschwindet dann, das Spiel zählt als „ohne Deutsch“, und in
den Einzelheiten holt „wieder melden“ es zurück. IGDB liefert den genauen Erscheinungstag, wo sonst keiner da ist. Der
Verbindungstest probiert GameTDB für GameCube und Wii (die libretro-database hat dafür keine Spielinfos).

## 0.10.11

Auch aus Playnite kommen keine PlayStation-Spiele mehr in die Sammlung (sie kommen später aus dem
ROM-Ordner); schon übernommene fallen beim nächsten Abgleich weg, Retro-Einträge bleiben.

## 0.10.10

Konsolenspiele aus der gg.deals-Sammlung (Zusatz wie „(PS4)“ oder „(PS4 & PS5)“ hinter dem Namen)
kommen nicht mehr in die Sammlung PC; schon übernommene fallen beim nächsten Abgleich weg. Das Ergebnis nennt ihre Zahl.

## 0.10.9

Statt „nach Spalte“ steht die sortierte Spalte selbst in „Sortieren“, mit Richtung („Preis ▲“), in
allen Tabellen. Das Lesezeichen liest bis zu 200 Seiten der gg.deals-Sammlung oder -Wunschliste (vorher 30) und gibt
nur die Launcher weiter; bitte das Lesezeichen neu anlegen (Fassung 10).

## 0.10.8

Beim Aufklappen bleibt die angeklickte Zeile an ihrer Stelle, auch wenn darüber eine andere zuklappt.
Genres der PC-Einzelheiten (Wunschliste, Jetzt) stehen unter der Spalte Genre. Die Zeile unter der Maus wird im
Darkmode dunkler statt heller. Nach einem Klick auf einen Spaltenkopf steht in „Sortieren“ „nach Spalte“; eine andere
Wahl dort sortiert wieder danach (Jetzt und Wunschliste wie in der Sammlung).

## 0.10.7

Tooltips zu „am Tief“, Tief, Rabatt, „kaufen“ und „gut“ nennen den tatsächlichen Tiefpreis mit Laden
und Datum, den Preis jetzt und den Abstand. Im Preisverlauf steht „jetzt“ am Tief grün, beim Tiefstpreis mit ★.
Wertungen in den Einzelheiten immer in der Farbe der Wertung (auch VR und der schwächere Laden), bei PC mit der Zahl der
Rezensionen. Die Zeile unter der Maus hebt sich leicht ab. Mein Stand baut beim Klicken nur die eigene Zeile neu
(kein Zucken der Tabelle), die Zeichen sind kräftiger und sitzen in der Namenszeile mittig. Genres der Einzelheiten
stehen bündig und näher an der Zeile. Ein Tief von 0 € (Gratis-Aktion bei gg.deals) zählt bei PC-Wünschen nicht mehr
als Tief; vorher stand dadurch jeder Preis „am Tief“.

## 0.10.6

VR-Einzelheiten zeigen die Genres unter der Spalte Genre und keine Marke doppelt. Die Zeichen von
Mein Stand sind Grafiken, die nicht von der Schrift abhängen; beim Klicken verschiebt sich nichts. Filter „Crossplay“
in der Sammlung. Preisverlauf: Spalte „überm Tief“, unter „zuletzt“ Preis grün und Rabatt blau nur bei einem guten
Preis, Läden und Preise als Links.

## 0.10.5

Meta im Meta-Blau, Steam im dunkleren Blau des Steam-Logos (vorher war Steam im dunklen Modus
heller als Meta).

## 0.10.4

ein teurerer Weg (Händler statt Keyshop, ein anderer Laden) steht in den Einzelheiten der PC-Wünsche nur
noch, wenn er höchstens 8 % über dem günstigsten Preis jetzt und höchstens 10 % über dem Tief liegt; gekauft wird fast
immer zum günstigsten Preis, Ausnahmen wie günstig gekauftes Guthaben zählen nur nah am Tief (Entscheidung 02.11.2026).

## 0.10.3

Einzelheiten der PC-Wünsche zeigen Händler, Keyshop und Läden nur, wenn sie höchstens 10 % über dem
günstigsten Preis jetzt liegen; „Üblich“ und „Steam-Angebote“ nur, wenn ein Steam-Angebot in üblicher Höhe den
günstigsten Preis jetzt unterböte und höchstens 5 % über dem Tief läge (dann mit dem Preis, den es hätte). Bei
VR-Titeln bleibt beides, weil es Meta gegen Steam abwägt. VR-Einzelheiten in Jetzt und Wunschliste: links die
Angaben, ab der Spalte Meta die Karten der Läden, rechts die Kurzbeschreibung (Steam oder IGDB); bei PC-Wünschen
beginnt die Beschreibung unter „Wo“. Marken und Genres, die in der Zeile unter „+n weitere“ verschwinden, stehen in
den Einzelheiten. Crossplay ist eine Marke am Namen statt eines Zeichens an der Spielerzahl. ○ ▷ ✓ so kräftig wie
★ und ✕, Rahmen beim Überfahren vollständig. Herkunft in der Sammlung als „n Quellen“ (welche im Tooltip). Im
Preisverlauf: „typisch“ bei gg.deals der Preis, der in den letzten 90 Tagen am längsten galt; „zuletzt“ grün bei
einem guten Preis; schließen mit ✕ oben rechts (bleibt beim Scrollen stehen), Esc oder Klick daneben.

## 0.10.2

Mein Stand kennt „ignorieren“ (rotes ✕, Gegenstück zu Favorit): Ein ignoriertes Spiel kommt in keiner
Mischung und in „Überrasch mich“ mehr vor, in der Liste bleibt es (Filter „ignoriert“). Backlog ○ ist pink, der Stern
fett. Besitz mit zweiter Quelle: das Steam-Konto gegen Sharenite und die gg.deals-Sammlung, die Meta-Käufe gegen
Sharenite (Oculus) und die gg.deals-Sammlung (Launcher Meta). Widersprüche stehen in „Zu erledigen“ als Meldung, der
Besitz bleibt. „Wo kaufen“ zählt auch eine Meta-Version, die seit über einem Jahr unverändert ist, während Steam später
ein Update bekam (abgeleitet, halb, violett; Meta nennt kein Update-Datum). Pakete: Liegen mindestens zwei deiner
VR-Wünsche in einem Meta-Bundle oder Crossbuy-Paket, das das Tool kennt (Titel mit Inhalt und Meta-Preis), steht in den
Einzelheiten Paketpreis gegen die Summe der Einzelpreise, dazu die Marke „im Paket günstiger“. In den Einzelheiten der
Wünsche „Steam-Angebote“: wann zuletzt und wie oft bisher, aus dem eigenen Verlauf. Crossplay heißt nach der Quelle
„Crossplay (Steam)“ oder „Crossplay (PCGW)“, die Recherche „Crossplay Quest/PC“. Kein „≈“ mehr in der Oberfläche:
Abgeleitetes, Übernommenes und Werte aus nur einer Quelle stehen violett.

## 0.10.1

PC-Wünsche ohne Steam-ID (GOG, Epic …) bekommen Preise je Laden über die Titelsuche von
IsThereAnyDeal (nur bei gleichem Namen oder Slug). Aktive Steam-Spieler in der Sammlung kommen zuerst für
Mehrspieler-Spiele. Für VR-Titel fragt der Auftrag für die Meinungen auch die Höchstzahl der Spieler online und lokal;
sie gilt nur, wo keine Datenbank eine Zahl nennt, und steht violett da. Für Meta-Titel misst das Tool, wie
viele neue Meta-Bewertungen je Monat dazukommen (Meta nennt keine Spielerzahlen): Zeile „Meta aktiv“ in den
Einzelheiten und grau in der Spalte Aktiv, wenn Steam keine Zahl hat. Nur ein Hinweis.

## 0.10.0

Preismuster aus dem eigenen Verlauf. Aus allen Steam-Angeboten (VR-Titel und PC-Wünsche) rechnet das
Tool den üblichen Rabatt je Alter des Spiels, die Monate mit vielen Angeboten und die übliche Dauer eines Angebots
(Kasten „Was dein Preisverlauf zeigt“ in der Legende und im Preisverlauf). Liegt ein laufendes Steam-Angebot deutlich
(10 Punkte) unter dem für das Alter üblichen Rabatt, steht neben dem Namen „üblich −x %“; in den Einzelheiten steht
der übliche Rabatt immer, wenn genug Angebote da sind. Keine Vorhersage, nur die Zahl, auf der eine beruhen würde
(Entscheidung 02.11.2026). Im Preisverlauf je Laden der Rhythmus (üblicher Abstand zwischen zwei Angeboten).
Crossplay (Partien über Plattformen hinweg) aus PCGamingWiki mit den Plattformen und aus der Steam-Kategorie
„Plattformübergreifender Mehrspielermodus“: Zeichen ⇄ in der Spalte max. Spieler, Zeile „Crossplay“ in den
Einzelheiten; Crossplay zwischen Quest und PC aus der Recherche bleibt in den Meinungen.

## 0.9.9

Das Lesezeichen „Seite lesen“ liest auch deine Sammlung bei gg.deals, samt Launcher je Spiel (Steam,
GOG, Epic, Ubisoft, EA, Battle.net, Xbox, Amazon, itch, Humble, Rockstar). Spiele, die weder Playnite noch das
Steam-Konto noch deine VR-Titel am PC unter demselben Namen führen, stehen damit in der Sammlung PC (Herkunft
„gg.deals-Sammlung“). Das Lesezeichen neu anlegen (Fassung 9).

## 0.9.8

In allen Tabellen kürzen sich erst die Genres, dann die Marken neben dem Namen zu „+n weitere“;
die Einzelheiten stehen im Raster der Zeile (links die Angaben, ab der Spalte Genre die übrigen Genres, Mein
Stand, Beschreibung, Gespielt), Steam-Wertungen dort immer in Prozent, Marken nicht doppelt; immer nur ein Eintrag
offen; im Preisverlauf alle Läden auf einmal an- oder abwählen; Ladenfarben für Steam, Microsoft, Humble,
Fanatical, Green Man Gaming und Keyshop.

## 0.9.7

Spiele aus dem Steam-Konto ohne Playnite-Eintrag stehen in der Sammlung (Herkunft „Steam-Konto“),
Preise werden 18 Monate behalten, die Tabellen in Jetzt und Wunschliste sortieren per Klick auf den Spaltenkopf,
die Einzelheiten folgen einer festen Reihenfolge (Wertung, Trend, Spieler, Koop, Spielzeit, Aktiv, Meta, Update,
USK, Erschienen, VR per Mod, Sim-Racing, Mods), PC-Wünsche zeigen den Rabatt des günstigsten Ladens.
