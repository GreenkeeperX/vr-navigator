# Roadmap

Reihenfolge nach Nutzen. Das Konzept dahinter: Kaufentscheidung erst nach Qualität
(Multiplayer, gepflegtere Version, bessere Version, Crossbuy), dann nach dem Preisabstand.
Erledigtes fällt heraus; was das Tool kann, steht in der [README](README.md), wann es dazukam,
in der Git-Geschichte.

## 0.3 Wo kaufen

Plan (22.10.2026): 0.4 Entdecken (Empfehlungen für die ganze PC-Sammlung, Konzept-Doc), erstes Recherche-Paket (etwa 20 Wunschtitel), dann 0.3.4 Urteil (misst am üblichen
Angebot, wenn der Bestpreis einmalig war).

- Bestpreis am PC über 24 Monate mit IsThereAnyDeal (optionaler Schlüssel), solange der eigene
  Steam-Verlauf kürzer ist; kleine Verlaufslinie im Bearbeiten-Fenster

- Crossbuy aus der VRDB-Liste, Updates je Shop (Steam-Patchmeldungen, VRDB-Versions-Tracker)
- Spielerzahl auf Steam mit eigenem Verlauf, Bewertungen je Shop
- Urteil je Titel mit Gründen: erst Nachteile je Shop, dann der Abstand (Startwert für „groß“:
  mindestens 40 % und 8 €, einstellbar)
- Gutscheine mit Shop, Prozent oder Betrag und Ablaufdatum
- Legende („?“ oben) nach `docs/oberflaeche.md`
- VRDB-Link aus der QuestStoreDB-Seite, Bundles mit den enthaltenen Spielen verknüpfen

## Danach

- Bundles und Cross-Buy-Pakete im Preisvergleich
- Benachrichtigung bei neuem Tief eines Wunschtitels
- Export der Meta-Bibliothek als CSV für Playnite
- weitere Anbieter über gg.deals
- Angebotsrhythmus je Titel
