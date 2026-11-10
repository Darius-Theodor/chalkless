---
name: uebergang
description: Handle a change of school year, training status or teaching assignment – ask only for what changed, archive old areas, create new ones, extend the calendar, adapt duties and templates, record the check – and carry out a core update over an existing instance as a checked step list. Use when a transition check in profil/checks.md is due, or they say "das neue Schuljahr beginnt", "meine Ausbildung ist zu Ende" (in their local term), "ich habe eine neue Klasse / ein neues Fach", or "spiel die neue Chalkless-Version ein".
---

# Skill: uebergang

Never in relief mode (`kern/regeln.md` §9). A transition and an update keep everything that belongs to the teacher: every instance file, every document and every own final version (`export: eigene-endfassung`) stays readable and unchanged in content. Nothing is deleted and nothing is created twice. Neither touches the core except the update itself (`kern/regeln.md` §10).

## Transition: steps
1. Read `profil/rahmen.md`, `profil/lehrkraft.md`, `profil/pflichten.md`, `profil/checks.md`. Determine which transition this is (school year, status, assignment change mid-year). Commit open instance changes first (skill `commit`), so the transition is one clean step.
2. Ask only the ↻ IDs from `kern/interview/katalog.md` that can have changed for this transition, in one message. Show the current value next to each ("Bisher: <Klasse Fach>, <Klasse Fach> – was ändert sich?"). Never repeat questions whose answers are still valid.
3. Apply:
   - **School year:** move areas that end to `archiv/<old school year>/<area>/` with `git mv` – the whole folder, with STAND, documents, PDFs and own final versions. Create new areas (STAND from `kern/instanz-vorlage/bereich/STAND.md`) only where no folder of that name exists in `bereiche/`; an area that continues (same class and subject) stays where it is and only gets `schuljahr` updated. If the target `archiv/<old school year>/<area>/` already exists, stop and ask – never merge or overwrite. Run `recherche` for the new calendar block (`kalender/<new school year>.md`) with status, unless it already exists.
   - **Status** (e.g. end of training): set `status` and move "Geplant ab" to "Aktiv" in `profil/rahmen.md`; training rules stop applying; ask which `pflichten.md` rows remain duties, which become optional, which go. Templates stay; their `Vorgabe` rows whose issuer no longer applies become `Vorliebe` after their yes (a new template version, via `herkunft.md`).
   - **New class or subject mid-year:** create the area (if it does not exist); curriculum blocks for the new subject via `recherche`; template needs via `pflichten.md`.
4. New files in `eingang/` that came with the change: skill `eingang`.
5. Record in `profil/checks.md`: update the existing transition row (date, what changed, next transition date from the calendar/profile) instead of adding a second one; close reminders whose cause is gone (`kern/regeln.md` §3). Leave `pilot` and the pilot rows as they are.
6. Run `python kern/tools/check_instance.py`; fix what it reports inside the instance (areas listed vs. folders, STAND keys). Commit `transition: <summary>`.
7. Reply: what changed, what was archived (where), what is new, what they should check.

## Core update over an existing instance (new package)
`kern/regeln.md` §10 "Core update" is binding; this is its checked step list. When they want a new version, or a new package lies in `eingang/` or where they say:

