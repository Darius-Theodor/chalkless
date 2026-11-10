---
name: recherche
description: Create or extend a framework package rahmen/<id>/ for a region × school type – curriculum excerpts verbatim, school calendar, local terms, legal duties (privacy, AI declaration), training rules and standard templates – each building block with source and verification status. Use when setup finds no package, when a needed building block is missing or unverified, or at a school-year transition (new calendar).
---

# Skill: recherche

The output is never "the truth about region X". It is a package that says per building block what is verified, what was found but not checked, and what is missing.

## Steps
0. Research usually takes more than two minutes: the waiting-time sentence comes first (`kern/regeln.md` §1).
1. Read `profil/rahmen.md` (country, region, school type, status) and `profil/lehrkraft.md` (subjects, grades). Research only what their areas need now; extend later.
2. Create `rahmen/<id>/` with `paket.md` (skeleton below) if missing.
3. For each building block, prefer primary sources (ministry, state institute, official gazette, examination regulations, the training institution itself). Use web search/fetch if the host has it; otherwise ask them for the document or link.
   | Block | File | Notes |
   |---|---|---|
   | Curriculum per subject and grade band | `lehrplan/<fach>-<stufe>.md` | verbatim excerpts with headings as in the source; record licence and whether AI use is allowed; keep structure terms of the source (competences, standards, content areas) |
   | School calendar of the current school year | `kalender/<schuljahr>.md` | holidays, public holidays, first/last school day; section "Schuleigene Termine" filled from U5 |
   | Local terms and citation | `begriffe.md` | what "Stunde", "Einheit", "Sequenz/Reihe/Vorhaben" mean locally; how curriculum items are cited; common abbreviations |
   | Legal duties | `recht.md` | privacy rules for AI tools at school, AI declaration duties for assessed documents, copyright notes |
   | Training rules (only if status `in_ausbildung`) | `ausbildung.md` | required documents, visits, exams, page limits, declarations; who issues them |
   | Standard templates (only if they have no example) | `standardvorlagen/<typ>.md` | a documented starting point, marked as such, with its source |
4. Status per block: `geprüft` only if you read the primary source yourself and the file matches it verbatim; `gefunden, ungeprüft` for secondary sources or sources you could not read fully; `fehlt` if nothing reliable was found. Never upgrade a status without re-reading the source.
5. Write the report table into `paket.md` and show it to them: "Das weiß ich sicher / das solltest du prüfen" (blocks with status other than `geprüft`, each with what they could check and where).
6. Commit `framework: <id> <blocks added>`.

## paket.md skeleton
```
# Rahmen-Paket <id>
- land: … · region: … · schulform: … · erstellt: YYYY-MM-DD · zuletzt ergänzt: YYYY-MM-DD

| Baustein | Datei | Quelle (Herausgeber, Titel, URL/Fundstelle) | Stand der Quelle | Geltung | Nutzung/Lizenz | Status | geprüft am |
|---|---|---|---|---|---|---|---|

## Das weiß ich sicher / das solltest du prüfen
| Baustein | Status | Was du prüfen kannst |
|---|---|---|
```

Write the report heading in their language and form of address (e.g. "das sollten Sie prüfen" when they are addressed with Sie).

## Rules
- Verbatim means verbatim: keep wording, punctuation and numbering; only normalise line breaks. Mark omissions with "[…]" (`kern/regeln.md` §6).
- Never fill a gap with plausible text. A missing block stays `fehlt`, and documents get `[PRÜFEN: <block>]`.
- Variation is local: templates, phases, terms and goal styles differ by training institution and even by mentor, not only by region. Do not present one institution's habit as a regional rule.
- No region is the default. Nothing from another package is copied unless the source says it applies.
