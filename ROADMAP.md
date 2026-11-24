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
Lesezeichen wie die Browser-Helfer im eShopKompass, Proben nachgeschärft. 0.7.2 Darkmode gedämpft wie
im eShopKompass 1.7.15 (`--ink`/`--ink-hi`), Wertung in den Einzelheiten als Zahl, „alle aufklappen“
in der Sammlung (mit Filter, bis 100 Spiele), einfachere Vorschau beim Einlesen, Proben ohne Cargo
und UEVR, IGDB-Suche mit Plattform. 0.7.3 Switch-Sammlung aus dem eShopKompass, nur lesend über eine
Adresse im eigenen Netz (`ESHOP_URL`, Entscheidung 27.10.2026): Reiter Switch und Switch 2 mit Wertung,
Spielzeit, Beschreibung und Mein Stand von dort. 0.7.4 Sammlung mit Reitern je Familie (PlayStation,
Nintendo …), deren Konsolen rechts ausklappen; „alle aufklappen“ bis 150 Spiele; Zahlen in „Zu
erledigen“ farbig, dezenter Knopf für den ROM-Ordner; Steam-Rezensionen mit drei Formen der Adresse;
Proben: PCGamingWiki-Vorlagen sauber gelesen, Lenkrad und Force Feedback (Sim-Racing), Nexus Mods
(Spielseite, beliebte Mods, Mods mit VR im Namen), DekuDeals-Treffer, mehr IGDB-Namensversuche. 0.7.5 Gleiten der Konsolen einheitlich und ruhiger, Switch und Switch 2 in
einem Reiter mit Filter „System“, Switch-Spiele wie „Spiele“ im eShopKompass (Spalten Konsole, Lokal,
Online, Koop, Metacritic, Spielzeit; Marken; Einzelheiten) und Link direkt auf das Spiel dort, Infotext
zum Aufklappen; Steam-Rezensionen zusätzlich über die Store-Schnittstelle der Web API; Proben: bester
DekuDeals-Treffer, Lenkrad an einem Rennspiel, IGDB über einen Teil des Namens. 0.7.6 Gleiten langsamer
wie die Kopfzeile, Filter wie im eShopKompass im Reiter Switch 2 (Spielweise, Spielzeit, USK; System nur
dort), Link „eShopKompass“ in dessen Marke, Sammlung nach dem Abgleich neu geladen. 0.7.7 Feld für den
persönlichen Nexus-Schlüssel (geht bei der Nexus-Abfrage mit), Mein Stand in den Einzelheiten auch bei
Reitern mit wenigen Spalten im Bild. 0.8.0 IGDB im Abgleich für die ganze Sammlung (Steam-IDs gebündelt,
sonst Name und System; falscher Treffer zählt nicht), Rangfolge je Feld für Wertung, Spielzeit, Spieler,
Genre, Mehrspieler und Beschreibung in allen Reitern außer Switch und VR; Verbindungstest im Hintergrund
(kein 504 mehr). 0.8.1 VR per Mod: PCGamingWiki je Steam-Spiel ohne eingebautes VR, Nexus-Spieleliste
und Mods je PC-Spiel; Marke, Filter, Links in den Einzelheiten. 0.8.2 Wunschliste mit Unterreitern VR
und PC: die ganze gg.deals-Wunschliste mit Steam-ID und Preisen (Händler, Keyshop, Tief). 0.8.3 Marke
„Lenkrad“ (Entscheidung 27.10.2026, „Beides“): Liste der Rennsimulationen aus dem Simucube-Forum als
Bestätigung, Steam-Schlagwörter (gebündelt über die Store-Schnittstelle) als violetter Hinweis; die
Simagic-Liste liegt hinter einer Bot-Prüfung. 0.8.4 Retro: 3DS mit Fassungslisten für Module und eShop,
Sprachen genau der eigenen Fassung über den Produktcode im Dateinamen; ähnliche Namen ohne Treffer zum
Bestätigen in „Zu erledigen“. 0.8.5 nach dem Verbindungstest: Lenkrad auch für VR-Titel, SimHub als zweite
Liste (Steam-ID im Bildnamen), strengere Schlagwort-Regel, Simucube nur der erste Beitrag; Nexus-Spieleliste
in Seiten zu 80. 0.8.6: „Beschleunigt auffüllen“ (ein Lauf von Hand mit fünffachen Grenzen, Pausen
bleiben); Retro: DSiWare-Liste beim DS, Titel ohne Leerzeichen gleich, ähnliche Namen nur bei gleichen
Zahlen; die Simucube-Liste wird nach einem neuen Leser gleich neu gelesen. 0.8.7: Wunschliste PC vor VR, mit Paketen
und DLC, VR-Spiele nur unter VR; VR-Titel am PC (auch Meta mit Crossbuy) in der Sammlung PC, VR-Marke aus mehr
Quellen; Suche je Reiter; Liste als CSV, Titel kopieren; Mein Stand überall an derselben Stelle; PC-Wunschliste in
der Sicherung. 0.8.8: Retro-Spielinfos aus der libretro-database (Genre, Spieler, Erscheinen, Entwickler, bei PS1
und PS2 Beschreibung), deine Ordner-Listen als erste Quelle mit Widersprüchen beim Genre in „Zu erledigen“,
Dateigröße aus der Ordnerwahl; Lenkrad-Marke auch bei VR-Titeln am PC ohne Playnite-Eintrag; das
gg.deals-Lesezeichen nennt, wenn gg.deals mehr Einträge zählt, als Links da waren. 0.8.9: VR-Titel am PC ohne Playnite-Eintrag
als eigene Spiele der Sammlung in allen Abrufen (Steam-Details, Rezensionen, IGDB, Mods); IGDB fragt Retro abwechselnd
mit den übrigen Spielen statt nach allen PC-Spielen. 0.8.10: Mein Stand in den Einzelheiten wieder gleich nach der
Spalte „Spiel“. 0.8.11: PC-Wunschliste mit Spielinfos von Steam und IGDB (Wertung, Spielzeit, Genre,
Einzelheiten), „Jetzt“ für alle Wünsche mit Schalter Alle, VR, PC. 0.8.12: Wunschliste PC und Jetzt brachen bei einer
Wertung nur von IGDB ab (fehlende Zahl der Bewertungen); Hinweisklappe dezenter und über die volle Breite. 0.8.13: Preise als Links, Abstand zum Tief in Euro; SimRacing
und Geheimtipp farbig, Geheimtipp erst ab 0,4, Filter VR im Reiter PC; Retro-Genre nur noch als Fall, wenn libretro
und IGDB sich einig sind, Sprachen bestätigt bei genau gleicher Datei in der Fassungsliste; „Zu erledigen“ klärt
Gekauftes selbst, „fehlt auf Laden-Wunschliste“ nur noch an der Karte; Steam-Namen ohne Leerzeichen gleich. 0.8.14: Sammlung
schneller: der Server hält sie berechnet, bis sich eine ihrer Dateien ändert, die Seite lädt sie im Hintergrund vor,
Genre-Blasen in einem Messdurchgang. 0.8.15: Urteil „wo kaufen“ aus Gemessenem (Crossbuy,
Preisabstand, Spieler, Wertung, Pflege; Recherche halb) im Kopf der Karte, Gründe in der Zeile „Wo“. 0.8.16: Retro-IGDB-Suche mit deinem Titel aus der
Ordner-Liste; GameCube, Wii und PlayStation über Spiel-ID und Seriennummer. 0.8.17: Hinweis-Marken in der Farbe ihrer Marke; Wunschliste PC
wie im eShopKompass (Preis mit Tooltip, „am Tief“ grün, Spalten Spieler und Jahr); Gekauftes fällt nicht mehr von selbst
von der Wunschliste; Jetzt mit Reitern. 0.8.18: Trend (Steam-Rezensionen der letzten 30 Tage gegen alle) als Pfeil an der
Wertung und Pflege („ruht“ nach einem Jahr ohne Update), auch für die PC-Wunschliste; „Preissturz“ aus dem eigenen
Preisverlauf je PC-Wunsch. 0.8.19: Spaltenreihenfolge, Wichtiges links (Wertung, Genre, Spielzeit, Mehrspieler),
Nachschlagen rechts. 0.8.20: Marken VR und SimRacing umrandet, Hinweise gestrichelt ohne „?“; Switch-Systemwahl als
Menü am Ende der Filterzeile; „hinzugefügt am“; Jetzt mit PC über VR. 0.8.21: Trend wöchentlich für alle Spiele ab 50 Rezensionen, nicht erst mit der nächsten
Rezensionszahl. 0.8.22: VR-Wünsche als Tabelle wie die PC-Wünsche, die Karte als Einzelheiten; Jetzt
mit zwei gleich gebauten Tabellen. 0.8.23: eine Spaltenreihenfolge für alle Tabellen, „max. Spieler“ statt Mehrspieler,
„Aktiv“ auch für PC-Spiele, Wertung der eigenen Fassung im Reiter VR. 0.8.24: PC-Wünsche ohne Steam-ID: mehr Suchen, Grundform des
Namens, Ähnliches zum Bestätigen in „Zu erledigen“; Geheimtipp dunkler. 0.8.25: Preissturz auch für VR-Wünsche. 0.8.26: Trend zählt halb in „wo kaufen“. 0.8.27: Jetzt „Alle“ als eine gemischte Tabelle. 0.9.0: Läden einzeln über IsThereAnyDeal, Jetzt PC nach Laden. 0.9.1: Preisverlauf je Titel. 0.9.2: „Meinung fehlt“ mit Auftrag für die Recherche. 0.9.3: Spielzeit und „zuletzt gespielt“ aus dem Steam-Konto, Mischung „Liegt brach“. 0.9.7: Spiele aus dem Steam-Konto in der Sammlung. 0.9.8: Kürzen zu „+n weitere“, Ladenfarben. 0.9.9: gg.deals-Sammlung per Lesezeichen. 0.10.0: Preismuster aus dem eigenen Verlauf („üblich −x %“, Rhythmus), Crossplay. 0.10.1: ITAD-Titelsuche, Aktiv zuerst für Mehrspieler, Spieler aus der Recherche, Wachstum der Meta-Bewertungen. 0.10.2: „ignorieren“ in Mein Stand, Besitz mit zweiter Quelle, Pflege je Laden ohne Meta-Datum, Pakete gegen Einzelpreise, Steam-Angebote je Wunsch, Crossplay nach Quelle benannt, violett statt „≈“ überall (Entscheidung 02.11.2026); 0.10.3: PC-Einzelheiten nur mit Preisen, die zählen, VR-Einzelheiten Angaben links und Läden rechts mit Kurzbeschreibung, Crossplay als Marke, Preisverlauf schließt mit ✕ und Klick daneben; 0.10.4: teurere Wege in den PC-Einzelheiten nur bis 8 % über dem günstigsten und nah am Tief; 0.10.5: Meta im Meta-Blau, Steam im dunklen Steam-Blau; 0.10.6: Genres der VR-Einzelheiten unter Genre, keine doppelten Marken, Mein Stand als Grafik, Filter Crossplay, Preisverlauf mit „überm Tief“ und Links; 0.10.7: Tooltips mit tatsächlichem Tief, „jetzt“ im Preisverlauf grün und ★ am Tief, Wertungen farbig, Zeile unter der Maus hervorgehoben, Mein Stand ohne Neuaufbau der Tabelle; 0.10.8: Zeile bleibt beim Aufklappen stehen, PC-Genres unter Genre, Hover im Darkmode dunkler, Sortieren-Auswahl hebt die Spaltensortierung auf; 0.10.9: sortierte Spalte mit Richtung in „Sortieren“, Lesezeichen bis 200 Seiten und nur mit Launchern; 0.10.10: Konsolenspiele der gg.deals-Sammlung nicht in der Sammlung PC; 0.10.11: PlayStation auch nicht aus Playnite (kommt später über den ROM-Ordner); 0.10.12: „DE fehlt“ in „Zu erledigen“ mit „ignorieren“, Erscheinungstag von IGDB, Probe GameTDB; 0.10.13: GameTDB im Abgleich (GameCube, Wii, DS, 3DS, PS3), PS3 mit Redump, Probe Wikidata und Wikipedia; 0.10.14: DekuDeals als zweite Quelle der Sammlung (Spielzeit laut HowLongToBeat, OpenCritic, USK, Spieler, Genre, Jahr); 0.10.15: Namen unter „Zu erledigen“ führen zu den Einzelheiten, Zustand und Sammlung vorab gerechnet, Wunschliste PC seitenweise; 0.10.16: Wikidata und deutsche Wikipedia für die Retro-Spiele (Beschreibung, Titel, USK), Filter Mehrspieler neben max. Spieler; 0.10.17: Recherche mit Technik je Fassung, aktuellerer Fassung, Lobbys je Plattform, Deutsch, Umfang, Auffrischen nach sechs Monaten; 0.10.18: Meldung nach dem Meinungs-Import nennt gespeicherte Meinungen statt „neu angelegt“; 0.10.19: Auftrag ohne Umbrüche mitten im Satz; 0.10.20: Vorschau des Meinungs-Imports nennt gefundene Spiele und ersetzte Meinungen; 0.10.21: Quellen gleichzeitig in Strängen, Pausen je Server, Protokoll in Blöcken je Quelle; 0.10.22: elf Stränge, unabhängige Quellen warten nicht mehr aufeinander; 0.10.23: Steam-Konto hängt nur Apps mit VR an, falsche Zuordnungen über den Namen werden gelöst; 0.10.24: „Zu erledigen“ herunterladen (CSV) und als Auftrag für eine Recherche, Antwort mit Vorschau einlesen; 0.10.25: Meinungen auch für die VR-Sammlung mit nur einer Fassung, „Zweitkauf lohnt“; 0.10.26: Zweitkauf in „Jetzt“, Recherche zu Lenkrad und VR-Mods der Sammlung; 0.10.27: Sammlung nach Erscheinungsjahr filtern („ab“, „vor“) und Genres ausschließen („ohne“); 0.10.28: VR-Ports laut Flat2VR Index und UEVR-Profile laut UEVR Hub in der Sammlung; gestrichen: Export der Meta-Bibliothek für Playnite (die Käufe stehen schon im Tool) und Meldungen bei neuem Tief. Grundsatz (Entscheidung 22.10.2026): so wenig
Handarbeit wie möglich; was sich abrufen und von einer zweiten Quelle bestätigen lässt, geht vor
Bestätigen und Einlesen von Hand. Als Nächstes:

