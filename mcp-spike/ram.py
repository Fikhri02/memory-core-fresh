"""Device-based session RAM for memory-core. Stdlib only.

Each laptop keeps its RAM in main/ram/{device-name}.md and writes only that file, so sync never has to
merge one laptop's RAM into another's. A clone with no device identity uses main/ram/unregistered.md.

CLI (skills call this; paths are relative to the memory root):
    python3 mcp-spike/ram.py [--root DIR] path            own RAM path (creates nothing)
    python3 mcp-spike/ram.py [--root DIR] ensure          create own RAM if missing, print its path
    python3 mcp-spike/ram.py [--root DIR] others          one line per other laptop, newest first
    python3 mcp-spike/ram.py [--root DIR] stamp "TEXT"    refresh own header (last activity, last session)
    python3 mcp-spike/ram.py [--root DIR] trim            keep 3 newest session blocks and only the Focus /
                                                          Repos / Open loops status keys; archive the rest
    python3 mcp-spike/ram.py [--root DIR] check           lint own RAM's shape (read-only), print JSON
    python3 mcp-spike/ram.py [--root DIR] absorb          move stray content out of main/current-session.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import sync_device as dev  # noqa: E402

RAM_DIR = "main/ram"
POINTER = "main/current-session.md"
ARCHIVE = "main/session-archive.md"
UNREGISTERED = "unregistered"
POINTER_TEXT = ("# Session RAM moved\n\n"
                "Session RAM now lives in `main/ram/{device}.md`, one file per laptop (since 2026-10-10).\n"
                "See `main/ram/README.md`. Nothing should be written to this file.\n")
RAM_FILE = re.compile(r"^main/ram/([a-z0-9][a-z0-9-]*)\.md$")
TITLE = re.compile(r"^# Session RAM — (.+)$", re.M)
DEVICE_LINE = re.compile(r"^\*\*Device\*\*: (.+?) · `([^`]*)` · \*\*Last activity\*\*: (.+)$", re.M)
SESSION_LINE = re.compile(r"^\*\*Last session\*\*: (.+)$", re.M)
SESSION_BLOCK = re.compile(r"^### (\d{4}-\d{2}-\d{2})", re.M)
ANY_H3 = re.compile(r"^### ", re.M)
BLOCK_END = re.compile(r"^#{1,3} ", re.M)
DATED_HEADING = re.compile(r"^### (\d{4}-\d{2}-\d{2})(.*)$")
STATUS_HEADING = re.compile(r"^## Session RAM Status[ \t]*$", re.M)
RECAP_HEADING = re.compile(r"^## Session Recap\b.*$", re.M)
ITALIC_LINE = re.compile(r"^\*[^*\s].*[^*\s]\*\s*$")
STATUS_KEY = re.compile(r"^\*\*([^*]+)\*\*:(.*)$")
STATUS_KEYS = ("Focus", "Repos", "Open loops")
LIST_CAP = 5
BLOCK_CAP = 3
EMPTY_BODY = ("## Session RAM Status\n**Focus**: —\n**Repos**:\n**Open loops**:\n\n"
              "## Session Recap (For AI Restart)\n*Quick summary when the AI loads after a close/reopen*\n")


# ---------------------------------------------------------------- identity and paths

def _identity(root: Path) -> dict[str, str]:
    return dev.read_kv(root / "device" / "id.md")


def device_name(root: Path) -> str:
    return _identity(root).get("name") or UNREGISTERED


def device_id(root: Path) -> str:
    return _identity(root).get("id", "")


def ram_rel(root: Path) -> str:
    return f"{RAM_DIR}/{device_name(root)}.md"


def owner(rel: str) -> str | None:
    m = RAM_FILE.match(rel)
    return m.group(1) if m else None


def foreign_changes(paths: list[str], name: str) -> list[str]:
    return sorted(p for p in paths if (o := owner(p)) is not None and o != name)


def conflict_side(rel: str, name: str) -> str | None:
    o = owner(rel)
    if o is None or o == UNREGISTERED:
        return None
    return "ours" if o == name else "theirs"


# ---------------------------------------------------------------- header

def render_header(name: str, device_id: str, last_activity: str, last_session: str) -> str:
    return (f"# Session RAM — {name}\n"
            f"**Device**: {name} · `{device_id or '—'}` · **Last activity**: {last_activity}\n"
            f"**Last session**: {last_session}\n")


def read_header(text: str) -> dict | None:
    head = "\n".join(text.splitlines()[:3])
    t, d, s = TITLE.search(head), DEVICE_LINE.search(head), SESSION_LINE.search(head)
    if not (t and d and s):
        return None
    return {"device": t.group(1).strip(), "id": d.group(2), "last_activity": d.group(3).strip(),
            "last_session": s.group(1).strip()}


def _body(text: str) -> str:
    if read_header(text) is None:
        return text
    rest = text.split("\n", 3)[3] if text.count("\n") >= 3 else ""
    return rest[1:] if rest.startswith("\n") else rest


def _stamp_time(now: datetime | None) -> str:
    return (now or datetime.now()).strftime("%Y-%m-%d %H:%M")


def ensure(root: Path) -> Path:
    path = root / ram_rel(root)
    if not path.is_file():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(render_header(device_name(root), device_id(root), "—", "—") + "\n" + EMPTY_BODY,
                        encoding="utf-8")
    return path


def stamp(root: Path, last_session: str, now: datetime | None = None) -> Path:
    path = ensure(root)
    body = _body(path.read_text(encoding="utf-8"))
    header = render_header(device_name(root), device_id(root), _stamp_time(now), last_session.strip())
    path.write_text(header + "\n" + body, encoding="utf-8")
    return path


# ---------------------------------------------------------------- other laptops

def _retired(root: Path) -> set[str]:
    names = set()
    for f in sorted((root / "devices").glob("*.md")):
        text = f.read_text(encoding="utf-8")
        title = re.search(r"^# (.+)$", text, re.M)
        if title and re.search(r"\*\*Status\*\*: retired", text):
            names.add(title.group(1).strip())
    return names


def others(root: Path) -> list[dict]:
    me, retired, rows = device_name(root), _retired(root), []
    for f in sorted((root / RAM_DIR).glob("*.md")):
        o = owner(f"{RAM_DIR}/{f.name}")
        if o is None or o == me or o in retired or (o == UNREGISTERED and me != UNREGISTERED):
            continue
        h = read_header(f.read_text(encoding="utf-8"))
        rows.append({"device": o, "last_activity": h["last_activity"] if h else "?",
                     "last_session": h["last_session"] if h else "(no header)"})
    rows.sort(key=lambda r: r["last_activity"], reverse=True)
    return rows


# ---------------------------------------------------------------- the Status section

def section_span(text: str, heading: re.Pattern) -> tuple[int, int] | None:
    """(start, end) of a section's lead-in: after its heading, up to the next heading of level 1–3."""
    m = heading.search(text)
    if not m:
        return None
    start = m.end() + 1 if m.end() < len(text) else m.end()
    nxt = BLOCK_END.search(text, start)
    return start, nxt.start() if nxt else len(text)


