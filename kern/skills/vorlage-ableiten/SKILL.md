---
name: vorlage-ableiten
description: Derive a reusable template for one document type from the teacher's example (pdf/docx/image) or from a standard template – herkunft.md, vorlage.html with fixed ids, stil.css in the print look of the original, pruefung.md – then rebuild the example from the template, print it to PDF and compare it with the original. Use during setup stage V, when a new document type or a new example arrives, or when they want a template changed fundamentally.
---

# Skill: vorlage-ableiten

Goal: after this skill, documents of this type are written as content only. Layout is never written again; the PDF is printed from the HTML.

## Inputs
- Document type (`profil/pflichten.md` row), their example(s) from `beispiele/` or `eingang/`, requirements from P2 (issuer).
- No example: start from the core default – `kern/gestaltung/standard.css` with the structure of the matching example in `kern/gestaltung/beispiele/` and the judgment rules in `kern/gestaltung/dokumente.md` – or from a package `standardvorlagen/` entry; all features are `Beispiel` except what P2 requires (`Vorgabe`) or they confirm (`Vorliebe`). If they already have a derived template of another type, you may carry its confirmed page setup and type family over for a consistent look [context]; record that in `herkunft.md` and say it in one sentence.

## Steps
0. Deriving a template usually takes more than two minutes: the waiting-time sentence comes first (`kern/regeln.md` §1).
1. **Inspect.** `python kern/tools/convert_example.py <file> --facts` → text, page size, orientation, margins, fonts, table column widths. Read the text fully; look at the layout (PDF pages, the docx structure, or the image).
2. **List features** the template must reproduce, grouped: page (size, orientation, margins), header block (fields), sections in order with their headings and numbering, tables (columns, widths, header row), wording conventions (how goals are phrased, time notation, phase names, abbreviations, legend), fixed text (declarations, signatures), variants. Use their words for headings.
3. **Ask V1–V3 in one message** (`kern/interview/katalog.md`): one numbered list of the salient features, they answer per line "Vorgabe (von …) / Vorliebe / Beispiel". Do not list trivial features (font size of body text) unless they look deliberate.
4. **Write `vorlagen/<typ>/`:**
   - `original.<ext>`: copy of the example.
   - `herkunft.md`: header `version: 1 · abgeleitet: <date> · aus: <file>`, then a table `| Merkmal | Ausprägung | Herkunft (Vorgabe/Vorliebe/Beispiel) | Quelle | Datum |`. Add a short "Schreibregeln" list for content (goal phrasing, time notation, language register) derived from the example.
   - `vorlage.html`: complete HTML document with the `chalkless.*` meta tags (placeholders), a link or inlined copy of `stil.css`, and the structure with `{{placeholder}}` text. Every section and every table gets a stable `id` (`kopf`, `ziele`, `verlauf`, …); table columns get `<col>` elements in a `<colgroup>`. Variants: mark optional blocks with `data-variante="<name>"`.
   - `stil.css`: the print look of the original. `@page { size: …; margin: … }` exactly as the original; body font family and size, line height, table borders, header row shading with `print-color-adjust: exact`, column widths in cm (the sum must fit the printable width), `break-inside: avoid` for table rows where the original keeps rows together, `thead { display: table-header-group }` if the header row repeats. On screen: white page of page width on grey background; under `@media print` remove background, shadow and screen padding so `@page` margins apply.
   - `pruefung.md`: type-specific checklist (sections present, columns present, time arithmetic, goal phrasing, mandatory declarations from `Vorgabe` features).
5. **Rebuild test.** Fill `vorlage.html` with the content of their example → `vorlagen/<typ>/probe.html`, then `python kern/tools/pdf_export.py vorlagen/<typ>/probe.html` → `probe.pdf`. Compare against the original with `kern/pruefung/rubrik.md` section "Template fidelity" (facts of both PDFs via `convert_example.py --facts`; page images of both via `pdf_export.py --png … --out <temp folder>`, looked at side by side) and fix the template, not the probe, until it passes. Record the comparison in `herkunft.md` under `## Vergleich mit dem Original`: date, template version, one line per criterion C1–C7 with ✓, ✗ (what differs and why it stays) or "nicht prüfbar" (why). The page images stay in the temp folder; the record names only what you saw. Report the same criteria in the reply.
6. **Confirm (V4).** Show them where to look (`probe.html` in the overview, or `probe.pdf`), one question: "Passt die Vorschau so? Dann nehme ich sie als Vorlage." On yes: commit `template: <typ> v1 derived from <file>`. On a change request: fix layout files, raise `version` in `herkunft.md`, repeat 5–6.

## Word copies (only on request)
PDF is the hand-in format. If they say they regularly need an editable Word file of this type, add `vorlagen/<typ>/export.py`:
```python
"""Export <typ> documents (HTML → .docx) on request. Generated once; afterwards only executed."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "kern" / "tools"))
from html_export_base import PageSetup, export_docx  # noqa: E402

HERE = Path(__file__).resolve().parent
PAGE = PageSetup(width_cm=21.0, height_cm=29.7, margins_cm=(2.0, 2.0, 2.0, 2.0),
                 font="Arial", size_pt=11, line_spacing=1.0)
COLUMNS = {"verlauf": [1.4, 2.6, 12.0, 2.8, 3.4]}   # table id -> column widths in cm
BASE = HERE / "original.docx"                        # only if the original is a .docx

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        src = Path(arg)
        export_docx(src, src.with_suffix(".docx"), page=PAGE, columns=COLUMNS,
                    base_docx=BASE if BASE.exists() else None)
```
Run: `python vorlagen/<typ>/export.py bereiche/<area>/<folder>/<file>.html`. Without `export.py`, `python kern/tools/html_export_base.py <file>.html` gives a generic Word copy. Say once that the Word layout is approximate.

## Rules
- Never "improve" their format. Reproduce it; ask before deviating. Sources that disagree follow `kern/regeln.md` §4 (institution > wish of today > stored preference > their template > reference): a `Vorgabe` beats their example, a `[bestätigt]` line in `gedaechtnis/vorlieben.md` beats a `Beispiel` feature, and the core reference fills only what the example leaves open. If their example contradicts a requirement of the institution, the requirement wins and you name the conflict in one sentence.
- A `Vorgabe` without a named issuer is recorded as `Vorliebe` (`ableitung.md` A7).
- No pupil data from the example goes into the template or the probe; replace names with neutral placeholders.
- If no Edge/Chrome/Chromium is available (`python kern/tools/pdf_export.py --check`): write the template anyway, note "PDF-Export: im Browser drucken" in `herkunft.md`, and tell them once how to print the HTML to PDF themselves.