- Meldungen aufs Handy: nicht gewünscht (Entscheidung 28.10.2026)

- Spielzeit auch für Spiele außerhalb von Steam: Export aus Playnite mit dem Plugin für HowLongToBeat, dann
  einlesen (wartet auf einen Zugang zu Playnite, Stand 02.11.2026)

- Gesamtbild (Entscheidung 27.10.2026): Das Tool wird zum Navigator über die ganze
  Spielesammlung. „Jetzt“ wird die Startseite für alle Wünsche, mit einem Filter VR; der genaue
  Vergleich Meta gegen Steam bleibt in der VR-Wunschliste. Name: VR-Navigator bleibt
  (Entscheidung 27.10.2026)
- Datenbasis je Plattform (Entscheidungen 27.10.2026): alles Sinnvolle automatisch abrufen, je
  Feld eine feste Rangfolge der Quellen (wie Metacritic vor OpenCritic im eShopKompass),
  Ersatzquelle sichtbar; welche Spalten ein Reiter zeigt, wird je Reiter entschieden. Playnite
  nur im Nachrang, keine Playnite-Plugin-Daten. Nach den Proben (0.7.0) entscheiden: Spielzeit
  wie im eShopKompass, Kurzbeschreibung je Spiel in den Einzelheiten, „VR per Mod“ (PCGamingWiki,
  UEVR-Profile). Unklarheiten möglichst selbst auflösen
