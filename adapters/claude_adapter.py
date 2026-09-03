"""
claude_adapter.py
Generates Claude Code SKILL.md plugin files from memory-core.yaml.
Output: plugins/violet-skills/skills/{skill-name}/SKILL.md
"""

from __future__ import annotations
from pathlib import Path
from textwrap import dedent, indent
from spec_loader import VioletSpec, Skill, load_spec


# =============================================================================
# Helpers
# =============================================================================

def _context_guard_rows(skill: Skill) -> str:
    rows = []
    for phrase in skill.triggers.explicit:
        rows.append(f"| **User says \"{phrase}\"** | ACTIVE |")
    if skill.triggers.passive:
        rows.append(f"| **{skill.triggers.passive.replace('_', ' ').title()}** | ACTIVE |")
    rows.append("| **Mid-conversation (no trigger context)** | DORMANT |")
    return "\n".join(rows)


def _protocol_checklist(skill: Skill) -> str:
    if not skill.protocol:
        return "_See sub-command protocols in the full skill definition._"
    lines = []
    for step in skill.protocol:
        cond = f" *(condition: {step.condition})*" if step.condition else ""
        target = f" — `{step.target}`" if step.target else ""
        lines.append(f"- [ ] **Step {step.step}**: {step.description}{target}{cond}")
    return "\n".join(lines)


def _level_history(skill: Skill) -> str:
    if not skill.level_history:
        return f"- **Lv.1** — Base implementation"
    return "\n".join(
        f"- **Lv.{lvl}** — {desc}"
        for lvl, desc in sorted(skill.level_history.items())
    )


def _rules_block(skill: Skill) -> str:
    if not skill.rules:
        return "_No explicit rules defined._"
    return "\n".join(f"{i+1}. {rule}" for i, rule in enumerate(skill.rules))


def _output_format_block(skill: Skill) -> str:
    if not skill.output_format:
        return ""
    return dedent(f"""
## Output Format

```
{skill.output_format.strip()}
```
""").strip()


# =============================================================================
# Main generator
# =============================================================================

def generate_skill_md(skill: Skill) -> str:
    activation = skill.activation_message or "_(activates silently)_"

    output_section = _output_format_block(skill)
    output_block = f"\n\n{output_section}" if output_section else ""

    return dedent(f"""\
---
name: {skill.name}
description: "{skill.description}"
---

# {skill.name.replace('-', ' ').title()} — Skill Plugin
*{skill.description[:80]}{"..." if len(skill.description) > 80 else ""}*

## Activation

When this skill activates, output:

`"{activation}"`

## Context Guard

| Context | Status |
|---------|--------|
{_context_guard_rows(skill)}

## Protocol

{_protocol_checklist(skill)}

## Rules

{_rules_block(skill)}{output_block}

## Level History

{_level_history(skill)}
""")


def run(spec: VioletSpec, memory_root: Path) -> list[str]:
    """
    Generate all SKILL.md files from the spec.
    Returns a list of paths written.
    """
    written: list[str] = []
    skills_root = memory_root / "plugins" / "violet-skills" / "skills"

    for name, skill in spec.skills.items():
        skill_dir = skills_root / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        content = generate_skill_md(skill)
        out_path = skill_dir / "SKILL.md"
        out_path.write_text(content, encoding="utf-8")
        written.append(str(out_path.relative_to(memory_root)))

    return written


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    memory_root = Path(__file__).parent.parent
    spec = load_spec(memory_root / "memory-core.yaml")
    written = run(spec, memory_root)
    print(f"Claude adapter: wrote {len(written)} SKILL.md files")
    for path in written:
        print(f"  {path}")
