# Abrufe: was woher, wie oft, wohin

Der Abgleich liest erst deine Konten (Steam, gg.deals-Wunschliste, Sharenite) und holt dann Preise nur für Wunschtitel, die du noch nirgends besitzt. Er läuft nach
Zeitplan (Standard alle 6 Stunden, einstellbar von 2 bis 48) und auf Knopfdruck unter
**Einstellungen**, Abgleich, oder oben über „Aktualisieren“. Fünf Minuten nach dem Start des Containers läuft ein
Abgleich, wenn der letzte länger als 30 Minuten zurückliegt, etwa nach einem Update mit neuen
Lesern. Ist der letzte vor weniger als 30 Minuten fehlgeschlagen, wartet auch dieser Lauf. Mit
`AUTO_SYNC=0` läuft gar kein Zeitplan.

Alle Abrufe gehen über `sources.fetch`: ehrliche Kennung `vr-navigator/<Version>`, nur
öffentliche Ziele, Grenzen für Zeit und Größe. Zwischen zwei Abrufen derselben Quelle liegen
2 Sekunden. Nach einem kurzen Netzfehler gibt es nach 5 Sekunden einen zweiten Versuch.
Antwortet eine Quelle mit 403 oder 429 oder mit einer Prüfseite (Cloudflare „Just a moment“),
endet sie für diesen Lauf und **ruht 24 Stunden**, auch über spätere Läufe hinweg; das Protokoll
nennt das Ende der Ruhezeit. Nach 5 anderen Fehlern endet sie nur für diesen Lauf. Die übrigen
Quellen laufen weiter, und es gelten die zuletzt gelesenen Preise.

**Beschleunigt auffüllen** (ab 0.8.6, nur von Hand, `run(fast=True)`): Für diesen einen Lauf gelten die
Grenzen je Lauf mal `FAST` (5): `REVIEWS_MAX`, `DETAILS_MAX`, `RATING_MAX`, `IGDB_NAMES`, `PCGW_MAX`,
`NEXUS_MAX`, `WHEEL_MAX`, `PLAYERS_MAX`, `VRDB_MAX`. Pausen, Ruhezeiten und der Abbruch bei 403 und 429
bleiben wie sonst; danach gelten wieder die üblichen Grenzen. Der Zeitplan startet nie einen solchen Lauf.

## Protokoll, Selbstprüfung, Verbindung testen

- **Protokoll:** jede Quelle schreibt, was sie tut, live während des Laufs (letzte 200 Zeilen,
  Zeit in UTC, die Oberfläche zeigt die Zeit des Browsers). Unter Einstellungen, Protokoll, zum Lesen und Kopieren.
  Die zweite Zeile ist eine Kurzfassung nach dem Lauf: Wunschtitel im Angebot, günstiger
  gewordene, neue Meta-Tiefstpreise, Quellen mit Fehler, Ergebnis der Selbstprüfung.
  Warteschlangen (Steam-Konto, Rezensionen, Details, Wertungen, Spieler, VRDB) nennen, wie viele
  Läufe sie noch brauchen. Preisänderungen unter 0,50 € und unter 5 % zählen als „kleine
  Schwankungen“ und stehen nur als Zahl da.
  Je Lauf: Anlass (von Hand, nach Zeitplan, nach dem Start); je Quelle Angebote samt
  Wunschtiteln darin, gelesene und noch aktuelle Titelseiten, was folgt, Suchen mit Treffern,
  Titeln ohne Treffer und dem Tag der nächsten Suche, Dauer und Anfragen; danach
  Preisänderungen (günstiger, teurer, neuer Meta-Tiefstpreis), der Stand der Wunschliste je
  Quelle mit den Titeln ganz ohne Preis, die Selbstprüfung und die Gesamtdauer.
- **Selbstprüfung** nach jedem Lauf: keine Angebote erkannt, obwohl es beim letzten Lauf welche
  gab; Titelseiten ohne lesbaren Preis; keine Preise für bekannte App-IDs bei Steam oder
  gg.deals; Normalpreise, die sich um mehr als 50 % ändern. Treffer stehen im Protokoll und als
  Hinweis über den Ansichten.
- **Verbindung testen** fragt jede Quelle einmal an, mit einem Titel deiner Wunschliste, und
  beschreibt die Antwort: HTTP-Status, Server, Kodierung, Größe und was die Leser erkennen
  (Angebote und Seiten, Suchtreffer, Preis, Tief und Version der Titelseite, Steam-Preis,
  gg.deals-Antwort samt Anfang). Gespeichert wird nichts; der gg.deals-Schlüssel erscheint nie
  im Ergebnis. Seit 0.8.0 läuft er in einem eigenen Faden auf dem Server (`POST /api/diag` startet,
  `GET /api/diag` liefert den Stand, ein zweiter Start während des Laufs startet nichts neu).
