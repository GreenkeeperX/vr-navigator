# Entfernter Code

Hier steht, was aus dem Code entfernt wurde, warum, und wie geprüft wurde, dass nichts fehlt. Entfernt wird nur nach
Prüfung, nie auf Verdacht. Die alte Fassung steht in der Git-Geschichte.

## 0.10.29: vier Funktionen ohne Aufruf (Review vom 13.11.2026, Befund V8)

| Was | Seit | Wo verwendet | Warum nicht mehr nötig | Ersatz |
|---|---|---|---|---|
| `mods.game_url(dom)` (Link zur Spielseite bei Nexus Mods) | 0.8.17 | nirgends: kein Aufruf in `app/`, `app/static/`, `tests/` | Die Oberfläche baut die Links zu Nexus Mods (Spielseite und einzelne Mods) selbst (`app.js`, `nxLink`) | Links in `app.js` |
| `probes.uevr_info(text)` (Auswertung einer UEVR-Seite im Verbindungstest) | 0.8.17 | nirgends: keine Probe ruft sie auf | Die UEVR-Probe fiel in 0.7.2 weg (Browser-App ohne offene Schnittstelle, siehe Docstring von `probes`), die Auswertung blieb liegen; seit 0.10.28 liest `flat2vr.parse_uevr` den UEVR Hub | `flat2vr.parse_uevr` |
| `retro._same_title(a, b)` (zwei Titel gleich bis auf Artikel und Zeichen) | 0.8.17 | nirgends | Der Vergleich läuft über `titles.norm`, `_squash` und `article_front` direkt an den Stellen, die ihn brauchen | dieselben Hilfsfunktionen |
| `wiki.page_url(article)` und die Konstante `WIKI_PAGE` | 0.10.16 | nirgends; `WIKI_PAGE` nur in `page_url` | Den Link zur Wikipedia baut die Oberfläche aus `wp` (`app.js`, Einzelheiten eines Spiels) | Link in `app.js` |

Geprüft mit `grep -rn` über `app/`, `app/static/`, `tests/`, `docs/`, README und ROADMAP (kein Treffer außer der
Definition) und `git log -S` (eingeführt in 0.8.17 bzw. 0.10.16, nie aufgerufen). Die Tests (`python3 -m unittest
tests.test_all`) laufen danach unverändert durch. Keine Auswirkung auf Daten, Einstellungen oder Schnittstellen:
Keine der Funktionen schrieb etwas oder stand in einer Antwort des Servers.

Ebenfalls ohne Aufruf, aber noch nicht entfernt (nicht Teil des Befunds, erst nach Rückfrage): `mods.mod_url`. Die
Oberfläche baut diese Links selbst.
