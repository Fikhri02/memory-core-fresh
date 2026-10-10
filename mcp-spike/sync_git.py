"""memory-core sync: git plumbing and the commands the sync-memory skill runs.

Every command prints one JSON object. The skill holds the conversation; this module does only what
can be tested — sparse checkout, scoped commits, merges and the device registry. Stdlib only.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import subprocess
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sync_device as dev  # noqa: E402
import sync_guard as guard  # noqa: E402
import sync_merge as mrg  # noqa: E402

BRANCH = "main"
OPT_IN = ("project-management", "ecosystem")
CURRENT_SESSION = "main/current-session.md"
SESSION_ARCHIVE = "main/session-archive.md"
LOG_FILES = {"project-management/*/Timeline.md": 2, "design/journal.md": 2,
             "career/timeline.md": 2, "main/session-archive.md": 3}
GITIGNORE_LINES = ["/device/", "/.superpowers/", "/outputs/", "/.venv/", "__pycache__/", "/migrations/in/",
                   "/.claude/settings.json", "/.claude/settings.local.json"]
MACHINE_ONLY = ("device", ".superpowers", "outputs", ".venv", "migrations/in")
SPEC_CORE = ("main", "context", "design", "career", "learning", "brainstorming", "project-plans", "notes",
             "delegate-task", "docs", "devices", "plugins", "adapters", "mcp-spike", "tests", "_templates",
             ".memory-core")
EMPTY_TREE = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
GITATTRIBUTES = """# memory-core sync — logs merge by keeping both sides' lines (sync-memory skill)
project-management/**/Timeline.md merge=union
design/journal.md merge=union
career/timeline.md merge=union
main/session-archive.md merge=union
delegate-task/** merge=union
"""
PENDING = "memory-core-merge.json"
FAILURE = ("error", "refused", "failed", "blocked")


class SyncError(RuntimeError):
    pass


# ---------------------------------------------------------------- git plumbing

def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise SyncError(f"git {' '.join(args)}: {(proc.stderr or proc.stdout).strip()}")
    return proc


def out(root: Path, *args: str) -> str:
    return git(root, *args).stdout.strip()


def git_path(root: Path, rel: str) -> Path:
    return root / out(root, "rev-parse", "--git-path", rel)


def has_ref(root: Path, ref: str) -> bool:
    return git(root, "rev-parse", "--verify", "-q", ref, check=False).returncode == 0


def tree_dirs(root: Path, ref: str = "HEAD", sub: str = "") -> list[str]:
    target = f"{ref}:{sub}" if sub else ref
    proc = git(root, "ls-tree", "-d", "-z", "--name-only", target, check=False)
    return [d for d in proc.stdout.split("\0") if d] if proc.returncode == 0 else []


def kind_at(root: Path, ref: str = "HEAD") -> str | None:
    """A sparse clone has not checked .memory-core/ out yet, so read the marker from git."""
    proc = git(root, "show", f"{ref}:.memory-core/kind", check=False)
    return (proc.stdout.strip() or None) if proc.returncode == 0 else None


def sync_cfg(root: Path) -> dict[str, str]:
    return dev.read_kv(root / dev.DEVICE_DIR / "sync.md")


def write_cfg(root: Path, cfg: dict[str, str]) -> None:
    dev.write_kv(root / dev.DEVICE_DIR / "sync.md", cfg, "Sync settings — never synced")


def auth_args(cfg: dict) -> list[str]:
    account, remote = cfg.get("account", ""), cfg.get("remote", "")
    if not account or not remote.startswith("https://"):
        return []
    helper = f'!f() {{ echo username={account}; echo "password=$(gh auth token --user {account})"; }}; f'
    return ["-c", "credential.helper=", "-c", f"credential.helper={helper}"]


def gh_visibility(remote: str, account: str) -> str | None:
    if guard.is_local(remote):
        return None
    slug = guard.normalise_remote(remote).split("/", 1)[1]
    env = dict(os.environ)
    if account:
        token = subprocess.run(["gh", "auth", "token", "--user", account], capture_output=True, text=True)
        if token.returncode == 0:
            env["GH_TOKEN"] = token.stdout.strip()
    proc = subprocess.run(["gh", "repo", "view", slug, "--json", "visibility", "-q", ".visibility"],
                          capture_output=True, text=True, env=env)
    return (proc.stdout.strip() or None) if proc.returncode == 0 else None


def claude_home() -> Path:
    return Path(os.environ.get("MEMORY_CORE_CLAUDE_HOME", str(Path.home())))


# ---------------------------------------------------------------- local state

def ensure_gitfiles(root: Path) -> None:
    ignore = root / ".gitignore"
    existing = ignore.read_text(encoding="utf-8").splitlines() if ignore.is_file() else []
    missing = [line for line in GITIGNORE_LINES if line not in existing]
    if missing:
        lines = existing + ([""] if existing else []) + ["# memory-core sync — machine-only", *missing]
        ignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
    attrs = root / ".gitattributes"
    current = attrs.read_text(encoding="utf-8") if attrs.is_file() else ""
    if "merge=union" not in current:
        attrs.write_text(current + ("\n" if current and not current.endswith("\n") else "") + GITATTRIBUTES,
                         encoding="utf-8")


def _ignored(root: Path, rel: str) -> bool:
    return git(root, "check-ignore", "-q", rel, check=False).returncode == 0


def core_dirs(root: Path) -> list[str]:
    """Spec §3 core list, plus any top-level folder another device already syncs. New local folders
    outside that list stay on this machine — they are never swept up silently."""
    shared = set(tree_dirs(root, "HEAD")) | set(tree_dirs(root, f"origin/{BRANCH}"))
    machine = {p.split("/")[0] for p in MACHINE_ONLY if "/" not in p}
    return sorted((set(SPEC_CORE) | shared) - set(OPT_IN) - machine - {".git"})


def sparse_patterns(top_dirs: list[str], follows: dict[str, list[str]], templates: list[str]) -> list[str]:
    patterns = sorted(d for d in set(top_dirs) if d not in OPT_IN and d != ".git")
    patterns += templates
    for kind in OPT_IN:
        patterns += [f"{kind}/{slug}" for slug in sorted(set(follows.get(kind, [])))]
    return patterns


def apply_sparse(root: Path, follows: dict[str, list[str]]) -> list[str]:
    # Cone mode checks out the immediate files of a listed directory's parents, so
    # project-management/README.md arrives with project-management/_template. A kind with no
    # _template and nothing followed (ecosystem/ today) keeps its README local until something is.
    templates = [f"{kind}/_template" for kind in OPT_IN
                 if (root / kind / "_template").is_dir() or "_template" in tree_dirs(root, "HEAD", kind)]
    patterns = sparse_patterns(core_dirs(root), follows, templates)
    git(root, "sparse-checkout", "set", "--cone", *patterns)
    return patterns


def untrack(root: Path, paths: list[str]) -> list[str]:
    """Stop tracking paths without touching the files on disk."""
    done = []
    for path in paths:
        if git(root, "ls-files", "--", path).stdout.strip():
            git(root, "rm", "-r", "-q", "-f", "--cached", "--", path)  # -f with --cached touches only the index
            done.append(path)
    return done


def stage(root: Path) -> None:
    patterns = apply_sparse(root, dev.read_follow(root))
    git(root, "add", "-u")
    for pattern in patterns:
        if (root / pattern).exists() and not _ignored(root, pattern + "/"):
            git(root, "add", "-A", "--", pattern)
    for f in sorted(root.iterdir()):
        if f.is_file() and not _ignored(root, f.name):
            git(root, "add", "--", f.name)


def commit(root: Path, message: str) -> bool:
    if git(root, "diff", "--cached", "--quiet", check=False).returncode == 0:
        return False
    git(root, "commit", "-q", "-m", message)
    return True


def register(root: Path, status: str | None = None) -> Path:
    home = claude_home()
    claude_dir = home / ".claude"
    return dev.write_registry(root, dev.ensure_identity(root), follows=dev.read_follow(root),
                              plugins=dev.plugin_rows(claude_dir, claude_dir / "settings.json"),
                              mcps=dev.mcp_rows(home / ".claude.json", root, claude_dir),
                              now=datetime.now(), os_name=dev.os_label(), status=status)


def items(root: Path, ref: str) -> dict[str, list[str]]:
    return {kind: sorted(d for d in tree_dirs(root, ref, kind) if not d.startswith("_")) for kind in OPT_IN}


def local_items(root: Path) -> dict[str, list[str]]:
    return {kind: sorted(p.name for p in (root / kind).iterdir() if p.is_dir() and not p.name.startswith("_"))
            if (root / kind).is_dir() else [] for kind in OPT_IN}


def _offline(err: str) -> bool:
    return any(s in err for s in ("Could not resolve host", "unable to access", "Connection", "Network is unreachable"))


def push(root: Path) -> dict:
    proc = git(root, *auth_args(sync_cfg(root)), "push", "-u", "origin", f"HEAD:{BRANCH}", check=False)
    err = proc.stderr.strip()
    if proc.returncode == 0:
        cfg = sync_cfg(root)
        cfg["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        write_cfg(root, cfg)
        return {"status": "pushed"}
    if "memory-core sync:" in err or "pre-push" in err:
        return {"status": "blocked", "reason": err}
    if "rejected" in err or "fetch first" in err or "non-fast-forward" in err:
        return {"status": "rejected"}
    return {"status": "offline" if _offline(err) else "failed", "reason": err}


def _pending_file(root: Path) -> Path:
    return git_path(root, PENDING)


def _merging(root: Path) -> bool:
    return has_ref(root, "MERGE_HEAD")


def _busy(root: Path) -> dict | None:
    """Nothing may stage, save or move files while merge questions are open or setup is unfinished."""
    if sync_cfg(root).get("state") == "pending":
        return {"status": "setup-incomplete", "reason": "sync setup was not finished — run 'sync setup' again"}
    pending = _pending_file(root)
    if pending.is_file():
        return {"status": "needs-answers", **json.loads(pending.read_text(encoding="utf-8"))}
    if _merging(root) or out(root, "diff", "--name-only", "--diff-filter=U"):
        return {"status": "needs-answers", "units": [],
                "reason": "a merge is unfinished — run 'sync' to ask again, or 'undo sync'"}
    return None


def hook_file(root: Path) -> Path:
    common = Path(out(root, "rev-parse", "--git-common-dir"))
    return (common if common.is_absolute() else root / common) / "hooks" / "pre-push"


# ---------------------------------------------------------------- setup

def _probe_remote(root: Path, remote: str, cfg: dict) -> tuple[bool, str | None]:
    probe = "refs/memory-core/probe"
    fetch = git(root, *auth_args(cfg), "fetch", "-q", remote, f"+refs/heads/{BRANCH}:{probe}", check=False)
    if fetch.returncode != 0:
        missing = "couldn't find remote ref" in fetch.stderr
        return missing, None
    kind = git(root, "show", f"{probe}:.memory-core/kind", check=False).stdout.strip() or None
    git(root, "update-ref", "-d", probe, check=False)
    return True, kind or "unknown"


def cmd_setup(root: Path, remote: str, account: str, name: str | None = None, visibility_fn=gh_visibility) -> dict:
    if guard.repo_kind(root) == "framework":
        return {"status": "refused", "reason": "this is the framework repo — sync is for context installs only"}
    if sync_cfg(root).get("remote") and sync_cfg(root).get("state", "active") == "active":
        return {"status": "refused", "reason": "sync is already set up on this device — see 'sync status'"}
    hooks_path = git(root, "config", "--get", "core.hooksPath", check=False).stdout.strip()
    if hooks_path:
        return {"status": "refused",
                "reason": f"core.hooksPath is set ({hooks_path}) — the sync guard would land in a shared hooks "
                          "folder and block other repos. Unset it for this repo first"}
    visibility = visibility_fn(remote, account)
    ok, reason = guard.remote_is_safe(remote, guard.DEFAULT_DENY, visibility)
    if not ok:
        return {"status": "refused", "reason": reason}
    cfg = {"remote": remote, "account": account, "visibility": visibility or "local",
           "deny": ",".join(guard.DEFAULT_DENY), "last_sync": "never", "state": "pending"}
    reachable, remote_kind = _probe_remote(root, remote, cfg)
    if not reachable:
        return {"status": "unreachable", "reason": f"cannot fetch {remote}"}
    if remote_kind == "framework":
        return {"status": "refused", "reason": f"{remote} holds a framework repo — context never goes there"}
    guard.set_kind(root, "context")
    ensure_gitfiles(root)
    dev.ensure_identity(root, name)
    write_cfg(root, cfg)
    has_origin = git(root, "remote", "get-url", "origin", check=False).returncode == 0
    git(root, "remote", "set-url" if has_origin else "add", "origin", remote)
    guard.install_hook(hook_file(root))
    if remote_kind is None:
        return {"status": "empty-remote", "local": local_items(root)}
    git(root, *auth_args(cfg), "fetch", "-q", "origin")
    return {"status": "remote-has-content", "local": local_items(root), "remote": items(root, f"origin/{BRANCH}")}


def _activate(root: Path) -> None:
    cfg = sync_cfg(root)
    cfg["state"] = "active"
    write_cfg(root, cfg)


def _start_following(root: Path, projects: list[str], ecosystems: list[str]) -> dict | None:
    chosen = {"project-management": list(projects), "ecosystem": list(ecosystems)}
    for kind in OPT_IN:
        for slug in local_items(root)[kind]:
            if slug not in chosen[kind] and has_ref(root, "HEAD") and \
                    out(root, "log", "--oneline", "-1", "HEAD", "--", f"{kind}/{slug}"):
                return {"status": "refused",
                        "reason": f"{kind}/{slug} is already in this repo's history, so uploading would publish it. "
                                  "Tick it, or remove it from history before setting up sync"}
    untrack(root, list(MACHINE_ONLY))
    untrack(root, [f"{kind}/{slug}" for kind in OPT_IN for slug in local_items(root)[kind]
                   if slug not in chosen[kind]])
    dev.write_follow(root, chosen)
    register(root)
    stage(root)
    commit(root, f"sync: {dev.ensure_identity(root)['name']} — first upload")
    return None


def cmd_first_upload(root: Path, projects: list[str], ecosystems: list[str]) -> dict:
    refused = _start_following(root, projects, ecosystems)
    if refused:
        return refused
    result = push(root)
    if result["status"] == "pushed":
        _activate(root)
    return result


def cmd_first_merge(root: Path, projects: list[str], ecosystems: list[str]) -> dict:
    refused = _start_following(root, projects, ecosystems)
    if refused:
        return refused
    _activate(root)
    return cmd_pull(root, allow_unrelated=True)


def cmd_join(root: Path, name: str | None = None, account: str = "", visibility_fn=gh_visibility) -> dict:
    if (guard.repo_kind(root) or kind_at(root)) != "context":
        return {"status": "refused", "reason": "not a memory-core context clone (.memory-core/kind is not 'context')"}
    hooks_path = git(root, "config", "--get", "core.hooksPath", check=False).stdout.strip()
    if hooks_path:
        return {"status": "refused", "reason": f"core.hooksPath is set ({hooks_path}) — unset it for this repo first"}
    remote = out(root, "remote", "get-url", "origin")
    visibility = visibility_fn(remote, account)
    ok, reason = guard.remote_is_safe(remote, guard.DEFAULT_DENY, visibility)
    if not ok:
        return {"status": "refused", "reason": reason}
    identity = dev.ensure_identity(root, name)
    write_cfg(root, {"remote": remote, "account": account, "visibility": visibility or "local",
                     "deny": ",".join(guard.DEFAULT_DENY), "last_sync": "never", "state": "active"})
    guard.install_hook(hook_file(root))
    dev.write_follow(root, dev.read_follow(root))
    register(root)
    stage(root)
    commit(root, f"sync: {identity['name']} — register device")
    result = push(root)
    result["available"] = items(root, "HEAD")
    return result


# ---------------------------------------------------------------- follow

def cmd_follow(root: Path, kind: str, slug: str) -> dict:
    busy = _busy(root)
    if busy:
        return busy
    if slug not in items(root, "HEAD")[kind]:
        return {"status": "not-found", "available": items(root, "HEAD")[kind]}
    follows = dev.read_follow(root)
    follows[kind] = sorted(set(follows[kind]) | {slug})
    dev.write_follow(root, follows)
    apply_sparse(root, follows)
    return {"status": "followed", "path": f"{kind}/{slug}"}


def cmd_unfollow(root: Path, kind: str, slug: str) -> dict:
    busy = _busy(root)
    if busy:
        return busy
    path = f"{kind}/{slug}"
    if git(root, "status", "--porcelain", "--", path).stdout.strip():
        return {"status": "refused", "reason": f"{path} has changes not yet saved"}
    ignored = [line for line in git(root, "status", "--porcelain", "--ignored", "--", path).stdout.splitlines()
               if line.startswith("!!") and not line.rstrip().endswith(".DS_Store")]
    if ignored:
        return {"status": "refused", "reason": f"{path} holds ignored files that would be lost: "
                                               + ", ".join(line[3:] for line in ignored[:5])}
    if has_ref(root, f"origin/{BRANCH}") and out(root, "log", "--oneline", f"origin/{BRANCH}..HEAD", "--", path):
        return {"status": "refused", "reason": f"{path} has saved changes not yet uploaded — run sync first"}
    follows = dev.read_follow(root)
    follows[kind] = [s for s in follows[kind] if s != slug]
    dev.write_follow(root, follows)
    apply_sparse(root, follows)
    return {"status": "unfollowed", "path": path}


def cmd_upload(root: Path, kind: str, slug: str) -> dict:
    busy = _busy(root)
    if busy:
        return busy
    if not (root / kind / slug).is_dir():
        return {"status": "not-found", "path": f"{kind}/{slug}"}
    if slug in items(root, "HEAD")[kind]:
        return {"status": "already-tracked", "hint": f"follow {kind} {slug}"}
    follows = dev.read_follow(root)
    follows[kind] = sorted(set(follows[kind]) | {slug})
    dev.write_follow(root, follows)
    apply_sparse(root, follows)
    git(root, "add", "-A", "--", f"{kind}/{slug}")
    commit(root, f"sync: {dev.ensure_identity(root)['name']} — upload {kind} {slug}")
    return push(root)


# ---------------------------------------------------------------- save / pull

def cmd_save(root: Path, label: str) -> dict:
    if not sync_cfg(root).get("remote"):
        return {"status": "not-set-up"}
    busy = _busy(root)
    if busy:
        return busy
    register(root)
    stage(root)
    committed = commit(root, f"sync: {dev.ensure_identity(root)['name']} — {label}")
    result = push(root)
    result["committed"] = committed
    return result


def _stage_bytes(root: Path, n: int, path: str) -> bytes | None:
    proc = subprocess.run(["git", "-C", str(root), "show", f":{n}:{path}"], capture_output=True)
    return proc.stdout if proc.returncode == 0 else None


def _as_text(data: bytes | None) -> str | None:
    if data is None:
        return None
    if b"\0" in data:
        raise UnicodeDecodeError("utf-8", data, 0, 1, "binary")
    return data.decode("utf-8")


def _scoped_choices(choices: dict, path: str) -> dict:
    scoped = dict(choices.get("*", {}))
    scoped.update(choices.get(path, {}))
    return scoped


def _write(root: Path, path: str, text: str | None) -> None:
    target = root / path
    if text is None or text == "":
        if target.exists():
            target.unlink()
        git(root, "rm", "-q", "--cached", "--ignore-unmatch", "--", path)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    git(root, "add", "--", path)


def _log_level(path: str) -> int | None:
    for pattern, level in LOG_FILES.items():
        if fnmatch.fnmatch(path, pattern):
            return level
    return None


def _settle_path(root: Path, path: str, scoped: dict, units: list) -> bool:
    """Resolve one conflicted path. Returns True when it regenerates generated files."""
    raw = [_stage_bytes(root, n, path) for n in (1, 2, 3)]
    if path == "AGENTS.md" or path.startswith("outputs/"):
        git(root, "checkout", "--ours", "--", path)
        git(root, "add", "--", path)
        return True
    try:
        base, ours, theirs = (_as_text(r) for r in raw)
    except UnicodeDecodeError:
        choice = scoped.get("(binary)", scoped.get("*"))
        if choice in ("ours", "theirs") and raw[1] is not None and raw[2] is not None:
            git(root, "checkout", f"--{choice}", "--", path)
            git(root, "add", "--", path)
        else:
            sizes = [f"binary, {len(r)} bytes" if r is not None else None for r in raw]
            units.append(mrg.Unit(path, "(binary)", *sizes))
        return False
    if ours is None or theirs is None:
        picked = mrg._choose(scoped.get("(deleted)", scoped.get("*")), ours or "", theirs or "")
        if picked is None:
            units.append(mrg.Unit(path, "(deleted)", base, ours, theirs))
        else:
            _write(root, path, picked)
        return False
    if path == CURRENT_SESSION:
        merged = mrg.merge_current_session(base or "", ours, theirs, choices=scoped)
        if merged.conflicts:
            units.extend(mrg.session_units(path, base or "", ours, theirs, merged.conflicts))
            return False
        _write(root, path, merged.text)
        if merged.archived:
            archive = root / SESSION_ARCHIVE
            current = archive.read_text(encoding="utf-8") if archive.is_file() else "# Session Archive\n\n"
            _write(root, SESSION_ARCHIVE, mrg.prepend_to_archive(current, merged.archived))
        return False
    result = mrg.three_way(path, base or "", ours, theirs, scoped)
    if result.text is None:
        units.extend(result.conflicts)
    else:
        _write(root, path, result.text)
    return False


def _settle(root: Path, ctx: dict, choices: dict | None = None) -> dict:
    choices = choices or {}
    units: list[mrg.Unit] = []
    regenerate = False
    try:
        for path in [p for p in out(root, "diff", "--name-only", "--diff-filter=U").splitlines() if p]:
            regenerate |= _settle_path(root, path, _scoped_choices(choices, path), units)
    except Exception as exc:  # never leave a half-settled merge behind
        git(root, "merge", "--abort", check=False)
        pending = _pending_file(root)
        if pending.is_file():
            pending.unlink()
        return {"status": "failed", "reason": f"merge stopped and was undone: {exc}"}
    if units:
        payload = {**ctx, "units": [asdict(u) for u in units]}
        _pending_file(root).write_text(json.dumps(payload), encoding="utf-8")
        return {"status": "needs-answers", "units": payload["units"], "backup": ctx["tag"]}
    return _finish(root, ctx, regenerate)


def _changed(root: Path, a: str, b: str) -> set[str]:
    return {p for p in out(root, "diff", "--name-only", a, b).splitlines() if p}


def _finish(root: Path, ctx: dict, regenerate: bool) -> dict:
    target = "MERGE_HEAD" if _merging(root) else "HEAD"
    changed = sorted(_changed(root, ctx["before"], target))
    both = _changed(root, ctx["base"], ctx["before"]) & _changed(root, ctx["base"], ctx["theirs"])
    for path in sorted(both):
        level = _log_level(path)
        f = root / path
        if level and f.is_file():
            text = f.read_text(encoding="utf-8")
            tidy = mrg.sort_log_sections(text, level)
            if tidy != text:
                _write(root, path, tidy)
    name = dev.ensure_identity(root)["name"]
    if _merging(root):
        git(root, "commit", "-q", "--no-edit", "--cleanup=strip")
    else:
        commit(root, f"sync: {name} — tidy logs")
    pending = _pending_file(root)
    if pending.is_file():
        pending.unlink()
    apply_sparse(root, dev.read_follow(root))
    if "memory-core.yaml" in changed:
        regenerate = True
    return {"status": "merged", "changed": changed, "regenerate": regenerate, "backup": ctx["tag"]}


def cmd_pull(root: Path, allow_unrelated: bool = False) -> dict:
    cfg = sync_cfg(root)
    if not cfg.get("remote"):
        return {"status": "not-set-up"}
    busy = _busy(root)
    if busy and busy["status"] == "needs-answers" and not _pending_file(root).is_file():
        git(root, "merge", "--abort", check=False)  # interrupted before any question was saved: start over
        busy = _busy(root)
    if busy:
        return busy
    name = dev.ensure_identity(root)["name"]
    stage(root)
    commit(root, f"sync: {name} — local changes before sync")
    fetch = git(root, *auth_args(cfg), "fetch", "-q", "origin", check=False)
    if fetch.returncode != 0:
        return {"status": "offline" if _offline(fetch.stderr) else "failed", "reason": fetch.stderr.strip()}
    if not has_ref(root, f"origin/{BRANCH}"):
        return {"status": "up-to-date"}
    if has_ref(root, "HEAD") and git(root, "merge-base", "--is-ancestor", f"origin/{BRANCH}", "HEAD",
                                     check=False).returncode == 0:
        return {"status": "up-to-date"}
    before = out(root, "rev-parse", "HEAD")
    theirs = out(root, "rev-parse", f"origin/{BRANCH}")
    base = git(root, "merge-base", "HEAD", theirs, check=False).stdout.strip() or EMPTY_TREE
    tag = f"sync-backup/{name}/{datetime.now().strftime('%Y%m%d-%H%M%S-%f')}"
    git(root, "tag", tag)
    args = ["merge", "--no-edit", "-m", f"sync: {name} — merge"]
    if allow_unrelated:
        args.append("--allow-unrelated-histories")
    merged = git(root, *args, theirs, check=False)
    if merged.returncode != 0 and not out(root, "diff", "--name-only", "--diff-filter=U"):
        git(root, "merge", "--abort", check=False)
        return {"status": "failed", "reason": (merged.stderr or merged.stdout).strip()}
    return _settle(root, {"before": before, "tag": tag, "base": base, "theirs": theirs})


def cmd_resolve(root: Path, choices: dict) -> dict:
    pending = _pending_file(root)
    if not pending.is_file():
        return {"status": "up-to-date"}
    state = json.loads(pending.read_text(encoding="utf-8"))
    return _settle(root, {k: state[k] for k in ("before", "tag", "base", "theirs")}, choices)


def cmd_undo(root: Path) -> dict:
    name = dev.ensure_identity(root)["name"]
    if _merging(root):
        git(root, "merge", "--abort", check=False)
        pending = _pending_file(root)
        if pending.is_file():
            pending.unlink()
        return {"status": "restored", "to": "the state before the unfinished merge"}
    tags = out(root, "tag", "--list", f"sync-backup/{name}/*", "--sort=-refname").splitlines()
    if not tags:
        return {"status": "nothing-to-undo"}
    tag = tags[0]
    if git(root, "status", "--porcelain").stdout.strip():
        return {"status": "refused", "reason": "there are unsaved changes — save or discard them before undoing"}
    if git(root, "merge-base", "--is-ancestor", tag, "HEAD", check=False).returncode != 0:
        return {"status": "refused", "reason": f"{tag} is not behind the current state — nothing to undo"}
    head = out(root, "rev-parse", "HEAD")
    if head != out(root, "rev-parse", tag) and has_ref(root, f"origin/{BRANCH}") and \
            git(root, "merge-base", "--is-ancestor", "HEAD", f"origin/{BRANCH}", check=False).returncode == 0:
        return {"status": "refused",
                "reason": "that sync was already uploaded — undoing it needs a revert commit, not a reset"}
    later = [s for s in out(root, "log", "--first-parent", "--format=%s", f"{tag}..HEAD").splitlines()
             if not s.startswith((f"sync: {name} — merge", f"sync: {name} — tidy logs"))]
    if later:
        return {"status": "refused", "reason": "there is newer work since that sync: " + "; ".join(later[:3])}
    git(root, "reset", "-q", "--hard", tag)
    return {"status": "restored", "to": tag}


# ---------------------------------------------------------------- status / registry

def cmd_status(root: Path, fetch: bool = True) -> dict:
    cfg = sync_cfg(root)
    if fetch and cfg.get("remote"):
        git(root, *auth_args(cfg), "fetch", "-q", "origin", check=False)
    remote_ref = f"origin/{BRANCH}" if has_ref(root, f"origin/{BRANCH}") else "HEAD"
    ahead = behind = 0
    if remote_ref != "HEAD":
        ahead, behind = (int(n) for n in out(root, "rev-list", "--left-right", "--count",
                                             f"HEAD...{remote_ref}").split())
    available = items(root, remote_ref)
    following = dev.read_follow(root)
    local = local_items(root)
    local_only = {k: [s for s in local[k] if s not in available[k] and s not in following[k]] for k in OPT_IN}
    devices = dev.read_registry(root)
    return {
        "status": "ok" if cfg.get("remote") else "not-set-up",
        "remote": cfg.get("remote", ""), "last_sync": cfg.get("last_sync", ""),
        "ahead": ahead, "behind": behind,
        "available": available, "following": following, "local_only": local_only,
        "devices": [{k: v for k, v in d.items() if k in ("id", "name", "status", "last_sync")} for d in devices],
        "differences": dev.registry_differences(devices),
    }


def cmd_retire(root: Path, device: str) -> dict:
    for d in dev.read_registry(root):
        if device in (d["name"], d["id"]):
            text = d["path"].read_text(encoding="utf-8").replace("**Status**: active", "**Status**: retired")
            d["path"].write_text(text, encoding="utf-8")
            git(root, "add", "--", str(d["path"].relative_to(root)))
            commit(root, f"sync: {dev.ensure_identity(root)['name']} — retire device {d['name']}")
            result = push(root)
            result["retired"] = d["name"]
            return result
    return {"status": "not-found", "device": device}


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sync_git.py")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = parser.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("setup")
    s.add_argument("remote")
    s.add_argument("--account", default="")
    s.add_argument("--name")
    for name in ("first-upload", "first-merge"):
        s = sub.add_parser(name)
        s.add_argument("--projects", default="")
        s.add_argument("--ecosystems", default="")
    s = sub.add_parser("join")
    s.add_argument("--account", default="")
    s.add_argument("--name")
    for name in ("follow", "unfollow", "upload"):
        s = sub.add_parser(name)
        s.add_argument("kind", choices=["project", "ecosystem"])
        s.add_argument("slug")
    s = sub.add_parser("save")
    s.add_argument("label")
    s = sub.add_parser("pull")
    s.add_argument("--allow-unrelated", action="store_true")
    s = sub.add_parser("resolve")
    s.add_argument("choices", help="JSON object, or @path to a JSON file")
    sub.add_parser("status")
    sub.add_parser("undo")
    sub.add_parser("register")
    s = sub.add_parser("retire")
    s.add_argument("device")
    s = sub.add_parser("migrate-paths")
    s.add_argument("--write", action="store_true")
    a = parser.parse_args(argv)
    root = Path(a.root).resolve()
    kinds = {"project": "project-management", "ecosystem": "ecosystem"}

    def split(text: str) -> list[str]:
        return [t.strip() for t in text.split(",") if t.strip()]

    try:
        if a.cmd == "setup":
            result = cmd_setup(root, a.remote, a.account, a.name)
        elif a.cmd == "first-upload":
            result = cmd_first_upload(root, split(a.projects), split(a.ecosystems))
        elif a.cmd == "first-merge":
            result = cmd_first_merge(root, split(a.projects), split(a.ecosystems))
        elif a.cmd == "join":
            result = cmd_join(root, a.name, a.account)
        elif a.cmd in ("follow", "unfollow", "upload"):
            result = {"follow": cmd_follow, "unfollow": cmd_unfollow, "upload": cmd_upload}[a.cmd](
                root, kinds[a.kind], a.slug)
        elif a.cmd == "save":
            result = cmd_save(root, a.label)
        elif a.cmd == "pull":
            result = cmd_pull(root, a.allow_unrelated)
        elif a.cmd == "resolve":
            raw = Path(a.choices[1:]).read_text(encoding="utf-8") if a.choices.startswith("@") else a.choices
            result = cmd_resolve(root, json.loads(raw))
        elif a.cmd == "status":
            result = cmd_status(root)
        elif a.cmd == "undo":
            result = cmd_undo(root)
        elif a.cmd == "register":
            result = {"status": "ok", "path": str(register(root))}
        elif a.cmd == "retire":
            result = cmd_retire(root, a.device)
        else:
            found = dev.migrate_general_paths(root, write=a.write)
            result = {"status": "ok", "written": a.write,
                      "paths": [{"project": p, "key": k, "path": v} for p, k, v in found]}
    except SyncError as exc:
        result = {"status": "error", "reason": str(exc)}
    print(json.dumps(result, indent=2, default=str))
    return 1 if result.get("status") in FAILURE else 0


if __name__ == "__main__":
    sys.exit(main())
