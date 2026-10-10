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
import pkgstate  # noqa: E402
import pkgclean  # noqa: E402
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


GENERAL = """# W

## Repositories

| Repo | Git Origin | Local Path |
|------|-----------|------------|
| api | https://github.com/x/api.git | /Users/fikhri/Projects/api |

<!-- pkg:dep@acme v2 sha:ab12cd34 -->
- owned
<!-- /pkg:dep@acme -->
"""

MAP_TABLE = """## Members

| Project | Role | Documented | Location |
|---------|------|-----------|----------|
| Admin | admin | `acme-admin` | → General.md |
| API | backend | — | _(not on this machine)_ |
"""


class Strip(unittest.TestCase):
    def test_local_path_column_and_markers_are_removed(self):
        text, removed = pkgclean.strip(GENERAL)
        self.assertNotIn("Local Path", text)
        self.assertNotIn("/Users/", text)
        self.assertNotIn("pkg:", text)
        self.assertIn("- owned", text)
        self.assertIn("| api | https://github.com/x/api.git |", text)
        self.assertEqual(3, len(removed))

    def test_location_column_only_when_asked(self):
        kept, _ = pkgclean.strip(MAP_TABLE)
        self.assertIn("Location", kept)
        text, _ = pkgclean.strip(MAP_TABLE, ("Local Path", "Location"))
        self.assertNotIn("Location", text)
        self.assertNotIn("not on this machine", text)
        self.assertIn("| Admin | admin | `acme-admin` |", text)

    def test_absence_marker_outside_a_table_is_removed(self):
        text, removed = pkgclean.strip("- API _(not on this machine)_\n")
        self.assertEqual("- API\n", text)
        self.assertEqual(["absence marker"], removed)

    def test_import_provenance_line_is_removed(self):
        text, _ = pkgclean.strip("---\nfeature: dep\nsource: {package: dep@acme, version: 2, sha: ab12cd34}\n---\n")
        self.assertNotIn("source:", text)

    def test_untouched_text_is_returned_exactly(self):
        plain = "# Plain\n\n| A | B |\n|---|---|\n|  1 |2|\n"
        self.assertEqual((plain, []), pkgclean.strip(plain))

    def test_drop_columns_agrees_with_health(self):
        for text in (GENERAL, MAP_TABLE, "no table\n"):
            self.assertEqual(pkgclean.drop_columns(text, pkgclean.MACHINE_COLUMNS, normalise=True)[0],
                             health._drop_columns(text))

    def test_normalise_ignores_cell_padding(self):
        a = "| A | B |\n|---|---|\n| 1 | 2 |\n"
        b = "|A|B|\n| --- | --- |\n|  1 |2|\n"
        self.assertEqual(pkgclean.drop_columns(a, (), normalise=True)[0],
                         pkgclean.drop_columns(b, (), normalise=True)[0])


class Scan(unittest.TestCase):
    def kinds(self, text):
        return [h.kind for h in pkgclean.scan(text)]

    def test_email_is_found(self):
        self.assertEqual(["email"], self.kinds("reach me at jamla@example.com today"))

    def test_git_origin_is_not_an_email(self):
        self.assertEqual([], self.kinds("origin git@github.com:Fikhri02/memory-core.git"))

    def test_phone_is_found_but_dates_and_shas_are_not(self):
        self.assertEqual(["phone"], self.kinds("call +60 12-345 6789"))
        self.assertEqual([], self.kinds("## 2026-10-10 — sha ab12cd34, 20260910"))

    def test_tokens_and_secrets_are_found(self):
        self.assertEqual(["token"], self.kinds("key sk-abcdefghijklmnop1234"))
        self.assertEqual(["token"], self.kinds("ghp_" + "a1" * 12))
        self.assertEqual(["secret"], self.kinds("API_KEY=supersecretvalue"))

    def test_home_paths_are_found(self):
        self.assertEqual(["home-path"], self.kinds("cd /Users/fikhri/Projects/api"))
        self.assertEqual(["home-path"], self.kinds("see /home/irfan/notes"))

    def test_clean_text_has_no_hits_and_lines_are_numbered(self):
        self.assertEqual([], pkgclean.scan("# Title\n\nNothing personal here.\n"))
        self.assertEqual(2, pkgclean.scan("fine\nmail jamla@example.com\n")[0].line)


