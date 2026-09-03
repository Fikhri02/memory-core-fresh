# Adapters

Spec-to-platform generators. Each adapter reads `memory-core.yaml` and writes the file a
particular platform needs to behave like your companion.

Claude Code does not need one. It reads `plugins/violet-skills/skills/*/SKILL.md` directly.

---

## The files

| File | Role |
|------|------|
| `spec_loader.py` | Parses `memory-core.yaml` into typed dataclasses (`VioletSpec`, `Skill`, `ProtocolStep`, `MemoryFile`). Every adapter starts here. |
| `context_modules.py` | Reads and validates `context/*.md`. **Shared with the MCP server** — see the warning below. |
| `generate.py` | The CLI. Loads the spec, validates, dispatches to adapters. |
| `codex_adapter.py` | → `AGENTS.md` at the repo root |
| `chatgpt_adapter.py` | → `outputs/chatgpt-system-prompt.md` |
| `gemini_adapter.py` | → `outputs/gemini-system-instruction.md` |
| `generic_adapter.py` | → `outputs/generic-prompt.md` |
| `claude_adapter.py` | → `SKILL.md` files. **Refuses to run without `--force`.** |

## Usage

```bash
python adapters/generate.py validate    # parse and check, write nothing
python adapters/generate.py all         # every platform except claude
python adapters/generate.py codex       # just AGENTS.md
```

`validate` reports spec warnings *and* context-module warnings, then exits 0. Run it after any
edit to `memory-core.yaml`.

## Two sources of truth

- **`SKILL.md` is canonical for Claude Code.** Hand-written and detailed — `continue-project`
  alone runs past 200 lines of protocol.
- **`memory-core.yaml` is canonical for every other platform.** It holds a condensed version of
  each skill.

`generate.py claude` would overwrite the detailed files with the spec's thin versions, so it
**refuses unless you pass `--force`**. That guard exists because the mistake is silent and
destructive: you would not notice until a skill stopped working.

**When you change a skill, change it in both places**, then run `generate.py all`.

## The drift this folder is prone to

A skill that exists as `SKILL.md` but not in the spec is deleted from `AGENTS.md` the next time
`generate.py codex` runs — silently, with a success message. `health_check` in `mcp-spike/`
catches exactly this (`skill_missing_from_spec`, severity high). Run it before generating.

## A rule for anything added here

`context_modules.py` is imported by both `generate.py` and `mcp-spike/server.py`. That is
deliberate: the folder-scan path and the tool path must apply identical parsing rules, or a
module that loads under Claude Code silently fails to load under Codex.

**Any new logic shared between an adapter and a tool must live in one module and be imported by
both.** Two implementations of the same rule is the failure this layer exists to prevent.

## Dependency

`pyyaml` — the only third-party requirement in the project. `pip install pyyaml`.
