---
name: pick-up-task
description: Use when user or agent says 'pick up task', 'pick-up-task', 'what's my task', 'check my tasks', 'what do I need to do', or when an agent wants to find the latest delegated task assigned to them.
---

# Pick Up Task — Skill Plugin
*Finds the latest pending task assigned to an agent and loads its context.*

## Activation

When this skill activates, output:

`"_(pick-up-task activates)_"`

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### Step 1: Identify Assignee

- [ ] If the assignee is clear from context (e.g. "what's my task, I'm Sam") → use it
- [ ] Otherwise ask: "Who is picking up the task?"

### Step 2: Find Latest Task

- [ ] Scan `delegate-task/Timeline/` for all year folders → sort descending
- [ ] Within the most recent year, scan date folders → sort descending
- [ ] Walk dates from newest to oldest; in each folder, read all `.md` files
- [ ] Filter for files where `**Assignee:**` matches the given name (case-insensitive)
- [ ] Among matching files, find the first with `**Status:** Pending` (has unchecked `- [ ]` items in Task List)

### Step 3a: Pending Task Found

- [ ] Present the task:
  - Task name, assignee, delegated date
  - Task Overview paragraph
  - Unchecked task items only (`- [ ]`)
  - Rules (if any)
  - Skills (if any)
- [ ] Ask: "Ready to start this task?"
  - If yes → follow the skills or steps listed; mark tasks as done as you go
  - If no → ask if they want to see the next oldest pending task instead

### Step 3b: No Pending Task Found

- [ ] Inform: "No pending tasks found for {assignee}."
- [ ] Find the most recently completed task for that assignee (all task items are `- [x]`, Status: Completed or all checked)
- [ ] Present it as: "Last completed task: #{no} — '{name}' (delegated {date})"
- [ ] Ask: "Want to check a different assignee or date?"

### Step 4: Mark Task Complete (Optional)

When all task items in the active task are checked:

- [ ] Ask: "All tasks done — mark this task as Completed?"
  - If yes → update `**Status:**` from `Pending` to `Completed` in the file
  - If no → leave as-is

## Rules

1. Never assume an assignee — always confirm if ambiguous
2. Show only unchecked tasks when presenting a pending task
3. Do not auto-mark complete — always ask the user/agent first
4. Walk date folders newest-first to surface the most recent task

## Level History

- **Lv.1** — Current behaviour, as described in the Protocol and Rules above
