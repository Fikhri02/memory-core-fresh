"""Tests for mcp-spike/sync_device.py. Stdlib only."""

import json
import sys
import tempfile
import unittest
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "mcp-spike"))

import sync_device as dev  # noqa: E402


def write(root: Path, rel: str, text: str) -> Path:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)


class Identity(Base):
    def test_identity_is_created_once_and_kept(self):
        first = dev.ensure_identity(self.root, "MacBook-Air.local", today=date(2026, 10, 10))
        again = dev.ensure_identity(self.root, "other")
        self.assertEqual(first, again)
        self.assertEqual("macbook-air", first["name"])
        self.assertEqual("2026-10-10", first["registered"])
        self.assertEqual(36, len(first["id"]))

    def test_slug_name_never_empty(self):
        self.assertEqual("device", dev.slug_name("..."))


class Follow(Base):
    def test_round_trip_keeps_only_checked_items(self):
        dev.write_follow(self.root, {"project-management": ["acme-web", "acme-cms"], "ecosystem": ["acme-retail"]})
        text = (self.root / "device/follow.md").read_text()
        write(self.root, "device/follow.md", text + "\n## Projects\n- [ ] ignored-one\n")
        got = dev.read_follow(self.root)
        self.assertEqual(["acme-cms", "acme-web"], got["project-management"])
        self.assertEqual(["acme-retail"], got["ecosystem"])

    def test_missing_file_means_core_only(self):
        self.assertEqual({"project-management": [], "ecosystem": []}, dev.read_follow(self.root))


class Paths(Base):
    def test_set_and_read_paths(self):
        dev.set_path(self.root, "git@github.com:acme/acme-cms.git", "~/code/acme-cms")
        dev.set_path(self.root, "acme-web/web", "~/code/acme-web")
        self.assertEqual("~/code/acme-cms", dev.read_paths(self.root)["git@github.com:acme/acme-cms.git"])
        self.assertEqual(2, len(dev.read_paths(self.root)))


class Registry(Base):
    def claude(self):
        home = self.root / "home"
        write(home, ".claude/plugins/installed_plugins.json", json.dumps({"version": 2, "plugins": {
            "violet-skills@violet-fresh": [{"installPath": str(home / "p/violet")}],
            "superpowers@claude-plugins-official": [{"installPath": str(home / "p/superpowers")}],
            "antislop@anti-slop": [{"installPath": str(home / "p/antislop")}],
        }}))
        write(home, ".claude/plugins/known_marketplaces.json", json.dumps({
            "claude-plugins-official": {"source": {"source": "github", "repo": "anthropics/claude-plugins-official"}},
            "anti-slop": {"source": {"source": "git", "url": "https://user:SECRET-GIT@github.com/m/anti-slop.git?token=SECRET-Q"}},
        }))
        write(home, ".claude/settings.json", json.dumps({"enabledPlugins": {"superpowers@claude-plugins-official": True}}))
        write(home, "p/antislop/.mcp.json", json.dumps({"mcpServers": {"antislop-contrast": {
            "command": "node", "args": ["--token", "SECRET-ARG"], "env": {"API_KEY": "SECRET-ENV"}}}}))
        write(home, ".claude.json", json.dumps({
            "mcpServers": {
                "memory-core-context": {"type": "stdio", "command": "/Users/x/.venv/bin/python3", "args": ["server.py", "--key=SECRET-ARG2"], "env": {"TOKEN": "SECRET-ENV2"}},
                "remote": {"type": "http", "url": "https://api.example.com/mcp?key=SECRET-URL", "headers": {"Authorization": "Bearer SECRET-HDR"}},
                "shell": {"command": "API_KEY=SECRET-INLINE node index.js"},
            },
            "projects": {"/Users/x/SECRET-PATH": {"mcpServers": {"proj": {"type": "stdio", "command": "dotnet"}}}},
        }))
        write(self.root, ".mcp.json", json.dumps({"mcpServers": {"repo-one": {"type": "sse", "url": "https://h.example.org/s?SECRET-REPO"}}}))
        return home

    def test_plugins_skip_violet_and_render_sources_without_credentials(self):
        home = self.claude()
        rows = dev.plugin_rows(home / ".claude", home / ".claude/settings.json")
        self.assertEqual(["antislop", "superpowers"], [r[0] for r in rows])
        self.assertEqual(("superpowers", "claude-plugins-official (github anthropics/claude-plugins-official)", "yes"), rows[1])
        self.assertEqual("anti-slop (git github.com/m/anti-slop.git)", rows[0][1])
        self.assertEqual("no", rows[0][2])

    def test_mcp_rows_cover_every_scope(self):
        home = self.claude()
        rows = dev.mcp_rows(home / ".claude.json", self.root, home / ".claude")
        by_name = {r[0]: r for r in rows}
        self.assertEqual(("memory-core-context", "user", "stdio", "python3"), by_name["memory-core-context"])
        self.assertEqual(("remote", "user", "http", "api.example.com"), by_name["remote"])
        self.assertEqual(("shell", "user", "stdio", "node"), by_name["shell"])
        self.assertEqual(("proj", "project", "stdio", "dotnet"), by_name["proj"])
        self.assertEqual(("repo-one", "repo", "sse", "h.example.org"), by_name["repo-one"])
        self.assertEqual(("antislop-contrast", "plugin antislop", "stdio", "node"), by_name["antislop-contrast"])

    def test_record_never_contains_a_planted_secret(self):
        home = self.claude()
        identity = dev.ensure_identity(self.root, "laptop-a")
        text = dev.device_record(identity, {"project-management": ["acme-web"], "ecosystem": ["acme-retail"]},
                                 dev.plugin_rows(home / ".claude", home / ".claude/settings.json"),
                                 dev.mcp_rows(home / ".claude.json", self.root, home / ".claude"),
                                 "2026-10-10 18:42", "macOS 26.5")
        self.assertNotIn("SECRET", text)
        self.assertIn("- acme-web · ecosystem acme-retail", text)
        self.assertIn("| memory-core-context | user | stdio | python3 |", text)

    def test_write_registry_keeps_a_retired_status(self):
        identity = dev.ensure_identity(self.root, "old-mac")
        common = dict(follows={"project-management": [], "ecosystem": []}, plugins=[], mcps=[], os_name="macOS 26.5")
        path = dev.write_registry(self.root, identity, now=datetime(2026, 1, 1, 9, 0), status="retired", **common)
        dev.write_registry(self.root, identity, now=datetime(2026, 10, 10, 9, 0), **common)
        self.assertIn("**Status**: retired", path.read_text())

    def test_read_registry_and_differences(self):
        a = {"id": "11111111-1111-4111-8111-111111111111", "name": "laptop-a", "registered": "2026-10-10"}
        b = {"id": "22222222-2222-4222-8222-222222222222", "name": "laptop-b", "registered": "2026-10-10"}
        f = {"project-management": [], "ecosystem": []}
        write(self.root, f"devices/{a['id']}.md", dev.device_record(a, f, [("antislop", "anti-slop (x)", "yes")],
                                                                     [("memory-core-context", "user", "stdio", "python3")], "2026-10-10 09:00", "macOS"))
        write(self.root, f"devices/{b['id']}.md", dev.device_record(b, f, [], [], "2026-10-09 09:00", "macOS"))
        devices = dev.read_registry(self.root)
        self.assertEqual({"laptop-a", "laptop-b"}, {d["name"] for d in devices})
        self.assertEqual({"antislop"}, next(d for d in devices if d["name"] == "laptop-a")["plugins"])
        diffs = dev.registry_differences(devices)
        self.assertIn("laptop-b is missing plugin antislop", diffs)
        self.assertIn("laptop-b is missing MCP server memory-core-context", diffs)



