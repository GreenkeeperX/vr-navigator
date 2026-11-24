# Ansichten

Aus der README ausgelagert (0.11.2), unverändert. Kurzfassung in der [README](../README.md).

## Ansichten

- **Jetzt:** Wunschtitel, die gerade bei Meta oder Steam reduziert sind und dabei nah am
  Bestpreis beider Läden liegen, mit den Grenzen des eShopKompass: „kaufen“ bis 2 % oder 0,50 €
  darüber (unter 2 € Bestpreis nur die 2 %), „gut“ bis 15 % oder 2 € darüber. Die übrigen
  Angebote stehen zugeklappt darunter („Reduziert, aber noch weit über dem Bestpreis“). Sortiert
  nach Nähe zum Bestpreis, nach Rabatt oder Wertung, mit Ende des Angebots. Jeder Titel als Zeile wie in der
  Wunschliste (bis 0.8.21 als Karte). Ab 0.8.11 darunter auch die PC-Wünsche, die höchstens 5 % über dem bisherigen Tief bei gg.deals
  liegen, als Liste wie unter Wunschliste, PC; die Reiter „Alle, PC, VR“ (ab 0.8.17, vorher ein Schalter, jetzt an
  derselben Stelle wie in Wunschliste und Sammlung) zeigen beide oder nur eine Seite. Ab 0.8.27 zeigt „Alle“
  PC- und VR-Wünsche gemischt in einer Tabelle (Spiel, Art PC oder VR, Wo, Preis, zum Tief, Wertung,
  Rezensionen, Aktiv; „zum Tief“ ist bei VR der Abstand zum Bestpreis, bei PC zum Tief bei gg.deals), sortiert wie gewählt; die weit über dem Bestpreis liegenden VR-Angebote stehen zugeklappt darunter.
  Ab 0.9.0 hat der Reiter PC ein Menü „Laden“ (mit IsThereAnyDeal-Schlüssel): Es nennt je offiziellem Laden, wie viele
  PC-Wünsche dort gerade höchstens 5 % über dem Tief der Händler liegen, und zeigt nach Wahl genau diese mit dem Preis
  dort. So lassen sich mehrere Spiele in einem Laden kaufen. In den Einzelheiten eines PC-Wunschs steht die Zeile
  „Läden“: bis zu sechs Läden nach Preis, grün nah am Tief, Normalpreis, Tief dort und Angebotsende im Tooltip.
  Ab 0.9.4 heißt es überall „Tief“ (bei VR das Tief beider Läden aus dem eigenen Verlauf, bei PC das Tief bei
  gg.deals); die Spalte heißt „überm Tief“, die Zelle „am Tief“. Die Gruppe „weit über dem Tief“ fällt weg. Spalten in
  „Alle“: Spiel, max. Spieler, Art, Preis, überm Tief, Wo, Wertung, Rezensionen, Genre, Aktiv. „Wo“ ist eine dünn
  umrandete Marke in der Farbe des Ladens (Meta, Steam oder Händler, Keyshop); ein Klick öffnet den Preisverlauf.
  Der Rabatt („−40 %“) gilt dem gezeigten Preis gegenüber dem Normalpreis dieses Ladens und ist nur Information.
  VR-Wünsche haben ab 0.9.4 Genre und Spielerzahl aus Steam und IGDB (Quelle „VR-Titel, Spielinfos“).
- **Preisverlauf** (ab 0.9.1, wie im eShopKompass): „Preisverlauf“ in den Einzelheiten eines Wunschs öffnet die Kurve
  je Laden der letzten 18 Monate, bei VR Meta, Steam und gg.deals, bei PC gg.deals und jeder Laden von IsThereAnyDeal
  (beim ersten Abgleich mit Schlüssel rückwirkend, danach führt das Tool ihn fort). Gestrichelt das Tief und
  der typische Angebotspreis. Darunter je Laden: Preis jetzt, Normalpreis (der am längsten galt), tiefster Preis mit
  Tag, Zahl der Angebote (jede Strecke mindestens 3 % unter normal), ihre übliche Dauer, Anteil der Zeit im Angebot,
  typischer Angebotspreis (Median der Tiefstwerte je Angebot, ab zwei; war das letzte tiefer, dieses) und das
  letzte Angebot. Ein Klick auf einen Laden blendet ihn aus.
