---
name: pilot
description: Pilot logging for a pilot build – active only while the file kern/PILOT exists and profil/rahmen.md has `pilot: an`. Without asking the teacher anything, record one line per setup, finished package and change (how long, how much, what kind) plus technical complications and relief in review/pilot-protokoll.md and the teacher's own sentences of criticism or useful input about the tool in review/pilot-feedback.md; every 14 days or on "Feedback-Datei" write a cleaned export file with kern/tools/pilot_export.py that they hand over themselves. Use after the setup, after every finished package and change, when something fails or takes long, when they comment on the tool (das nervt, das Tool nervt, dauert zu lange, das ging schnell, "könnte das nicht …"), say "Feedback-Datei", or "Protokoll aus".
---

# Skill: pilot

Purpose: the people developing Chalkless learn where the workflow fails and where it helps – with no extra work for the teacher and without any content of their planning or anything about persons leaving the folder. The pilot teacher has agreed to this logging before the handover (`AGENTS.md`, Pilot build); you still say once what you record.

## Switch
- **Active only when both hold:** the file `kern/PILOT` exists (pilot build) and `profil/rahmen.md` has `pilot: an`. A release package has no `kern/PILOT`: then this skill does nothing – no files, no mention, no export – whatever the field says (`check_instance.py` reports a leftover `pilot: an`; set it to `aus` without mentioning it).
- Skill `einrichten` sets `pilot: an` in a pilot build unless they decline. Nothing else ever sets it to `an` – not an update, a transition, a resumed setup or a preference – except their own explicit "Protokoll an".
- **"Protokoll aus"** (or any clear wish to stop it, in any wording or language) **acts at once and for good:** from that sentence on nothing more is appended – not this sentence, not the rest of the current step. Set `pilot: aus`, set the `pilot-export` row in `profil/checks.md` to `erledigt` (no more automatic exports), reply in one sentence ("Gut, ich schreibe nichts mehr mit; die bisherigen Notizen bleiben in review/."), commit `pilot: off`. Existing files stay; they may still ask for "Feedback-Datei" to export what was recorded before.
- **Transparency sentence – exactly once:** when `pilot: an` is first written: as the last paragraph of the setup's closing reply (skill `einrichten`, step 3), then record the row `pilot-hinweis | <date> | – | erledigt | Transparenzsatz gesagt` in `profil/checks.md`. Never repeat it unprompted; say it again only when they ask what you record. If a pilot instance with `pilot: an` has no `pilot-hinweis` row (e.g. a pilot build installed over an existing instance), say it once at the next session start and write the row. Wording (a model of meaning, `kern/regeln.md` §1 – say it in their language and form of address): "Testfassung: Ich notiere nebenbei für die Entwicklung, wo es hakt, wie lange etwas dauert und was du zum Werkzeug sagst – nie Inhalte deiner Planung und nichts über Personen. Ich frage dich nichts dazu und sende nichts; die Notizen liegen in deinem Ordner. Mit „Feedback-Datei“ fasse ich sie dir zum Weitergeben zusammen, „Protokoll aus“ schaltet es ab."

## 1. Complications and relief (technical) → `review/pilot-protokoll.md`
Create the file with the heading `# Pilot-Protokoll` when the first entry comes. Append one line per observation when it happens or at the end of the step:
`- YYYY-MM-DD · <skill> · <typ or –> · <kind>: <one technical sentence>`

Course of the work – one line each, always, so that the people developing Chalkless see how it went without the teacher reporting anything:
- `einrichtung` (once, at the end of the setup): minutes from their sentence to the ready card, where the history lives (`.git`, `verlauf`, none), tools present or missing, curriculum found or not.
- `paket` (after every finished package or single document): the parts with page and slide counts, minutes from their request to your closing reply, number of questions you asked before, number of `[PRÜFEN]` marks.
- `aenderung` (after every change they asked for): what kind – `layout`, `inhalt`, `umfang`, `zeit`, `sprache` or `fehler` (something was wrong) –, minutes, and whether it was done in one go. Only the kind, never what the change said.
- `rueckgaengig` (they asked to undo something): whether it worked.

Times are measured, never guessed. Take the clock time with your first command after their message and again right before your closing reply (`python -c "import time; print(time.strftime('%H:%M'))"`), and write both into the line: `14:02–14:11 (9 min)`. If you did not take the first time, write `Dauer nicht gemessen`; an estimate is worse than none.

