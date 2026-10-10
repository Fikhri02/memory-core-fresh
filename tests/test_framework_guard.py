"""The framework repo must never carry personal context (memory-core-sync spec §8, layer 5). Stdlib only.

Checks everything a push would send: tracked files plus untracked files that are not ignored. Runs
only where `.memory-core/kind` is `framework` — a personal install is marked `context` by setup.py.
"""

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp-spike"))

import health  # noqa: E402
import sync_merge  # noqa: E402

GITKEEPS = {f"{d}/{s}/.gitkeep" for d in ("brainstorming", "project-plans") for s in ("active", "archived", "done")}
ONLY = {
    "main/": {"main/.gitkeep", "main/README.md", "main/main-memory-format.md", "main/session-brief-core.md",
              "main/session-format.md"},
    "career/": {"career/README.md", "career/_template/"},
    "learning/": {"learning/README.md", "learning/_template/"},
    "project-management/": {"project-management/README.md", "project-management/_template/"},
    "ecosystem/": {"ecosystem/README.md", "ecosystem/_template/"},
    "brainstorming/": {"brainstorming/README.md"} | {g for g in GITKEEPS if g.startswith("brainstorming/")},
    "project-plans/": {"project-plans/README.md"} | {g for g in GITKEEPS if g.startswith("project-plans/")},
    "notes/": {"notes/.gitkeep", "notes/README.md", "notes/architecture-review/README.md"},
    "delegate-task/": {"delegate-task/README.md", "delegate-task/Timeline/.gitkeep"},
    "devices/": {"devices/README.md"},
    "device/": set(),
    "brain/": {"brain/README.md"},
    "debugging/": {"debugging/README.md"},
}
LAYERS = ("general.md", "website.md", "web-app.md", "mobile.md")


def kind() -> str | None:
    marker = ROOT / ".memory-core" / "kind"
    return marker.read_text(encoding="utf-8").strip() if marker.is_file() else None


def pushable() -> list[str]:
    tracked = subprocess.run(["git", "-C", str(ROOT), "ls-files"], capture_output=True, text=True)
    if tracked.returncode != 0:
        return []
    others = subprocess.run(["git", "-C", str(ROOT), "ls-files", "--others", "--exclude-standard"],
                            capture_output=True, text=True).stdout
    return sorted(set(tracked.stdout.splitlines()) | set(others.splitlines()))


def allowed(path: str, rules: set[str]) -> bool:
    return any(path == r or (r.endswith("/") and path.startswith(r)) for r in rules)


def outside_fences_and_comments(text: str) -> list[str]:
    lines, in_fence, in_comment = [], False, False
    for line in text.splitlines():
        if in_comment:
            in_comment = "-->" not in line
        elif sync_merge.FENCE_LINE.match(line):
            in_fence = not in_fence
        elif line.lstrip().startswith("<!--") and "-->" not in line.split("<!--", 1)[1]:
            in_comment = True
        elif not in_fence:
            lines.append(line)
    return lines


@unittest.skipUnless(kind() == "framework", "only the framework repo is checked")
class FrameworkCarriesNoContext(unittest.TestCase):
    def test_memory_folders_hold_only_templates(self):
        files = pushable()
        if not files:
            self.skipTest("not a git checkout")
        leaked = [p for p in files for folder, rules in ONLY.items() if p.startswith(folder) and not allowed(p, rules)]
        self.assertEqual([], leaked, "personal context in the framework repo — keep it in a context install")

    def test_design_layers_hold_no_rules(self):
        for name in LAYERS:
            rules = [l for l in outside_fences_and_comments((ROOT / "design" / name).read_text()) if l.startswith("- **")]
            self.assertEqual([], rules, f"design/{name} holds personal rules")

    def test_design_libraries_and_journal_are_empty(self):
        for name in ("palettes.md", "type.md"):
            self.assertEqual({}, health.library_entries((ROOT / "design" / name).read_text()), f"design/{name}")
        self.assertEqual([], sync_merge._section_starts((ROOT / "design/journal.md").read_text(), 2))


class Marker(unittest.TestCase):
    def test_framework_repo_is_marked(self):
        if not (ROOT / "plugins" / "violet-skills").is_dir():
            self.skipTest("not a memory-core checkout")
        self.assertIn(kind(), ("framework", "context"))
