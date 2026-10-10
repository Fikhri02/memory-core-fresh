#!/usr/bin/env python3
"""pkgtool — the deterministic half of export-package and import-package.

Run from the memory root:  python3 plugins/violet-skills/skills/import-package/scripts/pkgtool.py <command>

  validate PACKAGE                         check the header; print its fields
  sections PACKAGE                         list sections
  sha FILE [--section HEADING]             sha of the comparable text
  strip FILE [--column NAME ...] [--write] remove machine-bound data
  scan FILE                                list likely personal data
  profile-headings FILE --companion NAME   classify `## ` headings companion|user
  profile-share FILE --template T --user N --companion N --out-dir DIR
                                           stage main-memory.md for a share profile, names removed
  placeholders FILE --user N --companion N [--write]
  next-version ID [--root DIR]
  pack --spec SPEC.json --staging DIR --out FILE
  plan PACKAGE [--root DIR] [--rename OLD=NEW ...] [--fill KEY=VALUE ...]
  extract PACKAGE TARGET [--root DIR] [--rename OLD=NEW ...] [--fill KEY=VALUE ...]
  merge-timeline PACKAGE TARGET [--root DIR] [--rename OLD=NEW ...] [--fill KEY=VALUE ...]
  link PACKAGE LINK [--root DIR] [--rename OLD=NEW ...]
                                           create one planned symlink (never replaces a real file)
  feature-targets PACKAGE                  the only paths a feature import may write, validated
  record ID --version N --targets T [T ...] [--root DIR] [--date YYYY-MM-DD]
  log --dir in|out --package ID --kind K --audience A --version N --result R [--note T] [--root DIR] [--date D]

Exit 0 on success, 1 on a refused input (reason on stderr), 2 on bad usage.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pkgclean  # noqa: E402
import pkgformat  # noqa: E402
import pkgstate  # noqa: E402
from pkgformat import PackageError  # noqa: E402


def _read(path: str) -> str:
    return pkgformat.normalise_newlines(Path(path).read_text(encoding="utf-8"))


def _renames(pairs) -> dict:
    out = {}
    for pair in pairs or []:
        old, sep, new = pair.partition("=")
        if not sep or not old or not new:
            raise PackageError(f"--rename expects OLD=NEW, got {pair!r}")
        out[old] = new
    return out


def _package(path: str, fills=None):
    """Read a package; `--fill USER_NAME=Sam` replaces {{USER_NAME}} in every section path and body."""
    head, sections = pkgformat.read_package(_read(path))
    for pair in fills or []:
        key, sep, value = pair.partition("=")
        if not sep or not key:
            raise PackageError(f"--fill expects KEY=VALUE, got {pair!r}")
        for s in sections:
            s.arg = s.arg.replace("{{" + key + "}}", value)
            s.content = s.content.replace("{{" + key + "}}", value)
    return head, sections


def cmd_validate(a):
    h, _ = _package(a.package)
    print(f"package={h.package} kind={h.kind} audience={h.audience} version={h.version} format={h.format}")


def cmd_sections(a):
    _, sections = _package(a.package)
    for s in sections:
        print(f"{s.type}\t{s.arg}\t{len(s.content.splitlines())} lines")


def cmd_sha(a):
    text = _read(a.file)
    if a.section:
        text = pkgstate.heading_sections(text).get(a.section)
        if text is None:
            raise PackageError(f"no `## {a.section}` section in {a.file}")
    print(pkgstate.region_sha(pkgstate.comparable(text)))


def cmd_strip(a):
    text, removed = pkgclean.strip(_read(a.file), tuple(a.column or ("Local Path",)))
    for r in removed:
        print(f"removed: {r}", file=sys.stderr)
    if a.write:
        Path(a.file).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def cmd_scan(a):
    for h in pkgclean.scan(_read(a.file)):
        print(f"{h.line}\t{h.kind}\t{h.excerpt}")


def cmd_profile_headings(a):
    for heading in pkgstate.heading_sections(_read(a.file)):
        print(f"{pkgclean.classify_profile_heading(heading, a.companion)}\t{heading}")


def cmd_profile_share(a):
    sections, unknown = pkgstate.share_profile_sections(
        _read(a.file), _read(a.template), user=a.user, companion=a.companion)
    out = Path(a.out_dir) / "main"
    out.mkdir(parents=True, exist_ok=True)
    for heading, text in sections.items():
        (out / f"main-memory.md#{heading}").write_text(text, encoding="utf-8")
    print(f"staged {len(sections)} section(s)")
    for heading in unknown:
        print(f"unknown: {heading}")


def cmd_placeholders(a):
    text = pkgclean.placeholders(_read(a.file), user=a.user, companion=a.companion)
    if a.write:
        Path(a.file).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)


def cmd_next_version(a):
    print(pkgstate.next_version(Path(a.root), a.id))


def cmd_pack(a):
    out = Path(a.out)
    if out.exists():
        raise PackageError(f"{out} already exists — exports are never overwritten; bump the version")
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    text = pkgformat.pack_staging(spec["header"], Path(a.staging),
                                  links=[tuple(p) for p in spec.get("links", [])],
                                  header_extra=spec.get("header_extra", ""))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(out)


def cmd_plan(a):
    h, sections = _package(a.package, a.fill)
    for item in pkgstate.plan(Path(a.root), h, sections, _renames(a.rename)):
        print(f"{item.action}\t{item.target}\t{item.reason}")


def cmd_extract(a):
    h, sections = _package(a.package, a.fill)
    pkgstate.check_target(h.kind, a.target, h.audience)
    section = pkgstate.find_section(sections, a.target, _renames(a.rename))
    if section.type == "section":
        pkgstate.check_section(a.target, section.content)
    pkgstate.write_target(Path(a.root), a.target, section.content, kind=h.kind)
    print(f"wrote {a.target}")


def cmd_link(a):
    h, sections = _package(a.package)
    renames = _renames(a.rename)
    items = pkgstate.plan(Path(a.root), h, sections, renames)   # validates every link and home
    for item in items:
        link, sep, home = item.target.partition(" -> ")
        if sep and link == a.link:
            if item.action == "conflict":
                raise PackageError(f"{link}: {item.reason}")
            pkgstate.make_link(Path(a.root), h.kind, link, home)
            print(f"linked {link} -> {home}")
            return
    raise PackageError(f"package has no link at {a.link!r}")


def cmd_feature_targets(a):
    for role, target in pkgstate.feature_targets(_read(a.package)):
        print(f"{role}\t{target}")


def cmd_merge_timeline(a):
    h, sections = _package(a.package, a.fill)
    pkgstate.check_target(h.kind, a.target, h.audience)
    incoming = pkgstate.find_section(sections, a.target, _renames(a.rename)).content
    root = Path(a.root)
    local = pkgstate.target_text(root, a.target) or ""
    merged = pkgstate.merge_timeline(local, incoming)
    added = len(pkgstate.DATE_HEADER.findall(merged)) - len(pkgstate.DATE_HEADER.findall(local))
    if merged is not local:
        pkgstate.write_target(root, a.target, merged, kind=h.kind)
    print(f"added {added} section(s)")


def cmd_record(a):
    m = pkgstate.record(Path(a.root), a.id, a.version, a.date, a.targets)
    print(f"recorded {len(a.targets)} target(s) in {pkgstate.manifest_path(Path(a.root), m.package)}")


def cmd_log(a):
    sys.stdout.write(pkgstate.append_ledger(
        Path(a.root), date=a.date, direction=a.dir, package=a.package, kind=a.kind,
        audience=a.audience, version=a.version, result=a.result, note=a.note))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pkgtool", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)
    today = date.today().isoformat()

    def add(name, fn):
        sp = sub.add_parser(name)
        sp.set_defaults(fn=fn)
        return sp

    for name, fn in (("validate", cmd_validate), ("sections", cmd_sections)):
        add(name, fn).add_argument("package")
    sp = add("sha", cmd_sha)
    sp.add_argument("file")
    sp.add_argument("--section")
    sp = add("strip", cmd_strip)
    sp.add_argument("file")
    sp.add_argument("--column", action="append")
    sp.add_argument("--write", action="store_true")
    add("scan", cmd_scan).add_argument("file")
    sp = add("profile-headings", cmd_profile_headings)
    sp.add_argument("file")
    sp.add_argument("--companion", required=True)
    sp = add("profile-share", cmd_profile_share)
    sp.add_argument("file")
    sp.add_argument("--template", required=True)
    sp.add_argument("--user", required=True)
    sp.add_argument("--companion", required=True)
    sp.add_argument("--out-dir", required=True)
    sp = add("placeholders", cmd_placeholders)
    sp.add_argument("file")
    sp.add_argument("--user", required=True)
    sp.add_argument("--companion", required=True)
    sp.add_argument("--write", action="store_true")
    sp = add("next-version", cmd_next_version)
    sp.add_argument("id")
    sp.add_argument("--root", default=".")
    sp = add("pack", cmd_pack)
    sp.add_argument("--spec", required=True)
    sp.add_argument("--staging", required=True)
    sp.add_argument("--out", required=True)
    for name, fn, has_target in (("plan", cmd_plan, False), ("extract", cmd_extract, True),
                                 ("merge-timeline", cmd_merge_timeline, True)):
        sp = add(name, fn)
        sp.add_argument("package")
        if has_target:
            sp.add_argument("target")
        sp.add_argument("--root", default=".")
        sp.add_argument("--rename", action="append")
        sp.add_argument("--fill", action="append")
    sp = add("link", cmd_link)
    sp.add_argument("package")
    sp.add_argument("link")
    sp.add_argument("--root", default=".")
    sp.add_argument("--rename", action="append")
    add("feature-targets", cmd_feature_targets).add_argument("package")
    sp = add("record", cmd_record)
    sp.add_argument("id")
    sp.add_argument("--version", type=int, required=True)
    sp.add_argument("--targets", nargs="+", required=True)
    sp.add_argument("--root", default=".")
    sp.add_argument("--date", default=today)
    sp = add("log", cmd_log)
    sp.add_argument("--dir", required=True, choices=("in", "out"))
    sp.add_argument("--package", required=True)
    sp.add_argument("--kind", required=True)
    sp.add_argument("--audience", required=True)
    sp.add_argument("--version", required=True)
    sp.add_argument("--result", required=True)
    sp.add_argument("--note", default="")
    sp.add_argument("--root", default=".")
    sp.add_argument("--date", default=today)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        args.fn(args)
    except (PackageError, FileNotFoundError, json.JSONDecodeError, KeyError) as e:
        print(f"pkgtool: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
