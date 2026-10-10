"""Tests for mcp-spike/sync_merge.py. Stdlib only."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-spike"))

import sync_merge as mrg  # noqa: E402

SESSION = """# Violet Current Session Memory - RAM

## Session RAM Status
**Current Session**: {status}

## Session Recap (For AI Restart)

{blocks}### Auto-Reset Behaviour
rules
"""


def block(date, title, body="- did things"):
    return f"### {date} — {title}\n\n{body}\n\n"


def session(status="x", *blocks):
    return SESSION.format(status=status, blocks="".join(blocks))


class SortLogSections(unittest.TestCase):
    def test_same_date_sections_fold_into_one(self):
        text = "# Timeline\n\n## 2026-10-09\n- a\n\n## 2026-10-10\n- from b\n\n## 2026-10-10\n- from a\n"
        out = mrg.sort_log_sections(text)
        self.assertEqual(1, out.count("## 2026-10-10"))
        self.assertIn("- from b\n- from a", out)
        self.assertLess(out.index("2026-10-09"), out.index("2026-10-10"))

    def test_newest_first_files_stay_newest_first(self):
        text = "# Timeline\n\n## 2026-10-11\n- b\n\n## 2026-10-11\n- a\n\n## 2026-10-10\n- old\n\n## 2026-04-20\n- older\n"
        out = mrg.sort_log_sections(text)
        self.assertEqual(1, out.count("## 2026-10-11"))
        self.assertLess(out.index("2026-10-11"), out.index("2026-10-10"))
        self.assertLess(out.index("2026-10-10"), out.index("2026-04-20"))

    def test_titled_headings_with_the_same_date_stay_separate(self):
        text = "# T\n\n## 2026-10-03 — One\n- a\n\n## 2026-10-03 — Two\n- b\n"
        self.assertEqual(text, mrg.sort_log_sections(text))

    def test_level_three_archive(self):
        text = "# Archive\n\nintro\n\n### 2026-10-09 — x\nbody\n\n### 2026-10-09 — x\nbody\nmore\n"
        out = mrg.sort_log_sections(text, level=3)
        self.assertEqual(1, out.count("### 2026-10-09 — x"))
        self.assertIn("more", out)


class CurrentSession(unittest.TestCase):
    def setUp(self):
        self.old = [block("2026-10-09", "c"), block("2026-10-08", "b"), block("2026-10-07", "a")]
        self.base = session("x", *self.old)

    def test_new_blocks_from_both_sides_combine_and_cap_archives_verbatim(self):
        ours = session("x", block("2026-10-11", "ours"), *self.old)
        theirs = session("x", block("2026-10-11", "theirs"), *self.old)
        result = mrg.merge_current_session(self.base, ours, theirs)
        self.assertEqual([], result.conflicts)
        self.assertIn("### 2026-10-11 — ours", result.text)
        self.assertIn("### 2026-10-11 — theirs", result.text)
        self.assertIn("### 2026-10-09 — c", result.text)
        self.assertNotIn("### 2026-10-08 — b", result.text)
        self.assertEqual([block("2026-10-08", "b"), block("2026-10-07", "a")], result.archived)
        self.assertTrue(result.text.endswith("### Auto-Reset Behaviour\nrules\n"))

    def test_block_archived_on_one_side_does_not_come_back(self):
        ours = session("x", block("2026-10-11", "new"), *self.old[:2])
        result = mrg.merge_current_session(self.base, ours, self.base)
        self.assertNotIn("2026-10-07", result.text)
        self.assertEqual([], result.archived)

    def test_header_changed_on_one_side_is_taken(self):
        theirs = session("theirs status", *self.old)
        result = mrg.merge_current_session(self.base, self.base, theirs)
        self.assertIn("theirs status", result.text)
        self.assertEqual([], result.conflicts)

    def test_header_changed_on_both_sides_is_a_question_until_chosen(self):
        ours, theirs = session("mine", *self.old), session("yours", *self.old)
        self.assertEqual(["header"], mrg.merge_current_session(self.base, ours, theirs).conflicts)
        chosen = mrg.merge_current_session(self.base, ours, theirs, choices={"header": "theirs"})
        self.assertEqual([], chosen.conflicts)
        self.assertIn("yours", chosen.text)

    def test_session_units_expose_the_conflicting_parts(self):
        ours, theirs = session("mine", *self.old), session("yours", *self.old)
        unit = mrg.session_units("main/current-session.md", self.base, ours, theirs, ["header"])[0]
        self.assertIn("mine", unit.ours)
        self.assertIn("yours", unit.theirs)


class Archive(unittest.TestCase):
    def test_prepend_goes_above_the_first_block(self):
        archive = "# Session Archive\n\n_intro_\n\n### 2026-10-01 — old\nx\n"
        out = mrg.prepend_to_archive(archive, [block("2026-10-07", "a")])
        self.assertLess(out.index("2026-10-07"), out.index("2026-10-01"))
        self.assertTrue(out.startswith("# Session Archive\n\n_intro_\n\n### 2026-10-07"))



GENERAL = "# General Design Taste\n\n## Colour\n\n- **Flat**: {flat}\n- **Contrast**: AA always.\n\n## Typography\n\n- **Tabular**: figures line up.\n"


class SplitUnits(unittest.TestCase):
    def test_every_kind_is_lossless(self):
        samples = {
            "bullet": GENERAL.format(flat="one") + "- **Wrapped**: first line\n  continues here\n",
            "entry": "# Palettes\n\n## Ranked\n\n| 1 | a | 6.0 |\n\n## a-one\nscores\n\n## b-two\nmore\n",
            "row": "| Job | Company | Status |\n|-----|---------|--------|\n| Dev | Acme | applied |\n| Dev | Beta | found |\n",
            "section": "# T\n\nintro\n\n## A\nx\n\n### A.1\ny\n",
        }
        for kind, text in samples.items():
            self.assertEqual(text, "".join(t for _, t in mrg.split_units(kind, text)), kind)

    def test_bullet_keys_are_bold_titles_with_continuations(self):
        units = [u for u in mrg.split_units("bullet", "- **Wrapped**: a\n  b\n- plain one\n") if u[0]]
        self.assertEqual([("Wrapped", "- **Wrapped**: a\n  b\n"), ("- plain one", "- plain one\n")], units)

    def test_duplicate_keys_are_made_unique(self):
        keys = [k for k, _ in mrg.split_units("section", "## A\nx\n## A\ny\n") if k]
        self.assertEqual(["## A", "## A #2"], keys)

    def test_unit_kind_routing(self):
        self.assertEqual("entry", mrg.unit_kind("design/palettes.md"))
        self.assertEqual("bullet", mrg.unit_kind("design/mobile.md"))
        self.assertEqual("bullet", mrg.unit_kind("context/20-working-preferences.md"))
        self.assertEqual("row", mrg.unit_kind("career/tracker.md"))
        self.assertEqual("section", mrg.unit_kind("project-management/x/General.md"))
        self.assertEqual("section", mrg.unit_kind("design/journal.md"))


class ThreeWay(unittest.TestCase):
    def test_one_side_changes_merge_silently(self):
        base = GENERAL.format(flat="one")
        ours = base.replace("AA always", "AAA where possible")
        theirs = base.replace("- **Tabular**: figures line up.\n", "- **Tabular**: figures line up.\n- **Floor**: 12px.\n")
        result = mrg.three_way("design/general.md", base, ours, theirs)
        self.assertEqual([], result.conflicts)
        self.assertIn("AAA where possible", result.text)
        self.assertIn("- **Floor**: 12px.", result.text)
        self.assertLess(result.text.index("Tabular"), result.text.index("Floor"))

    def test_same_rule_changed_both_sides_is_one_conflict(self):
        base, ours, theirs = (GENERAL.format(flat=v) for v in ("one", "two", "three"))
        result = mrg.three_way("design/general.md", base, ours, theirs)
        self.assertIsNone(result.text)
        self.assertEqual(["Flat"], [u.key for u in result.conflicts])
        self.assertIn("two", result.conflicts[0].ours)
        self.assertIn("three", result.conflicts[0].theirs)

    def test_choices_resolve_conflicts(self):
        base, ours, theirs = (GENERAL.format(flat=v) for v in ("one", "two", "three"))
        for choice, expect in (("ours", "two"), ("theirs", "three"), ("edit:- **Flat**: four\n", "four")):
            text = mrg.three_way("design/general.md", base, ours, theirs, {"Flat": choice}).text
            self.assertIn(expect, text)
        both = mrg.three_way("design/general.md", base, ours, theirs, {"Flat": "both"}).text
        self.assertIn("two", both)
        self.assertIn("three", both)
        default = mrg.three_way("design/general.md", base, ours, theirs, {"*": "theirs"}).text
        self.assertIn("three", default)

    def test_deleted_one_side_unchanged_other_is_deleted(self):
        base = GENERAL.format(flat="one")
        ours = base.replace("- **Contrast**: AA always.\n", "")
        result = mrg.three_way("design/general.md", base, ours, base)
        self.assertNotIn("Contrast", result.text)

    def test_deleted_one_side_edited_other_is_a_conflict(self):
        base = GENERAL.format(flat="one")
        ours = base.replace("- **Contrast**: AA always.\n", "")
        theirs = base.replace("AA always", "AAA")
        self.assertEqual(["Contrast"], [u.key for u in mrg.three_way("design/general.md", base, ours, theirs).conflicts])

    def test_structure_changed_both_sides_is_a_whole_file_question(self):
        base = GENERAL.format(flat="one")
        ours = base.replace("## Typography", "## Type")
        theirs = base.replace("## Typography", "## Fonts")
        result = mrg.three_way("design/general.md", base, ours, theirs)
        self.assertEqual(["(structure)"], [u.key for u in result.conflicts])
        self.assertIn("## Fonts", mrg.three_way("design/general.md", base, ours, theirs, {"(structure)": "theirs"}).text)

    def test_ranked_tables_never_ask_and_flag_a_recompute(self):
        base = "# P\n\n## Ranked\n\n| 1 | a | 6.0 |\n\n## a\nx\n"
        ours = base.replace("6.0", "6.5")
        theirs = base.replace("6.0", "7.0")
        result = mrg.three_way("design/palettes.md", base, ours, theirs)
        self.assertEqual([], result.conflicts)
        self.assertEqual(["recompute ranked tables"], result.notes)

    def test_tracker_rows_merge_per_job(self):
        head = "| Job | Company | Status |\n|-----|---------|--------|\n"
        base = head + "| Dev | Acme | found |\n| Dev | Beta | found |\n"
        ours = base.replace("Acme | found", "Acme | applied")
        theirs = base.replace("Beta | found", "Beta | screening")
        text = mrg.three_way("career/tracker.md", base, ours, theirs).text
        self.assertIn("Acme | applied", text)
        self.assertIn("Beta | screening", text)


class SortLogSectionsSafety(unittest.TestCase):
    """Final review C2: the tidy must never drop real lines or move entries."""

    def test_no_duplicate_headings_means_no_change(self):
        text = "# T\n\n## 2026-04-16\n- late entry\n\n## 2026-04-20\n- a\n\n\n## 2026-04-17\n\n- b\n"
        self.assertEqual(text, mrg.sort_log_sections(text))

    def test_repeated_lines_inside_one_section_are_kept(self):
        text = ("# A\n\n### 2026-10-05 — x\n**Lessons**: one\n```\ncode\n```\n**Lessons**: one\n```\nmore\n```\n"
                "\n### 2026-10-05 — x\n- new from b\n")
        out = mrg.sort_log_sections(text, level=3)
        self.assertEqual(2, out.count("**Lessons**: one"))
        self.assertEqual(4, out.count("```"))
        self.assertIn("- new from b", out)
        self.assertEqual(1, out.count("### 2026-10-05 — x"))

    def test_headings_inside_comments_and_fences_are_not_sections(self):
        text = ("# Design Journal\n\n<!-- Entry shape:\n\n```\n## YYYY-MM-DD — {project}\n**Shown**: A\n```\n-->\n\n"
                "## 2026-10-10 — cms / sign-in\n**Picked**: C\n")
        self.assertEqual(text, mrg.sort_log_sections(text))

    def test_folded_copy_skips_only_lines_already_present(self):
        text = "# T\n\n## 2026-10-11\n- a\n- shared\n\n## 2026-10-10\n- old\n\n## 2026-10-11\n- shared\n- b\n"
        out = mrg.sort_log_sections(text)
        self.assertEqual(1, out.count("## 2026-10-11"))
        self.assertEqual(1, out.count("- shared"))
        self.assertLess(out.index("- b"), out.index("## 2026-10-10"))


class NonMarkdownFiles(unittest.TestCase):
    """Final review M5: code and yaml merge as whole files, never by comment lines."""

    def test_python_changed_on_both_sides_is_a_whole_file_question(self):
        base = "# one\nx = 1\n# two\ny = 2\n"
        ours, theirs = base.replace("x = 1", "x = 10"), base.replace("y = 2", "y = 20")
        result = mrg.three_way("mcp-spike/tool.py", base, ours, theirs)
        self.assertEqual(["(file)"], [u.key for u in result.conflicts])

    def test_python_changed_on_one_side_takes_that_side(self):
        base = "# one\nx = 1\n"
        self.assertEqual("# one\nx = 2\n", mrg.three_way("a.py", base, base.replace("1", "2"), base).text)


class RenamedUnits(unittest.TestCase):
    """Rehearsal finding: a rule renamed differently on both sides must be one question, not two rules."""

    BASE = "## Colour\n\n- **Flat**: one.\n- **No emojis**: icons only.\n- **Contrast**: AA.\n"

    def test_both_sides_rename_the_same_rule_is_one_question(self):
        ours = self.BASE.replace("**No emojis**", "**No emojis (A)**")
        theirs = self.BASE.replace("**No emojis**", "**No emojis (B)**")
        result = mrg.three_way("design/general.md", self.BASE, ours, theirs)
        self.assertEqual(["No emojis"], [u.key for u in result.conflicts])
        self.assertIn("(A)", result.conflicts[0].ours)
        self.assertIn("(B)", result.conflicts[0].theirs)

    def test_choice_keeps_one_version_in_place(self):
        ours = self.BASE.replace("**No emojis**", "**No emojis (A)**")
        theirs = self.BASE.replace("**No emojis**", "**No emojis (B)**")
        text = mrg.three_way("design/general.md", self.BASE, ours, theirs, {"No emojis": "theirs"}).text
        self.assertEqual(self.BASE.replace("**No emojis**", "**No emojis (B)**"), text)

    def test_rename_on_one_side_only_is_taken_silently(self):
        ours = self.BASE.replace("**No emojis**", "**No emojis (A)**")
        theirs = self.BASE.replace("AA.", "AAA.")
        text = mrg.three_way("design/general.md", self.BASE, ours, theirs).text
        self.assertIn("**No emojis (A)**", text)
        self.assertIn("AAA.", text)
        self.assertEqual(1, text.count("No emojis"))

if __name__ == "__main__":
    unittest.main()