- **Proben neuer Quellen** (0.7.0, `app/probes.py`): je ein Spiel der Sammlung (PC mit den
  meisten Steam-Rezensionen, ein Konsolenspiel, ein Retro-Spiel). Steam `appdetails` auf Deutsch;
  PCGamingWiki über die Cargo-Schnittstelle (`cargofields` für `VR_support`, dann das Spiel über
  `Infobox_game.Steam_AppID` und seine VR-Zeile mit den eben gelesenen Feldern); die Startseite
  von uevr-profiles.com; DekuDeals-Suche und Artikelseite (Kasten Details, Beschreibung);
  die Startseite von HowLongToBeat; libretro `metadat/genre`, `maxusers`, `releaseyear`,
  `developer` des Retro-Systems; seit 0.7.1 zuerst `cargotables` (die VR-Tabelle heißt nicht
  `VR_support`), die Skriptdatei der UEVR-Seite (die Seite baut sich erst im Browser) und IGDB beim
  PC-Spiel über `external_games` (Steam-ID); IGDB mit Twitch-Schlüssel (`games` per Suche, dann
  `game_time_to_beats` zum ersten Treffer, eine Sekunde Pause je Anfrage). IGDB-Client-ID und
  -Secret stehen in `settings.json`, erscheinen nie im Ergebnis und nie im Browser.
  Seit 0.7.2: PCGamingWiki ohne Cargo (die Abfrage ist nur noch angemeldet erlaubt,
  „permissiondenied“): `api/appid.php?appid=<App-ID>` leitet auf die Seite des Spiels, dann
  `action=parse&prop=wikitext` und daraus die Vorlage „VR support“ (Native 3D, vorpX, OpenXR,
  SteamVR …). Die UEVR-Profile fallen weg (Browser-App ohne offene Schnittstelle). DekuDeals nur mit
  einem Spiel für Switch, PS4, PS5 oder Xbox (PS1 führt DekuDeals nicht). IGDB sucht Konsolen- und
  Retro-Namen mit der Plattform des Systems, dann ohne Sonderzeichen („é“ als „e“), zuletzt
  ohne Plattform. Die Steam-Rezensionen prüft der Test an drei Spielen (das bekannteste, eins aus der
  Mitte, eins ohne Wert) und nennt bei einer HTML-Antwort Titel und Ziel der Umleitung.
  Seit 0.7.4: Die Rezensionen prüft der Test zusätzlich in Form 2 und 3 der Adresse (siehe unten).
  Die Vorlage „VR support“ wird sauber gelesen (ein leerer Wert schluckt nicht mehr die nächste
  Zeile, Felder „… notes“ fallen weg). Aus derselben Seite die Vorlage „Input“: Lenkrad, Force
  Feedback, Haptik (für Sim-Racing). Nexus Mods über die offene GraphQL-Schnittstelle
  `https://api.nexusmods.com/v2/graphql` ohne Schlüssel, eine Sekunde Pause je Anfrage: das Spiel
  zum Namen (genau, ohne Zusätze wie „Legacy“, dann mit Platzhaltern), Zahl der Mods, Link auf die
  Spielseite, die drei beliebtesten Mods und Mods mit „VR“ im Namen; Fehler stehen wörtlich im
  Ergebnis. Seit 0.7.7 geht ein gespeicherter persönlicher Schlüssel als Kopfzeile `apikey` mit
  (Zeile „Nexus Mods (mit Schlüssel)“); er steht nie im Protokoll.
  DekuDeals erkennt Treffer auch als ganze Adresse mit Zusatz; IGDB versucht bei Konsolen
  auch den Namen ohne Satzzeichen und den Teil nach dem Doppelpunkt.
  Seit 0.7.5: DekuDeals nimmt den Treffer, dessen Name am besten passt (nicht den ersten), und trennt
  Metacritic und Nutzerwertung. Lenkrad und Force Feedback zusätzlich an einem Rennspiel der Sammlung.
  IGDB sucht zuletzt über einen Teil des Namens bis zum ersten Sonderzeichen (`name ~ *"…"*`).

## eShopKompass (eigenes Netz, ab 0.7.3)

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Switch-Sammlung | `ESHOP_URL/api/sammlung` (Umgebungsvariable, etwa `http://eshop-kompass:8787`) | jeder Abgleich einmal, nur mit `ESHOP_URL` | je Spiel Name, System (Switch, Switch 2), Genres, Spieler, Koop, Metacritic oder OpenCritic, Spielzeit, Erscheinen, Firmen, USK, Sprachen, Beschreibung, Kaufdatum, Mein Stand; ab eShopKompass 1.7.17 unter `kv` die Zeile seiner Ansicht „Spiele“ (nur bekannte Felder, gekürzt). Ersetzt nur die Einträge `eshop:<slug>`; eine Antwort, die nicht vom eShopKompass kommt, ändert nichts |

Das ist die einzige Adresse außerhalb des öffentlichen Internets, die das Tool abruft
(`sources.eshop_url`, genau diese eine Adresse mit diesem Pfad; Weiterleitungen woandershin nicht).

## Konten (vor den Preisen)