class ProfileHeadings(unittest.TestCase):
    def test_classification(self):
        cases = {"Violet Profile": "companion", "Communication Style": "companion",
                 "Core Purpose ": "companion", "Jamla Profile": "user",
                 "Identity & Relationship": "user", "Relationship Context": "user",
                 "Something New": "user"}
        for heading, expected in cases.items():
            self.assertEqual(expected, pkgclean.classify_profile_heading(heading, "Violet"), heading)

    def test_placeholders_replace_whole_names_only(self):
        self.assertEqual("{{USER_NAME}}'s companion {{COMPANION_NAME}}. Violetta stays.",
                         pkgclean.placeholders("Jamla's companion Violet. Violetta stays.",
                                               user="Jamla", companion="Violet"))

    def test_empty_names_change_nothing(self):
        self.assertEqual("text", pkgclean.placeholders("text", user="", companion=""))


def pkg(sections, **over):
    """A parsed package: (Header, sections) as plan() takes them."""
    return pkgformat.read_package(pkgformat.render(header(**over), sections))


class HashAgreement(unittest.TestCase):
    INPUTS = ("", "a", "  a  \n\n", "\n\nline one   \nline two\t\n\n", "ünïcode — dash\n")

    def test_region_sha_matches_health(self):
        for text in self.INPUTS:
            self.assertEqual(health.region_sha(text), pkgstate.region_sha(text))

    def test_heading_sections_match_health(self):
        text = "# T\n\n## A\nbody a\n\n```\n## not a heading\n```\n## B\nbody b\n"
        sections = pkgstate.heading_sections(text)
        self.assertEqual(["A", "B"], list(sections))
        self.assertIn("## not a heading", sections["A"])
        for name in ("A", "B", "Missing"):
            self.assertEqual(sections.get(name), health._heading_section(text, name))


class PathSafety(unittest.TestCase):
    def test_unsafe_paths_are_refused(self):
        for kind, target in (("project", "../x.md"), ("project", "/etc/hosts"),
                             ("project", "project-management/../../x.md"),
                             ("project", "project-management/_template/general.md"),
                             ("project", "context/10-git-rules.md"),
                             ("project", "project-management\\w\\x.md"),
                             ("profile", "main/notes.md"),
                             ("profile", "project-management/w/General.md"),
                             ("ecosystem", "main/main-memory.md")):
            with self.assertRaises(PackageError, msg=target):
                pkgstate.check_target(kind, target)

    def test_allowed_paths_pass(self):
        for kind, target in (("project", "project-management/w/General.md"),
                             ("project", "project-plans/active/w.md"),
                             ("project", "debugging/open/w-crash.md"),
                             ("ecosystem", "ecosystem/acme/map.md"),
                             ("profile", "main/main-memory.md#Core Purpose"),
                             ("profile", "main/preferences.md")):
            pkgstate.check_target(kind, target)

    def test_plan_refuses_a_traversal_section_before_reading_anything(self):
        h, s = pkg([Section("file", "../../.ssh/authorized_keys", "ssh-rsa AAA\n")])
        with self.assertRaisesRegex(PackageError, "unsafe"):
            pkgstate.plan(Path("/nonexistent"), h, s)


