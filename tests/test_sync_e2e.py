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
import ram  # noqa: E402

ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
    "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
}
def NO_GH(remote, account):
    return None



def write(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def append(root: Path, rel: str, text: str) -> None:
    write(root, rel, (root / rel).read_text(encoding="utf-8") + text)


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True)


def memory(root: Path) -> None:
    write(root, "main/current-session.md", ram.POINTER_TEXT)
    write(root, "main/session-archive.md", "# Session Archive\n\n_older_\n\n### 2026-10-01 — old\n\n- old\n")
    write(root, "main/preferences.md", "# Preferences\n\n## Output\n\n- **Show**: render, do not describe.\n")
    write(root, "design/general.md", "# General\n\n## Colour\n\n- **Flat**: one.\n")
    write(root, "project-management/README.md", "# Projects\n")
    write(root, "project-management/_template/general.md", "# {project-name}\n")
    for slug in ("alpha", "beta"):
        write(root, f"project-management/{slug}/Timeline.md", f"# Timeline — {slug}\n\n## 2026-10-10\n- start\n")
    write(root, "ecosystem/README.md", "# Ecosystems\n")
    (root / "mcp-spike").mkdir(parents=True, exist_ok=True)
    for name in ("sync_device.py", "sync_guard.py", "sync_merge.py", "sync_git.py", "ram.py"):
        shutil.copy(ROOT / "mcp-spike" / name, root / "mcp-spike" / name)


class LaptopPair(unittest.TestCase):
    """Two laptops joined to one bare repo — the fixture, with no tests of its own."""

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

    def save_or_merge(self, root):
        saved = sg.cmd_save(root, "save")
        if saved["status"] == "rejected":
            self.assertIn(sg.cmd_pull(root)["status"], ("merged", "up-to-date"))
            saved = sg.cmd_save(root, "save")
        self.assertEqual("pushed", saved["status"], saved)


