"""Tests for mcp-spike/brief.py — everything session-briefing gathers, in one call. Stdlib + git."""

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-spike"))

import brief  # noqa: E402
import ram  # noqa: E402

TODAY = date(2026, 10, 19)
NOW = datetime(2026, 10, 19, 8, 31)
GIT_ENV = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def git(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, env=GIT_ENV, capture_output=True, text=True, check=True).stdout


TRACKER = """# Job Tracker

| Job | Company | Location (tier) | Fit | Status | Last update | Next action | File |
|-----|---------|-----------------|-----|--------|-------------|-------------|------|
| Dev | Alpha | KL (1) | Strong | screening | 2026-10-10 | Await reply; follow up 2026-10-24 | [f](x) |
| Dev | Beta | KL (1) | Strong | applied | 2026-10-05 | Follow up 2026-10-16 if no reply | [f](x) |
| Dev | Gamma | KL (1) | Strong | ready | 2026-10-04 | Submit the application yourself | [f](x) |
| Dev | Delta | KL (1) | Strong | closed | 2026-10-04 | Follow up 2026-10-01 | [f](x) |
"""

TIMELINE = """# Career Timeline

## 2026-10-04
- Open: an old question that was settled

## 2026-10-10
- did things
- Open: is Acme a fit
- Open: Globex — withdraw or not
"""


class Period(unittest.TestCase):
    def test_boundaries(self):
        cases = {5: "morning", 11: "morning", 12: "afternoon", 16: "afternoon", 17: "evening",
                 20: "evening", 21: "late night", 2: "late night"}
        for hour, expected in cases.items():
            self.assertEqual(expected, brief.period(datetime(2026, 10, 19, hour, 0)), hour)


