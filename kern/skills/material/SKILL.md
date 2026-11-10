---
name: material
description: Create what pupils get in their hands for a lesson – worksheet with answer key, help or tip cards, text or source sheets, games, cards, quizzes – as one print file. Runs as part of every lesson package (skill dokument) and alone when they ask for material only (AB, Arbeitsblatt, Hilfekarte, Tippkarte, Lösungsblatt, Quiz, Lückentext).
---

# Skill: material

## Inputs
- The lesson it belongs to: within a package the plan you just made; alone, the lesson they name or STAND `letztes`. They asked for a lesson, not only for material → skill `dokument` (the whole package).
- Age group and subject of the area; their template `vorlagen/<typ>/` if one exists, otherwise `kern/gestaltung/dokumente.md` §4 with the structure of `kern/gestaltung/beispiele/arbeitsblatt.html` (help cards: `loesung-hilfekarte.html`).

## Steps
1. **One file per lesson:** `bereiche/<area>/material/YYYY-MM-DD_material_<slug>.html`, meta `stunde` = path of the plan. Sections in this order, each on a new page: the worksheet (pupil pages) · further pupil parts the plan uses (help card, text sheet, cards to cut) · the answer key as `section.teacher-insert` with the band "Nur für die Lehrkraft".
2. **Match the lesson exactly:** the tasks of the plan with the same numbers and wording, the same terms, in the order of the lesson. One task per step of the lesson; do not add tasks the plan has no time for.
3. **Write for these pupils:** short instructions that say what to do; type size and writing room for the age (`dokumente.md` §4). Generous room to write, draw and tick – cramped sheets are the most common fault. A table pupils fill in has enough rows and tall rows; blank rows for their own finds are welcome.
4. **Differentiation where the plan has it:** an extension task with ★ for the fast ones; a tip box or a help card for those who need support (the next step or a worked example with other numbers, never the answer).
5. **Answer key:** solve every task yourself, then write the key: expected answers per task number; for open tasks what a good answer contains; for experiments what really happens, including the surprising cases. Add how many copies to print and what to cut.
6. **Pictures** only where they carry meaning, as simple inline SVG (the object, the set-up, a diagram).
7. Look at the pages (`kern/pruefung/rubrik.md` A and C), fix, make the file self-contained, export the PDF. Alone (not inside a package): update STAND, commit, and reply in a few lines without paths.
