# Meinungen-Datei

## Auftrag (ab 0.9.2)

Unter Einstellungen, „Zu erledigen“, stehen in „Meinung fehlt“ die VR-Wünsche ohne Recherche.
„Auftrag kopieren“ legt einen Text in die Zwischenablage: was zu recherchieren ist (Meta oder Steam,
Mehrspieler, Pflege, Crossbuy), die Titel mit Meta-ID und Steam-App-ID und der Aufbau der Antwort
unten; höchstens 25 Titel je Auftrag, die zuletzt gewünschten zuerst, damit ein Lauf gründlich bleibt. Nach dem
Einlesen kommen die nächsten. Den Text in eine Claude-Routine oder einen Chat mit Websuche einfügen (Entscheidung 28.10.2026: Recherche per Routine,
nicht über eine Schnittstelle im Tool); die Antwort als Datei oder Text einlesen. Das Tool selbst
ruft dafür nichts ab.

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
      "crossplay": true,
      "crossplay_grund": "Quest und PC treffen sich in derselben Lobby.",
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
| `crossbuy`, `crossbuy_grund` | `true`, `false` oder weglassen; gilt nur, wo du Crossbuy nicht selbst gesetzt hast, und steht dann mit „≈“ da. Belegt durch Store-Seite, VRDB oder einen Test, nie durch die eigene Tabelle |
| `crossplay`, `crossplay_grund` | `true`, `false` oder weglassen: spielen Quest und PC zusammen (gleiche Lobby), mit Grund |
| `komfort` | Bewegung, Sitzen oder Stehen, Spieldauer |
| `warnungen` | Bugs, Abbruch der Entwicklung, Bezahlinhalte |
| `quellen` | Links (nur http/https) mit Titel und Datum |

## Crossbuy und Crossplay

**Crossbuy** heißt: ein Kauf im Meta Store gilt für die Quest und für PC-VR über die Meta-App am
PC (Link, Air Link). Steam gehört nie dazu; wer bei Steam kauft, hat nur die Steam-Fassung.
**Crossplay** ist etwas anderes: Spieler auf Quest und PC spielen zusammen, egal wo gekauft.

Eine Crossbuy-Begründung, die Steam, Crossplay, „Tabelle“ oder „Zuordnung“ nennt, ist kein Beleg:
der Import verwirft den Wert, behält die übrigen Felder und nennt die Zahl in der Vorschau. Die
Rangfolge bleibt: von Hand vor VRDB vor Tabelle vor Recherche.

Leere Felder fallen weg, Texte werden gekürzt. Eine neue Datei ersetzt die Meinungen eines
Titels ganz. In der Oberfläche stehen sie unter dem Titel als zugeklappte Zeile
„Recherche, Datum: PC-Fassung besser · Mehrspieler ruhig“.
