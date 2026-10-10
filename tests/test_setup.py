"""Tests for setup.py's plugin install step and closing summary. Stdlib only."""

import contextlib
import io
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import setup  # noqa: E402


def result(code=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args=[], returncode=code, stdout=stdout, stderr=stderr)


def run_step(side_effect):
    out = io.StringIO()
    with mock.patch("setup.subprocess.run", side_effect=side_effect) as run, contextlib.redirect_stdout(out):
        setup.step_install_plugin(ROOT)
    return out.getvalue(), run


class InstallPlugin(unittest.TestCase):
    def test_success_adds_marketplace_then_installs(self):
        text, run = run_step([result(), result()])
        self.assertIn("done", text)
        self.assertEqual(run.call_args_list[0].args[0],
                         ["claude", "plugin", "marketplace", "add", str(ROOT / "plugins")])
        self.assertEqual(run.call_args_list[1].args[0],
                         ["claude", "plugin", "install", "violet-skills@violet-local"])

    def test_existing_marketplace_still_installs(self):
        text, run = run_step([result(1, stderr="Marketplace 'violet-local' is already installed"), result()])
        self.assertEqual(run.call_count, 2)
        self.assertIn("done", text)

    def test_marketplace_failure_stops_before_install(self):
        text, run = run_step([result(1, stderr="Invalid marketplace manifest")])
        self.assertEqual(run.call_count, 1)
        self.assertIn("FAILED", text)
        self.assertIn("Invalid marketplace manifest", text)
        self.assertIn("claude plugin install violet-skills@violet-local", text)

    def test_install_failure_shows_cli_error(self):
        text, _ = run_step([result(), result(1, stderr="Plugin not found in marketplace")])
        self.assertIn("FAILED", text)
        self.assertIn("Plugin not found in marketplace", text)
        self.assertNotIn("done", text)

    def test_already_installed_counts_as_done(self):
        text, run = run_step([result(), result(1, stderr="Plugin violet-skills is already installed")])
        self.assertEqual(run.call_count, 2)
        self.assertIn("done", text)

    def test_missing_cli_prints_manual_commands(self):
        text, _ = run_step(FileNotFoundError("claude"))
        self.assertIn("claude CLI not found", text)
        self.assertIn(f"claude plugin marketplace add {ROOT / 'plugins'}", text)
        self.assertIn("claude plugin install violet-skills@violet-local", text)


def run_mcp(side_effect):
    out = io.StringIO()
    with mock.patch("setup.subprocess.run", side_effect=side_effect), \
            mock.patch("builtins.input", return_value="y"), contextlib.redirect_stdout(out):
        setup.step_register_mcp(ROOT)
    return out.getvalue()


class RegisterMcp(unittest.TestCase):
    def test_missing_cli_is_reported_not_raised(self):
        text = run_mcp(FileNotFoundError("claude"))
        self.assertIn("skipped (claude CLI not found)", text)

    def test_already_registered_counts_as_done(self):
        text = run_mcp([result(1, stderr="MCP server memory-core-context already exists in user config")])
        self.assertIn("done", text)
        self.assertNotIn("not found", text)

    def test_other_failure_shows_cli_error(self):
        text = run_mcp([result(1, stderr="Invalid server command")])
        self.assertIn("FAILED", text)
        self.assertIn("Invalid server command", text)


