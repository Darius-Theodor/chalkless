# Document design reference (core)

The design repertoire for everything printed: lesson plans, written drafts, worksheets, answer keys, help cards, overviews. It applies when the teacher has no template of their own for the document (`vorlage: standard`); when they brought an example, their format wins (`vorlage-ableiten`), and a requirement of school or seminar wins over everything (`kern/regeln.md` §4). Slides: `folien.md`.

The goal is a page one would gladly hand out: calm, even, generous, readable at a glance, and it survives the school copier.

## 1. How to build a document
1. Start from the matching example in `beispiele/` – read that one file, not all of them: `kurzentwurf.html` (lesson plan: head data, short sections, Verlaufsplan table on a landscape page), `arbeitsblatt.html` (worksheet with task blocks, tip box, answer grid, then the answer key as a teacher page), `loesung-hilfekarte.html` (help cards to cut out, answer key for open tasks), `sequenz.html` (overview of several lessons). The examples are synthetic: take structure and classes, never their content, dates or references. Their comments mark STRUCTURE (keep), RECIPE (adapt) and CONTEXT (decide for this class).
2. Write the file with `<link rel="stylesheet" href="../../../kern/gestaltung/standard.css">` (three levels up from `bereiche/<area>/<folder>/`) and put document-specific CSS in a `<style>` after it. You do not need to read `standard.css`; §6 lists its classes.
3. Export and look at every page (`kern/pruefung/rubrik.md`), fix, look again.
4. When the document is finished, make it self-contained: `python -c "import re,sys,pathlib as P; f=P.Path(sys.argv[1]); c=P.Path('kern/gestaltung/standard.css').read_text(encoding='utf-8'); f.write_text(re.sub(r'<link[^>]*standard\.css[^>]*>', lambda m: '<style>\n'+c+'\n</style>', f.read_text(encoding='utf-8')), encoding='utf-8')" <file>.html` – then export the PDF once more.