class TwoLaptops(LaptopPair):
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

    def test_first_merge_resolves_a_conflict_outside_the_sparse_cone(self):
        # An existing install joining: its ecosystem/README.md differs, and with no ecosystem followed
        # that path sits outside the sparse cone — resolving it must still write the index
        c = self.bare.parent / "c"
        memory(c)
        write(c, "ecosystem/README.md", "# Ecosystems on laptop c\n")
        run("git", "init", "-q", "-b", "main", cwd=c)
        run("git", "add", "-A", cwd=c)
        run("git", "commit", "-q", "-m", "another install", cwd=c)
        self.assertEqual("remote-has-content", sg.cmd_setup(c, str(self.bare), "", "laptop-c", visibility_fn=NO_GH)["status"])
        merged = sg.cmd_first_merge(c, ["alpha", "beta"], [])
        if merged["status"] == "needs-answers":
            merged = sg.cmd_resolve(c, {u["path"]: {"*": "ours"} for u in merged["units"]})
        self.assertEqual("merged", merged["status"], merged)
        self.assertIn("laptop c", run("git", "show", "HEAD:ecosystem/README.md", cwd=c).stdout)

    def test_each_laptop_writes_its_own_ram_and_sync_never_asks(self):
        self.settle(self.a)
        self.settle(self.b)
        for round_ in (1, 2):
            for root, tag in ((self.a, "a"), (self.b, "b")):
                name = ram.device_name(root)
                ram.ensure(root)
                ram.stamp(root, f"round {round_} on {tag}")
                append(root, f"main/ram/{name}.md", f"\n### 2026-10-1{round_} — from {tag} {round_}\n\n- {tag}\n")
                self.save_or_merge(root)
        self.settle(self.a)
        mine = (self.a / "main/ram/laptop-a.md").read_text()
        theirs = (self.a / "main/ram/laptop-b.md").read_text()
        self.assertIn("from a 2", mine)
        self.assertNotIn("from b", mine)
        self.assertIn("from b 2", theirs)
        self.assertNotIn("from a", theirs)
        self.assertEqual(1, mine.count("# Session RAM — laptop-a"))
        self.assertEqual("round 2 on b", ram.read_header(theirs)["last_session"])

    def test_editing_another_laptops_ram_blocks_the_upload(self):
        ram.ensure(self.b)
        self.assertEqual("pushed", sg.cmd_save(self.b, "save")["status"])
        self.settle(self.a)
        append(self.a, "main/ram/laptop-b.md", "\n- stray\n")
        blocked = sg.cmd_save(self.a, "save")
        self.assertEqual("blocked", blocked["status"], blocked)
        self.assertTrue(blocked["reason"].startswith("main/ram/laptop-b.md belongs to laptop-b — only that laptop writes it"))
        self.assertIn("git restore --source=origin/main --staged --worktree -- main/ram/laptop-b.md", blocked["reason"])
        self.assertEqual("blocked", sg.cmd_pull(self.a)["status"])

    def test_renaming_another_laptops_ram_blocks_the_upload(self):
        ram.ensure(self.b)
        self.assertEqual("pushed", sg.cmd_save(self.b, "save")["status"])
        self.settle(self.a)
        self.assertEqual(0, run("git", "mv", "main/ram/laptop-b.md", "main/moved.md", cwd=self.a).returncode)
        blocked = sg.cmd_save(self.a, "save")
        self.assertEqual("blocked", blocked["status"], blocked)
        self.assertEqual(["main/ram/laptop-b.md"], blocked["paths"])

    def test_committed_edit_to_another_laptops_ram_blocks_the_upload(self):
        ram.ensure(self.b)
        self.assertEqual("pushed", sg.cmd_save(self.b, "save")["status"])
        self.settle(self.a)
        append(self.a, "main/ram/laptop-b.md", "\n- stray from a\n")
        run("git", "commit", "-q", "-am", "agent commit", cwd=self.a)
        blocked = sg.cmd_save(self.a, "save")
        self.assertEqual("blocked", blocked["status"], blocked)
        run("git", "restore", "--source=origin/main", "--staged", "--worktree", "--", "main/ram/laptop-b.md", cwd=self.a)
        self.assertEqual("pushed", sg.cmd_save(self.a, "save")["status"])
        self.assertNotIn("stray from a", show(self.bare, "main/ram/laptop-b.md"))

    def test_conflict_on_a_ram_file_keeps_its_owners_version(self):
        ram.ensure(self.b)
        self.assertEqual("pushed", sg.cmd_save(self.b, "save")["status"])
        self.settle(self.a)
        append(self.a, "main/ram/laptop-b.md", "\n- stray from a\n")
        run("git", "commit", "-q", "-am", "stray", cwd=self.a)  # bypasses the guard on purpose
        append(self.b, "main/ram/laptop-b.md", "\n- b again\n")
        self.save_or_merge(self.b)  # b is behind a's settle push, so it may need a pull first
        pulled = sg.cmd_pull(self.a)
        self.assertEqual("merged", pulled["status"], pulled)
        text = (self.a / "main/ram/laptop-b.md").read_text()
        self.assertIn("- b again", text)
        self.assertNotIn("stray from a", text)
        self.assertTrue(any("laptop-b" in n for n in pulled.get("notes", [])), pulled)

    def test_conflict_side_delete_is_honoured(self):
        ram.ensure(self.b)
        self.assertEqual("pushed", sg.cmd_save(self.b, "save")["status"])
        self.settle(self.a)
        append(self.a, "main/ram/laptop-b.md", "\n- stray from a\n")
        run("git", "commit", "-q", "-am", "stray", cwd=self.a)
        (self.b / "main/ram/laptop-b.md").unlink()
        self.save_or_merge(self.b)
        self.assertEqual("merged", sg.cmd_pull(self.a)["status"])
        self.assertFalse((self.a / "main/ram/laptop-b.md").exists())

    def test_old_layout_ram_from_another_laptop_is_not_absorbed_here(self):
        self.settle(self.a)
        self.settle(self.b)
        write(self.b, "main/current-session.md", ram.POINTER_TEXT + "\n### 2026-10-11 — b on old skills\n\n- b\n")
        run("git", "commit", "-q", "-am", "sync: laptop-b — save memory", cwd=self.b)  # what old sync code commits
        self.assertEqual("pushed", sg.push(self.b)["status"])
        self.assertEqual("merged", sg.cmd_pull(self.a)["status"])
        saved = sg.cmd_save(self.a, "save")
        self.assertEqual("pushed", saved["status"], saved)
        own = self.a / "main/ram/laptop-a.md"
        self.assertFalse(own.exists() and "b on old skills" in own.read_text())
        self.assertIn("b on old skills", (self.a / "main/current-session.md").read_text())
        self.save_or_merge(self.b)  # laptop-b, now on the new code, saves: its old RAM moves into its own file
        self.assertIn("b on old skills", (self.b / "main/ram/laptop-b.md").read_text())
        self.assertEqual(ram.POINTER_TEXT, (self.b / "main/current-session.md").read_text())

    def test_pointer_drift_is_absorbed_on_save(self):
        self.settle(self.a)
        write(self.a, "main/current-session.md", ram.POINTER_TEXT + "\n### 2026-10-11 — old skills\n\n- x\n")
        saved = sg.cmd_save(self.a, "save")
        self.assertEqual("pushed", saved["status"], saved)
        self.assertTrue(any("main/ram/laptop-a.md" in n for n in saved.get("notes", [])))
        self.assertEqual(ram.POINTER_TEXT, (self.a / "main/current-session.md").read_text())
        self.assertIn("old skills", (self.a / "main/ram/laptop-a.md").read_text())

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


