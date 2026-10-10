"""End-to-end sync between two simulated laptops sharing one bare repo. Needs git. Stdlib only."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp-spike"))

import sync_device as dev  # noqa: E402
import sync_git as sg  # noqa: E402

ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}
def NO_GH(remote, account):
    return None


SESSION = ("# RAM\n\n## Session RAM Status\n**Current Session**: x\n\n## Session Recap (For AI Restart)\n\n"
           "### 2026-10-09 — c\n\n- c\n\n### 2026-10-08 — b\n\n- b\n\n### 2026-10-07 — a\n\n- a\n\n"
           "### Auto-Reset Behaviour\nrules\n")


def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def append(root: Path, rel: str, text: str) -> None:
    write(root, rel, (root / rel).read_text(encoding="utf-8") + text)


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def memory(root: Path) -> None:
    write(root, "main/current-session.md", SESSION)
    write(root, "main/session-archive.md", "# Session Archive\n\n_older_\n\n### 2026-10-01 — old\n\n- old\n")
    write(root, "main/preferences.md", "# Preferences\n\n## Output\n\n- **Show**: render, do not describe.\n")
    write(root, "design/general.md", "# General\n\n## Colour\n\n- **Flat**: one.\n")
    write(root, "project-management/README.md", "# Projects\n")
    write(root, "project-management/_template/general.md", "# {project-name}\n")
    for slug in ("alpha", "beta"):
        write(root, f"project-management/{slug}/Timeline.md", f"# Timeline — {slug}\n\n## 2026-10-10\n- start\n")
    write(root, "ecosystem/README.md", "# Ecosystems\n")
    (root / "mcp-spike").mkdir(parents=True, exist_ok=True)
    for name in ("sync_device.py", "sync_guard.py", "sync_merge.py", "sync_git.py"):
        shutil.copy(ROOT / "mcp-spike" / name, root / "mcp-spike" / name)


class TwoLaptops(unittest.TestCase):
    def setUp(self):
        saved = dict(os.environ)
        os.environ.update(ENV)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        os.environ["MEMORY_CORE_CLAUDE_HOME"] = str(base / "home")
        self.bare = base / "ctx.git"
        run("git", "init", "-q", "--bare", "-b", "main", str(self.bare))
        self.a, self.b = base / "a", base / "b"
        memory(self.a)
        run("git", "init", "-q", "-b", "main", cwd=self.a)
        run("git", "add", "-A", cwd=self.a)
        run("git", "commit", "-q", "-m", "existing install", cwd=self.a)
        self.assertEqual("empty-remote", sg.cmd_setup(self.a, str(self.bare), "", "laptop-a", visibility_fn=NO_GH)["status"])
        self.assertEqual("pushed", sg.cmd_first_upload(self.a, ["alpha", "beta"], [])["status"])
        run("git", "clone", "-q", "--sparse", str(self.bare), str(self.b))
        joined = sg.cmd_join(self.b, "laptop-b", "", visibility_fn=NO_GH)
        self.assertEqual("pushed", joined["status"], joined)
        self.assertEqual("followed", sg.cmd_follow(self.b, "project-management", "alpha")["status"])

    def settle(self, root):
        result = sg.cmd_pull(root)
        self.assertIn(result["status"], ("up-to-date", "merged"), result)
        return sg.cmd_save(root, "save")

    def test_new_laptop_has_core_and_only_followed_projects(self):
        self.assertTrue((self.b / "design/general.md").is_file())
        self.assertTrue((self.b / "project-management/alpha/Timeline.md").is_file())
        self.assertFalse((self.b / "project-management/beta").exists())
        self.assertTrue((self.b / "project-management/_template/general.md").is_file())
        self.assertEqual("context", (self.b / ".memory-core/kind").read_text().strip())

    def test_timeline_entries_from_both_laptops_merge_without_questions(self):
        self.settle(self.a)
        append(self.a, "project-management/alpha/Timeline.md", "\n## 2026-10-11\n- from a\n")
        self.assertEqual("pushed", sg.cmd_save(self.a, "save project alpha")["status"])
        append(self.b, "project-management/alpha/Timeline.md", "\n## 2026-10-11\n- from b\n")
        self.assertEqual("rejected", sg.cmd_save(self.b, "save project alpha")["status"])
        self.assertEqual("merged", sg.cmd_pull(self.b)["status"])
        text = (self.b / "project-management/alpha/Timeline.md").read_text()
        self.assertEqual(1, text.count("## 2026-10-11"))
        self.assertIn("- from a", text)
        self.assertIn("- from b", text)
        self.assertEqual("pushed", sg.cmd_save(self.b, "save")["status"])

    def test_same_rule_edited_on_both_is_one_question_then_resolved(self):
        self.settle(self.a)
        write(self.a, "design/general.md", "# General\n\n## Colour\n\n- **Flat**: two.\n")
        sg.cmd_save(self.a, "save")
        write(self.b, "design/general.md", "# General\n\n## Colour\n\n- **Flat**: three.\n")
        self.assertEqual("rejected", sg.cmd_save(self.b, "save")["status"])
        pulled = sg.cmd_pull(self.b)
        self.assertEqual("needs-answers", pulled["status"])
        self.assertEqual([("design/general.md", "Flat")], [(u["path"], u["key"]) for u in pulled["units"]])
        self.assertEqual("needs-answers", sg.cmd_pull(self.b)["status"])
        resolved = sg.cmd_resolve(self.b, {"design/general.md": {"Flat": "theirs"}})
        self.assertEqual("merged", resolved["status"], resolved)
        self.assertIn("two", (self.b / "design/general.md").read_text())
        self.assertEqual("pushed", sg.cmd_save(self.b, "save")["status"])

    def test_session_blocks_from_both_laptops_combine_and_archive(self):
        self.settle(self.a)
        write(self.a, "main/current-session.md", SESSION.replace("### 2026-10-09", "### 2026-10-11 — from a\n\n- a\n\n### 2026-10-09", 1))
        sg.cmd_save(self.a, "save")
        write(self.b, "main/current-session.md", SESSION.replace("### 2026-10-09", "### 2026-10-11 — from b\n\n- b\n\n### 2026-10-09", 1))
        sg.cmd_save(self.b, "save")
        self.assertEqual("merged", sg.cmd_pull(self.b)["status"])
        current = (self.b / "main/current-session.md").read_text()
        archive = (self.b / "main/session-archive.md").read_text()
        self.assertIn("### 2026-10-11 — from a", current)
        self.assertIn("### 2026-10-11 — from b", current)
        self.assertIn("### 2026-10-08 — b", archive)
        self.assertNotIn("### 2026-10-08 — b", current)

    def test_pre_push_hook_blocks_any_other_remote(self):
        other = Path(self._tmp.name).resolve() / "other.git"
        run("git", "init", "-q", "--bare", "-b", "main", str(other))
        proc = run("git", "push", str(other), "HEAD:main", cwd=self.a)
        self.assertNotEqual(0, proc.returncode)
        self.assertIn("not this memory's sync remote", proc.stderr)

    def test_undo_restores_the_state_before_the_sync(self):
        self.settle(self.a)
        append(self.a, "project-management/alpha/Timeline.md", "\n## 2026-10-12\n- a only\n")
        sg.cmd_save(self.a, "save")
        write(self.b, "main/preferences.md", "# Preferences\n\n## Output\n\n- **Show**: b edit.\n")
        self.assertEqual("merged", sg.cmd_pull(self.b)["status"])
        self.assertIn("a only", (self.b / "project-management/alpha/Timeline.md").read_text())
        undone = sg.cmd_undo(self.b)
        self.assertEqual("restored", undone["status"])
        self.assertNotIn("a only", (self.b / "project-management/alpha/Timeline.md").read_text())
        self.assertIn("b edit", (self.b / "main/preferences.md").read_text())

    def test_unfollow_refuses_unsaved_changes_then_removes(self):
        append(self.b, "project-management/alpha/Timeline.md", "- unsaved\n")
        self.assertEqual("refused", sg.cmd_unfollow(self.b, "project-management", "alpha")["status"])
        run("git", "checkout", "--", "project-management/alpha/Timeline.md", cwd=self.b)
        self.assertEqual("unfollowed", sg.cmd_unfollow(self.b, "project-management", "alpha")["status"])
        self.assertFalse((self.b / "project-management/alpha").exists())

    def test_registry_has_one_file_per_device_and_both_laptops_agree(self):
        self.settle(self.a)
        self.settle(self.b)
        ids = {dev.ensure_identity(self.a)["id"], dev.ensure_identity(self.b)["id"]}
        self.assertEqual({f"{i}.md" for i in ids}, {p.name for p in (self.a / "devices").glob("*.md")})
        a_file = f"devices/{dev.ensure_identity(self.a)['id']}.md"
        self.assertEqual((self.a / a_file).read_text(), (self.b / a_file).read_text())

    def test_status_lists_available_and_devices(self):
        status = sg.cmd_status(self.b)
        self.assertEqual(["alpha", "beta"], status["available"]["project-management"])
        self.assertEqual(["alpha"], status["following"]["project-management"])
        self.assertEqual({"laptop-a", "laptop-b"}, {d["name"] for d in status["devices"]})

    def test_framework_remote_is_refused_at_setup(self):
        c = Path(self._tmp.name).resolve() / "c"
        memory(c)
        run("git", "init", "-q", "-b", "main", cwd=c)
        result = sg.cmd_setup(c, "git@github.com:Fikhri02/memory-core-fresh.git", "", "laptop-c",
                              visibility_fn=lambda r, a: "PRIVATE")
        self.assertEqual("refused", result["status"])
        self.assertEqual("", run("git", "remote", cwd=c).stdout.strip())



def show(bare: Path, rel: str) -> str:
    return run("git", "--git-dir", str(bare), "show", f"main:{rel}").stdout


def tree(bare: Path) -> str:
    return run("git", "--git-dir", str(bare), "ls-tree", "-r", "--name-only", "main").stdout


class FinalReviewFixes(TwoLaptops):
    """Regression tests for the final review's Critical and Important findings."""

    def conflict_on_flat(self):
        self.settle(self.a)
        write(self.a, "design/general.md", "# General\n\n## Colour\n\n- **Flat**: two.\n")
        sg.cmd_save(self.a, "save")
        write(self.b, "design/general.md", "# General\n\n## Colour\n\n- **Flat**: three.\n")
        sg.cmd_save(self.b, "save")
        self.assertEqual("needs-answers", sg.cmd_pull(self.b)["status"])

    def test_c1_nothing_saves_or_moves_while_questions_are_pending(self):
        self.conflict_on_flat()
        self.assertEqual("needs-answers", sg.cmd_save(self.b, "save memory")["status"])
        self.assertNotIn("<<<<<<<", show(self.bare, "design/general.md"))
        for result in (sg.cmd_follow(self.b, "project-management", "beta"),
                       sg.cmd_unfollow(self.b, "project-management", "alpha")):
            self.assertEqual("needs-answers", result["status"])
        self.assertEqual("merged", sg.cmd_resolve(self.b, {"design/general.md": {"Flat": "ours"}})["status"])
        self.assertIn("three", (self.b / "design/general.md").read_text())

    def test_c1_binary_conflict_is_a_whole_file_question(self):
        self.settle(self.a)
        (self.a / "design/logo.png").write_bytes(b"\x89PNG\x00\xffA")
        sg.cmd_save(self.a, "save")
        self.settle(self.b)
        self.settle(self.a)
        (self.a / "design/logo.png").write_bytes(b"\x89PNG\x00\xffAA")
        sg.cmd_save(self.a, "save")
        (self.b / "design/logo.png").write_bytes(b"\x89PNG\x00\xffBB")
        sg.cmd_save(self.b, "save")
        pulled = sg.cmd_pull(self.b)
        self.assertEqual("needs-answers", pulled["status"])
        self.assertEqual([("design/logo.png", "(binary)")], [(u["path"], u["key"]) for u in pulled["units"]])
        self.assertEqual("merged", sg.cmd_resolve(self.b, {"design/logo.png": {"(binary)": "theirs"}})["status"])
        self.assertEqual(b"\x89PNG\x00\xffAA", (self.b / "design/logo.png").read_bytes())

    def test_c2_untouched_log_on_one_side_is_never_rewritten(self):
        self.settle(self.a)
        odd = "# Timeline — alpha\n\n## 2026-10-12\n- later\n\n## 2026-10-10\n- start\n- start\n"
        write(self.a, "project-management/alpha/Timeline.md", odd)
        sg.cmd_save(self.a, "save")
        self.assertEqual("merged", sg.cmd_pull(self.b)["status"])
        self.assertEqual(odd, (self.b / "project-management/alpha/Timeline.md").read_text())

    def test_i2_new_core_folder_and_new_files_reach_the_other_laptop(self):
        self.settle(self.a)
        write(self.a, "learning/rust/topic.md", "# Rust\n")
        write(self.a, "scratchstuff/note.md", "not core\n")
        self.assertEqual("pushed", sg.cmd_save(self.a, "save learning rust")["status"])
        self.assertIn("learning/rust/topic.md", tree(self.bare))
        self.assertNotIn("scratchstuff/note.md", tree(self.bare))
        self.assertEqual("merged", sg.cmd_pull(self.b)["status"])
        self.assertTrue((self.b / "learning/rust/topic.md").is_file())

    def test_i3_project_folders_named_like_machine_dirs_still_sync(self):
        self.settle(self.a)
        write(self.a, "project-management/alpha/Features/Device/Development/pairing.md", "# Pairing\n")
        write(self.a, "project-management/alpha/outputs/report.md", "# Report\n")
        sg.cmd_save(self.a, "save project alpha")
        sg.cmd_pull(self.b)
        self.assertTrue((self.b / "project-management/alpha/Features/Device/Development/pairing.md").is_file())
        self.assertTrue((self.b / "project-management/alpha/outputs/report.md").is_file())

    def test_i3_unfollow_refuses_when_ignored_files_would_be_lost(self):
        write(self.b, "project-management/alpha/__pycache__/x.pyc", "bytecode")
        self.assertEqual("refused", sg.cmd_unfollow(self.b, "project-management", "alpha")["status"])

    def test_i5_undo_refuses_after_the_merge_was_uploaded(self):
        self.settle(self.a)
        append(self.a, "project-management/alpha/Timeline.md", "\n## 2026-10-12\n- a only\n")
        sg.cmd_save(self.a, "save")
        self.assertEqual("merged", sg.cmd_pull(self.b)["status"])
        self.assertEqual("pushed", sg.cmd_save(self.b, "save")["status"])
        result = sg.cmd_undo(self.b)
        self.assertEqual("refused", result["status"])
        self.assertIn("already uploaded", result["reason"])

    def test_i5_undo_refuses_with_unsaved_edits(self):
        self.settle(self.a)
        append(self.a, "project-management/alpha/Timeline.md", "\n## 2026-10-12\n- a only\n")
        sg.cmd_save(self.a, "save")
        sg.cmd_pull(self.b)
        write(self.b, "main/preferences.md", "# Preferences\n\n- unsaved\n")
        self.assertEqual("refused", sg.cmd_undo(self.b)["status"])
        self.assertIn("unsaved", (self.b / "main/preferences.md").read_text())

    def test_m3_a_merge_that_fails_without_conflicts_is_reported_failed(self):
        self.settle(self.a)
        append(self.a, "project-management/alpha/Timeline.md", "\n## 2026-10-12\n- a\n")
        sg.cmd_save(self.a, "save")
        real = sg.git

        def fake(root, *args, check=True):
            if args and args[0] == "merge" and "--abort" not in args:
                return subprocess.CompletedProcess(args, 1, "", "error: untracked working tree files would be overwritten")
            return real(root, *args, check=check)

        with unittest.mock.patch.object(sg, "git", side_effect=fake):
            result = sg.cmd_pull(self.b)
        self.assertEqual("failed", result["status"])
        self.assertIn("would be overwritten", result["reason"])


