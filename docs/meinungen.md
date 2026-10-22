# Meinungen-Datei

Recherchierte Meinungen (Reddit, Foren, Tests) kommen als JSON-Datei ins Tool, über
Einstellungen → Einlesen → „Datei oder Text“. Das Tool erkennt sie an `"app":
"vr-navigator-meinungen"`, zeigt erst eine Vorschau und ordnet nur Titel zu, die es schon
kennt (Meta-ID, Steam-App-ID oder Name). Gespeichert wird nur im Datenordner, nie im Repo.

```json
{
  "app": "vr-navigator-meinungen",
  "stand": "2026-10-22",
  "titles": [
    {
      "name": "Orbit Golf",
      "meta_id": "1234567890123456",
      "steam_appid": "3000040",
      "fazit": "Ruhiges Minigolf mit guter Physik, wenig Inhalt für den Vollpreis.",
      "fassung": "pc",
      "fassung_grund": "Am PC schärfere Texturen und Mod-Bahnen, sonst gleich.",
      "mehrspieler": "ruhig",
      "mehrspieler_stand": "Abends wenige offene Runden, Freunde-Lobbys gehen gut.",
      "pflege": "Letztes größeres Update im Frühjahr, Entwickler antwortet im Forum.",
      "crossbuy": false,
      "crossbuy_grund": "Store-Seite nennt kein Crossbuy.",
      "komfort": "Stehen oder Sitzen, Teleport, Runden um 20 Minuten.",
      "warnungen": "",
      "quellen": [{"url": "https://www.reddit.com/r/OculusQuest/", "titel": "Reddit-Thread", "datum": "2026-09-30"}]
    }
  ]
}
```

| Feld | Inhalt |
|---|---|
| `fazit` | zwei bis drei Sätze, wie das Spiel ankommt |
| `fassung`, `fassung_grund` | `quest`, `pc` oder `gleich`, mit Grund (Grafik, Inhalte, Updates) |
| `mehrspieler`, `mehrspieler_stand` | `lebendig`, `ruhig`, `tot` oder `keiner`, mit Stand |
| `pflege` | letzte größere Updates, Entwickler aktiv |
| `crossbuy`, `crossbuy_grund` | `true`, `false` oder weglassen; gilt nur, wo du Crossbuy nicht selbst gesetzt hast, und steht dann mit „≈“ da |
| `komfort` | Bewegung, Sitzen oder Stehen, Spieldauer |
| `warnungen` | Bugs, Abbruch der Entwicklung, Bezahlinhalte |
| `quellen` | Links (nur http/https) mit Titel und Datum |

Leere Felder fallen weg, Texte werden gekürzt. Eine neue Datei ersetzt die Meinungen eines
Titels ganz. In der Oberfläche stehen sie unter dem Titel als zugeklappte Zeile
„Recherche, Datum: PC-Fassung besser · Mehrspieler ruhig“.
