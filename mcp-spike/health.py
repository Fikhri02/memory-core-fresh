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

import hashlib
import json
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


# --- package markers -------------------------------------------------------
# Imported feature knowledge carries provenance in the file that holds it, so a
# region can be checked without consulting anything else. See
# notes/ecosystem-feature-migrations-spec.md, Decision 2.

PKG_OPEN = re.compile(r"^<!--\s*pkg:(\S+)\s+v(\d+)\s+sha:([0-9a-f]{8})\s*-->$", re.M)
PKG_SOURCE_LINE = re.compile(r"^source:\s*\{([^}]*)\}\s*$", re.M)
PKG_FIELD = re.compile(r"package:\s*([^,}\s]+)")
SHA_FIELD = re.compile(r"sha:\s*([0-9a-f]{8})")
FRONTMATTER_BLOCK = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
CODE_FENCE = re.compile(r"^```.*?^```", re.M | re.S)
PKG_SCAN_SKIP = {".git", ".venv", "__pycache__", "node_modules", "migrations"}


MACHINE_COLUMNS = {"local path", "location"}
CELL_SPLIT = re.compile(r"(?<!\\)\|")


ALIGN_CELL = re.compile(r"^(:?)-+(:?)$")


def _norm_separator(cell: str) -> str:
    sep = ALIGN_CELL.match(cell)
    return f"{sep.group(1)}---{sep.group(2)}" if sep else cell


MAP_PATH = re.compile(r"^ecosystem/[^/]+/map\.md$")


def _drop_columns(text: str, path: str = "") -> str:
    """Drop machine-bound table columns and normalise cell padding before hashing. Mirrors
    pkgstate.comparable: `Location` is machine-bound only in an ecosystem map."""
    machine = MACHINE_COLUMNS if MAP_PATH.match(path) else {"local path"}
    lines = text.split("\n")
    out: list[str] = []
    i = 0
    while i < len(lines):
        if not lines[i].lstrip().startswith("|"):
            out.append(lines[i])
            i += 1
            continue
        j = i
        while j < len(lines) and lines[j].lstrip().startswith("|"):
            j += 1
        table = lines[i:j]

        def cells(line: str) -> list[str]:
            return [c.strip() for c in CELL_SPLIT.split(line.strip())[1:-1]]

        drop = {k for k, c in enumerate(cells(table[0])) if c.lower() in machine}
        out += ["| " + " | ".join(_norm_separator(c) for k, c in enumerate(cells(r)) if k not in drop) + " |"
                for r in table]
        i = j
    return "\n".join(out)


def region_sha(content: str) -> str:
    """Hash of a region's content, insensitive to trailing whitespace and surrounding blank lines."""
    normalised = "\n".join(line.rstrip() for line in content.strip().splitlines())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:8]


HEADING_FENCE = re.compile(r"^(```|~~~)")


def _heading_section(text: str, heading: str) -> str | None:
    """One `## ` section of a Markdown file, heading line included. Mirrors pkgstate.heading_sections."""
    name: str | None = None
    buf: list[str] = []
    in_fence = False
    for line in text.split("\n"):
        if HEADING_FENCE.match(line):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            if name == heading:
                break
            name, buf = line[3:].strip(), [line]
            continue
        if name is not None:
            buf.append(line)
    return "\n".join(buf).rstrip("\n") + "\n" if name == heading else None


def _scannable_markdown(root: Path):
    for f in sorted(root.rglob("*.md")):
        if PKG_SCAN_SKIP & set(f.relative_to(root).parts):
            continue
        # Fenced blocks document the marker format; those examples are not installs.
        yield f, CODE_FENCE.sub("", f.read_text(encoding="utf-8"))


def _owned_regions(text: str):
    """Yield (package, recorded_sha, actual_content, closed) for every owned region."""
    m = FRONTMATTER_BLOCK.match(text)
    if m:
        line = PKG_SOURCE_LINE.search(m.group(1))
        if line:
            pkg = PKG_FIELD.search(line.group(1))
            sha = SHA_FIELD.search(line.group(1))
            if pkg and sha:
                yield pkg.group(1), sha.group(1), text[m.end():], True

    for open_marker in PKG_OPEN.finditer(text):
        package, _version, sha = open_marker.groups()
        close = text.find(f"<!-- /pkg:{package} -->", open_marker.end())
        if close == -1:
            yield package, sha, "", False
        else:
            yield package, sha, text[open_marker.end():close], True


def package_region_drift(root: Path) -> list[Finding]:
    """Imported knowledge edited locally — the next import of that package will conflict."""
    out: list[Finding] = []
    for f, text in _scannable_markdown(root):
        for package, recorded, content, closed in _owned_regions(text):
            if not closed:
                out.append(
                    Finding("package_marker_unclosed", "medium", _rel(f, root),
                            f"`{package}` region is opened but never closed")
                )
            elif region_sha(content) != recorded:
                out.append(
                    Finding("package_region_drift", "medium", _rel(f, root),
                            f"`{package}` region was edited locally since import "
                            f"(recorded sha:{recorded}, now sha:{region_sha(content)})")
                )
    return out


LEDGER_INSTALLED = {"applied", "partial", "conflict-resolved"}


