---
name: save-project-management
description: "MUST use when user says 'save project' or 'save project management'. Auto-suggest after any session where project-related work was done (feature implementation, project-management file changes, commits, component/design updates, or an investigation). Appends the session record to the active project's Timeline.md. Bare 'save' belongs to save-memory."
---

# Save Project Management — Skill Plugin
*Updates the project Timeline.md with a brief record of what changed this session.*

## Activation

When this skill activates, output:

`"_(save-project-management activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "save project"** | ACTIVE |
| **User says "save project management"** | ACTIVE |
| **User says "save" (bare)** | DORMANT — belongs to save-memory, which will suggest this skill |
| **Auto-suggest after project work detected** | SUGGEST |
| **No project work done this session** | DORMANT |

## Auto-Suggest Rule

Monitor the conversation for project-related work signals:
- Feature file created, updated, or completed
- Code implemented, committed, or reviewed
- Project-management structure changed (components, design, timeline, folders)
- `continue-project` skill was used this session
- An **investigation** was run — read-only analysis that produced or updated a `notes/` file

When any signal is detected, after the work is done (or when the user says "save"), prompt:

> "Project work was done this session — want to update the timeline? (`save project management`)"

Only suggest once per session. Do not suggest if the user already ran this skill.

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### Step 1: Check for Project Work

- [ ] Review the conversation for project-related changes (features, code, project-management files, commits)
- [ ] If no project work detected → say: "No project changes detected this session. Nothing to save." → stop

### Step 2: Identify Active Project

- [ ] Check `main/current-session.md` for the active project name
- [ ] If unclear or multiple projects were worked on → ask: "Which project should I update the timeline for? [list candidates]"

### Step 3: Find Timeline File

- [ ] Locate `project-management/{name}/Timeline.md`
- [ ] If not found → warn: "Timeline.md not found for {name}. Create it first with `new project` or manually." → stop

### Step 4: Collect Changes

Summarise the session's work into brief bullet points, covering both:

- **Project management changes** — feature files created/updated/completed, backlog items added or cleared, components added, design updated, structure changes
- **Code changes** — features implemented, files modified, commits made (include hash if available)
- **Investigation findings** — for read-only analysis sessions, one line naming what was investigated
  and the `notes/{slug}.md` file that holds the detail

Rules for bullets:
- One line per distinct change
- Start with a verb (Added, Updated, Implemented, Migrated, Fixed, Created, Committed)
- No sub-bullets — keep it flat
- Maximum 10 bullets per entry

### Step 5: Write Timeline Entry

- [ ] Read `project-management/{name}/Timeline.md`
- [ ] If today's date section (`## YYYY-MM-DD`) already exists → append bullets to it
- [ ] If not → add new section at the top (below the file header):
  ```
  ## YYYY-MM-DD
  - bullet 1
  - bullet 2
  ```
- [ ] Write updated file

### Step 6: Confirm

- [ ] Report: "Saved **{project-name}** — timeline updated."

## Rules

1. Only run if project-related work actually happened — do not create empty or near-empty entries
2. Keep bullets brief — one line, verb-first, no padding
3. Append to today's section if it exists; never overwrite existing entries
4. Always ask which project if ambiguous — never assume

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| `Timeline.md` missing | Warn and stop — do not create it silently |
| Today's section already exists | Append new bullets below existing ones |
| Multiple projects worked on | Ask which project, run once per project if user wants both |
| No commit hash available | Skip hash — just describe the work |

## Level History

- **Lv.3** — Current behaviour, as described in the Protocol and Rules above