class Manifests(TempRoot):
    def test_round_trip_with_awkward_paths(self):
        m = pkgstate.Manifest("profile@irfan", 2, "2026-10-12",
                              {'main/main-memory.md#Terms "of" Address': "1a2b3c4d",
                               "main/preferences.md": "5e6f7a8b"})
        path = pkgstate.manifest_path(self.root, "profile@irfan")
        pkgstate.write_manifest(path, m)
        self.assertEqual(m, pkgstate.read_manifest(path))

    def test_missing_manifest_is_none(self):
        self.assertIsNone(pkgstate.read_manifest(self.root / "nope.yaml"))

    def test_record_refuses_a_missing_target(self):
        with self.assertRaisesRegex(PackageError, "does not exist"):
            pkgstate.record(self.root, "w@project", 1, "2026-10-10", ["project-management/w/General.md"])


class Plan(TempRoot):
    G = "project-management/w/General.md"

    def install(self, content="# W\n", version=1):
        """Simulate a completed import: write the file and record it."""
        write(self.root, self.G, content)
        pkgstate.record(self.root, "wikipetia@project", version, "2026-10-10", [self.G])

    def actions(self, content, version=1, renames=None):
        h, s = pkg([Section("file", self.G, content)], version=version)
        return [(i.action, i.target) for i in pkgstate.plan(self.root, h, s, renames)]

    def test_new_when_absent(self):
        self.assertEqual([("new", self.G)], self.actions("# W\n"))

    def test_unchanged_after_install(self):
        self.install()
        self.assertEqual([("unchanged", self.G)], self.actions("# W\n"))

    def test_update_when_newer_and_untouched(self):
        self.install()
        self.assertEqual([("update", self.G)], self.actions("# W v2\n", version=2))

    def test_conflict_when_edited_locally(self):
        self.install()
        write(self.root, self.G, "# W — edited here\n")
        h, s = pkg([Section("file", self.G, "# W v2\n")], version=2)
        item = pkgstate.plan(self.root, h, s)[0]
        self.assertEqual("conflict", item.action)
        self.assertIn("edited here", item.reason)

    def test_conflict_when_present_without_record(self):
        write(self.root, self.G, "# W — documented here first\n")
        self.assertEqual([("conflict", self.G)], self.actions("# W\n"))

    def test_skip_older(self):
        self.install(version=3)
        self.assertEqual([("skip-older", self.G)], self.actions("# W v2\n", version=2))

    def test_same_version_different_content_is_a_conflict(self):
        self.install()
        self.assertEqual([("conflict", self.G)], self.actions("# W but different\n", version=1))

    def test_local_path_column_added_after_import_is_not_an_edit(self):
        stripped = "| Repo | Git Origin |\n|---|---|\n| api | https://x/api.git |\n"
        self.install(stripped)
        write(self.root, self.G, "| Repo | Git Origin | Local Path |\n|---|---|---|\n"
                                 "| api | https://x/api.git | /Users/me/api |\n")
        self.assertEqual([("unchanged", self.G)], self.actions(stripped))

    def test_timeline_merges_and_reports_unchanged_when_nothing_new(self):
        t = "project-management/w/Timeline.md"
        write(self.root, t, "# T\n\n## 2026-10-02\n- local\n\n## 2026-10-01\n- shared\n")
        h, s = pkg([Section("file", t, "# T\n\n## 2026-10-03\n- new\n\n## 2026-10-01\n- shared\n")])
        self.assertEqual("merge-timeline", pkgstate.plan(self.root, h, s)[0].action)
        h, s = pkg([Section("file", t, "# T\n\n## 2026-10-01\n- shared\n")])
        self.assertEqual("unchanged", pkgstate.plan(self.root, h, s)[0].action)

    def test_rename_moves_targets_and_links(self):
        h, s = pkg([Section("file", self.G, "# W\n"),
                    Section("link", "project-management/w/Plans/a.md -> project-plans/active/a.md", "")])
        items = pkgstate.plan(self.root, h, s, {"project-management/w": "project-management/w2"})
        self.assertEqual(["project-management/w2/General.md",
                          "project-management/w2/Plans/a.md -> project-plans/active/a.md"],
                         [i.target for i in items])
        self.assertEqual("link", items[1].action)

    def test_feature_packages_are_refused(self):
        h, s = pkgformat.read_package(FORMAT1)
        with self.assertRaisesRegex(PackageError, "in-file markers"):
            pkgstate.plan(self.root, h, s)

    def test_profile_sections_are_planned_per_heading(self):
        write(self.root, "main/main-memory.md", "# V\n\n## Core Purpose\nHelp.\n\n## Usage Notes\nOld.\n")
        h, s = pkg([Section("section", "main/main-memory.md#Core Purpose", "## Core Purpose\nHelp.\n"),
                    Section("section", "main/main-memory.md#Time Intelligence", "## Time Intelligence\nT.\n")],
                   kind="profile", package="profile@irfan")
        self.assertEqual(["unchanged", "new"], [i.action for i in pkgstate.plan(self.root, h, s)])


