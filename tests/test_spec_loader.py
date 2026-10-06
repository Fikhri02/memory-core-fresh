"""Tests for adapters/spec_loader.validate_spec. Needs PyYAML: run with .venv/bin/python."""

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HAS_YAML = importlib.util.find_spec("yaml") is not None
if HAS_YAML:
    sys.path.insert(0, str(ROOT / "adapters"))
    import spec_loader  # noqa: E402


@unittest.skipUnless(HAS_YAML, "PyYAML not installed — run with .venv/bin/python")
class ValidateSkills(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def folders(self, *names):
        for name in names:
            d = self.root / "plugins" / "violet-skills" / "skills" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text("---\nname: x\n---\n", encoding="utf-8")

    def spec(self, *names):
        lines = ['version: "1.0"', "skills:"]
        for name in names:
            lines += [f"  {name}:", "    description: x", "    triggers:", "      explicit: []"]
        path = self.root / "memory-core.yaml"
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return spec_loader.load_spec(path)

    def test_matching_skills_give_no_warnings(self):
        self.folders("alpha", "beta")
        self.assertEqual([], spec_loader.validate_spec(self.spec("alpha", "beta"), self.root))

    def test_any_skill_count_is_fine_when_folders_match(self):
        self.folders("a", "b", "c", "d", "e")
        warnings = spec_loader.validate_spec(self.spec("a", "b", "c", "d", "e"), self.root)
        self.assertFalse(any("Expected" in w for w in warnings), warnings)

    def test_new_skill_folder_without_spec_entry_is_reported(self):
        self.folders("alpha", "gamma")
        warnings = spec_loader.validate_spec(self.spec("alpha"), self.root)
        self.assertIn(
            "MISSING from spec: plugins/violet-skills/skills/gamma/ has no entry in memory-core.yaml",
            warnings,
        )

    def test_spec_entry_without_folder_is_reported(self):
        self.folders("alpha")
        warnings = spec_loader.validate_spec(self.spec("alpha", "ghost"), self.root)
        self.assertIn("MISSING skill directory: plugins/violet-skills/skills/ghost/", warnings)


if __name__ == "__main__":
    unittest.main()
