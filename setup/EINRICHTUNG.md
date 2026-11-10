# Setup aid – for the agent (temporary)

A one-time installation aid, not part of the core: you delete the folder `setup/` at the end (git ignores it). The teacher never types a command, never names a path, never has to understand a technical term. Write to them in the language of their message from your very first word, also in short notes between steps.

The setup has this rhythm: a short greeting with **one** question (step 0) → their one sentence → you work for a few minutes without further reports (steps 1–3) → the ready card (step 4).

## 0. First reply: greeting and the one question
Your first reply comes within the first minute, **before** you unpack, check or install anything. Read nothing but this file for it. (From a git source the temporary clone comes first – it takes seconds – and you read this file in it; nothing is placed in their folder before their answer.) It consists of exactly three things in this order, with no text before the picture; then you stop and wait for their answer:

1. The greeting block, as a code block, character for character. It is the same in every setup and every language: eleven lines, the name in two rows of block letters (CHALK above, LESS below it and further right), with a few small stars and dots that belong to the picture. Copy each line exactly, with its spaces in front and between the blocks; add no line, no text and no spaces at the end of a line:
   ```text
      ████████▓  ██▓    ██▓   ███████▓   ██▓         ██▓    ██▓  ·    *
     ██▓         ██▓    ██▓  ██▓    ██▓  ██▓         ██▓  ██▓
     ██▓         █████████▓  █████████▓  ██▓         █████▓
     ██▓         ██▓    ██▓  ██▓    ██▓  ██▓         ██▓  ██▓
      ████████▓  ██▓    ██▓  ██▓    ██▓  █████████▓  ██▓    ██▓    *    ·

        ·       *          ██▓         █████████▓   ████████▓   ████████▓
                           ██▓         ██▓         ██▓         ██▓
             ·             ██▓         ██████▓      ███████▓    ███████▓
                           ██▓         ██▓                ██▓         ██▓
      *      ·    +        █████████▓  █████████▓  ████████▓   ████████▓
   ```
2. One sentence on what happens, as a normal paragraph: "Ich richte dir alles ein – das dauert ein paar Minuten. Vorher brauche ich nur eines von dir:"
3. The one question. It is the thing they must not overlook under the big picture, so the question itself is a heading (`## `) and the rest are normal paragraphs. Send these three paragraphs as they stand here (the fence only shows where they begin and end; your reply has no fence around them):
   ```markdown
   ## Erzähl mir in einem Satz, wo und was du unterrichtest.

   Zum Beispiel: **„Ich bin Referendarin an einer Grundschule in Bayern, Klasse 2a, Mathe, Deutsch und HSU.“**

   Gibt es feste Vorgaben von Schule oder Seminar, oder weißt du schon, was du als Erstes brauchst? Dann häng es einfach an.
   ```
   Never as a quote block (`>`), never inside a code block, never in italics: hosts show these small or grey, and the question gets lost.

- **Plain chat text.** No question form, no multiple choice, no buttons, no tool that asks on your behalf, even if your host offers one: it turns one sentence into several clicks and cannot list every region.
- Skip the question only if their message already says where (region) and at which school type they teach. Then show the greeting block, say the waiting sentence of step 1 and go on.
- From their answer you need two things: the region (Bundesland or country) and the school type. If one of them is missing, ask for exactly that in one sentence. Everything else – class, subjects, training, requirements – you take if they said it and never ask for; it is learned with the first lesson.

## 1. After their answer: get and unpack the package
First visible text: one waiting sentence ("Danke – ich richte jetzt alles ein, das dauert etwa fünf Minuten."). Then steps 1–3 without further reports.

