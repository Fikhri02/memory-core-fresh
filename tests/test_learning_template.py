"""The learning template and health.py must agree on file formats. Stdlib only."""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "learning" / "_template"
sys.path.insert(0, str(ROOT / "mcp-spike"))

import health  # noqa: E402

HEADER = "| Concept | Module | Confidence | Last reviewed | Note |"


class LearningTemplate(unittest.TestCase):
    def test_every_template_named_in_structure_exists(self):
        structure = (TEMPLATE / "structure.yaml").read_text(encoding="utf-8")
        named = re.findall(r"^\s+template:\s*(\S+)\s*$", structure, re.M)
        self.assertEqual(
            ["general.md", "study-plan.md", "progress.md", "projects.md"], named
        )
        for name in named + ["note.md", "exercise.md"]:
            self.assertTrue((TEMPLATE / name).is_file(), name)

    def test_progress_template_has_the_exact_header(self):
        self.assertIn(HEADER, (TEMPLATE / "progress.md").read_text(encoding="utf-8"))

    def test_progress_row_in_template_format_is_parsed_by_health(self):
        text = (TEMPLATE / "progress.md").read_text(encoding="utf-8").replace(
            "|---------|--------|-----------|---------------|------|",
            "|---------|--------|-----------|---------------|------|\n"
            "| brute-force-lockout | M3 | shaky | 2026-10-02 | Notes/brute-force-lockout.md |",
        )
        rows = health.progress_rows(text)
        self.assertEqual(
            [("brute-force-lockout", "M3", "shaky", "2026-10-02", "Notes/brute-force-lockout.md")], rows
        )

    def test_empty_templates_contain_no_parseable_rows_or_links(self):
        # The template ships to every install; an example row would read as a real concept.
        self.assertEqual([], health.progress_rows((TEMPLATE / "progress.md").read_text(encoding="utf-8")))
        self.assertEqual([], health.PROJECT_LINK.findall((TEMPLATE / "projects.md").read_text(encoding="utf-8")))

    def test_project_line_in_documented_format_is_parsed_by_health(self):
        self.assertEqual(["acme-auth"], health.PROJECT_LINK.findall("- `acme-auth` — realms and SPIs\n"))


if __name__ == "__main__":
    unittest.main()
