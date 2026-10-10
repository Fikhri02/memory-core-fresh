"""Tests for import-package/scripts — pkgformat, pkgclean, pkgstate and the pkgtool CLI. Stdlib only."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "plugins" / "violet-skills" / "skills" / "import-package" / "scripts"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO / "mcp-spike"))

import health  # noqa: E402
import pkgformat  # noqa: E402
from pkgformat import PackageError, Section  # noqa: E402


def write(root: Path, relpath: str, text: str) -> Path:
    p = root / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def header(**over) -> dict:
    fields = {"package": "wikipetia@project", "kind": "project", "audience": "self",
              "version": 1, "exported": "2026-10-10", "format": 2}
    fields.update(over)
    return fields


class TempRoot(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


FORMAT1 = """---
package: dep@acme
version: 2
exported: 2026-09-03
ecosystem:
  slug: acme
  label: "Acme Inc — POS platform"
feature:
  slug: dep
  label: "DEP (Device Enrollment Program)"
members:
  - {project: acme-admin, component: DEP, git_origin: "https://github.com/acme/acme-admin.git"}
---

## note

# DEP — cross-ecosystem note

Spans three repos.

## map

- **DEP** — Admin drives · API owns the data

## overview: acme-admin

DEP screens live under lib/dep/.
"""


class HeaderValidation(unittest.TestCase):
    def fields(self, **over):
        return {k: str(v) for k, v in header(**over).items()}

    def test_each_kind_accepts_its_own_id(self):
        for kind, pid in (("project", "wikipetia@project"), ("ecosystem", "acme@ecosystem"),
                          ("feature", "dep@acme"), ("profile", "profile@irfan"),
                          ("profile", "profile@shared")):
            h = pkgformat.validate_header(self.fields(kind=kind, package=pid))
            self.assertEqual((kind, pid), (h.kind, h.package))

    def test_id_must_fit_kind(self):
        for kind, pid in (("project", "acme@ecosystem"), ("feature", "dep@project"),
                          ("profile", "irfan@profile"), ("ecosystem", "Acme@ecosystem"),
                          ("feature", "profile@acme"), ("project", "noscope")):
            with self.assertRaisesRegex(PackageError, "not a valid"):
                pkgformat.validate_header(self.fields(kind=kind, package=pid))

    def test_missing_kind_is_named(self):
        f = self.fields()
        del f["kind"]
        with self.assertRaisesRegex(PackageError, "`kind`"):
            pkgformat.validate_header(f)

    def test_unknown_kind_is_named(self):
        with self.assertRaisesRegex(PackageError, "`kind`"):
            pkgformat.validate_header(self.fields(kind="team"))

    def test_unknown_audience_is_named(self):
        with self.assertRaisesRegex(PackageError, "`audience`"):
            pkgformat.validate_header(self.fields(audience="team"))

    def test_future_format_is_refused(self):
        with self.assertRaisesRegex(PackageError, "newer"):
            pkgformat.validate_header(self.fields(format=3))

    def test_version_must_be_a_positive_whole_number(self):
        for bad in ("0", "two", ""):
            with self.assertRaisesRegex(PackageError, "`version`"):
                pkgformat.validate_header(self.fields(version=bad))

    def test_format_1_feature_package_reads_as_feature_share(self):
        h, sections = pkgformat.read_package(FORMAT1)
        self.assertEqual(("dep@acme", "feature", "share", 2, 1),
                         (h.package, h.kind, h.audience, h.version, h.format))
        self.assertEqual(["note", "map", "overview"], [s.type for s in sections])
        self.assertEqual("acme-admin", sections[2].arg)
        self.assertTrue(sections[0].content.startswith("# DEP"))

    def test_format_1_without_members_is_refused(self):
        broken = FORMAT1.replace("members:\n", "crew:\n")
        with self.assertRaisesRegex(PackageError, "`members`"):
            pkgformat.read_package(broken)

    def test_comments_and_quotes_in_header_values(self):
        text = ('---\npackage: wikipetia@project   # id\nkind: project\naudience: self\n'
                'version: 1\nexported: 2026-10-10\nformat: 2\n'
                'source_install: "irfan@macbook"  # label\n---\n')
        h, _ = pkgformat.read_package(text)
        self.assertEqual("wikipetia@project", h.package)
        self.assertEqual("irfan@macbook", h.fields["source_install"])

    def test_no_frontmatter_is_refused(self):
        with self.assertRaisesRegex(PackageError, "frontmatter"):
            pkgformat.read_package("## file: x.md\n")


class SectionsRoundTrip(unittest.TestCase):
    def roundtrip(self, sections):
        _, back = pkgformat.read_package(pkgformat.render(header(), sections))
        return back

    def test_files_links_and_sections_survive(self):
        src = [Section("file", "project-management/w/General.md", "# W\n\nBody.\n"),
               Section("section", "main/main-memory.md#Core Purpose", "## Core Purpose\n\nHelp.\n"),
               Section("link", "project-management/w/Plans/a.md -> project-plans/active/a.md", "")]
        self.assertEqual(src, self.roundtrip(src))

    def test_content_with_section_lines_and_fences_survives(self):
        tricky = "## file: not/a/header.md\n\n```pkg\ninner\n```\n\n````\nfour\n````\n"
        src = [Section("file", "project-management/w/Design.md", tricky),
               Section("file", "project-management/w/General.md", "after\n")]
        self.assertEqual(src, self.roundtrip(src))

    def test_empty_file_survives(self):
        src = [Section("file", "project-management/w/Empty.md", "")]
        self.assertEqual(src, self.roundtrip(src))

    def test_crlf_package_reads_cleanly(self):
        src = [Section("file", "project-management/w/General.md", "line one\nline two\n")]
        text = pkgformat.render(header(), src).replace("\n", "\r\n")
        h, back = pkgformat.read_package(text)
        self.assertEqual("wikipetia@project", h.package)
        self.assertEqual(src, back)
        self.assertNotIn("\r", back[0].content)

    def test_unclosed_fence_is_refused(self):
        text = pkgformat.render(header(), []) + "## file: project-management/w/x.md\n\n```pkg\nno close\n"
        with self.assertRaisesRegex(PackageError, "unclosed"):
            pkgformat.read_package(text)


class PackStaging(TempRoot):
    def test_staged_files_become_sorted_sections_with_links_last(self):
        write(self.root, "project-management/w/General.md", "g\n")
        write(self.root, "project-plans/active/a.md", "a\n")
        write(self.root, ".DS_Store", "ignored")
        text = pkgformat.pack_staging(
            header(), self.root,
            links=[("project-management/w/Plans/a.md", "project-plans/active/a.md")])
        _, sections = pkgformat.read_package(text)
        self.assertEqual(
            [("file", "project-management/w/General.md"), ("file", "project-plans/active/a.md"),
             ("link", "project-management/w/Plans/a.md -> project-plans/active/a.md")],
            [(s.type, s.arg) for s in sections])

    def test_profile_sections_are_staged_by_hash_name(self):
        write(self.root, "main/main-memory.md#Core Purpose", "## Core Purpose\n\nHelp.\n")
        text = pkgformat.pack_staging(header(kind="profile", package="profile@irfan"), self.root)
        _, sections = pkgformat.read_package(text)
        self.assertEqual([("section", "main/main-memory.md#Core Purpose")],
                         [(s.type, s.arg) for s in sections])

    def test_feature_parts_are_staged_with_at_names(self):
        write(self.root, "@note.md", "# DEP\n")
        write(self.root, "@overview/acme-admin.md", "screens\n")
        text = pkgformat.pack_staging(header(kind="feature", package="dep@acme"), self.root)
        _, sections = pkgformat.read_package(text)
        self.assertEqual([("note", ""), ("overview", "acme-admin")],
                         [(s.type, s.arg) for s in sections])

    def test_binary_file_is_refused_by_name(self):
        f = self.root / "project-management" / "w" / "Feedbacks" / "shot.png"
        f.parent.mkdir(parents=True)
        f.write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe\x00")
        with self.assertRaisesRegex(PackageError, "shot.png"):
            pkgformat.pack_staging(header(), self.root)

    def test_invalid_header_is_never_emitted(self):
        with self.assertRaisesRegex(PackageError, "`kind`"):
            pkgformat.pack_staging(header(kind="team"), self.root)


if __name__ == "__main__":
    unittest.main()
