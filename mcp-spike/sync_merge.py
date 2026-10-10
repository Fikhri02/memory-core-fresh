"""Merge helpers for memory-core sync. Stdlib only.

- sort_log_sections: put a union-merged log back in date order, folding same-heading sections.
- merge_current_session: three-way merge of main/current-session.md by session block.
- three_way: three-way merge of a judgement file by unit (rule, entry, row, section).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
SESSION_BLOCK = re.compile(r"^### (\d{4}-\d{2}-\d{2})", re.M)
ANY_H3 = re.compile(r"^### ", re.M)


def _pick(base, ours, theirs):
    if ours == theirs:
        return ours, False
    if ours == base:
        return theirs, False
    if theirs == base:
        return ours, False
    return ours, True


def _choose(choice: str | None, ours: str, theirs: str) -> str | None:
    if choice is None:
        return None
    if choice == "ours":
        return ours
    if choice == "theirs":
        return theirs
    if choice == "both":
        if not ours or not theirs:
            return ours or theirs
        return ours.rstrip("\n") + "\n" + theirs
    if choice.startswith("edit:"):
        return choice[5:]
    raise ValueError(f"unknown choice {choice!r}")


FENCE_LINE = re.compile(r"^\s*(```|~~~)")
KEEP_REPEATS = re.compile(r"^\s*(```|~~~|\|?[\s:|-]*-{3,}[\s:|-]*\|?\s*$)")


def _section_starts(text: str, level: int) -> list[int]:
    """Offsets of real `#…# ` headings at `level` — never inside a code fence or an HTML comment."""
    heading = re.compile(rf"^{'#' * level} (?!#)")
    starts, pos, in_fence, in_comment = [], 0, False, False
    for line in text.splitlines(keepends=True):
        if in_comment:
            in_comment = "-->" not in line
        elif FENCE_LINE.match(line):
            in_fence = not in_fence
        elif not in_fence and line.lstrip().startswith("<!--") and "-->" not in line.split("<!--", 1)[1]:
            in_comment = True
        elif not in_fence and heading.match(line):
            starts.append(pos)
        pos += len(line)
    return starts


def sort_log_sections(text: str, level: int = 2) -> str:
    """Fold sections that a union merge duplicated (same heading twice) into the first copy.

    Nothing else changes: no reordering, no blank-line edits, and a later copy only contributes
    lines the first copy lacks (fence and table-rule lines are always kept). A file with no repeated
    heading comes back byte for byte.
    """
    starts = _section_starts(text, level)
    if not starts:
        return text
    preamble = text[:starts[0]]
    sections = [text[a:b] for a, b in zip(starts, starts[1:] + [len(text)])]
    heads = [s.split("\n", 1)[0].rstrip() for s in sections]
    if len(set(heads)) == len(heads):
        return text
    kept: list[str] = []
    index: dict[str, int] = {}
    for head, section in zip(heads, sections):
        if head not in index:
            index[head] = len(kept)
            kept.append(section)
            continue
        first = kept[index[head]]
        present = set(first.split("\n"))
        body = section.split("\n", 1)[1] if "\n" in section else ""
        extra = [line for line in body.rstrip("\n").split("\n")
                 if not line.strip() or KEEP_REPEATS.match(line) or line not in present]
        while extra and not extra[0].strip():
            extra.pop(0)
        while extra and not extra[-1].strip():
            extra.pop()
        if extra:
            kept[index[head]] = first.rstrip("\n") + "\n" + "\n".join(extra) + "\n\n"
    return (preamble + "".join(kept)).rstrip("\n") + "\n"


@dataclass
class SessionMerge:
    text: str
    archived: list[str]
    conflicts: list[str]


def _session_parts(text: str) -> tuple[str, list[tuple[str, str]], str]:
    heads = [(m.start(), bool(SESSION_BLOCK.match(text, m.start()))) for m in ANY_H3.finditer(text)]
    first = next((i for i, (_, dated) in enumerate(heads) if dated), None)
    if first is None:
        return text, [], ""
    end = next((i for i in range(first, len(heads)) if not heads[i][1]), len(heads))
    suffix_start = heads[end][0] if end < len(heads) else len(text)
    blocks = []
    for i in range(first, end):
        start = heads[i][0]
        stop = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        chunk = text[start:min(stop, suffix_start)]
        blocks.append((chunk.split("\n", 1)[0].rstrip(), chunk.rstrip("\n") + "\n\n"))
    return text[:heads[first][0]], blocks, text[suffix_start:]


def merge_current_session(base: str, ours: str, theirs: str, cap: int = 3,
                          choices: dict | None = None) -> SessionMerge:
    choices = choices or {}
    bp, bb, bs = _session_parts(base)
    op, ob, osuf = _session_parts(ours)
    tp, tb, ts = _session_parts(theirs)
    conflicts: list[str] = []

    def settle(key, b, o, t):
        value, conflict = _pick(b, o, t)
        if not conflict:
            return value
        chosen = _choose(choices.get(key), o, t)
        if chosen is None:
            conflicts.append(key)
            return o
        return chosen

    prefix = settle("header", bp, op, tp)
    suffix = settle("footer", bs, osuf, ts)
    bmap, omap, tmap = dict(bb), dict(ob), dict(tb)
    order = [h for h, _ in ob] + [h for h, _ in tb if h not in omap]
    merged = []
    for h in order:
        o, t, b = omap.get(h), tmap.get(h), bmap.get(h)
        if o is None or t is None:
            present = o if o is not None else t
            if b is not None and present == b:
                continue
            merged.append((h, present))
            continue
        merged.append((h, settle(h, b, o, t)))
    merged.sort(key=lambda hc: SESSION_BLOCK.match(hc[0]).group(1), reverse=True)
    keep, extra = merged[:cap], merged[cap:]
    return SessionMerge(prefix + "".join(chunk for _, chunk in keep) + suffix, [c for _, c in extra], conflicts)


def session_units(path: str, base: str, ours: str, theirs: str, keys: list[str]) -> list:
    parts = [_session_parts(x) for x in (base, ours, theirs)]
    units = []
    for key in keys:
        if key == "header":
            values = [p[0] for p in parts]
        elif key == "footer":
            values = [p[2] for p in parts]
        else:
            values = [dict(p[1]).get(key) for p in parts]
        units.append(Unit(path, key, *values))
    return units


def prepend_to_archive(archive: str, blocks: list[str]) -> str:
    if not blocks:
        return archive
    m = ANY_H3.search(archive)
    cut = m.start() if m else len(archive)
    head = archive[:cut]
    if head and not head.endswith("\n\n"):
        head = head.rstrip("\n") + "\n\n"
    return head + "".join(b.rstrip("\n") + "\n\n" for b in blocks) + archive[cut:]


@dataclass
class Unit:
    path: str
    key: str
    base: str | None
    ours: str | None
    theirs: str | None


@dataclass
class MergeResult:
    text: str | None
    conflicts: list[Unit] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


BULLET = re.compile(r"^- ")
BOLD_KEY = re.compile(r"^- \*\*(.+?)\*\*")
ENTRY_HEAD = re.compile(r"^## \S")
ANY_HEAD = re.compile(r"^#{1,6} \S")
LIBRARY_FILES = ("design/palettes.md", "design/type.md")
BULLET_FILES = ("main/preferences.md", "main/main-memory.md")
NOT_BULLET_DESIGN = ("design/README.md", "design/journal.md")
RANKED_KEYS = ("## Ranked", "## Unranked")


def unit_kind(path: str) -> str:
    if not path.endswith(".md"):
        return "file"
    if path in LIBRARY_FILES:
        return "entry"
    if path == "career/tracker.md":
        return "row"
    if path in BULLET_FILES or path.startswith("context/") or (
            path.startswith("design/") and path.endswith(".md") and path not in NOT_BULLET_DESIGN):
        return "bullet"
    return "section"


def split_units(kind: str, text: str) -> list[tuple[str | None, str]]:
    segs: list[list] = []

    def glue(line: str) -> None:
        if segs and segs[-1][0] is None:
            segs[-1][1] += line
        else:
            segs.append([None, line])

    for line in text.splitlines(keepends=True):
        if kind == "bullet":
            if BULLET.match(line):
                m = BOLD_KEY.match(line)
                segs.append([m.group(1) if m else line.strip(), line])
            elif segs and segs[-1][0] is not None and line.strip() and line[:1] in " \t":
                segs[-1][1] += line
            else:
                glue(line)
        elif kind == "row":
            cells = [c.strip() for c in line.strip().strip("|").split("|")] if line.startswith("|") else []
            if len(cells) >= 3 and not set(cells[0]) <= set("-: ") and cells[0] != "Job":
                segs.append([f"{cells[0]} | {cells[1]}", line])
            else:
                glue(line)
        else:
            starts_unit = ENTRY_HEAD.match(line) if kind == "entry" else ANY_HEAD.match(line)
            if starts_unit:
                segs.append([line.rstrip("\n").strip(), line])
            elif segs and segs[-1][0] is not None:
                segs[-1][1] += line
            else:
                glue(line)

    seen: dict[str, int] = {}
    result = []
    for key, chunk in segs:
        if key is not None:
            seen[key] = seen.get(key, 0) + 1
            if seen[key] > 1:
                key = f"{key} #{seen[key]}"
        result.append((key, chunk))
    return result


def _assemble(skeleton, other, decisions: dict[str, str | None]) -> str:
    skeleton_keys = {k for k, _ in skeleton if k}
    inserts: dict[str | None, list[str]] = {}
    previous = None
    for key, _ in other:
        if not key:
            continue
        if key in skeleton_keys:
            previous = key
            continue
        inserts.setdefault(previous, []).append(key)
    out: list[str] = []

    def emit(keys):
        out.extend(decisions[k] for k in keys if decisions.get(k))

    leading_done = False
    for key, chunk in skeleton:
        if key is None:
            out.append(chunk)
            continue
        if not leading_done:
            emit(inserts.get(None, []))
            leading_done = True
        if decisions.get(key):
            out.append(decisions[key])
        emit(inserts.get(key, []))
    if not leading_done:
        emit(inserts.get(None, []))
    return "".join(out)


def _replacements(base_segs, side_segs) -> dict[str, str]:
    """Base unit → the new unit that took its place on one side (a rename): the base key is gone
    there and a key unknown to base sits in its slot, right after the same surviving predecessor."""
    base_keys = [k for k, _ in base_segs if k]
    side_keys = {k for k, _ in side_segs if k}
    predecessor, previous = {}, None
    for key in base_keys:
        predecessor[key] = previous
        previous = key
    new_after: dict[str | None, list[str]] = {}
    previous = None
    for key, _ in side_segs:
        if not key:
            continue
        if key in predecessor:
            previous = key
        else:
            new_after.setdefault(previous, []).append(key)
    return {k: new_after[predecessor[k]][0] for k in base_keys
            if k not in side_keys and new_after.get(predecessor[k])}


def three_way(path: str, base: str, ours: str, theirs: str, choices: dict | None = None) -> MergeResult:
    choices = choices or {}
    kind = unit_kind(path)
    if kind == "file":
        value, conflict = _pick(base, ours, theirs)
        if not conflict:
            return MergeResult(value)
        whole = _choose(choices.get("(file)", choices.get("*")), ours, theirs)
        return MergeResult(whole) if whole is not None else MergeResult(None, [Unit(path, "(file)", base, ours, theirs)])
    bs, os_, ts = (split_units(kind, x) for x in (base, ours, theirs))

    def glue(segs):
        return [chunk for key, chunk in segs if key is None]

    _, structure_conflict = _pick(glue(bs), glue(os_), glue(ts))
    if structure_conflict:
        whole = _choose(choices.get("(structure)", choices.get("*")), ours, theirs)
        if whole is None:
            return MergeResult(None, [Unit(path, "(structure)", base, ours, theirs)])
        return MergeResult(whole)
    if glue(os_) == glue(bs) and glue(ts) != glue(bs):
        skeleton, other = ts, os_
    else:
        skeleton, other = os_, ts

    bmap = {k: c for k, c in bs if k}
    omap = {k: c for k, c in os_ if k}
    tmap = {k: c for k, c in ts if k}
    keys = [k for k, _ in os_ if k] + [k for k, _ in ts if k and k not in omap]
    decisions: dict[str, str | None] = {}
    conflicts: list[Unit] = []
    notes: list[str] = []
    renamed_ours, renamed_theirs = _replacements(bs, os_), _replacements(bs, ts)
    for key in [k for k, _ in bs if k]:
        o_key, t_key = renamed_ours.get(key), renamed_theirs.get(key)
        if not o_key or not t_key or omap[o_key] == tmap[t_key]:
            continue
        keys = [k for k in keys if k not in (o_key, t_key)]
        value = _choose(choices.get(key, choices.get("*")), omap[o_key], tmap[t_key])
        if value is None:
            conflicts.append(Unit(path, key, bmap[key], omap[o_key], tmap[t_key]))
            continue
        on_skeleton = o_key if skeleton is os_ else t_key
        decisions[on_skeleton] = value
        decisions[t_key if on_skeleton == o_key else o_key] = None
    for key in keys:
        b, o, t = bmap.get(key), omap.get(key), tmap.get(key)
        value, conflict = _pick(b, o, t)
        if conflict and kind == "entry" and key in RANKED_KEYS:
            value, conflict = o, False
            notes.append("recompute ranked tables")
        if conflict:
            value = _choose(choices.get(key, choices.get("*")), o or "", t or "")
            if value is None:
                conflicts.append(Unit(path, key, b, o, t))
                continue
        decisions[key] = value
    if conflicts:
        return MergeResult(None, conflicts, sorted(set(notes)))
    return MergeResult(_assemble(skeleton, other, decisions), [], sorted(set(notes)))
