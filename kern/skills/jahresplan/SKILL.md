---
name: jahresplan
description: Create or update a plan for one subject and class across the school year or term (Jahresplan, Stoffverteilungsplan, Jahresübersicht, schulinternes Curriculum), distributing the curriculum over the counted lessons of the school calendar – overview first, then section by section. Use when they ask to plan a subject for the year or a term, or when lessons were lost and the rest of the year must be redistributed.
---

# Skill: jahresplan

## Inputs (from context; planning reply and their go first, `kern/regeln.md` §4)
- Area, lessons per week and slots (`profil/lehrkraft.md`), start date, what was already taught, optional textbook or theme.
- Whether the plan is required and in which form (`profil/pflichten.md`); if not required, keep it as light as they want.

## Steps
1. Template for the type; none → `vorlage-ableiten` (or, without an example, the core reference: `kern/gestaltung/standard.css` with the structure of `kern/gestaltung/beispiele/jahresplan.html`; a lighter table if it is not a mandatory document and they agree).
2. **Count the lessons per section against the calendar** (explicit step):
   - Read `rahmen/<id>/kalender/<schuljahr>.md`: first and last school day, holidays, public holidays, the school's own dates, status.
   - Per week: the area's slots minus the days that fall into holidays, onto public holidays or onto the school's own dates. Compute weekdays (e.g. Python `datetime`), never from memory; a public holiday on a weekend costs nothing.
   - Days the calendar does not name (movable days off, school-set days) are never invented; they stay an assumption in one line and reduce the buffer, not a section.
   - Write the count traceably in `<file>.abdeckung.md`, section `Zählung`: one line per section (period, weeks, slots, subtracted dates with reasons, result) and the total. Put a count into the document only where their template has a column for it.
   - If the calendar block is not `geprüft`, every count is provisional and the plan and the reply say so in one sentence.
3. **List** all parts of the subject curriculum for the grade band from `rahmen/<id>/lehrplan/`. Place every part at least once; seasons, festivals and exam periods decide the order where it matters.
4. **First pass = overview only:** sections with period, number of lessons, topic, curriculum parts. Show it, ask for confirmation.
5. **Then one section per request:** rows per lesson or week with date or week, topic, short content, curriculum reference, cross-references (only from the source).
   - Curriculum references verbatim only from building blocks with status `geprüft` (`kern/regeln.md` §6), with the location in the source; otherwise `[PRÜFEN: <block>]` (for a whole column: once as a table note, `kern/gestaltung/dokumente.md` §4).
   - Omissions only where they are visible: each marked `[…]`, the location next to it. Never shorten without the mark, merge or paraphrase inside quotation marks.
   - Sources that disagree (requirement, their wish, preference, template, reference): order of precedence `kern/regeln.md` §4.
6. Coverage check: curriculum part → lessons; uncovered parts marked. Put it into the document only if their template has such a section; otherwise in `<file>.abdeckung.md` (section `Abdeckung`) and name uncovered parts in the reply. Never add a section to their format on your own. Keep 1–2 buffer lessons at the end of the year (or of each term if the year has exam periods).
7. Rubric parts A and B, then part D: export, look at the pages (wide tables are the usual failure); recount against the calendar and check every date with its weekday (D3); status and notes describe only what happened (D5) – no "abgestimmt", "genehmigt" or "gehalten" before it is true.
8. STAND, commit `<typ> <area>: <slug> (entwurf)` after each pass; short reply (`kern/regeln.md` §1), the `pruefung` line goes into the file.

## Updating
- Change only affected rows; set meta `geaendert`. If the calendar changed, recount and show the difference before changing anything.
- Lessons and weeks already taught stay exactly as they are (date, row, wording); "already taught" = before today and not reported as cancelled, or its document has status `verwendet`, or STAND `letztes` is past it (the same definition as skill `sequenz`).
- Lost lessons or a cancelled week: recount the remaining weeks, then use the buffer first, then shorten practice in the same section, then move later sections – never into holidays, onto a public holiday or a school's own date. If a curriculum part no longer fits, name the trade-off in one sentence ("Für … bleiben nur noch 4 statt 6 Stunden; ich kürze die Übungsphase."), mark it in the coverage file and show the changed rows first.

## Variants (no school type assumed)
- **Several lessons per week or double lessons:** count slots, not days; a double lesson is two lessons unless `begriffe.md` says otherwise.
- **Text-heavy subjects** (literature, history, languages): a section may list set texts with author, title and edition; an edition that has not been verified gets `[PRÜFEN: Auflage/Jahr]`. Long rows follow default G2 in `kern/gestaltung/dokumente.md` §3.
- **Exam periods and assessed tasks** come from the calendar or `profil/pflichten.md`; never set an exam date that neither they nor a source named – write the week and `[PRÜFEN: Termin]`.
