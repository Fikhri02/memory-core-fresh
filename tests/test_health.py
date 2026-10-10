"""Tests for mcp-spike/health.py. Stdlib only — health.py is dependency-free by design."""

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-spike"))

import health  # noqa: E402


def write(root: Path, relpath: str, text: str) -> Path:
    p = root / relpath
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


MAP = """---
ecosystem: acme
label: Acme Inc
updated: 2026-09-01
---

## Members

| Project | Role | Documented | Location |
|---------|------|-----------|----------|
| Admin | admin surface | `acme-admin` | → General.md |

## Relations
"""


class EcosystemFolderLayout(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        (self.root / "project-management" / "acme-admin").mkdir(parents=True)

    def test_map_in_folder_is_discovered(self):
        # Asserted positively: a stale map MUST produce a finding. Asserting the absence of
        # one would pass vacuously when zero ecosystems are discovered.
        write(self.root, "ecosystem/acme/map.md", MAP.replace("2026-09-01", "2025-01-01"))
        findings = health.ecosystem_drift(self.root, today=date(2026, 9, 3))
        stale = [f for f in findings if f.check == "ecosystem_stale"]
        self.assertEqual(1, len(stale))
        self.assertEqual("ecosystem/acme/map.md", stale[0].path)

    def test_fresh_map_in_folder_reports_no_staleness(self):
        write(self.root, "ecosystem/acme/map.md", MAP)
        findings = health.ecosystem_drift(self.root, today=date(2026, 9, 3))
        self.assertEqual([], [f for f in findings
                              if f.check in ("ecosystem_stale", "ecosystem_no_updated")])

    def test_member_missing_is_still_detected_in_folder_layout(self):
        write(self.root, "ecosystem/acme/map.md",
              MAP.replace("`acme-admin`", "`ghost-project`"))
        findings = health.ecosystem_drift(self.root, today=date(2026, 9, 3))
        self.assertEqual(1, len([f for f in findings if f.check == "ecosystem_member_missing"]))

    def test_duplicate_member_names_the_ecosystem_not_the_filename(self):
        # Both maps list the SAME member, so it is a genuine duplicate. The detail must
        # name the two ecosystem folders, not "map, map" (the old f.stem behaviour).
        write(self.root, "ecosystem/eco-one/map.md", MAP)
        write(self.root, "ecosystem/eco-two/map.md", MAP)
        findings = health.ecosystem_drift(self.root, today=date(2026, 9, 3))
        dupes = [f for f in findings if f.check == "ecosystem_duplicate_member"]
        self.assertEqual(1, len(dupes))
        self.assertIn("eco-one", dupes[0].detail)
        self.assertIn("eco-two", dupes[0].detail)
        self.assertNotIn("map", dupes[0].detail)

    def test_ecosystem_folder_without_map_is_reported(self):
        (self.root / "ecosystem" / "empty-eco").mkdir(parents=True)
        findings = health.ecosystem_drift(self.root, today=date(2026, 9, 3))
        self.assertEqual(1, len([f for f in findings if f.check == "ecosystem_no_map"]))


NOTE = """---
ecosystem: acme
feature: dep
members: [{members}]
updated: 2026-09-03
---

# DEP — cross-ecosystem note
"""


class FeatureNoteDrift(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        (self.root / "project-management" / "acme-admin").mkdir(parents=True)
        write(self.root, "ecosystem/acme/map.md", MAP)

    def test_note_naming_a_non_member_is_reported(self):
        write(self.root, "ecosystem/acme/features/dep.md",
              NOTE.format(members="acme-admin, acme-api"))
        findings = health.ecosystem_feature_note_drift(self.root)
        self.assertEqual(1, len(findings))
        self.assertEqual("ecosystem_feature_note_member_unknown", findings[0].check)
        self.assertIn("acme-api", findings[0].detail)

    def test_note_with_only_real_members_is_clean(self):
        write(self.root, "ecosystem/acme/features/dep.md",
              NOTE.format(members="acme-admin"))
        self.assertEqual([], health.ecosystem_feature_note_drift(self.root))

    def test_no_features_folder_is_not_an_error(self):
        self.assertEqual([], health.ecosystem_feature_note_drift(self.root))


REGION = "- **DEP** \u2014 Admin drives \u00b7 Middleware owns the data"

MARKED_MAP = """# Acme Ecosystem

## Shared Domains

- **Voucher** \u2014 local, untouched

<!-- pkg:dep@acme v2 sha:{sha} -->
{region}
<!-- /pkg:dep@acme -->
"""

OWNED_NOTE = """---
ecosystem: acme
feature: dep
source: {{package: dep@acme, version: 2, imported: 2026-09-03, sha: {sha}}}
---
{body}"""


class PackageRegionDrift(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        write(self.root, "migrations/applied/dep@acme.pkg.md", "---\npackage: dep@acme\n---\n")

    def test_region_matching_its_hash_is_clean(self):
        write(self.root, "ecosystem/acme/map.md",
              MARKED_MAP.format(sha=health.region_sha(REGION), region=REGION))
        self.assertEqual([], health.package_region_drift(self.root))

    def test_locally_edited_region_is_reported(self):
        write(self.root, "ecosystem/acme/map.md",
              MARKED_MAP.format(sha=health.region_sha(REGION),
                                region=REGION + " and calculates discounts"))
        findings = health.package_region_drift(self.root)
        self.assertEqual(1, len(findings))
        self.assertEqual("package_region_drift", findings[0].check)
        self.assertIn("dep@acme", findings[0].detail)

    def test_whitespace_only_change_is_not_drift(self):
        write(self.root, "ecosystem/acme/map.md",
              MARKED_MAP.format(sha=health.region_sha(REGION), region=REGION + "   "))
        self.assertEqual([], health.package_region_drift(self.root))

    def test_marker_inside_a_code_fence_is_ignored(self):
        # notes/ and README files document the marker format; those examples are not installs.
        write(self.root, "notes/spec.md",
              "# Spec\n\n```markdown\n" + MARKED_MAP.format(sha="deadbeef", region=REGION) + "```\n")
        self.assertEqual([], health.package_region_drift(self.root))

    def test_wholly_owned_note_reports_body_drift(self):
        body = "\n# DEP \u2014 cross-ecosystem note\n\nThe domain spans three repos.\n"
        write(self.root, "ecosystem/acme/features/dep.md",
              OWNED_NOTE.format(sha=health.region_sha(body), body=body))
        self.assertEqual([], health.package_region_drift(self.root))

        write(self.root, "ecosystem/acme/features/dep.md",
              OWNED_NOTE.format(sha=health.region_sha(body), body=body + "\nEdited locally.\n"))
        findings = health.package_region_drift(self.root)
        self.assertEqual(1, len(findings))
        self.assertEqual("package_region_drift", findings[0].check)

    def test_unclosed_marker_is_reported(self):
        write(self.root, "ecosystem/acme/map.md",
              "<!-- pkg:dep@acme v2 sha:deadbeef -->\n" + REGION + "\n")
        findings = health.package_region_drift(self.root)
        self.assertEqual(1, len(findings))
        self.assertEqual("package_marker_unclosed", findings[0].check)

    def test_sha_is_eight_lowercase_hex(self):
        s = health.region_sha(REGION)
        self.assertRegex(s, r"^[0-9a-f]{8}$")


LEDGER = """# Migration Ledger

| Date | Dir | Package | Kind | Audience | Ver | Result | Note |
|------|-----|---------|------|----------|-----|--------|------|
{rows}
"""


class PackageOrphanMarker(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        write(self.root, "ecosystem/acme/map.md",
              MARKED_MAP.format(sha=health.region_sha(REGION), region=REGION))

    def ledger(self, *rows):
        write(self.root, "migrations/ledger.md", LEDGER.format(rows="\n".join(rows)))

    def test_no_ledger_is_not_an_error(self):
        # Ledger and packages are git-ignored; a fresh clone has nothing to judge against.
        write(self.root, "migrations/applied/.gitkeep", "")
        self.assertEqual([], health.package_orphan_marker(self.root))

    def test_marker_with_an_import_row_is_clean(self):
        self.ledger("| 2026-09-03 | in | dep@acme | feature | share | 2 | applied | |")
        self.assertEqual([], health.package_orphan_marker(self.root))

    def test_partial_and_resolved_imports_count(self):
        for result in ("partial", "conflict-resolved"):
            self.ledger(f"| 2026-09-03 | in | dep@acme | feature | share | 2 | {result} | |")
            self.assertEqual([], health.package_orphan_marker(self.root), result)

    def test_marker_without_an_import_row_is_orphan(self):
        self.ledger("| 2026-09-03 | out | dep@acme | feature | share | 2 | written | |",
                    "| 2026-09-04 | in | dep@acme | feature | share | 3 | refused | bad field |")
        findings = health.package_orphan_marker(self.root)
        self.assertEqual(1, len(findings))
        self.assertEqual("package_orphan_marker", findings[0].check)
        self.assertIn("dep@acme", findings[0].detail)
        self.assertIn("ledger", findings[0].detail)


MANIFEST = """package: w@project
version: 1
imported: 2026-10-10
entries:
{entries}
"""


class PackageManifestDrift(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def install(self, target, text, on_disk=None):
        path = target.partition("#")[0]
        write(self.root, path, on_disk if on_disk is not None else text)
        sha = health.region_sha(health._drop_columns(text, path))
        write(self.root, "migrations/manifests/w@project.yaml",
              MANIFEST.format(entries=f'  - {{path: {json.dumps(target)}, sha: {sha}}}'))

    def test_untouched_install_is_clean(self):
        self.install("project-management/w/General.md", "# W\n")
        self.assertEqual([], health.package_manifest_drift(self.root))

    def test_edited_file_is_medium(self):
        self.install("project-management/w/General.md", "# W\n", on_disk="# W edited\n")
        findings = health.package_manifest_drift(self.root)
        self.assertEqual([("package_manifest_drift", "medium")], [(f.check, f.severity) for f in findings])
        self.assertIn("w@project", findings[0].detail)

    def test_removed_file_is_low(self):
        self.install("project-management/w/General.md", "# W\n")
        (self.root / "project-management/w/General.md").unlink()
        findings = health.package_manifest_drift(self.root)
        self.assertEqual([("package_manifest_drift", "low")], [(f.check, f.severity) for f in findings])

    def test_timeline_growth_is_never_drift(self):
        self.install("project-management/w/Timeline.md", "## 2026-10-01\n",
                     on_disk="## 2026-10-02\n\n## 2026-10-01\n")
        self.assertEqual([], health.package_manifest_drift(self.root))

    def test_local_path_column_is_not_drift(self):
        self.install("project-management/w/General.md", "| Repo |\n|---|\n| api |\n",
                     on_disk="| Repo | Local Path |\n|---|---|\n| api | /Users/me/api |\n")
        self.assertEqual([], health.package_manifest_drift(self.root))

    def test_profile_section_edit_is_drift(self):
        self.install("main/main-memory.md#Core Purpose", "## Core Purpose\nHelp.\n",
                     on_disk="# V\n\n## Core Purpose\nHelp more.\n")
        self.assertEqual(1, len(health.package_manifest_drift(self.root)))

    def test_run_all_includes_manifest_drift(self):
        self.install("project-management/w/General.md", "# W\n", on_disk="# W edited\n")
        checks = {f["check"] for f in health.run_all(self.root)["findings"]}
        self.assertIn("package_manifest_drift", checks)


PROGRESS = """# Keycloak — Progress

| Concept | Module | Confidence | Last reviewed | Note |
|---------|--------|-----------|---------------|------|
{rows}

## Log
"""


class LearningDrift(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)
        (self.root / "project-management" / "acme-auth").mkdir(parents=True)
        write(self.root, "learning/keycloak/General.md", "# Keycloak\n\n**Status**: active\n")

    def progress(self, *rows):
        write(self.root, "learning/keycloak/Progress.md", PROGRESS.format(rows="\n".join(rows)))

    def checks(self, name):
        return [f for f in health.learning_drift(self.root) if f.check == name]

    def test_rated_concept_without_note_is_reported(self):
        self.progress("| brute-force-lockout | M3 | shaky | 2026-10-02 | Notes/brute-force-lockout.md |")
        found = self.checks("learning_note_missing")
        self.assertEqual(1, len(found))
        self.assertEqual("learning/keycloak/Progress.md", found[0].path)
        self.assertIn("brute-force-lockout", found[0].detail)

    def test_rated_concept_with_note_is_clean(self):
        self.progress("| brute-force-lockout | M3 | okay | 2026-10-02 | Notes/brute-force-lockout.md |")
        write(self.root, "learning/keycloak/Notes/brute-force-lockout.md", "# brute-force-lockout\n")
        self.assertEqual([], self.checks("learning_note_missing"))

    def test_unstudied_concept_needs_no_note(self):
        self.progress("| token-exchange | M5 | — | — | Notes/token-exchange.md |")
        self.assertEqual([], self.checks("learning_note_missing"))

    def test_backticked_and_linked_note_paths_resolve(self):
        self.progress(
            "| a-concept | M1 | shaky | 2026-10-01 | `Notes/a-concept.md` |",
            "| b-concept | M1 | solid | 2026-10-01 | [b-concept](Notes/b-concept.md) |",
        )
        write(self.root, "learning/keycloak/Notes/a-concept.md", "# a\n")
        write(self.root, "learning/keycloak/Notes/b-concept.md", "# b\n")
        self.assertEqual([], self.checks("learning_note_missing"))

    def test_backticked_or_capitalised_concept_id_is_still_checked(self):
        # Only start-learning's drafted branch promises kebab-case ids; any other shape must not
        # silently fall outside the check.
        self.progress(
            "| `import-realm` | M2 | shaky | 2026-10-01 | Notes/import-realm.md |",
            "| Blazor_prerender | M4 | okay | 2026-10-01 | Notes/blazor-prerender.md |",
        )
        found = self.checks("learning_note_missing")
        self.assertEqual(2, len(found))
        self.assertIn("`import-realm`", found[0].detail)

    def test_any_unrated_placeholder_is_not_reported(self):
        # An en dash or n/a typed instead of — must not flag every planned concept.
        self.progress(
            "| a-concept | M1 | – | – | Notes/a-concept.md |",
            "| b-concept | M1 | n/a | — | Notes/b-concept.md |",
        )
        self.assertEqual([], self.checks("learning_note_missing"))

    def test_emphasised_rating_is_recognised(self):
        self.progress("| c-concept | M1 | **shaky** | 2026-10-01 | Notes/c-concept.md |")
        found = self.checks("learning_note_missing")
        self.assertEqual(1, len(found))
        self.assertIn("rated shaky", found[0].detail)

    def test_linked_project_missing_is_reported(self):
        write(self.root, "learning/keycloak/Projects.md",
              "# Linked projects\n\n- `acme-auth` — realms and SPIs\n- `ghost-app` — nothing\n")
        found = self.checks("learning_project_missing")
        self.assertEqual(1, len(found))
        self.assertIn("ghost-app", found[0].detail)

    def test_template_folder_is_not_a_topic(self):
        write(self.root, "learning/_template/Progress.md",
              PROGRESS.format(rows="| example | M1 | shaky | 2026-01-01 | Notes/example.md |"))
        write(self.root, "learning/_template/Projects.md", "- `example-project` — example\n")
        self.assertEqual([], health.learning_drift(self.root))

    def test_topic_without_progress_or_projects_is_clean(self):
        self.assertEqual([], health.learning_drift(self.root))

    def test_no_learning_folder_is_not_an_error(self):
        empty = tempfile.TemporaryDirectory()
        self.addCleanup(empty.cleanup)
        self.assertEqual([], health.learning_drift(Path(empty.name)))

    def test_run_all_includes_learning_findings(self):
        self.progress("| brute-force-lockout | M3 | shaky | 2026-10-02 | Notes/brute-force-lockout.md |")
        checks = {f["check"] for f in health.run_all(self.root)["findings"]}
        self.assertIn("learning_note_missing", checks)


if __name__ == "__main__":
    unittest.main()
