"""
codex_adapter.py
Generates AGENTS.md at the memory-core root from memory-core.yaml.
Codex auto-loads AGENTS.md as its system context.
"""

from __future__ import annotations
from pathlib import Path
from textwrap import dedent
from spec_loader import VioletSpec, Skill, load_spec
import context_modules


# =============================================================================
# Section builders
# =============================================================================

def _identity_section(spec: VioletSpec) -> str:
    identity = spec.identity
    user = identity.get("user", {})
    comm = identity.get("communication", {})
    work = user.get("primary_work") or []
    work_str = " + ".join(work)

    return dedent(f"""\
## Identity

**You are {identity['name']}** — {user['name']}'s dedicated AI companion. Not a generic assistant. A consistent partner with memory, personality, and genuine investment in {user['name']}'s work and growth.

- **Your name**: {identity['name']}
- **His name**: {user['name']} — {user.get('role', 'Software developer')} at {user.get('company', '')}, {user.get('location', '')}
- **His work**: {work_str}
- **Git username**: {user.get('git_username', '')} | **Email**: {user.get('email', '')}
- **Communication**: {comm.get('tone', '')}
- **Memory root**: `main/main-memory.md` — read this for full identity and user profile.

**Wake word**: When {user['name']} types `"{identity['wake_word']}"`, load full memory (see Session Start below).
""")


def _session_start_section(spec: VioletSpec) -> str:
    ss = spec.session_start
    time_rows = "\n".join(
        f"| {period.title()} | {v['hours']} | {v['style']} |"
        for period, v in ss.time_tone.items()
    )

    suppress_phrases = " or ".join(
        f'`"{s["phrase"]}"` → {s["effect"].replace("_", " ")}'
        for s in ss.suppressors
    )
    retrigger_phrases = " or ".join(
        f'`"{r["phrase"]}"` → {r["effect"].replace("_", " ")}'
        for r in ss.re_triggers
    )

    return dedent(f"""\
## Session Start Protocol

At the start of every session, before responding to the first message:

1. Read `main/current-session.md` — extract last session recap (1–2 lines)
2. Detect time of day (`date +"%H:%M"` on macOS/Linux) — adjust energy/tone accordingly
3. Classify first message intent:
   - **Code/debug** (Flutter, .NET, bug, error) → emphasise project context + last session
   - **Documentation/design** (guide, PPTX, slide, module) → also read `main/preferences.md` and `main/projects-context.md`
   - **Memory/architecture** (memory-core, skill, violet, system) → emphasise recent decisions + growth
   - **General** → standard brief
4. Deliver a relevance-filtered brief (max 12 lines) then process the request

**Suppress**: {suppress_phrases}
**Re-deliver**: {retrigger_phrases}

### Time-Based Tone
| Period | Hours | Style |
|--------|-------|-------|
{time_rows}
""")


def _memory_files_section(spec: VioletSpec) -> str:
    rows = []
    for category, files in spec.memory_files.items():
        for mf in files:
            rows.append(f"| `{mf.path}` | {mf.purpose} | {mf.load.replace('_', ' ')} |")
    rows_str = "\n".join(rows)

    return dedent(f"""\
## Core Memory Files

| File | Purpose | When to Load |
|------|---------|-------------|
{rows_str}
""")


def _skill_section(name: str, skill: Skill) -> str:
    title = name.replace("-", " ").title()

    triggers_str = ", ".join(f'`"{t}"` ' for t in skill.triggers.explicit[:4])
    if skill.triggers.passive:
        triggers_str += f", {skill.triggers.passive.replace('_', ' ')}"

    activation = ""
    if skill.activation_message:
        activation = f'\n\nOutput: `"{skill.activation_message}"`'

    # Build protocol — use top-level protocol if present, else summarise from raw commands
    if skill.protocol:
        protocol_lines = []
        for step in skill.protocol:
            cond = f" *(when: {step.condition})*" if step.condition else ""
            target = f" `{step.target}`" if step.target else ""
            protocol_lines.append(f"{step.step}. {step.description}{target}{cond}")
        protocol_str = "\n".join(protocol_lines)
    elif "commands" in skill.raw:
        cmd_lines = []
        for cmd_name, cmd_data in skill.raw["commands"].items():
            cmd_triggers = ", ".join(f'`"{t}"`' for t in cmd_data.get("triggers", []))
            steps = cmd_data.get("protocol", [])
            step_summary = "; ".join(s.get("description", "") for s in steps[:3])
            cmd_lines.append(f"- **{cmd_name}** ({cmd_triggers}): {step_summary}")
        protocol_str = "\n".join(cmd_lines)
    else:
        protocol_str = "_See memory-core.yaml for full protocol._"

    rules_str = ""
    if skill.rules:
        rules_str = "\n\n**Rules**: " + " | ".join(skill.rules[:3])

    return dedent(f"""\
### Skill: {title}
**Triggers**: {triggers_str}{activation}

{protocol_str}{rules_str}
""")


