---
name: dokument
description: Build the lesson package for one lesson – lesson plan (Verlaufsplan, or a full written draft for a visit or exam), worksheet with answer key, and slides – as documents that fit together; then change it in conversation. Use for every request for a lesson of any kind (Stunde, Verlaufsplan, Unterrichtsentwurf, Unterrichtsbesuch, "ich brauch für nächste Woche …"), also as one lesson of several (skill sequenz).
---

# Skill: dokument – the lesson package

A request for a lesson produces, together and without further asking: **the lesson plan, the worksheet with its answer key, and the slides.** Single parts only when they explicitly want only that part ("nur das Arbeitsblatt" → skill `material`, "nur Folien" → skill `praesentation`). A full written draft (Unterrichtsentwurf) instead of the short plan when they need one for a visit, an exam or their seminar – the worksheet, answer key and slides come with it all the same.

## 1. Understand
- Take everything from their words: topic, class, time, what the pupils should do, what they have (material, devices), how it should start, what pupils should know at the end, requirements of the seminar or school. Area → `bereiche/<area>/STAND.md` and the earlier files of the area: a follow-up lesson builds on what the class did and keeps the look of the earlier package.
- Ask only when something wrong would be built otherwise (`kern/regeln.md` §4). Everything else is an assumption you name in one line at the end: the date (next fitting school day), the clock time, the class size if neither they nor the profile says it. What they mention about their context along the way goes into the profile (`kern/regeln.md` §5).
- **A follow-up lesson lies after the last lesson of the area.** A lesson they report as taught is in the past, whatever date its file carries: date the new one after it (the next fitting school day, or a week later when they say "nächste Woche"), never on the same day again.
- **A document someone will assess** (visit, exam) needs facts only the teacher has – how the group works, where it stands, what came before. Write what they told you, keep each open point to one short marked gap, and ask for exactly these facts in the closing reply as two or three concrete questions (they take the place of the "points to look at"), so that the next turn can fill the chapter.
- Say the waiting-time sentence (a package takes roughly 10–15 minutes), then build.

## 2. Plan the lesson first, in your head
Before any file: the one insight of the lesson, the tasks (numbered 1, 2, 3 – these numbers and wordings are used everywhere), the phases with minutes that add up, what is on the worksheet, what each slide shows. The lesson plan is the source of truth; worksheet and slides are derived from it. Check the plan against the request, wish by wish, and against the time: handing out, tidying up and a class discussion cost real minutes.

## 3. Build the parts
All files share date and slug (`kern/konventionen.md` §2). Design: `kern/gestaltung/dokumente.md` for the printed parts, `kern/gestaltung/folien.md` for the slides; their own template in `vorlagen/` wins where one exists.
1. **Lesson plan** → `stunden/YYYY-MM-DD_stunde_<slug>.html`. Short form: head data, prior knowledge, goal, material list, Verlaufsplan with the worksheet's task numbers and the slide numbers in its rows, homework/reserve, "Noch zu prüfen". Written draft: the sections the seminar names, in its order, within its page limit (`dokumente.md` §3).
2. **Worksheet with answer key** → `material/YYYY-MM-DD_material_<slug>.html`: skill `material`. It contains everything pupils get in their hands in this lesson – the sheet, a help card if the plan uses one, the text they work with – and the answer key as teacher pages.
3. **Slides** → `praesentationen/YYYY-MM-DD_praesentation_<slug>.html`: skill `praesentation`.

What the lesson needs is built now. Nothing of the package is left "to be added".

## 4. Look, compare, fix
`kern/pruefung/rubrik.md`: export and look at every page and every slide (A), lay the parts side by side (B), solve the tasks and check the facts (C). Fix what you see and look again. Then make the printed documents self-contained and export the PDFs once more (`dokumente.md` §1 step 4). Write the `pruefung` line into each file.

## 5. Save and tell
- Update STAND (`letztes`, `naechstes`, `offen`), commit `paket <area>: <slug> (entwurf)` (skill `commit`).
- Closing reply as `kern/regeln.md` §1 says: about eight lines, their language, no paths. What exists (plan, worksheet with answer key, slides – with page and slide counts if you like), your assumptions in one line, at most two things they should look at (a fact you could not verify, a decision that could go either way), one next step ("Sag mir, was anders sein soll.").

## Changing a package
`kern/regeln.md` §4 "Changes": change exactly what they ask, carry the consequence into every other part (a task removed from the worksheet disappears from the answer key, the plan row, the slide and the minutes; five minutes moved from one phase to another change the plan's times, the slide notes and any time on a slide), re-export, look at the changed pages, set meta `geaendert`, note the change in the feedback log (`kern/konventionen.md` §5), commit `change <area>: <slug> (<what>)`. Reply in two or three lines: what changed and what you adjusted with it. When they say it is fine: status `geprüft`; if `[PRÜFEN: …]` marks are still in it, say so in one sentence – their yes does not verify those points.
