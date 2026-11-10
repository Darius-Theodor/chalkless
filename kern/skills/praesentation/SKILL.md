---
name: praesentation
description: Build the slides for one lesson as a single self-contained offline HTML presentation from the core frame, one slide per moment of the lesson plan, with teacher notes; checked slide by slide before it is shown. Runs as part of every lesson package (skill dokument) and alone when they ask for slides only (Folien, Präsentation, Beamer, Smartboard).
---

# Skill: praesentation

## Inputs
- The lesson plan (within a package the one you just made; alone, the one they name or STAND `letztes`). No plan and they want a lesson → skill `dokument`. Slides without any plan are guesswork: write the plan first.
- Age group of the area; their template `vorlagen/praesentation/` if one exists; otherwise `kern/gestaltung/folien.md`.

## Steps
1. **Build** as `folien.md` §1 says: copy the frame (do not read it through), set meta tags, contract block and reading floor, replace the demo beats. File: `bereiche/<area>/praesentationen/YYYY-MM-DD_praesentation_<slug>.html`, meta `stunde` = path of the plan. A follow-up lesson keeps the look of the earlier deck of the area.
2. **Slides from the plan:** a title slide, then one slide per moment in the plan's order (`folien.md` §2). On the slide: what learners need now – the question, the task with the worksheet's number and wording, the `.meta` line (social form · time · material), the collection, the result. Builds where the phase unfolds; a solution only with its build.
3. **One thing per slide.** A slide with more than about six lines or four steps becomes two. Never shrink below the reading floor.
4. **Notes:** everything for the teacher goes into `aside.notes` – clock time and duration as in the plan, what to say, expected answers, when to click.
5. **Pictures:** none to decorate; a simple inline SVG where it carries meaning (`folien.md` §5).
6. **Check every display step:** `python kern/tools/folien_check.py <file> --out <temp folder outside the instance>`; fix exit 1 and run again; look at `uebersicht.png` and the fullest slides; compare slide by slide with the plan (order, tasks, times, nothing the plan does not have); spelling. Write the `pruefung` line.
7. Alone (not inside a package): update STAND, commit, and reply in a few lines without paths and without keyboard shortcuts – they open the deck in the overview; if they ask how to present: full screen with F, forward with the arrow key or a click, the button at the bottom opens the notes.

## After a change of the plan
Update the deck in the same turn: the affected slides, their notes, the times; run the check again and look at the changed slides.
