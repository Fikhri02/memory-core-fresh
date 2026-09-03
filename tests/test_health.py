"""Tests for mcp-spike/health.py. Stdlib only — health.py is dependency-free by design."""

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


if __name__ == "__main__":
    unittest.main()