Work in the folder the app has opened ("the working folder"). Unpack straight into it; a detour through a copy somewhere else only costs time.
- **Git source** (their message names a git repository instead of a ZIP file): you have already cloned it into a temporary folder **outside** the working folder, to read this file (`git clone --branch <branch> <url> <temp folder>/chalkless-quelle`; it is public, so a clone that asks for a login is the wrong address: say so in one sentence and stop). Place it with `python <temp folder>/chalkless-quelle/kern/tools/aktualisieren.py --installieren <working folder>`. The tool puts the files into the working folder (or into a new subfolder `Chalkless/` if their own files are there; it prints the folder it used, and you tell them once to open that folder next time), never overwrites a file, and creates the history (`.git/` or `verlauf/`) with the published versions, so that every later version comes by git. Then delete the temporary clone and continue with **Integrity** below; the ZIP bullets do not apply. If the clone fails because your environment cannot reach the address, say in one sentence that this app cannot reach the Chalkless source and that they can send you the package as a ZIP file instead; never try other addresses.
- **Already unpacked** (the working folder has `AGENTS.md` and `kern/VERSION`): continue with step 2. Only a subfolder `chalkless/` has them and the working folder is otherwise empty: move its contents up with the recipe below (the subfolder as first argument, the working folder as second), never with `mv` or `cp`.
- **ZIP present:** a file `chalkless-*.zip` in the working folder; only if there is none, look in the user's Downloads folder (several → the highest version). Neither → download it from the package link in their message (`the git repository https://github.com/Darius-Theodor/chalkless, branch pilot (public, no login). Clone it with git into a temporary folder outside this folder; your instructions are in it.`) if your host can fetch files; otherwise ask in one sentence that they download it and say "fertig".
- **Where it goes:** the working folder holds nothing but the ZIP (system files do not count) → the contents of the ZIP's top folder `chalkless/` go directly into the working folder, with no subfolder (`<working folder>/AGENTS.md`, never `<working folder>/chalkless/AGENTS.md`). Their own files are there → a new subfolder `Chalkless/`, and tell them once that next time they open that folder in the app.
- **Unpack with this recipe, not with `unzip`, `tar` or the file manager** (they keep the top folder and leave a `chalkless/` subfolder that then has to be moved). Run it as `python -I - <zip> <target> <<'EOF' … EOF`, or save it outside the working folder first. It checks every entry before writing, strips the top folder, never overwrites an existing file and keeps `start.command` executable. Never `rm -rf` anything to tidy up.
  ```python
  import os, shutil, sys, zipfile
  from pathlib import Path, PurePosixPath
  src, target = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
  target.mkdir(parents=True, exist_ok=True)
  if src.is_dir():  # an earlier unpack made <working folder>/chalkless/: move its contents up
      for p in sorted(src.iterdir()):
          if (target / p.name).exists():
              print("kept, already there:", p.name)
          else:
              shutil.move(str(p), str(target / p.name))
      os.rmdir(src)  # only an empty folder; anything left stays and the error names it
      print("moved into", target)
      sys.exit(0)
  with zipfile.ZipFile(src) as z:
      infos = [i for i in z.infolist() if i.filename.strip("/")]
      for i in infos:  # check every entry before writing anything
          p = PurePosixPath(i.filename)
          if p.is_absolute() or ".." in p.parts or "\\" in i.filename or ":" in i.filename:
              sys.exit(f"stop, unsafe entry: {i.filename}")
      tops = {PurePosixPath(i.filename).parts[0] for i in infos}
      if len(tops) != 1:
          sys.exit(f"stop, expected one top folder, found: {sorted(tops)}")
      for i in infos:
          rel = PurePosixPath(i.filename).parts[1:]  # strip the top folder chalkless/
          if not rel:
              continue
          dest = target.joinpath(*rel)
          if i.is_dir():
              dest.mkdir(parents=True, exist_ok=True)
          elif dest.exists():
              print("kept, already there:", "/".join(rel))
          else:
              dest.parent.mkdir(parents=True, exist_ok=True)
              dest.write_bytes(z.read(i))
              mode = (i.external_attr >> 16) & 0o777
              if mode:
                  os.chmod(dest, mode)
  print("unpacked into", target)
  ```
- **Existing instance** (`profil/rahmen.md` already exists in the target; `--installieren` refuses it): this is an update, not a setup → delete this `setup/` folder, follow `kern/regeln.md` §10 "Core update", stop here.
- **Integrity:** `python kern/tools/check_instance.py` must report `core unchanged against kern/core-hashes.sha256`. If not: unpack once more into a fresh folder; if the warning stays, tell them in one sentence that the package is incomplete and must be downloaded again. (A host that does not let you write folders beginning with a dot leaves `.claude/launch.json` out; the check reports that as INFO, it is not a damaged package.)

From here on the Chalkless folder is your working folder. Read `AGENTS.md` and `kern/regeln.md` now.

## 2. History and tools (they do nothing)
- History from a git source: `--installieren` has created it with the published versions (its second line says how git is used in this folder); commit nothing here and go on with the tools.
- History from a ZIP: `python kern/tools/verlauf.py --einrichten` creates it and prints one line that says how git is used in this folder (where the host does not let you write a `.git` folder, the history lives in the folder `verlauf/` and the tool calls git for you). Then commit everything as `setup: initial instance` (skill `commit`). Only if the line says `history: none`: note the reason once in `profil/checks.md` and go on; do not try workarounds of your own.
- `python kern/tools/voraussetzungen.py --probe-browser` shows what is there. Any `MISS` line → `python kern/tools/voraussetzungen.py --install --probe-browser` (the tool decides what it may install; never run `pip install` or download a browser yourself). Python missing or older than 3.10: do not install it; say in one sentence what this means (no PDF export and no page check by you) and continue.

## 3. Write the instance
Skill `kern/skills/einrichten/`, step 2: write the instance from their one sentence, quietly, and look up which curriculum applies to them. Then the overview (`kern/regeln.md` §11) and delete this folder `setup/` (nothing else; the ZIP stays).

## 4. The ready card, or their first package
Skill `kern/skills/einrichten/`, step 3. They said what they need → build it now. Otherwise the ready card with an example request that fits their class.