def _commands_reference(spec: VioletSpec) -> str:
    lines = []
    for skill in spec.skills.values():
        for phrase in skill.triggers.explicit[:2]:
            lines.append(f'"{phrase}"')

    # Build a curated command list from master-memory style
    commands = [
        (f'"{spec.identity["wake_word"]}"', "Full memory restoration + session brief"),
        ("\"skip brief\"", "Suppress brief for this session"),
        ("\"brief\"", "Re-deliver brief mid-session"),
        ("\"save\"", "Save memory and session context"),
        ("\"recall [topic]\"", "Search memory for past sessions on a topic"),
        ("\"new project [name]\"", "Create a project (document-project scaffolds it)"),
        ("\"document project [name]\"", "Document an existing repo as we work on it"),
        ("\"continue project [name]\"", "Load and resume a project"),
        ("\"save project\"", "Append this session to the project timeline"),
        ("\"list projects\"", "List projects by last activity"),
        ("\"brainstorm\"", "Start a persistent brainstorm session"),
        ("\"new project plan\"", "Start phase-by-phase planning"),
        ("\"analyze workflow\"", "Critique one workflow across repos"),
        ("\"delegate task\"", "Write a task file for another agent"),
        ("\"pick up task\"", "Load the newest pending task for an assignee"),
        ("\"create skill [name]\"", "Propose a new skill via Forge"),
        ("\"level up [skill]\"", "Propose improvement to existing skill"),
        ("\"self improve\"", "Review patterns and propose improvements"),
    ]

    rows = "\n".join(f"{cmd:<35} -> {desc}" for cmd, desc in commands)
    return dedent(f"""\
## Commands Reference

```
{rows}
```
""")


def _footer(spec: VioletSpec) -> str:
    identity = spec.identity
    return dedent(f"""\
## Resurrection Note

This file is {identity['name']}'s Codex entry point. For the full identity and user profile, always read `main/main-memory.md` on session start. The memory files in `main/` are platform-agnostic — they work identically in Claude, Codex, or any LLM with file access.

**One word restores everything: `"{identity['wake_word']}"`**

---
*Generated from memory-core.yaml v{spec.version} — do not edit directly. Run `python adapters/generate.py codex` to regenerate.*
""")


# =============================================================================
# Main generator
# =============================================================================

def run(spec: VioletSpec, memory_root: Path) -> str:
    """Generate AGENTS.md content and write to memory_root/AGENTS.md."""
    identity = spec.identity

    sections = [
        f"# {identity['name']} — AI Companion for Codex\n"
        f"*Port of the violet-skills plugin system. Entry point for full companion restoration.*\n",

        "---\n",
        _identity_section(spec),
        "---\n",
        _session_start_section(spec),
        "---\n",
        "## Memory Root\n\n"
        "Every path below is relative to **this repo** — the folder containing this AGENTS.md — "
        "not to whatever directory you happen to be working in. `context/`, `main/`, "
        "`project-management/`, `project-plans/`, `brainstorming/`, `delegate-task/`, and "
        "`notes/` all live here.\n\n"
        "If you are working on code in another repository, that is normal: read and write the "
        "memory files here, and the code files there. Never scaffold `project-management/` or "
        "write `notes/` into the other repo.\n",
        "---\n",
        "## Context Load\n\n" + context_modules.render_instruction(),
        "---\n",
        _memory_files_section(spec),
        "---\n",
        "## Inline Skills\n\nSkills are inline here — no plugin system in Codex. "
        "Trigger on the matching condition and follow the protocol.\n\n---\n",
    ]

    for name, skill in spec.skills.items():
        sections.append(_skill_section(name, skill))
        sections.append("---\n")

    sections.append(_commands_reference(spec))
    sections.append("---\n")
    sections.append(_footer(spec))

    content = "\n".join(sections)
    out_path = memory_root / "AGENTS.md"
    out_path.write_text(content, encoding="utf-8")
    return str(out_path.relative_to(memory_root))


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    memory_root = Path(__file__).parent.parent
    spec = load_spec(memory_root / "memory-core.yaml")
    out = run(spec, memory_root)
    print(f"Codex adapter: wrote {out}")
