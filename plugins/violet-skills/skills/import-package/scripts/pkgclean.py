"""Stripping machine-bound data, scanning for personal data, classifying profile headings.

Stdlib only. `drop_columns` is mirrored by health._drop_columns; a test keeps them in agreement.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

MACHINE_COLUMNS = ("Local Path", "Location")
ABSENT = "_(not on this machine)_"
MARKER_LINE = re.compile(r"^\s*<!--\s*/?pkg:[^>]*-->\s*$")
SOURCE_LINE = re.compile(r"^source:\s*\{.*\}\s*$")
CELL_SPLIT = re.compile(r"(?<!\\)\|")


def _cells(line: str) -> list[str]:
    return [c.strip() for c in CELL_SPLIT.split(line.strip())[1:-1]]


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(cells) + " |"


def drop_columns(text: str, columns, normalise: bool = False) -> tuple[str, list[str]]:
    """Remove every Markdown table column whose header cell matches one of `columns` (any case).

    `normalise=True` also rebuilds every other table row as `| a | b |`, so two tables that differ
    only in cell padding compare equal — used for hashing, never for export."""
    wanted = {c.lower() for c in columns}
    lines = text.split("\n")
    out: list[str] = []
    removed: list[str] = []
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
        head = _cells(table[0])
        drop = {k for k, c in enumerate(head) if c.lower() in wanted}
        if drop:
            removed += [head[k] for k in sorted(drop)]
        if drop or normalise:
            out += [_row([c for k, c in enumerate(_cells(r)) if k not in drop]) for r in table]
        else:
            out += table
        i = j
    return "\n".join(out), removed


def strip(text: str, columns=("Local Path",)) -> tuple[str, list[str]]:
    """Remove what is only true on this machine. Returns the text and a description of each removal."""
    text, dropped = drop_columns(text, columns)
    removed = [f"table column `{c}`" for c in dropped]
    out: list[str] = []
    for line in text.split("\n"):
        if MARKER_LINE.match(line):
            removed.append(f"package marker `{line.strip()}`")
            continue
        if SOURCE_LINE.match(line):
            removed.append("import provenance `source:` line")
            continue
        if ABSENT in line:
            removed.append("absence marker")
            line = re.sub(r"[ \t]*" + re.escape(ABSENT), "", line)
        out.append(line)
    return "\n".join(out), removed


@dataclass
class Hit:
    line: int
    kind: str
    excerpt: str


PATTERNS = (
    ("email", re.compile(
        r"(?<![\w.+-])[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(?![\w:])")),
    ("phone", re.compile(r"(?<![\w.-])\+?\d[\d -]{7,15}\d(?![\w-])")),
    ("token", re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}"
        r"|AKIA[0-9A-Z]{16}|AIza[0-9A-Za-z_-]{35}|xox[abposr]-[A-Za-z0-9-]{10,})")),
    ("secret", re.compile(
        r"(?i)\b(?:api[_-]?key|secret|token|password|passwd)\b\s*[:=]\s*['\"]?[^\s'\"]{8,}")),
    ("home-path", re.compile(r"(?:/Users/|/home/)[^\s/`'\")\]]+|[A-Za-z]:\\Users\\[^\s\\]+")),
)
DATE_LIKE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def scan(text: str) -> list[Hit]:
    """Likely personal data, for a human to review. A check, not a guarantee."""
    hits: list[Hit] = []
    for n, line in enumerate(text.split("\n"), 1):
        for kind, pattern in PATTERNS:
            for m in pattern.finditer(line):
                found = m.group(0)
                if kind == "phone" and (sum(ch.isdigit() for ch in found) < 9 or DATE_LIKE.match(found)):
                    continue
                hits.append(Hit(n, kind, found[:60]))
    return hits


COMPANION_HEADINGS = (
    "{companion} profile", "communication style", "core purpose", "time intelligence",
    "echo memory recall", "self-improvement awareness", "session start protocol", "usage notes",
)


def classify_profile_heading(heading: str, companion: str) -> str:
    """`companion` sections travel in a share profile; everything else — including any heading this
    table does not know — is `user` and is blanked. Unknown defaults to user so nothing leaks."""
    h = re.sub(r"\s+", " ", heading.strip().lower())
    known = {k.replace("{companion}", companion.strip().lower()) for k in COMPANION_HEADINGS}
    return "companion" if h in known else "user"


def placeholders(text: str, user: str, companion: str) -> str:
    for name, token in ((user, "{{USER_NAME}}"), (companion, "{{COMPANION_NAME}}")):
        if name.strip():
            text = re.sub(rf"\b{re.escape(name.strip())}\b", token, text)
    return text