def status_span(text: str) -> tuple[int, int] | None:
    return section_span(text, STATUS_HEADING)


def status_units(body: str) -> list[tuple[str, list[str]]]:
    """Split the Status body into (key, lines) units. A `**Key**:` line starts a unit; text before the
    first key is a unit with key "" so it is never silently kept or dropped."""
    units: list[tuple[str, list[str]]] = []
    for line in body.splitlines():
        m = STATUS_KEY.match(line)
        if m:
            units.append((m.group(1).strip(), [line]))
        elif units:
            units[-1][1].append(line)
        elif line.strip():
            units.append(("", [line]))
    for _, lines in units:
        while lines and not lines[-1].strip():
            lines.pop()
    return units


def _items(lines: list[str]) -> list[str]:
    return [ln[2:].strip() for ln in lines[1:] if ln.startswith("- ")]


def repos(text: str) -> list[dict]:
    """The `**Repos**:` bullets — `- \\`path\\` · branch` — as [{path, branch}]."""
    span = status_span(text)
    if span is None:
        return []
    rows = []
    for key, lines in status_units(text[span[0]:span[1]]):
        if key != "Repos":
            continue
        for item in _items(lines):
            path, _, branch = item.partition(" · ")
            rows.append({"path": path.strip().strip("`"), "branch": branch.strip().strip("`") or None})
    return rows


