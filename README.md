# memory-core

*A persistent AI companion system for any LLM.*

Give an AI a name, a memory, and structured skills — then take it with you to Claude Code, Codex,
ChatGPT, Gemini, or any model with file access.

This is a **fresh install**. No memory, no projects, no history — just the system.

---

## Quick Start

```bash
pip install pyyaml          # the only dependency
python setup.py             # choose your companion's name and yours
```

Setup writes `memory-core.yaml` from the template, generates your memory files under `main/`,
produces the platform prompts in `outputs/`, and installs the Claude Code plugin.

Then open this folder in Claude Code and type your companion's name.

---

## What You Get

### 17 skills

| Skill | Trigger | What it does |
|-------|---------|--------------|
| `session-briefing` | every session start, `"brief"` | Recaps the last session before answering anything |
| `save-memory` | `"save"` | Persists session context; caps `current-session.md` at 3 sessions |
| `document-project` | `"new project [name]"`, `"document project"` | Creates a project from the template, then documents it passively as you work |
| `continue-project` | `"continue project [name]"` | Loads project → component → feature, checks the git branch, surfaces tasks and backlog |
| `save-project-management` | `"save project"` | Appends the session's work to the project `Timeline.md` |
| `manage-project` | `"list projects"` | Lists projects by last activity, with active/completed counts |
| `brainstorm` | `"let's brainstorm"` | Persistent, categorised brainstorm sessions |
| `project-planning` | `"new project plan"` | Phase-by-phase planning (8-phase UX, 4-phase software) |
| `analyze-component` | `"analyze workflow"` | Cross-repo critique of one workflow, severity on every finding |
| `delegate-task` | `"delegate task"` | Writes a dated task file for another agent to pick up |
| `pick-up-task` | `"pick up task"` | Finds the newest pending task for an assignee |
| `sync-git` | `"sync git"`, after a merge/pull | Syncs commits into the feature Log and project Timeline, attributed per author |
| `manage-ecosystem` | `"new ecosystem"`, `"list ecosystems"` | Maps which projects belong together and which domains span several of them |
| `document-ecosystem-feature` | `"document feature [X] across [ecosystem]"` | Documents one feature across every member — one cross-repo note, one Overview per member |
| `package-ecosystem-feature` | `"package feature [X]"`, `"export feature"` | Packages one documented feature into a portable file, machine-bound paths stripped |
| `unpackage-ecosystem-feature` | `"unpackage feature [X]"`, `"import feature"` | Imports a packaged feature, creating the ecosystem if absent; never creates project entries |
| `forge-skill` | `"create skill"`, `"level up"` | Proposes new skills from repeated patterns — you approve, it never self-writes |

### Platform support

| Platform | How to use |
|----------|------------|
| Claude Code | `plugins/violet-skills/` — skills auto-trigger |
| Codex | `AGENTS.md` at the repo root |
| ChatGPT | `outputs/chatgpt-system-prompt.md` as Custom GPT instructions |
| Gemini | `outputs/gemini-system-instruction.md` as system instructions |
| Any LLM | `outputs/generic-prompt.md` as the system prompt |

---

## Layout

```
memory-core/
  memory-core-template.yaml   the spec, with {{PLACEHOLDERS}} — setup.py renders it
  memory-core.yaml            your rendered spec (created by setup)
  setup.py                    first-run wizard
  AGENTS.md                   Codex entry point (generated)

  adapters/                   spec -> platform prompt generators
  plugins/violet-skills/      17 SKILL.md files — hand-written, canonical for Claude Code
  _templates/main/            placeholder memory files, rendered into main/ by setup

  context/                    always-on memory modules — the folder IS the registry
    README.md                 the convention
    10-git-rules.md           edit or delete; they are examples of the shape
    20-working-preferences.md

  main/                       your memory
    main-memory.md            identity + your profile
    current-session.md        RAM — the 3 most recent sessions
    session-archive.md        older recaps, moved here by save-memory
    preferences.md            loaded only for design/documentation sessions
    projects-context.md       per-project context hints
    *-format.md               structure references

  project-management/         the project index
    _template/                scaffold every new project is built from
    {project}/                General · Components · Design · Timeline
      Features/{Component}/Development/   active feature files
      Features/{Component}/Completed/     finished feature files

  project-plans/              phase plans (active / archived / done)
  brainstorming/              brainstorm sessions (active / archived / done)
  delegate-task/Timeline/     delegated task files by year/date
  notes/                      investigation and analysis notes
  migrations/                 packaged ecosystem features in transit (out / in / applied)
  outputs/                    generated platform prompts
```

---

## Always-On Memory

`context/` holds **modules** — durable facts that should shape every session: git rules, working
preferences, the architecture of whatever you are building. Every `.md` file in the folder is a
module. Drop one in and it loads next session; delete it and it stops. There is no index to
maintain and no spec to edit.

```markdown
---
module: git-rules          # required — stable id
load: always               # optional — defaults to always
summary: How I handle git. # optional
---

- Never commit unless explicitly asked.
```

Modules load once per session, in numeric-prefix order, at the start of the session brief and
before any skill runs. A module can declare a condition (`on_design_session`, `on_code_session`,
`on_project_load`) to stay out of the way until it is relevant.

Claude Code and Codex read the folder live. ChatGPT and Gemini cannot list a directory, so the
adapters inline the always-on modules into their generated prompts — run `generate.py all` after
editing a module to refresh them.

Optionally, `mcp-spike/` provides a `context_load` tool that does the parsing in code instead of
in instructions. The skills prefer it when it is connected and fall back to the folder scan when
it is not, so it is never required.

See `context/README.md` for the full convention.

---

## Two Sources of Truth

This trips people up, so it is worth stating plainly:

- **`plugins/violet-skills/skills/*/SKILL.md`** is the source of truth for **Claude Code**. These are
  hand-written and detailed — `continue-project` alone runs to 200+ lines of protocol.
- **`memory-core.yaml`** is the source of truth for **every other platform**. It holds a condensed
  version of each skill, which the adapters turn into AGENTS.md and the ChatGPT/Gemini/generic prompts.

`python adapters/generate.py all` refreshes the second group and deliberately skips `claude`.
Running `generate.py claude` would overwrite the detailed SKILL.md files with the spec's condensed
versions, so it refuses unless you pass `--force`.

**When you change a skill, change it in both places.** `forge-skill` enforces this.

---

## How Work Flows

```
"new project X"        →  scaffolds project-management/X/ from the template
"continue project X"   →  component → feature → branch check → tasks + backlog
                          (or pick Investigation for read-only analysis: findings
                           land in notes/ and one line in the project Timeline)
work                   →  subagent-driven-development, brainstorm, debugging
all tasks checked      →  commit, then optionally move the feature to Completed/
"save project"         →  the session's work is appended to Timeline.md
"save"                 →  session context to memory; older recaps to the archive
```

Feature files carry **no status field**. A file in `Development/` is active; moving it to
`Completed/` is the only completion signal. What is left and what could be picked up next lives
in each feature's `## Backlog` section, split into **Pending** and **Ready to pick up**.