**By git** (the history has a source: `python kern/tools/aktualisieren.py --pruefen` answers instead of saying "no git source connected"). Use this whenever it works; no package is needed:
1. **Before:** as step 1 below (commit open changes, run the check, note the `aktiv` core changes and `pilot`).
2. `python kern/tools/aktualisieren.py --einspielen`. It fetches the newest version, makes every published file (`kern/`, root files, folder READMEs) exactly the published one, removes core files the new version dropped, never brings `setup/` back and never touches an instance file; all of it is one merge commit `core: update to <version>`. It prints the local core changes it overwrote. Exit 2 = unsaved changes (commit, then again); 4 = source not reachable (say so in one sentence; nothing changed); "current" = nothing new, say so in one sentence.
3. Then steps 5, 7 and 8 below (tools and check, `kern_version`, overwritten `aktiv` rows; the overview; tell them), and commit those instance changes as `update: instance adjusted to <version>`. Undo of the whole update: `git revert -m 1 <hash of the merge commit>`.
When the weekly check (`kern/regeln.md` §2) brings the update in, nobody asked for it: do it after their request, and step 8 shrinks to the sentence of §2 plus at most one sentence on what is new for them; overwritten core changes are still named and offered again.
A folder set up from a ZIP package can be connected once when they give you the source address (it is in the copy text of `START-HIER.md` of a git-published version): `python kern/tools/aktualisieren.py --anbinden <url> --zweig <branch>`, then as above. No history at all (`verlauf.py --route` says `none`): clone the source into a temporary folder and use it as the new package in the steps below.

**From a package** (a ZIP file):
1. **Before:** commit open instance changes (skill `commit`). Run `python kern/tools/check_instance.py` and note: the rows of `gedaechtnis/kernaenderungen.md` that are still `aktiv`, the value of `pilot`, half states it reports (finish or note them first, so the update does not mix with an unfinished step).
2. **Unpack outside the instance** into a temporary folder. It is a Chalkless package if it has `kern/VERSION` and `kern/core-hashes.sha256`; otherwise stop and say so.
3. **Replace the core only:** replace `kern/` as a whole (old core files that the new package no longer has disappear) and the root files `AGENTS.md`, `CLAUDE.md`, `README.md`, `START-HIER.md`, `CHANGELOG.md`, `.claude/launch.json`. Never copy the package's `setup/` folder. Already unpacked over the instance by them: delete the `setup/` folder it brought and continue with step 4. Never touch `profil/ vorlagen/ bereiche/ gedaechtnis/ review/ rahmen/ beispiele/ eingang/ archiv/`. `kern/PILOT` comes or goes with the package.
4. **Verify:** `git status --short` lists changes only in `kern/` and those root files. Anything else changed → restore it from git (`git checkout -- <path>`) and say so in one sentence.
5. **Tools and check:** `python kern/tools/voraussetzungen.py --install`, then `python kern/tools/check_instance.py`. Fix inside the instance only: a profile field the new skeleton has and the instance lacks → add the line with `[ ]` and keep every existing value; an old field → keep it, move its value to the new field only if the meaning is clearly the same; old `[vermutet]` lines stay (§5). Pilot: the new package has no `kern/PILOT` but the instance says `pilot: an` → set `aus` without mentioning it; `pilot: aus` never becomes `an`. Set `kern_version` to the new `kern/VERSION`. Set every `aktiv` row noted in step 1 to `überschrieben durch Update <version> am <date>`.
6. **Commit** `core: update to <version>` (skill `commit`), then delete the temporary folder.
7. **Overview:** as a file (`Übersicht.html` / `Overview.html` in the folder): write it again with `python kern/webapp/server.py --datei`. In a side panel: if it is running, it still runs the old code: stop it and start it again (`kern/regeln.md` §11). A start that answers "läuft schon" means the old one is still running. If you cannot stop it (e.g. it was started by the host's preview tool or in another session), say so in one sentence: the next start shows the new version.
8. **Tell them** in a few sentences (§10 step 4): what changed (the new top section of `CHANGELOG.md`), which of their local core changes the update overwrote; offer to re-apply each change from its `.geaendert` copy or its `core-change:` commit (`git show <hash>`), made anew against the new file – never copy the backup (the old original) over the new core; each only with a new yes (§10 steps 1–4, new backup, new row).

## Rules
- Archive, never delete. Archived areas remain readable for "mach es wie letztes Jahr".
- No transition is hard-wired to a month; dates come from the package calendar and the profile.
- A transition never re-exports, renames or rewrites existing documents; own final versions are never overwritten.