def check(root: Path) -> dict:
    """Read-only lint of own RAM: Status shape and the session-block cap."""
    path = root / ram_rel(root)
    if not path.is_file():
        return {"ok": True, "issues": [], "status_lines": 0, "blocks": 0}
    text = path.read_text(encoding="utf-8")
    issues = []
    span = status_span(text)
    body = text[span[0]:span[1]] if span else ""
    for key, lines in status_units(body):
        if key not in STATUS_KEYS:
            issues.append(f"Status key '{key or '(no key)'}' is not one of {', '.join(STATUS_KEYS)} "
                          f"({len(lines)} line{'' if len(lines) == 1 else 's'}) — trim moves it to the archive")
        elif key == "Focus" and len(lines) > 1:
            issues.append(f"Focus spans {len(lines)} lines (max 1)")
        elif key != "Focus" and len(_items(lines)) > LIST_CAP:
            issues.append(f"{key} has {len(_items(lines))} items (max {LIST_CAP})")
    recap = section_span(text, RECAP_HEADING)
    loose = _paragraphs(_loose_recap(text[recap[0]:recap[1]])[1]) if recap else 0
    if loose:
        issues.append(f"{loose} loose recap paragraph(s) outside dated ### blocks — trim moves them to the archive")
    blocks = len(session_parts(text)[1])
    if blocks > BLOCK_CAP:
        issues.append(f"{blocks} session blocks (max {BLOCK_CAP}) — trim archives the oldest")
    return {"ok": not issues, "issues": issues,
            "status_lines": sum(1 for ln in body.splitlines() if ln.strip()), "blocks": blocks}


def _split_status(text: str) -> tuple[str, list[str]]:
    """Return (text with only the allowed Status keys, the moved-out lines)."""
    span = status_span(text)
    if span is None:
        return text, []
    units = status_units(text[span[0]:span[1]])
    moved = [ln for key, lines in units if key not in STATUS_KEYS for ln in lines]
    if not moved:
        return text, []
    kept = "".join(ln + "\n" for key, lines in units if key in STATUS_KEYS for ln in lines)
    return text[:span[0]] + kept + "\n" + text[span[1]:], moved


def _loose_recap(body: str) -> tuple[list[str], list[str]]:
    """Split the Recap section's lead-in into (kept italic subtitle lines, loose paragraphs). Session
    recaps belong in dated `###` blocks, where the cap can count them; anything else is loose."""
    kept, moved = [], []
    for line in body.splitlines():
        if ITALIC_LINE.match(line):
            kept.append(line)
        elif line.strip() or (moved and moved[-1].strip()):
            moved.append(line)
    while moved and not moved[-1].strip():
        moved.pop()
    return kept, moved


def _paragraphs(lines: list[str]) -> int:
    return sum(1 for i, ln in enumerate(lines) if ln.strip() and (i == 0 or not lines[i - 1].strip()))


def _split_recap(text: str) -> tuple[str, list[str]]:
    """Return (text with only dated blocks after the Recap heading, the loose lines moved out)."""
    span = section_span(text, RECAP_HEADING)
    if span is None:
        return text, []
    kept, moved = _loose_recap(text[span[0]:span[1]])
    if not moved:
        return text, []
    lead = "".join(ln + "\n" for ln in kept)
    return text[:span[0]] + lead + ("\n" if span[1] < len(text) else "") + text[span[1]:], moved


def _split_extras(text: str) -> tuple[str, list[str]]:
    text, status = _split_status(text)
    text, recap = _split_recap(text)
    return text, status + ([""] if status and recap else []) + recap


# ---------------------------------------------------------------- session blocks and the archive

def session_parts(text: str) -> tuple[str, list[tuple[str, str]], str]:
    """Split RAM into (prefix, [(heading, chunk)…], suffix). Blocks are consecutive dated `### ` sections;
    any heading of level 1–3 that is not a dated `### ` ends the run, so trailing `##` sections stay put."""
    heads = [(m.start(), bool(SESSION_BLOCK.match(text, m.start()))) for m in BLOCK_END.finditer(text)]
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


