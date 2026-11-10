#!/usr/bin/env python3
"""History of the instance: git, also where the host does not allow a `.git` folder.

  python kern/tools/verlauf.py --einrichten      find or create the history; prints one line with the route
  python kern/tools/verlauf.py --route           print the route line only, change nothing
  python kern/tools/verlauf.py <git arguments>   run git on this history, e.g.
                                                 status --short | add <paths> | commit -m "<message>" |
                                                 log --oneline -10 | revert --no-edit <hash>

Routes
  .git/      the folder has (or accepts) a `.git` folder: plain `git` works; this tool only passes the
             arguments on.
  verlauf/   the host refuses a `.git` folder (some hosts protect folders whose name starts with a dot):
             the history lives in the folder `verlauf/` and git is called with --git-dir / --work-tree.
             If the host accepts a small file named `.git` that points there, plain `git` works as well.
  none       no git, or neither place can be written: no history.

Nothing here leaves the folder and this tool configures no remote (only aktualisieren.py adds the Chalkless
source, fetch only). The teacher's name is never used: without a
configured identity commits are made as "Chalkless".

Exit: git's exit code; 3 = no history (the line on stdout says why).
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

DIR = "verlauf"
IDENT = ["-c", "user.name=Chalkless", "-c", "user.email=chalkless@localhost"]
NOTE = ("History of this Chalkless folder (written by git through kern/tools/verlauf.py).\n"
        "Do not edit or delete anything in here: \"Mach das rückgängig\" restores from it.\n")


def _run(cmd: list[str], root: Path, text_in: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(root), input=text_in, capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def route(root: Path) -> str | None:
    """Where the history of this folder lives: 'git' (.git folder or pointer file), 'verlauf', or None."""
    if (root / ".git").is_dir():
        return "git"
    if (root / DIR / "HEAD").is_file():
        return "verlauf"
    return None


def base(git: str, root: Path, r: str) -> list[str]:
    cmd = [git]
    if r == "verlauf":
        cmd += ["--git-dir", str(root / DIR), "--work-tree", str(root)]
    probe = _run(cmd + ["config", "user.email"], root)
    if probe.returncode != 0 or not probe.stdout.strip():
        cmd += IDENT
    return cmd


def plain_git_works(git: str, root: Path) -> bool:
    """Plain `git` finds the history (a .git folder, or a pointer file .git that leads to verlauf/)."""
    p = _run([git, "rev-parse", "--git-dir"], root)
    if p.returncode != 0:
        return False
    found = (root / p.stdout.strip()).resolve()
    return found in ((root / ".git").resolve(), (root / DIR).resolve())


def line(git: str | None, root: Path, r: str | None, reason: str = "") -> str:
    if r == "git":
        return "history: git (.git/) - use git as usual"
    if r == "verlauf":
        if git and plain_git_works(git, root):
            return f"history: git in {DIR}/ - plain git works here (pointer file .git)"
        return (f"history: git in {DIR}/ - run every git command as: "
                "python kern/tools/verlauf.py <git arguments>")
    return f"history: none - {reason or 'not set up yet'}; no undo, say so once"


def _probe(git: str, root: Path) -> str | None:
    """Write, lock and delete once inside the history; returns the error or None."""
    cmd = base(git, root, "verlauf")
    blob = _run(cmd + ["hash-object", "-w", "--stdin"], root, text_in="chalkless\n")
    if blob.returncode != 0:
        return "cannot write objects: " + (blob.stderr.strip().splitlines() or ["?"])[-1][:120]
    for step in (["update-ref", "refs/chalkless/probe", blob.stdout.strip()],
                 ["update-ref", "-d", "refs/chalkless/probe"],
                 ["status", "--porcelain"]):
        p = _run(cmd + step, root)
        if p.returncode != 0:
            return f"git {step[0]} failed: " + (p.stderr.strip().splitlines() or ["?"])[-1][:120]
    return None


def einrichten(git: str | None, root: Path, dot_folder: bool = True, pointer: bool = True) -> tuple[str | None, str]:
    """Find or create the history. Returns (route, reason if none). The two switches exist for the tests."""
    r = route(root)
    if r:
        return r, ""
    if not git:
        return None, "git is not installed"
    if dot_folder:
        p = _run([git, "-c", "init.defaultBranch=main", "init", "-q"], root)
        if p.returncode == 0 and (root / ".git" / "HEAD").is_file():
            return "git", ""
    # the host does not take a .git folder: keep the history in a folder without a dot
    gd = root / DIR
    p = _run([git, "-c", "init.defaultBranch=main", "--git-dir", str(gd), "--work-tree", str(root), "init", "-q"], root)
    if p.returncode != 0 or not (gd / "HEAD").is_file():
        shutil.rmtree(gd, ignore_errors=True)
        return None, "the folder accepts neither .git/ nor " + DIR + "/"
    cfg = [git, "--git-dir", str(gd), "config"]
    _run(cfg + ["--unset", "core.worktree"], root)  # an absolute path of this session; the tool passes the work tree
    _run(cfg + ["core.bare", "false"], root)
    _run(cfg + ["gc.auto", "0"], root)
    try:
        (gd / "info").mkdir(exist_ok=True)
        with (gd / "info" / "exclude").open("a", encoding="utf-8", newline="\n") as f:
            f.write(f"/{DIR}/\n")
        (gd / "LIES-MICH.txt").write_text(NOTE, encoding="utf-8", newline="\n")
    except OSError as e:
        shutil.rmtree(gd, ignore_errors=True)
        return None, f"cannot write into {DIR}/ ({type(e).__name__})"
    err = _probe(git, root)
    if err:
        shutil.rmtree(gd, ignore_errors=True)
        return None, err
    if pointer:
        try:  # lets plain `git` find the history; fine if the host refuses the file
            (root / ".git").write_text(f"gitdir: {DIR}\n", encoding="utf-8", newline="\n")
            if not plain_git_works(git, root):
                (root / ".git").unlink()
        except OSError:
            pass
    return "verlauf", ""


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    root = Path(__file__).resolve().parents[2]
    if argv[:1] == ["--root"] and len(argv) > 1:
        root, argv = Path(argv[1]).resolve(), argv[2:]
    git = shutil.which("git")
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    if argv[0] == "--einrichten":
        r, reason = einrichten(git, root)
        print(line(git, root, r, reason))
        return 0 if r else 3
    r = route(root)
    if argv[0] == "--route":
        print(line(git, root, r, "" if git else "git is not installed"))
        return 0 if r else 3
    if not git or not r:
        print(line(git, root, None, "" if git else "git is not installed"))
        return 3
    return subprocess.call(base(git, root, r) + argv, cwd=str(root))


if __name__ == "__main__":
    sys.exit(main())
