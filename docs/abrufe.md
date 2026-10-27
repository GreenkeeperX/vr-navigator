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
  im Ergebnis.

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
| Rezensionen | `https://store.steampowered.com/appreviews/<App-ID>?json=1&language=all&purchase_type=all&num_per_page=0&filter=summary` | je Lauf höchstens 100 Steam-Spiele der Sammlung, zuerst die ohne Wert, dann die ältesten; jedes nach 30 Tagen neu | Zahl der Rezensionen und Anteil positiv |

Daraus: Wertung „Steam“ ab 50 Rezensionen, Bekanntheit und Geheimtipp-Wert. Hat ein Spiel mit
nur vermutetem Laden Rezensionen, gilt die Steam-ID als bestätigt. Abgelegt je Spiel unter
`rev` in `collection.json`; ein neuer Playnite-Export behält es.

## Steam-Details (Sammlung)

Nur mit einer Sammlung. Ohne Schlüssel, nach den Rezensionen.

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Details | `https://store.steampowered.com/api/appdetails?appids=<App-ID>&l=english` | je Lauf höchstens 80 Steam-Spiele der Sammlung, zuerst die ohne Wert, dann die ältesten; jedes nach 90 Tagen neu | Genres, Kategorien (Mehrspieler-Arten, VR), Erscheinungsjahr |

Steam-Genres werden auf die Genre-Gruppen der Sammlung abgebildet (Action, Strategie, Rollenspiel,
Casual, Rennen, Sport, Abenteuer, Simulation), Kategorien auf die Mehrspieler-Arten. Was Playnite
und Steam beide sagen, gilt als bestätigt; der Rest bleibt mit „≈“. Liefert Steam die App, ist
ein nur vermuteter Laden bestätigt. Abgelegt je Spiel unter `steam` in `collection.json`
(`ok: false`, wenn Steam die App nicht kennt); ein neuer Playnite-Export behält es.

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
| Fassungsliste | `https://raw.githubusercontent.com/libretro/libretro-database/master/metadat/no-intro/<System>.dat` (Discs: `…/metadat/redump/…`) | je System höchstens alle 7 Tage | alle bekannten Fassungen mit Region, Sprachen und bei GBA, GBC und DS dem Produktcode |
| Retool-Liste | `https://raw.githubusercontent.com/unexpectedpanda/retool-clonelists-metadata/main/clonelists/<System> (No-Intro).json` | mit der Fassungsliste | Gruppen von Fassungen eines Spiels mit verschiedenen Titeln |

Fassungen gehören zusammen, wenn sie denselben Titel haben, denselben Produktcode ohne den
Buchstaben für die Region („AMRE“ und „AMRD“) oder in derselben Retool-Gruppe stehen. Beta,
Proto, Demo und Ähnliches zählen nicht. Je Retro-Spiel steht danach unter `de`: Deutsch
vorhanden (`have`), deutsche Fassung fehlt (`missing`, mit der gesuchten Fassung `alt`, ob ihr
Deutsch nur aus der Region geschätzt ist, und worüber sie gefunden wurde), keine deutsche
Fassung bekannt (`none`) oder nicht in der Liste (`unknown`). Systeme ohne Liste (3DS) bleiben
ohne Angabe. „Verbindung testen“ fragt beide Listen eines Systems der Retro-Liste einmal ab.

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
- `settings.json`: Zeitplan und gg.deals-Schlüssel.
- `retro_dat.json`: die Fassungen je System aus den Listen oben, mit Tag des Abrufs; wird neu
  geholt, wenn sie fehlt oder älter als sieben Tage ist.
- `collection.json`: die ganze Sammlung (je Spiel mit System, ohne Feld PC), je Spiel Merkmale aus Playnite;
  Spiele aus der Retro-Liste mit `src` „retro“, Schlüssel `retro:<system>:<name>`, dazu `files`, `regions`,
  `langs`, `lang_guess`, `flags`, gegebenenfalls `tid` und `serial` (3DS) und `gone` (Tag, seit dem es in der
  Liste fehlt) und `de` (siehe Retro-Fassungen), nie Pfade; und
  `rev` (Steam-Rezensionen) und `steam` (Steam-Details).
