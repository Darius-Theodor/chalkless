---
name: bilder
description: Pictures for lessons – drawn SVG for simple structures and objects, a picture the teacher provides inserted into slides or sheets (embedded, offline), and generated illustrations (picture cards, memory sets, busy scenes, posters, slide images) with one consistent style per series – generated with the host's image tool if one is available (way B), otherwise as an English prompt file shown for copying (way A). Pictures are generated only on their wish. Use when they ask for Bild, Bilder, Bildkarte, Wimmelbild, Poster, Illustration, or send a picture for a slide or sheet.
---

# Skill: bilder

## Inputs (from context; questions: `kern/regeln.md` §4)
- Area, purpose (card / memory / scene / poster / slide image / picture on a sheet), where it goes (slides, material), motifs, format (portrait default for cards, landscape for scenes, square for memory), series name (default: the unit slug).

## Choose the way (by what is asked and what you can actually use, never by host name; `kern/regeln.md` §10)
1. **Draw it yourself** when it is a clear structure, a process or a simple object (magnet, worksheet, arrow diagram, timeline): inline SVG in the slide or sheet, in the house hand (`kern/gestaltung/folien.md` §8, `dokumente.md` §4 figures). This is not image generation and needs no prompt file; still only where it carries meaning.
2. **They provide a picture** (a file in `eingang/`, an attachment, a path they name in plain words): copy it to `bereiche/<area>/bilder/<nn>_<slug>.<ext>` and insert it (below). Only their own or freely usable pictures; no recognisable pupils or other people from their school.
3. **They want a generated picture:**
   - **Way B** – an image generation tool is available to you (native or a tool/connector you can call): generate, save the image under the prompt's name, insert it, show it.
   - **Way A** – no such tool: write the prompt file and show each prompt as one copyable block; when they bring the image back, continue with way 2.
   Nothing is generated without their wish; a slide or sheet never waits for a picture (it shows the placeholder).

## Style (ways A and B)
- `vorlagen/bild/bildstil.md` holds the English STYLE block(s). If it does not exist, derive it once: from images they sent (`beispiele/`), their description, and the age group of the area; show it, and save it after their yes. They never have to invent a style; propose one that fits the age group.
- The STYLE block stays identical within a series; only SUBJECT and optional EDIT lines change.

## Steps
1. Ways A/B: per motif write `bereiche/<area>/bilder/<nn>_<slug>.prompt.md` (front matter `titel` in their language, `typ: bild`, `bereich`, `datum`, `status`, `serie`, `format`), followed by the full English prompt in one fenced block: STYLE … SUBJECT … [EDIT …].
2. Way B: generate, save next to the prompt with the same name. Way A: show each prompt as one copyable block with a one-line title in their language; tell them once per series: use one chat in the image tool for the whole series, attach 2–3 earlier images of the series as style references, one prompt per message, save the result into the same folder under the prompt's name (or simply send it here).
3. **Insert, offline.**
   - Slides: embed as a `data:` URI (`<img src="data:image/png;base64,…" alt="<what it shows>">` inside `figure.pic`), photos scaled first to about 1600 px wide with pillow so the deck stays small; or a relative path `../bilder/<file>` when the picture is large and the folder travels with the deck. Never an absolute path or a web address.
   - Sheets: relative path or embedded, as the template does it.
   - Replace the placeholder at that place; then run the check again (`kern/tools/folien_check.py` for slides, `pdf_export.py` for sheets) and look at the affected states or pages.
4. **Placeholder** while a planned or wished picture is missing: a calm neutral area with the motif in words, `Bild folgt: <Motiv>` (slides: `.pic-missing`, see `folien.md` §8). Never a file name, prompt path or template text; the slide or sheet stays usable without the picture.
5. Reference the images in the lesson plan's media column and mark generated ones as AI-generated (rubric A9).
6. Commit `bild <area>: <series> (<n> prompts)` or `bild <area>: <motif> eingesetzt`.

## Rules
- Prompts are English only. Describe what should be present, not what should be absent ("pure white background", "contains no letters").
- Text inside images only for posters; tell them to check every letter.
- No pupil names, photos or recognisable people from their school in any prompt or inserted picture. Nothing frightening for children.
