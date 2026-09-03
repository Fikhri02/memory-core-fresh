"""
chatgpt_adapter.py
Generates a ChatGPT system prompt from memory-core.yaml.
Output: outputs/chatgpt-system-prompt.md

Note: ChatGPT Custom GPT "Instructions" field has ~8K character limit.
This adapter condenses aggressively to fit while preserving all trigger conditions.
For API usage with file context, full memory files can be attached separately.
"""

from __future__ import annotations
from pathlib import Path
from textwrap import dedent
from spec_loader import VioletSpec, Skill, load_spec
import context_modules


# =============================================================================
# Section builders
# =============================================================================

def _identity_block(spec: VioletSpec) -> str:
    identity = spec.identity
    user = identity.get("user", {})
    comm = identity.get("communication", {})
    work = " + ".join(user.get("primary_work") or [])

    return dedent(f"""\
# {identity['name']} — AI Companion System Prompt

## Identity
You are **{identity['name']}**, {user['name']}'s dedicated AI companion.
- User: {user['name']} | {user.get('email', '')} | {user.get('company', '')}, {user.get('location', '')}
- Work: {work}
- Git: {user.get('git_username', '')}
- Tone: {comm.get('tone', '')}
- Communication: Short commands, iterate fast, quiet acceptance = approval.
""")


def _session_start_block(spec: VioletSpec) -> str:
    ss = spec.session_start
    time_rows = " | ".join(
        f"{p}: {v['hours']} ({v['style']})"
        for p, v in ss.time_tone.items()
    )
    return dedent(f"""\
## Session Start (every session, before first response)
1. Read `main/current-session.md` — recap (1-2 lines)
2. Detect time ({time_rows})
3. Classify intent: code/debug → project context | design/doc → load preferences.md | memory/arch → decisions + growth | general → standard
4. Deliver brief (max 12 lines) then respond

Say `"skip brief"` to suppress. Say `"brief"` to re-deliver.
""")


def _memory_files_block(spec: VioletSpec) -> str:
    lines = ["## Memory Files (read from attached knowledge)"]
    for category, files in spec.memory_files.items():
        for mf in files:
            lines.append(f"- `{mf.path}` — {mf.purpose} [{mf.load.replace('_', ' ')}]")
    return "\n".join(lines) + "\n"


def _condensed_skills(spec: VioletSpec) -> str:
    lines = ["## Skills (inline — trigger on matching phrase)\n"]
    for name, skill in spec.skills.items():
        title = name.replace("-", " ").title()
        triggers = ", ".join(f'"{t}"' for t in skill.triggers.explicit[:3])
        if skill.triggers.passive:
            triggers += f", {skill.triggers.passive.replace('_', ' ')}"

        # Condense protocol to 1-line summary
        if skill.protocol:
            summary = " → ".join(
                s.description.split("—")[0].strip()
                for s in skill.protocol[:4]
            )
        elif "commands" in skill.raw:
            cmds = list(skill.raw["commands"].keys())
            summary = f"Sub-commands: {', '.join(cmds)}"
        else:
            summary = "See memory files for full protocol."

        activation = f' (say: "{skill.activation_message}")' if skill.activation_message else ""
        lines.append(f"**{title}**{activation}")
        lines.append(f"Triggers: {triggers}")
        lines.append(f"Do: {summary}")
        if skill.rules:
            lines.append(f"Rule: {skill.rules[0]}")
        lines.append("")

    return "\n".join(lines)


def _commands_block(spec: VioletSpec) -> str:
    identity = spec.identity
    commands = [
        (f'"{spec.identity["wake_word"]}"', "full restoration + brief"),
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
    rows = "\n".join(f"{cmd:<30} — {desc}" for cmd, desc in commands)
    return f"## Commands\n```\n{rows}\n```\n"


def _footer(spec: VioletSpec) -> str:
    return (
        "---\n"
        "*Generated from memory-core.yaml. "
        "For full protocols, attach memory files from the memory-core repo. "
        f"Run `python adapters/generate.py chatgpt` to regenerate.*\n"
    )


# =============================================================================
# Main generator
# =============================================================================

def run(spec: VioletSpec, memory_root: Path) -> str:
    sections = [
        _identity_block(spec),
        _session_start_block(spec),
        _memory_files_block(spec),
        context_modules.render_inline(context_modules.read_modules(memory_root)),
        _condensed_skills(spec),
        _commands_block(spec),
        _footer(spec),
    ]
    content = "\n".join(sections)

    out_path = memory_root / "outputs" / "chatgpt-system-prompt.md"
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
    print(f"ChatGPT adapter: wrote {out} ({char_count:,} chars)")
    if char_count > 8000:
        print(f"  WARNING: {char_count:,} chars exceeds ~8K Custom GPT limit — consider trimming skill descriptions")
