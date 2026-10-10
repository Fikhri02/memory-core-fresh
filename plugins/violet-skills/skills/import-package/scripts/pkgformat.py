"""Package file format — header validation, section parsing, rendering, packing.

Stdlib only. See docs/superpowers/specs/2026-10-10-migration-packages-design.md §3.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

FORMAT = 2
KINDS = ("project", "ecosystem", "feature", "profile")
AUDIENCES = ("self", "share")
RESERVED_SCOPES = ("project", "ecosystem")
FEATURE_PARTS = ("note", "map", "overview", "components")

SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n?", re.S)
TOP_KEY = re.compile(r"^([a-z_]+):(.*)$")
QUOTED = re.compile(r'^"(?:[^"\\]|\\.)*"')
SECTION_LINE = re.compile(
    r"^## (file|link|section|note|map|overview|components)(?::[ \t]*(.*?))?[ \t]*$")
FENCE_OPEN = re.compile(r"^(`{3,})pkg[ \t]*$")
PLAIN_VALUE = re.compile(r"^[A-Za-z0-9@._/+-]+$")


class PackageError(ValueError):
    """A package that cannot be read or does not fit the format. The message names the problem."""


@dataclass
class Header:
    package: str
    kind: str
    audience: str
    version: int
    format: int
    exported: str
    fields: dict = field(default_factory=dict)


@dataclass
class Section:
    type: str
    arg: str
    content: str


def normalise_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _scalar(raw: str) -> str:
    v = raw.strip()
    quoted = QUOTED.match(v)
    if quoted:
        return json.loads(quoted.group(0))
    if len(v) >= 2 and v[0] == v[-1] == "'":
        return v[1:-1]
    return re.sub(r"\s+#.*$", "", v).strip()


def split_frontmatter(text: str) -> tuple[dict[str, str], str]:
    text = normalise_newlines(text)
    m = FRONTMATTER.match(text)
    if not m:
        raise PackageError("no frontmatter — a package starts with a --- header block")
    fields: dict[str, str] = {}
    for line in m.group(1).split("\n"):
        key = TOP_KEY.match(line)
        if key:
            fields[key.group(1)] = _scalar(key.group(2))
    return fields, text[m.end():]


def id_matches(kind: str, package_id: str) -> bool:
    name, sep, scope = package_id.partition("@")
    if not sep or not SLUG.match(name) or not SLUG.match(scope):
        return False
    if kind == "project":
        return scope == "project"
    if kind == "ecosystem":
        return scope == "ecosystem"
    if kind == "profile":
        return name == "profile" and scope not in RESERVED_SCOPES
    return name != "profile" and scope not in RESERVED_SCOPES


def _positive_int(fields: dict[str, str], key: str) -> int:
    raw = str(fields.get(key, ""))
    if not re.fullmatch(r"[0-9]+", raw) or int(raw) < 1:
        raise PackageError(f"`{key}` must be a whole number of 1 or more, got {raw!r}")
    return int(raw)


def validate_header(fields: dict) -> Header:
    fields = {k: str(v) for k, v in fields.items()}
    if "format" not in fields:
        for key in ("package", "version", "ecosystem", "feature", "members"):
            if key not in fields:
                raise PackageError(f"format 1 package is missing `{key}`")
        kind, audience, fmt = "feature", "share", 1
    else:
        fmt = _positive_int(fields, "format")
        if fmt > FORMAT:
            raise PackageError(f"`format` {fmt} is newer than this importer understands (up to {FORMAT})")
        for key in ("package", "kind", "audience", "version", "exported"):
            if not fields.get(key):
                raise PackageError(f"missing `{key}`")
        kind, audience = fields["kind"], fields["audience"]
        if kind not in KINDS:
            raise PackageError(f"unknown `kind` {kind!r} — expected one of {', '.join(KINDS)}")
        if audience not in AUDIENCES:
            raise PackageError(f"unknown `audience` {audience!r} — expected self or share")
        if kind == "feature":
            for key in ("ecosystem", "feature", "members"):
                if key not in fields:
                    raise PackageError(f"feature package is missing `{key}`")
    package = fields["package"]
    if not id_matches(kind, package):
        raise PackageError(f"`package` {package!r} is not a valid {kind} id")
    return Header(package, kind, audience, _positive_int(fields, "version"), fmt,
                  fields.get("exported", ""), fields)


def parse_sections(body: str, fmt: int) -> list[Section]:
    """Split a package body into sections.

    Format 2: each section's content is the single ```pkg fence under its header; anything else
    between sections is layout. Format 1: content is every line up to the next section header.
    """
    body = normalise_newlines(body)
    sections: list[Section] = []
    current: Section | None = None
    lines: list[str] = []
    fence: str | None = None

    def close() -> None:
        if current is None:
            return
        if fmt >= 2:
            current.content = "\n".join(lines) + "\n" if lines else ""
        else:
            text = "\n".join(lines).strip("\n")
            current.content = text + "\n" if text.strip() else ""
        sections.append(current)

    for line in body.split("\n"):
        if fence is not None:
            if line == fence:
                fence = None
            else:
                lines.append(line)
            continue
        m = SECTION_LINE.match(line)
        if m:
            close()
            current, lines = Section(m.group(1), m.group(2) or "", ""), []
            continue
        if current is None:
            continue
        if fmt >= 2:
            opened = FENCE_OPEN.match(line)
            if opened:
                fence = opened.group(1)
        else:
            lines.append(line)
    if fence is not None:
        raise PackageError(f"unclosed content fence in `## {current.type}: {current.arg}`")
    close()
    return sections


def _yaml_value(v) -> str:
    if isinstance(v, int):
        return str(v)
    s = str(v)
    return s if PLAIN_VALUE.match(s) else json.dumps(s, ensure_ascii=False)


def render(fields: dict, sections: list[Section], header_extra: str = "") -> str:
    out = ["---"]
    out += [f"{k}: {_yaml_value(v)}" for k, v in fields.items()]
    if header_extra.strip():
        out += header_extra.rstrip("\n").split("\n")
    out += ["---", ""]
    for s in sections:
        out.append(f"## {s.type}: {s.arg}" if s.arg else f"## {s.type}")
        if s.type != "link":
            longest = max((len(run) for run in re.findall(r"`+", s.content)), default=0)
            fence = "`" * max(3, longest + 1)
            body = s.content.rstrip("\n")
            out += ["", fence + "pkg", *(body.split("\n") if body else []), fence]
        out.append("")
    return "\n".join(out)


def pack_staging(fields: dict, staging: Path, links=(), header_extra: str = "") -> str:
    """Render every staged file as a section. Paths are relative to the staging root.

    `main/main-memory.md#Heading` → a profile section; `@note.md`, `@overview/{project}.md` → a
    feature part; anything else → a whole file. Dotfiles are skipped.
    """
    sections: list[Section] = []
    for f in sorted(p for p in staging.rglob("*") if p.is_file()):
        rel = f.relative_to(staging).as_posix()
        if any(part.startswith(".") for part in rel.split("/")):
            continue
        try:
            content = normalise_newlines(f.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            raise PackageError(f"{rel} is not UTF-8 text — packages carry text only; remove it from staging")
        if rel.startswith("@"):
            typ, _, arg = rel[1:].removesuffix(".md").partition("/")
            if typ not in FEATURE_PARTS:
                raise PackageError(f"unknown staged feature part {rel}")
        elif "#" in rel:
            typ, arg = "section", rel
        else:
            typ, arg = "file", rel
        sections.append(Section(typ, arg, content))
    sections += [Section("link", f"{a} -> {b}", "") for a, b in links]
    text = render(fields, sections, header_extra)
    validate_header(split_frontmatter(text)[0])   # never emit a package the importer would refuse
    return text


def read_package(text: str) -> tuple[Header, list[Section]]:
    fields, body = split_frontmatter(text)
    head = validate_header(fields)
    return head, parse_sections(body, head.format)