## 2. Principles
- **Content before layout.** Answers are computed, not copied; all parts of a package agree; the phases add up.
- **Black and white.** Black text on white; greys only for secondary text and rules. Colour or a grey shade is never the only way to tell things apart: every distinction also has a word, a symbol, a position or an outline. Nothing a learner reads is light grey. No fills behind text, no zebra rows, no shadows, no gradients.
- **One family, two weights.** Segoe UI (fallback "Noto Sans", Arial), regular and semibold. Hierarchy comes from size, weight, rules and whitespace, never from colour or decoration. Body text left-aligned, never justified. Two heading levels are enough.
- **Keep things whole.** A task block, a box, a card, a table row never splits across pages; table headers repeat on every page. A row taller than half a page is split by you into two rows, the second starting with "Fortsetzung".
- **Never save space by shrinking type or dropping content.** Too long means: shorten the wording, restructure, or use another page.
- **Self-contained.** No web fonts, no external images, nothing fetched.
- **Pictures only where they carry meaning**, drawn as simple monochrome inline SVG (an object, a structure, a process). No clip art, no emoji (☐ U+2610 and ★ U+2605 are fine; ⚠ and ⭐ may print as colour emoji – use the stylesheet's `.box.safety` or SVG).
- **No cover page** unless the school or seminar asks for one or the document is long (8 pages and more).
- **No boilerplate:** no declaration that someone checked or approved, no AI declaration unless a requirement asks for it.

## 3. Teacher documents (`<body class="teacher">`)
- **Page:** A4 portrait, margins 16/18/18/18 mm; a wide table goes on a landscape page (`<section class="landscape">`). Type 10 pt / 1.36; 9.5–11 pt by density.
- **Shape:** title block (`header.sec.title-block`: document type as label, `h1`), head data as a term/value grid (`dl.head-data`: subject, class with size, date, time, topic, where it stands in a series), then label-column sections (`.sec` > `.label` + `.body`): the left edge navigates.
- **Lesson plan (the everyday form):** head data · what the class already knows (two sentences) · the goal of the lesson (one main goal, two to four things pupils can do at the end, written as observable actions) · material list (what you built, what the teacher brings, how many copies) · the Verlaufsplan · at the end homework/reserve and "Noch zu prüfen". Usually 2 pages.
- **Verlaufsplan** (`table.t-table` with `colgroup` in mm that sums to the printable width: 174 mm portrait, 261 mm landscape): columns Zeit · Phase · Unterrichtsgeschehen (what the teacher does and says, key impulses in quotation marks, what pupils are expected to answer) · Sozialform · Material/Medien; a didactic comment column when the plan is for a visit. First column `td.key` with the clock time and the duration as `.sub`; a `tr.sum` row at the end shows that the minutes add up. No vertical rules. Name the task numbers of the worksheet and the slide that is on ("Folie 4") in the rows where they are used.
- **Written draft for a visit or exam (Unterrichtsentwurf):** the sections the seminar asks for, in its order and with its names – typically Lerngruppe/Lernvoraussetzungen, Sachanalyse, didaktische Überlegungen, methodische Überlegungen, Lernziele, Verlaufsplan, then material in an appendix. Prose in portrait with `h2.chapter` per section, the Verlaufsplan on a landscape page. A page limit they name is a requirement: count the pages of the PDF; the appendix (worksheet, cards) is a separate file and does not count. Write for the reader who assesses: concrete to this class and this lesson, no general textbook pedagogy. Where the draft needs something only the teacher knows (the group, prior lessons), write what they told you and leave one short marked gap per open point (`[PRÜFEN: Lernstand der Gruppe]`) instead of inventing a class; ask for these facts in your reply.
- **Status and page numbers:** "Entwurf" bottom left, "Seite X von Y" bottom right come from the stylesheet; the running head is typed once in the document's `<style>`: `@page { @top-left { content: "<Dokumentart> · <Titel>"; } } @page :first { @top-left { content: none; } }` (a landscape section: `@page landscape { … }`).
- **`[PRÜFEN: …]`:** `<span class="pruefen">[PRÜFEN: Lehrplanbezug]</span>` at the spot, all of them once more at the end under "Noch zu prüfen". Keep the marker short (two to four words) and use it only for official texts, sources, unverified facts and unknown facts about the class – assumed dates, times and class sizes are written plainly with "(angenommen)" (`kern/regeln.md` §6). The head data of a document carries no marker boxes for assumptions. For a whole table column use one `.table-note` under the table.

## 4. Pupil documents (`<body class="pupil">`)
- **Page:** A4 portrait, 15/15/18/15 mm; footer with the title left and a plain page number right (`@page pupil { @bottom-left { content: "<Titel> · Arbeitsblatt"; } }`).
- **Type by readers** – set once with `body.pupil { font-size: … }` in the document's `<style>`; everything scales with it:

| Readers | Body | Writing lines | Notes |
|---|---|---|---|
| grades 1–2 | 15–16 pt | 12–14 mm apart | one sentence per task; a pictogram per task (ear, pencil, eye); very little text |
| grades 3–4 | 13 pt | at least 10 mm apart | short sentences, one step per sentence |
| grades 5–8 | 12 pt | 9–10 mm | |
| grade 9 and older | 11–12 pt | 8–9 mm | a dense source text may be 11 pt |

- Lines of text no longer than about 75 characters, line height at least 1.35.
- **Head:** `.name-line` (Name, Datum), then `.title-block` with `h1` and an optional small SVG icon that carries meaning.
- **Task block** `.task` = `.badge` (the task number, white on black) + `.content` with `h2` and `.instruction` (what to do, as a full sentence). An extension task gets `.badge.star` with ★. Number tasks 1, 2, 3 – the plan and the slides use the same numbers.
- **Room to write is part of the task.** Give every answer the space a child of that age needs: `.lines` (ruled lines, 12 mm apart: `<ul class="lines"><li><span class="rule"></span></li>…</ul>`; three to five for a sentence answer in primary school), `.box.draw` (an empty framed area with a set height), a full-grid table `table.p-table` with rows 10–12.5 mm high when pupils write into cells, `.checkbox` ☐ for ticking, `.gap-text` with `.blank` gaps and a `.word-box` for the word bank. When in doubt, more room – a second page is better than cramped lines.
- **Boxes:** `.box.tip` (a hint: it points to the next step or shows a worked example with other numbers, never the answer), `.box.safety` (at most three short sentences).
- **Source text for pupils:** a framed block with line numbers every fifth line when tasks refer to lines; above it one line saying what the text is, who wrote it and when; below it the source. Short enough for the class in front of you. A text you wrote yourself says so ("Für diese Stunde geschriebener Text").
- **Help card / Tippkarte** for those who need support: a small card (`.cards`, 2 × 2 per A4 with dashed cut lines, or one half page) with the next step, a picture of the material or a worked example – as its own page in the material file, with a print note for the teacher.
- **Answer key:** in the same file after the pupil pages, as `section.teacher-insert` that starts with the `.band` "Nur für die Lehrkraft" and a new page. It repeats each task number with the expected answer – for open tasks what a good answer contains – and notes how many copies to print and what to cut.

## 5. Limits of the PDF export
| Limit | Do instead |
|---|---|
| no automatic hyphenation | `&shy;` in long compounds in narrow columns and labels |
| running head and footer cannot read the title | type it once in the document's `<style>` (§3, §4) |
| no per-part page counters | plain page numbers on pupil pages; separate files when numbering matters |
| no real footnotes | superscript numbers and an "Anmerkungen" block |
| no table of contents numbers | type them, re-check after layout changes |

## 6. Classes of `standard.css`
| Purpose | Classes |
|---|---|
| Registers and pages | `body.teacher`, `body.pupil`, `.landscape`, `.teacher-insert`, `.cards`, `.page-break`, `.keep` |
| Teacher structure | `.sec` > `.label` (`.nr`) + `.body`; `.title-block`; `dl.head-data` (`.two-col`); `h2.chapter`; `.closing`; `.caption`; `.band` |
| Teacher tables | `table.t-table` (`.compact`), `td.key`, `.sub`, `tr.sum`, `tr.buffer`, `tr.holiday`, `tr.group`, `.marker`, `.table-note` |
| Pupil structure | `.name-line` (`.field`, `.rule`), `.title-block` (svg, `h1`, `.subtitle`), `.task` > `.badge` (`.star`) + `.content` (`h2`, `.instruction`) |
| Pupil elements | `table.p-table`, `.checkbox`, `.lines`, `.box` (`.tip`, `.draw`, `.safety`, `.box-title`), `.word-box`, `.gap-text`, `.blank`, `.pill` (`.outline`), `.card` > `.card-inner` (`h3`, `.steps`, `.card-meta`) |
| Shared | `.pruefen`, `.secondary`, `.nums`, `.nowrap`, `.center` |

If a class does not do what you expect, grep `standard.css` for it instead of reading the whole file.
