# Conventions (core)

## 1. Folders
```
profil/        rahmen.md, lehrkraft.md, pflichten.md, stil.md, checks.md; werkzeuge.md (written by the tools check)
vorlagen/      one folder per document type they brought an example for (§3)
bereiche/      one folder per class × subject: <klasse>-<fach>/ (lowercase ASCII, hyphens: 3b-hsu, 8c-geschichte)
               with STAND.md and the sub-folders in use:
               stunden/ material/ praesentationen/ sequenzen/ jahresplan/ bilder/
gedaechtnis/   vorlieben.md, feedback-log.md
review/        offen.md
eingang/       drop folder for new files (§8)
beispiele/     processed originals, read-only reference
archiv/        areas moved at a transition
rahmen/        <id>/ – framework package (§6)
verlauf/       the history, only on a host that allows no .git folder (written by git through
               kern/tools/verlauf.py; never edit, never delete)
```

## 2. Documents
- One HTML file per document, saved in the area: `stunden/` (lesson plan or written draft, typ `stunde`), `material/` (worksheet with answer key, help cards; typ `material`), `praesentationen/` (slides; typ `praesentation`), `sequenzen/` (overview of several lessons; typ `sequenz`).
- **File name:** `YYYY-MM-DD_<typ>_<slug>.html`; the date is the day of the lesson (if they gave none, the next fitting school day; say the assumption). Slug: lowercase ASCII, hyphens, at most 40 characters. **The parts of one lesson share date and slug**, so the package is recognisable: `stunden/2027-03-17_stunde_magnete.html`, `material/2027-03-17_material_magnete.html`, `praesentationen/2027-03-17_praesentation_magnete.html`.
- **PDF** is the hand-in and print format of documents: `python kern/tools/pdf_export.py <file>.html` writes `<file>.pdf` next to it. Re-export after every change. Slides need no PDF. Word (`kern/tools/html_export_base.py`) or PowerPoint only when they ask. An export they edited themselves is theirs: meta `export: eigene-endfassung`, never overwritten.
- **Metadata** in the HTML `<head>`, one tag per field: `<meta name="chalkless.<field>" content="…">`.

| Field | Required | Values |
|---|---|---|
| `titel` | yes | document title in their language |
| `typ` | yes | `stunde`, `material`, `praesentation`, `sequenz`, `jahresplan`, `bild` |
| `bereich` | yes | area folder name |
| `datum` | yes | `YYYY-MM-DD` |
| `status` | yes | `entwurf` → `geprüft` (they say it is fine) → `verwendet` (they taught with it) |
| `vorlage` / `vorlage_version` | yes | their template folder and its version; `standard` / `0` for the core default layout |
| `pruefung` | yes | one line, what you looked at and what stays open, e.g. `Seiten angesehen, Aufgaben nachgerechnet; offen: Lehrplanbezug` |
| `stunde` | parts of a package | relative path of the lesson plan this part belongs to |
| `sequenz`, `teil` | no | relative path of the overview this lesson belongs to, and its number in it |
| `variante` | no | e.g. `unterrichtsbesuch` |
| `geaendert` | no | `YYYY-MM-DD – what` (latest change) |
| `export` | no | `pdf` once exported; `eigene-endfassung` |

- Brain files (profil, gedaechtnis, STAND, rahmen) are Markdown with normal relative links.

## 3. Templates (`vorlagen/<typ>/`)
Only when the teacher brought an example of their own format (skill `vorlage-ableiten` writes `original.*`, `herkunft.md`, `vorlage.html`, `stil.css`, `pruefung.md`). Without one, the core design reference applies (`kern/gestaltung/`, meta `vorlage: standard`). A template is changed only through skill `rueckmeldung`, never while writing a document.

## 4. STAND.md (one per area, a short note of where the area stands)
```
# Stand: <area>
- schuljahr: 2026/27
- sequenz: [<title>](sequenzen/<file>.html) – Teil <n> von <m>     (or –)
- naechstes: <what comes next, one line>
- letztes: [<title>](stunden/<file>.html) · <status>
- offen: <open points, one line, or –>
- aktiv: –
```
Update `letztes`, `naechstes` and `offen` when a package or a change is finished. Keep the keys of the skeleton (`kern/instanz-vorlage/bereich/STAND.md`); `aktiv` stays `–` and the section `## Spur` stays empty – no time log is kept. When a lesson follows another, `letztes` and the earlier files of the area tell you what the class already did.

## 5. Preference line (`gedaechtnis/vorlieben.md`)
`- YYYY-MM-DD (<source>) [bestätigt|überholt] (<scope>): <rule in one sentence>.`
Scope: `alle`, a document type, an area, or `<area>/<typ>`.

## 6. Framework package (`rahmen/<id>/`)
- id: `<country>-<region>-<schooltype>` in lowercase ASCII: `de-by-grundschule`, `de-ni-grundschule`, `de-nw-gymnasium`, `at-wien-volksschule`.
- `paket.md` is the index: one table row per building block (Lehrplan per subject, Kalender, Begriffe, Ausbildung, Recht) with source, location, as-of date and **status** `geprüft` (read in the primary source and checked against it) / `gefunden, ungeprüft` / `fehlt`. Setup writes the index and looks up which curriculum applies (rows `gefunden, ungeprüft` with publisher, title and address; everything else `fehlt`); skill `recherche` fills it later, block by block. The core ships no packages.

## 7. Commits
One line, English: `<typ> <area>: <slug> (<status>)` – for a package `paket <area>: <slug> (entwurf)` –, `change <area>: <slug> (<what>)`, `memory: …`, `profile: …`, `template: …`, `framework: …`, `setup: …`, `core: update to <version>`. Instance paths only.

## 8. Incoming files (`eingang/`)
What they want you to use goes into `eingang/` (or they send it in the chat and you save it there). After processing, move it to `beispiele/<topic>/` and add a row to `beispiele/README.md`.

## 9. Visible markers
`[PRÜFEN: <was>]` is written exactly like this in every language (tools and the overview search for it); in a document in another language explain it once on the teacher page. Status words in a footer follow their language (Entwurf / geprüft / verwendet); the meta values stay German.
