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
| Gold | `--best` | am Bestpreis (niedrigster Preis des Shops in 24 Monaten, bis 2 % darüber) | ★ hinter dem Preis (`.star`), Marke „am Bestpreis“ (`.b.best`) |
| Grün | `--go` | spricht für den Kauf, gelingt | Crossbuy, Meta günstiger (`.gap-meta`), Quelle „ok“ |
| Rot | `--stop` | spricht gegen den Kauf, misslingt | Betrag, um den Meta teurer ist (`+5 €`, `.gap-steam`), sanft als Marke „kein Crossbuy“ (`.b.stop`), Fehler einer Quelle |
| Violett | `--warn` | prüfen, veraltet, geschätzt | „Steam-ID ≈“, Stand älter als zwei Tage, Hinweise oben |
| Grau | `--chip`, `--muted` | Information ohne Wertung | Meta, PC, „Wunsch“ |

Geschätzte oder übernommene Werte tragen „≈“ oder „Tabelle“ samt Datum. Links stehen in
Textfarbe, unterstrichen.

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
- Einstellungen: Sprungleiste oben (bleibt beim Scrollen stehen), darunter „Derselbe Titel?“
  (nur wenn etwas zu entscheiden ist), Abgleich (Quellen, „Jetzt abrufen“, „Verbindung testen“,
  darunter klappbar Verbindungstest, Protokoll, Zeitplan und gg.deals), Einlesen (Konten,
  Meta per Lesezeichen, ein Feld für jede Datei) und Sicherung. Das Protokoll ist zu, außer der letzte Lauf hatte
  Fehler.
- Werkzeugzeile: Suche mit eigenem ×, Esc leert sie ebenso; dahinter Sortierung als Chips.
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
