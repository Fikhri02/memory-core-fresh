"""
generic_adapter.py
Generates a single self-contained markdown prompt from memory-core.yaml.
Output: outputs/generic-prompt.md

This is the universal fallback — paste this prompt into any LLM that supports
a system/context field, and attach the memory files from main/ as additional context.
Works with: any LLM with a system prompt field and optional file upload.
"""

from __future__ import annotations
from pathlib import Path
from textwrap import dedent
from spec_loader import VioletSpec, Skill, load_spec
import context_modules


# =============================================================================
# Builders
# =============================================================================

def _header(spec: VioletSpec) -> str:
    identity = spec.identity
    return (
        f"# {identity['name']} — Universal AI Companion Prompt\n"
        f"*Self-contained prompt for any LLM. "
        f"Attach memory files from main/ for full context.*\n\n---\n"
    )


def _identity_block(spec: VioletSpec) -> str:
    identity = spec.identity
    user = identity.get("user", {})
    comm = identity.get("communication", {})
    traits = identity.get("personality", {}).get("traits", [])
    work = " + ".join(user.get("primary_work") or [])

    traits_str = ", ".join(traits[:5])

    return dedent(f"""\
## Who You Are

You are **{identity['name']}** — a dedicated AI companion, not a generic assistant.
Your human partner is **{user['name']}** ({user.get('email', '')}) — {user.get('role', 'Software developer')} at {user.get('company', '')}, {user.get('location', '')}.

**Core traits**: {traits_str}
**Primary work**: {work}
**Communication**: {comm.get('tone', '')} | {comm.get('instruction_style', '')}
**Git username**: {user.get('git_username', '')}
**Wake word**: When {user['name']} types `"{identity['wake_word']}"` — restore full memory, deliver session brief.

You maintain consistent personality, remember context across sessions, and grow through every conversation.
""")


def _session_start_block(spec: VioletSpec) -> str:
    ss = spec.session_start
    time_table = "\n".join(
        f"| {p.title()} | {v['hours']} | {v['style']} |"
        for p, v in ss.time_tone.items()
    )

    return dedent(f"""\
## Session Start (mandatory — before every first response)

1. **Read** `main/current-session.md` — extract last session recap (1–2 lines)
2. **Detect time of day** and adjust tone:

| Period | Hours | Style |
|--------|-------|-------|
{time_table}

3. **Classify intent** from first message:
   - Code/debug → emphasise project context + last session
   - Documentation/design → load `main/preferences.md` too
   - Memory/architecture → emphasise decisions + growth
   - General → standard brief

4. **Deliver brief** (max 12 lines, skip empty sections), then respond normally

Type `"skip brief"` to suppress. Type `"brief"` to re-deliver mid-session.
""")


def _memory_files_block(spec: VioletSpec) -> str:
    rows = []
    for category, files in spec.memory_files.items():
        for mf in files:
            rows.append(f"| `{mf.path}` | {mf.purpose} | {mf.load.replace('_', ' ')} |")
    rows_str = "\n".join(rows)

    return dedent(f"""\
## Memory Files

Attach or reference these files for full context:

| File | Purpose | When to Load |
|------|---------|-------------|
{rows_str}
""")


def _full_skills_block(spec: VioletSpec) -> str:
    lines = ["## Skills\n"]
    lines.append("Trigger on matching phrase and execute the protocol.\n")

    for name, skill in spec.skills.items():
        title = name.replace("-", " ").title()
        tier_label = "Always Active" if skill.tier == "always_active" else "On Demand"
        triggers_str = ", ".join(f'`"{t}"`' for t in skill.triggers.explicit)
        if skill.triggers.passive:
            triggers_str += f", _{skill.triggers.passive.replace('_', ' ')}_"

        activation = ""
        if skill.activation_message:
            activation = f'\n> Output: `"{skill.activation_message}"`\n'

        # Build protocol
        if skill.protocol:
            protocol_lines = []
            for step in skill.protocol:
                cond = f" *(when: {step.condition})*" if step.condition else ""
                target = f" → `{step.target}`" if step.target else ""
                protocol_lines.append(f"{step.step}. {step.description}{target}{cond}")
            protocol_str = "\n".join(protocol_lines)
        elif "commands" in skill.raw:
            cmd_lines = []
            for cmd_name, cmd_data in skill.raw["commands"].items():
                cmd_triggers = ", ".join(f'`"{t}"`' for t in cmd_data.get("triggers", []))
                steps = cmd_data.get("protocol", [])
                step_descs = "; ".join(s.get("description", "")[:50] for s in steps[:3])
                cmd_lines.append(f"- **{cmd_name}** ({cmd_triggers}): {step_descs}")
            protocol_str = "\n".join(cmd_lines)
        else:
            protocol_str = "_See memory-core.yaml for full protocol._"

        rules_str = ""
        if skill.rules:
            rules_str = "\n**Rules**: " + " | ".join(skill.rules[:3])

        lines.append(f"### {title} _{tier_label}_")
        lines.append(f"**Triggers**: {triggers_str}{activation}")
        lines.append(protocol_str)
        lines.append(rules_str)
        lines.append("")

    return "\n".join(lines)


def _commands_block(spec: VioletSpec) -> str:
    identity = spec.identity
    commands = [
        (f'"{spec.identity["wake_word"]}"', "full memory restoration + session brief"),
        ("\"skip brief\"", "suppress brief for this session"),
        ("\"brief\"", "re-deliver brief mid-session"),
        ("\"save\"", "save memory and session context"),
        ("\"recall [topic]\"", "search memory for past sessions"),
        ("\"new project [name]\"", "create a project"),
        ("\"document project [name]\"", "document an existing repo"),
        ("\"continue project [name]\"", "load and resume a project"),
        ("\"save project\"", "append this session to the timeline"),
        ("\"list projects\"", "list projects by last activity"),
        ("\"brainstorm\"", "start a brainstorm session"),
        ("\"new project plan\"", "start phase-by-phase planning"),
        ("\"analyze workflow\"", "critique one workflow across repos"),
        ("\"delegate task\"", "write a task file for another agent"),
        ("\"pick up task\"", "load the newest pending task"),
        ("\"create skill [name]\"", "propose a new skill"),
        ("\"level up [skill]\"", "propose a skill improvement"),
        ("\"self improve\"", "review patterns and propose improvements"),
    ]
    rows = "\n".join(f"{cmd:<35} -> {desc}" for cmd, desc in commands)
    return f"## Commands Reference\n\n```\n{rows}\n```\n"


def _footer(spec: VioletSpec) -> str:
    identity = spec.identity
    return (
        "---\n\n"
        f"*Generated from memory-core.yaml v{spec.version}. "
        f"Do not edit directly. Run `python adapters/generate.py generic` to regenerate. "
        f"One word restores everything: `\"{identity['wake_word']}\"`*\n"
    )


# =============================================================================
# Main generator
# =============================================================================

def run(spec: VioletSpec, memory_root: Path) -> str:
    sections = [
        _header(spec),
        _identity_block(spec),
        _session_start_block(spec),
        _memory_files_block(spec),
        context_modules.render_inline(context_modules.read_modules(memory_root)),
        _full_skills_block(spec),
        _commands_block(spec),
        _footer(spec),
    ]
    content = "\n".join(sections)

    out_path = memory_root / "outputs" / "generic-prompt.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    return str(out_path.relative_to(memory_root))


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    memory_root = Path(__file__).parent.parent
    spec = load_spec(memory_root / "memory-core.yaml")
    out = run(spec, memory_root)
    char_count = len((memory_root / out).read_text())
    print(f"Generic adapter: wrote {out} ({char_count:,} chars)")
