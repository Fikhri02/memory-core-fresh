"""Everything session-briefing gathers, in one call. Stdlib only.

The skill composes the brief; this module only collects facts that can be tested: the sync download,
own RAM (created if missing) with its Status and lint, the live git state of the repos RAM lists,
other laptops, learning flags and the career flag. Git state is always read live — RAM records which
repo and branch, never whether it is clean.

CLI (paths are relative to the memory root):
    python3 mcp-spike/brief.py [--root DIR] [--cwd DIR] [--no-sync]     prints one JSON object
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ram  # noqa: E402

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TIMELINE_ENTRY = re.compile(r"^## (\d{4}-\d{2}-\d{2})\s*$", re.M)
OPEN_LINE = re.compile(r"^- Open:\s*(.+)$", re.M)
ACTIVE = re.compile(r"\*\*Status\*\*:\s*active\b", re.I)
AWAITING = {"applied", "screening", "interview"}
INACTIVE = {"rejected", "withdrawn", "closed"}
STALE_DAYS = 7


def period(now: datetime) -> str:
    h = now.hour
    if 5 <= h < 12:
        return "morning"
    if 12 <= h < 17:
        return "afternoon"
    if 17 <= h < 21:
        return "evening"
    return "late night"


# ---------------------------------------------------------------- markdown helpers

def _cells(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _table(text: str, needed: tuple[str, ...]) -> list[dict[str, str]]:
    """Rows of the first pipe table whose header names every column in `needed`."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.lstrip().startswith("|") and all(n in _cells(line) for n in needed):
            header, rows = _cells(line), []
            for row in lines[i + 2:]:
                if not row.lstrip().startswith("|"):
                    break
                cells = _cells(row)
                rows.append({h: cells[i] if i < len(cells) else "" for i, h in enumerate(header)})
            return rows
    return []


def _first_file(folder: Path, *names: str) -> Path | None:
    return next((folder / n for n in names if (folder / n).is_file()), None)


def _date(text: str) -> date | None:
    m = DATE.search(text or "")
    return date.fromisoformat(m.group(0)) if m else None


# ---------------------------------------------------------------- flags

def career(root: Path, today: date) -> dict | None:
    folder = root / "career"
    if not folder.is_dir():
        return None
    tracker = folder / "tracker.md"
    rows = _table(tracker.read_text(encoding="utf-8"), ("Company", "Status", "Next action")) if tracker.is_file() else []
    ready = sum(1 for r in rows if r["Status"].lower() == "ready")
    awaiting = sum(1 for r in rows if r["Status"].lower() in AWAITING)
    due = []
    for r in rows:
        if r["Status"].lower() in INACTIVE:
            continue
        reached = [d for d in DATE.findall(r["Next action"]) if d <= today.isoformat()]
        if reached:
            due.append({"company": r["Company"], "date": reached[0], "action": r["Next action"]})
    open_ = []
    timeline = folder / "timeline.md"
    if timeline.is_file():
        text = timeline.read_text(encoding="utf-8")
        entries = list(TIMELINE_ENTRY.finditer(text))
        if entries:
            latest = max(range(len(entries)), key=lambda i: (entries[i].group(1), i))
            end = entries[latest + 1].start() if latest + 1 < len(entries) else len(text)
            open_ = [m.group(1).strip() for m in OPEN_LINE.finditer(text, entries[latest].end(), end)]
    return {"fire": bool(due or open_), "ready": ready, "awaiting": awaiting, "due": due, "open": open_}


def learning(root: Path, today: date) -> list[dict]:
    flags = []
    for topic in sorted((root / "learning").glob("*/")):
        if topic.name.startswith("_"):
            continue
        general = _first_file(topic, "General.md", "general.md")
        progress = _first_file(topic, "Progress.md", "progress.md")
        if not general or not progress or not ACTIVE.search(general.read_text(encoding="utf-8")):
            continue
        ages = []
        for r in _table(progress.read_text(encoding="utf-8"), ("Concept", "Confidence", "Last reviewed")):
            reviewed = _date(r["Last reviewed"])
            if r["Confidence"].lower() == "shaky" and reviewed and (today - reviewed).days >= STALE_DAYS:
                ages.append((today - reviewed).days)
        if ages:
            flags.append({"topic": topic.name, "shaky": len(ages), "oldest_days": max(ages)})
    return sorted(flags, key=lambda f: f["oldest_days"], reverse=True)