- **Spaltenreihenfolge** (ab 0.8.19, Entscheidung 28.10.2026): links, wonach du entscheidest, rechts das Nachschlagen.
  Sammlung: Spiel, (Sprache bei Retro), Wertung, Genre, Spielzeit, Mehrspieler, Spieler, Jahr, Rezensionen, Launcher;
  Reiter VR: Spiel, Besitz, Meta, Steam, Spieler, Update, Crossbuy, Recherche.
  Ab 0.8.23 (Entscheidung 28.10.2026) gilt in allen Tabellen eine Reihenfolge: Spiel, Wertung, Rezensionen, Genre,
  Spielzeit, max. Spieler, Aktiv, Sprache, Launcher oder System, Jahr ganz rechts. Wunschliste PC: Preis und zum Tief
  vorn; Wunschliste VR: Wo, Meta, Steam und zum Bestpreis vorn, dahinter Wertung, Rezensionen, Aktiv, Update; Reiter VR:
  Wertung, Rezensionen, Aktiv, Update, Crossbuy, Besitz, Recherche; Switch: Wertung, Genre, Spielzeit, max. Spieler, Jahr.
  Mehrspieler ist keine Spalte mehr: die Arten stehen im Tooltip von „max. Spieler“ (ohne Zahl ab 0.9.5 „–“, vorher „2+“, laut Steam ohne
  Mehrspieler „1“), in den Einzelheiten und im Filter Mehrspieler (auch in der Wunschliste PC). „Aktiv“ heißt überall
  die Zahl der Steam-Spieler gerade eben, für PC-Spiele (Wunschliste, Sammlung) wöchentlich gemessen. Der Reiter VR
  zeigt die Wertung der Fassung, die du besitzt (bei beiden die bessere); ist die andere mindestens 8 Punkte besser,
  steht sie klein daneben („M 92“). Gleich benannte Spalten sind überall gleich breit.
  Ab 0.9.4 (Entscheidung 28.10.2026) steht „max. Spieler“ überall als erste Spalte nach „Spiel“. Wunschliste VR:
  Spiel, max. Spieler, Meta, Steam, überm Tief, Wo, Wertung, Rezensionen, Genre, Aktiv, Update; Wunschliste PC:
  Spiel, max. Spieler, Preis, überm Tief, Wo, Wertung, Rezensionen, Genre, Spielzeit, Aktiv, Jahr. Der Knopf
  „Preisverlauf“ steht in den Einzelheiten unter dem Preis.
