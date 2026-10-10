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

### 27 skills

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
| `export-package` | `"export [name]"`, `"export my profile"`, `"package feature [X]"` | Packages a project, ecosystem, feature or the profile into one labelled file — for yourself or to share |
| `import-package` | `"import [name]"`, `"import migration"`, `"migration log"` | Reads the package label and places it safely; never overwrites local edits; keeps a local ledger |
| `start-learning` | `"start learning [topic]"` | Creates a learning topic: goal, a drafted or course-mirrored study plan, a concept table |
| `continue-learning` | `"continue learning [topic]"` | Quizzes shaky concepts first, then the next objective or an exercise |
| `save-learning` | `"save learning"` | Ticks confirmed objectives, writes concept notes, appends the study log |
| `career` | `"career profile"`, `"find jobs"`, `"tailor cv for [job]"`, `"save career"` | Sourced profile, scored job search, profile-only CV tailoring, application tracker and timeline |
| `forge-skill` | `"create skill"`, `"level up"` | Proposes new skills from repeated patterns — you approve, it never self-writes |
| `log-debugging` | `"log debugging"`, `"debug log"` | Records a debugging session — symptom, root cause, dead ends — as a searchable file under `debugging/` |
| `architecture-review` | `"architecture review"` | Studies a repo's architecture and stack from file evidence, writes `notes/architecture-review/{project}.md` |
| `brain` | `"brain on [topic]"`, `"save brain"` | Accumulates theoretical thinking as topic files under `brain/` — builds nothing |
| `brain-recall` | `"what do I think about [topic]"`, `"list brain"` | Reads the brain — lookup, browse, search, project view, health. Never writes |
| `design-preferences` | any UI work, `"seed design"`, `"rank palettes"`, `"harvest design"` | Your design taste by layer (general · website · web-app · mobile): checks UI before it is shown, files rules from your reactions, seeds contrasting directions, ranks palettes and fonts 1–10 |
| `sync-memory` | `"sync setup"`, `"sync"`, `"sync status"`, `"follow project [X]"` | Keeps one memory across your laptops through a private GitHub repo: core always, projects by choice, a question only where both laptops changed the same thing |

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
  plugins/violet-skills/      27 SKILL.md files — hand-written, canonical for Claude Code
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
  brain/                      theoretical topic files by domain — builds nothing
  delegate-task/Timeline/     delegated task files by year/date
  notes/                      investigation and analysis notes
  learning/                   study topics: plan, concept notes, progress, exercises
  career/                     profile, job files, tracker, search runs, timeline
  design/                     design taste by layer, ranked palette and type libraries, seed journal
  devices/                    sync registry — one file per device: follows, plugins, MCP servers
  device/                     this machine only, never synced: id, sync settings, follows, repo paths
  migrations/                 labelled packages in transit, manifests, ledger — all local
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

## Ecosystems and Portable Knowledge

`ecosystem/` groups projects that belong together and records which domains span several of them.
Each ecosystem is a folder: `map.md` is the map, `features/*.md` are the cross-repo notes. A note is
the expensive artifact — it is the product of reading every member repo — and it is what
`continue-project` draws on to warn you that a change is almost never one-repo.

That knowledge — and the projects around it — is worth moving between machines and people.
`export-package` writes one labelled file:

```
migrations/out/{id}.v{n}.pkg.md        id: wikipetia@project · acme@ecosystem · dep@acme · profile@irfan
```

It works out the **kind** from what you name — a project, an ecosystem, one feature, or your profile
— and asks the **audience**: for you on another machine (`self`, everything travels) or for someone
else (`share`, timelines, session history and personal details stripped, with a scan for anything
that looks personal). Machine-bound data never travels; `git_origin` goes in its place.

`import-package` reads the label on the other side and places the package where its kind belongs. It
asks before writing anything, checks every path, and never overwrites something you edited locally —
a hash recorded at import tells your edits apart from the package's. Timelines merge by date. Every
export and import is a row in a local, git-ignored `migrations/ledger.md` ("migration log").

See `migrations/README.md` for the file shape and the full re-import table.

## Sync Across Devices

Packages move one piece at a time. To keep the **whole** memory in step across your own laptops,
say `sync setup`: the memory folder becomes a clone of a **private** GitHub repo you own.

- Core memory (preferences, design, career, notes, plans, brainstorms) always syncs; each
  project and ecosystem is opt-in per laptop (`follow project X`, `upload project X`)
- Session start downloads; every save uploads. Logs merge by keeping both sides; anything where
  both laptops changed the same rule, entry or section is asked, one item at a time
- Local repo paths live in `device/paths.md` on each machine, never in `General.md`
- Each device gets a permanent id and a registry file in `devices/`; `sync status` shows every
  device and which plugins or MCP servers one has that another lacks
- A new laptop: `python setup.py --sync <private repo URL> [folder]`

Personal context never reaches this framework repo: sync refuses public or framework remotes, a
pre-push hook re-checks every push, and `tests/test_framework_guard.py` fails if personal files
ever appear here. `setup.py` marks your install `context` (`.memory-core/kind`) as it personalises it.

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

"document feature X across E"  →  one cross-repo note + an Overview per member
"export X"                     →  migrations/out/X@kind.vN.pkg.md — kind inferred,
                                  audience asked, machine-bound data stripped
"import X"                     →  on the other machine: label read, paths checked,
                                  plan confirmed, local edits never overwritten
```

Feature files carry **no status field**. A file in `Development/` is active; moving it to
`Completed/` is the only completion signal. What is left and what could be picked up next lives
in each feature's `## Backlog` section, split into **Pending** and **Ready to pick up**.
