---
name: delegate-task
description: Use when user says 'delegate task', 'delegate-task', 'assign task to', 'give task to [name]', or wants to create a task for another agent or team member to pick up later.
---

# Delegate Task — Skill Plugin
*Creates a structured task file for an assignee to pick up.*

## Activation

When this skill activates, output:

`"_(delegate-task activates)_"`

## Folder Structure

Tasks are stored in the memory-core repository:

```
delegate-task/
  Timeline/
    {Year}/           e.g. 2026
      {Date}/         e.g. 2026-04-18
        {no} - {name}.md
```

- `{no}` = sequential count of files already in that date folder + 1
- `{name}` = slugified task name (lowercase, hyphens, no spaces)

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### Step 1: Gather Task Info

Ask the following in sequence (or all at once if user has already provided some):

- [ ] **Assignee:** "Who is this task for? (a teammate, another agent, or a named AI companion)"
- [ ] **Task name:** "What is the task name? (short, descriptive)"
- [ ] **Overview:** "Give a one-paragraph overview of what needs to be done."
- [ ] **Task list:** "List the tasks (I'll format them as checkboxes)."
- [ ] **Rules:** "Any rules or constraints for this task? (optional)"
- [ ] **Skills needed:** "Does this task require any skills? (optional)"
  - If yes, ask: "Which skill(s)? Provide relevant context: project name, component, feature, and any implementation plan."

### Step 2: Determine File Path

- [ ] Get today's date: `{YYYY-MM-DD}` format for folder name, `{YYYY}` for year
- [ ] Resolve path: `delegate-task/Timeline/{YYYY}/{YYYY-MM-DD}/`
- [ ] Count `.md` files already in that folder → next task number = count + 1
- [ ] Slugify task name → `{name}` (lowercase, spaces → hyphens)
- [ ] Final file: `delegate-task/Timeline/{YYYY}/{YYYY-MM-DD}/{no} - {name}.md`

### Step 3: Write Task File

- [ ] Create directories if they don't exist
- [ ] Write the file using the template below
- [ ] Confirm: "Task #{no} — '{task name}' delegated to {assignee}. File created at `{path}`."

## Task File Template

```markdown
# {Task Name}

**Assignee:** {name}
**Delegated:** {YYYY-MM-DD}
**Status:** Pending

## Task Overview

{One paragraph describing what needs to be done and why.}

## Task List

- [ ] {task 1}
- [ ] {task 2}

## Rules

- {rule 1}
- {rule 2 — or "None." if not applicable}

## Skills

{If no skills needed, write "None."}

- use skill `continue-project`, project: {project name}, component: {component name}, feature: {feature name}
  Implementation plan:
  {plan here}
```

## Rules

1. Never create the task file without confirming with the user first
2. Always show the full file content for review before writing
3. If the date folder doesn't exist, create it (and the year folder if needed)
4. Task numbers are per-day — count only files in that specific date folder
5. Skills section: keep it minimal — just enough for the assignee to act without ambiguity

## Level History

- **Lv.1** — Current behaviour, as described in the Protocol and Rules above