class FreshInstall(unittest.TestCase):
    """Setup-time findings: C3 (unticked staged items), I4 (interrupted setup), I6 (hooks)."""

    def setUp(self):
        saved = dict(os.environ)
        os.environ.update(ENV)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(saved)))
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        base = Path(self._tmp.name).resolve()
        os.environ["MEMORY_CORE_CLAUDE_HOME"] = str(base / "home")
        self.bare = base / "ctx.git"
        run("git", "init", "-q", "--bare", "-b", "main", str(self.bare))
        self.c = base / "c"
        memory(self.c)
        write(self.c, "project-management/gamma/General.md", "# Gamma — company project\n")
        write(self.c, "outputs/report.md", "# generated\n")
        run("git", "init", "-q", "-b", "feature/x", cwd=self.c)
        run("git", "add", "-A", cwd=self.c)
        run("git", "commit", "-q", "-m", "existing install", "--", "main", "design", "mcp-spike", "outputs",
            "project-management/README.md", "project-management/_template", cwd=self.c)

    def test_c3_unticked_staged_project_is_not_uploaded_and_stays_on_disk(self):
        sg.cmd_setup(self.c, str(self.bare), "", "laptop-c", visibility_fn=NO_GH)
        self.assertEqual("pushed", sg.cmd_first_upload(self.c, ["alpha"], [])["status"])
        listing = tree(self.bare)
        self.assertIn("project-management/alpha/Timeline.md", listing)
        self.assertNotIn("project-management/gamma", listing)
        self.assertNotIn("project-management/beta", listing)
        self.assertNotIn("outputs/report.md", listing)
        self.assertTrue((self.c / "project-management/gamma/General.md").is_file())
        self.assertTrue((self.c / "outputs/report.md").is_file())

    def test_rehearsal_untracking_keeps_a_file_staged_and_edited_differently(self):
        write(self.c, "outputs/report.md", "# staged version\n")
        run("git", "add", "outputs/report.md", cwd=self.c)
        write(self.c, "outputs/report.md", "# working copy\n")
        sg.cmd_setup(self.c, str(self.bare), "", "laptop-c", visibility_fn=NO_GH)
        self.assertEqual("pushed", sg.cmd_first_upload(self.c, ["alpha"], [])["status"])
        self.assertEqual("# working copy\n", (self.c / "outputs/report.md").read_text())
        self.assertNotIn("outputs/report.md", tree(self.bare))

    def test_i4_interrupted_setup_does_not_break_saves_and_can_resume(self):
        self.assertEqual("empty-remote", sg.cmd_setup(self.c, str(self.bare), "", "laptop-c", visibility_fn=NO_GH)["status"])
        self.assertEqual("setup-incomplete", sg.cmd_save(self.c, "save memory")["status"])
        self.assertEqual("setup-incomplete", sg.cmd_pull(self.c)["status"])
        self.assertEqual("empty-remote", sg.cmd_setup(self.c, str(self.bare), "", "laptop-c", visibility_fn=NO_GH)["status"])

    def test_i6_global_hooks_path_is_refused(self):
        run("git", "config", "core.hooksPath", str(Path(self._tmp.name) / "global-hooks"), cwd=self.c)
        result = sg.cmd_setup(self.c, str(self.bare), "", "laptop-c", visibility_fn=NO_GH)
        self.assertEqual("refused", result["status"])
        self.assertIn("core.hooksPath", result["reason"])

    def test_i6_existing_pre_push_hook_is_kept_and_chained(self):
        hook = self.c / ".git/hooks/pre-push"
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text("#!/bin/sh\necho mine >&2\nexit 0\n")
        hook.chmod(0o755)
        sg.cmd_setup(self.c, str(self.bare), "", "laptop-c", visibility_fn=NO_GH)
        self.assertIn("echo mine", (self.c / ".git/hooks/pre-push.local").read_text())
        self.assertIn("sync_guard.py", hook.read_text())
        sg.cmd_first_upload(self.c, ["alpha"], [])
        proc = run("git", "push", "origin", "HEAD:main", cwd=self.c)
        self.assertIn("mine", proc.stderr)

if __name__ == "__main__":
    unittest.main()