Jeder Abgleich liest zuerst die eingerichteten Konten, damit neue Wunschtitel gleich Preise
bekommen. Eingetragen wird erst nach dem Lesen, unter der Sperre auf `data.json`.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Steam, Profilname auflösen | `api.steampowered.com/ISteamUser/ResolveVanityURL/v1/` (mit Schlüssel) | nur bei Profilnamen statt Zahl | SteamID |
| Steam, Besitz | `api.steampowered.com/IPlayerService/GetOwnedGames/v1/` (mit Schlüssel) | jeder Lauf | App-ID und Name je Spiel |
| Steam, Wunschliste | `api.steampowered.com/IWishlistService/GetWishlist/v1/` | jeder Lauf | App-IDs |
| Steam, VR-Prüfung | `store.steampowered.com/api/appdetails?appids=<ID>&cc=de&l=german` | je unbekannter App einmal, 40 je Lauf | Name, Kategorien (VR Support, VR Supported, VR Only) |
| gg.deals-Wunschliste | der geteilte Link, `?page=N` | jeder Lauf, höchstens 10 Seiten; nach einer Sperre (Cloudflare) per Lesezeichen, nach 7 Tagen (`GG_RETRY_DAYS`) oder beim Speichern des Links ein neuer Versuch (`sync.json`, `manual`) | Links auf `/game/<name>/` mit Namen |
| Steam-Suche für unbekannte Namen aus dem Lesezeichen | `store.steampowered.com/api/storesearch/` | aus `data["gg_unknown"]`, dasselbe Kontingent | App-ID bei genau gleichem Namen |
| Steam-Suche für unbekannte gg.deals-Namen | `store.steampowered.com/api/storesearch/` | 15 je Lauf, je Name höchstens alle 7 Tage | App-ID bei genau gleichem Namen |
| Sharenite | `sharenite.link/profiles/<Profil>/games?sort=name_asc`, dann mit `tag_ids[]` der VR-Schlagwörter | höchstens alle 20 Stunden (von Hand immer) | Name, Laden und Schlagwörter je Spiel; ohne VR-Filter die ganze Liste (100 je Seite, höchstens 40 Seiten) |

Ergebnis der VR-Prüfung: `data["steam_apps"]` (`{App-ID: {name, vr, at}}`), versuchte
gg.deals-Namen: `data["gg_tried"]`. Wunschlisten setzen je Titel `wish_src` (`{Quelle: Zeit}`,
Quellen `meta`, `steam`, `gg`, `hand`); von Hand genommene Quellen stehen in `wish_off`.
Gekaufte Spiele aus Steam tragen `owned.pc.src = "steam"`, aus Sharenite `"sharenite"` mit dem
Laden als `label`.

## Zuordnung (nach den Konten, vor den Preisen)

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Steam, Prüfung einer Steam-ID „≈“ | `store.steampowered.com/api/appdetails?appids=<ID>&cc=de&l=german` | je App einmal, aus demselben Kontingent wie die VR-Prüfung (40 je Lauf) | Name und VR |
| QuestStoreDB, Suche für Titel außerhalb der Preisliste | `queststoredb.com/all_apps/?release_status=all&q=<Name>` | 15 Anfragen je Lauf, je Titel höchstens alle 7 Tage | Meta-ID, Pfad und Name |

Ergebnis je Titel: `steam_sure` oder `steam_doubt` (Grund), `meta_id` mit `links.qsdb`, gelernte
Namen in `aliases`, von Hand verworfene Steam-Apps in `steam_wrong`. Die Liste „Zu erledigen“
rechnet `titles.todo` jedes Mal aus `data.json` aus. Eine Sperre in diesem Schritt lässt die
Quelle wie sonst 24 Stunden ruhen.

Von 0.8.13 bis 0.8.16 nahm `lists.auto` gekaufte Titel ohne Laden-Wunschliste von der Wunschliste (`wish_done`); ab
0.8.17 holt `lists.undo_auto` sie im selben Schritt zurück und löscht `wish_done` (Entscheidung 28.10.2026). Der
Steam-Name passt auch ohne Leerzeichen oder wenn alle Wörter des kürzeren Namens (mindestens drei, gleiche
Zahlen) in derselben Reihenfolge im längeren stehen. Retro: Die Dateinamen ohne Endung liegen je Spiel in
`dumps` (höchstens 8); steht einer genau so in der Fassungsliste, trägt `de` den Wert `dat` und die Sprachen
gelten als bestätigt. Ältere Daten ohne `dumps` bekommen ihn mit der nächsten Retro-Liste.

## QuestStoreDB (Meta-Preise)

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Angebotsliste | `/on_sale/?sort=-sale_start_time&page=N` | jeder Lauf, alle Seiten (höchstens 15) | Preis, Normalpreis, Rabatt, Ende, Gutschein ja/nein |
| Titelseite | `/game/<name>-<Meta-ID>/` | je Titel höchstens alle 20 Stunden, 60 je Lauf, die älteste zuerst | Preis, Normalpreis, Ende, Tiefstpreis samt Tag, Bewertung, App-Version |
| Suche | `/all_apps/?release_status=all&q=<Name>` | nur ohne bekannten Pfad, 30 je Lauf | Pfad und Meta-ID |

