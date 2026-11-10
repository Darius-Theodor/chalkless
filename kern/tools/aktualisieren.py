#!/usr/bin/env python3
"""Get Chalkless from its git source and bring in new versions; the teacher's own files are never touched.

  python <clone>/kern/tools/aktualisieren.py --installieren <folder>
        Setup from a fresh clone that the agent made in a temporary folder OUTSIDE the teacher's folder.
        Places the package in <folder> (or in <folder>/Chalkless if <folder> already holds files of theirs),
        creates the history there (.git/ or verlauf/, see verlauf.py) with the published history of the
        source, and remembers the source for updates (fetch only, never push). Never overwrites a file.
        The folder setup/ (setup aid) is placed, but it is not part of the history, as in a ZIP setup.
  python kern/tools/aktualisieren.py --pruefen
        Asks the source whether a newer version exists. Changes nothing.
  python kern/tools/aktualisieren.py --einspielen
        Brings in the newest version as one merge commit "core: update to <version>": everything the source
        publishes (kern/, the root files, the folder READMEs) becomes exactly the published file, files the
        new version no longer has disappear, setup/ never comes back. Every other file (the instance) stays
        exactly as it is. Local core changes are overwritten and listed (re-offer them, kern/regeln.md §10).
  python kern/tools/aktualisieren.py --woechentlich
        The weekly check at session start (kern/regeln.md §2): if this calendar week was already checked, it
        answers at once without network ("checked already"); otherwise it asks the source. The week is
        remembered in the history's settings (git config chalkless.geprueft, no file in the folder) once the
        folder is known to be current: after "current" here or in --pruefen, after --einspielen and --installieren.
        "update available" and "not reachable" are not remembered, so the next session asks again.
        A folder without history or without git source answers "skipped" (exit 0).
  python kern/tools/aktualisieren.py --anbinden <url> [--zweig <branch>]
        Connects a folder that was set up from a ZIP package to a git source; then --einspielen works.
        Changes no file.

Nothing here asks for a login: a source that needs one counts as not reachable. Without a configured git
identity commits are made as "Chalkless", never with the teacher's name.
Exit: 0 ok (also "current"), 1 problem (the line says what), 2 unsaved changes (commit them first),
3 no git or no history, 4 source not reachable.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import sys
import tarfile
from datetime import date
from pathlib import Path, PurePosixPath

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))
import verlauf  # noqa: E402

REMOTE = "chalkless"
NO_PUSH = "kein-push"  # push URL that cannot work: an instance never publishes anything
SETUP = "setup"
SYSTEM_FILES = {".DS_Store", "Thumbs.db", "desktop.ini", ".localized"}
ROOT_FILES = ("AGENTS.md", "CLAUDE.md", "README.md", "START-HIER.md", "CHANGELOG.md", ".claude/launch.json",
              ".gitattributes", ".gitignore")
INSTANCE_DIRS = ("profil", "vorlagen", "bereiche", "gedaechtnis", "review", "eingang", "beispiele", "archiv", "rahmen")
WEEK_KEY = "chalkless.geprueft"
ENV = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never", GIT_ASKPASS="", SSH_ASKPASS="")
TIMEOUT = 180


class Stop(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code, self.msg = code, msg


def run(cmd: list[str], cwd: Path, check: bool = False, binary: bool = False) -> subprocess.CompletedProcess:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, env=ENV, timeout=TIMEOUT,
                           **({} if binary else {"text": True, "encoding": "utf-8", "errors": "replace"}))
    except subprocess.TimeoutExpired:
        raise Stop(4, f"git did not answer within {TIMEOUT} s: {' '.join(cmd[-3:])}")
    if check and p.returncode != 0:
        err = p.stderr if isinstance(p.stderr, str) else p.stderr.decode("utf-8", "replace")
        raise Stop(1, f"git {' '.join(a for a in cmd[1:] if not a.startswith('-c'))[:120]} failed: "
                      + (err.strip().splitlines() or ["?"])[-1][:200])
    return p


class Repo:
    """git on the history of one folder, whichever route it has (.git/ or verlauf/)."""

    def __init__(self, git: str, root: Path):
        self.git, self.root = git, root
        self.route = verlauf.route(root)
        if not self.route:
            raise Stop(3, verlauf.line(git, root, None, "this folder has no history yet"))
        self.base = verlauf.base(git, root, self.route)

    def __call__(self, *args: str, check: bool = True) -> str:
        return run(self.base + list(args), self.root, check=check).stdout.strip()

    def ok(self, *args: str) -> bool:
        return run(self.base + list(args), self.root).returncode == 0

    def config(self, key: str) -> str:
        return self("config", "--get", key, check=False)

    def git_dir(self) -> Path:
        return self.root / (verlauf.DIR if self.route == "verlauf" else ".git")


def need_git() -> str:
    git = shutil.which("git")
    if not git:
        raise Stop(3, "git is not installed: no git source; updates come as a package (kern/regeln.md §10)")
    return git


def version_at(repo: Repo, ref: str) -> str:
    return repo("show", f"{ref}:kern/VERSION", check=False).strip() or "?"


def tree_paths(repo: Repo, ref: str) -> set[str]:
    out = run(repo.base + ["ls-tree", "-r", "-z", "--name-only", ref], repo.root, check=True).stdout
    return {p for p in out.split("\0") if p}


def fetch(repo: Repo) -> tuple[str, str]:
    """Fetch the remembered source; returns (branch, upstream ref)."""
    url = repo.config(f"remote.{REMOTE}.url")
    if not url:
        raise Stop(1, "no git source connected (this folder was set up from a package): "
                      "--anbinden <url> connects it, the address is in START-HIER.md")
    branch = repo.config("chalkless.zweig") or "main"
    ref = f"refs/remotes/{REMOTE}/{branch}"
    p = run(repo.base + ["fetch", "--quiet", "--no-tags", REMOTE, f"+refs/heads/{branch}:{ref}"], repo.root)
    if p.returncode != 0:
        raise Stop(4, f"source not reachable ({url}, branch {branch}): "
                      + (p.stderr.strip().splitlines() or ["?"])[-1][:200])
    return branch, ref


def this_week() -> str:
    y, w, _ = date.today().isocalendar()
    return f"{y}-W{w:02d}"


def remember_week(repo: Repo) -> None:
    repo("config", WEEK_KEY, this_week(), check=False)


def local_core_changes(root: Path) -> list[str]:
    """Core files that differ from the hash list of the installed core (kern_hashes.py), i.e. local changes."""
    sys.path.insert(0, str(root / "kern" / "tools"))
    try:
        import kern_hashes  # the installed (old) core's own tool
        res = kern_hashes.compare(root)
    except Exception:
        return []
    finally:
        sys.path.pop(0)
        sys.modules.pop("kern_hashes", None)
    return [] if res is None else res["changed"]


# ---------------------------------------------------------------------------------------------------------
def installieren(src: Path, folder: Path) -> int:
    git = need_git()
    src = src.resolve()
    if not (src / "kern" / "VERSION").is_file() or run([git, "rev-parse", "--git-dir"], src).returncode != 0:
        raise Stop(1, f"not a Chalkless clone: {src}")
    url = run([git, "remote", "get-url", "origin"], src).stdout.strip() or str(src)
    branch = run([git, "rev-parse", "--abbrev-ref", "HEAD"], src, check=True).stdout.strip()
    if branch == "HEAD":
        raise Stop(1, "the clone has no branch checked out; clone with --branch <branch>")
    head = run([git, "rev-parse", "HEAD"], src, check=True).stdout.strip()

    folder = folder.resolve()
    if folder == src or src in folder.parents or folder in src.parents:
        raise Stop(1, "the clone must lie outside the teacher's folder (a temporary folder)")
    folder.mkdir(parents=True, exist_ok=True)
    own = [p for p in folder.iterdir() if p.name not in SYSTEM_FILES and not (
        p.name.lower().startswith("chalkless-") and p.suffix.lower() == ".zip")]
    if (folder / "profil" / "rahmen.md").exists():
        raise Stop(1, "this folder already holds a Chalkless instance: this is an update (--anbinden / --einspielen)")
    target = folder
    if own:
        target = folder / "Chalkless"
        if target.exists() and any(p.name not in SYSTEM_FILES for p in target.iterdir()):
            raise Stop(1, f"{target} exists and is not empty; choose another folder")
        target.mkdir(exist_ok=True)

    # 1. the files, exactly as committed (git archive applies the line endings of .gitattributes)
    data = run([git, "archive", "--format=tar", "HEAD"], src, check=True, binary=True).stdout
    kept = written = 0
    with tarfile.open(fileobj=io.BytesIO(data)) as t:
        members = t.getmembers()
        for m in members:  # check every entry before writing anything
            p = PurePosixPath(m.name)
            if p.is_absolute() or ".." in p.parts or "\\" in m.name or ":" in m.name or m.issym() or m.islnk():
                raise Stop(1, f"stop, unsafe entry in the source: {m.name}")
        for m in members:
            dest = target.joinpath(*PurePosixPath(m.name).parts)
            if m.isdir():
                dest.mkdir(parents=True, exist_ok=True)
            elif m.isfile():
                if dest.exists():
                    kept += 1
                    print("kept, already there:", m.name)
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(t.extractfile(m).read())
                if m.mode & 0o111:
                    os.chmod(dest, 0o755)
                written += 1

    # 2. the history, with the published commits of the source
    r, reason = verlauf.einrichten(git, target)
    if not r:
        print(f"installed into {target} ({written} files)")
        print(verlauf.line(git, target, None, reason))
        print(f"source: {url} (branch {branch}); without history updates come as a package (kern/regeln.md §10)")
        return 0
    repo = Repo(git, target)
    if repo("rev-parse", "--verify", "-q", "HEAD", check=False):
        raise Stop(1, "the new history is not empty; stop")
    ref = f"refs/remotes/{REMOTE}/{branch}"
    repo("fetch", "--quiet", "--no-tags", str(src), f"+{head}:{ref}")
    local_branch = repo("symbolic-ref", "--short", "HEAD")
    repo("update-ref", f"refs/heads/{local_branch}", head)
    repo("reset", "--quiet")  # index = the published state; the files are already there
    repo("remote", "add", "-t", branch, REMOTE, url)
    repo("config", f"remote.{REMOTE}.pushurl", NO_PUSH)
    repo("config", f"remote.{REMOTE}.tagopt", "--no-tags")
    repo("config", "chalkless.zweig", branch)
    remember_week(repo)
    if repo("ls-files", "--", SETUP):
        repo("rm", "-r", "-q", "--cached", "--", SETUP)
        repo("commit", "-q", "-m", "setup: the setup aid is not part of the history")
    left = repo("status", "--porcelain")
    print(f"installed into {target} ({written} files{f', {kept} kept' if kept else ''})")
    print(verlauf.line(git, target, r))
    print(f"source: {url} (branch {branch}), version {version_at(repo, 'HEAD')}; updates: "
          "python kern/tools/aktualisieren.py --einspielen")
    if left:
        print("not clean after setup (look at it):\n" + left)
    return 0


def pruefen(root: Path) -> int:
    repo = Repo(need_git(), root)
    _, up = fetch(repo)
    now = version_at(repo, "HEAD")
    if repo.ok("merge-base", "--is-ancestor", up, "HEAD"):
        remember_week(repo)
        print(f"current: version {now}, nothing new at the source")
        return 0
    new = version_at(repo, up)
    print(f"update available: {now} -> {new}")
    for s in repo("log", "--format=%s", f"HEAD..{up}", check=False).splitlines()[:10]:
        print("  ", s)
    return 0


def einspielen(root: Path) -> int:
    repo = Repo(need_git(), root)
    if (repo.git_dir() / "MERGE_HEAD").exists():
        raise Stop(1, "an earlier update was not finished: git merge --abort, then again")
    dirty = repo("status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise Stop(2, "unsaved changes; commit them first (skill commit), then again:\n" + dirty)
    _, up = fetch(repo)
    old = version_at(repo, "HEAD")
    if repo.ok("merge-base", "--is-ancestor", up, "HEAD"):
        remember_week(repo)
        print(f"current: version {old}, nothing to bring in")
        return 0
    new = version_at(repo, up)
    base = repo("merge-base", "HEAD", up, check=False)
    new_core = tree_paths(repo, up)
    if base:
        old_core = tree_paths(repo, base)
    else:  # set up from a ZIP package: no shared history yet
        old_core = {p for p in tree_paths(repo, "HEAD") if p.startswith("kern/") or p in ROOT_FILES
                    or any(p == f"{d}/README.md" for d in INSTANCE_DIRS)}
    overwritten = local_core_changes(root)
    setup_before = (root / SETUP).exists()

    args = ["merge", "--no-ff", "--no-commit", "--quiet"] + ([] if base else ["--allow-unrelated-histories"]) + [up]
    p = run(repo.base + args, root)
    if not (repo.git_dir() / "MERGE_HEAD").exists():
        raise Stop(1, "the update could not start, nothing changed: "
                      + ((p.stderr or p.stdout).strip().splitlines() or ["?"])[-1][:300])
    try:
        repo("checkout", up, "--", ".")  # every published path becomes exactly the published file
        gone = sorted(old_core - new_core)
        tracked_gone = [g for g in gone if repo("ls-files", "--", g)]
        if tracked_gone:
            repo("rm", "-q", "-f", "--", *tracked_gone)
        if repo("ls-files", "--", SETUP):
            repo("rm", "-r", "-q", "-f", *([] if not setup_before else ["--cached"]), "--", SETUP)
        if not setup_before and (root / SETUP).exists():
            shutil.rmtree(root / SETUP, ignore_errors=True)
        conflicts = repo("diff", "--name-only", "--diff-filter=U").splitlines()
        if conflicts:
            raise Stop(1, "conflict outside the core, the update was undone: " + ", ".join(conflicts))
        repo("commit", "-q", "--no-edit", "-m", f"core: update to {new}")
    except Stop:
        run(repo.base + ["merge", "--abort"], root)
        raise
    remember_week(repo)
    commit = repo("rev-parse", "--short", "HEAD")
    print(f"updated: {old} -> {new} (commit {commit} 'core: update to {new}')")
    print("local core changes overwritten: " + (", ".join(overwritten) if overwritten else "none"))
    changed = sorted(set(local_core_changes(root)))
    print("core against its hash list: " + ("unchanged" if not changed else "CHANGED " + ", ".join(changed)))
    print("next: voraussetzungen.py --install, check_instance.py, kern_version in profil/rahmen.md, commit; "
          f"undo the whole update: git revert -m 1 {commit}")
    return 0


def woechentlich(root: Path) -> int:
    git = shutil.which("git")
    if not git or not verlauf.route(root):
        print("skipped: no history here; new versions come as a package (kern/regeln.md §10)")
        return 0
    repo = Repo(git, root)
    if not repo.config(f"remote.{REMOTE}.url"):
        print("skipped: no git source connected; new versions come as a package (kern/regeln.md §10)")
        return 0
    week = this_week()
    if repo.config(WEEK_KEY) == week:
        print(f"checked already this week ({week}), nothing to do")
        return 0
    _, up = fetch(repo)  # not reachable: exit 4, the week stays unchecked
    now = version_at(repo, "HEAD")
    if repo.ok("merge-base", "--is-ancestor", up, "HEAD"):
        remember_week(repo)
        print(f"current: version {now}, checked for {week}")
        return 0
    print(f"update available: {now} -> {version_at(repo, up)}; bring it in after their request "
          "(kern/regeln.md §2, skill uebergang)")
    return 0


def anbinden(root: Path, url: str, branch: str) -> int:
    repo = Repo(need_git(), root)
    if repo.config(f"remote.{REMOTE}.url"):
        repo("remote", "set-url", REMOTE, url)
        repo("config", "--unset-all", f"remote.{REMOTE}.fetch", check=False)
        repo("config", "--add", f"remote.{REMOTE}.fetch", f"+refs/heads/{branch}:refs/remotes/{REMOTE}/{branch}")
    else:
        repo("remote", "add", "-t", branch, REMOTE, url)
    repo("config", f"remote.{REMOTE}.pushurl", NO_PUSH)
    repo("config", f"remote.{REMOTE}.tagopt", "--no-tags")
    repo("config", "chalkless.zweig", branch)
    _, up = fetch(repo)
    if not repo("ls-tree", "--name-only", up, "kern/VERSION", check=False):
        raise Stop(1, f"{url} (branch {branch}) is not a Chalkless source")
    print(f"connected: {url} (branch {branch}), newest version there {version_at(repo, up)}; "
          "now --einspielen brings it in")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    argv = list(sys.argv[1:] if argv is None else argv)
    root = TOOLS.parents[1]
    if argv[:1] == ["--root"] and len(argv) > 1:
        root, argv = Path(argv[1]).resolve(), argv[2:]
    try:
        if argv[:1] == ["--installieren"] and len(argv) == 2:
            return installieren(TOOLS.parents[1], Path(argv[1]))
        if argv == ["--pruefen"]:
            return pruefen(root)
        if argv == ["--woechentlich"]:
            return woechentlich(root)
        if argv == ["--einspielen"]:
            return einspielen(root)
        if argv[:1] == ["--anbinden"] and len(argv) in (2, 4) and (len(argv) == 2 or argv[2] == "--zweig"):
            return anbinden(root, argv[1], argv[3] if len(argv) == 4 else "main")
    except Stop as s:
        print(s.msg)
        return s.code
    print(__doc__)
    return 0 if argv[:1] in (["-h"], ["--help"]) else 1


if __name__ == "__main__":
    sys.exit(main())
