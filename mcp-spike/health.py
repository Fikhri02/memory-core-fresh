"""
SPIKE — drift detection for a memory-core repo.

Every check here corresponds to a bug that actually occurred, found by hand:
a feature 100% complete but never moved out of Development/, timelines four
months stale while work continued in notes/, symlinks pointing at a folder that
no longer existed, memory files missing from MEMORY.md so they never loaded,
and skills present as SKILL.md but absent from the spec — which made
`generate.py codex` a silent delete.

Dependency-free on purpose: the YAML scan is a line match, not a parse.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

STALE_DAYS = 60
DATE_HEADER = re.compile(r"^##\s+(\d{4})-(\d{2})-(\d{2})\s*$", re.M)
TASK_LINE = re.compile(r"^- \[( |x)\]", re.M)
INDEX_LINK = re.compile(r"\]\(([^)]+\.md)\)")
SPEC_SKILL_KEY = re.compile(r"^  ([a-z][a-z0-9-]*):\s*$", re.M)


@dataclass
class Finding:
    check: str
    severity: str          # "high" | "medium" | "low"
    path: str
    detail: str


def _rel(p: Path, root: Path) -> str:
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def complete_features_still_in_development(root: Path) -> list[Finding]:
    """A feature with every task checked that never moved to Completed/."""
    out = []
    for f in sorted(root.glob("project-management/*/**/Development/*.md")):
        marks = TASK_LINE.findall(f.read_text(encoding="utf-8"))
        if not marks:
            continue
        done = sum(1 for m in marks if m == "x")
        if done == len(marks):
            out.append(
                Finding(
                    "complete_feature_in_development",
                    "medium",
                    _rel(f, root),
                    f"all {done} tasks checked but still in Development/",
                )
            )
    return out


def stale_timelines(root: Path, today: date | None = None) -> list[Finding]:
    """A project whose Timeline.md has not been touched in STALE_DAYS."""
    today = today or date.today()
    out = []
    for f in sorted(root.glob("project-management/*/Timeline.md")):
        if f.parent.name.startswith("_"):
            continue
        dates = [date(int(y), int(m), int(d)) for y, m, d in DATE_HEADER.findall(f.read_text(encoding="utf-8"))]
        if not dates:
            out.append(Finding("stale_timeline", "low", _rel(f, root), "no dated entries at all"))
            continue
        age = (today - max(dates)).days
        if age > STALE_DAYS:
            out.append(
                Finding("stale_timeline", "low", _rel(f, root), f"last entry {max(dates)} — {age} days ago")
            )
    return out


def broken_symlinks(root: Path) -> list[Finding]:
    out = []
    for f in sorted(root.rglob("*")):
        if ".git" in f.parts:
            continue
        if f.is_symlink() and not f.exists():
            out.append(
                Finding("broken_symlink", "high", _rel(f, root), f"points at missing {f.readlink()}")
            )
    return out


def memory_index_drift(root: Path) -> list[Finding]:
    """Files not listed in MEMORY.md never load; listed files that vanished are dead links."""
    mem = root / "memory"
    index = mem / "MEMORY.md"
    if not index.is_file():
        return []

    text = index.read_text(encoding="utf-8")
    linked = set(INDEX_LINK.findall(text))
    on_disk = {f.name for f in mem.glob("*.md") if f.name != "MEMORY.md"}

    out = []
    for name in sorted(on_disk - linked):
        out.append(
            Finding("memory_not_indexed", "high", f"memory/{name}", "not in MEMORY.md — it never loads")
        )
    for name in sorted(linked - on_disk):
        out.append(
            Finding("memory_index_dangling", "medium", f"memory/{name}", "listed in MEMORY.md but the file is gone")
        )
    return out


def skills_missing_from_spec(root: Path) -> list[Finding]:
    """A skill absent from the spec is invisible to every non-Claude platform,
    and regenerating AGENTS.md would silently delete it."""
    spec = root / "memory-core.yaml"
    if not spec.is_file():
        spec = root / "memory-core-template.yaml"
    skills_dir = root / "plugins" / "violet-skills" / "skills"
    if not spec.is_file() or not skills_dir.is_dir():
        return []

    text = spec.read_text(encoding="utf-8")
    body = text.split("\nskills:", 1)[-1]
    in_spec = set(SPEC_SKILL_KEY.findall(body))
    on_disk = {d.name for d in skills_dir.iterdir() if (d / "SKILL.md").is_file()}

    return [
        Finding(
            "skill_missing_from_spec",
            "high",
            f"plugins/violet-skills/skills/{name}/",
            "not in the spec — invisible to Codex/ChatGPT/Gemini, and `generate.py codex` would drop it",
        )
        for name in sorted(on_disk - in_spec)
    ]


ECOSYSTEM_MEMBER_ROW = re.compile(r"^\|\s*([^|]+?)\s*\|[^|]*\|\s*`?([^|`]+?)`?\s*\|", re.M)
FRONTMATTER_UPDATED = re.compile(r"^updated:\s*(\d{4})-(\d{2})-(\d{2})\s*$", re.M)
ECOSYSTEM_STALE_DAYS = 180


def ecosystem_drift(root: Path, today: date | None = None) -> list[Finding]:
    """An ecosystem map that has gone stale or points at projects that no longer exist."""
    today = today or date.today()
    eco_dir = root / "ecosystem"
    if not eco_dir.is_dir():
        return []

    pm = root / "project-management"
    known = {d.name for d in pm.iterdir() if d.is_dir() and not d.name.startswith("_")} if pm.is_dir() else set()

    out: list[Finding] = []
    membership: dict[str, list[str]] = {}

    for d in sorted(p for p in eco_dir.iterdir() if p.is_dir()):
        if not (d / "map.md").is_file():
            out.append(Finding("ecosystem_no_map", "high", _rel(d, root),
                               "ecosystem folder has no map.md"))

    for f in sorted(eco_dir.glob("*/map.md")):
        text = f.read_text(encoding="utf-8")
        rel = _rel(f, root)

        m = FRONTMATTER_UPDATED.search(text)
        if not m:
            out.append(Finding("ecosystem_no_updated", "medium", rel, "no `updated:` field — staleness cannot be tracked"))
        else:
            age = (today - date(int(m.group(1)), int(m.group(2)), int(m.group(3)))).days
            if age > ECOSYSTEM_STALE_DAYS:
                out.append(Finding("ecosystem_stale", "low", rel, f"not updated in {age} days"))

        section = text.split("## Members", 1)[-1].split("## ", 1)[0] if "## Members" in text else ""
        for _project, documented in ECOSYSTEM_MEMBER_ROW.findall(section):
            documented = documented.strip()
            # skip the header row, the |---|---| separator, and "no entry" markers
            if documented in ("", "—", "-", "Documented") or set(documented) <= set("-: "):
                continue
            membership.setdefault(documented, []).append(f.parent.name)
            if known and documented not in known:
                out.append(
                    Finding("ecosystem_member_missing", "high", rel,
                            f"member references `{documented}`, which is not a project under project-management/")
                )

    for project, ecosystems in sorted(membership.items()):
        if len(ecosystems) > 1:
            out.append(
                Finding("ecosystem_duplicate_member", "medium", f"ecosystem/ ({project})",
                        f"appears in {len(ecosystems)} ecosystems: {', '.join(sorted(ecosystems))}")
            )
    return out


NOTE_MEMBERS = re.compile(r"^members:\s*\[([^\]]*)\]\s*$", re.M)


def ecosystem_feature_note_drift(root: Path) -> list[Finding]:
    """A feature note claiming a member its ecosystem map does not list."""
    eco_dir = root / "ecosystem"
    if not eco_dir.is_dir():
        return []

    out: list[Finding] = []
    for map_file in sorted(eco_dir.glob("*/map.md")):
        features = map_file.parent / "features"
        if not features.is_dir():
            continue

        text = map_file.read_text(encoding="utf-8")
        section = text.split("## Members", 1)[-1].split("## ", 1)[0] if "## Members" in text else ""
        listed = set()
        for _project, documented in ECOSYSTEM_MEMBER_ROW.findall(section):
            documented = documented.strip()
            if documented in ("", "—", "-", "Documented") or set(documented) <= set("-: "):
                continue
            listed.add(documented)

        for note in sorted(features.glob("*.md")):
            m = NOTE_MEMBERS.search(note.read_text(encoding="utf-8"))
            if not m:
                continue
            for member in (x.strip() for x in m.group(1).split(",")):
                if member and member not in listed:
                    out.append(
                        Finding("ecosystem_feature_note_member_unknown", "medium", _rel(note, root),
                                f"names member `{member}`, which its ecosystem map does not list")
                    )
    return out


def run_all(root: Path) -> dict:
    findings: list[Finding] = []
    for check in (
        broken_symlinks,
        memory_index_drift,
        skills_missing_from_spec,
        ecosystem_drift,
        ecosystem_feature_note_drift,
        complete_features_still_in_development,
        stale_timelines,
    ):
        findings.extend(check(root))

    rank = {"high": 0, "medium": 1, "low": 2}
    findings.sort(key=lambda f: (rank[f.severity], f.check, f.path))

    counts: dict[str, int] = {}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1

    if findings:
        summary = f"{len(findings)} finding(s): " + ", ".join(
            f"{counts[s]} {s}" for s in ("high", "medium", "low") if s in counts
        )
    else:
        summary = "No drift detected."

    return {"summary": summary, "root": str(root), "findings": [asdict(f) for f in findings]}