Das Tool schickt das Cookie `currency=EUR`, damit Listen und Preisverlauf in Euro kommen. Die
Titelseite trägt die Preise als strukturierte Daten (JSON-LD, ein Angebot je Währung) und den
Preisverlauf als JSON für das Diagramm; daraus stammt der Tiefstpreis.

Gesucht wird nacheinander unter dem Namen, dem Namen ohne Klammer am Ende und, bei bekannter
Meta-ID, dem Namen aus dem VRDB- oder QuestStoreDB-Link (der passt zur ID, auch wenn der Name
aus der Tabelle anders lautet). Die Suche gilt als Treffer, wenn die Meta-ID gleich ist oder
genau ein Ergebnis einen dieser Namen trägt. Ohne Treffer sucht das Tool sieben Tage nicht
erneut nach dem Titel; eine von Hand eingetragene Meta-ID hebt die Pause auf, ebenso eine
geänderte Suche (`search_v` in `sync.json`). Die Steam-Suche geht genauso vor.

## Steam-Store

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Preise | `/api/appdetails?appids=<IDs>&cc=de&filters=price_overview` | jeder Lauf, Pakete zu 50 IDs | Preis, Normalpreis, Rabatt in Euro |
| Suche | `/api/storesearch/?term=<Name>&l=german&cc=DE` | nur ohne Steam-App-ID, 30 je Lauf | App-ID bei genau einem gleichen Namen |

Kostenlose Titel haben keine Preisangabe und gelten als 0 €. Ein Ende des Angebots nennt
Steam hier nicht.

## gg.deals

Nur mit eigenem, kostenlosem Schlüssel (gg.deals, Einstellungen, API). Der Schlüssel liegt in
`settings.json` im Datenordner, nie in der Sicherung, im Protokoll oder im Browser.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Preise | `https://api.gg.deals/v1/prices/by-steam-app-id/?ids=<IDs>&region=de` | jeder Lauf, Pakete zu 100 IDs | Händler und Keyshops, jetzt und bisheriges Tief, Link |

Das Antwortformat ist noch nicht gegen die echte API geprüft. „Verbindung testen“ zeigt, ob
der Schlüssel angenommen wird, und den Anfang der Antwort.

## Steam-Rezensionen (Sammlung)

Nur mit einer Sammlung (Playnite-Export). Ohne Schlüssel, nach den Preisen.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Rezensionen | `https://store.steampowered.com/appreviews/<App-ID>?json=1&language=all&purchase_type=all&num_per_page=0&filter=summary` | je Lauf höchstens 100 Steam-Spiele der Sammlung, zuerst die ohne Wert, dann die ältesten; jedes nach 30 Tagen neu | Zahl der Rezensionen und Anteil positiv; kommt statt Daten eine Store-Seite (etwa bei Spielen ab 18 ohne Anmeldung), merkt sich der Eintrag `page` und das Protokoll zählt sie (0.7.2) |

Form der Adresse (0.7.4): Am 27.10.2026 leitete Steam die Adresse oben bei allen getesteten Apps auf die
Startseite um. Kommt eine Seite statt Daten, versucht der Abruf beim selben Spiel Form 2
(`…&review_type=all&num_per_page=1&filter=all&cursor=*`) und Form 3 (`json=1&filter=recent&language=all&num_per_page=1`)
und bleibt bis zum Neustart bei der, die Daten liefert; das Protokoll nennt den Wechsel. Gilt für
Sammlung und Wunschliste. Form 4 (0.7.5): `https://api.steampowered.com/IStoreBrowseService/GetItems/v1/`
mit `input_json` (App-ID, `include_reviews`), ohne Schlüssel; liest `reviews.summary_filtered`
(Zahl, Anteil positiv, Text). Lieferte bei einem Spiel keine Form Daten, fragt der Lauf danach je Spiel
nur noch die zuletzt gültige Form. Der Verbindungstest prüft Form 1 und 4 an drei Spielen, Form 2 und 3
am ersten.

Daraus: Wertung „Steam“ ab 50 Rezensionen, Bekanntheit und Geheimtipp-Wert. Hat ein Spiel mit
nur vermutetem Laden Rezensionen, gilt die Steam-ID als bestätigt. Abgelegt je Spiel unter
`rev` in `collection.json`; ein neuer Playnite-Export behält es.

## Steam-Details (Sammlung)

Nur mit einer Sammlung. Ohne Schlüssel, nach den Rezensionen.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Details | `https://store.steampowered.com/api/appdetails?appids=<App-ID>&l=german&cc=de` | je Lauf höchstens 120 Steam-Spiele der Sammlung, zuerst die ohne Wert, dann die ältesten; jedes nach 90 Tagen neu, Einträge von vor 0.7.1 (ohne `v` 2) sofort | Genres, Kategorien (Mehrspieler-Arten, VR), Erscheinungsjahr; seit 0.7.1 auch Metacritic, Kurzbeschreibung (deutsch, ohne HTML, bis 400 Zeichen), Erscheinungsdatum, Entwickler, Verlag, Zahl der Sprachen und ob Deutsch dabei ist. Genres und Kategorien werden über ihre Kennungen gelesen, die Sprache der Antwort ändert daran nichts |

