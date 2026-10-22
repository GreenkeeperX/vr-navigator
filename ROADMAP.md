# Roadmap

Reihenfolge nach Nutzen. Das Konzept dahinter: Kaufentscheidung erst nach Qualität
(Multiplayer, gepflegtere Version, bessere Version, Crossbuy), dann nach dem Preisabstand.
Erledigtes fällt heraus; was das Tool kann, steht in der [README](README.md), wann es dazukam,
in der Git-Geschichte.

## 0.3 Wo kaufen

Plan (22.10.2026): erstes Recherche-Paket (etwa 20 Wunschtitel), dann das Urteil (misst am
üblichen Angebot, wenn der Bestpreis einmalig war).

- Bestpreis am PC über 24 Monate mit IsThereAnyDeal (optionaler Schlüssel), solange der eigene
  Steam-Verlauf kürzer ist; kleine Verlaufslinie im Bearbeiten-Fenster

- Crossbuy aus der VRDB-Liste, Updates je Shop (Steam-Patchmeldungen, VRDB-Versions-Tracker)
- Spielerzahl auf Steam mit eigenem Verlauf, Bewertungen je Shop
- Urteil je Titel mit Gründen: erst Nachteile je Shop, dann der Abstand (Startwert für „groß“:
  mindestens 40 % und 8 €, einstellbar)
- Gutscheine mit Shop, Prozent oder Betrag und Ablaufdatum
- Legende („?“ oben) nach `docs/oberflaeche.md`
- VRDB-Link aus der QuestStoreDB-Seite, Bundles mit den enthaltenen Spielen verknüpfen

## 0.4 Entdecken

0.4.0 bringt die Sammlung und den Reiter. Als Nächstes:

- 0.4.1 Steam-Rezensionen schonend abrufen (Anzahl und Anteil positiv, eigene Quelle im
  Abgleich, je Lauf begrenzt, nach 30 Tagen neu): Bekanntheit, echter Geheimtipp-Wert, vermutete
  Steam-IDs dabei prüfen
- 0.4.2 Spielzeit und „zuletzt gespielt“ (Steam-Konto oder zusätzliche Playnite-Spalten),
  Mischung „Liegt brach“, Gespieltes ausblenden
- eigene Marken je Spiel („nie wieder vorschlagen“, „merken“), Sharenite als Nachschub

## Danach

- Bundles und Cross-Buy-Pakete im Preisvergleich
- Benachrichtigung bei neuem Tief eines Wunschtitels
- Export der Meta-Bibliothek als CSV für Playnite
- weitere Anbieter über gg.deals
- Angebotsrhythmus je Titel
