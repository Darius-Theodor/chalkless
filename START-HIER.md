# Start hier

Chalkless ist dein Ordner für die Unterrichtsplanung. Ein KI-Agent arbeitet direkt darin: Du sagst in deinen Worten, was du für eine Stunde brauchst, und bekommst ein fertiges Paket – Stundenplanung, Arbeitsblatt mit Lösung und Folien, die zusammenpassen. Du musst nichts Technisches wissen und tippst keine Befehle.

## So fängst du an
1. **Öffne deine KI-App mit einem Ordner**, in dem Chalkless wohnen soll – am besten ein neuer, leerer Ordner „Chalkless“ in deinen Dokumenten.
2. **Kopiere den Text unten in den Chat** und schick ihn ab. Der Agent stellt dir eine einzige Frage, die du in einem Satz beantwortest, und richtet dann alles selbst ein.
3. **Sag, was du brauchst** – getippt oder diktiert, in beliebiger Reihenfolge. Zum Beispiel: „Ich brauch für Donnerstag in der 3b eine Stunde zu …, die Kinder sollen …, 45 Minuten, Beamer hab ich.“

### Text zum Kopieren
```text
Bitte richte mir Chalkless ein, meinen Arbeitsbereich für die Unterrichtsplanung.
Paket: das Git-Repository https://github.com/Darius-Theodor/chalkless, Zweig pilot (öffentlich, ohne Anmeldung). Klone es mit git in einen temporären Ordner außerhalb dieses Ordners; darin liegt deine Anleitung.

Schreib mir von Anfang an auf Deutsch. Alles Technische machst du selbst; ich tippe
keine Befehle und nenne keine Pfade. Im Paket liegt eine Anleitung für dich:
setup/EINRICHTUNG.md. Lies sie zuerst, noch bevor du in diesem Ordner etwas anlegst,
und folge ihr Schritt für Schritt: Stell mir zuerst deine eine Frage und richte danach
alles ein.
```

### Copy text (English)
```text
Please set up Chalkless for me, my workspace for lesson planning.
Package: the git repository https://github.com/Darius-Theodor/chalkless, branch pilot (public, no login). Clone it with git into a temporary folder outside this folder; your instructions are in it.

You do all technical steps yourself; I type no commands and name no paths.
The package contains instructions for you: setup/EINRICHTUNG.md. Read them first,
before you create anything in this folder, and follow them step by step: ask me your
one question first and set everything up after that. Write to me in English from the start.
```

## So arbeitest du damit
- **Erst der Plan, dann das Ergebnis.** Der Agent sagt dir in ein paar Zeilen, wie er dich verstanden hat, stellt höchstens eine Handvoll Fragen mit Vorschlag und baut erst, wenn du „los“ sagst. Soll er ohne Rückfragen anfangen, sag es dazu: „Mach alles in einem Rutsch.“
- **Nachbessern im Gespräch:** „Die Folie ist zu voll, mach zwei draus.“ „Die Kinder brauchen mehr Platz zum Schreiben.“ Er ändert genau das und hält den Rest stimmig.
- **Die Übersicht** zeigt, was fertig ist, mit Vorschau. Dort öffnest du die Dokumente. Je nach App steht sie neben dem Chat oder liegt als Datei „Übersicht“ im Ordner, die du mit einem Doppelklick öffnest; der Agent sagt dir, was bei dir gilt. Dokumente gibt es als PDF zum Drucken, Folien als Präsentation im Browser.
- **Dauerhafte Wünsche:** Sag „immer“ oder „nie“, dann merkt er es sich. „Was hast du dir gemerkt?“ zeigt alles, „vergiss das“ nimmt es zurück.
- **Eigene Vorgaben und Beispiele:** Gibt dein Seminar oder deine Schule eine Form vor, sag es oder leg ein Beispiel in den Ordner „eingang“. Vorgaben gehen vor.
- **Was nicht belegt ist, ist markiert.** Lehrplanbezüge und Quellen, die der Agent nicht geprüft hat, stehen als „[PRÜFEN: …]“ im Dokument. Alles ist ein Entwurf, bis du es für gut befindest.

## Wenn etwas schiefgeht
- „Mach die letzte Änderung rückgängig.“ – Jeder fertige Schritt ist gesichert. Was du selbst an einer Datei änderst, überschreibt der Agent nicht.
- „Prüf, ob mit meinem Arbeitsbereich alles in Ordnung ist.“
- Schließe den Chat und öffne einen neuen. Der Agent weiß, wo ihr stehen geblieben seid.

## Für den Agenten
If `setup/EINRICHTUNG.md` exists, installation is not finished: follow it now. Otherwise this folder is installed: read `AGENTS.md`. Talk to the teacher in the language of their own words; never ask them to type a command or name a path.
