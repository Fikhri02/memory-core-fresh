"""
generate.py — Violet Universal Spec CLI
Generate platform-native files from memory-core.yaml.

Usage:
  python adapters/generate.py codex      # Regenerate AGENTS.md
  python adapters/generate.py chatgpt    # Generate ChatGPT system prompt
  python adapters/generate.py gemini     # Generate Gemini system instruction
  python adapters/generate.py generic    # Generate universal markdown prompt
  python adapters/generate.py all        # Generate all platforms except claude
  python adapters/generate.py validate   # Validate spec without generating

  python adapters/generate.py claude --force
      Regenerates plugins/violet-skills/skills/*/SKILL.md FROM THE SPEC.
      The shipped SKILL.md files are hand-written and far more detailed than the
      spec's condensed protocols, so this OVERWRITES them with thinner versions.
      SKILL.md is the source of truth for Claude Code; the spec is the source of
      truth for every other platform. Only use --force if you know why you want it.
"""

from __future__ import annotations
import sys
from pathlib import Path

# Allow running from repo root or from adapters/
_this_dir = Path(__file__).parent
if str(_this_dir) not in sys.path:
    sys.path.insert(0, str(_this_dir))

from spec_loader import load_spec, validate_spec
import context_modules
import claude_adapter
import codex_adapter
import chatgpt_adapter
import gemini_adapter
import generic_adapter


MEMORY_ROOT = Path(__file__).parent.parent
SPEC_FILE = MEMORY_ROOT / "memory-core.yaml"

PLATFORMS = {
    "claude": claude_adapter,
    "codex": codex_adapter,
    "chatgpt": chatgpt_adapter,
    "gemini": gemini_adapter,
    "generic": generic_adapter,
}


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0)

    target = args[0].lower()

    # Load and validate spec
    if not SPEC_FILE.exists():
        print(f"ERROR: memory-core.yaml not found at {SPEC_FILE}")
        sys.exit(1)

    spec = load_spec(SPEC_FILE)
    warnings = validate_spec(spec, MEMORY_ROOT)
    warnings += context_modules.warnings_for(context_modules.read_modules(MEMORY_ROOT))

    if warnings:
        print("Spec warnings:")
        for w in warnings:
            print(f"  ! {w}")
        print()

    if target == "validate":
        if not warnings:
            mods = context_modules.read_modules(MEMORY_ROOT)
            print(
                f"memory-core.yaml v{spec.version} — validation OK "
                f"({len(spec.skills)} skills, {len(mods)} context modules)"
            )
        sys.exit(0)

    # Run adapters
    if target == "claude" and "--force" not in args:
        print("REFUSED: 'claude' would overwrite the hand-written SKILL.md files with")
        print("         condensed versions generated from the spec.")
        print()
        print("  SKILL.md is the source of truth for Claude Code.")
        print("  memory-core.yaml is the source of truth for every other platform.")
        print()
        print("  Edit skills in plugins/violet-skills/skills/<name>/SKILL.md, mirror the")
        print("  change into memory-core.yaml, then run: generate.py all")
        print()
        print("  To overwrite anyway: generate.py claude --force")
        sys.exit(1)

    if target == "all":
        targets = [p for p in PLATFORMS if p != "claude"]
    elif target in PLATFORMS:
        targets = [target]
    else:
        print(f"ERROR: Unknown platform '{target}'")
        print(f"Valid options: {', '.join(PLATFORMS)} | all | validate")
        sys.exit(1)

    results: list[str] = []
    for platform in targets:
        adapter = PLATFORMS[platform]
        out = adapter.run(spec, MEMORY_ROOT)
        if isinstance(out, list):
            results.extend(out)
        else:
            results.append(out)

    print(f"Generated {len(results)} file(s):")
    for path in results:
        print(f"  {path}")


if __name__ == "__main__":
    main()
