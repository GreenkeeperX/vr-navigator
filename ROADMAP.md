# Roadmap

Reihenfolge nach Nutzen. Das Konzept dahinter: Kaufentscheidung erst nach Qualität
(Multiplayer, gepflegtere Version, bessere Version, Crossbuy), dann nach dem Preisabstand.

## 0.2 Preise und Abgleich

- Meta-Preise von QuestStoreDB: Sale-Liste jeder Abgleich, Titelseiten der Wunschtitel täglich,
  Obergrenze je Lauf, Pausen, Abbruch bei 403/429
- Steam-Preise in Euro über den Store (`appdetails`, `cc=de`)
- gg.deals-API (kostenloser Schlüssel, Quellenlink Pflicht): Keyshop-Bestpreis und historisches Tief
- eigener Preisverlauf ab Tag 1 (`history.json`), Zeitplan alle 6 Stunden
- jede Angabe mit Abrufdatum, Warnung bei veralteten Werten, „Verbindung testen“ je Quelle
- Reiter „Jetzt“: Wunschtitel im Angebot, Rabatt-Ende, „neues Tief“
- `docs/abrufe.md`: was woher, wie oft, wohin

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
