"""Local migration state — hashing, path safety, manifests, import planning, timeline merge, ledger.

Stdlib only. `region_sha` and `heading_sections` are mirrored in mcp-spike/health.py; tests keep
them in agreement, because the plugin and the health server are installed independently.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from pkgclean import MACHINE_COLUMNS, classify_profile_heading, drop_columns, placeholders
from pkgformat import Header, PackageError, Section

ALLOWED_ROOTS = {
    "project": ("project-management/", "project-plans/", "brainstorming/", "debugging/"),
    "ecosystem": ("ecosystem/", "project-management/", "project-plans/", "brainstorming/", "debugging/"),
    "feature": ("ecosystem/", "project-management/"),
}
PROFILE_FILES = ("main/main-memory.md", "main/preferences.md", "main/projects-context.md",
                 "main/current-session.md", "main/session-archive.md")
SHARE_EXCLUDED_FILES = ("main/current-session.md", "main/session-archive.md", "main/projects-context.md")
# Package paths end up in commands an agent runs, so only plain filename characters are accepted.
SAFE_SEGMENT = re.compile(r"^[A-Za-z0-9 ._@()&,+-]+$")
UNSAFE_HEADING = re.compile(r'[\x00-\x1f$`"\\;|<>]')
LINK_PATH = re.compile(r"^project-management/[a-z0-9][a-z0-9-]*/(Plans|Debugging)/[^/]+\.md$")
MAP_PATH = re.compile(r"^ecosystem/[^/]+/map\.md$")


def region_sha(content: str) -> str:
    """Exact copy of health.region_sha."""
    normalised = "\n".join(line.rstrip() for line in content.strip().splitlines())
    return hashlib.sha256(normalised.encode("utf-8")).hexdigest()[:8]


def comparable(text: str, target: str = "") -> str:
    """Text as compared across machines — machine-bound columns removed, table padding normalised.
    `Location` is machine-bound only in an ecosystem map; everywhere else it is content."""
    columns = MACHINE_COLUMNS if MAP_PATH.match(target.partition("#")[0]) else ("Local Path",)
    return drop_columns(text, columns, normalise=True)[0]


FENCE = re.compile(r"^(```|~~~)")


def heading_spans(text: str) -> dict[str, tuple[int, int]]:
    """Line spans [start, end) of each `## ` section, first occurrence wins. Fences are never split."""
    spans: dict[str, tuple[int, int]] = {}
    lines = text.split("\n")
    name: str | None = None
    start = 0
    in_fence = False
    for i, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
        if not in_fence and line.startswith("## "):
            if name is not None:
                spans.setdefault(name, (start, i))
            name, start = line[3:].strip(), i
    if name is not None:
        spans.setdefault(name, (start, len(lines)))
    return spans


def heading_sections(text: str) -> dict[str, str]:
    """`## ` sections keyed by heading text; each value runs from its heading line to the next."""
    lines = text.split("\n")
    return {name: "\n".join(lines[a:b]).rstrip("\n") + "\n" for name, (a, b) in heading_spans(text).items()}


def target_text(root: Path, target: str) -> str | None:
    path, _, heading = target.partition("#")
    f = root / path
    if not f.is_file():
        return None
    text = f.read_text(encoding="utf-8").replace("\r\n", "\n")
    return heading_sections(text).get(heading) if heading else text


def check_target(kind: str, target: str, audience: str = "self") -> None:
    path, _, heading = target.partition("#")
    segments = path.split("/")
    if (not path or path.startswith("/") or re.match(r"^[A-Za-z]:", path)
            or any(seg in ("", ".", "..") or seg.startswith("-") or not SAFE_SEGMENT.match(seg)
                   for seg in segments)):
        raise PackageError(f"unsafe path in package: {target!r}")
    if heading and UNSAFE_HEADING.search(heading):
        raise PackageError(f"unsafe heading in package: {target!r}")
    if segments[0] == "project-management" and len(segments) > 1 and segments[1].startswith("_"):
        raise PackageError(f"package may not write infrastructure folder {path!r}")
    if kind == "profile":
        ok = path in PROFILE_FILES
    else:
        ok = any(path.startswith(r) for r in ALLOWED_ROOTS.get(kind, ()))
    if not ok:
        raise PackageError(f"a {kind} package may not write {path!r}")
    if audience == "share" and (path in SHARE_EXCLUDED_FILES or segments[-1] == "Timeline.md"
                                or "Feedbacks" in segments[:-1]):
        raise PackageError(f"a share package may not carry {path!r} — it is personal history")


def check_section(target: str, content: str) -> None:
    """A profile section must be exactly its own `## ` section — nothing that would add or shadow another."""
    heading = target.partition("#")[2]
    first = content.split("\n", 1)[0].rstrip()
    if first != f"## {heading}" or list(heading_sections(content)) != [heading]:
        raise PackageError(f"section {target!r} must hold exactly one `## {heading}` section")


@dataclass
class Manifest:
    package: str
    version: int
    imported: str
    entries: dict


MANIFEST_ENTRY = re.compile(r'^\s*-\s*\{path:\s*("(?:[^"\\]|\\.)*"),\s*sha:\s*([0-9a-f]{8})\s*\}\s*$')
MANIFEST_HEAD = re.compile(r"^(package|version|imported):\s*(.*?)\s*$")


def manifest_path(root: Path, package_id: str) -> Path:
    return root / "migrations" / "manifests" / f"{package_id}.yaml"


def read_manifest(path: Path) -> Manifest | None:
    if not path.is_file():
        return None
    head: dict[str, str] = {}
    entries: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        entry = MANIFEST_ENTRY.match(line)
        if entry:
            entries[json.loads(entry.group(1))] = entry.group(2)
            continue
        field = MANIFEST_HEAD.match(line)
        if field:
            head[field.group(1)] = field.group(2)
    if "package" not in head or not head.get("version", "").isdigit():
        raise PackageError(f"{path} is not a manifest — missing package or version")
    return Manifest(head["package"], int(head["version"]), head.get("imported", ""), entries)


def write_manifest(path: Path, m: Manifest) -> None:
    lines = [f"package: {m.package}", f"version: {m.version}", f"imported: {m.imported}", "entries:"]
    lines += [f"  - {{path: {json.dumps(t, ensure_ascii=False)}, sha: {s}}}"
              for t, s in sorted(m.entries.items())]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def record(root: Path, package_id: str, version: int, imported: str, targets) -> Manifest:
    """Record what is on disk now as the installed baseline. Record only what was written or found
    unchanged — never a file the user chose to keep local, or its local edits become the baseline."""
    path = manifest_path(root, package_id)
    m = read_manifest(path) or Manifest(package_id, version, imported, {})
    m.version, m.imported = version, imported
    for t in targets:
        text = target_text(root, t)
        if text is None:
            raise PackageError(f"cannot record {t!r} — it does not exist under {root}")
        m.entries[t] = region_sha(comparable(text, t))
    write_manifest(path, m)
    return m


@dataclass
class PlanItem:
    action: str
    target: str
    reason: str


def apply_renames(target: str, renames: dict | None) -> str:
    for old, new in (renames or {}).items():
        old, new = old.rstrip("/"), new.rstrip("/")
        if target == old or target.startswith(old + "/"):
            return new + target[len(old):]
    return target


def merge_timeline_needed(target: str) -> bool:
    return target.rsplit("/", 1)[-1] == "Timeline.md"


def timeline_differences(local: str, incoming: str) -> list[str]:
    """Dated headers present on both sides whose bodies differ."""
    mine = {h: body for _, h, body in _blocks(local)[1]}
    return [h[3:] for _, h, body in _blocks(incoming)[1]
            if h in mine and region_sha(mine[h]) != region_sha(body)]


def _classify(root: Path, header: Header, manifest: Manifest | None, target: str, incoming: str) -> PlanItem:
    local = target_text(root, target)
    if local is None:
        return PlanItem("new", target, "not present here")
    local_sha = region_sha(comparable(local, target))
    if local_sha == region_sha(comparable(incoming, target)):
        return PlanItem("unchanged", target, "identical")
    if merge_timeline_needed(target):
        differs = timeline_differences(local, incoming)
        note = f"; same date differs on both sides: {', '.join(differs)} — review by hand" if differs else ""
        if merge_timeline(local, incoming) is not local:
            return PlanItem("merge-timeline", target, "new dated sections added; existing ones untouched" + note)
        if differs:
            return PlanItem("timeline-differs", target,
                            f"same date differs on both sides: {', '.join(differs)} — review by hand")
        return PlanItem("unchanged", target, "no new dated sections")
    recorded = manifest.entries.get(target) if manifest else None
    if recorded is None:
        return PlanItem("conflict", target, "exists here with different content and no import record")
    if local_sha != recorded:
        return PlanItem("conflict", target, f"edited here since the last import (v{manifest.version} recorded)")
    if header.version > manifest.version:
        return PlanItem("update", target, f"v{manifest.version} -> v{header.version}")
    if header.version < manifest.version:
        return PlanItem("skip-older", target,
                        f"incoming v{header.version} is older than installed v{manifest.version}")
    return PlanItem("conflict", target, f"same version v{header.version} but different content")


def _classify_link(root: Path, link: str, home: str) -> PlanItem:
    f = root / link
    if f.is_symlink():
        if f.resolve() == (root / home).resolve():
            return PlanItem("unchanged", f"{link} -> {home}", "link already in place")
        return PlanItem("link", f"{link} -> {home}", "replace symlink")
    if f.exists():
        return PlanItem("conflict", f"{link} -> {home}", "a regular file is here, not a link")
    return PlanItem("link", f"{link} -> {home}", "recreate symlink")


def parse_link(arg: str, renames: dict | None) -> tuple[str, str]:
    link, sep, home = arg.partition(" -> ")
    if not sep:
        raise PackageError(f"malformed link section: {arg!r}")
    return apply_renames(link.strip(), renames), apply_renames(home.strip(), renames)


def plan(root: Path, header: Header, sections: list[Section], renames: dict | None = None) -> list[PlanItem]:
    if header.kind == "feature":
        raise PackageError("feature packages use in-file markers — use feature-targets and kinds/feature.md")
    checked: list[tuple[Section, str]] = []
    files: set[str] = set()
    for s in sections:                      # validate every path before touching the disk
        if s.type in ("file", "section"):
            target = apply_renames(s.arg, renames)
            check_target(header.kind, target, header.audience)
            if s.type == "section":
                check_section(target, s.content)
            files.add(target)
            checked.append((s, target))
        elif s.type != "link":
            raise PackageError(f"`## {s.type}` does not belong in a {header.kind} package")
    for s in sections:
        if s.type == "link":
            link, home = parse_link(s.arg, renames)
            check_target(header.kind, link, header.audience)
            check_target(header.kind, home, header.audience)
            if not LINK_PATH.match(link):
                raise PackageError(f"link {link!r} must be a .md file under a project's Plans/ or Debugging/")
            if home not in files or not home.endswith(".md"):
                raise PackageError(f"link {link!r} points at {home!r}, which the package does not carry")
            checked.append((s, f"{link} -> {home}"))
    manifest = read_manifest(manifest_path(root, header.package))
    items: list[PlanItem] = []
    for s, target in checked:
        if s.type == "link":
            items.append(_classify_link(root, *target.split(" -> ")))
        else:
            items.append(_classify(root, header, manifest, target, s.content))
    return items


def find_section(sections: list[Section], target: str, renames: dict | None = None) -> Section:
    for s in sections:
        if s.type in ("file", "section") and apply_renames(s.arg, renames) == target:
            return s
    raise PackageError(f"package has no section for {target!r}")


def _inside(root: Path, path: Path, kind: str | None) -> None:
    """Refuse a write whose real location — after following symlinks — leaves the memory root or
    lands somewhere the kind may not write."""
    real_root = root.resolve()
    real = path.resolve()
    try:
        rel = real.relative_to(real_root).as_posix()
    except ValueError:
        raise PackageError(f"{path} resolves outside the memory root ({real})")
    if kind:
        check_target(kind, rel)


def write_target(root: Path, target: str, content: str, kind: str | None = None) -> None:
    path, _, heading = target.partition("#")
    f = root / path
    f.parent.mkdir(parents=True, exist_ok=True)
    _inside(root, f, kind)
    if not heading:
        f.write_text(content, encoding="utf-8")
        return
    text = f.read_text(encoding="utf-8").replace("\r\n", "\n") if f.is_file() else ""
    span = heading_spans(text).get(heading)
    new = content.rstrip("\n").split("\n")
    if span is None:
        text = (text.rstrip("\n") + "\n\n" if text.strip() else "") + "\n".join(new) + "\n"
    else:
        lines = text.split("\n")
        a, b = span
        trailing = len(lines[a:b]) - len("\n".join(lines[a:b]).rstrip("\n").split("\n"))
        lines[a:b] = new + [""] * trailing
        text = "\n".join(lines)
    f.write_text(text, encoding="utf-8")


def make_link(root: Path, kind: str, link: str, home: str) -> None:
    """Create `link` → absolute `home`, replacing only an existing symlink — never a real file."""
    f = root / link
    if f.exists() and not f.is_symlink():
        raise PackageError(f"{link} is a regular file here — refusing to replace it with a link")
    f.parent.mkdir(parents=True, exist_ok=True)
    _inside(root, f.parent, kind)
    target = (root / home).resolve()
    _inside(root, target, kind)
    if f.is_symlink():
        f.unlink()
    f.symlink_to(target)


FEATURE_MEMBER = re.compile(r"^\s*-\s*\{(.*)\}\s*$")
FLOW_FIELD = re.compile(r'(\w+):\s*("(?:[^"\\]|\\.)*"|[^,}]*)')
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def feature_members(frontmatter: str) -> list[dict]:
    members: list[dict] = []
    inside = False
    for line in frontmatter.split("\n"):
        if re.match(r"^[a-z_]+:", line):
            inside = line.startswith("members:")
            continue
        m = FEATURE_MEMBER.match(line) if inside else None
        if m:
            fields = {}
            for key, raw in FLOW_FIELD.findall(m.group(1)):
                raw = raw.strip()
                fields[key] = json.loads(raw) if raw.startswith('"') else raw
            members.append(fields)
    return members


def feature_targets(text: str) -> list[tuple[str, str]]:
    """The only paths a feature import may write, derived from the package id and `members:` and
    validated. Agents use this list; they never build a path from package text themselves."""
    from pkgformat import FRONTMATTER, normalise_newlines, read_package
    head, sections = read_package(text)
    if head.kind != "feature":
        raise PackageError(f"feature-targets needs a feature package, got {head.kind}")
    feature, ecosystem = head.package.split("@")
    members = feature_members(FRONTMATTER.match(normalise_newlines(text)).group(1))
    if not members:
        raise PackageError("feature package lists no `members`")
    out = [("map", f"ecosystem/{ecosystem}/map.md"), ("note", f"ecosystem/{ecosystem}/features/{feature}.md")]
    names = set()
    for m in members:
        project, component = m.get("project", ""), m.get("component", "")
        if not SLUG.match(project):
            raise PackageError(f"member project {project!r} is not a valid slug")
        if not component or component in (".", "..") or component.startswith("-") or not SAFE_SEGMENT.match(component):
            raise PackageError(f"member {project!r} has an unsafe component {component!r}")
        names.add(project)
        out += [("overview", f"project-management/{project}/Features/{component}/Overview.md"),
                ("components", f"project-management/{project}/Components.md")]
    for s in sections:
        if s.type in ("overview", "components") and s.arg not in names:
            raise PackageError(f"`## {s.type}: {s.arg}` names a project that is not a member")
    for _, target in out:
        check_target("feature", target)
    return out


TEMPLATE_FENCE = re.compile(r"^```markdown\n(.*?)^```", re.M | re.S)
USER_TEMPLATE = {"Identity & Relationship": "Identity & Relationship",
                 "{user} Profile": "[YOUR_NAME] Profile",
                 "Relationship Context": "Relationship Context"}


def share_profile_sections(memory: str, template: str, user: str, companion: str) -> tuple[dict, list]:
    """main-memory.md split for a share profile: {target heading: section text}, plus unknown headings.

    Headings and bodies carry {{USER_NAME}} / {{COMPANION_NAME}} instead of names. Companion sections
    keep their body; user sections are replaced by the matching section of the template (the
    ```markdown block in main-memory-format.md); a heading neither table knows is blanked and reported.
    """
    fenced = TEMPLATE_FENCE.search(template)
    tmpl = heading_sections(fenced.group(1) if fenced else template)
    user_map = {k.replace("{user}", user.strip()): v for k, v in USER_TEMPLATE.items()}
    out: dict[str, str] = {}
    unknown: list[str] = []
    for heading, body in heading_sections(memory).items():
        target = placeholders(heading, user, companion)
        if classify_profile_heading(heading, companion) == "companion":
            out[target] = placeholders(body, user, companion)
            continue
        key = user_map.get(heading)
        text = tmpl.get(key) if key else None
        if key is None:
            unknown.append(heading)
        if text:
            out[target] = text.replace("[AI_NAME]", "{{COMPANION_NAME}}").replace("[YOUR_NAME]", "{{USER_NAME}}")
        else:
            out[target] = f"## {target}\n\n<!-- left blank in a shared profile -->\n"
    return out, unknown


DATE_HEADER = re.compile(r"^## (\d{4}-\d{2}-\d{2})\b.*$", re.M)


def _blocks(text: str):
    marks = list(DATE_HEADER.finditer(text))
    if not marks:
        return text, []
    blocks = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(text)
        blocks.append((m.group(1), m.group(0).rstrip(), text[m.start():end]))
    return text[:marks[0].start()], blocks


def _direction(*block_lists) -> str:
    for blocks in block_lists:
        dates = [d for d, _, _ in blocks]
        for a, b in zip(dates, dates[1:]):
            if a != b:
                return "asc" if b > a else "desc"
    return "desc"


def merge_timeline(local: str, incoming: str) -> str:
    """Add incoming dated sections whose header line is not already present, in the local file's
    order. Existing sections are never touched. Returns `local` itself when nothing is new."""
    pre, mine = _blocks(local)
    _, theirs = _blocks(incoming)
    have = {h for _, h, _ in mine}
    new = [b for b in theirs if b[1] not in have]
    if not new:
        return local
    order = _direction(mine, theirs)
    merged = list(mine)
    for block in new:
        date = block[0]
        idx = next((i for i, b in enumerate(merged)
                    if (b[0] > date if order == "asc" else b[0] < date)), len(merged))
        merged.insert(idx, block)
    body = "\n\n".join(b[2].rstrip("\n") for b in merged)
    return (pre.rstrip("\n") + "\n\n" if pre.strip() else "") + body + "\n"


LEDGER_HEAD = (
    "# Migration Ledger\n\n"
    "*Local and git-ignored. One row per export or import — append only.*\n\n"
    "| Date | Dir | Package | Kind | Audience | Ver | Result | Note |\n"
    "|------|-----|---------|------|----------|-----|--------|------|\n"
)
LEDGER_RESULTS = {"out": ("written",),
                  "in": ("applied", "no-op", "partial", "conflict-resolved", "refused")}
LEDGER_KEYS = ("date", "dir", "package", "kind", "audience", "version", "result", "note")
CELL_SPLIT = re.compile(r"(?<!\\)\|")


def ledger_path(root: Path) -> Path:
    return root / "migrations" / "ledger.md"


def _cell(value) -> str:
    return str(value).replace("\r", " ").replace("\n", " ").replace("|", "\\|").strip()


def append_ledger(root: Path, *, date, direction, package, kind, audience, version, result, note="") -> str:
    if direction not in LEDGER_RESULTS:
        raise PackageError(f"direction must be `in` or `out`, got {direction!r}")
    if result not in LEDGER_RESULTS[direction]:
        raise PackageError(f"result {result!r} is not valid for direction {direction!r}")
    path = ledger_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file():
        path.write_text(LEDGER_HEAD, encoding="utf-8")
    existing = path.read_text(encoding="utf-8")
    row = "| " + " | ".join(_cell(v) for v in (date, direction, package, kind, audience,
                                                version, result, note)) + " |\n"
    with path.open("a", encoding="utf-8") as fh:
        if not existing.endswith("\n"):
            fh.write("\n")
        fh.write(row)
    return row


def ledger_rows(root: Path) -> list[dict]:
    path = ledger_path(root)
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [c.strip().replace("\\|", "|") for c in CELL_SPLIT.split(line.strip())[1:-1]]
        if len(cells) == 8 and cells[0] != "Date" and not set(cells[0]) <= set("-"):
            rows.append(dict(zip(LEDGER_KEYS, cells)))
    return rows


def next_version(root: Path, package_id: str) -> int:
    best = 0
    out = root / "migrations" / "out"
    versioned = re.compile(rf"^{re.escape(package_id)}\.v(\d+)\.pkg\.md$")
    if out.is_dir():
        for f in out.iterdir():
            m = versioned.match(f.name)
            if m:
                best = max(best, int(m.group(1)))
            elif f.name == f"{package_id}.pkg.md":          # format-1 export
                legacy = re.search(r"^version:\s*(\d+)", f.read_text(encoding="utf-8"), re.M)
                if legacy:
                    best = max(best, int(legacy.group(1)))
    for r in ledger_rows(root):
        if r["dir"] == "out" and r["package"] == package_id and r["version"].isdigit():
            best = max(best, int(r["version"]))
    return best + 1
