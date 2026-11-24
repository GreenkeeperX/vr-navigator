# Leistung der Sammlung (V-3, 0.11.1)

Gemessen mit einer erfundenen Sammlung von 8000 Spielen (`app/leistung.py`, `synthetic`): dieselben Felder je Quelle
wie in der echten Sammlung; Anteile der Quellen, Namen, Kennungen und Texte erfunden. Gemessen über HTTP, wie die
Oberfläche fragt (mit gzip), in einem Cloud-Container, nicht auf dem Server zu Hause; dort ist alles langsamer, das
Verhältnis bleibt. Angegeben ist der Bereich aus zwei Läufen je Version.

| | 0.10.28 | 0.11.0 | 0.11.1 |
|---|---|---|---|
| `collection.json` auf der Platte | 14,8 MB | 14,8 MB | 14,8 MB |
| `/api/collection`, Inhalt | 9,9 MB | 9,9 MB | 7,0 MB |
| `/api/collection`, übertragen (gzip) | 1,38 MB | 1,38 MB | 0,63 MB |
| `/api/collection` kalt (Server rechnet) | 0,69–0,74 s | 0,68–0,76 s | 0,66–0,68 s |
| `/api/collection` warm | 0,03–0,04 s | 0,03 s | 0,02 s |
| `/api/collection` unverändert, Browser fragt nach | 1,38 MB neu | 1,38 MB neu | 304, 0 Byte, 1 ms |
| `/api/state` (Inhalt, übertragen) | 0,54 MB, 43 KB | gleich | gleich, ab 0.11.1 auch 304 |
| `/api/state` kalt | 0,39–0,47 s | 0,35–0,37 s | 0,35–0,36 s |
| eine Entscheidung („DE fehlt“ ignorieren), Antwort | 1,30–1,37 s | 0,81–0,89 s | 0,17–0,18 s |
| Antwort der Entscheidung, übertragen | 1400 KB | 1400 KB | 18 KB |
| danach `/api/collection` | 0,76–0,80 s | 0,80–0,82 s | 0,21–0,22 s |
| danach `/api/state` | 0,38–0,45 s | 0,40–0,42 s | 0,39 s |
| Rechenzeit des ganzen Laufs | 13,1–14,2 s | 11,1–11,7 s | 4,9–5,0 s |
| Speicher (Spitze des Prozesses) | 248 MB | 251 MB | 211–212 MB |

## Was sich geändert hat

- **Zeilen einzeln** (`collection.row`, `collection.rows`): Eine Entscheidung rechnet nur die Zeilen der betroffenen
  Spiele neu und setzt sie in die zwischengespeicherte Sammlung (`server.colview_patch`), statt alles neu zu bauen.
  Das gilt nur, wenn der Zwischenspeicher genau zum Stand der Dateien beim Lesen passt; sonst rechnet der nächste
  Abruf alles neu, wie bisher. Ein Test vergleicht die gepatchte Sammlung mit einer ganz neu gerechneten.
- **Antwort einer Entscheidung**: nur die geänderten Zeilen (`rows`), die Oberfläche tauscht sie aus. Vorher kam die
  ganze Sammlung zurück.
- **Ohne Beschreibung**: `/api/collection` lässt `desc` weg (ein Drittel der Antwort) und sagt mit `hd`, dass es eine
  gibt. Beim Aufklappen holt die Oberfläche sie über `POST /api/details`, gesammelt für alle aufgeklappten Spiele; die
  Liste herunterladen wartet darauf. Suche und Filter brauchen die Beschreibung nicht.
- **ETag und 304** für `/api/collection` und `/api/state`, dazu HTTP/1.1: Ohne HTTP/1.1 fragt Chromium mit dem ETag
  nicht nach. Eine Verbindung ohne weitere Anfrage endet nach 60 Sekunden; eine Anfrage, deren Inhalt der Server nicht
  liest (zu groß, falscher Typ), beendet ihre Verbindung.
- **Stile und Skript mit Version** in der Adresse (`app.js?v=…`): der Browser behält sie ein Jahr, ein Update bringt
  eine neue Adresse. `index.html` fragt jedes Mal nach.

## Was bleibt

- Nach einem Abgleich oder Import rechnet der Server die Sammlung einmal ganz (0,6–0,8 s, davon das Lesen von
  `collection.json` 0,1–0,3 s); das tut er im Hintergrund, bevor jemand fragt.
- `/api/state` rechnet nach einer Entscheidung neu (0,4 s, davon die Retro-Listen gut die Hälfte), ebenfalls im
  Hintergrund; die Antwort der Entscheidung bringt die geänderte Liste schon mit.
- **SQLite ist nicht nötig**: Eine Entscheidung braucht 0,17 s, die große Datei wird dabei nicht geschrieben, und die
  verbleibenden Rechnungen laufen im Hintergrund. Neu prüfen, wenn die Sammlung deutlich wächst oder der
  Leistungstest der Statuskarte (V-5) auf dem Server Werte über einer Sekunde für eine Entscheidung zeigt.

## Selbst messen

Ab 0.11.1 misst `leistung.measure(n)` dasselbe ohne HTTP in einem temporären Datenordner. Es schaltet den Datenordner
für den ganzen Prozess um; im laufenden Server nur in einem eigenen Prozess (so wird es die Statuskarte aufrufen).