class BinaryGuard(LaptopPair):
    """Memory holds text: a new binary outside design/ or the allow list blocks the upload."""

    PNG = b"\x89PNG\r\n\x1a\n\x00\x00"

    def put(self, rel: str, data: bytes) -> None:
        (self.a / rel).parent.mkdir(parents=True, exist_ok=True)
        (self.a / rel).write_bytes(data)

    def test_new_binary_outside_design_blocks_the_save(self):
        self.settle(self.a)
        self.put("notes/site/img/hero.webp", self.PNG)
        write(self.a, "notes/site/index.md", "# Site\n")
        blocked = sg.cmd_save(self.a, "save")
        self.assertEqual("blocked", blocked["status"], blocked)
        self.assertEqual(["notes/site/img/hero.webp"], blocked["paths"])
        self.assertIn("binary", blocked["reason"])
        self.assertIn(".memory-core/binary-allow", blocked["reason"])
        self.assertNotIn("notes/site/index.md", tree(self.bare))

    def test_binary_detected_by_content_not_only_extension(self):
        self.settle(self.a)
        self.put("notes/blob.dat", b"abc\x00def")
        self.assertEqual(["notes/blob.dat"], sg.cmd_save(self.a, "save")["paths"])

    def test_non_ascii_file_name_is_caught(self):
        self.settle(self.a)
        self.put("notes/site/café.webp", self.PNG)
        self.assertEqual(["notes/site/café.webp"], sg.cmd_save(self.a, "save")["paths"])

    def test_committed_binary_is_caught_too(self):
        self.settle(self.a)
        self.put("notes/a.png", self.PNG)
        run("git", "add", "notes/a.png", cwd=self.a)
        run("git", "commit", "-q", "-m", "agent commit", cwd=self.a)
        self.assertEqual("blocked", sg.cmd_save(self.a, "save")["status"])

    def test_allow_list_pattern_lets_it_through(self):
        self.settle(self.a)
        write(self.a, ".memory-core/binary-allow", "# globs, one per line\nnotes/site/**\n")
        self.put("notes/site/hero.webp", self.PNG)
        self.assertEqual("pushed", sg.cmd_save(self.a, "save")["status"])
        self.assertIn("notes/site/hero.webp", tree(self.bare))

    def test_binary_already_tracked_can_still_change(self):
        self.settle(self.a)
        self.put("notes/old.png", self.PNG)
        run("git", "add", "notes/old.png", cwd=self.a)
        run("git", "commit", "-q", "-m", "before the guard", cwd=self.a)
        run("git", "push", "-q", "origin", "HEAD:main", cwd=self.a)
        run("git", "fetch", "-q", "origin", cwd=self.a)
        self.put("notes/old.png", self.PNG + b"x")
        self.assertEqual("pushed", sg.cmd_save(self.a, "save")["status"])

    def test_upload_of_a_project_with_a_binary_is_blocked_and_unstaged(self):
        self.settle(self.a)
        write(self.a, "project-management/gamma/Timeline.md", "# Timeline — gamma\n")
        self.put("project-management/gamma/shot.jpg", b"\xff\xd8\xff\x00")
        blocked = sg.cmd_upload(self.a, "project-management", "gamma")
        self.assertEqual("blocked", blocked["status"], blocked)
        self.assertEqual(["project-management/gamma/shot.jpg"], blocked["paths"])
        self.assertEqual("", run("git", "diff", "--cached", "--name-only", cwd=self.a).stdout.strip())
        self.assertNotIn("project-management/gamma/Timeline.md", tree(self.bare))


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
