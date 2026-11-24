# Oberfläche: Farben, Marken, Klappen

Verbindliche Regeln für `app/static/` (`index.html`, `style.css`, `js/app.js`), übernommen aus
dem eShopKompass. Wer Farben, Marken oder Bezeichnungen ändert, passt diese Datei und
`docs/ansichten.md` im selben Commit an (bis 0.11.1 stand das in der README).

## Grundsatz

Jede Farbe hat genau eine Bedeutung. Was nichts entscheidet, bleibt grau. Hell und dunkel
müssen beide lesbar sein; jede Farbänderung wird in beiden geprüft.

| Farbe | Token | Bedeutung | Beispiele |
|---|---|---|---|
| Blau | `--deal` | Rabatt | `−67 %`, `−40 % Gutschein` (`.b.deal`, ab 0.9.4 nur blaue Schrift ohne Fläche, Ton wie im eShopKompass) |
| Gold | `--best` | am Tief (niedrigster Preis beider Läden in 18 Monaten, bis 2 % darüber; ab 0.9.4 heißt es überall „Tief“, nicht mehr „Bestpreis“) | „★ am Tief“ im Preisfeld (`.bl.at`, `.star`) |
| Grün | `--go` | spricht für dich, gelingt | Urteil „kaufen“ (gefüllt, `.vd.buy`) und „gut“ (umrandet, `.vd.good`) wie im eShopKompass, günstigerer Laden (Rahmen `.shop.win`, „5 € günstiger“ ab 1 €), besser bewerteter Laden (`.rate.win`, „Meta +8“), Quelle „ok“ |
| Rot | `--stop` | spricht gegen dich, misslingt | Aufpreis über dem Tief (`.over`, „+7 €“), Fehler einer Quelle |
| Violett | `--warn` | prüfen, veraltet, geschätzt, unsicher | „Steam-ID ungeprüft“ (Wunschliste; Sammlung „Steam-ID prüfen“), Wert aus nur einer Quelle, abgeleitet oder übernommen (`.gxc`, ab 0.10.2 überall statt „≈“), Stand älter als zwei Tage, Hinweise oben, widersprechende Quelle („Tabelle: nein“), Recherche (gestrichelte Linie links, „Recherche“), ignoriert ✕ ist rot (`--stop`, `.gign`) |
| Grau | `--chip`, `--muted` | Information ohne Wertung | Meta, PC, „Wunsch“, „Wunsch · Tabelle“, „ohne Crossbuy“, Feld ohne Preis (gestrichelt) |

Ausnahme, nur für die Reiter je System in der Sammlung (Entscheidung 27.10.2026): der gewählte
Reiter trägt die Farbe seiner Familie, Nintendo rot (`--sys-nin`), PlayStation blau (`--sys-ps`),
PC grün (`--sys-pc`), VR im Türkis des Tools (`--brand`), „Alle“ in `--accent`. Diese Töne sind
eigene Tokens und stehen nirgends sonst.

Ausnahme für die Marke „Wo“ (ab 0.9.4, Entscheidung 28.10.2026): Laden als dünn umrandete Marke ohne
Fläche in der Farbe des Ladens, Meta `--wo-meta`, Steam und Händler `--wo-steam`, Keyshop `--wo-key`, „egal“
grau gestrichelt (`.wo`, `woChip`). Das Preisurteil steht nur im Tooltip. Ein Klick öffnet den Preisverlauf.
Diese Töne stehen nur in `.wo-*` (Test). Ab 0.9.8 (Entscheidung 02.11.2026, vom dunklen Modus aus) je Laden
die Farbe seiner Marke (`shopCls`): Steam im dunklen Blau des Steam-Logos `--wo-steam`, Meta im helleren Meta-Blau
`--wo-meta` (ab 0.10.5, Entscheidung 02.11.2026; vorher war Steam im dunklen Modus heller als Meta), Microsoft/Xbox grün `--wo-ms`, Humble grau
`--wo-humble`, Fanatical orange `--wo-fan`, Green Man Gaming grünlich `--wo-gmg`, Keyshop gelb wie Kinguin
`--wo-key` (0.9.7 graublau); Epic, GOG, „Händler“ und alle übrigen in der Schriftfarbe.

Ausnahme für die Marke „Crossbuy“ (ab 0.9.7, Entscheidung 01.11.2026): Goldgelb in eigenen Tokens
`--cb`/`--cb-bg` (`.b.cb`), damit sie sich neben dem grünen „Preissturz“ abhebt. Nur diese Marke.

Rabatt bei PC-Wünschen (ab 0.9.7): blaue Marke `−40 %` vor dem Preis wie bei VR, vom günstigsten
offiziellen Laden laut IsThereAnyDeal (`r.cut`, Laden im Tooltip). Ohne IsThereAnyDeal keine Marke.

Weitere Ausnahmen in der Sammlung, übernommen aus „Spiele“ im eShopKompass (0.6.0, Entscheidung
27.10.2026): Die Wertung ist ein Farbton von Rot über Gelb nach Grün (`.gsc`, `--sh` aus 50 bis
95 %), Genres stehen als Blasen im Farbton ihrer Verwandtschaft (`.chip.gg`, `G_HUE`; violett
bleibt frei). Mein Stand: Backlog ○ pink (`--pink`, ab 0.10.2), angefangen ▷ blau, durchgespielt ✓ grün, Favorit ★
gold und fett (Kontur `-webkit-text-stroke`, die Größe bleibt; ○ ▷ ✓ ab 0.10.3 mit 1 px ebenso kräftig; beim Überfahren
liegt der Rahmen des Knopfs oben, `.seg button:hover`), ignoriert ✕ rot (Tooltip „Nie wieder
vorschlagen“; Gegenstück zu Favorit, nie in Mischungen und Vorschlägen, nur mit dem Filter „ignoriert“).
Ab 0.10.6 (Entscheidung 02.11.2026) sind alle fünf Zeichen kleine SVG-Grafiken (`mIcon`, `.mi`) statt
Schriftzeichen: gleiche Strichstärke, 1 em groß, optisch mittig zum Text (`vertical-align:-.13em`), ☆ als leere und
★ als volle Form; nichts hängt mehr von der Schrift ab, beim Klicken verschiebt sich nichts. Abstand unter der
Überschrift „Mein Stand“ wie unter „Gespielt“ (`.gdm>.fl+.gmk`); ab 0.10.7 kräftiger (Strich 2,4, ☆ 1,4) und in der
Namenszeile 15 px mittig ohne Einfluss auf die Zeilenhöhe (`.gme .mi`); ein Klick baut nur Knöpfe und Namenszeile neu
(`patchMarks`), die ganze Tabelle nur bei aktivem Filter oder Mischung;
nur als Zeichen, nie als Fläche. Die Marke „VR“ hinter dem Namen ist türkis gefüllt
(`.b.vrb`). Der gewählte System-Reiter: Linie in der Familienfarbe, Schrift in `--ink`
(Nintendo-Rot `#e60012`, dunkel `#ff3d48`).

