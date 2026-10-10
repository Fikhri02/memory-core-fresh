"""Tests for mcp-spike/sync_guard.py. Stdlib only."""

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-spike"))

import sync_device as dev  # noqa: E402
import sync_guard as guard  # noqa: E402


class Normalise(unittest.TestCase):
    def test_every_spelling_of_the_framework_repo_is_the_same(self):
        spellings = [
            "git@github.com:Fikhri02/memory-core-fresh.git",
            "https://github.com/Fikhri02/memory-core-fresh.git",
            "https://github.com/Fikhri02/memory-core-fresh/",
            "HTTPS://GITHUB.COM/FIKHRI02/MEMORY-CORE-FRESH",
            "https://x-access-token:ghp_SECRET@github.com/Fikhri02/memory-core-fresh.git",
            "ssh://git@github.com/Fikhri02/memory-core-fresh.git",
            "github.com/fikhri02/memory-core-fresh",
        ]
        self.assertEqual({"github.com/fikhri02/memory-core-fresh"}, {guard.normalise_remote(s) for s in spellings})

    def test_local_paths_are_local(self):
        self.assertTrue(guard.is_local("/tmp/ctx.git"))
        self.assertTrue(guard.is_local("repos/ctx.git"))
        self.assertTrue(guard.is_local("file:///tmp/ctx.git"))
        self.assertFalse(guard.is_local("git@github.com:a/b.git"))


class RemoteIsSafe(unittest.TestCase):
    def test_framework_repo_refused_whatever_the_spelling_or_visibility(self):
        for url in ("git@github.com:Fikhri02/memory-core-fresh.git", "https://github.com/fikhri02/MEMORY-CORE-FRESH/"):
            ok, reason = guard.remote_is_safe(url, guard.DEFAULT_DENY, "PRIVATE")
            self.assertFalse(ok)
            self.assertIn("framework repo", reason)

    def test_public_and_unknown_visibility_refused(self):
        self.assertFalse(guard.remote_is_safe("git@github.com:me/ctx.git", [], "PUBLIC")[0])
        ok, reason = guard.remote_is_safe("git@github.com:me/ctx.git", [], None)
        self.assertFalse(ok)
        self.assertIn("unknown visibility", reason)

    def test_private_remote_and_local_repo_accepted(self):
        self.assertTrue(guard.remote_is_safe("git@github.com:me/ctx.git", guard.DEFAULT_DENY, "PRIVATE")[0])
        self.assertTrue(guard.remote_is_safe("/tmp/ctx.git", guard.DEFAULT_DENY, None)[0])

    def test_push_to_anything_but_the_configured_remote_refused(self):
        ok, reason = guard.remote_is_safe("git@github.com:me/other.git", [], "PRIVATE", "git@github.com:me/ctx.git")
        self.assertFalse(ok)
        self.assertIn("not this memory's sync remote", reason)


class Marker(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_kind_round_trip(self):
        self.assertIsNone(guard.repo_kind(self.root))
        guard.set_kind(self.root, "context")
        self.assertEqual("context", guard.repo_kind(self.root))

    def test_check_push_without_setup_is_refused(self):
        ok, reason = guard.check_push(self.root, "/tmp/x.git")
        self.assertFalse(ok)
        self.assertIn("sync setup", reason)

    def test_check_push_uses_device_settings(self):
        dev.write_kv(self.root / "device/sync.md", {"remote": "git@github.com:me/ctx.git", "visibility": "PRIVATE",
                                                    "deny": ""}, "Sync settings")
        self.assertTrue(guard.check_push(self.root, "https://github.com/me/ctx.git")[0])
        self.assertFalse(guard.check_push(self.root, "git@github.com:Fikhri02/memory-core-fresh.git")[0])

    def test_install_hook_is_executable_and_calls_the_guard(self):
        hook = guard.install_hook(self.root / ".git/hooks/pre-push")
        self.assertTrue(hook.stat().st_mode & stat.S_IXUSR)
        self.assertIn("sync_guard.py\" check-push \"$2\"", hook.read_text())


if __name__ == "__main__":
    unittest.main()
