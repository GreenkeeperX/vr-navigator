# Roadmap

Reihenfolge nach Nutzen. Das Konzept dahinter: Kaufentscheidung erst nach Qualität
(Multiplayer, gepflegtere Version, bessere Version, Crossbuy), dann nach dem Preisabstand.
Erledigtes fällt heraus; was das Tool kann, steht in der [README](README.md), wann es dazukam,
in der Git-Geschichte.

## 0.3 Wo kaufen

Plan (22.10.2026): 0.3.1 Zuordnung für alle Titel (Meta-IDs auch für Käufe, Namen
lernen, Steam-ID selbst prüfen, Liste „Zu erledigen“), 0.3.2 Bestpreis je Shop aus 24 Monaten
statt Abstand als Mittelpunkt, Abrufzeit nur bei Veraltung, 0.3.3 Meinungen als Datei
einlesen, 0.3.4 Urteil.

- Crossbuy aus der VRDB-Liste, Updates je Shop (Steam-Patchmeldungen, VRDB-Versions-Tracker)
- Spielerzahl auf Steam mit eigenem Verlauf, Bewertungen je Shop
- Urteil je Titel mit Gründen: erst Nachteile je Shop, dann der Abstand (Startwert für „groß“:
  mindestens 40 % und 8 €, einstellbar)
- Gutscheine mit Shop, Prozent oder Betrag und Ablaufdatum
- Legende („?“ oben) nach `docs/oberflaeche.md` und eine Liste „Zu erledigen“ (offene
  Zuordnungen, fehlende IDs, ungeprüfte Steam-IDs)

## Danach

- Bundles und Cross-Buy-Pakete im Preisvergleich
- Benachrichtigung bei neuem Tief eines Wunschtitels
- Export der Meta-Bibliothek als CSV für Playnite
- weitere Anbieter über gg.deals
- Angebotsrhythmus je Titel
