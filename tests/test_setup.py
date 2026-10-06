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


if __name__ == "__main__":
    unittest.main()
