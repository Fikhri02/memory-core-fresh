# violet-skills

Auto-triggered skills for the memory-core AI companion.

## Installed Skills

| Skill | Triggers | What It Does |
|-------|---------|-------------|
| `save-memory` | "save", "save memory", "save progress", "update memory" | Persists conversation insights to Violet's memory files |
| `session-briefing` | Session start (auto), "brief", "where did we leave off" | Delivers a concise brief before processing first message |
| `manage-project` | "list projects", "show projects" | Lists projects from `project-management/`, newest activity first |
| `save-project-management` | "save project", "save project management" | Appends the session record to the project `Timeline.md` |
| `continue-project` | "continue project", "resume project", "load project" | Loads project context, dev branches, and suggests the next skill |
| `document-project` | "document project", "start documenting", "new project [name]" | Single creation path for projects; scaffolds from `_template/structure.yaml`, then builds docs progressively |
| `brainstorm` | "let's brainstorm", "continue brainstorm [name]" | Persistent, categorized brainstorming sessions |
| `project-planning` | "new project plan", "plan brainstorm [name]" | Phase-by-phase UX/Product or Software Feature planning |
| `analyze-component` | "analyze workflow", "audit feature" | Cross-project critique of a specific workflow or feature path |
| `delegate-task` | "delegate task", "assign task to [name]" | Writes a structured task file for another agent to pick up |
| `pick-up-task` | "pick up task", "what's my task" | Finds the latest pending task assigned to an agent |
| `sync-git` | "sync git", "update from git", after a merge/pull/new branch | Syncs commits into the feature Log and project Timeline, attributed per author; proposes task and completion updates |
| `manage-ecosystem` | "new ecosystem", "add to ecosystem", "list ecosystems" | Maps which projects belong together, how they relate, and which domains span several — warns before cross-project features |
| `forge-skill` | "create skill", "level up", "self improve", auto-detect pattern (3+) | Proposes new skills and level-ups based on detected patterns (human-in-the-loop) |
| *(time-aware)* | Session start (auto) | Built into main-memory — time-of-day adaptive greetings and behavior |

## Adding New Skills

1. Create a folder: `skills/[skill-name]/`
2. Create `SKILL.md` inside with YAML frontmatter + protocol
3. Done — skill auto-activates based on its `description` field

Reference `skill-format.md` for the standard structure.

## Installation

```bash
claude plugin add --local plugins/violet-skills
```

---

*Installed: 2026-04-01*
