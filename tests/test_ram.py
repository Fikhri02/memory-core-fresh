"""Tests for mcp-spike/ram.py — device-based session RAM. Stdlib only."""

import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-spike"))

import ram  # noqa: E402

NOW = datetime(2026, 10, 10, 19, 20)


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def identity(root: Path, name: str = "laptop-a", device_id: str = "id-a") -> None:
    write(root, "device/id.md", f"# Device identity — never synced\n\nid: {device_id}\nname: {name}\nregistered: 2026-10-10\n")


def block(date: str, title: str) -> str:
    return f"### {date} — {title}\n\n- {title}\n\n"


BODY = ("## Session RAM Status\n**Focus**: x\n\n## Session Recap (For AI Restart)\n\n"
        + block("2026-10-09", "c") + block("2026-10-08", "b") + block("2026-10-07", "a")
        + "### Auto-Reset Behaviour\nrules\n")


class Lookup(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_registered_laptop_uses_its_name(self):
        identity(self.root)
        self.assertEqual("laptop-a", ram.device_name(self.root))
        self.assertEqual("main/ram/laptop-a.md", ram.ram_rel(self.root))

    def test_no_identity_is_unregistered(self):
        self.assertEqual("unregistered", ram.device_name(self.root))
        self.assertEqual("main/ram/unregistered.md", ram.ram_rel(self.root))

    def test_owner_ignores_readme_and_other_paths(self):
        self.assertEqual("laptop-b", ram.owner("main/ram/laptop-b.md"))
        self.assertIsNone(ram.owner("main/ram/README.md"))
        self.assertIsNone(ram.owner("main/current-session.md"))
        self.assertIsNone(ram.owner("main/ram/sub/x.md"))

    def test_foreign_changes_flags_only_other_laptops(self):
        paths = ["main/ram/laptop-a.md", "main/ram/laptop-b.md", "design/general.md", "main/ram/README.md"]
        self.assertEqual(["main/ram/laptop-b.md"], ram.foreign_changes(paths, "laptop-a"))

    def test_registered_laptop_cannot_write_unregistered(self):
        self.assertEqual(["main/ram/unregistered.md"], ram.foreign_changes(["main/ram/unregistered.md"], "laptop-a"))
        self.assertEqual([], ram.foreign_changes(["main/ram/unregistered.md"], "unregistered"))

    def test_conflict_side(self):
        self.assertEqual("ours", ram.conflict_side("main/ram/laptop-a.md", "laptop-a"))
        self.assertEqual("theirs", ram.conflict_side("main/ram/laptop-b.md", "laptop-a"))
        self.assertIsNone(ram.conflict_side("main/ram/unregistered.md", "laptop-a"))
        self.assertIsNone(ram.conflict_side("design/general.md", "laptop-a"))


class Header(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        identity(self.root)

    def test_render_and_read_round_trip(self):
        text = ram.render_header("laptop-a", "id-a", "2026-10-10 19:20", "Design research")
        self.assertEqual("# Session RAM — laptop-a\n"
                         "**Device**: laptop-a · `id-a` · **Last activity**: 2026-10-10 19:20\n"
                         "**Last session**: Design research\n", text)
        self.assertEqual({"device": "laptop-a", "id": "id-a", "last_activity": "2026-10-10 19:20",
                          "last_session": "Design research"}, ram.read_header(text))

    def test_ensure_creates_file_with_header(self):
        path = ram.ensure(self.root)
        self.assertEqual(self.root / "main/ram/laptop-a.md", path)
        self.assertIsNotNone(ram.read_header(path.read_text()))
        self.assertIn("## Session RAM Status", path.read_text())

    def test_stamp_updates_header_and_keeps_body(self):
        write(self.root, "main/ram/laptop-a.md", ram.render_header("laptop-a", "id-a", "old", "old") + "\n" + BODY)
        ram.stamp(self.root, "New work", now=NOW)
        text = (self.root / "main/ram/laptop-a.md").read_text()
        self.assertEqual("2026-10-10 19:20", ram.read_header(text)["last_activity"])
        self.assertEqual("New work", ram.read_header(text)["last_session"])
        self.assertTrue(text.endswith(BODY))
        self.assertEqual(1, text.count("# Session RAM —"))

    def test_stamp_adds_header_to_headerless_file(self):
        write(self.root, "main/ram/laptop-a.md", BODY)
        ram.stamp(self.root, "First", now=NOW)
        text = (self.root / "main/ram/laptop-a.md").read_text()
        self.assertEqual("First", ram.read_header(text)["last_session"])
        self.assertTrue(text.endswith(BODY))


class Others(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        identity(self.root)

    def test_lists_other_laptops_newest_first_skipping_self_retired_unregistered(self):
        write(self.root, "main/ram/laptop-a.md", ram.render_header("laptop-a", "id-a", "2026-10-10 20:00", "me"))
        write(self.root, "main/ram/laptop-b.md", ram.render_header("laptop-b", "id-b", "2026-10-09 10:00", "older"))
        write(self.root, "main/ram/laptop-c.md", ram.render_header("laptop-c", "id-c", "2026-10-10 18:00", "newer"))
        write(self.root, "main/ram/old-test.md", ram.render_header("old-test", "id-t", "2026-10-10 21:00", "gone"))
        write(self.root, "main/ram/unregistered.md", ram.render_header("unregistered", "", "2026-10-10 22:00", "x"))
        write(self.root, "devices/id-t.md", "# old-test\n\n**Id**: id-t · **Status**: retired\n")
        rows = ram.others(self.root)
        self.assertEqual(["laptop-c", "laptop-b"], [r["device"] for r in rows])
        self.assertEqual("newer", rows[0]["last_session"])

    def test_others_lists_headerless_file(self):
        write(self.root, "main/ram/laptop-b.md", BODY)
        self.assertEqual([{"device": "laptop-b", "last_activity": "?", "last_session": "(no header)"}],
                         ram.others(self.root))


class Trim(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        identity(self.root)
        header = ram.render_header("laptop-a", "id-a", "x", "x") + "\n"
        body = BODY.replace("## Session Recap (For AI Restart)\n\n",
                            "## Session Recap (For AI Restart)\n\n" + block("2026-10-10", "d"), 1)
        write(self.root, "main/ram/laptop-a.md", header + body)
        write(self.root, "main/session-archive.md", "# Session Archive\n\n_older_\n\n" + block("2026-10-01", "old"))

    def test_keeps_three_newest_and_archives_rest_with_device_tag(self):
        moved = ram.trim(self.root)
        self.assertEqual(["### 2026-10-07 · laptop-a — a"], moved)
        current = (self.root / "main/ram/laptop-a.md").read_text()
        archive = (self.root / "main/session-archive.md").read_text()
        self.assertIn("### 2026-10-10 — d", current)
        self.assertNotIn("### 2026-10-07", current)
        self.assertIn("### Auto-Reset Behaviour", current)
        self.assertLess(archive.index("### 2026-10-07 · laptop-a — a"), archive.index("### 2026-10-01 — old"))
        self.assertIn("- a\n", archive)

    def test_trim_twice_archives_once(self):
        ram.trim(self.root)
        self.assertEqual([], ram.trim(self.root))
        self.assertEqual(1, (self.root / "main/session-archive.md").read_text().count("— a\n"))

    def test_trailing_level_two_section_stays_in_ram(self):
        path = self.root / "main/ram/laptop-a.md"
        text = path.read_text().replace("### Auto-Reset Behaviour\nrules\n", "## Quick Context for Next Session\n- keep me\n")
        path.write_text(text)
        ram.trim(self.root)
        current = path.read_text()
        archive = (self.root / "main/session-archive.md").read_text()
        self.assertIn("## Quick Context for Next Session\n- keep me", current)
        self.assertNotIn("keep me", archive)

    def test_tag_heading_variants(self):
        self.assertEqual("### 2026-10-05 → 10-06 · laptop-a — t\n\nx\n",
                         ram.tag_heading("### 2026-10-05 → 10-06 — t\n\nx\n", "laptop-a"))
        self.assertEqual("### 2026-10-05 · laptop-a\n", ram.tag_heading("### 2026-10-05\n", "laptop-a"))
        already = "### 2026-10-05 · laptop-a — t\n"
        self.assertEqual(already, ram.tag_heading(already, "laptop-a"))

    def test_prepend_goes_above_the_first_block(self):
        out = ram.prepend_to_archive("# Archive\n\n_x_\n\n### 2026-10-01 — z\n\n- z\n", ["### 2026-10-07 — a\n\n- a\n"])
        self.assertTrue(out.startswith("# Archive\n\n_x_\n\n### 2026-10-07 — a\n\n- a\n\n### 2026-10-01 — z"))


def status(*lines: str) -> str:
    return "## Session RAM Status\n" + "".join(l + "\n" for l in lines) + "\n## Session Recap (For AI Restart)\n\n"


class Status(unittest.TestCase):
    """The Status section has a fixed shape — Focus, Repos, Open loops — and trim moves anything else out."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        identity(self.root)
        write(self.root, "main/session-archive.md", "# Session Archive\n\n_older_\n\n" + block("2026-10-01", "old"))

    def ram_file(self, body: str) -> Path:
        header = ram.render_header("laptop-a", "id-a", "x", "x") + "\n"
        return write(self.root, "main/ram/laptop-a.md", header + body + block("2026-10-09", "c"))

    def test_ensure_writes_the_new_status_shape(self):
        text = ram.ensure(self.root).read_text()
        self.assertIn("## Session RAM Status\n**Focus**: —\n**Repos**:\n**Open loops**:\n", text)
        self.assertTrue(ram.check(self.root)["ok"])

    def test_trim_moves_unknown_status_keys_to_the_archive_verbatim(self):
        path = self.ram_file(status("**Current Session**: old summary", "**Focus**: rebuild",
                                    "**Atlas (2026-10-10)**: worktree `x` on `y`", "second line of atlas",
                                    "**Open loops**:", "- follow up"))
        moved = ram.trim(self.root, now=NOW)
        self.assertEqual(["### 2026-10-10 · laptop-a — status moved out of RAM"], moved)
        current = path.read_text()
        self.assertIn("**Focus**: rebuild\n**Open loops**:\n- follow up\n", current)
        self.assertNotIn("Atlas", current)
        self.assertNotIn("Current Session", current)
        self.assertIn("### 2026-10-09 — c", current)
        archive = (self.root / "main/session-archive.md").read_text()
        self.assertIn("**Current Session**: old summary\n**Atlas (2026-10-10)**: worktree `x` on `y`\n"
                      "second line of atlas\n", archive)
        self.assertLess(archive.index("status moved out of RAM"), archive.index("### 2026-10-01 — old"))

    def test_loose_recap_paragraphs_move_out_and_dated_blocks_stay(self):
        body = ("## Session RAM Status\n**Focus**: x\n\n## Session Recap (For AI Restart)\n"
                "*Quick summary when the AI loads after a close/reopen*\n\n"
                "**2026-10-11 — Atlas 1c**: old style recap\nsecond line\n\n"
                "**2026-10-10 — Device RAM**: another\n\n")
        path = self.ram_file(body)
        self.assertIn("2 loose recap paragraph(s) outside dated ### blocks", " | ".join(ram.check(self.root)["issues"]))
        moved = ram.trim(self.root, now=NOW)
        self.assertEqual(["### 2026-10-10 · laptop-a — status moved out of RAM"], moved)
        current = path.read_text()
        self.assertIn("## Session Recap (For AI Restart)\n*Quick summary when the AI loads after a close/reopen*\n\n"
                      "### 2026-10-09 — c", current)
        self.assertNotIn("Atlas 1c", current)
        archive = (self.root / "main/session-archive.md").read_text()
        self.assertIn("**2026-10-11 — Atlas 1c**: old style recap\nsecond line\n\n**2026-10-10 — Device RAM**: another\n",
                      archive)
        self.assertTrue(ram.check(self.root)["ok"])

    def test_trim_leaves_a_clean_status_alone(self):
        self.ram_file(status("**Focus**: rebuild", "**Repos**:", "- `~/x` · main", "**Open loops**:", "- one"))
        self.assertEqual([], ram.trim(self.root, now=NOW))

    def test_check_flags_unknown_keys_overlong_focus_and_too_many_loops(self):
        self.ram_file(status("**Focus**: a", "still focus", "**Old**: y", "**Open loops**:",
                             *[f"- loop {i}" for i in range(7)]))
        result = ram.check(self.root)
        self.assertFalse(result["ok"])
        joined = " | ".join(result["issues"])
        self.assertIn("Old", joined)
        self.assertIn("Focus", joined)
        self.assertIn("Open loops has 7 items (max 5)", joined)

    def test_check_flags_too_many_session_blocks(self):
        self.ram_file(status("**Focus**: a") + block("2026-10-08", "b") + block("2026-10-07", "a")
                      + block("2026-10-06", "z"))
        self.assertIn("4 session blocks (max 3)", " | ".join(ram.check(self.root)["issues"]))

    def test_repos_reads_path_and_branch(self):
        text = status("**Focus**: a", "**Repos**:", "- `~/projects/cms` · feature/rebuild",
                      "- /tmp/other · main", "- `~/no-branch`")
        self.assertEqual([{"path": "~/projects/cms", "branch": "feature/rebuild"},
                          {"path": "/tmp/other", "branch": "main"},
                          {"path": "~/no-branch", "branch": None}], ram.repos(text))


class Pointer(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        identity(self.root)

    def test_clean_pointer_is_left_alone(self):
        write(self.root, "main/current-session.md", ram.POINTER_TEXT)
        self.assertIsNone(ram.absorb_pointer(self.root))

    def test_stray_content_moves_into_own_ram(self):
        write(self.root, "main/current-session.md", ram.POINTER_TEXT + "\n### 2026-10-11 — stray\n\n- s\n")
        note = ram.absorb_pointer(self.root, now=NOW)
        self.assertIn("main/ram/laptop-a.md", note)
        self.assertEqual(ram.POINTER_TEXT, (self.root / "main/current-session.md").read_text())
        own = (self.root / "main/ram/laptop-a.md").read_text()
        self.assertIn("### 2026-10-11 — stray", own)
        self.assertIsNotNone(ram.read_header(own))

    def test_missing_pointer_is_fine(self):
        self.assertIsNone(ram.absorb_pointer(self.root))


if __name__ == "__main__":
    unittest.main()
