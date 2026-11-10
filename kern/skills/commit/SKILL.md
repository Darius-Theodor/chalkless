---
name: commit
description: Save the instance in the local git repository after every finished step (a package, a change, the setup, a memory or template change), and restore a step when they ask to undo. Never mid-work, never in relief mode.
---

# Skill: commit

## Where the history lives
`python kern/tools/verlauf.py <git arguments>` runs git on the history of this folder, wherever it lives: in `.git/`, or in the folder `verlauf/` on a host that does not allow a `.git` folder. Every `git …` in this skill and in the rules can be written that way with the same arguments, and must be when plain `git` says this is not a repository. Never touch the folder `verlauf/` by hand.

## Save
1. `python kern/tools/verlauf.py status --short`. Exit 3 means there is no history yet: `python kern/tools/verlauf.py --einrichten`, then commit everything as `setup: initial instance`. If that prints `history: none`: note the reason once in `profil/checks.md` ("kein Verlauf – …"), tell them once, stop.
2. **Their own changes first.** A file that shows as changed and that you did not touch in this session is the teacher's edit: commit it on its own as `teacher: own changes in <file>` before your step, and never overwrite it.
3. Stage only the paths of this step (`git add <paths>`) – instance paths. `kern/` and the root files are committed only as a whole after a core update (`core: update to <version>`, `kern/regeln.md` §10).
4. `git commit -m "<message>"` in the format of `kern/konventionen.md` §7. One line, English, no personal data. If git has no identity configured, commit as `git -c user.name="Chalkless" -c user.email="chalkless@localhost" commit …`; never put the teacher's name or e-mail address into a commit.
5. On failure (lock, permissions): do not retry in a loop; note it in the area's STAND `offen` and tell them in one line.

## Afterwards, also without git
If `Übersicht.html` or `Overview.html` lies in the folder, the overview is a file (`kern/regeln.md` §11): run `python kern/webapp/server.py --datei` so that it shows the new state. These files are generated and never committed.

## Restore
"Mach das rückgängig" → `git log --oneline -10`, find the commit of that step, `git revert --no-edit <hash>`, re-export the affected PDFs, tell them what was restored. Never rewrite history.