Steam-Genres werden auf die Genre-Gruppen der Sammlung abgebildet (Action, Strategie, Rollenspiel,
Casual, Rennen, Sport, Abenteuer, Simulation), Kategorien auf die Mehrspieler-Arten. Was Playnite
und Steam beide sagen, gilt als bestätigt; der Rest bleibt mit „≈“. Liefert Steam die App, ist
ein nur vermuteter Laden bestätigt. Abgelegt je Spiel unter `steam` in `collection.json`
(`ok: false`, wenn Steam die App nicht kennt); ein neuer Playnite-Export behält es.

## IGDB (Sammlung, ab 0.8.0)

Nur mit Twitch-Schlüssel (Client-ID und Secret in den Einstellungen). Nach den Steam-Wertungen. Je
Anfrage 0,3 Sekunden Pause (IGDB erlaubt vier je Sekunde), Ende bei 403 und 429 wie überall.
Switch-Spiele aus dem eShopKompass fragt es nicht an.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Anmeldung | `https://id.twitch.tv/oauth2/token` (POST, client_credentials) | einmal je Lauf, nur wenn etwas zu tun ist | Zugangsmarke für diesen Lauf |
| Steam-IDs | `https://api.igdb.com/v4/external_games` (POST) | Pakete zu 400 Steam-IDs | IGDB-Spiel je Steam-ID |
| Spiele | `…/v4/games` (POST, `where id = (…)`) | je Paket einmal | Name, Genres, Spielmodi, Mehrspieler-Angaben, Kritiker- und Gesamtwertung samt Zahl, Beschreibung, Erscheinen, Entwickler, Verlag |
| Namenssuche | `…/v4/games` (POST, `search` mit Plattform, dann ohne Sonderzeichen, nach dem Doppelpunkt, ohne Plattform, zuletzt Teilname) | höchstens 120 Spiele je Lauf (`IGDB_NAMES`): erst die ohne Steam-ID, dann Steam-Spiele, die IGDB nicht verknüpft hat; bei gleichem Stand ab 0.8.9 zuerst VR-Titel am PC, dann abwechselnd Retro und die übrigen; ab 0.8.16 bei Retro ohne Treffer dieselben Anfragen noch einmal mit deinem Titel aus der Ordner-Liste (auch für ältere „kein Treffer“ einmal) | wie oben, dazu `alternative_names.name`; ein Treffer zählt nur bei gleichem oder weitgehend gleichem Namen, mit deinem Titel auch bei einem der anderen Namen |
| Spielzeiten | `…/v4/game_time_to_beats` (POST) | Pakete zu 400 Spielen | eilig, normal, komplett, Zahl der Angaben |

Jedes Spiel nach 90 Tagen neu (`IGDB_DAYS`), ohne Treffer nach 30 (`IGDB_MISS_DAYS`), alles sofort,
wenn sich der Stand der Ablage ändert (`igdb.V`). Abgelegt je Spiel unter `igdb` in `collection.json`
(`none: true` ohne Treffer); ein neuer Playnite-Export und eine neue Retro-Liste behalten es.

## PC-Wunschliste (ab 0.8.2)

Die ganze gg.deals-Wunschliste (über den Teilen-Link, das Lesezeichen oder eine Datei) liegt in
`pcwish.json`; eine neue Liste behält Steam-ID und Preise je Spiel. Ab 0.8.7 auch Pakete und DLC (`kind`,
Schlüssel `pack:<slug>`, `dlc:<slug>`): ohne Steam-Suche und ohne API-Preis, nur der Link zur Seite bei gg.deals.
`PCWISH_SEARCH` zählt beim beschleunigten Auffüllen mit. Die Sicherung enthält `pcwish.json` ab 0.8.7. Nach den Konten:

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Steam-Suche | `store.steampowered.com/api/storesearch/?term=<Name>&l=german&cc=DE` | nur ohne Steam-ID aus Titeln oder Sammlung, 30 je Lauf, je Spiel höchstens alle 7 Tage | App-ID bei genau einem gleichen Namen |
| gg.deals-Preise | `https://api.gg.deals/v1/prices/by-steam-app-id/?ids=<IDs>&region=de` (mit Schlüssel) | jeder Lauf, Pakete zu 100 IDs | Händler und Keyshop jetzt, bisheriges Tief, Link |

