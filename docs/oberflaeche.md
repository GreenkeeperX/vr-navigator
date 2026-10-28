# Oberfläche: Farben, Marken, Klappen

Verbindliche Regeln für `app/static/` (`index.html`, `style.css`, `js/app.js`), übernommen aus
dem eShopKompass. Wer Farben, Marken oder Bezeichnungen ändert, passt diese Datei und die
README im selben Commit an.

## Grundsatz

Jede Farbe hat genau eine Bedeutung. Was nichts entscheidet, bleibt grau. Hell und dunkel
müssen beide lesbar sein; jede Farbänderung wird in beiden geprüft.

| Farbe | Token | Bedeutung | Beispiele |
|---|---|---|---|
| Blau | `--deal` | Rabatt | `−67 %`, `−40 % Gutschein` (`.b.deal`) |
| Gold | `--best` | am Bestpreis (niedrigster Preis beider Läden in 24 Monaten, bis 2 % darüber) | „★ Bestpreis“ im Preisfeld (`.bl.at`, `.star`) |
| Grün | `--go` | spricht für dich, gelingt | Urteil „kaufen“ (gefüllt, `.vd.buy`) und „gut“ (umrandet, `.vd.good`) wie im eShopKompass, günstigerer Laden (Rahmen `.shop.win`, „5 € günstiger“ ab 1 €), Crossbuy, besser bewerteter Laden (`.rate.win`, „Meta +8“), Quelle „ok“ |
| Rot | `--stop` | spricht gegen dich, misslingt | Aufpreis über dem Bestpreis (`.over`, „+7 €“), Fehler einer Quelle |
| Violett | `--warn` | prüfen, veraltet, geschätzt, unsicher | „Steam-ID ≈“ (Wunschliste; Sammlung „Steam-ID prüfen“), Wert aus nur einer Quelle in der Sammlung (`.gxc`), Stand älter als zwei Tage, Hinweise oben, widersprechende Quelle („Tabelle: nein“), Recherche (gestrichelte Linie links, „≈ Recherche“) |
| Grau | `--chip`, `--muted` | Information ohne Wertung | Meta, PC, „Wunsch“, „Wunsch · Tabelle“, „ohne Crossbuy“, Feld ohne Preis (gestrichelt) |

Ausnahme, nur für die Reiter je System in der Sammlung (Entscheidung 27.10.2026): der gewählte
Reiter trägt die Farbe seiner Familie, Nintendo rot (`--sys-nin`), PlayStation blau (`--sys-ps`),
PC grün (`--sys-pc`), VR im Türkis des Tools (`--brand`), „Alle“ in `--accent`. Diese Töne sind
eigene Tokens und stehen nirgends sonst.

Weitere Ausnahmen in der Sammlung, übernommen aus „Spiele“ im eShopKompass (0.6.0, Entscheidung
27.10.2026): Die Wertung ist ein Farbton von Rot über Gelb nach Grün (`.gsc`, `--sh` aus 50 bis
95 %), Genres stehen als Blasen im Farbton ihrer Verwandtschaft (`.chip.gg`, `G_HUE`; violett
bleibt frei). Mein Stand: Backlog ○ rot, angefangen ▷ blau, durchgespielt ✓ grün, Favorit ★
gold; nur als Zeichen, nie als Fläche. Die Marke „VR“ hinter dem Namen ist türkis gefüllt
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

Herkunft am Wert: ohne Zeichen gemessen oder von Hand; „≈“ abgeleitet oder aus fremder Quelle
(in der Sammlung seit 0.6.1 kein „≈“ mehr: unbestätigt steht violett, `.gxc`, der Tooltip nennt die
Quelle; das gilt nach und nach überall);
„Tabelle“ (samt Datum, wo Platz ist) aus der Vergleichstabelle; violett gestrichelt Recherche.
Links stehen in Textfarbe, unterstrichen. Erklärungen stehen einmal in der Legende („?“), nicht
über jeder Liste; über einer Liste höchstens eine Zeile.

## Titelkarte

Jetzt und Wunschliste (`.item.wi`), immer in dieser Reihenfolge:

1. Kopf (`.hd`): Name, Marken.
2. Preise (`.shops`): zwei feste Felder, Meta links, Steam rechts (`.shop`; ohne Preis
   `.shop.none`, gestrichelt, „kein Preis“). Je Feld Preis, Rabatt, darunter `bestLine`: rot
   „+x € über Bestpreis“ (jeder Aufpreis rot, Entscheidung 26.10.2026) und der Bestpreis mit Laden oder gold
   „★ Bestpreis“, gemessen am niedrigsten Preis beider Läden (`best_all`); kommt er aus dem
   anderen Laden, klein darunter der eigene Tiefstpreis („Steam-Tief“). Der günstigere Laden:
   `.shop.win` mit „x € günstiger“.