def tag_heading(chunk: str, name: str) -> str:
    first, nl, rest = chunk.partition("\n")
    m = DATED_HEADING.match(first)
    if not m or f" · {name}" in first:
        return chunk
    date, tail = m.group(1), m.group(2)
    cut = tail.find(" — ")
    tagged = (f"### {date}{tail[:cut]} · {name}{tail[cut:]}" if cut >= 0 else f"### {date}{tail} · {name}")
    return tagged + nl + rest


def prepend_to_archive(archive: str, blocks: list[str]) -> str:
    if not blocks:
        return archive
    m = ANY_H3.search(archive)
    cut = m.start() if m else len(archive)
    head = archive[:cut]
    if head and not head.endswith("\n\n"):
        head = head.rstrip("\n") + "\n\n"
    return head + "".join(b.rstrip("\n") + "\n\n" for b in blocks) + archive[cut:]


def trim(root: Path, cap: int = BLOCK_CAP, now: datetime | None = None) -> list[str]:
    """Keep the `cap` newest session blocks in own RAM; move the rest, device-tagged, to the archive.
    Status keys other than Focus / Repos / Open loops, and loose recap paragraphs that are not dated
    `###` blocks, move out too — verbatim, as one dated block.
    Same-date blocks keep file order, so new blocks must be added above older ones."""
    path = root / ram_rel(root)
    if not path.is_file():
        return []
    name = device_name(root)
    text, moved = _split_extras(path.read_text(encoding="utf-8"))
    tagged = []
    if moved:
        day = (now or datetime.now()).strftime("%Y-%m-%d")
        tagged.append(f"### {day} · {name} — status moved out of RAM\n\n" + "".join(ln + "\n" for ln in moved))
    prefix, blocks, suffix = session_parts(text)
    ordered = sorted(blocks, key=lambda hc: SESSION_BLOCK.match(hc[0]).group(1), reverse=True)
    keep, extra = ordered[:cap], ordered[cap:]
    tagged += [tag_heading(chunk, name) for _, chunk in extra]
    if not tagged:
        return []
    path.write_text(prefix + "".join(chunk for _, chunk in keep) + suffix, encoding="utf-8")
    archive = root / ARCHIVE
    current = archive.read_text(encoding="utf-8") if archive.is_file() else "# Session Archive\n\n"
    archive.write_text(prepend_to_archive(current, tagged), encoding="utf-8")
    return [t.split("\n", 1)[0] for t in tagged]


# ---------------------------------------------------------------- the old pointer file

def pointer_dirty(root: Path) -> bool:
    pointer = root / POINTER
    return pointer.is_file() and bool(pointer.read_text(encoding="utf-8").replace(POINTER_TEXT, "", 1).strip())


def absorb_pointer(root: Path, now: datetime | None = None) -> str | None:
    pointer = root / POINTER
    if not pointer.is_file():
        return None
    text = pointer.read_text(encoding="utf-8")
    extra = text.replace(POINTER_TEXT, "", 1).strip()
    if not extra:
        if text != POINTER_TEXT:
            pointer.write_text(POINTER_TEXT, encoding="utf-8")
        return None
    path = ensure(root)
    moved = f"\n<!-- moved from {POINTER} on {_stamp_time(now)} -->\n{extra}\n"
    path.write_text(path.read_text(encoding="utf-8").rstrip("\n") + "\n" + moved, encoding="utf-8")
    pointer.write_text(POINTER_TEXT, encoding="utf-8")
    return f"Moved stray content from {POINTER} into {ram_rel(root)}"


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ram.py", description="Device-based session RAM")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("path", "ensure", "others", "trim", "check", "absorb"):
        sub.add_parser(name)
    st = sub.add_parser("stamp")
    st.add_argument("text")
    args = ap.parse_args(argv)
    root = Path(args.root)
    if args.cmd == "path":
        print(ram_rel(root))
    elif args.cmd == "ensure":
        print(ensure(root).relative_to(root))
    elif args.cmd == "others":
        for r in others(root):
            print(f"{r['device']} — {r['last_activity']} · {r['last_session']}")
    elif args.cmd == "stamp":
        print(stamp(root, args.text).relative_to(root))
    elif args.cmd == "trim":
        print(json.dumps({"archived": trim(root)}))
    elif args.cmd == "check":
        print(json.dumps(check(root), indent=2))
    elif args.cmd == "absorb":
        note = absorb_pointer(root)
        if note:
            print(note)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