- **Wunschliste** (0.8.2, vorher „VR-Wunschliste“) mit den Unterreitern PC und VR (ab 0.8.7 PC zuerst, wie in der
  Sammlung). **PC** spiegelt deine gg.deals-Wunschliste (gepflegt wird sie dort), ab 0.8.7 mit Paketen und DLC
  (Marke „Paket“, „DLC“; Preis über den Link zur Seite bei gg.deals, die API kennt nur Steam-Apps) und ohne die
  VR-Spiele, die unter VR stehen. Nennt nur der Name VR („… VR“), steht ein violettes „VR“ als Hinweis. Je Spiel der günstigste Preis jetzt (Händler
  oder Keyshop, als Link zu gg.deals) und wie weit er über dem bisherigen Tief liegt: grün „am Tief“ (bis 2 %),
  sonst rot der Betrag. Ab 0.8.17 wie im eShopKompass: Händler, Keyshop und das Tief stehen im Tooltip des
  Preises und in den Einzelheiten statt in eigenen Spalten; dazu die Spalten Spieler und Jahr. Reihenfolge:
  Spiel, Preis, zum Tief, Wertung, Genre, Spielzeit, Mehrspieler (mit Spielerzahl, ab 0.8.19), Jahr. „Nah am Tief“ (Jetzt) heißt höchstens 5 % darüber.
  Ab 0.8.18 merkt sich das Tool den Preisverlauf je Spiel; liegt der Preis jetzt deutlich unter dem üblichen (mindestens
  25 % und 3 € unter dem Median der letzten 90 Tage), steht grün „Preissturz“ am Namen. Das gilt für Händler und
  Keyshop gleich, denn Keyshops sind oft günstiger als ein Steam-Sale. Dazu Trend und Pflege wie unten. Die Steam-ID kommt aus dem, was das Tool kennt, sonst aus der
  Steam-Suche nach genau gleichem Namen (30 je Abgleich); ohne gg.deals-Schlüssel gibt es keine Preise.
  Ab 0.8.24 60 Suchen je Abgleich, gesucht ohne Emoji und „[Studio]“ vorn, sonst mit der Grundform des Namens (vor
  „ / “, ohne „Definitive Edition“ und Ähnliches). Passt ein Treffer nur in der Grundform, übernimmt das Tool die ID, zeigt
  „Steam-ID ungeprüft“ und fragt unter Einstellungen, Zu erledigen, „PC-Wunsch: Steam-ID“ nach („passt“, „falsch“). Mehrere
  ähnliche Treffer stehen dort zur Wahl („dieses“, „keins“); Verworfenes schlägt das Tool nicht wieder vor.
  Ab 0.8.11 mit Spielinfos wie in der Sammlung: Spalten Wertung (Steam-Rezensionen ab 50, sonst IGDB grau und
  kursiv), Spielzeit (IGDB) und Genre (Steam und IGDB, violett nur eine Quelle); ein Klick auf den Namen zeigt
  Mehrspieler, Spieler, Erscheinen, Entwickler, Rezensionen, das Tief je Art, die Beschreibung und die Links zu
  gg.deals und Steam. Sortieren auch nach Wertung und Spielzeit. Die Infos holt der Abgleich über die Steam-ID,
  60 Spiele je Lauf (Pakete und DLC bekommen keine).
  „schon in der Sammlung“ markiert Spiele, die du schon besitzt. **VR**: Was du bei Meta oder am PC schon besitzt, steht unten in der zugeklappten
  Gruppe „Schon im Besitz“, etwa wenn du ein PC-Spiel zusätzlich für die Quest willst.
  „nicht mehr wünschen“ (in der Klappe unter der Karte) nimmt einen Titel von der Liste (mit Rückgängig);
  „+ Titel“ in der Werkzeugzeile trägt einen von Hand ein.
  Ab 0.8.22 (Entscheidung 28.10.2026) stehen die VR-Wünsche als Tabelle wie unter PC: Spiel (mit Crossbuy,
  SimRacing und kurz „keine Liste“ oder „fehlt: Meta“), Wo (Urteil „wo kaufen“), Meta, Steam (Preis mit Rabatt,
  als Link zum Laden), zum Bestpreis (grün „am Bestpreis“, sonst rot der Abstand), Wertung mit Trend, Rezensionen, Aktiv (bis 0.8.22 „Spieler“),
  Update. Ab 0.8.25 steht grün „Preissturz“ am Namen wie bei den PC-Wünschen: der Preis bei Meta oder Steam liegt
  mindestens 25 % und 3 € unter dem Median der letzten 90 Tage aus dem eigenen Preisverlauf (mit dem von QuestStoreDB).
  Ein Klick auf den Namen klappt darunter die bisherige Karte als Einzelheiten auf. Jetzt zeigt die
  VR-Angebote in derselben Tabelle.
  Je Titel eine Karte mit festem Aufbau (ab 0.8.22 die Einzelheiten einer Zeile):
  - **Kopf:** Name, „wo kaufen“, Crossbuy-Marke mit Herkunft (siehe unten), Besitz, Bundle, „Steam-ID ungeprüft“.
  - **Wo kaufen** (ab 0.8.15): für jeden Wunschtitel, den du noch nicht hast, der Laden, für den mehr
    spricht, und dahinter das Preisurteil dort („Meta kaufen“, „Steam warten“, „Laden egal, gut“). Gezählt
    wird nur Gemessenes: nur ein Laden führt ihn (entscheidet), Crossbuy (2 für Meta), ein großer
    Preisabstand von mindestens 40 % und 8 € (2), je 1 für Mehrspieler mit weniger als 20 Spielern auf
    Steam (Spitze; spricht für Meta), 8 Punkte bessere Wertung, eine um ein Jahr jüngere Pflege (letztes
    Steam-Update gegen die Meta-Version), spürbar günstiger (Steam 20 % und 3 €, Meta ab 1 €). Die
    Recherche („Quest-“ oder „PC-Fassung besser“) zählt halb und steht violett. Ab 0.8.26 zählt auch der Trend
    halb, wenn es beide Läden gibt: fällt die Steam-Wertung der letzten 30 Tage deutlich, für Meta, steigt sie, für Steam. Wer mindestens
    einen Punkt vorn liegt, gewinnt, sonst ist der Laden egal. Die Gründe stehen in der Zeile „Wo“, die
    für den anderen Laden grau.
  - **Preise:** zwei feste Felder, Meta links, Steam rechts; fehlt ein Laden, bleibt sein Feld grau
    mit „kein Preis“. Je Feld Preis, Rabatt und Ende, darunter der Abstand zum **Bestpreis**
    beider Läden, dem niedrigsten Preis von Meta oder Steam der letzten 18 Monate: rot „+3,50 € über
    Bestpreis“ mit Betrag, Laden und Prozent (jeder Aufpreis rot), gold „★ Bestpreis“
    (bis 2 % darüber). Neben dem Laden steht das Urteil wie im eShopKompass: grün „kaufen“ (bis
    2 % oder 0,50 € über dem Bestpreis beider Läden), grün umrandet „gut“ (bis 15 % oder 2 €). Kommt der Bestpreis aus dem anderen Laden, steht klein darunter der
    Tiefstpreis des Ladens selbst („Steam-Tief 12 €“ oder „jetzt“); so sieht Steam nicht golden
    aus, wenn Meta einmal günstiger war. Dazu „übliches Angebot“ (so tief wie in mindestens zwei
    getrennten Angeboten). Für Meta reicht der Verlauf von QuestStoreDB Jahre
    zurück, für Steam zählt der eigene Verlauf; ohne jede Preisänderung steht „Bestpreis noch
    offen“. Ist der eigene Verlauf noch zu kurz, gilt das Allzeit-Tief einer anderen Quelle, violett:
    bei Meta von QuestStoreDB, bei Steam das niedrigste Angebot laut gg.deals, Händler und
    Keyshops. Ist ein Angebot bei gg.deals günstiger als Steam, steht es im Steam-Feld. Der günstigere Laden
    (gegen das günstigste PC-Angebot, Keyshops eingeschlossen) bekommt ab 1 € Unterschied einen grünen
    Rahmen und den Betrag („5 € günstiger“). Der Abrufzeitpunkt steht nur da, wenn ein Preis älter
    als zwei Tage ist.
  - **Fakten** in einem festen Raster (Name links, Wert rechts, in jeder Karte gleich): Wertung beider Läden auf einer Skala (Steam: Anteil positiver
    Rezensionen ab 50, darunter nur die Zahl; Meta: Anteil der 4- und 5-Sterne-Bewertungen laut
    VRDB, sonst Sterne × 20 über QuestStoreDB violett; ab 5 Punkten Abstand der bessere grün mit
    „Meta +8“), Steam-Spieler gerade jetzt mit der Spitze aus den eigenen Messungen der letzten
    30 Tage, das letzte Steam-Update laut Entwickler-Meldungen und die Meta-Version mit dem Tag,
    an dem das Tool sie zuerst sah.
    Ab 0.8.18 **Trend und Pflege**: Sind die Steam-Rezensionen der letzten 30 Tage mindestens 8 Punkte besser oder
    schlechter als insgesamt, steht neben der Steam-Wertung ein grüner ↗ oder roter ↘ Pfeil (Zahlen im Tooltip, in den
    Fakten „Trend: fallend (60 % gegen 92 %)“). Über ein Jahr ohne Update heißt „ruht“ (grau). Dasselbe gilt in der
    Wunschliste PC und im Reiter VR der Sammlung (Spalten Steam und Update). Ab 0.8.21 frischt der Abgleich den Trend
    wöchentlich auf, je Lauf bis zu 60 Titel und 60 PC-Wünsche. Woher die Zahlen kommen, steht in
    `docs/abrufe.md` (Trend und Pflege).
  - **Recherche** violett gestrichelt, weil sie nicht vom Tool gemessen ist; die Notiz.
  - **Klappe** (zugeklappt), ihre Zeile nennt den Inhalt, etwa „Bestpreise · gg.deals · Links ·
    bearbeiten“: Bestpreise je Laden mit Datum und Quelle, gg.deals (Händler, Keyshop,
    Allzeit-Tief), die Werte deiner Tabelle, Links (Meta, VRDB, QuestStoreDB, Steam, fertige
    Suchen auf Reddit und Google nach „Quest vs Steam“), „bearbeiten“.

  Ohne Abruf gelten die Werte der Tabelle, gekennzeichnet mit „Tabelle“ und Datum (Differenz
  dort: Meta-Tief minus gg.deals). Am Desktop stehen Preise und Fakten nebeneinander.
  Werkzeugzeile in Jetzt und Wunschliste: Suche, „Sortieren“ (Name, „Nah am
  Bestpreis“, Rabatt, Wertung, „Neu“), das Menü „Filter“ mit Häkchen (Crossbuy, Im Angebot,
  Am Bestpreis, Gut bewertet: die bessere Wertung ab 85) und „?“ für die Legende der Farben und
  Zeichen. Gewählte Filter stehen darunter als Marken mit ×.