Text (0.7.2, wie eShopKompass 1.7.15, Entscheidung 27.10.2026: der Darkmode blendete): Im Dunkeln ist
die Grundschrift gedeckt (`--ink` #cdd5d4 statt #e5ebea, im Farbton des Tools). Hell (`--ink-hi`)
bleiben nur, was bewusst hervorsticht: der Name oben (`header.top h1`), Überschriften (`h1`–`h4`),
der aktive Reiter (`nav button.on`, `.systabs button.on`), der Name der offenen Zeile in der Sammlung
(`.gr.open .g-n`) und der große Preis je Laden (`.shop .big`). Im Hellen sind beide Töne gleich.
Gefüllte Knöpfe (primär, gewählt: `button.primary`, `.chips button.on`, `.seg button.on`,
`.bar .tools>button.on`, `label.btn`) nutzen alle `--accent`, im Dunkeln so hell wie `--ink`, also
gleich hell. Gewählte Knöpfe sind nicht fett, sonst wächst der Knopf und die Reihe springt; fett
bleiben nur Reiter (wie im eShopKompass) und die Einträge im Ansichtsmenü (untereinander, ohne Springen).

Switch-Spiele aus dem eShopKompass (0.7.3) zeigen ihre Angaben wie dort ohne Violett (geprüft hat
der eShopKompass); die Wertung ist Metacritic, sonst OpenCritic, ohne „%“. Mein Stand steht in den
Einzelheiten nur als Text („ändern im eShopKompass“), Knöpfe gibt es dafür nicht. Die Spalte
Spielzeit erscheint nur, wo ein Spiel eine hat.

Herkunft am Wert: ohne Farbe gemessen oder von Hand; violett (`.gxc`) abgeleitet, übernommen oder nur aus einer
Quelle, der Tooltip nennt die Quelle. Kein „≈“ (Entscheidung 02.11.2026, seit 0.10.2 überall; in der Sammlung seit
0.6.1). Auf Marken mit eigener Farbe gilt Violett über `.b.gxc`, `.shop .bl.gxc`, `.g-buy.gxc`;
„Tabelle“ (samt Datum, wo Platz ist) aus der Vergleichstabelle; violett gestrichelt Recherche.
Links stehen in Textfarbe, unterstrichen. Erklärungen stehen einmal in der Legende („?“), nicht
über jeder Liste; über einer Liste höchstens eine Zeile.

## Titelkarte

Jetzt und Wunschliste (`.item.wi`), immer in dieser Reihenfolge:

1. Kopf (`.hd`): Name, „Wo“ (ab 0.9.4 `.wo` wie oben, vorher `.vd.wb`), dann die Marken; in den Einzelheiten
   einer Tabelle nur, wenn es Marken gibt. Die
   Gründe stehen in der Zeile „Wo“; ab 0.8.26 auch „Steam-Wertung fällt“ oder „steigt“ (Trend, zählt halb). Die
   Legende nennt die Gewichte.
2. Preise (`.shops`): zwei feste Felder, Meta links, Steam rechts (`.shop`; ohne Preis
   `.shop.none`, gestrichelt, „kein Preis“). Je Feld Preis, Rabatt, darunter `bestLine`: rot
   „+x € über dem Tief“ (jeder Aufpreis rot, Entscheidung 26.10.2026) und das Tief mit Laden oder gold
   „★ am Tief“, gemessen am niedrigsten Preis beider Läden (`best_all`); kommt er aus dem
   anderen Laden, klein darunter der eigene Tiefstpreis („Steam-Tief“). Der günstigere Laden:
   `.shop.win` mit „x € günstiger“. Darunter, linksbündig unter den Preisen, der Knopf „Preisverlauf“
   (ab 0.9.4, `.pr .vlr`).
3. Fakten (`.facts`): festes Raster mit zwei Spalten, links der kleine graue Name (`.fl`),
   rechts der Wert (`.fv`): zuerst „Wo“ mit den Gründen je Laden (`.wbl`; der gewählte Laden zuerst,
   der andere grau, Abgeleitetes und Recherche violett), dann Wertung, Spieler, Update, Meta-Version; nur was es gibt.
4. Recherche, Notiz.
5. Klappe (`details.more`, nicht gemerkt, nicht bei „alle aufklappen“); die Zeile nennt den
   Inhalt („Bestpreise · gg.deals · Tabelle · Links · bearbeiten“): Bestpreise je Laden,
   gg.deals, Tabelle, Links, Bearbeiten.

Die Karten nutzen die ganze Breite des Fensters. Ab 900 px stehen Preise (bis 560 px) und
Fakten nebeneinander. Die Einzelheiten eines VR-Titels in der Sammlung zeigen Marken, Fakten,
Recherche, Notiz und die Klappe.

## Sammlung

Wie „Spiele“ im eShopKompass (0.6.0): eine Liste (`.glist`) mit Zeilen im Raster (`.gr`), die
Spalten (`--gcols`) wählt die Ansicht je Reiter aus `COLS`; eine Spalte erscheint nur, wenn ein
Spiel im Reiter dafür einen Wert hat. Leere Zellen zeigen einen grauen Strich. Der Kopf
(`.gr.nph`) sortiert per Klick (`data-act="tsort"`, gemerkt in `vn.view`, `sorts`), Enter und
Leertaste ebenso; der dritte Klick nimmt die Sortierung zurück. Der Name ist ein Knopf und klappt
die Einzelheiten (`.gd`) auf: links nur Angaben ohne eigene Spalte (`.gdf`, Name und Wert), rechts
Mein Stand (`.gdm`), darunter klein Herkunft und Links. Die Genre-Zelle der offenen Zeile zeigt alle
Genres (ohne `fit`), statt sie in den Einzelheiten zu wiederholen (0.6.2). Erscheinen, Entwickler und
Verlag stehen im Tooltip am Jahr. Die Zeile richtet ihre Zellen oben aus (`align-items:start`), damit
Name und Spalten beim Aufklappen nicht springen (0.7.1). Die Kurzbeschreibung (`.gdesc`) steht unter Mein
Stand, wie im eShopKompass höchstens 68 Zeichen breit und vier Zeilen hoch, ein Klick zeigt alles
(`V.gDesc`, markieren klappt nicht um; 0.7.2). Die Wertung in den Einzelheiten steht als Zahl
(„Steam 97 % · Metacritic 96“, Farbton wie die Spalte; Steams Worte wie „Sehr positiv“ und die Zahl
der Rezensionen im Tooltip; 0.7.2). „alle aufklappen · alle zuklappen“ (`.foldall`) steht hinter
Sortieren (`V.gAll`, einzeln zugeklappte in `V.gShut`, nicht gemerkt, Wechsel des Reiters setzt
zurück); „alle aufklappen“ geht bei höchstens 150 Spielen der Liste (`G_ALL`), sonst grau mit
Tooltip, der die Zahl nennt (0.7.4). Unter 760 px stehen die Werte je Zeile mit kleinem
Namen davor untereinander, leere Werte fallen weg.

Die Einzelheiten (`.gd`) nutzen dasselbe Raster wie die Zeile: Angaben in der Spalte des Namens,
Mein Stand (`.gdm`) ab der zweiten Spalte (Spieler), oben bündig; so steht er in jedem Reiter an
derselben Stelle. Hat ein Reiter keine mitwachsende Spalte (etwa nur „Jahr“ oder gar keine), nutzen die
Einzelheiten ein eigenes Raster (`--dcols`: Name, dann mindestens 320 px für Mein Stand), damit nichts
über den Rand ragt (0.7.7). Die Marke von Mein Stand hinter dem Namen hat eine feste Breite und Höhe, damit
die Zeile beim Setzen nicht springt. Genres in der Zeile: `.gtags.fit`, einzeilig; `fitTags()`
blendet aus, was nicht passt, und hängt „+n weitere“ (`.chip.gmore`) an. Reihenfolge
(`genreOrder`): seltenstes in der Sammlung zuerst, dann Alphabet, „Sonstiges“ zuletzt. Spalte
Launcher: am PC der Launcher, bei Konsolen unter „Alle“ das System.

## Hell, dunkel, System

- Runder Knopf oben rechts mit dem Zeichen der Wahl (halber Kreis System, Sonne, Mond); ein Klick
  öffnet die drei Stufen, ein Klick daneben oder Esc schließt sie. Vorgabe ist System.
- `data-theme="light|dark"` am `html`-Element, ohne Angabe gilt `prefers-color-scheme`.
  Gemerkt unter `vn.theme`; ein Skript im Kopf setzt es vor dem ersten Zeichnen.
- Die dunklen Tokens stehen zweimal (Gerät dunkel, Wahl dunkel) und müssen gleich bleiben; ein
  Test prüft das.

## Klappen

- Jede Gruppe mit mehr als einer Zeile ist ein `details` mit `data-kc`. In den Einstellungen
  klappen nicht die Karten, sondern ihre Teile (`details.sub`: Protokoll, Verbindungstest,
  Zeitplan, jeder Import). Die Klappzeile nennt zugeklappt das Nötigste (Stand, letzte Zeile des
  Protokolls, „zuletzt … erkannt, … neu“, Schlüssel ja/nein); die Kartenüberschrift trägt grau
  ihren Stand. Offen ist die Vorgabe, mit `data-shut` zu (etwa „Schon im Besitz“ oder ein Import,
  der schon lief). Gemerkt wird je Browser nur die Abweichung (`vn.view`, `folds`).
- Gibt es mehrere Gruppen, steht „alle aufklappen · alle zuklappen“ in der Werkzeugzeile bzw.
  in der Sprungleiste.
- Während einer Suche ist alles offen, damit kein Treffer versteckt bleibt; das zählt nicht als
  Wahl.
- Kopf einer Gruppe: fetter Name, graue Zahl.

## Reiter und Werkzeuge

- Kopfleiste (Name, Stand, Aktualisieren, Reiter) kommt beim Scrollen mit, blendet nach 300 px
  nach unten weich aus (0,8 s) und nach 40 px nach oben wieder ein, wie im eShopKompass; kleine
  Gegenbewegungen unter 8 px zählen nicht. Ohne Bewegung (reduzierte Bewegung) ohne Übergang.
- Reiter: Jetzt, Wunschliste (0.8.2, Unterreiter als `.systabs`, `V.wsub`, ab 0.8.7 PC zuerst und Vorgabe; PC in
  Grün der Familie PC, ohne bestätigte VR-Spiele (`pcIsVr`), Liste im Raster der Sammlung `.glist.pcw`, Name verlinkt
  gg.deals, Marken „Paket“, „DLC“ grau, „VR“ violett nur aus dem Namen, „schon in der Sammlung“ violett,
  „nah am Tief“ grün; ab 0.8.11 Spalten Wertung, Spielzeit, Genre mit `gSc` und `gGenres` wie in der Sammlung, der
  Name klappt Einzelheiten auf (`pcRow`, `pcDetail`, `V.pwOpen`), die Links zu gg.deals und Steam stehen dort klein
  unten), Sammlung, Einstellungen (die Bibliothek ist seit 0.6.0 der Reiter
  VR in der Sammlung; ein gemerkter Reiter „Bibliothek“ öffnet ihn). Am Reiter eine graue Zahl oder ein
  Wort („läuft“, „Fehler“, „1 prüfen“). Am Handy blendet die Leiste rechts weich aus, solange
  weitere Reiter folgen.
- Einstellungen in der Reihenfolge der Daten: Sprungleiste oben (bleibt beim Scrollen stehen),
  „Zu erledigen“ (nur wenn etwas offen ist), Einlesen (Konten und Schlüssel, Lesezeichen, ein
  Feld für jede Datei), Abgleich (oben „automatisch alle … Stunden“, speichert sofort; Quellen,
  „Aktualisieren“, „Beschleunigt auffüllen“ (0.8.6, Lauf von Hand mit fünffachen Grenzen), „Verbindung testen“, klappbar Verbindungstest und Protokoll) und Sicherung
  (drei Knöpfe wie im eShopKompass: Abgleichsdaten herunterladen, Sicherung herunterladen,
  Sicherung einlesen). Die Klappe „Quellen“ nennt den Stand farbig wie im eShopKompass
  („10 ok“ grün, „1 mit Problem (gg.deals)“ rot), aufgeklappt eine kompakte Tabelle (`.mini-t`: Quelle,
  Zustand farbig, Zeit, Abrufe und Meldung); Knöpfe in der Zeile `.bar.slim` sind so hoch wie
  im eShopKompass.
  Das Protokoll ist zu, außer der letzte Lauf hatte Fehler.
- Ab 0.11.2 als letzte Karte „Betrieb“ (V-5): eine Klappe „Zustand“, deren Zeile den Gesamtstatus nennt („alles in
  Ordnung“ grün, „n Hinweise“ violett, „n Probleme“ rot, dahinter die Gründe). Zu ist die Vorgabe, nur bei einem
  Hinweis oder Problem offen. Darin eine kurze Tabelle (Version, Sicherung, Wiederherstellungstest, Daten, Speicher,
  Platz) und Klappen für Quellen, ruhende Server, Läufe, Sperren, Dateien und den Leistungstest. Kein Datenalter als
  Spalte oder Marke (Entscheidung 24.11.2026).
- Werkzeugzeile: Suche mit eigenem ×, Esc leert sie ebenso; dahinter „Sortieren“ als Auswahl,
  Menüs (`details.menu` mit `data-menu`, nicht `data-kc`) mit Häkchen und „?“ für die Legende.
  Ein Menü zur Zeit; ein Klick daneben oder Esc schließt es; am Handy klappt es über die volle
  Zeilenbreite auf. Gewählte Filter stehen darunter als Marken mit × (`.chips.act`).
- Sammlung öffnet im Reiter PC (gibt es keine PC-Spiele, „Alle“); der gewählte System-Reiter ist
  in seiner Familienfarbe unterstrichen (siehe Grundsatz). Reiter (0.7.4, Entscheidung 27.10.2026):
  Alle, PC, VR, dann je Familie einer (`FAMS`: PlayStation, Nintendo, Weitere für alle übrigen; eine
  Familie mit nur einem System steht als dieses System). Der Familienreiter (`@ps`, `@nin` …)
  zeigt alle Spiele der Familie; rechts daneben gleiten ihre Konsolen aus (`.subtabs`, kleiner,
  `.anim` nur beim Wechsel der Familie, nicht bei reduzierter Bewegung). Ist eine Konsole gewählt,
  bleibt die Familie halb unterstrichen (`.part`). Das Gleiten (0.7.6: 0,7 s, Kurve wie die Kopfzeile) mit Aufdecken von
  links (`clip-path`); wird gleich danach neu gezeichnet, läuft es mit negativer Verzögerung weiter
  (`V.famAt`), statt abzubrechen.
- Switch-Spiele (0.7.5, Entscheidung 27.10.2026): ein Reiter „Switch 2“ für beide, Filter „System“
  (alle, Switch 2, nur Switch, `d.sw`; nur in diesem Reiter; ab 0.8.20 ein Menü am Ende der Filterzeile, damit die übrigen
  Filter beim Wechsel der Reiter an ihrem Platz bleiben). Stehen im Reiter nur Spiele mit `kv`,
  gelten auch dessen Filter: Spielweise (`K_HOW`, statt Mehrspieler), Spielzeit, USK (0.7.6). Mit der Zeile aus dem eShopKompass (`kv`) gelten dessen
  Spalten (`K_COLS`, Kopf „Spieler“ über Konsole, Lokal, Online), Marken (`.lgt`: Switch 2, S2-Upgrade,
  fehlende Spielmodi, GameShare blau, ohne Deutsch rot, „aus: Paket“) und Einzelheiten (`kDetail`);
  violett heißt dort wie hier: Nintendo nennt anderes als DekuDeals; OpenCritic grau kursiv (`.galt`),
  USK 16 blau, 18 rot. Mein Stand nur lesend; „eShopKompass“ fett, „eShop“ im Nintendo-Rot wie in seiner
  Kopfzeile, ohne Unterstrich (`a.eshl`), öffnet das Spiel dort.
- Rangfolge je Feld (0.8.0, `collection.merge_igdb`): Eine Ersatzquelle bei der Wertung steht grau kursiv
  (`.galt`, wie OpenCritic): am PC jede IGDB-Wertung (Steam zählt zuerst), sonst die IGDB-Gesamtwertung.
  Spieler aus Playnite, wenn IGDB das Spiel kennt, aber keine Zahl nennt: violett. Genres und Mehrspieler:
  violett, was nur eine Quelle nennt, solange eine andere etwas sagt (`gc`, `mpc`); kennt sonst keine
  Quelle Genres, gilt IGDB als bestätigt. Tooltips nennen die Quellen (`g.srcs`). Die Einzelheiten
  wiederholen die Wertung der Zeile nicht, nur weitere (Metacritic, IGDB neben Steam).
- VR per Mod (0.8.1): Marke „VR per Mod“ (`.b`) nach PCGamingWiki „hackable“; nur Nexus-Mods mit VR im Namen
  oder vorpX: „VR-Mod“ (`.b.vrq`, türkis gestrichelt in der Farbe der VR-Marke, ab 0.8.20 ohne „?“), ein Hinweis. Filter „VR per Mod“ (`d.vm`) erscheint, wenn ein
  Spiel im Reiter eins von beiden hat. Einzelheiten: Zeilen „VR per Mod“ und „Nexus Mods“ mit Links.
- Filter „Erschienen“ (ab 0.10.27, Menü `yr`, `d.y0` und `d.y1`): „ab“ schließt das Jahr ein, „vor“ nicht; zur Wahl
  stehen die Jahre des Reiters. Spiele ohne Jahr fallen heraus, sobald einer der beiden gesetzt ist; das Menü nennt
  ihre Zahl. Im Kopf des Menüs steht die Wahl („ab 2020, vor 2023“), darunter je eine Marke mit ×.
- Genres ausschließen (ab 0.10.27, `d.gnot`): im Menü „Genre“ hinter jeder Zeile der Schalter „ohne“ (`.gnot`). Ein
  Genre ist entweder gewählt oder ausgeschlossen. Ausgeschlossen: rot (`--stop`), Name durchgestrichen, die Zahl mit
  Minus nennt die gerade ausgeblendeten Spiele; im Kopf des Menüs ein rotes „−n“, unter den Filtern rote Marken
  „ohne … ×“. „Auswahl leeren“ nimmt Häkchen und Ausschlüsse zurück.
- Flat-to-VR (ab 0.10.28): ein Port laut Flat2VR Index (`g.f2vr`, nicht nur aufgegebene) gibt die gefüllte Marke
  „VR per Mod“ (`.b.vrb`), nur ein UEVR-Profil (`g.uevr`) den Hinweis „VR-Mod“ (`.b.vrq`). Zeile „VR per Mod“ in den
  Einzelheiten: je Port Name mit Link, Stand („aufgegeben“ rot), Plattform, Steuerung, Version mit Datum, bekannte
  Fehler; Quelle und Prüfdatum im Tooltip (`f2Port`). UEVR violett mit Zahl, 6DOF oder 3DOF und Bewegungssteuerung,
  Links „Profil“ und „UEVR Hub“ (`uevrHtml`).
- Filter „Crossplay“ (ab 0.10.6, `d.xp`): Spiele mit Crossplay laut PCGamingWiki oder Steam; erscheint, wenn ein Spiel
  im Reiter es hat.
- SimRacing (ab 0.8.12, vorher „Lenkrad“): Marke orange gefüllt (`.b.simb`, Token `--sim`), wie VR türkis (`.b.vrb`);
  „SimRacing“ orange gestrichelt (`.b.simq`). Ab 0.8.20: bestätigte Marken VR, VR per Mod und SimRacing (`.b.vrb`, `.b.simb`)
  durchgehend umrandet in ihrer Farbe wie „Geheimtipp“, Hinweise gestrichelt ohne „?“; ein „VR“ nur nach dem Namen ebenfalls türkis gestrichelt. Filter „SimRacing“ (`d.wh`) und im Reiter PC „VR“ (`d.vr`, nur bestätigte VR-Marken).
- Geheimtipp (ab 0.8.12): grün umrandet (`.b.gemb`), erst ab Wert 0,4 (`GEM_MIN`); ab 0.8.24 gedämpft (Rand 45 % Grün,
  Schrift zwischen Grün und `--muted`), damit die Marke nicht heraussticht.
- Preise als Links (ab 0.8.12, `extLink`, `a.pl` in Textfarbe): VR-Karte Meta und Steam in den Laden, gg.deals-Zeile zu
  gg.deals; PC-Wunschliste der Preis zu gg.deals (Händler, Keyshop, Tief und Stand im Tooltip, `pcPriceTip`), ★ gold
  vor dem Preis am Tief (bis 2 %), Spalte „zum Tief“ als roter Betrag `+x €` ohne Fettdruck (`.over`, Prozent im Tooltip),
  am Tief grün „am Tief“ (`.g-buy`, ab 0.8.17 wie „am Bestpreis“ im eShopKompass). Spalten ab 0.8.17: Spiel, Preis,
  zum Tief, Wertung, Genre, Spielzeit, Spieler, Jahr (`PC_COLS`); ab 0.8.19 statt Spieler „Mehrspieler“ mit der Zahl
  dahinter („coop, online bis 4“). Ab 0.9.4: Spiel, max. Spieler, Preis, überm Tief, Wo (Keyshop, sonst der günstigste Händler laut
  IsThereAnyDeal, sonst „Händler“), Wertung, Rezensionen, Genre, Spielzeit, Aktiv, Jahr.
- Spaltenreihenfolge der Sammlung (ab 0.9.4 „max. Spieler“ zuerst, dann wie bisher; ab 0.8.19, `COL_ORDER`): Wertung, Genre, Spielzeit, Mehrspieler, Spieler, dann Jahr,
  Rezensionen, Launcher; Sprache (Retro) vor der Wertung. Reiter VR: Besitz, Meta, Steam, Spieler, Update, Crossbuy,
  Recherche. Die CSV folgt der gezeigten Reihenfolge.
- Spalten ab 0.8.23 (Entscheidung 28.10.2026), eine Reihenfolge für alle Tabellen (`COL_ORDER`, `PC_COLS`, `VR_COLS`,
  `K_COLS`): Spiel, Wertung, Rezensionen, Genre, Spielzeit, max. Spieler, Aktiv, Sprache, Launcher oder System (Kopf
  „System“, wenn der Reiter keine PC-Spiele hat), Jahr ganz rechts. Preise und Wo stehen in den Wunschlisten vor diesem
  Block; Reiter VR: Wertung, Rezensionen, Aktiv, Update, Crossbuy, Besitz, Recherche. Breiten überall gleich: Spiel
  `minmax(180px,1.5fr)`, Wertung 70, Rezensionen 98, Spielzeit 66, max. Spieler 96, Aktiv 56, Update 62, Jahr 44 px;
  den Rest nimmt Genre, sonst Recherche oder Wo.
- „max. Spieler“ (`gMaxPl`, Switch `kMaxCell`): die Zahl; ohne Zahl grau „2+“ bei bekanntem Mehrspieler (ab 0.9.7
  wieder, 0.9.5 und 0.9.6 „–“; Entscheidung 01.11.2026), grau „1“ für Einzelspieler (laut Steam oder IGDB ohne
  Mehrspieler, `plSolo`). Sortiert zählt „2+“ als 2 (`plSort`). Die Arten im Tooltip.
- Spieler in den Einzelheiten (ab 0.9.7, `plKinds`, `plRows`): die Zeile „Spieler“ an dritter Stelle, die Zahl fett vorn,
  „**8** online · **2+** lokal · **8** LAN“ (ohne Zahl „2+“, MMO ohne Zahl), darunter die Zeile „Koop“ nach demselben
  Schema („**4** online · **2** lokal“, Koop ohne Art „**2+**“). Violett, was nur eine Quelle nennt; Quelle der Zahl im
  Tooltip (IGDB, PCGamingWiki, beide einig). Einzelspieler bekommen keine Zeile. Switch (`kDetail`): „**1–4** an einer
  Konsole · **2–8** lokal drahtlos · **2–12** online“, Koop laut IGDB darunter.
- Reihenfolge der Einzelheiten (ab 0.9.7, Entscheidung 01.11.2026), überall, soweit die Zeile vorkommt: Wertung, Trend,
  Spieler, Koop, Spielzeit, Aktiv, Meta, Update, USK, Erschienen (Entwickler und Verlag im Tooltip, keine eigene Zeile),
  VR per Mod, Sim-Racing, Mods (Nexus Mods). Danach, was es nur dort gibt: bei PC-Wünschen die Preise (Preissturz,
  Jetzt, Tief, Läden, Preisverlauf), bei Retro-Spielen Gesucht, Dateien und die Ordner-Liste, bei Switch Online und
  GameShare vor USK. Ab 0.9.8 (Entscheidung 02.11.2026) stehen die Einzelheiten im Raster der Zeile: links die
  Angaben bis vor die Spalte Genre (`--gc`, `gCol`), rechts ab der Spalte Genre die Genres, die in der Zeile keinen
  Platz hatten (`.ggen`, füllt `fitAll`), dann Mein Stand, die Beschreibung und „Gespielt“ ganz unten; reine
  Meta-Titel: „Gespielt: unbekannt“, der Meta Store nennt keine Spielzeit. Die Genres der Zeile bleiben auch offen
  einzeilig, damit die Angaben links oben beginnen. Steam-Wertung in den Einzelheiten immer als farbige Prozentzahl
  (`spct`), unter 50 Rezensionen nur die Zahl. Marken eines VR-Titels nebeneinander (`.gbadges`), in der Reihenfolge
  Steam (Launcher), Meta, Bundle, Crossbuy oder ohne Crossbuy, SimRacing; was die Zeile schon zeigt (Marke oder
  Spalte Besitz, Crossbuy), fällt weg. In den VR-Wünschen statt der zweiten Wunschlisten-Marke nur „+ Meta“ usw.
- Kürzen in der Zeile (ab 0.9.8, alle Reiter): erst die Genres (`fitTags`, „+n weitere“), dann die Marken neben dem
  Namen (`fitMarks`, „+n weitere“ grau, die übrigen im Tooltip). Spalte Spiel 2,2 zu 1 gegen Genre. In jeder Tabelle
  ist immer nur ein Eintrag offen, auch in „Jetzt, Alle“.
- Preisverlauf (ab 0.9.8): vor den Läden „alle abwählen“ bzw. „alle anwählen“ (gestrichelt, `vlall`).
- Sprachen (ab 0.9.5, Entscheidung 28.10.2026): nur, wenn Deutsch fehlt, als rotes „ohne Deutsch“ (`.gno`) klein in
  der Zeile unten der Einzelheiten, die Sprachen im Tooltip; gilt für PC, Retro, Switch und die eShopKompass-Zeilen.
- Reiter VR der Sammlung (ab 0.9.5): Spiel, max. Spieler, Wertung, Rezensionen, Genre, Aktiv, Update, Crossbuy, Besitz,
  Recherche (130 px); Genre und Spieler aus den VR-Spielinfos (`r.info`).
  Filter Mehrspieler in Sammlung und Wunschliste PC (`V.pcMp`).
- „Aktiv“ (`gActive`): Steam-Spieler gerade eben, überall dieser Name (auch die Zeile in der VR-Karte). Rezensionen
  (`gRev`): Steam-Zahl, ab einer Million kurz („1,9 Mio.“), Meta-Bewertungen im Tooltip.
- Reiter VR, Wertung (`vrOwnScore`, `vrScoreCell`): die der Fassung im Besitz, bei beiden die bessere; ist die andere
  mindestens 8 Punkte besser, klein grau kursiv daneben „M 92“ oder „S 85“ (`.valt`). Eine Sache, mehrere Orte: Filter
  und Sortieren nach Wertung im Reiter VR nutzen denselben Wert.
- Trend und Pflege (ab 0.8.18): Pfeil hinter der Steam-Wertung (`trendMark`, `.tr.up` grün ↗, `.tr.down` rot ↘, nur ab
  8 Punkten Abstand, gleichbleibend ohne Zeichen), Zahlen im Tooltip; in Fakten und Einzelheiten die Zeile „Trend“
  (`trendText`). Pflege: „ruht“ als graue, umrandete Marke (`.b.care`) am Namen in der Wunschliste PC, sonst „(ruht)“
  oder „(gepflegt)“ hinter „Update“; in der Spalte Update des Reiters VR grau. Eine Sache, mehrere Orte: VR-Karte
  (Fakten), Reiter VR der Sammlung (Spalten Steam, Update), Wunschliste PC (Wertung, Name, Einzelheiten), Jetzt PC.
- Preissturz (ab 0.8.18): grüne Marke „Preissturz“ (`.b.go`, `dropMark`) am Namen in der Wunschliste PC und unter
  Jetzt, ab 0.8.25 auch an VR-Wünschen (`badges`, Laden im Tooltip, nur ohne Besitz), Prozent und üblicher Preis im Tooltip, in den Einzelheiten die Zeile „Preissturz“.
- Üblicher Rabatt (ab 0.10.0): grau gestrichelte Marke „üblich −x %“ (`.b.usq`, `usualMark`), nur wenn ein laufendes
  Steam-Angebot mindestens 10 Punkte unter dem für das Alter üblichen Rabatt liegt; keine Empfehlung, der Tooltip
  nennt Altersstufe, Zahl der Angebote und „Keine Vorhersage“. In den Einzelheiten die Zeile „Üblich“ (`usualText`),
  sobald die Stufe genug Angebote hat. Kasten „Was dein Preisverlauf zeigt“ (`.muster`, `musterHtml`) unten in der
  Legende und aufklappbar unter dem Preisverlauf; dort je Laden die Spalte „Rhythmus“ (`gapText`). Eine Sache, mehrere
  Orte: Name in der Wunschliste VR (`badges`), Wunschliste PC, Jetzt PC und Alle, Einzelheiten VR (`factsHtml`) und PC
  (`pcDetail`).
- Spieler aus der Recherche (ab 0.10.1): violett (`gMaxPl0`, `plParts`), Tooltip „Aus der Recherche“.
- Meta aktiv (ab 0.10.1): neue Meta-Bewertungen je 30 Tage, grau „+n/Mon.“ in der Spalte Aktiv des Reiters VR, wenn
  Steam keine Spielerzahl hat, und Zeile „Meta aktiv“ in den Fakten (`growTip`); nur ein Hinweis.
- Crossplay (ab 0.10.0; ab 0.10.3 Marke „Crossplay“ am Namen statt „⇄“ an der Spielerzahl, Entscheidung 02.11.2026):
  `xpMark` grau, violett, wenn nur eine Quelle es sagt oder PCGamingWiki widerspricht; in der Sammlung, der VR-Wunschliste,
  bei PC-Wünschen und in Jetzt Alle; Zeile „Crossplay (Quelle)“ in den Einzelheiten (`xpLabel`, `plRows`, VR in
  `factsHtml`) mit den Plattformen, etwa „Crossplay (Steam)“ oder „Crossplay (PCGW/Steam)“. Die Steam-Kategorie nennt
  keine Plattformen (Tooltip). „Crossplay Quest/PC“ aus der Recherche steht bei den Meinungen (ab 0.10.2 so benannt,
  auch „kein Crossplay Quest/PC“). Nicht verwechseln mit Crossbuy (Kauf bei Meta gilt für Quest und PC).
- Besitz mit zweiter Quelle (ab 0.10.2, `besitz.check`, `own_check`): „Zu erledigen“, Gruppe „Besitz: Quellen
  widersprechen sich“, nur Meldungen ohne Knöpfe, oben die Zahl der bestätigten Käufe je Laden.
- Pakete (ab 0.10.2, `bundles` am Wunsch): Zeile „Paket“ in den Einzelheiten VR, „statt“ mit der Summe grün, wenn das
  Paket günstiger ist; Marke „im Paket günstiger“ (`.b.go`) am Namen. Tooltip `bundleTip`.
- PC-Einzelheiten (ab 0.10.3, Entscheidung 02.11.2026): „Jetzt“ und „Tief“ zeigen Händler und Keyshop nur, wenn der
  teurere höchstens 8 % (ab 0.10.4, vorher 10 %) über dem günstigeren liegt (`pcPair`, `PC_ALT`; der Tooltip nennt den
  anderen), „Läden“ nur die Läden bis 8 % über dem günstigsten Preis jetzt. Ab 0.10.4 muss ein teurerer Weg in „Jetzt“
  und „Läden“ außerdem höchstens 10 % über dem Tief liegen (`PC_ALT_LOW`): gekauft wird fast immer zum günstigsten
  Preis, ein Umweg (etwa günstig gekauftes Guthaben) lohnt nur nah am Tief (Entscheidung 02.11.2026). „Üblich“ (mit Preis, „−40 % = 17,99 €“) und „Steam-Angebote“ nur,
  wenn ein Steam-Angebot in üblicher Höhe unter dem günstigsten Preis jetzt und höchstens 5 % über dem Tief läge
  (`muster.worth_pc`); bei VR bleiben sie, weil sie Meta gegen Steam abwägen.
- VR-Einzelheiten in Jetzt und Wunschliste (ab 0.10.3, `vrDetail`): im Raster der Tabelle links die Angaben (`.vdf`),
  ab der Spalte Meta bzw. Preis bis vor Wertung die Karten der Läden mit dem Preisverlauf (`.vdp`), rechts Genres und
  Kurzbeschreibung (`.vdd`), darunter Tiefstpreise und Links. PC-Einzelheiten: Beschreibung ab der Spalte „Wo“.
  Marken und Genres hinter „+n weitere“ stehen in den Einzelheiten (`fitAll`, `.gmarks`, `.ggen`). Ab 0.10.6 stehen die
  Genres dort unter der Spalte Genre (`.vdd` als `subgrid`, `--gg`), die Beschreibung ab der Spalte Wertung; über
  den Angaben nur, was die Zeile nie zeigt („ohne Crossbuy“, `cbOff`, und die Links zum Nachtragen), keine Marke
  doppelt. Ab 0.10.7 stehen die Genres bündig mit denen der Zeile (`.gdm.vdd{column-gap:10px}`) und 10 px höher,
  ohne die übrigen Angaben mitzunehmen.
  Ab 0.10.8 ebenso in den PC-Einzelheiten (Wunschliste und Jetzt, `pcDetail(r, gc, gg)`), die Beschreibung bleibt
  ab der Spalte „Wo“.
- Wertung in den Einzelheiten (ab 0.10.7): jeder Wert in der Farbe der Wertung (`.gsc`, `--sh` aus `gScoreHue`), auch
  bei VR und beim schwächeren Laden; aus Sternen umgerechnete Werte violett gepunktet unterstrichen (`.gxu`); „+24“
  bleibt grün; bei PC dahinter klein die Zahl der Rezensionen in Klammern.
- Zeile unter der Maus (ab 0.10.7, nur mit Maus `@media (hover:hover)`): Hintergrund 6 % Textfarbe (`--hov`), in
  allen Tabellen, im Preisverlauf und in den kleinen Tabellen der Einzelheiten. Ab 0.10.8 im Darkmode dunkler statt heller
  (`--hov` je Ansicht: hell 6 % Textfarbe, dunkel 70 % Seitenhintergrund in der Kartenfarbe).
- Aufklappen (ab 0.10.8, `keepRow`): die angeklickte Zeile bleibt an ihrer Stelle im Fenster, auch wenn darüber eine
  andere Zeile zuklappt; danach rückt das Fenster nach, bis die Einzelheiten zu sehen sind (`showOpen`).
- Sortieren (ab 0.10.8, `sortSel`): ist in Jetzt oder Wunschliste eine Spalte sortiert, hebt eine andere Wahl die
  Spaltensortierung dieser Tabelle auf, wie in der Sammlung. Ab 0.10.9 (`sortOpts`, Entscheidung 02.11.2026) steht
  statt „nach Spalte“ die Spalte selbst in der Auswahl, mit Richtung (`Preis ▲`); gibt es dieselbe Wahl schon (etwa
  „Wertung“), ist sie gewählt und trägt den Pfeil. Ebenso in der Sammlung.
- Tooltips zum Tief (ab 0.10.7, `lowTip`): „am Tief“, Stern, Tief-Spalte, Rabatt, „kaufen“/„gut“ und `bestLine` nennen
  den tatsächlichen Tiefpreis mit Laden und Datum, den Preis jetzt und den Abstand; der Rabatt zusätzlich Normalpreis
  und Ende, die gg.deals-Zeile Händler, Keyshop und Steam. Ein Tief von 0 € (Gratis-Aktion) zählt bei PC-Wünschen
  und im Preisverlauf nicht (`pcwish.view`, `verlauf._pack`).
- Steam-Angebote (ab 0.10.2, `rhythm`): Zeile in den Einzelheiten VR und PC, „zuletzt vor n Wochen (bisher etwa alle
  m Wo.)“ oder „läuft gerade“ (`rhythmText`, `rhythmTip`), keine Vorhersage.
- Lenkrad (0.8.3): Marke „Lenkrad“ (`.b`), wenn das Spiel in einer Liste der Rennspiele steht (SimHub,
  Simucube-Forum; Tooltip nennt beide); nur Steam-Schlagwörter: „Lenkrad?“ violett (`.b.gxc`), `wheelBadge`.
  Ab 0.8.5 auch an VR-Titeln (Reiter VR, Wunschliste, Karten). Filter „Lenkrad“ (`d.wh`), wenn ein Spiel im Reiter eins
  hat. Einzelheiten: Zeile „Sim-Racing“ mit Links auf die Listen und den Schlagwörtern (violett ohne Liste).
- Über der Liste nur „Alle n Spiele (Reiter).“ mit Aufklappdreieck; die Herkunft klappt darunter auf (`details.gnote`, 0.7.5).
- „Zu erledigen“, alle Gruppen (ab 0.10.15, `todoGo`): der Name ist ein Link (`button.link`, Tooltip „Einzelheiten zeigen
  (Wunschliste VR)“ usw.) zu den Einzelheiten: VR-Titel auf die Wunschliste VR, sonst Sammlung, Reiter VR; PC-Wünsche auf
  die Wunschliste PC; Retro-Spiele in ihr System der Sammlung. Das Ziel sucht nach dem Namen, die Zeile ist aufgeklappt,
  Filter der Wunschliste sind aus; ohne Ziel bleibt der Name Text. Bei „Derselbe Titel?“ sind beide Namen Links.
- Wunschliste PC (ab 0.10.15): wie die Sammlung erst 100 Zeilen, dann „weitere … zeigen“, das beim Herunterscrollen von
  selbst lädt; eine offene Zeile weiter unten wird mitgezeichnet.
- „Zu erledigen“, Gruppe „PC-Wunsch: Steam-ID“ (0.8.24, `pcwish_ids`): übernommene ID nach der Grundform mit Link zur
  Steam-Seite und „passt“, „falsch“; sonst Vorschläge mit Link und „dieses“, dazu „keins“. In der Wunschliste PC am
  Namen „Steam-ID ungeprüft“ (`.b.warn`, Steam-Name im Tooltip), solange nicht bestätigt.
- Recherche unter dem Titel (ab 0.10.17): in der Kopfzeile dazu „Quest-Fassung aktueller“ / „Steam-Fassung aktueller“
  / „gleicher Stand“ und bei getrennten Lobbys „Mehrspieler Quest …, PC …“; aufgeklappt die Zeilen Technik Quest,
  Technik PC, Aktueller, Umfang und Deutsch. In „Meinung fehlt“ steht bei aufzufrischenden Titeln „Mehrspieler zuletzt
  recherchiert am …“.
- „Zu erledigen“, Gruppe „Meinung fehlt“ (0.9.2, `todo` mit kind `opinion`): VR-Wünsche ohne Recherche, die zuletzt gewünschten oben (in dieser Reihenfolge nimmt sie der Auftrag), je Titel
  welche Kennungen da sind und Links zu Reddit und Google; oben „Auftrag kopieren“ (`opcopy`, Text aus `opinion_task`).
- „Zu erledigen“, Gruppe „Retro: DE fehlt“ (0.10.12, `retro_de`): je System eine Überschrift mit Zahl und „alle …
  ignorieren“ (nur bei mehreren Systemen), oben „Alle ignorieren“; je Spiel die gesuchte Fassung (violett, wenn ihr
  Deutsch nur aus der Region geschätzt ist) und „ignorieren“. Der Hinweis danach hat „Rückgängig“. Ignoriert: keine
  Marke „DE fehlt“, Filter „Sprache“ zählt es als „ohne Deutsch“, in den Einzelheiten „Gesucht: …, ignoriert“ grau
  mit „wieder melden“; die Zeile über der Tabelle nennt die Zahl der ignorierten.
- „Zu erledigen“, Gruppe „Retro: ähnlicher Name“ (0.8.4): je Spiel System, ähnlicher Titel der Fassungsliste,
  Knöpfe „dasselbe“ und „anderes“. Sprachen eines 3DS-Spiels über den Produktcode sind nicht violett; der
  Tooltip nennt „laut No-Intro“ und die Fassung.
- Einstellungen (0.7.4): Zahlen in „Zu erledigen“ in der Farbe für Prüfen (`b.warnc`), auch in den
  Gruppen. Der Knopf „ROM-Ordner wählen“ ist dezent (`label.btn.quiet`), nicht hell gefüllt.
- Sammlung: ganz oben „Nicht mehr in der Retro-Liste“, wenn etwas fehlt (Behalten, Stand
  übernehmen); Retro-Spiele tragen DE, EN oder JP (violett: aus der Region geschätzt), Homebrew, Hack
  und „nicht mehr in der Liste“ als Marken, Dateizahl und Regionen in den Einzelheiten. Unterreiter je System („Alle“, PC, VR, dann Konsolen, je mit grauer Zahl; der
  gewählte unterstrichen, am Handy seitlich wischbar), darunter Mischungen in einer Zeile (am Handy wischbar; „Liegt brach“ ab 0.9.3 nur, wenn ein Spiel des Reiters laut Steam nie gespielt ist), Filter als Menüs (Mehrspieler: alle
  müssen passen; Genre: Schalter „eines davon“ oder „alle“, Suche, Zahl je Genre).
- Gespielt (0.9.3): in den Einzelheiten unter Mein Stand „Gespielt“ mit Spielzeit und „zuletzt am …“ oder „nie“
  (`.gpt`, Tooltip „Laut Steam-Konto“); Filter „Gespielt“ (`G_PL`) hinter Mein Stand, nur wenn ein Spiel des Reiters
  eine Spielzeit hat; Sortierung „Zuletzt gespielt“.
- Löschen und Zusammenführen fragen nicht vorher. Der Hinweis unten nennt, was geschah, und
  bietet sieben Sekunden „Rückgängig“. Rückfragen bleiben für Dinge, die alles ersetzen
  (Sicherung einlesen).
- Probleme stehen als violetter Hinweis über den Ansichten, jeweils mit „Protokoll öffnen“.

## Prüfen vor dem Commit

- `python3 -m unittest tests.test_all`: Darin lädt `tests/ui_selbsttest.html` die Seite in
  Chromium bei 390 px Breite, geht alle Reiter, eine Suche, Zuklappen und das Thema-Menü durch
  und meldet seitliches Scrollen, Skriptfehler und Bedienelemente ohne Namen (`aria-label`
  oder `label`). Ohne Chromium wird er lokal übersprungen, in GitHub Actions nicht.
- Jede Adresse `/api/...`, die die Oberfläche ruft, muss es im Server geben (Test).
- Bildschirmfotos breit und bei 390 px, hell und dunkel, gegen eine bestehende Ansicht halten.

## Jetzt, ab 0.8.11

- Reiter „Alle, PC, VR“ (`.systabs`, `V.nowKind`, ab 0.8.17 statt des Schalters) über der Werkzeugzeile, an derselben
  Stelle wie in Wunschliste und Sammlung, mit Zahl je Seite; PC grün, VR türkis wie dort. Bei „Alle“ zwei
  Klappen „VR“ und „PC“; die PC-Liste ist dieselbe Tabelle wie unter Wunschliste, PC (`pcTable`), nur Wünsche nah am
  Tief und ohne die schon in der Sammlung. Bei „PC“ keine VR-Filter. Ab 0.8.27 bei „Alle“ eine Tabelle
  (`allTable`, `allVrRow`, `allPcRow`, Spalten `ALL_COLS`): ab 0.9.4 Spiel, max. Spieler, Preis, überm Tief, Art (`.b.pcb` PC grün
  umrandet, VR türkis; ab 0.9.7 hinter „überm Tief“), Wo, Wertung, Rezensionen, Genre, Aktiv; sortiert nach Nähe, Rabatt
  (`_saleOf`) oder Wertung. Die Gruppe „VR: reduziert, aber noch weit über dem Tief“ fiel mit 0.9.4 weg (keine
  Kaufempfehlung). „max. Spieler“ ist in allen Tabellen die erste Spalte nach „Spiel“, auch in der Sammlung. Ab 0.9.7 sortieren alle
  Tabellen in Jetzt und Wunschliste per Klick auf den Spaltenkopf wie in der Sammlung (`gTh` mit Tabelle, `sortRows`,
  `V.sorts.all`, `.pcw`, `.vrw`; Schlüssel `ALL_KEYS`, `PC_KEYS`, `VR_KEYS`), dritter Klick zurück zur Sortierung im Menü. Ab 0.9.0 im Reiter PC das Menü „Laden“ (`select
  data-shop`, `V.nowShop`, Zählung `shopCounts`): je Laden die PC-Wünsche nah am Tief der Händler; nach Wahl dieselbe
  Tabelle (`pcTable`) mit dem Preis dort (`atShop` ersetzt `best`, `url`, `over`), Hinweis darüber nennt den Laden.
- Läden einzeln (0.9.0, `pcShopsHtml`): in den Einzelheiten der PC-Wünsche die Zeile „Läden“, bis sechs Läden nach
  Preis, Name und Preis als Link, grün (`.g-buy`) höchstens 5 % über dem Tief der Händler, Rabatt als `.b.deal`,
  Normalpreis, Tief dort und Ende im Tooltip, „+n weitere“ grau mit Liste im Tooltip. Eine Sache, mehrere Orte: das
  Urteil „nah am Tief“ je Laden kommt aus `itad.shop_rows` (Server) und gilt für Einzelheiten und das Menü „Laden“.
- Preisverlauf (0.9.1, wie im eShopKompass): Knopf „Preisverlauf“ als Link (`.vlb`), ab 0.9.4 überall
  unter dem Preis: bei VR unter den Preisfeldern, bei PC als Zeile nach „Läden“ (nicht bei Paketen und DLC); dazu
  öffnet ein Klick auf die Marke „Wo“ den Verlauf. Öffnet `dialog#verlauf.vl`
  (`openVerlauf`, `drawVerlauf`, `vlSvg`): Kurve je Laden als Stufenlinie, Meta im Türkis des Tools, Steam in
  `--deal`, gg.deals grau gestrichelt, Läden von IsThereAnyDeal in festen Farben (`VL_SHOP`); Tief gold
  (`--best`) und „typisch“ grau gestrichelt quer; Legende als Knöpfe zum Ausblenden (`V.vl.hide`, ab sieben Läden die
  übrigen aus). Darunter eine Tabelle je Laden, am Handy seitlich scrollbar (`.scroll`). Esc schließt.
- Hinweisklappe `.gnote`: Überschrift klein und grau (13 px, wie in der Sammlung), Text über die volle Breite (ab 0.8.12).
- Eine Sache, mehrere Orte: Zeilen der PC-Wünsche ändern sich in `pcRow` für Wunschliste und Jetzt zugleich.
- VR-Wünsche ab 0.8.22 als Tabelle (`vrTable`, `vrRow`, Spalten `VR_COLS`): ab 0.9.4 Spiel, max. Spieler, Meta,
  Steam, überm Tief, Wo, Wertung (mit Trend), Rezensionen, Genre, Aktiv, Update. Genre und Spielerzahl aus den
  VR-Spielinfos (`library.info`, wie bei den PC-Wünschen). Der Trendpfeil hinter der Wertung steht frei
  (`.gr .tr` absolut ab 761 px) und verschiebt die Wertung nicht. Preise mit Rabattmarke (`vrPrice`, `.b.deal` klein) als Link zum Laden,
  Tief und Shop im Tooltip. „am Tief“ grün (`.g-buy`, violett bei übernommenem Tief), sonst rot der
  Abstand (`.over`). Am Namen kurze Marken (`badges(r, true)`: ohne „ohne Crossbuy“, Liste als „keine Liste“ oder
  „fehlt: Meta“). Klick auf den Namen (`V.vwOpen`) zeigt die Karte (`wishRow(r, true)`, ohne Namenskopf) als
  Einzelheiten. Eine Sache, mehrere Orte: Zeilen der VR-Wünsche ändern sich in `vrRow` für Wunschliste und Jetzt; Zellen
  der VR-Zeilen kommen aus `vrCells` (auch für `allVrRow`), Preis und Tief der PC-Zeilen aus `pcPriceHtml` und
  `pcLowHtml` (auch für `allPcRow`).

## Sammlung, ab 0.8.7

- Marke „VR“ in PC-Zeilen türkis (`.vrb`), Tooltip nennt die Quelle (`vr_src`); nur aus dem Namen violett (`.gxc`).
  Zeilen `pcvr:` sind VR-Titel des Tools am PC, die Playnite nicht kennt; ihre Einzelheiten sagen das.
- Einzelheiten: Mein Stand immer gleich nach der Spalte „Spiel“, bei 3fr / 5fr (`--dcols` fest, ab 0.8.10; vorher
  1,5fr / 1fr, das stand zu weit rechts), gleich in jedem Reiter, wie in der Switch-Ansicht bis 0.8.6.
- Werkzeugzeile: „herunterladen“ (Link, `gdl`) als CSV; Spaltenkopf „Spiel“ mit ⧉ (`.gcopy`) für alle Titel.
- Suche (`V.q`, `V.d.q`) leert sich beim Wechsel von Reiter, Unterreiter und System.
- Knöpfe in `.bar.slim` mit fester Höhe 30 px.

## Retro, ab 0.8.8

- Name: dein Titel aus der Ordner-Liste (Artikel nach vorn); der Titel laut Dateiname steht in den Einzelheiten
  als „Dateiname“. Dein Genre steht als erste Genre-Marke und gilt als bestätigt.
- Einzelheiten: „Dein Ordner“ (Genre › Untergruppe, dazu der Ordner, wenn er anders heißt), „Reihe“ (mit
  Sammelreihe), „Status“, „Dateien“ mit Größe (`mb()`: KB, MB, GB; sonst MB laut deiner Liste), „Genre anders“
  violett (`.gxc`), wenn libretro oder IGDB widersprechen. Herkunft: „deine Ordner-Liste“, „libretro-database
  (dort „…“)“.
- Spalten: Spieler mit Tooltip „Laut libretro-database“, violett nur, wenn IGDB etwas weiß und keine Zahl nennt;
  Jahr mit „Laut libretro-database“; Erscheinen mit nur Monat als „im Juli 2003“ (`relDay`). Beschreibung von
  libretro: Tooltip „nur auf Englisch“.
- GameTDB (0.10.13; GameCube, Wii, DS, 3DS, PS3): die deutsche Beschreibung steht vor der von IGDB und libretro,
  Tooltip „Beschreibung laut GameTDB“ (englisch: „…, nur auf Englisch“). Nach Erschienen die Zeilen „Deutscher Titel“
  (wenn er anders heißt), „USK“ oder „PEGI“ (USK 16 und 18 in ihrer Farbe wie bei Switch) und „Online“ (Spieler über
  die abgeschaltete Nintendo Wi-Fi Connection). Spieler: Tooltip „Laut GameTDB (Spieler an einer Konsole)“, nennt
  GameTDB dieselbe Zahl wie IGDB oder libretro, „… und GameTDB“ und nicht violett. Jahr: „Laut GameTDB“; nennt GameTDB
  ein anderes Jahr, ist die Zahl violett und der Tooltip nennt es. Unten „GameTDB (ID)“ unter den Quellen und ein
  Link „GameTDB“ zur Spielseite.
- Wikidata und Wikipedia (0.10.16; Retro-Spiele): Beschreibung mit Tooltip „Einleitung des Artikels „…“ der deutschen
  Wikipedia“, nur wo keine deutsche steht; „Deutscher Titel“ mit „Laut Wikidata“, Freigabe mit „Laut Wikidata“; Spieler:
  nennt Wikidata dieselbe Zahl, „… und Wikidata“ und nicht violett; ein anderes Jahr violett mit „Wikidata …“ im
  Tooltip. Unten „Wikidata (Q…) und deutsche Wikipedia“ unter den Quellen und die Links „Wikipedia“ und „Wikidata“.
- Filter der Sammlung (ab 0.10.16): Genre, dann Mehrspieler (Switch: Spielweise) direkt vor „max. Spieler“.
- Preise in den Tabellen (ab 0.10.16) in normaler Stärke, PC wie VR; vorher war nur der PC-Preis fett (aus dem
  eShopKompass übernommen). Was günstig ist, zeigen „überm Tief“, ★ und „Wo“.
- DekuDeals (0.10.14; PC, PlayStation 4 und 5, Xbox, Switch aus Playnite): Spalte Spielzeit mit „Laut HowLongToBeat
  (über DekuDeals)“, IGDB im Tooltip, wenn es eine eigene Zahl hat; in den Einzelheiten die Zeile „Spielzeit“ (Hauptspiel,
  mit Extras, komplett). Wertung: OpenCritic neben Metacritic, Metacritic von DekuDeals mit Herkunft im Tooltip
  („laut Steam und DekuDeals“, wenn beide gleich). Spieler: nennt DekuDeals dieselbe Zahl, „… und DekuDeals“ und nicht
  violett. Jahr: nennt DekuDeals ein anderes, ist die Zahl violett und der Tooltip nennt es. Altersfreigabe mit der
  Stelle als Bezeichnung (USK, PEGI, ESRB) und Herkunft im Tooltip; Deutsch laut DekuDeals im Tooltip der Sprachen.
  Unten „DekuDeals“ unter den Quellen und ein Link zur Spielseite.
- „Zu erledigen“, Gruppe „Retro: Genre weicht von deiner Liste ab“: je Spiel deins und das der anderen Quelle,
  Knöpfe „Liste gilt“ und ab 0.9.6 „Quellen gelten“ (`data-take`), oben beide für alle. Gilt das Genre der Quellen,
  nennen die Einzelheiten unter „Genre“ deins mit dem Link „deins gilt“ (`own_taken`).
- Konten und Schlüssel (ab 0.9.6): je Dienst eine kurze Zeile, wo es die Schlüssel gibt und was sie tun, in der
  Klappe darunter (`details.how`, zu, gemerkt als `keyhow`).
- Vorschau der Retro-Liste: Zeile zu deinen Ordner-Listen (passende Zeilen, nur in der Liste, nicht in der Liste)
  und die Größe zusammen.
- VR-Titel am PC ohne Playnite-Eintrag (`pcvr:`) tragen die Marke „Lenkrad“ wie die übrigen.
- Ab 0.8.9 sind sie Spiele der Sammlung mit Spalten aus Steam und IGDB; die Herkunft nennt „dein VR-Titel im Tool
  (…), Playnite kennt ihn nicht; Steam-Details“.
- Herkunft in der Fußzeile der Einzelheiten (ab 0.10.3, Entscheidung 02.11.2026): nur „n Quellen“, welche und wie im
  Tooltip; Playnite und Steam zählen einzeln.

## Preisverlauf (Fenster)

- Ab 0.10.3: ✕ oben rechts in einer Kopfzeile, die beim Scrollen stehen bleibt (`.vlx`, `dialog.vl header` sticky);
  Esc oder ein Klick neben das Fenster schließen es auch.
- Spalte „typisch“: Median der Tiefstwerte je Angebot, bei gg.deals (Händler und Keyshops) der Median der Preise der
  letzten 90 Tage nach Tagen (klein „90 Tage“; die Hälfte der Zeit günstiger, die Hälfte teurer, ein kurzer Ausreißer
  zählt kaum). Ab 0.10.6 unter „zuletzt“ oben Rabatt und Preis, darunter klein die Zeit; nur bei einem guten Preis
  (höchstens 5 % über dem Tief aller Läden oder unter dem typischen gg.deals-Preis) der Rabatt blau (`.b.deal`) und
  der Preis grün (`.g-buy`), sonst ohne Farbe.
- Ab 0.10.6: Spalte „überm Tief“ nach „jetzt“ wie in den Tabellen (grün „am Tief“ bis 2 %, sonst rot `+x €`). Der
  Laden führt zu seiner Seite des Spiels (Meta, Steam, gg.deals, bei PC-Wünschen die Läden von IsThereAnyDeal), der
  Preis jetzt ebenso (`url` je Reihe aus `verlauf.vr` und `verlauf.pc`). Ab 0.10.7 steht „jetzt“ am Tief (bis 2 %)
  grün und fett, beim Tiefstpreis mit ★ wie in der Tabelle; Tooltip mit Tief aller Läden.
