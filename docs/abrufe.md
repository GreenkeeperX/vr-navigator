# Abrufe: was woher, wie oft, wohin

Der Abgleich liest erst deine Konten (Steam, gg.deals-Wunschliste, Sharenite) und holt dann Preise nur für Wunschtitel, die du noch nirgends besitzt. Er läuft nach
Zeitplan (Standard alle 6 Stunden, einstellbar von 2 bis 48) und auf Knopfdruck unter
**Einstellungen**, Abgleich, oder oben über „Aktualisieren“. Zwei Minuten nach dem Start des Containers läuft ein
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
| gg.deals-Wunschliste | der geteilte Link, `?page=N` | jeder Lauf, höchstens 10 Seiten | Links auf `/game/<name>/` mit Namen |
| Steam-Suche für unbekannte gg.deals-Namen | `store.steampowered.com/api/storesearch/` | 15 je Lauf, je Name höchstens alle 7 Tage | App-ID bei genau gleichem Namen |
| Sharenite | `sharenite.link/profiles/<Profil>/games?sort=name_asc`, dann mit `tag_ids[]` der VR-Schlagwörter | höchstens alle 20 Stunden (von Hand immer) | Name, Laden und Schlagwörter je Spiel; ohne VR-Filter die ganze Liste (100 je Seite, höchstens 40 Seiten) |

Ergebnis der VR-Prüfung: `data["steam_apps"]` (`{App-ID: {name, vr, at}}`), versuchte
gg.deals-Namen: `data["gg_tried"]`. Wunschlisten setzen je Titel `wish_src` (`{Quelle: Zeit}`,
Quellen `meta`, `steam`, `gg`, `hand`); von Hand genommene Quellen stehen in `wish_off`.
Gekaufte Spiele aus Steam tragen `owned.pc.src = "steam"`, aus Sharenite `"sharenite"` mit dem
Laden als `label`.

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

## Ablage im Datenordner

- `data.json`: je Titel unter `live` die letzten Werte je Quelle (`meta`, `steam`, `gg`), jeweils
  mit Zeitpunkt `at`. Werte älter als 48 Stunden markiert die Oberfläche. Ein Meta-Angebot,
  dessen Ende vorbei ist, zeigt sie wieder zum Normalpreis.
- `history.json`: eigener Preisverlauf, je Quelle und Kennung (Meta-ID, Steam-App-ID) eine
  Liste `[Tag, Preis]`; ein Eintrag nur, wenn sich der Preis ändert.
- `sync.json`: Beginn und Ende des letzten Laufs, Ergebnis je Quelle, Ruhezeiten (`rest`),
  Selbstprüfung (`warnings`), Protokoll.
- `settings.json`: Zeitplan und gg.deals-Schlüssel.