- **Crossbuy und Herkunft:** Crossbuy kommt von Hand, von VRDB (Angabe im Meta Store), aus deiner
  Tabelle oder aus der Recherche, in dieser Rangfolge. Die Marke zeigt die Herkunft: ohne
  Zeichen von Hand oder VRDB, „Crossbuy · Tabelle“ aus der Tabelle, violettes „Crossbuy“ aus der
  Recherche; „ohne Crossbuy“ ist grau. Widersprechen sich Quellen, gilt die stärkere und die
  andere steht violett daneben („Tabelle: nein“). Unter „bearbeiten“ heißt „automatisch“: keine
  eigene Angabe. Titel aus der Zeit vor 0.4.8 ohne gespeicherte Herkunft gelten als „Tabelle“,
  wenn eine Tabellenzeile da ist, sonst als von Hand.
- **Sammlung** (bis 0.5.5 „Entdecken“): die ganze Sammlung aus dem Playnite-Export, der Retro-Liste und
  (ab 0.7.3, mit `ESHOP_URL`) der Switch-Sammlung des eShopKompass, mit einem Reiter je
  System („Alle“ vorn, nur bei mehr als einem System aus Playnite und Retro-Liste, dann PC, VR
  und die Konsolen mit Zahl). Beim Öffnen gilt PC; der gewählte Reiter ist in der Farbe seiner
  Familie unterstrichen (Nintendo rot, PlayStation blau, PC grün, VR türkis).
  Aufbau wie „Spiele“ im eShopKompass (0.6.0): je Spiel eine Zeile mit Spalten, die nur
  erscheinen, wenn ein Spiel im Reiter dafür einen Wert hat (Spieler, Mehrspieler, Wertung,
  Rezensionen, Sprache, Genre, Jahr, Launcher; die Spalte Launcher zeigt am PC Steam, Epic, GOG …,
  bei Konsolen unter „Alle“ das System). Genres stehen einzeilig, seltene zuerst (je seltener in
  der Sammlung, desto weiter vorn, bei Gleichstand nach dem Alphabet, „Sonstiges“ zuletzt); was
  nicht passt, zählt „+n weitere“ (Tooltip mit den Namen), die Einzelheiten zeigen alle. Ein Klick auf einen
  Spaltenkopf sortiert (Wertungen und Zahlen zuerst absteigend), der zweite andersherum, der dritte
  zurück zur gewählten Sortierung. Die Wertung ist von Rot über Gelb nach Grün eingefärbt (50 bis
  95 %), Genres stehen als farbige Blasen (verwandte Genres in ähnlichem Farbton, violett bleibt
  frei). Ein Klick auf den Namen klappt die Einzelheiten auf: Die Genres der Zeile laufen nach
  unten weiter (Name und Spalten bleiben dabei, wo sie sind), darunter steht nur, was keine Spalte
  zeigt: bei Steam-Spielen die Wertung als Zahl wie im eShopKompass („Steam 97 % · Metacritic 96“,
  Steams Worte und die Zahl der Rezensionen im Tooltip; 0.7.2), das genaue Erscheinen (Entwickler und Verlag im Tooltip), ab 0.9.5 „Spieler“ je Art mit
  der höchsten Zahl („Online bis 8 · Koop online bis 4 · Lokal bis 4“, aus IGDB und PCGamingWiki; vorher
  „Mehrspieler“), bei Retro-Spielen gesuchte Fassung und Dateien. Sprachen stehen ab 0.9.5 nur, wenn Deutsch fehlt,
  klein unten als „ohne Deutsch“ (die Sprachen im Tooltip), wie in den Nintendo-Reitern; unter Mein Stand die Kurzbeschreibung aus dem Steam-Store auf Deutsch (0.7.1; vier
  Zeilen, ein Klick zeigt alles). „alle aufklappen“ öffnet alle Spiele der Liste, solange es
  höchstens 150 sind (sonst grau, der Tooltip sagt, wie viele es sind; 0.7.4). Die Reiter oben
  zeigen Alle, PC, VR, PlayStation, Nintendo und Weitere (alle übrigen Systeme); ein Klick
  auf eine Familie zeigt alle ihre Spiele und klappt rechts daneben ihre Konsolen aus (PS1 bis PS5,
  Switch 2, 3DS …; 0.7.4). Switch und Switch 2 stehen in einem Reiter „Switch 2“, der Filter
  „System“ trennt sie wieder; die Switch-Spiele zeigen Spalten, Marken und Einzelheiten wie „Spiele“
  im eShopKompass (ab eShopKompass 1.7.17), „im eShopKompass“ öffnet das Spiel dort aufgeklappt
  (0.7.5), mit dessen Filtern Spielweise, Spielzeit und USK (0.7.6). Alle übrigen Reiter füllt seit
  0.8.0 IGDB mit fester Rangfolge je Feld: Wertung am PC Steam (ab 50 Rezensionen), sonst IGDB grau
  und kursiv; auf Konsolen und Retro IGDB-Kritiken, sonst die IGDB-Gesamtwertung grau und kursiv.
  Spielzeit von IGDB (normal, sonst eilig; komplett im Tooltip), Spieler von IGDB, sonst Playnite
  (violett). Genres und Mehrspieler aus allen Quellen; was nur eine nennt, während eine andere etwas
  anderes sagt, ist violett. Ohne Steam-Beschreibung steht die englische von IGDB da. **VR per Mod**
  (0.8.1): Sagt PCGamingWiki bei einer Brille „hackable“, trägt das PC-Spiel die Marke „VR per Mod“;
  hat Nexus Mods nur Mods mit VR im Namen oder geht es mit vorpX, steht „VR-Mod“ (ein Hinweis, türkis
  gestrichelt; bis 0.8.19 mit „?“). Der Filter „VR per Mod“ zeigt beide. Die Einzelheiten nennen die Brillen und verlinken die
  Nexus-Seite, die beliebtesten Mods und die VR-Mods. **Lenkrad** (0.8.3, Sim-Racing): Steht ein
  PC-Spiel oder ein VR-Titel (ab 0.8.5, auch auf der Wunschliste) in einer Liste der Rennspiele, trägt es
  die Marke „Lenkrad“: die Liste „Supported Games“ von SimHub (ab 0.8.5, über die Steam-ID) oder die
  offene Liste der Rennsimulationen aus dem Simucube-Forum (Direktantriebe mit Force Feedback; was dort
  läuft, läuft auch mit Simagic). Deuten nur die Steam-Schlagwörter darauf (unter den ersten zehn ein
  Rennen, „Racing“ oder „Driving“, und eine Simulation, „Automobile Sim“ oder „Simulation“), steht
  violett „Lenkrad?“ (ein Hinweis). Die Kompatibilitätsliste zu Simagic selbst liegt hinter einer
  Bot-Prüfung und wird deshalb nicht abgerufen. Filter „Lenkrad“, Zeile „Sim-Racing“ in den Einzelheiten.
  Ab 0.8.12 heißt die Marke „SimRacing“ (ab 0.8.20 wie „VR“ und „Geheimtipp“ nur umrandet in ihrer Farbe; aus Steam-Schlagwörtern allein gestrichelt, ohne „?“), dazu im Reiter PC
  ein Filter „VR“ neben „SimRacing“ und „VR per Mod“.
  Über der Liste steht kurz die Zahl
  der Spiele, die Herkunft der Angaben klappt auf,
  daneben ab der Spalte Spieler **Mein Stand** (Backlog ○, angefangen ▷, durchgespielt ✓,
  Favorit ★; steht in allen Reitern an derselben Stelle, die Zeile springt beim Setzen nicht), der
  hinter dem Namen steht, sich filtern lässt („Mein Stand“, Mischung „Aus dem Backlog“) und in
  der Sicherung steckt. Am Handy stehen die Werte je Spiel untereinander.
  **VR** (bis 0.5.8 der Reiter „Bibliothek“): alle VR-Titel, die du bei Meta oder am PC hast,
  mit den Spalten Besitz, Crossbuy (Herkunft im Tooltip, „T“ aus der Tabelle, violett „Recherche“
  aus der Recherche), Meta- und Steam-Wertung, Steam-Spieler jetzt, letztes Update und Recherche. Filter
  Besitz, Wertung, Mein Stand und Crossbuy. Die Einzelheiten zeigen dieselben Fakten, Recherche
  und Klappe (Links, bearbeiten) wie die Wunschliste. Unter „Alle“ stehen VR-Titel nicht, am PC
  meist ohnehin unter PC.
  Filter, Mischungen und Zufall gelten im gewählten Reiter; unter „Alle“ trägt ein Konsolenspiel
  sein System als Marke. Steam-Abgleich und Steam-Wertung gibt es nur für PC-Spiele. Filter nach
  Genre (Menü mit Suche und Häkchen, umschaltbar zwischen
  „eines davon“ und „alle“; die Zahl hinter einem Genre zählt, was mit den übrigen Filtern übrig
  bliebe), Mehrspieler-Art (Menü mit Häkchen; mehrere gewählt: alle müssen passen: Mehrspieler, Online,
  Koop, Lokal, Splitscreen, LAN, MMO; ab 0.10.16 direkt vor der Spielerzahl), Spielerzahl, Launcher, Steam-Wertung und „über zwei Jahre in der Sammlung“; gewählte
  Mehrspieler-Arten und Genres stehen als Marken mit × darunter; sortiert nach Wertung, Geheimtipp, Bekanntheit, neu in der Sammlung, zuletzt gespielt, Jahr, Name
  oder Zufall. Ab 0.9.3 stehen bei Spielen aus Steam (auch VR-Titeln mit Steam-ID) unter Mein Stand die Spielzeit
  und der Tag, an dem du zuletzt gespielt hast, laut Steam-Konto; der Filter „Gespielt“ zeigt nie gespielte, seit
  über einem Jahr nicht gespielte oder schon gespielte. Meta nennt keine Spielzeit. Die Suche findet Name, Entwickler, Verlag und Genre; Erscheinungsdatum, Entwickler und
  Verlag stehen im Tooltip am Jahr wie im eShopKompass. Die Liste lädt beim Scrollen weiter.
  Mischungen (eine Zeile, am Handy seitlich wischbar) setzen Filter mit einem Klick: „Koop zu zweit“, „Couch-Abend“, „Große Runde“,
  „Geheimtipps“, „Gut, lange her“, „Liegt brach“ (ab 0.9.3: gekauft und laut Steam-Konto nie gespielt); ein zweiter Klick nimmt sie zurück. „Überrasch mich“ zieht
  drei Spiele aus dem, was die Filter zeigen (gut bewertete kommen öfter), „Wilde Mischung“
  würfelt dazu eine Mehrspieler-Art und ein Genre; „Schließen“ blendet die Vorschläge aus.
  Filter und Zufall stehen in der Adresse (`#sammlung?…`, alte Lesezeichen mit `#entdecken?…`
  gelten weiter), eine Mischung lässt sich so als Lesezeichen merken.
  Merkmale stammen aus Playnite: Mehrspieler aus `Features` und Schlagwörtern, die höchste
  Spielerzahl aus „N Players in Co-Op“ (ab 0.9.5 ohne geratene Zahl, vorher galt Splitscreen als
  zwei; unbekannt zählt beim Filter „ab 2“ als zwei), Genres in etwa 20 Gruppen. Ein Launcher, der nur aus der Kennung
  vermutet ist, steht violett. Bei Steam-Spielen gleicht der Abgleich Genres, Mehrspieler-Arten und
  Jahr mit den Steam-Store-Daten ab (80 je Lauf): was Playnite und Steam beide sagen, steht ohne
  Zeichen, was nur eine Quelle sagt, bleibt drin und steht violett, der Tooltip nennt die Quelle
  (seit 0.6.1 statt „≈“; Steam kennt nur grobe Genres,
  Puzzle oder Horror etwa nicht). Die Einzelheiten nennen, ob ein Spiel schon abgeglichen ist;
  Spiele mit VR tragen die türkise Marke „VR“: laut Steam-Details, als VR-Titel im Tool oder laut VR-Prüfung im
  Steam-Store (ab 0.8.7); nennt nur der Name VR, ist die Marke violett. Ab 0.8.7 stehen unter PC auch deine
  VR-Titel am PC, die Playnite nicht kennt (am PC gekauft oder bei Meta mit Crossbuy). Ab 0.8.9 sind sie eigene
  Spiele der Sammlung und bekommen wie alle Steam-Details, Rezensionen, IGDB, PCGamingWiki und Nexus Mods; kennt
  Playnite einen davon später, fällt der eigene Eintrag weg. Die Suche gilt je Reiter
  und leert sich beim Wechsel. „herunterladen“ gibt die gefilterte Liste mit den gezeigten Spalten und Mein Stand
  als CSV aus, aufgeklappte Spiele mit ihren Einzelheiten; ⧉ am Spaltenkopf „Spiel“ kopiert alle Titel der Liste. PlayStation-Spiele der ersten Generation
  stehen unter PS1 (bis 0.6.0 „PS“). Die Wertung kommt nur aus Steam-Rezensionen (ab 50, Anteil positiv),
  die der Abgleich nach und nach holt (100 je Lauf, siehe [docs/abrufe.md](abrufe.md));
  die Community- und Expertenwertung aus Playnite zählt nicht (Entscheidung 22.10.2026: zu
  unzuverlässig). Die Zahl der Rezensionen zeigt die Bekanntheit. Der Geheimtipp-Wert
  G = (Wertung − 70) / 30 · (1 − log10(Rezensionen + 1) / 5) ist hoch bei guter Wertung und
  wenigen Rezensionen; die Marke „Geheimtipp“ (grün umrandet) steht ab 0,4 (bis 0.8.11 ab 0,2, das traf zu viele Spiele, um noch ein Tipp zu sein).

Farben haben je eine Bedeutung: Rabatt blau, ★ und „Bestpreis“ Gold, Prüfen, Veraltetes und
Recherche violett, Grün für das, was für dich spricht (günstigerer Laden, Crossbuy, bessere
Wertung), Rot für den Aufpreis über dem Bestpreis, Grau für Eigenschaften ohne Wertung („ohne
Crossbuy“). Ausnahmen wie im eShopKompass: die Familienfarben der System-Reiter, die farbigen
Genre-Blasen und die Wertung als Farbton in der Sammlung. Gruppen und Karten klappen, der Browser merkt sich, was du
zuklappst; „alle aufklappen · alle zuklappen“ steht darüber, eine Suche öffnet alles. Das
Suchfeld leert × oder Esc. Oben rechts: hell, dunkel oder wie das Gerät; im Dunkeln ist die
Schrift gedeckt, hell bleiben nur Name, Überschriften, aktiver Reiter und große Preise (0.7.2). Regeln für Änderungen:
[docs/oberflaeche.md](oberflaeche.md).