Complication kinds: `fehler` (a tool, export or command failed – name the tool and the error class), `quelle` (building block missing or unverified; give the number of `[PRÜFEN]` marks in the document), `rueckfrage-offen` (a question they could not answer → became an assumption), `wartezeit` (a step took longer than about 5 minutes; give the minutes), `korrektur-wiederholt` (the same correction a second time – only the count; the preference question is asked by `rueckmeldung`, this skill never writes `vorlieben.md`), `orientierung` (they asked where something is or how to do something), `abbruch` (a step was interrupted), `grenze` (a wish that needs the core), `host` (something the host lacks or refuses: Python package, browser, git, a folder it does not let you write, a file it does not let you delete, preview, side panel, web search).
Relief kinds: `uebernommen` (a document accepted without a change), `erster-anlauf` (export fine on the first try), `wiederaufnahme` (a new session continued correctly without being told where you were), `zeit` (they mention saved time or effort).

Never: document content, document titles, anything they said about themselves, colleagues, pupils or parents, names, the school or place, anything from relief mode (`kern/regeln.md` §9).

## 2. Their sentences about the tool → `review/pilot-feedback.md`
Create the file with the heading `# Pilot-Feedback` when the first entry comes. No question is ever asked. When they, in the course of normal work, criticise the tool – also in passing ("das Tool nervt", "das dauert mir zu lange", "warum fragst du das schon wieder") –, propose something useful ("könnte das nicht gleich als PDF kommen"), or praise it ("das ging schnell"), append:
`- YYYY-MM-DD · <skill/typ> · [kritik|hinweis|hilft] · "<their sentence about the tool, verbatim>" → <what you did: changed …, noted, nothing to change>`
- Only the sentence about the tool. If it mixes tool and private matters, keep the tool part and mark the cut with "…". Nothing from relief mode.
- Such a sentence is a pilot entry only – it always lands here and **never in `gedaechtnis/vorlieben.md`**. It is not a standing preference (`kern/regeln.md` §5 still decides what goes to `vorlieben.md`, only with their yes), not a correction of a document (`rueckmeldung` still handles that), and not a relief signal (§9 decides that). Those rules run unchanged; the pilot entry is additional.
- Do not thank them for feedback or announce that you noted it; just continue with their request.

## 3. Export → `review/pilot-export_<date>.md`
Every 14 days while `pilot: an` (row `pilot-export` in `profil/checks.md`, checked at session start) and whenever they say "Feedback-Datei":
1. Run `python kern/tools/pilot_export.py --host "<host/app as far as you know it>" --dry-run` first and read every line yourself for names, school, place, pupils, parents and document contents (the block list cannot see these); fix such a line as in step 2, and only then run it without `--dry-run` to write the file. It compiles: core version, host, period, counts (days with entries, documents per type, protocol entries per kind and skill, framework blocks per status, open change requests), the technical protocol lines and every line of `pilot-feedback.md` verbatim – and nothing else. It checks every line against a block list (privacy markers, e-mail addresses, phone-like numbers, titles of their documents).
2. Exit 3 (stopped): it lists line numbers and categories and writes nothing. Look at the named lines in `review/pilot-*.md`; if a line really holds something private, run again with `--schwaerzen` (such lines become `[entfernt: …]`). Never edit earlier pilot lines to make the check pass.
3. Without Python: compile the same sections by hand and check the draft for names, school, place, pupils, parents, document titles and contents, e-mail addresses and phone numbers before saving.
4. Say one sentence: "Die Feedback-Datei für die Entwicklung liegt in review/pilot-export_<datum>.md – gib sie weiter, wenn du magst." If your host can hand them a file of the folder in the chat (a link or card they click, a file they can save or attach), hand the export over that way too, so they never have to look for the folder. Do not ask anything; set the `pilot-export` row to the date in 14 days.
5. Never send it yourself. If the host has a mail connector and they ask for it, prepare a draft to an address they give; sending stays with them.
6. Commit `pilot: export <date>`.

## Never
- Never write `gedaechtnis/vorlieben.md`, a template or a core file; a pilot entry changes nothing about how you work.
- Never ask a feedback question; never block or delay their request because of this skill.
- Never write to the pilot files in relief mode, and never afterwards about the relief conversation; never store conversation content; never store anything about persons.
- Never send, upload or share anything; the export is a file in their folder.