Spielinfos (ab 0.8.11, Quelle `pcinfo`, gleich nach der PC-Wunschliste) nur für Spiele mit Steam-ID, ohne Pakete
und DLC. Ruhen Steam-Details oder Steam-Rezensionen nach einer Sperre, fragt auch `pcinfo` Steam nicht. Abgelegt je
Spiel in `pcwish.json` unter `steam`, `rev` und `igdb`; ältere Dateien ohne diese Felder laden wie bisher.
`PCWISH_INFO` zählt beim beschleunigten Auffüllen mit.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Steam-Details | `store.steampowered.com/api/appdetails?appids=<ID>&l=german&cc=de` | je Spiel nach 90 Tagen (`DETAILS_DAYS`), zusammen mit den Rezensionen höchstens 60 Spiele je Lauf (`PCWISH_INFO`) | Genres, Mehrspieler, Erscheinen, Entwickler, Beschreibung, VR |
| Steam-Rezensionen | wie bei der Sammlung (`appreviews/<ID>`) | je Spiel nach 30 Tagen (`REVIEWS_DAYS`) | Zahl und Anteil positiv |
| IGDB | `api.igdb.com/v4/external_games`, `games`, `game_time_to_beats` (nur mit IGDB-Schlüssel) | je Spiel nach 90 Tagen (`IGDB_DAYS`), gebündelt zu 400 Steam-IDs | Genres, Spieler, Spielzeit, Kritiken, Jahr |

## PCGamingWiki und Nexus Mods (Sammlung, ab 0.8.1)

Für „VR per Mod“ am PC: nur PC-Spiele, die laut Steam kein VR eingebaut haben. Bekannte Spiele (viele
Steam-Rezensionen) zuerst.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| PCGamingWiki, Seite | `https://www.pcgamingwiki.com/api/appid.php?appid=<App-ID>` | je Steam-Spiel, 60 je Lauf (`PCGW_MAX`), nach 90 Tagen neu | Seitenname (Umleitung) |
| PCGamingWiki, Wikitext | `…/w/api.php?action=parse&page=<Seite>&prop=wikitext&format=json` | je Seite einmal | Vorlage „VR support“: Brillen mit „hackable“ (VR per Mod), „true“ (eingebaut), vorpX |
| Nexus Mods, Spieleliste | `https://api.nexusmods.com/v2/graphql` (POST, `games(count:100, offset)`; Nexus liefert höchstens 80 je Seite, ab 0.8.5 weiter um so viele, wie kamen) | höchstens wöchentlich (`NEXUS_LIST_DAYS`), bis 150 Seiten mit einer Sekunde Pause; abgelegt in `nexus_games.json` | Kürzel, Name und Zahl der Mods je Spiel; Zuordnung lokal über den Namen (auch IGDB-Name, ohne Zusätze wie „Legacy“) |
| Nexus Mods, Mods | dieselbe Adresse (POST, `mods` nach Kürzel) | je zugeordnetem Spiel, 60 je Lauf (`NEXUS_MAX`), nach 30 Tagen neu | die drei beliebtesten Mods, bis drei Mods mit VR im Namen (ganzes Wort, UEVR, vorpX) |

Nexus mit einer Sekunde Pause je Anfrage, mit persönlichem Schlüssel als Kopfzeile `apikey`. Abgelegt je
Spiel unter `pcgw` und `nexus` in `collection.json`; ein neuer Export behält beides.

## Sim-Racing (Sammlung, ab 0.8.3)

Für die Marke „Lenkrad“ der PC-Spiele. Die Kompatibilitätsliste zu Simagic (simracingsetup.com) zeigt
dem Server eine Bot-Prüfung und wird nicht abgerufen.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Liste der Rennsimulationen | `https://community.granitedevices.com/raw/5645` (Rohtext eines offenen Themas im Simucube-Forum; gelesen wird nur der erste Beitrag) | höchstens alle 30 Tage (`WHEEL_LIST_DAYS`), eine Anfrage; abgelegt in `wheel_list.json`; unter 20 Namen bleibt die alte Liste; ändert sich der Leser (`wheel.V`, ab 0.8.6 unter `v`), liest der nächste Abgleich beide Listen gleich neu | ein Name je Zeile; Zuordnung lokal über den Namen (auch IGDB-Name). Bestätigung |
| SimHub, unterstützte Spiele (ab 0.8.5) | `https://www.simhubdash.com/supported-games/` | höchstens alle 30 Tage, eine Anfrage; in `wheel_list.json` unter `simhub` | nur der Abschnitt „Racing“: Steam-IDs aus den Bildnamen, die Namen darunter. Bestätigung |
| Steam-Schlagwörter, Liste | `https://api.steampowered.com/IStoreService/GetTagList/v1/?language=english` | höchstens alle 30 Tage; abgelegt in `steam_tags.json` | Name je Kennung |
| Steam-Schlagwörter je Spiel | `https://api.steampowered.com/IStoreBrowseService/GetItems/v1/?input_json=…` mit `include_tag_count` | zuerst die VR-Titel mit Steam-ID (ab 0.8.5), dann die Steam-Spiele am PC, je nach 90 Tagen (`WHEEL_DAYS`), 50 Apps je Anfrage, höchstens 400 je Lauf (`WHEEL_MAX`) | die stärksten Schlagwörter; Hinweis, wenn unter den ersten zehn „Racing“ oder „Driving“ und „Automobile Sim“ oder „Simulation“ stehen |