- PC-Wunschliste: gg.deals bleibt führend (Wunschliste und Sammlung dort), das Tool liest sie
  wie der eShopKompass DekuDeals (Entscheidung 27.10.2026). Eigene Ansicht als Unterreiter
  der Wunschliste, automatisch gelesen, mit Wertung, Spielern und Bestpreisen. Dazu
  je Spiel die Läden nah am Bestpreis, damit sich mehrere Spiele in einem Laden bündeln lassen;
  die gg.deals-API liefert nur das günstigste Angebot je Händler und Keyshop, die Liste aller
  Läden steht nur auf der Spielseite (Cloudflare), also vermutlich über das Lesezeichen
- PlayStation: seit 0.10.11 nicht aus Playnite und gg.deals (Entscheidung 02.11.2026), sondern über den ROM-Ordner
  wie die Nintendo-Systeme. Bereit (Stand 0.10.13): PS1, PS2 und PSP mit Redump-Fassungen („DE fehlt“), Spielinfos der
  libretro-database (bei PS1 und PS2 mit Beschreibung) und IGDB; PS3 mit Redump-Fassungen über die Seriennummer und
  GameTDB (deutsche Beschreibung, USK, Spieler); PS4 und PS5 bekommen Spielinfos von DekuDeals (seit 0.10.14 im
  Abgleich, über den Namen und die Plattform). Offen: PS4 und PS5 im ROM-Ordner (keine Redump-Liste, Zuordnung über die
  CUSA-Kennung im Dateinamen oder den Namen) und Vita (No-Intro nur für Downloads)