def _ledger_imports(root: Path) -> set[str] | None:
    """Packages this machine has imported, from migrations/ledger.md. None when there is no ledger."""
    ledger = root / "migrations" / "ledger.md"
    if not ledger.is_file():
        return None
    found: set[str] = set()
    for line in ledger.read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in CELL_SPLIT.split(line.strip())[1:-1]]
        if len(cells) == 8 and cells[1] == "in" and cells[6] in LEDGER_INSTALLED:
            found.add(cells[2])
    return found


def package_orphan_marker(root: Path) -> list[Finding]:
    """A marker naming a package this machine has no record of importing."""
    imported = _ledger_imports(root)
    if imported is None:
        return []          # ledger is local and git-ignored — a fresh clone has nothing to judge against

    out: list[Finding] = []
    for f, text in _scannable_markdown(root):
        for package in sorted({p for p, _s, _c, _cl in _owned_regions(text)} - imported):
            out.append(
                Finding("package_orphan_marker", "low", _rel(f, root),
                        f"`{package}` region is installed, but no import of it is recorded in "
                        f"migrations/ledger.md")
            )
    return out


MANIFEST_ENTRY = re.compile(r'^\s*-\s*\{path:\s*("(?:[^"\\]|\\.)*"),\s*sha:\s*([0-9a-f]{8})\s*\}\s*$')


def package_manifest_drift(root: Path) -> list[Finding]:
    """Whole files or profile sections imported from a package and changed here since.
    Timelines are skipped: they grow locally by design and always merge on re-import."""
    out: list[Finding] = []
    manifests = root / "migrations" / "manifests"
    if not manifests.is_dir():
        return out
    for mf in sorted(manifests.glob("*.yaml")):
        package = mf.stem
        for line in mf.read_text(encoding="utf-8").splitlines():
            entry = MANIFEST_ENTRY.match(line)
            if not entry:
                continue
            target, recorded = json.loads(entry.group(1)), entry.group(2)
            path, _, heading = target.partition("#")
            if path.rsplit("/", 1)[-1] == "Timeline.md":
                continue
            f = root / path
            text = f.read_text(encoding="utf-8").replace("\r\n", "\n") if f.is_file() else None
            if text is not None and heading:
                text = _heading_section(text, heading)
            if text is None:
                out.append(Finding("package_manifest_drift", "low", path,
                                   f"`{package}` installed {target}, which has been removed here"))
                continue
            now = region_sha(_drop_columns(text, path))
            if now != recorded:
                out.append(Finding("package_manifest_drift", "medium", path,
                                   f"`{package}` {target} was edited here since import — the next "
                                   f"re-import will conflict (recorded sha:{recorded}, now sha:{now})"))
    return out


# --- learning topics -------------------------------------------------------
# learning/{topic}/Progress.md rows drive quizzes; a rated concept with no note cannot be quizzed.

LEARNING_ROW = re.compile(r"^\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|([^|\n]*)\|\s*$", re.M)
PROJECT_LINK = re.compile(r"^- `([^`]+)`", re.M)
MD_LINK_TARGET = re.compile(r"\]\(([^)]+)\)")
SEPARATOR_CELL = re.compile(r"^:?-+:?$")
RATED = {"shaky", "okay", "solid"}


def progress_rows(text: str) -> list[tuple[str, str, str, str, str]]:
    """Data rows of a Progress.md concept table, cells stripped. The header and separator are
    skipped; concept ids are taken in any shape, since only one skill path promises kebab-case."""
    rows = []
    for cells in LEARNING_ROW.findall(text):
        cells = tuple(c.strip() for c in cells)
        if cells[0].lower() == "concept" or SEPARATOR_CELL.match(cells[0]):
            continue
        rows.append(cells)
    return rows


def _rating(cell: str) -> str:
    """`**Shaky**` → shaky. Anything outside RATED (—, –, -, n/a, blank) counts as not yet studied."""
    return cell.strip("*_` ").lower()


def _note_path(cell: str) -> str:
    """A Note cell may be a bare path, a `backticked` path, or a [label](path) link."""
    link = MD_LINK_TARGET.search(cell)
    return (link.group(1) if link else cell).strip().strip("`")


def learning_drift(root: Path) -> list[Finding]:
    learning = root / "learning"
    if not learning.is_dir():
        return []
    pm = root / "project-management"
    out: list[Finding] = []
    for topic in sorted(d for d in learning.iterdir() if d.is_dir() and not d.name.startswith("_")):
        progress = topic / "Progress.md"
        if progress.is_file():
            for concept, _module, cell_rating, _reviewed, cell in progress_rows(progress.read_text(encoding="utf-8")):
                confidence = _rating(cell_rating)
                if confidence not in RATED:
                    continue
                note = _note_path(cell)
                if not note or not (topic / note).is_file():
                    out.append(
                        Finding("learning_note_missing", "medium", _rel(progress, root),
                                f"`{concept}` is rated {confidence} but its note {note or '(none)'} does not exist — it cannot be quizzed")
                    )
        projects = topic / "Projects.md"
        if projects.is_file():
            for name in PROJECT_LINK.findall(projects.read_text(encoding="utf-8")):
                if not (pm / name).is_dir():
                    out.append(
                        Finding("learning_project_missing", "medium", _rel(projects, root),
                                f"links `{name}`, which is not a project under project-management/")
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
        package_region_drift,
        package_orphan_marker,
        package_manifest_drift,
        learning_drift,
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