class WriteTarget(TempRoot):
    def test_whole_file(self):
        pkgstate.write_target(self.root, "project-management/w/General.md", "# W\n")
        self.assertEqual("# W\n", (self.root / "project-management/w/General.md").read_text())

    def test_section_replaced_in_place(self):
        write(self.root, "main/main-memory.md", "# V\n\n## A\nold\n\n## B\nkeep\n")
        pkgstate.write_target(self.root, "main/main-memory.md#A", "## A\nnew\n")
        self.assertEqual("# V\n\n## A\nnew\n\n## B\nkeep\n",
                         (self.root / "main/main-memory.md").read_text())

    def test_missing_section_appended(self):
        write(self.root, "main/main-memory.md", "# V\n\n## A\nold\n")
        pkgstate.write_target(self.root, "main/main-memory.md#C", "## C\nnew\n")
        self.assertEqual("# V\n\n## A\nold\n\n## C\nnew\n",
                         (self.root / "main/main-memory.md").read_text())

    def test_find_section_honours_renames(self):
        sections = [Section("file", "project-management/w/General.md", "g\n")]
        found = pkgstate.find_section(sections, "project-management/w2/General.md",
                                      {"project-management/w": "project-management/w2"})
        self.assertEqual("g\n", found.content)
        with self.assertRaisesRegex(PackageError, "no section"):
            pkgstate.find_section(sections, "project-management/w/Design.md")


class TimelineMerge(unittest.TestCase):
    def test_newest_first_insertion(self):
        local = "# T\n\n## 2026-10-03\n- c\n\n## 2026-10-01\n- a\n"
        incoming = "# T\n\n## 2026-10-04\n- d\n\n## 2026-10-02\n- b\n\n## 2026-10-01\n- a\n"
        self.assertEqual("# T\n\n## 2026-10-04\n- d\n\n## 2026-10-03\n- c\n\n## 2026-10-02\n- b\n\n"
                         "## 2026-10-01\n- a\n", pkgstate.merge_timeline(local, incoming))

    def test_oldest_first_insertion(self):
        local = "# T\n\n## 2026-10-01\n- a\n\n## 2026-10-03\n- c\n"
        incoming = "## 2026-10-02\n- b\n"
        self.assertEqual("# T\n\n## 2026-10-01\n- a\n\n## 2026-10-02\n- b\n\n## 2026-10-03\n- c\n",
                         pkgstate.merge_timeline(local, incoming))

    def test_suffixed_headers_are_distinct(self):
        local = "## 2026-09-05\n- first\n"
        incoming = "## 2026-09-05 (session 2)\n- second\n\n## 2026-09-05\n- first, other wording\n"
        merged = pkgstate.merge_timeline(local, incoming)
        self.assertEqual(1, merged.count("## 2026-09-05\n"))
        self.assertIn("## 2026-09-05 (session 2)", merged)
        self.assertIn("- first\n", merged)
        self.assertNotIn("other wording", merged)

    def test_nothing_new_returns_local_exactly(self):
        local = "# T\n\n## 2026-10-01\n- a   \n\n\n"
        self.assertIs(local, pkgstate.merge_timeline(local, "## 2026-10-01\n- a\n"))

    def test_local_without_dates_gets_incoming_appended(self):
        self.assertEqual("# T\n\n## 2026-10-01\n- a\n",
                         pkgstate.merge_timeline("# T\n", "## 2026-10-01\n- a\n"))


