---
name: einrichten
description: Set up a teacher's personal instance from one sentence of theirs (where and at which school type they teach, classes and subjects, anything special such as training or fixed format requirements), show the ready card, then build the first lesson package at once. Use on the first session (no profil/rahmen.md), when they say einrichten / anfangen, or to finish an interrupted setup.
---

# Skill: einrichten

The teacher wants to start working, not to be interviewed. Setup is one question that they answer in one sentence; whatever they already said is never asked again. Right after it comes the ready card or, if they already asked for something, the first package.

## 1. The one question
If the setup aid (`setup/EINRICHTUNG.md`, step 0) has already asked it and they answered, do not ask again: go to step 2. Otherwise ask it now, as plain chat text with an example sentence. The question itself is a heading (`## `) so that it cannot be overlooked; the rest are normal paragraphs. Send them as they stand here (the fence only shows where they begin and end; your reply has no fence around them):

```markdown
## Erzähl mir in einem Satz, wo und was du unterrichtest.

Zum Beispiel: **„Ich bin Referendarin an einer Grundschule in Bayern, Klasse 2a, Mathe, Deutsch und HSU.“**

Gibt es feste Vorgaben von Schule oder Seminar, oder weißt du schon, was du als Erstes brauchst? Dann häng es einfach an.
```

- **Never as a quote block (`>`), in a code block or in italics**, here and on the ready card: hosts show these small or grey, and the text gets lost.
- **Plain chat text.** No question form, no multiple choice, no buttons, no tool that asks on your behalf, even if your host offers one.
- You need two things: the region (Bundesland or country) and the school type. If one is missing after their answer, ask for exactly that in one sentence. Everything else (class, subjects, training, requirements, an example of their own) you take if they said it and never ask for.
- Before asking, read what they already wrote (their first messages, files in `eingang/`). If that already gives region and school type, ask nothing.
- If their message already contains a request for a lesson, setup and the first package happen in the same turn: write the profile from what they said, then build (step 3). A missing detail that would not make the lesson wrong (class name, class size, exact date) is assumed and named, not asked.
- Form of address and language: as they write (German: "du" unless they write "Sie"). Never ask for pupil data.

## 2. Write the instance (quietly, from what they said)
- Skeletons: copy `kern/instanz-vorlage/` into `profil/`, `gedaechtnis/`, `review/` (its README says where); never overwrite an existing file.
- `profil/rahmen.md`: `land`, `region`, `schulform`, `status` (`in_ausbildung` / `ausgebildet` / `quereinstieg`; unknown → `ausgebildet` is not assumed, leave `[ ]`), `status_begriff`, `paket: rahmen/<id>` (id as in `kern/konventionen.md` §6), `kern_version` from `kern/VERSION`, `pilot: aus` (only if the file `kern/PILOT` exists: `pilot: an` and the transparency sentence of skill `pilot`).
- `profil/lehrkraft.md`: `anrede`, `sprache`, one row per class × subject with the area folder in the first cell written as `bereiche/<area>` (for example `bereiche/2a-mathe`; the folder check finds the areas by this), lesson length, class sizes and what the room has if they said it, dates they named (a visit, an exam) under "Termine".
- `profil/pflichten.md`: a row for every requirement they named (who asks for it, what it must contain, limits such as "höchstens sechs Seiten") with `Art` = `Pflicht` and the issuer as source. These rows are requirements: they go before wishes.
- One area per class × subject: `bereiche/<area>/STAND.md` from the skeleton.
- Framework package index `rahmen/<id>/paket.md`: a table of building blocks (Lehrplan per subject, Kalender, Begriffe; Ausbildung if in training) with status `fehlt`.
- **Find the curriculum – always, and short.** If your host has web search: look up which official curriculum applies to their region × school type and, where they named them, to their subjects and grade, on the publisher's own pages (ministry or state institute). You locate it, you do not excerpt it: publisher, exact title, the address of the page per subject, the year it is from. A handful of searches, about two minutes at most. Enter what you found in the index rows as `gefunden, ungeprüft` with publisher, title and address. Never write a title or an address from memory: a row you did not see on the publisher's page in this session stays `fehlt`. No web search on this host, or nothing reliable found → the rows stay `fehlt` and the card says so.
  The verbatim texts are read later, subject by subject, when a document needs them (skill `recherche`); until then such places carry `[PRÜFEN: …]`. The curriculum is proposed to them on the ready card (step 3); it never delays the first package.
