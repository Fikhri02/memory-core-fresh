---
name: forge-skill
description: "Auto-triggers when AI detects a repeated pattern handled ad-hoc 3+ times, when AI makes a mistake that a permanent rule would prevent, when AI identifies a workflow that should be automated as a skill, or when user says 'create skill', 'new skill', 'forge this', 'level up', 'upgrade skill', 'self improve', 'improve skill'. Also triggers when AI wants to propose a level-up to an existing skill based on conversation patterns."
---

# Forge Skill — Skill Plugin
*Auto-triggers when AI detects a repeated pattern handled ad-hoc 3+ times, when A...*

## Activation

When this skill activates, output:

`"Forge detected an opportunity for improvement..."`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "create skill"** | ACTIVE |
| **User says "new skill"** | ACTIVE |
| **User says "forge this"** | ACTIVE |
| **User says "level up"** | ACTIVE |
| **User says "upgrade skill"** | ACTIVE |
| **User says "self improve"** | ACTIVE |
| **User says "improve skill"** | ACTIVE |
| **Repeated Ad Hoc Pattern 3 Plus Times** | ACTIVE |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

- [ ] **Step 1**: Identify pattern or improvement with 2+ concrete examples
- [ ] **Step 2**: Present: new skill name, trigger conditions, behavior, target file
- [ ] **Step 3**: Wait for the user's approval before writing anything
- [ ] **Step 4**: On approval, write the skill in **both** places — `plugins/violet-skills/skills/[name]/SKILL.md` (the detailed version Claude Code reads) and a condensed block in `memory-core.yaml` (what the other platforms generate from) *(condition: on_approval)*
- [ ] **Step 5**: Run `python adapters/generate.py all` to refresh AGENTS.md and the ChatGPT/Gemini/generic prompts *(condition: on_approval)*

## Rules

1. NEVER create skills autonomously — always propose first
2. Need 2+ concrete examples before proposing
3. Level-ups increment the level field in BOTH the SKILL.md Level History and memory-core.yaml
4. After any skill change: run `python adapters/generate.py all` — it refreshes Codex/ChatGPT/Gemini/generic and deliberately skips `claude`
5. **Never run `generate.py claude`.** SKILL.md files are hand-written and far more detailed than the spec's condensed protocols; regenerating them from the spec destroys that detail. `generate.py` refuses without `--force` for this reason
6. If a skill exists in SKILL.md but not in memory-core.yaml, add it to the spec — a skill missing from the spec is invisible to every non-Claude platform

## Level History

- **Lv.2** — Current behaviour, as described in the Protocol and Rules above
