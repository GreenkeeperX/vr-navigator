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
- VRDB-Link aus der QuestStoreDB-Seite, Bundles mit den enthaltenen Spielen verknüpfen

## 0.4 Entdecken

0.4.0 brachte die Sammlung und den Reiter, 0.4.1 die Steam-Rezensionen, 0.4.2 das Ausklammern
reiner Konsolenspiele, 0.4.3 die Bestpreis-Leiste in Jetzt und Feinschliff in Entdecken, 0.4.4
den Abgleich der Merkmale mit den Steam-Store-Daten (beide einig: bestätigt, sonst „≈“), 0.4.5
Wertungen beider Läden mit Sortierung und Filtern in Wunschliste und Bibliothek, 0.4.6 eine
aufgeräumte Zeile je Titel (Leiste zum Bestpreis, eine Wertungsskala, Klappe „Mehr“, Recherche als
unsicher gekennzeichnet), 0.4.7 gemessene Kaufgründe (Steam-Spieler, letztes Steam-Update,
Meta-Version, Crossbuy und Meta-Wertung von VRDB; gg.deals-Lesezeichen mit Paketen und DLC),
0.4.8 die Übersicht (Titelkarte mit festen Preisfeldern statt Leiste, Fakten in einer Zeile,
Menüs für Sortieren und Filter, Legende, Genre-Menü mit „eines davon“ oder „alle“, Herkunft je
Crossbuy-Wert, Einstellungen in der Reihenfolge der Daten, ruhigeres Protokoll), 0.4.9 Aufräumen
(Bestpreis über beide Läden, Karten über die volle Breite, Fakten im festen Raster, Klappe mit
Inhaltszeile, Crossbuy-Begriff und Crossplay in der Recherche, ruhigeres Konten-Formular,
gg.deals-Wunschliste nach einer Woche wieder vom Server), 0.5.0 eine Stelle für Wünsche
(Wunschlisten der Läden als Spiegel, „Wunschliste abgleichen“ mit Aktionen für ganze Gruppen,
Herkunft des Wunsches je Titel, die Tabelle eingefroren), 0.5.1 Nachtragen leicht gemacht
(„fehlt auf einer Laden-Wunschliste“ mit Links zum Eintragen, Meta-Wunschliste sauber gelesen,
Jetzt nur nah am Bestpreis mit den Grenzen des eShopKompass), 0.5.2 Steam-Wunschliste
abschaltbar (am PC zählt dann nur gg.deals, Entscheidung 22.10.2026). Grundsatz (Entscheidung 22.10.2026): so wenig
Handarbeit wie möglich; was sich abrufen und von einer zweiten Quelle bestätigen lässt, geht vor
Bestätigen und Einlesen von Hand. Als Nächstes:

- 0.5.3 Urteil „wo kaufen“ aus Gemessenem (Spieler, Pflege, Crossbuy, Wertung, Preis) als
  Hinweis im Kopf der Karte („Meta kaufen“, „warten“), Gründe in der Klappe; Recherche nur als
  Ergänzung
- 0.5.4 Spielzeit und „zuletzt gespielt“ (Steam-Konto oder zusätzliche Playnite-Spalten),
  Mischung „Liegt brach“, Gespieltes ausblenden
- eigene Marken je Spiel („nie wieder vorschlagen“, „merken“), Sharenite als Nachschub
- Besitz mit zweiter Quelle bestätigen (Steam-Konto und Sharenite, Meta-Käufe und VRDB) und
  Widersprüche melden statt sie nachzufragen

## Danach

- Freie Abrufe für die PC-Sammlung: Sind alle VR-Titel aktuell, holt der Abgleich mit dem Rest
  seines Kontingents Spielerzahlen für Entdecken (zuerst gut bewertete Mehrspieler-Spiele) und
  hält sie dann ebenso aktuell
- Wunschliste am Desktop als Tabelle mit sortierbaren Spalten

- Bundles und Cross-Buy-Pakete im Preisvergleich
- Benachrichtigung bei neuem Tief eines Wunschtitels
- Export der Meta-Bibliothek als CSV für Playnite
- weitere Anbieter über gg.deals
- Angebotsrhythmus je Titel