- Deutsche Beschreibung für die übrigen Systeme (SNES, NES, N64, GB, GBC, GBA, PS1, PS2 …): Wikidata und die deutsche
  Wikipedia ohne Schlüssel, die Probe läuft seit 0.10.13 im Verbindungstest; nach dem Ergebnis entscheiden. Als
  Alternative ScreenScraper (deutsche Beschreibungen für fast alle Retro-Spiele), braucht aber ein Konto und eine
  Entwickler-Kennung

## Danach

- Flat-to-VR, Schritt 2 (nach 0.10.28): ähnliche Namen (Editionen, Remakes), die der Abgleich bewusst nicht zuordnet,
  als Liste unter „Zu erledigen“ mit „passt“ und „falsch“; Source-Ports auch für Retro-Spiele, wenn gewünscht.
  Nur verlinken, nicht auslesen: PCVR Central (keine offene Lizenz), UEVR Deluxe (keine dokumentierte Schnittstelle).
  Später möglich: die VRMods-List (CC BY 4.0, nur als HTML-Seite)

- Freie Abrufe für die PC-Sammlung: Sind alle VR-Titel aktuell, holt der Abgleich mit dem Rest
  seines Kontingents Spielerzahlen für die Sammlung (zuerst gut bewertete Mehrspieler-Spiele) und
  hält sie dann ebenso aktuell
