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
abschaltbar (am PC zählt dann nur gg.deals, Entscheidung 22.10.2026), 0.5.3 erster Abgleich
fünf statt zwei Minuten nach dem Start, 0.5.4 jeder Aufpreis über dem Bestpreis wieder rot,
am PC zählt das günstigste Angebot einschließlich Keyshops, Links direkt zum Spiel zum Entfernen
von einer Laden-Wunschliste (Entscheidungen 26.10.2026), 0.5.5 Entdecken je System (Konsolenspiele
aus Playnite nicht mehr verworfen, Reiter „Alle“, PC, PS4 …), 0.5.6 Retro-Liste aus dem
ROM-Ordner (Ordnerwahl im Browser, nur Namen), Reiter heißt „Sammlung“, Kopfleiste blendet beim
Scrollen aus wie im eShopKompass (Entscheidungen 26.10.2026), 0.5.7 „DE fehlt“ für Retro-Spiele
aus No-Intro, Redump und Retool mit Filter „Sprache“, 0.5.8 Sammlung öffnet bei PC, Reiter in
Familienfarben, PlayStation-Trophäenlisten als „PS3 / Vita“ (Entscheidungen 27.10.2026). 0.6.0
Zusammenführen (Entscheidung 27.10.2026): Sammlung mit Spalten, Sortierung per Spaltenkopf,
Einzelheiten und Mein Stand wie „Spiele“ im eShopKompass, die Bibliothek als Reiter VR darin,
„VR-Wunschliste“ mit dem Urteil „kaufen“ und „gut“, „Aktualisieren“ und die Sicherung wie im
eShopKompass. 0.6.1 Feinschliff nach Rückmeldung (27.10.2026): violett statt „≈“ in der
Sammlung, Spalte Launcher (PC) bzw. System (Konsole), Genres einzeilig mit „+n weitere“ und
fester Reihenfolge, Mein Stand an fester Stelle, PS1 statt PS, Quellen in den Einstellungen
farbig. 0.6.2 Einzelheiten nur mit Mehrwert, Genres klappen in der Zeile auf, Entwickler und
Verlag im Tooltip am Jahr, Quellen als kompakte Tabelle (Entscheidungen 27.10.2026). 0.7.0 Proben
der neuen Quellen im Verbindungstest, IGDB-Schlüssel in den Einstellungen. 0.7.1 Einzelheiten mit
Metacritic, Sprachen, Erscheinen und Kurzbeschreibung aus den Steam-Details, Aufklappen ohne Springen,
Lesezeichen wie die Browser-Helfer im eShopKompass, Proben nachgeschärft. Grundsatz (Entscheidung 22.10.2026): so wenig
Handarbeit wie möglich; was sich abrufen und von einer zweiten Quelle bestätigen lässt, geht vor
Bestätigen und Einlesen von Hand. Als Nächstes:

- Retro, Sprache: 3DS über die Title-ID, ähnliche Namen ohne Treffer als „≈ vielleicht dieselbe
  Fassung“ zum Bestätigen
- Retro, Infos: Genre, Spielerzahl, Jahr aus der libretro-database, zur Bestätigung IGDB
  (optionaler Twitch-Schlüssel); jede Quelle zuerst als Probe in „Verbindung testen“.
  GameCube, Wii und PlayStation mit Redump-Namen

- Urteil „wo kaufen“ aus Gemessenem (Spieler, Pflege, Crossbuy, Wertung, Preis) als
  Hinweis im Kopf der Karte („Meta kaufen“, „warten“), Gründe in der Klappe; Recherche nur als
  Ergänzung
- Spielzeit und „zuletzt gespielt“ (Steam-Konto oder zusätzliche Playnite-Spalten),
  Mischung „Liegt brach“, Gespieltes ausblenden
- weitere Marken je Spiel neben Mein Stand („nie wieder vorschlagen“), Sharenite als Nachschub
- Besitz mit zweiter Quelle bestätigen (Steam-Konto und Sharenite, Meta-Käufe und VRDB) und
  Widersprüche melden statt sie nachzufragen

- Gesamtbild (Entscheidung 27.10.2026): Das Tool wird zum Navigator über die ganze
  Spielesammlung. „Jetzt“ wird die Startseite für alle Wünsche, mit einem Filter VR; der genaue
  Vergleich Meta gegen Steam bleibt in der VR-Wunschliste. Name: VR-Navigator bleibt
  (Entscheidung 27.10.2026)
- Datenbasis je Plattform (Entscheidungen 27.10.2026): alles Sinnvolle automatisch abrufen, je
  Feld eine feste Rangfolge der Quellen (wie Metacritic vor OpenCritic im eShopKompass),
  Ersatzquelle sichtbar; welche Spalten ein Reiter zeigt, wird je Reiter entschieden. Playnite
  nur im Nachrang, keine Playnite-Plugin-Daten. Nach den Proben (0.7.0) entscheiden: Spielzeit
  wie im eShopKompass, Kurzbeschreibung je Spiel in den Einzelheiten, „VR per Mod“ (PCGamingWiki,
  UEVR-Profile). „≈“ auch in der VR-Wunschliste ablösen und Unklarheiten möglichst selbst auflösen
- PC-Wunschliste: gg.deals bleibt führend (Wunschliste und Sammlung dort), das Tool liest sie
  wie der eShopKompass DekuDeals (Entscheidung 27.10.2026). Eigene Ansicht als Unterreiter
  der Wunschliste, automatisch gelesen, mit Wertung, Spielern und Bestpreisen. Dazu
  je Spiel die Läden nah am Bestpreis, damit sich mehrere Spiele in einem Laden bündeln lassen;
  die gg.deals-API liefert nur das günstigste Angebot je Händler und Keyshop, die Liste aller
  Läden steht nur auf der Spielseite (Cloudflare), also vermutlich über das Lesezeichen
- PS4-Sammlung: steht seit 0.5.5 mit im Reiter, wenn der Playnite-Export die PlayStation-Bibliothek
  enthält; Sharenite als zweite Quelle, Preise der PlayStation ohne offene Schnittstelle, daher
  zuerst ohne Preise

## Danach

- Freie Abrufe für die PC-Sammlung: Sind alle VR-Titel aktuell, holt der Abgleich mit dem Rest
  seines Kontingents Spielerzahlen für die Sammlung (zuerst gut bewertete Mehrspieler-Spiele) und
  hält sie dann ebenso aktuell
- Wunschliste am Desktop als Tabelle mit sortierbaren Spalten

- Bundles und Cross-Buy-Pakete im Preisvergleich
- Benachrichtigung bei neuem Tief eines Wunschtitels
- Export der Meta-Bibliothek als CSV für Playnite
- weitere Anbieter über gg.deals
- Angebotsrhythmus je Titel
