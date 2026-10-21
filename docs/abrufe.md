# Abrufe: was woher, wie oft, wohin

Der Abgleich holt Preise nur für Wunschtitel, die du noch nirgends besitzt. Er läuft nach
Zeitplan (Standard alle 6 Stunden, einstellbar von 2 bis 48) und auf Knopfdruck unter
**Abrufe**. Der erste Blick auf den Zeitplan fällt zwei Minuten nach dem Start des Containers.
Mit `AUTO_SYNC=0` läuft gar kein Zeitplan.

Alle Abrufe gehen über `sources.fetch`: ehrliche Kennung `vr-navigator/<Version>`, nur
öffentliche Ziele, Grenzen für Zeit und Größe. Zwischen zwei Abrufen derselben Quelle liegen
2 Sekunden. Antwortet eine Quelle mit 403 oder 429, endet sie für diesen Lauf; nach 5 anderen
Fehlern ebenso. Die übrigen Quellen laufen weiter.

## QuestStoreDB (Meta-Preise)

| Abruf | Adresse | Wie oft | Liefert |
|---|---|---|---|
| Angebotsliste | `/on_sale/?sort=-sale_start_time&page=N` | jeder Lauf, alle Seiten (höchstens 15) | Preis, Normalpreis, Rabatt, Ende, Gutschein ja/nein |
| Titelseite | `/game/<name>-<Meta-ID>/` | je Titel höchstens alle 20 Stunden, 60 je Lauf, die älteste zuerst | Preis, Normalpreis, Ende, Tiefstpreis samt Tag, Bewertung, App-Version |
| Suche | `/all_apps/?release_status=all&q=<Name>` | nur ohne bekannten Pfad, 30 je Lauf | Pfad und Meta-ID |

Das Tool schickt das Cookie `currency=EUR`, damit Listen und Preisverlauf in Euro kommen. Die
Titelseite trägt die Preise als strukturierte Daten (JSON-LD, ein Angebot je Währung) und den
Preisverlauf als JSON für das Diagramm; daraus stammt der Tiefstpreis.

Die Suche gilt als Treffer, wenn die Meta-ID gleich ist oder genau ein Ergebnis denselben
Namen trägt. Ohne Treffer sucht das Tool sieben Tage nicht erneut nach dem Titel; eine von Hand
eingetragene Meta-ID hebt die Pause auf.

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
der Schlüssel angenommen wird.

## Ablage im Datenordner

- `data.json`: je Titel unter `live` die letzten Werte je Quelle (`meta`, `steam`, `gg`), jeweils
  mit Zeitpunkt `at`. Werte älter als 48 Stunden markiert die Oberfläche. Ein Meta-Angebot,
  dessen Ende vorbei ist, zeigt sie wieder zum Normalpreis.
- `history.json`: eigener Preisverlauf, je Quelle und Kennung (Meta-ID, Steam-App-ID) eine
  Liste `[Tag, Preis]`; ein Eintrag nur, wenn sich der Preis ändert.
- `sync.json`: Beginn und Ende des letzten Laufs, Ergebnis je Quelle, Protokoll.
- `settings.json`: Zeitplan und gg.deals-Schlüssel.
