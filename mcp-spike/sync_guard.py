"""Guardrails that keep personal context out of the public framework repo. Stdlib only.

A context install carries `.memory-core/kind` = context. Its sync remote must be private and must
not be the framework repo; a pre-push hook re-checks that on every push.
"""

from __future__ import annotations

import re
import stat
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from sync_device import read_kv  # noqa: E402

MARKER = Path(".memory-core") / "kind"
DEFAULT_DENY = ["github.com/fikhri02/memory-core-fresh"]
SCP_LIKE = re.compile(r"^[\w.-]+@([\w.-]+):(.+)$")
HOST_PATH = re.compile(r"^([\w-]+(?:\.[\w-]+)+)/(.+)$")

HOOK = """#!/bin/sh
# memory-core sync guard — installed by sync setup.
# Blocks any push except to this memory's private sync remote, then runs the pre-push hook it replaced.
root="$(git rev-parse --show-toplevel)"
python3 "$root/mcp-spike/sync_guard.py" check-push "$2" || exit 1
replaced="$(dirname "$0")/pre-push.local"
if [ -x "$replaced" ]; then exec "$replaced" "$@"; fi
exit 0
"""
HOOK_MARK = "memory-core sync guard"


def repo_kind(root: Path) -> str | None:
    path = root / MARKER
    return path.read_text(encoding="utf-8").strip() if path.is_file() else None


def set_kind(root: Path, kind: str) -> None:
    path = root / MARKER
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(kind + "\n", encoding="utf-8")


def _host_and_path(url: str) -> tuple[str, str] | None:
    text = url.strip()
    m = SCP_LIKE.match(text)
    if m:
        return m.group(1), m.group(2)
    if "://" in text and not text.lower().startswith("file://"):
        parts = urlsplit(text)
        return (parts.hostname or ""), parts.path
    m = HOST_PATH.match(text)
    if m and not text.startswith((".", "/", "~")):
        return m.group(1), m.group(2)
    return None


def is_local(url: str) -> bool:
    return _host_and_path(url) is None


def normalise_remote(url: str) -> str:
    found = _host_and_path(url)
    if found is None:
        local = url.strip()
        if local.lower().startswith("file://"):
            local = local[7:]
        return str(Path(local).expanduser().resolve()).lower()
    host, path = found
    return f"{host.lower()}/{path.strip('/').removesuffix('.git').lower()}"


def remote_is_safe(url: str, deny: list[str], visibility: str | None,
                   configured: str | None = None) -> tuple[bool, str]:
    target = normalise_remote(url)
    if target in {normalise_remote(d) for d in deny}:
        return False, f"{url} is the framework repo — personal context never goes there"
    if configured and target != normalise_remote(configured):
        return False, f"{url} is not this memory's sync remote ({configured})"
    if is_local(url):
        return True, "local repository"
    if (visibility or "").upper() != "PRIVATE":
        state = (visibility or "of unknown visibility").lower()
        return False, f"{url} is {state} — the sync remote must be private"
    return True, "private remote"


def deny_list(sync_md: dict) -> list[str]:
    extra = [d.strip() for d in sync_md.get("deny", "").split(",") if d.strip()]
    return DEFAULT_DENY + extra


def check_push(root: Path, url: str) -> tuple[bool, str]:
    cfg = read_kv(root / "device" / "sync.md")
    if not cfg.get("remote"):
        return False, "sync is not set up on this device — run 'sync setup' first"
    return remote_is_safe(url, deny_list(cfg), cfg.get("visibility"), cfg["remote"])


def install_hook(hook_path: Path) -> Path:
    """Install the guard. A pre-push hook that is not ours is kept as pre-push.local and chained."""
    hook_path.parent.mkdir(parents=True, exist_ok=True)
    if hook_path.is_file() and HOOK_MARK not in hook_path.read_text(encoding="utf-8", errors="replace"):
        replaced = hook_path.with_name("pre-push.local")
        if not replaced.exists():
            hook_path.rename(replaced)
    hook_path.write_text(HOOK, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return hook_path


def main(argv: list[str]) -> int:
    if len(argv) == 3 and argv[1] == "check-push":
        ok, reason = check_push(Path(__file__).resolve().parents[1], argv[2])
        if not ok:
            print(f"memory-core sync: {reason}", file=sys.stderr)
        return 0 if ok else 1
    print("usage: sync_guard.py check-push <url>", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
