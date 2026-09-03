# Context Modules

Always-on memory. Every `.md` file in this folder is a **module** that loads automatically at the
start of a session and whenever a memory-core skill runs.

**The folder is the registry.** Drop a file in and it loads next session. Delete it and it stops.
There is no index to update and no spec to edit.

---

## Writing a module

```markdown
---
module: git-rules          # required — stable id, independent of the filename
load: always               # optional — defaults to always
summary: How I handle git. # optional — shown in the load report
---

- Never commit unless explicitly asked.
- Never commit to `main`; branch first.
```

The **numeric prefix sets load order** — lower loads first, so foundational rules land before
specific ones. Prefixes are spaced by 10 to leave room for insertion.

`README.md` is skipped. It documents the folder; it is not a module.

## How they get loaded

Two paths, same result:

- **`context_load` tool** — if the `memory-core-context` MCP server is registered, the skills call
  it. Parsing, ordering, and condition resolution happen in code rather than in instructions.
- **Folder scan** — if the tool is not available (Codex, ChatGPT, or a clone with no server
  registered), the skills read the folder directly, following the rules below.

The tool is an optimisation. Everything here works without it.

## Load conditions

| `load:` | Loads when |
|---------|-----------|
| `always` | Every session. The default — omit the field and you get this. |
| `on_design_session` | The first message classifies as documentation / design / UI |
| `on_code_session` | The first message classifies as code / debug |
| `on_project_load` | A project is loaded via `continue-project` |

Conditional modules resolve in two phases, because loading starts before the session type is
known. `always` modules load immediately; conditional ones are noted and their bodies read later,
once intent has been classified (or once a project is resolved).

A module with no frontmatter still loads, treated as `always`, and is reported as a warning. An
unrecognised `load:` value does the same — a typo makes a module too visible rather than
silently invisible.

## What belongs here

Durable facts that should shape how the AI works with you, every session:

- Rules — git habits, review standards, what never to do without asking
- Preferences — output formats, naming, tone, what "done" means to you
- Architecture — how your main systems fit together, so it does not have to be re-explained

## What does not belong here

- **Session state** — that is `main/current-session.md`, written by `save-memory`
- **Project detail** — that is `project-management/{name}/`, loaded by `continue-project`
- **Anything that changes weekly** — a module is read every session, so churn is expensive
- **Long reference documents** — link to them from a module instead of pasting them in

Nothing writes here automatically. Modules are added and edited deliberately.

## A note for Claude Code users

Claude Code has its own auto-memory (a `memory/` folder with a `MEMORY.md` index) that it manages
itself. That store is Claude-only — Codex, ChatGPT, and Gemini never see it.

This folder is the platform-independent equivalent. If a fact should reach every platform, it
belongs here. Some facts will end up in both places; that is fine, as long as you know which is
which.

## Starter modules

`10-git-rules.md` and `20-working-preferences.md` ship with sensible defaults. **Edit them to
match how you actually work, or delete them** — they are examples of the shape, not rules you
are stuck with.