GENERAL = """# X

## Repositories

| Name | Local Path | Git Origin |
|------|-----------|------------|
| Api | `~/projects/x/api` (nested one level deeper) | `git@github.com:a/api.git` |
| Web | `~/projects/x/web` | *(not set)* |
| Docs |  | `https://github.com/a/docs.git` |

## Dev Notes
"""


class MigratePaths(Base):
    def test_dry_run_reports_without_writing(self):
        write(self.root, "project-management/x/General.md", GENERAL)
        found = dev.migrate_general_paths(self.root)
        self.assertEqual([("x", "git@github.com:a/api.git", "~/projects/x/api"),
                          ("x", "x/Web", "~/projects/x/web")], found)
        self.assertEqual(GENERAL, (self.root / "project-management/x/General.md").read_text())
        self.assertEqual({}, dev.read_paths(self.root))

    def test_write_moves_paths_and_drops_the_column(self):
        write(self.root, "project-management/x/General.md", GENERAL)
        write(self.root, "project-management/_template/general.md", GENERAL)
        dev.migrate_general_paths(self.root, write=True)
        text = (self.root / "project-management/x/General.md").read_text()
        self.assertIn("| Name | Git Origin |\n|------|------------|\n| Api | `git@github.com:a/api.git` |", text)
        self.assertNotIn("Local Path", text)
        self.assertIn("## Dev Notes", text)
        self.assertEqual("~/projects/x/api", dev.read_paths(self.root)["git@github.com:a/api.git"])
        self.assertEqual(GENERAL, (self.root / "project-management/_template/general.md").read_text())

    def test_placeholder_origin_is_not_a_key(self):
        write(self.root, "project-management/x/General.md",
              GENERAL.replace("*(not set)*", "_(no remote yet)_"))
        keys = [k for _, k, _ in dev.migrate_general_paths(self.root)]
        self.assertEqual(["git@github.com:a/api.git", "x/Web"], keys)

    def test_second_run_finds_nothing(self):
        write(self.root, "project-management/x/General.md", GENERAL)
        dev.migrate_general_paths(self.root, write=True)
        self.assertEqual([], dev.migrate_general_paths(self.root, write=True))

if __name__ == "__main__":
    unittest.main()