- **Templates only from an example.** If they gave an example of their own format (a file), derive it with skill `vorlage-ableiten` – after the first package unless the example is needed for it. Without an example the core design applies; do not ask about layout, fonts or document types.
- `profil/checks.md`: set the `setup` row to `erledigt` with today's date.
- Tools: if `profil/werkzeuge.md` does not exist yet, run `python kern/tools/voraussetzungen.py --probe-browser` (and `--install` if a line says `MISS`); set the `werkzeuge` row to `erledigt`.
- Commit `setup: instance for <area(s)>` (skill `commit`).
- The overview (`kern/regeln.md` §11): side panel where the host has one, otherwise the file.
- If `setup/EINRICHTUNG.md` still exists: delete the folder `setup/` now (it is only for the first setup).

## 3. Ready card, or the first package
**They already said what they need:** build it now (skill `dokument`). The closing reply of that package starts with one extra line, "Chalkless ist eingerichtet: <Schulform> · <Region> · <Klasse und Fächer>.", says once how the overview is opened and names the curriculum you found in one sentence (as in point 2 below).

**Otherwise the ready card.** It is the whole reply and is not counted against the eight lines of `kern/regeln.md` §1:
1. This block as a code block. The three check lines and the three rules are fixed; fill in the five rows from what they said and what you found, in their language, the values starting in the same column. Leave out a row you have nothing for (no class yet → `Unterricht` shows the subjects only; not in training and nothing special → no `Status` row). `Lehrplan` names the curriculum you found, short (its name and the grade band); nothing found → "noch nicht gefunden". `Übersicht` says how they open it, in a few words ("neben dem Chat" for a side panel; "Datei „Übersicht“ im Ordner – Doppelklick" for the file).
   ```text
     ════════════════════════════════════════════════════════════════════
     ✓ Paket entpackt
     ✓ Werkzeuge bereit
     ✓ Dein Profil angelegt
     ────────────────────────────────────────────────────────────────────
     Schule       Grundschule · Bayern
     Unterricht   2a · Mathematik, Deutsch, HSU
     Status       Referendariat
     Lehrplan     LehrplanPLUS Grundschule · Jgst. 1/2
     Übersicht    Datei „Übersicht“ im Ordner – Doppelklick
     ════════════════════════════════════════════════════════════════════
   ```
   Only what really happened gets a check line: if a tool is missing, the second line says what that means instead ("– PDF-Export fehlt: Du druckst im Browser als PDF").
2. The curriculum as a proposal, one normal paragraph: its full name in bold, the publisher, one link to the publisher's page you opened, and that you will go by it unless they say otherwise. It needs no answer from them:
   ```markdown
   Als Lehrplan habe ich den **LehrplanPLUS Grundschule** (ISB Bayern), Jahrgangsstufen 1/2, gefunden: [zur Seite](https://…). Danach richte ich mich bei deinen Stunden. Stimmt das nicht, sag es mir einfach.
   ```
   Nothing found: "Den Lehrplan für dich habe ich noch nicht gefunden. Schick mir gern einen Link oder die Datei, dann richte ich mich danach." When they confirm or correct it later, note that in the index row (`bestätigt von der Lehrkraft, <date>`); the status changes only by reading the source (skill `recherche`).
3. Under it, as two normal paragraphs (no fence in your reply): one heading that it starts now, and one example request made for them – their class, one of their subjects, a topic that fits the grade, with the things a good request contains (what the children should do, the time, the device):
   ```markdown
   ## Sag mir jetzt einfach, was du brauchst – getippt oder diktiert.

   Zum Beispiel: **„Ich brauch für Donnerstag in der 2a eine Mathestunde zum Geld. Die Kinder sollen viel selber legen, am besten zu zweit. 45 Minuten, ich hab ein Smartboard.“**
   ```

4. Only in a pilot build with `pilot: an`: as the very last paragraph the transparency sentence of skill `pilot`, said once.

Nothing else: no summary of what was stored, no table of sources, no list of features, no folder names, no side note about the package, its files or its tools.

## Later, when it comes up
Everything else is learned while working, never in an interview up front: timetable and lesson times, textbooks, school dates, further classes, how they like things. (The files in `kern/interview/` belong to later tasks such as a year plan or a transition; do not read them for setup.)