class Summary(unittest.TestCase):
    def test_summary_does_not_point_at_missing_customize_doc(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            setup.print_summary({"{{COMPANION_NAME}}": "Violet", "{{USER_NAME}}": "Sam"})
        self.assertNotIn("CUSTOMIZE.md", out.getvalue())



class SyncJoin(unittest.TestCase):
    def test_sync_flag_skips_companion_questions_and_joins(self):
        with mock.patch.object(sys, "argv", ["setup.py", "--sync"]), \
             mock.patch("setup.collect_inputs") as collect, \
             mock.patch("setup.step_join_sync") as join, \
             mock.patch("setup.ensure_pyyaml"), mock.patch("setup.check_python_version"):
            setup.main()
        collect.assert_not_called()
        join.assert_called_once()

    def test_sync_with_url_clones_sparse_then_runs_the_clone(self):
        calls = []

        def fake_run(args, **kw):
            calls.append(args)
            return result()

        with mock.patch.object(sys, "argv", ["setup.py", "--sync", "git@github.com:me/ctx.git", "/tmp/mc"]), \
             mock.patch("setup.subprocess.run", side_effect=fake_run), \
             mock.patch("setup.ensure_pyyaml"), mock.patch("setup.check_python_version"):
            setup.main()
        self.assertEqual(["git", "clone", "--sparse", "git@github.com:me/ctx.git", "/tmp/mc"], calls[0])
        self.assertEqual([sys.executable, str(Path("/tmp/mc") / "setup.py"), "--sync"], calls[-1])

    def test_join_refuses_a_non_context_folder(self):
        out = io.StringIO()
        with mock.patch("setup._clone_kind", return_value=None), contextlib.redirect_stdout(out):
            setup.step_join_sync(ROOT)
        self.assertIn("not a memory-core context clone", out.getvalue())


class CloneForSync(unittest.TestCase):
    """Final review I1: a sparse clone must hold the core folders before setup runs."""

    def test_clone_checks_out_core_and_templates_but_no_projects(self):
        import os
        import tempfile
        env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@e", "GIT_COMMITTER_NAME": "t",
               "GIT_COMMITTER_EMAIL": "t@e", "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, env):
            base = Path(tmp)
            src = base / "src"
            for rel in ("mcp-spike/sync_git.py", "adapters/generate.py", "main/x.md",
                        "project-management/_template/general.md", "project-management/alpha/Timeline.md", "setup.py"):
                (src / rel).parent.mkdir(parents=True, exist_ok=True)
                (src / rel).write_text("x\n")
            for args in (["init", "-q", "-b", "main"], ["add", "-A"], ["commit", "-q", "-m", "c"]):
                subprocess.run(["git", "-C", str(src), *args], check=True, capture_output=True)
            dest = base / "dest"
            self.assertEqual(0, setup.clone_for_sync(str(src), str(dest)))
            self.assertTrue((dest / "mcp-spike/sync_git.py").is_file())
            self.assertTrue((dest / "adapters/generate.py").is_file())
            self.assertTrue((dest / "project-management/_template/general.md").is_file())
            self.assertFalse((dest / "project-management/alpha").exists())


class MarkContext(unittest.TestCase):
    """A personalised install is context, never framework — sync setup and the framework guard rely on it."""

    def test_mark_context_writes_the_marker(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".memory-core").mkdir()
            (root / ".memory-core" / "kind").write_text("framework\n")
            setup.step_mark_context(root)
            self.assertEqual("context", (root / ".memory-core" / "kind").read_text().strip())

    def test_main_marks_context_after_writing_memory(self):
        steps = []
        names = ("step_write_spec", "step_write_memory_files", "step_mark_context", "step_run_adapters",
                 "step_write_claude_settings", "step_register_mcp", "step_install_plugin")
        patches = [mock.patch(f"setup.{n}", side_effect=lambda *a, n=n: steps.append(n)) for n in names]
        with mock.patch.object(sys, "argv", ["setup.py", "--reset"]), mock.patch("setup.collect_inputs", return_value={}), \
             mock.patch("setup.print_summary"), mock.patch("setup.ensure_pyyaml"), mock.patch("setup.check_python_version"):
            for p in patches:
                p.start()
            try:
                setup.main()
            finally:
                for p in patches:
                    p.stop()
        self.assertLess(steps.index("step_write_memory_files"), steps.index("step_mark_context"))

if __name__ == "__main__":
    unittest.main()