Ohne Schlüssel. Abgelegt je Spiel unter `stag` in `collection.json`, je VR-Titel unter `stag` in `data.json`; ein
neuer Export behält es. Der
Verbindungstest prüft beide Steam-Abrufe an einem Rennspiel der Sammlung und die Liste (statt der
PCGamingWiki-Vorlage „Input“, die kein Feld für Lenkräder hat).

## Steam-Wertungen (Wunschliste, Sammlung VR)

Für alle Titel des Tools mit Steam-ID, ohne Schlüssel, nach den Steam-Details.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Rezensionen | wie bei der Sammlung (`appreviews`) | je Lauf höchstens 60 Titel, zuerst die ohne Wert; jeder nach 30 Tagen neu, sofort bei geänderter Steam-ID | Zahl der Rezensionen und Anteil positiv |

Hat die Sammlung dasselbe Spiel in den letzten 30 Tagen schon gefragt, wird der Wert übernommen
statt neu abgerufen. Abgelegt je Titel unter `rev` in `data.json` (mit `app`, der Steam-ID). Die
Meta-Sterne kommen ohne eigenen Abruf aus der QuestStoreDB-Titelseite (`live.meta.rating`).

## VRDB (Wunschliste, Sammlung VR)

Für Titel mit Meta-ID, ohne Schlüssel, nach den Steam-Spielern.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Titelseite | gespeicherter VRDB-Link, sonst `https://vrdb.app/game/<Slug>/<Meta-ID>` (Slug aus der QuestStoreDB-Seite) | je Lauf höchstens 30 Titel; jeder nach 14 Tagen neu, auch nach einem Fehlschlag | Crossbuy, Version, Spielmodi, Meta-Wertung mit Anteil der 4- und 5-Sterne-Bewertungen |

Abgelegt je Titel unter `vrdb`; ändert sich die Version, steht unter `meta_ver` der Tag, an dem
das Tool sie zuerst sah (bei der ersten Sicht leer).

## Steam-Spieler und Updates (Wunschliste, Sammlung VR)

Für Titel mit Steam-ID, ohne Schlüssel.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Spieler | `https://api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers/v1/?appid=<App-ID>` | je Lauf höchstens 80 Titel, jeder nach 20 Stunden | Spieler gerade jetzt |
| Neuigkeiten | `https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/?appid=<App-ID>&count=20&maxlength=1` | jeder nach 7 Tagen | jüngste Entwickler-Meldung, die nach Update klingt (Update, Patch, Hotfix, Version, v1.2) |

Abgelegt unter `play` (jetzt, Tageshöchstwerte der letzten 30 Tage, Spitze) und `news`. Die
Spitze ist die höchste eigene Messung, keine Angabe von Steam. Antwortet Steam bei der
Spielerzahl mit 404, hat die App keine (unveröffentlicht, Demo, nie gestartet): Das zählt nicht
als Fehler, steht als „Apps ohne Zahl bei Steam“ in der Summenzeile und wird nach 20 Stunden
wieder gefragt.

## Retro-Fassungen (Sammlung)

Nur mit einer Retro-Liste, je System, das darin vorkommt. Ohne Schlüssel, nach VRDB.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Fassungsliste | `https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/no-intro/<System>.dat` (Discs: `…/metadat/redump/…`) | je System höchstens alle 7 Tage | alle bekannten Fassungen mit Region, Sprachen und bei GBA, GBC, DS und 3DS dem Produktcode |
| Fassungsliste, weitere | `…/metadat/no-intro/Nintendo - Nintendo 3DS (Digital).dat` (3DS, ab 0.8.4), `…/Nintendo - Nintendo DSi.dat` (DS, ab 0.8.6) | mit der Fassungsliste | Download-Titel aus dem eShop und dem DSi-Shop (DSiWare), mit Produktcode |
| Retool-Liste | `https://raw.githubusercontent.com/unexpectedpanda/retool-clonelists-metadata/main/clonelists/<System> (No-Intro).json` | mit der Fassungsliste | Gruppen von Fassungen eines Spiels mit verschiedenen Titeln |

Fassungen gehören zusammen, wenn sie denselben Titel haben, denselben Produktcode ohne den
Buchstaben für die Region („AMRE“ und „AMRD“) oder in derselben Retool-Gruppe stehen. Beta,
Proto, Demo und Ähnliches zählen nicht. Je Retro-Spiel steht danach unter `de`: Deutsch
vorhanden (`have`), deutsche Fassung fehlt (`missing`, mit der gesuchten Fassung `alt`, ob ihr
Deutsch nur aus der Region geschätzt ist, und worüber sie gefunden wurde), keine deutsche
Fassung bekannt (`none`) oder nicht in der Liste (`unknown`, mit `near`, wenn ein ähnlicher Titel in der
Liste steht). Nennt der Dateiname eines 3DS-Spiels den Produktcode, stehen unter `langs` und `rel` die
Sprachen und der Name genau dieser Fassung (ab 0.8.4, `retro_dat.json` in Fassung 2). Bestätigte
ähnliche Namen stehen je Spiel unter `alias`, abgelehnte unter `near_no`; ein neuer Import behält beides.
Ab 0.8.6 (`retro_dat.json` in Fassung 3, alle Listen einmal neu): eine Fassung je Eintrag `game ( name … )`
(in der DSi-Liste heißen viele Dateien nur „00000000“), dazu `sq` mit Titeln ohne Leerzeichen.
Systeme ohne Liste bleiben ohne Angabe. „Verbindung testen“ fragt beide Listen eines Systems der Retro-Liste einmal ab.

