"""
gemini_adapter.py
Generates a Gemini system instruction from memory-core.yaml.
Output: outputs/gemini-system-instruction.md

Gemini supports system instructions via Google AI Studio or the API.
Format follows Gemini's preferred instruction style: direct, structured, no markdown headers
in the system field itself (use plain text with clear labels).
"""

from __future__ import annotations
from pathlib import Path
from textwrap import dedent
from spec_loader import VioletSpec, Skill, load_spec
import context_modules


# =============================================================================
# Builders
# =============================================================================

def _identity_block(spec: VioletSpec) -> str:
    identity = spec.identity
    user = identity.get("user", {})
    comm = identity.get("communication", {})
    work = " + ".join(user.get("primary_work") or [])

    return dedent(f"""\
IDENTITY:
You are {identity['name']}, a dedicated AI companion for {user['name']}.
User: {user['name']} ({user.get('email', '')}) at {user.get('company', '')}, {user.get('location', '')}.
Primary work: {work}. Git username: {user.get('git_username', '')}.
Communication style: {comm.get('tone', '')}. Short commands, iterate fast. Quiet acceptance = approval.
Wake word: "{identity['wake_word']}" — restore full memory when this is typed.
Memory root: main/main-memory.md (read for full identity and user profile).
""")


def _session_start_block(spec: VioletSpec) -> str:
    ss = spec.session_start
    time_lines = "\n".join(
        f"  {p.title()} {v['hours']}: {v['style']}"
        for p, v in ss.time_tone.items()
    )
    return dedent(f"""\
SESSION START (execute before responding to first message):
1. Read main/current-session.md — get last session recap
2. Detect time of day, adjust tone:
{time_lines}
3. Classify intent:
  - code/debug keywords (flutter, .net, bug, error) -> emphasise project context
  - design/doc keywords (guide, pptx, slide, module) -> load main/preferences.md
  - memory/arch keywords (memory-core, skill, violet, system) -> emphasise decisions
  - general -> standard brief
4. Deliver relevance-filtered brief (max 12 lines), then respond.
Suppress with: "skip brief". Re-deliver with: "brief".
""")


def _memory_files_block(spec: VioletSpec) -> str:
    lines = ["MEMORY FILES (read from attached context):"]
    for category, files in spec.memory_files.items():
        for mf in files:
            lines.append(f"  {mf.path} [{mf.load.replace('_', ' ')}] — {mf.purpose}")
    return "\n".join(lines) + "\n"


def _skills_block(spec: VioletSpec) -> str:
    lines = ["SKILLS (trigger on matching phrase, execute protocol):"]
    for name, skill in spec.skills.items():
        title = name.replace("-", " ").title()
        triggers = ", ".join(f'"{t}"' for t in skill.triggers.explicit[:3])
        if skill.triggers.passive:
            triggers += f", [{skill.triggers.passive.replace('_', ' ')}]"

        if skill.protocol:
            steps = " | ".join(s.description[:40] for s in skill.protocol[:3])
        elif "commands" in skill.raw:
            cmds = list(skill.raw["commands"].keys())
            steps = f"Commands: {', '.join(cmds)}"
        else:
            steps = "See memory files."

        lines.append(f"  [{title}] triggers: {triggers}")
        lines.append(f"    do: {steps}")
        if skill.rules:
            lines.append(f"    rule: {skill.rules[0]}")

    return "\n".join(lines) + "\n"


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
    rows = "\n".join(f"  {cmd:<30} -> {desc}" for cmd, desc in commands)
    return f"COMMANDS:\n{rows}\n"


def _footer(spec: VioletSpec) -> str:
    return (
        "---\n"
        "Generated from memory-core.yaml. "
        "Attach main/main-memory.md and main/current-session.md for full context. "
        "Run `python adapters/generate.py gemini` to regenerate.\n"
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
        _skills_block(spec),
        _commands_block(spec),
        _footer(spec),
    ]
    content = "\n".join(sections)

    out_path = memory_root / "outputs" / "gemini-system-instruction.md"
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
    print(f"Gemini adapter: wrote {out} ({char_count:,} chars)")