- Pakete selbst finden: welche Meta-Bundles einen Wunsch enthalten, nennt bisher keine abrufbare Quelle; das Tool
  vergleicht nur Pakete, deren Inhalt es kennt (0.10.2)
- weitere Anbieter über gg.deals

## Stabilisierung nach dem Review (ab 0.10.29)

Reihenfolge fest: V-1 Betrieb und Fehlerbehandlung (0.10.29), dann die Schreibfelder der Sammlung erfassen und V-2
Nutzereingaben aus `collection.json` in eine eigene kleine Datei (0.11.0, `docs/sammlung-felder.md`), V-3 schlanke Listen und
Messung vorher und nachher (0.11.1, `docs/leistung.md`: eine Entscheidung 0,17 statt 0,85 s, SQLite nicht nötig),
V-5 Statuskarte „Betrieb“ im Einstellungsreiter (0.11.2: eingeklappt der Gesamtstatus, Leistungstest im eigenen
Prozess), danach Dokumentation, Altlasten und V-6.

Später, wenn belegbar: VR-Platzbedarf (Spielfläche, sitzend, stehend, Roomscale; nur dokumentierte Angaben) und die
Qualität eines UEVR-Profils als weiteres Kriterium der bestehenden KI-Aufträge (mit Quellen und Stand, erst Vorschau).

## Von den Geschwistern

Pokédex, eShopKompass und VR-Navigator bleiben eigenständig (kein gemeinsamer Kern, keine Submodule). Hier steht, was
sich lohnen könnte, hinüber oder herüber zu nehmen; übernommen wird nur nach Prüfung im jeweiligen Projekt.

- Ruhezeit je Server statt je Quelle, sofort gespeichert (`app/ruhe.py`, 0.10.29): lohnt im eShopKompass, wenn dort
  mehrere Quellen denselben Server fragen; mit nur einer Quelle je Server bringt es wenig.
- Zwischenstand des Abgleichs nach jeder Quelle und Erkennung eines unterbrochenen Laufs (0.10.29): passt zu jedem
  Projekt mit längeren Läufen und Watchtower-Neustarts.
- Tägliche Sicherung im Datenordner mit monatlichem Wiederherstellungstest im temporären Ordner (`app/sicherung.py`):
  übertragbar, die Teile der Sicherung sind je Projekt andere.
- Feldweises Einspielen mit Vorschau und Sicherung vorher, NaN und Unendlich abgelehnt: übertragbar.
- `/healthz` und `HEALTHCHECK` im Image: übertragbar ohne Anpassung.
- Nutzereingaben getrennt von abgerufenen Daten, eingesetzt beim Lesen (0.11.0): der eShopKompass hat dasselbe Muster
  (Mein Stand neben großen Abrufdaten); lohnt dort, wenn seine Sammlung beim Haken spürbar langsam schreibt. Erst messen.
- ETag und 304 für die großen Antworten, mit HTTP/1.1 (sonst fragt Chromium nicht nach), dazu Stile und Skript mit der
  Version in der Adresse (0.11.1): übertragbar auf eShopKompass und Pokédex, beide liefern ebenfalls große JSON-Antworten
  an dieselbe Seite. Klein und ohne Risiko für die Daten.
- Statuskarte mit Gesamtstatus und Leistungstest im eigenen Prozess mit erfundenen Daten (0.11.2, `app/betrieb.py`):
  übertragbar auf beide; die Gründe für Hinweise und Probleme sind je Projekt andere, der Leistungstest braucht je
  Projekt einen eigenen Generator für erfundene Daten.
- Nach einer Entscheidung nur die betroffenen Zeilen neu rechnen und zurückgeben (0.11.1): lohnt nur, wo eine
  Entscheidung heute die ganze Liste neu baut; im eShopKompass erst messen.