### Spielinfos (0.8.8)

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Spielinfos je Feld | `…/metadat/genre/<System>.dat`, ebenso `maxusers`, `releaseyear`, `releasemonth`, `developer`; dazu dieselben Felder der weiteren Listen (3DS-Downloads, DSiWare) | je System höchstens alle 30 Tage (`META_DAYS`), früher nur, wenn ein Retro-Spiel des Systems noch kein `lr` hat; 404 heißt „gibt es nicht“ | Genre, Spielerzahl, Jahr und Monat, Entwickler; bei PS1 und PS2 steht in der Entwickler-Liste alles, mit Verlag, Tag und englischer Beschreibung |

Die Listen werden nur im Speicher zu einem Verzeichnis je Titel; behalten wird je Retro-Spiel unter `lr`, was
passt (`n` Name der Fassung, `genre` als Liste, `users`, `rel` als `JJJJ`, `JJJJ-MM` oder `JJJJ-MM-TT`, `dev`,
`pub`, `desc`), `{}` ohne Treffer. Gesucht wird unter dem bestätigten ähnlichen Namen, dem Titel aus dem
Dateinamen und deinem Titel aus der Ordner-Liste, Fassungen der eigenen Region zuerst. Fehlt ein Feld in der
besten Fassung, gilt das der nächsten. Beta, Proto und Ähnliches zählen nicht.

## Ablage im Datenordner

- `data.json`: je Titel unter `live` die letzten Werte je Quelle (`meta`, `steam`, `gg`), jeweils
  mit Zeitpunkt `at`. Werte älter als 48 Stunden markiert die Oberfläche. Ein Meta-Angebot,
  dessen Ende vorbei ist, zeigt sie wieder zum Normalpreis.
- `history.json`: Preisverlauf, je Quelle und Kennung (Meta-ID, Steam-App-ID) eine
  Liste `[Tag, Preis]`; ein Eintrag nur, wenn sich der Preis ändert. Bei Meta kommt der
  Verlauf der QuestStoreDB-Titelseite dazu (je Tag gilt der eigene Wert). Daraus rechnet die
  Ansicht den Bestpreis der letzten 24 Monate je Shop (`prices.best_of`); gespeichert wird er
  nicht.
- `sync.json`: Beginn und Ende des letzten Laufs, Ergebnis je Quelle, Ruhezeiten (`rest`),
  Selbstprüfung (`warnings`), Protokoll.
- `settings.json`: Zeitplan, Konten und Schlüssel (gg.deals, Steam, IGDB).
- `retro_dat.json`: die Fassungen je System aus den Listen oben, mit Tag des Abrufs; wird neu
  geholt, wenn sie fehlt oder älter als sieben Tage ist.
- `retro_meta.json` (0.8.8): je System Tag des letzten Abrufs der Spielinfos, Fassung (`v`) und Zahl der Einträge.
- `collection.json`: die ganze Sammlung (je Spiel mit System, ohne Feld PC), je Spiel Merkmale aus Playnite;
  Spiele aus der Retro-Liste mit `src` „retro“, Schlüssel `retro:<system>:<name>`, dazu `files`, `regions`,
  `langs`, `lang_guess`, `flags`, gegebenenfalls `tid` und `serial` (3DS) und `gone` (Tag, seit dem es in der
  Liste fehlt) und `de` (siehe Retro-Fassungen), ab 0.8.8 `lr` (Spielinfos), `size` (Bytes aus der Ordnerwahl),
  `own` (deine Zeile der Ordner-Liste: `file`, `title`, `series`, `coll`, `genre`, `sub`, `folder`, `status`, `mb`)
  und `own_ok` (bestätigte Widersprüche), nie Pfade; ein neuer Import ohne Ordner-Liste für das System behält
  `own`, einer ohne Größen behält `size`; und
  `rev` (Steam-Rezensionen) und `steam` (Steam-Details). Ab 0.8.9 dazu `pcvr:<Titel>` mit `src` „pcvr“: deine
  VR-Titel am PC, die Playnite nicht kennt (`store` Steam, Epic … oder „Meta (Crossbuy)“, `id` die Steam-ID,
  `from_vr` der Titel), angelegt und bereinigt bei jedem Abgleich vor den Steam-Abrufen und nach einem
  Playnite-Import; ein Playnite-Import lässt sie stehen.