class Ledger(TempRoot):
    def append(self, **over):
        row = dict(date="2026-10-10", direction="out", package="wikipetia@project", kind="project",
                   audience="self", version=1, result="written", note="out/wikipetia@project.v1.pkg.md")
        row.update(over)
        return pkgstate.append_ledger(self.root, **row)

    def test_first_append_creates_the_header(self):
        self.append()
        text = pkgstate.ledger_path(self.root).read_text()
        self.assertTrue(text.startswith("# Migration Ledger"))
        self.assertIn("| Date | Dir | Package | Kind | Audience | Ver | Result | Note |", text)
        self.assertEqual(1, len(pkgstate.ledger_rows(self.root)))

    def test_rows_round_trip_with_pipes_in_notes(self):
        self.append()
        self.append(direction="in", result="partial", note="2 placed | api not here\nsecond line")
        rows = pkgstate.ledger_rows(self.root)
        self.assertEqual(["out", "in"], [r["dir"] for r in rows])
        self.assertEqual("2 placed | api not here second line", rows[1]["note"])

    def test_invalid_result_for_direction_is_refused(self):
        with self.assertRaisesRegex(PackageError, "not valid"):
            self.append(direction="out", result="applied")
        with self.assertRaisesRegex(PackageError, "direction"):
            self.append(direction="sideways")

    def test_next_version_reads_out_folder_ledger_and_legacy_files(self):
        self.assertEqual(1, pkgstate.next_version(self.root, "wikipetia@project"))
        write(self.root, "migrations/out/wikipetia@project.v2.pkg.md", "x")
        self.assertEqual(3, pkgstate.next_version(self.root, "wikipetia@project"))
        self.append(version=5)
        self.assertEqual(6, pkgstate.next_version(self.root, "wikipetia@project"))
        write(self.root, "migrations/out/dep@acme.pkg.md", "---\npackage: dep@acme\nversion: 4\n---\n")
        self.assertEqual(5, pkgstate.next_version(self.root, "dep@acme"))


