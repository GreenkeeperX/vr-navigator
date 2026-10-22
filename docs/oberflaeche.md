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
| Grün | `--go` | spricht für dich, gelingt | günstigerer Laden (Rahmen `.shop.win`, „5 € günstiger“ ab 1 €), Crossbuy, besser bewerteter Laden (`.rate.win`, „Meta +8“), Quelle „ok“ |
| Rot | `--stop` | spricht gegen dich, misslingt | Aufpreis über dem Bestpreis (`.over`, „+7 €“), Fehler einer Quelle |
| Violett | `--warn` | prüfen, veraltet, geschätzt, unsicher | „Steam-ID ≈“, Stand älter als zwei Tage, Hinweise oben, widersprechende Quelle („Tabelle: nein“), Recherche (gestrichelte Linie links, „≈ Recherche“) |
| Grau | `--chip`, `--muted` | Information ohne Wertung | Meta, PC, „Wunsch“, „Wunsch · Tabelle“, „ohne Crossbuy“, Feld ohne Preis (gestrichelt) |

Herkunft am Wert: ohne Zeichen gemessen oder von Hand; „≈“ abgeleitet oder aus fremder Quelle;
„Tabelle“ (samt Datum, wo Platz ist) aus der Vergleichstabelle; violett gestrichelt Recherche.
Links stehen in Textfarbe, unterstrichen. Erklärungen stehen einmal in der Legende („?“), nicht
über jeder Liste; über einer Liste höchstens eine Zeile.

## Titelkarte

Jetzt und Wunschliste (`.item.wi`), immer in dieser Reihenfolge:

1. Kopf (`.hd`): Name, Marken.
2. Preise (`.shops`): zwei feste Felder, Meta links, Steam rechts (`.shop`; ohne Preis
   `.shop.none`, gestrichelt, „kein Preis“). Je Feld Preis, Rabatt, darunter `bestLine`: rot
   „+x € über Bestpreis“ (unter 1 € und 5 % ohne Rot) und der Bestpreis mit Laden oder gold
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
Fakten nebeneinander. Die Bibliothek zeigt Kopf, Fakten und die Klappe.

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

- Reiter: Jetzt, Wunschliste, Bibliothek, Entdecken, Einstellungen. Am Reiter eine graue Zahl oder ein
  Wort („läuft“, „Fehler“, „1 prüfen“). Am Handy blendet die Leiste rechts weich aus, solange
  weitere Reiter folgen.
- Einstellungen in der Reihenfolge der Daten: Sprungleiste oben (bleibt beim Scrollen stehen),
  „Zu erledigen“ (nur wenn etwas offen ist), Einlesen (Konten und Schlüssel, Lesezeichen, ein
  Feld für jede Datei), Abgleich (oben „automatisch alle … Stunden“, speichert sofort; Quellen,
  „Jetzt abrufen“, „Verbindung testen“, klappbar Verbindungstest und Protokoll) und Sicherung.
  Das Protokoll ist zu, außer der letzte Lauf hatte Fehler.
- Werkzeugzeile: Suche mit eigenem ×, Esc leert sie ebenso; dahinter „Sortieren“ als Auswahl,
  Menüs (`details.menu` mit `data-menu`, nicht `data-kc`) mit Häkchen und „?“ für die Legende.
  Ein Menü zur Zeit; ein Klick daneben oder Esc schließt es; am Handy klappt es über die volle
  Zeilenbreite auf. Gewählte Filter stehen darunter als Marken mit × (`.chips.act`).
- Entdecken: Mischungen in einer Zeile (am Handy wischbar), Filter als Menüs (Mehrspieler: alle
  müssen passen; Genre: Schalter „eines davon“ oder „alle“, Suche, Zahl je Genre).
- Löschen und Zusammenführen fragen nicht vorher. Der Hinweis unten nennt, was geschah, und
  bietet sieben Sekunden „Rückgängig“. Rückfragen bleiben für Dinge, die alles ersetzen
  (Sicherung einspielen).
- Probleme stehen als violetter Hinweis über den Ansichten, jeweils mit „Protokoll öffnen“.

## Prüfen vor dem Commit

- `python3 -m unittest tests.test_all`: Darin lädt `tests/ui_selbsttest.html` die Seite in
  Chromium bei 390 px Breite, geht alle Reiter, eine Suche, Zuklappen und das Thema-Menü durch
  und meldet seitliches Scrollen, Skriptfehler und Bedienelemente ohne Namen (`aria-label`
  oder `label`). Ohne Chromium wird er lokal übersprungen, in GitHub Actions nicht.
- Jede Adresse `/api/...`, die die Oberfläche ruft, muss es im Server geben (Test).
- Bildschirmfotos breit und bei 390 px, hell und dunkel, gegen eine bestehende Ansicht halten.
