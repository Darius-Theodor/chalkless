---
name: sequenz
description: Plan several lessons – two lessons, a unit, a Reihe, an Unterrichtsvorhaben – as a short overview of its own, then build the lesson package for each lesson they asked for (skill dokument). Also redistributes the rest of a running unit when a lesson was cancelled.
---

# Skill: sequenz – several lessons

## When they ask for several lessons at once
1. **Overview first, as its own short document:** `bereiche/<area>/sequenzen/YYYY-MM-DD_sequenz_<slug>.html` (date = first lesson), teacher register, landscape table with the structure of `kern/gestaltung/beispiele/sequenz.html`: one row per lesson with number, date, topic, the one goal of the lesson, the central task or material, and how it connects to the next. One page for up to about eight lessons. No two lessons with the same goal; an arc from entry to a closing that refers back to the start.
2. **Then package by package** (skill `dokument`), in order, for exactly the lessons they asked for: "the first two lessons" means two full packages, each with plan, worksheet with answer key and slides. Each lesson's files carry meta `sequenz` (path of the overview) and `teil`. Later lessons build on earlier ones: same terms, no repeated entry, a short look back at the start.
3. Say the waiting-time sentence with an honest estimate (about 10–15 minutes per lesson). If they ask for a long unit (more than about four lessons) in one go: build the overview and the first two packages, then ask whether to go on in the same way – long runs get generic.
4. Check the overview like every document (`kern/pruefung/rubrik.md`) and check across the lessons: terms and goals agree with the overview. Update STAND (`sequenz: … – Teil <n> von <m>`), commit after each finished package.
5. One closing reply for everything, short (`kern/regeln.md` §1): the lessons with their parts, assumptions, at most two points to look at, the next step.

## Dates and the curriculum
- Lesson dates: from what they said and `profil/lehrkraft.md`; compute weekdays (Python `datetime`), never from memory. Holidays only from the package calendar if it is `geprüft`; otherwise dates are an assumption named in one line – never invent days off.
- Curriculum references: `kern/regeln.md` §6 – verbatim only from `geprüft` building blocks with their location, otherwise in your own words with `[PRÜFEN: Lehrplanbezug]`.

## Changing a running unit
Lessons already taught stay exactly as they are. A cancelled lesson: move its content into the remaining dates (merge with a neighbour, or drop a practice lesson), name the trade-off in one sentence, update the overview, set meta `geaendert`, commit.

## Text extracts
A text the class works with is part of the material of that lesson (skill `material`), short enough for this class, with author, title, year and where it comes from; line numbers in plan, sheet and answer key agree. A source you cannot verify is not presented as one (`kern/regeln.md` §6).