class Career(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def test_no_career_folder_is_none(self):
        self.assertIsNone(brief.career(self.root, TODAY))

    def test_due_follow_up_and_latest_open_questions_fire_the_flag(self):
        write(self.root, "career/tracker.md", TRACKER)
        write(self.root, "career/timeline.md", TIMELINE)
        c = brief.career(self.root, TODAY)
        self.assertTrue(c["fire"])
        self.assertEqual(1, c["ready"])
        self.assertEqual(2, c["awaiting"])
        self.assertEqual([{"company": "Beta", "date": "2026-10-16", "action": "Follow up 2026-10-16 if no reply"}],
                         c["due"])
        self.assertEqual(["is Acme a fit", "Globex — withdraw or not"], c["open"])

    def test_short_row_does_not_crash(self):
        write(self.root, "career/tracker.md", TRACKER + "| Dev | Epsilon |\n")
        self.assertEqual(1, brief.career(self.root, TODAY)["ready"])

    def test_ready_alone_does_not_fire(self):
        write(self.root, "career/tracker.md", "\n".join(TRACKER.splitlines()[:4] + [TRACKER.splitlines()[6]]) + "\n")
        c = brief.career(self.root, TODAY)
        self.assertEqual(1, c["ready"])
        self.assertFalse(c["fire"])

    def test_missing_timeline_still_fires_on_a_due_follow_up(self):
        write(self.root, "career/tracker.md", TRACKER)
        c = brief.career(self.root, TODAY)
        self.assertTrue(c["fire"])
        self.assertEqual([], c["open"])


class Learning(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        table = ("| Concept | Module | Confidence | Last reviewed | Note |\n|---|---|---|---|---|\n"
                 "| Ownership | 1 | shaky | 2026-10-01 | |\n| Borrowing | 1 | shaky | 2026-10-15 | |\n"
                 "| Traits | 2 | solid | 2026-09-01 | |\n")
        for slug, status in (("rust", "active"), ("go", "paused"), ("_template", "active")):
            write(self.root, f"learning/{slug}/General.md", f"# {slug}\n\n**Status**: {status}\n")
            write(self.root, f"learning/{slug}/Progress.md", f"# Progress\n\n{table}")

    def test_flags_only_active_topics_with_stale_shaky_concepts(self):
        self.assertEqual([{"topic": "rust", "shaky": 1, "oldest_days": 18}], brief.learning(self.root, TODAY))

    def test_lowercase_template_file_names_are_read(self):
        for name in ("General.md", "Progress.md"):
            src = self.root / "learning/rust" / name
            src.rename(src.with_name(name.lower()))
        self.assertEqual("rust", brief.learning(self.root, TODAY)[0]["topic"])


class Repos(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.base = Path(self._tmp.name).resolve()
        self.repo = self.base / "cms"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "feature/rebuild")
        write(self.repo, "a.txt", "a\n")
        git(self.repo, "add", "a.txt")
        git(self.repo, "commit", "-q", "-m", "first commit")

    def test_live_state_of_a_listed_repo(self):
        write(self.repo, "dirty.txt", "x\n")
        state = brief.repo_state(str(self.repo), "feature/rebuild")
        self.assertTrue(state["exists"])
        self.assertEqual("feature/rebuild", state["branch"])
        self.assertTrue(state["branch_matches"])
        self.assertEqual(1, state["dirty"])
        self.assertTrue(state["head"].endswith("first commit"))

    def test_branch_mismatch_is_flagged(self):
        state = brief.repo_state(str(self.repo), "feature/other")
        self.assertFalse(state["branch_matches"])

    def test_missing_path(self):
        state = brief.repo_state(str(self.base / "gone"), "main")
        self.assertFalse(state["exists"])

    def test_repos_from_ram_plus_the_working_directory(self):
        other = self.base / "other"
        (other / "sub").mkdir(parents=True)
        git(other, "init", "-q", "-b", "main")
        text = ("## Session RAM Status\n**Focus**: x\n**Repos**:\n"
                f"- `{self.repo}` · feature/rebuild\n\n## Session Recap (For AI Restart)\n")
        rows = brief.repos(text, cwd=other / "sub")
        self.assertEqual([str(self.repo), str(other)], [r["path"] for r in rows])
        self.assertEqual([True, None], [r["branch_matches"] for r in rows])

    def test_working_directory_already_listed_is_not_repeated(self):
        text = f"## Session RAM Status\n**Repos**:\n- `{self.repo}` · feature/rebuild\n"
        self.assertEqual(1, len(brief.repos(text, cwd=self.repo)))


class Gather(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        write(self.root, "device/id.md", "id: id-a\nname: laptop-a\n")
        write(self.root, "main/ram/laptop-b.md", ram.render_header("laptop-b", "id-b", "2026-10-18 21:00", "side project"))

    def test_creates_own_ram_and_reports_everything_without_sync(self):
        out = brief.gather(self.root, cwd=self.root, now=NOW, sync=False)
        self.assertTrue((self.root / "main/ram/laptop-a.md").is_file())
        self.assertEqual({"status": "skipped"}, out["sync"])
        self.assertEqual("morning", out["time"]["period"])
        self.assertEqual("main/ram/laptop-a.md", out["ram"]["path"])
        self.assertTrue(out["ram"]["check"]["ok"])
        self.assertEqual(["laptop-b"], [o["device"] for o in out["others"]])
        self.assertIsNone(out["career"])
        self.assertEqual([], out["learning"])

    def test_sync_not_set_up_is_reported_not_attempted(self):
        out = brief.gather(self.root, cwd=self.root, now=NOW, sync=True)
        self.assertEqual({"status": "not-set-up"}, out["sync"])

    def test_ram_focus_and_open_loops_are_returned(self):
        ram.ensure(self.root)
        path = self.root / "main/ram/laptop-a.md"
        path.write_text(path.read_text().replace("**Focus**: —", "**Focus**: rebuild")
                        .replace("**Open loops**:\n", "**Open loops**:\n- follow-up email\n"))
        out = brief.gather(self.root, cwd=self.root, now=NOW, sync=False)
        self.assertEqual("rebuild", out["ram"]["focus"])
        self.assertEqual(["follow-up email"], out["ram"]["open_loops"])


if __name__ == "__main__":
    unittest.main()