3. Fakten (`.facts`): festes Raster mit zwei Spalten, links der kleine graue Name (`.fl`),
   rechts der Wert (`.fv`): Wertung, Spieler, Update, Meta-Version; nur was es gibt.
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
- Reiter: Jetzt, Wunschliste (0.8.2, Unterreiter VR und PC als `.systabs`, `V.wsub`; PC in Grün der Familie PC,
  Liste im Raster der Sammlung `.glist.pcw`, Name verlinkt gg.deals, Marken VR, „schon in der Sammlung“ violett,
  „nah am Tief“ grün), Sammlung, Einstellungen (die Bibliothek ist seit 0.6.0 der Reiter
  VR in der Sammlung; ein gemerkter Reiter „Bibliothek“ öffnet ihn). Am Reiter eine graue Zahl oder ein
  Wort („läuft“, „Fehler“, „1 prüfen“). Am Handy blendet die Leiste rechts weich aus, solange
  weitere Reiter folgen.
- Einstellungen in der Reihenfolge der Daten: Sprungleiste oben (bleibt beim Scrollen stehen),
  „Zu erledigen“ (nur wenn etwas offen ist), Einlesen (Konten und Schlüssel, Lesezeichen, ein
  Feld für jede Datei), Abgleich (oben „automatisch alle … Stunden“, speichert sofort; Quellen,
  „Aktualisieren“, „Verbindung testen“, klappbar Verbindungstest und Protokoll) und Sicherung
  (drei Knöpfe wie im eShopKompass: Abgleichsdaten herunterladen, Sicherung herunterladen,
  Sicherung einlesen). Die Klappe „Quellen“ nennt den Stand farbig wie im eShopKompass
  („10 ok“ grün, „1 mit Problem (gg.deals)“ rot), aufgeklappt eine kompakte Tabelle (`.mini-t`: Quelle,
  Zustand farbig, Zeit, Abrufe und Meldung); Knöpfe in der Zeile `.bar.slim` sind so hoch wie
  im eShopKompass.
  Das Protokoll ist zu, außer der letzte Lauf hatte Fehler.
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
  (alle, Switch 2, nur Switch, `d.sw`; nur in diesem Reiter). Stehen im Reiter nur Spiele mit `kv`,
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
  oder vorpX: „VR-Mod?“ violett (`.b.gxc`), ein Hinweis. Filter „VR per Mod“ (`d.vm`) erscheint, wenn ein
  Spiel im Reiter eins von beiden hat. Einzelheiten: Zeilen „VR per Mod“ und „Nexus Mods“ mit Links.
- Lenkrad (0.8.3): Marke „Lenkrad“ (`.b`), wenn das Spiel in einer Liste der Rennspiele steht (SimHub,
  Simucube-Forum; Tooltip nennt beide); nur Steam-Schlagwörter: „Lenkrad?“ violett (`.b.gxc`), `wheelBadge`.
  Ab 0.8.5 auch an VR-Titeln (Reiter VR, Wunschliste, Karten). Filter „Lenkrad“ (`d.wh`), wenn ein Spiel im Reiter eins
  hat. Einzelheiten: Zeile „Sim-Racing“ mit Links auf die Listen und den Schlagwörtern (violett ohne Liste).
- Über der Liste nur „Alle n Spiele (Reiter).“ mit Aufklappdreieck; die Herkunft klappt darunter auf (`details.gnote`, 0.7.5).
- „Zu erledigen“, Gruppe „Retro: ähnlicher Name“ (0.8.4): je Spiel System, ähnlicher Titel der Fassungsliste,
  Knöpfe „dasselbe“ und „anderes“. Sprachen eines 3DS-Spiels über den Produktcode sind nicht violett; der
  Tooltip nennt „laut No-Intro“ und die Fassung.
- Einstellungen (0.7.4): Zahlen in „Zu erledigen“ in der Farbe für Prüfen (`b.warnc`), auch in den
  Gruppen. Der Knopf „ROM-Ordner wählen“ ist dezent (`label.btn.quiet`), nicht hell gefüllt.
- Sammlung: ganz oben „Nicht mehr in der Retro-Liste“, wenn etwas fehlt (Behalten, Stand
  übernehmen); Retro-Spiele tragen DE, EN oder JP (violett: aus der Region geschätzt), Homebrew, Hack
  und „nicht mehr in der Liste“ als Marken, Dateizahl und Regionen in den Einzelheiten. Unterreiter je System („Alle“, PC, VR, dann Konsolen, je mit grauer Zahl; der
  gewählte unterstrichen, am Handy seitlich wischbar), darunter Mischungen in einer Zeile (am Handy wischbar), Filter als Menüs (Mehrspieler: alle
  müssen passen; Genre: Schalter „eines davon“ oder „alle“, Suche, Zahl je Genre).
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