class Cli(TempRoot):
    def run_tool(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(SCRIPTS / "pkgtool.py"), *map(str, args)],
                              capture_output=True, text=True, cwd=cwd or self.root)

    def make_package(self, version=1, general="# W\n"):
        staging = self.root / "staging"
        write(staging, "project-management/w/General.md", general)
        write(staging, "project-management/w/Timeline.md", "# T\n\n## 2026-10-01\n- a\n")
        write(staging, "project-plans/active/w.md", "# Plan\n")
        spec = self.root / "spec.json"
        spec.write_text(json.dumps({
            "header": header(package="w@project", version=version),
            "header_extra": "",
            "links": [["project-management/w/Plans/w.md", "project-plans/active/w.md"]]}))
        out = self.root / f"w@project.v{version}.pkg.md"
        result = self.run_tool("pack", "--spec", spec, "--staging", staging, "--out", out)
        self.assertEqual(0, result.returncode, result.stderr)
        import shutil
        shutil.rmtree(staging)
        return out

    def test_validate_reports_and_refuses(self):
        good = self.make_package()
        r = self.run_tool("validate", good)
        self.assertEqual(0, r.returncode)
        self.assertEqual("package=w@project kind=project audience=self version=1 format=2", r.stdout.strip())
        bad = write(self.root, "bad.pkg.md", "---\npackage: w@project\nformat: 2\n---\n")
        r = self.run_tool("validate", bad)
        self.assertEqual(1, r.returncode)
        self.assertIn("`kind`", r.stderr)

    def test_pack_refuses_to_overwrite(self):
        out = self.make_package()
        staging = self.root / "staging2"
        write(staging, "project-management/w/General.md", "x\n")
        spec = self.root / "spec2.json"
        spec.write_text(json.dumps({"header": header(package="w@project"), "header_extra": "", "links": []}))
        r = self.run_tool("pack", "--spec", spec, "--staging", staging, "--out", out)
        self.assertEqual(1, r.returncode)
        self.assertIn("exists", r.stderr)

    def test_full_import_cycle_then_reimport_is_unchanged(self):
        pkgfile = self.make_package()
        dst = self.root / "dst"
        dst.mkdir()
        r = self.run_tool("plan", pkgfile, "--root", dst)
        lines = [l.split("\t") for l in r.stdout.strip().splitlines()]
        self.assertEqual(["new", "new", "new", "link"], [l[0] for l in lines])
        targets = [l[1] for l in lines if l[0] == "new"]
        for t in targets:
            self.assertEqual(0, self.run_tool("extract", pkgfile, t, "--root", dst).returncode)
        self.assertEqual("# W\n", (dst / "project-management/w/General.md").read_text())
        r = self.run_tool("record", "w@project", "--version", 1, "--targets", *targets,
                          "--root", dst, "--date", "2026-10-10")
        self.assertEqual(0, r.returncode, r.stderr)
        r = self.run_tool("plan", pkgfile, "--root", dst)
        self.assertEqual(["unchanged"] * 3 + ["link"],
                         [l.split("\t")[0] for l in r.stdout.strip().splitlines()])
        r = self.run_tool("log", "--dir", "in", "--package", "w@project", "--kind", "project",
                          "--audience", "self", "--version", 1, "--result", "applied",
                          "--note", "3 files", "--root", dst, "--date", "2026-10-10")
        self.assertEqual(0, r.returncode, r.stderr)
        self.assertIn("| 2026-10-10 | in | w@project |", (dst / "migrations/ledger.md").read_text())

    def test_extract_refuses_unsafe_target(self):
        pkgfile = self.make_package()
        r = self.run_tool("extract", pkgfile, "../escape.md", "--root", self.root)
        self.assertEqual(1, r.returncode)
        self.assertFalse((self.root.parent / "escape.md").exists())

    def test_merge_timeline_in_place(self):
        pkgfile = self.make_package()
        dst = self.root / "dst"
        write(dst, "project-management/w/Timeline.md", "# T\n\n## 2026-10-05\n- local\n")
        r = self.run_tool("merge-timeline", pkgfile, "project-management/w/Timeline.md", "--root", dst)
        self.assertEqual("added 1 section(s)", r.stdout.strip())
        self.assertIn("## 2026-10-01", (dst / "project-management/w/Timeline.md").read_text())

    def test_strip_scan_sha_and_profile_helpers(self):
        f = write(self.root, "General.md", GENERAL)
        r = self.run_tool("strip", f, "--write")
        self.assertEqual(0, r.returncode)
        self.assertNotIn("Local Path", f.read_text())
        self.assertIn("table column `Local Path`", r.stderr)
        self.assertEqual("", self.run_tool("scan", f).stdout)
        self.assertRegex(self.run_tool("sha", f).stdout.strip(), r"^[0-9a-f]{8}$")
        mem = write(self.root, "mm.md", "# V\n\n## Violet Profile\nx\n\n## Jamla Profile\ny\n")
        r = self.run_tool("profile-headings", mem, "--companion", "Violet")
        self.assertEqual("companion\tViolet Profile\nuser\tJamla Profile", r.stdout.strip())
        r = self.run_tool("sha", mem, "--section", "Violet Profile")
        self.assertEqual(pkgstate.region_sha("## Violet Profile\nx\n"), r.stdout.strip())

    def test_next_version(self):
        self.make_package()
        write(self.root, "migrations/out/w@project.v1.pkg.md", "x")
        self.assertEqual("2", self.run_tool("next-version", "w@project", "--root", self.root).stdout.strip())


if __name__ == "__main__":
    unittest.main()
