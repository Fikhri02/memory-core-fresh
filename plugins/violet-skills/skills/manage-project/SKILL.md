---
name: manage-project
description: "Auto-triggers on 'list projects' or 'show projects'. Lists every project tracked under project-management/. For creating a project use document-project ('new project [name]' routes there). For saving session progress use save-project-management. For resuming or loading a project to continue work, use continue-project."
---

# Manage Project — Skill Plugin
*Lists the projects tracked in `project-management/`.*

## Activation

When this skill activates, output:

`"_(activates silently)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "list projects"** | ACTIVE |
| **User says "show projects"** | ACTIVE |
| **User says "new project"** | DORMANT — defer to document-project |
| **User says "create project"** | DORMANT — defer to document-project |
| **User says "save project"** | DORMANT — defer to save-project-management |
| **User says "load project"** | DORMANT — defer to continue-project |
| **User says "resume project"** | DORMANT — defer to continue-project |
| **User says "open project"** | DORMANT — defer to continue-project |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### list — List all projects

Triggers: "list projects", "show projects"

- [ ] **Step 1**: List every directory under `project-management/`, skipping names that start with `_`
      (`_template`, `_project-structure-memory` are infrastructure, not projects)
- [ ] **Step 2**: For each project, scan **every** `## YYYY-MM-DD` header in `Timeline.md` and take the
      **latest** date — that is its last activity. Never take the first header: some timelines are
      written oldest-first and some newest-first, so position does not imply recency. A header may
      carry a suffix (`## 2026-04-17 (session 2)`) — match the leading date and ignore the rest
- [ ] **Step 3**: Count feature files under `Features/*/Development/` (active) and `Features/*/Completed/` (done)
- [ ] **Step 4**: Present newest-activity-first:

  ```
  {project-name}    last active {YYYY-MM-DD}    {N} active · {M} completed
  ```

- [ ] **Step 5**: Flag anything with no timeline activity in over 60 days as `(stale)`

## Rules

1. `project-management/` is the only project index — there is no separate registry file to read or write
2. Never create or modify project folders here — creation belongs to `document-project`
3. Sort by last activity, not alphabetically — the useful question is "what was I last working on"
4. **Last activity is the newest date in `Timeline.md`, never the topmost one.** Timeline ordering is
   not consistent across projects, and reading position as recency reports a project's birth date as
   its last activity

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| `project-management/` missing | Inform user, suggest `document project [name]` |
| Project folder has no `Timeline.md` | Show it with `last active —` rather than skipping it |
| `Timeline.md` has no `## YYYY-MM-DD` headers | Show `last active —`, same as a missing `Timeline.md` |
| Project folder has no `Features/` yet | Show `0 active · 0 completed` |

## Level History

- **Lv.7** — Current behaviour, as described in the Protocol and Rules above
