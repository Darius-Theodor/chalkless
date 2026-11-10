# Before you show it (core)

You are the only one who looks at the pages before the teacher does. Do the steps below – executed, not affirmed – fix what you find, look again at what you fixed. Never hand the teacher a checklist. The result goes into the file as one line (meta `pruefung`, `kern/konventionen.md` §2): what you looked at, what stays open. The chat gets no check report; at most two points the teacher should look at themselves.

## A. Look at every page
- **Documents:** `python kern/tools/pdf_export.py <file>.html` writes the PDF; `python kern/tools/pdf_export.py --png <file>.pdf --out <temp folder outside the instance>` writes one image per page. Open every image and look:
  - nothing cut off or running over at the right or bottom edge; no table column squeezed, no word broken letter by letter;
  - no empty or nearly empty page; a pupil page that is more than half empty gives its tasks more room to write and draw, or the pages are balanced anew; no heading alone at a page end; a task, a box or a card is never split across pages;
  - enough room where pupils write (lines and boxes sized for the hand of that age, `kern/gestaltung/dokumente.md` §4);
  - the page count is plausible (a one-lesson plan of nine pages is a fault; a page limit they named is kept);
  - no leftover `{{…}}`, placeholder, template text or note to yourself; footer and page numbers present;
  - what learners read still works as a black-and-white copy.
- **Slides:** `python kern/tools/folien_check.py <deck>.html --out <temp folder outside the instance>` renders every display step. Exit 1 (content outside the screen, a visible teacher note, an external request, a script error) → fix and run again. Then open `uebersicht.png` and the fullest slides: is each slide readable from the back row at a glance, or is it a wall of text? A slide that is full is split into two; type is never shrunk below the reading floor. And the other way round: does each slide use the screen, with type well above the floor and something to see where it helps (`kern/gestaltung/folien.md` §3 and §5)? Small text in the corner of a white slide is fixed before showing.
- Does it look like something one would gladly hand out and show? Calm, even, generous. If a page looks cramped, crooked or bare, fix the layout.
- No renderer available: read the HTML once more for structure and record `Seiten nicht gesehen` in `pruefung`.

## B. One lesson, one story
Put plan, worksheet, answer key and slides side by side:
- the same tasks with the same numbers and the same wording; the same terms; the same times, social forms and materials;
- everything the plan uses exists: every sheet, card, text, table and slide it names; what the teacher brings is listed in the plan under "Material";
- the phases add up to the lesson length; the time per phase is realistic for this age (handing out, moving, tidying up cost minutes; a discussion with 25 children needs more than two minutes);
- what they asked for is there: read their request once more, wish by wish.

## C. True and solvable
- Solve every task yourself and compare with the answer key; compute every number; an experiment's expected result is what really happens.
- List the statements learners will take as true (facts, definitions, dates, safety statements) and check each; what you are not certain of is checked against a source or marked `[PRÜFEN: …]`.
- Nothing official, quoted or sourced is invented (`kern/regeln.md` §6). `[PRÜFEN: …]` markers are collected under "Noch zu prüfen" on the teacher document.
- Status and declarations describe only what happened: a new document is "Entwurf".
- It fits the age group in language, amount of text and difficulty.

## D. After a change
Check that exactly what they asked for changed, that every other part of the package agrees again (B), re-export, and look at the changed pages or slides once more.

## E. Template fidelity (only in skill `vorlage-ableiten`: probe against their original)
Same page size, orientation and margins (± 0.2 cm); same sections, headings and numbering in the same order; same tables (columns, header labels, width ratios ± 10 %); same font family and sizes (± 1 pt); the example's content reproduced completely; `probe.pdf` has about the original's page count, nothing runs past the right margin, shaded cells keep their colour. Compare `python kern/tools/convert_example.py probe.pdf --facts` with the facts of the original and look at the pages of both side by side. Tell the teacher the result in one line and name what you could not compare.
