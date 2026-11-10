# Slide design reference (core)

The slides that come with a lesson: one self-contained offline HTML presentation built from the frame `deck-rahmen.html`. They show the class what the lesson asks of them at this moment – the question, the task, the collection, the result – readable from the back row while the teacher teaches. The lesson plan is the source: nothing on a slide that the plan does not contain, and nothing of the plan's tasks, steps, times or safety notes lost. If the teacher has a template in `vorlagen/praesentation/`, its look wins.

## 1. Build the deck without reading the frame
The frame is 50 KB of mechanics you never change. Do not read it through.
1. Copy it: `cp kern/gestaltung/deck-rahmen.html bereiche/<area>/praesentationen/<file>.html`.
2. Read only two ranges of the copy: lines 1–15 (meta tags, title) and from `<main id="deck">` to `</main>` (grep for the line numbers; four demo beats).
3. Edit: `<html lang>`, the `chalkless.*` meta tags and `<title>`; the contract block `<script type="application/json" id="chalkless-deck">` (`quelle` = relative path of the lesson plan, `titel`, `bereich`, `datum`, `dauer_min`, `beats` = number of slides); the `h1.sr-only`; then replace all demo beats by your own.
4. Deck-specific CSS goes into a new block directly before the line `/* ---------- 4. MECHANICS` : `/* ---------- 3b. THIS DECK ---------- */` with the reading floor (§3) and one comment why. Leave everything from section 4 on, and the script, alone.
5. Check: `python kern/tools/folien_check.py <file> --out <temp folder outside the instance>`; look at `uebersicht.png` and the fullest slides (`kern/pruefung/rubrik.md`).

## 2. Slides, builds, notes
- **One slide per moment of the lesson**, in the plan's order, a title slide first: usually one per phase; a phase with two clearly different moments (task, then results) gets two. A 45-minute lesson has about 6–10 slides.
- **A slide carries one thing.** At most about six short lines or four task steps at the reading floor. More than that is two slides, not smaller type. Short sentences; the teacher talks, the slide anchors.
- **Builds** (`data-build="1"`, `"2"` … without gaps; equal numbers appear together) where the phase unfolds: impulses one after another, a collection that grows with the conversation, the rule after the class has formulated it, the solution after the task. A solution never shows before its build. Steps pupils work through at their own pace all stand from the start. Every state makes sense on its own: no empty frame waiting.
- **Task slides** show the task with the worksheet's number and wording, its steps, and one `.meta` line with what pupils need to act: "Partnerarbeit · 15 Minuten · Arbeitsblatt Aufgabe 1".
- **Teacher notes:** everything for the teacher – clock time, duration, what to do and say, expected answers, when to click, help for those who struggle – goes into one `<aside class="notes" hidden>` per slide. Never on the slide: no stage directions, no phase numbers, no words of your own process, no file names.
- **Line breaks** where they matter: `<br>` preceded by a space, at a sentence boundary. `&shy;` in long compounds. Never rely on automatic hyphenation.

## 3. Legibility
Sizes are design px on a 1920 × 1080 canvas; the frame scales them. Set the sizes for the class in block 3b: `:root { --fs-body: calc(50 * var(--u)); --fs-row: calc(56 * var(--u)); }`.

| Readers | Start with `--fs-body` / `--fs-row` | Floor (never below) |
|---|---|---|
| first readers, grades 1–2 | 58 / 64, very few lines per slide | 52 |
| grades 3–4 | 50 / 56 | 44 |
| grades 5–7 | 46 / 52 | 40 |
| grade 8 and older | 44 / 48 | 36 |

**The floor is the lower limit, not the normal size.** Start with the larger values; if the fullest slide does not fit, split it or shorten it first, and only then go down – never below the floor. (For comparison: 36 on this canvas is what an 18 pt line is on an ordinary presentation slide.)

**Use the canvas.** In its end state a slide's content reaches into the lower half of the screen. Two or three short lines are never left small in the top left corner of an empty screen: set them as `.lead` (one sentence) or `ul.rows.rows--lead` in a `.body.body--center`, or put a drawing beside them (`.body--pic`). Look at `uebersicht.png` from a distance: mostly white slides with a little text at the top are not finished.

Everything pupils must read to act is at least the floor. Title 112, slide headline 72, the question or sentence of the day 52 (`.lead`) stay as the frame sets them. Orientation-only text may be 32 (`.secondary`). One text block at most about 60 characters wide. Light canvas, one accent that marks only "just appeared"; no colour as the only carrier of meaning; no light-grey text. Never go below the floor to make content fit: split the slide, use builds, or shorten the wording.

## 4. Markup (copy these shapes)
Every slide: `<section class="beat" id="bN" data-title="…">` with `.head` (an `h2`), `.body`, the notes, and `<span class="folio" data-ui>N / M</span>`. Ids `b1`, `b2` … in order.

