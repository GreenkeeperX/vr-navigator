# Roadmap

Reihenfolge nach Nutzen. Das Konzept dahinter: Kaufentscheidung erst nach Qualität
(Multiplayer, gepflegtere Version, bessere Version, Crossbuy), dann nach dem Preisabstand.
Erledigtes fällt heraus; was das Tool kann, steht in der [README](README.md), wann es dazukam,
in der Git-Geschichte.

## Offen aus 0.2

- das gg.deals-Format gegen die echte Antwort prüfen (sobald ein Schlüssel da ist; „Verbindung
  testen“ zeigt den Anfang der Antwort)

## 0.2.2 Ansicht und Bedienung (wie im eShopKompass)

- Farbregeln: jede Farbe eine Bedeutung (Rabatt blau, Tiefstpreis Gold mit ★, prüfen und
  veraltet violett, rot nur der Betrag), festgehalten in `docs/oberflaeche.md`
- klappbare Bereiche mit Gedächtnis, „alle aufklappen · alle zuklappen“
- Reiter „Einstellungen“ mit Karten und Sprungleiste statt „Import“ und „Abrufe“
- Werkzeugzeile mit eigenem × im Suchfeld, Hinweis mit „Rückgängig“ statt Rückfrage
- Theme-Knopf mit Zeichen und Menü, Reiterleiste am Handy mit weichem Rand
- Selbsttest der Oberfläche bei 390 px (Chromium) und Vertragstest der Felder

## 0.3 Wo kaufen

- Steam-Besitz und -Wunschliste über die Steam Web API (Schlüssel in den Einstellungen)
- Crossbuy aus der VRDB-Liste, Updates je Shop (Steam-Patchmeldungen, VRDB-Versions-Tracker)
- Spielerzahl auf Steam mit eigenem Verlauf, Bewertungen je Shop
- Urteil je Titel mit Gründen: erst Nachteile je Shop, dann der Abstand (Startwert für „groß“:
  mindestens 40 % und 8 €, einstellbar)
- Gutscheine mit Shop, Prozent oder Betrag und Ablaufdatum

## Danach

- Bundles und Cross-Buy-Pakete im Preisvergleich
- Benachrichtigung bei neuem Tief eines Wunschtitels
- Export der Meta-Bibliothek als CSV für Playnite
- weitere Anbieter über gg.deals
- Angebotsrhythmus je Titel