# ---------------------------------------------------------------- live git state

def _git(path: Path, *args: str) -> str | None:
    proc = subprocess.run(["git", "-C", str(path), *args], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def repo_state(path: str, expected_branch: str | None) -> dict:
    p = Path(path).expanduser()
    row = {"path": str(p), "expected_branch": expected_branch, "exists": False, "branch": None,
           "branch_matches": None, "dirty": None, "head": None}
    if not p.is_dir() or _git(p, "rev-parse", "--git-dir") is None:
        return row
    branch = _git(p, "symbolic-ref", "--short", "-q", "HEAD") or "(detached)"
    status = _git(p, "status", "--porcelain") or ""
    row.update(exists=True, branch=branch, dirty=len([ln for ln in status.splitlines() if ln.strip()]),
               head=_git(p, "log", "-1", "--format=%h %cs %s") or None,
               branch_matches=None if expected_branch is None else branch == expected_branch)
    return row


def _toplevel(cwd: Path) -> Path | None:
    here = cwd
    while not here.is_dir() and here != here.parent:
        here = here.parent
    top = _git(here, "rev-parse", "--show-toplevel")
    return Path(top).resolve() if top else None


def repos(ram_text: str, cwd: Path | None) -> list[dict]:
    """Live state of every repo RAM's Status lists, plus the working directory's repo if not listed."""
    rows = [repo_state(str(Path(r["path"]).expanduser()), r["branch"]) for r in ram.repos(ram_text)]
    top = _toplevel(Path(cwd)) if cwd else None
    seen = {Path(r["path"]).resolve() for r in rows}
    if top and top not in seen:
        rows.append(repo_state(str(top), None))
    return rows


# ---------------------------------------------------------------- RAM and sync

def _status(text: str) -> dict:
    span = ram.status_span(text)
    units = dict(ram.status_units(text[span[0]:span[1]])) if span else {}
    focus = None
    if units.get("Focus"):
        m = ram.STATUS_KEY.match(units["Focus"][0])
        focus = m.group(2).strip() if m and m.group(2).strip() not in ("", "—") else None
    loops = [ln[2:].strip() for ln in units.get("Open loops", [])[1:] if ln.startswith("- ")]
    return {"focus": focus, "open_loops": loops}


def _sync(root: Path, enabled: bool) -> dict:
    if not enabled:
        return {"status": "skipped"}
    if not (root / "device" / "sync.md").is_file():
        return {"status": "not-set-up"}
    import sync_git  # only when syncing: it needs git and the sync modules
    try:
        return sync_git.cmd_pull(root)
    except sync_git.SyncError as exc:
        return {"status": "error", "reason": str(exc)}


def gather(root: Path, cwd: Path | None = None, now: datetime | None = None, sync: bool = True) -> dict:
    now = now or datetime.now()
    synced = _sync(root, sync)  # before RAM is touched, so the download sees a clean tree
    path = ram.ensure(root)
    text = path.read_text(encoding="utf-8")
    header = ram.read_header(text) or {}
    return {
        "sync": synced,
        "time": {"now": now.strftime("%Y-%m-%d %H:%M %A"), "period": period(now)},
        "ram": {"path": ram.ram_rel(root), "last_activity": header.get("last_activity"),
                "last_session": header.get("last_session"), **_status(text), "check": ram.check(root)},
        "repos": repos(text, cwd),
        "others": ram.others(root)[:3],
        "learning": learning(root, now.date()),
        "career": career(root, now.date()),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="brief.py", description="Gather everything session-briefing needs")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--cwd", default=os.getcwd(), help="the working directory the session started in")
    ap.add_argument("--no-sync", action="store_true", help="skip the sync download")
    a = ap.parse_args(argv)
    print(json.dumps(gather(Path(a.root).resolve(), Path(a.cwd), sync=not a.no_sync), indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
