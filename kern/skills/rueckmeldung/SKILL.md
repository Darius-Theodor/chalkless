---
name: rueckmeldung
description: Apply a correction to an existing document, log it, and store standing preferences only with their consent (they say immer/nie, or say yes when a repeated correction prompts the question) – visibly and reversibly; layout wishes change the template. Use when they say immer/nie so, vergiss das, want a layout change to their template, or paste feedback from a mentor or examiner. An ordinary change to a document needs no skill (kern/regeln.md §4).
---

# Skill: rueckmeldung

## Steps
1. **Target.** The document they name, else STAND `letztes` of the area. If genuinely ambiguous, ask one question. Feedback with several points (e.g. from a mentor) is a long request: carry out every point, or name it as not done with the reason (`kern/regeln.md` §4).
2. **Content change:** edit the HTML content only; keep everything else byte-identical. If an export exists and they have not marked it as their own final version, re-export. Then look again at the affected pages or display steps (`kern/pruefung/rubrik.md` D) and update the `pruefung` line in the file. Set meta `geaendert`. If the document is a lesson plan with slides (a deck in `praesentationen/` whose `quelle` is this plan), update the deck in the same turn (skill `praesentation` steps 2–6, `folien_check.py` again), and make worksheet and answer key agree as well.
   **Layout change** ("Spalte breiter", "Überschrift fett", "immer mit Deckblatt"): change `vorlagen/<typ>/stil.css` / `vorlage.html` (and `export.py` only if they actually use Word copies; otherwise leave it untouched), add a row to `herkunft.md` (`Vorliebe`, or `Vorgabe` with issuer), raise `version`. Apply to the current document too. Commit `template: <typ> v<n> <change>`.
3. **Log:** append to `gedaechtnis/feedback-log.md`:
   ```
   ## YYYY-MM-DD · <area> · <typ> · <slug>
   Rückmeldung: "<their words, or the mentor's words verbatim>"
   Änderung: <what you changed>
   Regel: keine | gefragt (<scope>) | bestätigt (<scope>) | abgelehnt (<scope>)
   ```
4. **Preference** (`kern/regeln.md` §5, line format `kern/konventionen.md` §5):
   - explicit standing wish → `[bestätigt]` line; reply "Gemerkt: <rule>. Sag ‚vergiss das', wenn nicht." An older `[bestätigt]` line about the same thing for that scope becomes `[überholt]` in the same step and is named in the reply (§5).
   - same correction a second time → check whether a standing preference makes sense (§5); if so, ask once as the last sentence of this reply "Soll ich das künftig immer so machen?". Store `[bestätigt]` only after their yes; no, no answer or evasive → store nothing, log `abgelehnt`, do not ask again for this correction.
   - "vergiss das" → set the line to `[überholt]`, reply "Vergessen.", and withdraw it from templates and STAND (§5).
   - one-off wish → no line.
5. **Mentor/examiner feedback:** log verbatim. Rules derived from it are `[bestätigt]` only if they say they apply generally; requirements that belong to the template become `Vorgabe` rows in `herkunft.md` with that issuer.
6. Remove the item from `review/offen.md` if it was queued. Status `geprüft` if they say it is fine now.
7. Commit (`<typ> <area>: <slug> (<status>)`, the updated deck in the same commit and, if changed, `memory: <rule> (<state>)`). Reply in two lines: what changed, and which rule applies from now on, if any.

## Core
- A correction or preference is applied in the instance (document, template, `vorlieben.md`), never in the core.
- A wish that only a core change can fulfil follows `kern/regeln.md` §10: offer the closest instance alternative, and if they still want it, the very clear core-change notice and one yes/no question. No clear yes → no core change.

## Never
- Never rewrite or delete earlier log entries; add a dated correction instead.