```html
<!-- title slide -->
<section class="beat beat--title" id="b1" data-title="Titel">
  <div class="title">
    <div class="head"><h1>Titel der Stunde als Frage?</h1><p class="title__sub">Untertitel in drei Wörtern</p></div>
    <figure class="pic pic--title" aria-hidden="true"><svg viewBox="0 0 480 340">…</svg></figure>  <!-- optional -->
  </div>
  <p class="title__meta secondary">Fach · Klasse · Wochentag, Datum</p>
  <aside class="notes" hidden>…</aside><span class="folio" data-ui>1 / 8</span>
</section>

<!-- impulses, then the key question on the base line -->
<div class="body">
  <ul class="rows"><li data-build="1">…</li><li data-build="2">…</li></ul>
  <p class="lead" data-build="3">Die Leitfrage?</p>
</div>

<!-- task in steps, with the line pupils need to act; optional extension in a star box -->
<div class="body">
  <ul class="tasks">
    <li><span class="tasks__n">1</span> <span>Erster Schritt.</span></li>
    <li><span class="tasks__n">2</span> <span>Zweiter Schritt.</span></li>
  </ul>
  <p class="meta">Partnerarbeit · 15 Minuten · Arbeitsblatt Aufgabe 1</p>
  <div class="star" data-build="1"><p><span class="star__glyph">★</span> Fertig? …</p></div>
</div>

<!-- task beside a drawing: text left (.top / .low), picture right -->
<div class="body body--pic">
  <ul class="tasks top">…</ul>
  <figure class="pic" aria-hidden="true"><svg viewBox="0 0 440 440">…</svg></figure>
</div>

<!-- collecting into two columns; rows fill in the order of the conversation -->
<div class="sort">
  <div class="sort__col"><h3 class="sort__h" data-build="1">dafür</h3>
    <ul class="sort__list"><li data-build="2">…</li><li data-build="4">…</li></ul></div>
  <div class="sort__col"><h3 class="sort__h" data-build="1">dagegen</h3>
    <ul class="sort__list"><li data-build="3">…</li></ul></div>
</div>
```

| Pattern | Markup | Use |
|---|---|---|
| question / sentence of the day | `p.lead`; several in `div.leads` | impulse, key question, rule to remember |
| rows | `ul.rows > li`, or single `p.row`, `p.goal` | statements, homework, outlook; run-in bold lead `<b>Hausaufgabe:</b>` |
| word cards | `ul.body.words > li > span` | a few big words that grow with the conversation |
| object cards | `ul.cards > li` | names of things on the table, three columns |
| task steps | `ul.tasks > li > span.tasks__n + span`; `ul.tasks.tasks--plain` for separate tasks; a single task as `p.task-text` | work assignments |
| box, star box | `div.box`, `div.star` with `span.star__glyph` | hint, extension task |
| sorting | `div.sort > div.sort__col > h3.sort__h + ul.sort__list` | two or three columns |
| gap sentence | `div.merk > p.merk__s` with `<span class="gap gap--1"></span>`, then inside `.merk` a `div.fills > span.fill.fill--1[data-build]` per gap (up to three) | a rule completed after the class formulated it |
| quotation with source | `div.voices > figure.quote > blockquote > p` + `figcaption.quote__by` | short source texts, verbatim, the source always named |
| term – definition | `div.defs > p.defs__row > b.defs__t + span` | terms the class works out |
| checklist | `ul[data-check] > li > button[type=button role=checkbox aria-checked=false tabindex=0]` | criteria to tick |
| table | `table.tbl`, at most three columns | only when the content is a table |
| centred single block | `div.body.body--center` | one paragraph or list alone on a slide |
| missing picture | `<div class="pic-missing" role="img" aria-label="Bild folgt: …">Bild folgt: <Motiv></div>` | only for a picture the teacher wished that is not there yet |

Signal rule, carried by the frame: the newest build is marked (a bar beside unframed elements, an accent border on framed ones). Never set `transition` on an element with `data-build`. If a pattern does not render as expected, grep `deck-rahmen.html` for its class instead of reading the file; the two example decks in `beispiele/` (`folien-grundschule.html`, `folien-sekundarstufe.html`) are synthetic and large – grep them for a pattern, never copy their content.

## 5. Pictures
A deck of text alone looks bare, and a class looks at a picture before it reads a line. Go through the slides and ask of each: is there something to *see* here that helps – the object, the set-up of the task, the two things being compared, a timeline, a diagram of the result? Then draw it beside the text (`.body--pic`), on the slide where it helps understanding, not only on the title. Usually several slides of a deck carry a drawing or a structured pattern (sorting, cards, table, arrows). Still no decoration: a picture that shows nothing of the content is left out. Simple things you draw yourself as inline SVG: ink strokes 5–7 wide with round joins (`stroke="var(--ink)"`), one fill grey (`var(--grey)`), big simple shapes that read from the back row, labels inside a drawing at the floor size or larger. A picture the teacher provides is embedded as a `data:` URI or referenced relatively from the area's `bilder/` folder; never a web address. Generated images only when they ask (skill `bilder`).

## 6. Offline and print
One file: CSS and script inline, installed fonts only, no request to the network (the check counts every external request as an error). It opens from any folder in any browser. No PDF is needed; a print version (`folien_check.py … --pdf`, A4 landscape, one slide per page) or PowerPoint only when they ask.

## 7. Do not
- No notes, stage directions, solutions before their build, file names or template text on a slide.
- No slide the plan has no moment for; no task that differs from the worksheet.
- No wall of text; no shrinking below the floor; no nearly empty slide with small type.
- No decoration, clip art, external resource or web font.
