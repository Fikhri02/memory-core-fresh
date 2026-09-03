# Delegate Task

Task files written for someone else — a teammate, another agent, or a second AI companion — to
pick up in a different session.

Written by `delegate-task` (**"delegate task"**, **"assign task to [name]"**).
Read by `pick-up-task` (**"pick up task"**, **"what's my task"**).

---

## Layout

```
Timeline/
  {YYYY}/                 2026
    {YYYY-MM-DD}/         2026-04-18
      {no} - {name}.md    1 - migrate-auth.md
```

- `{no}` — sequential within that date folder: existing `.md` count + 1
- `{name}` — slugified task name, lowercase, hyphens

Date-partitioned rather than status-partitioned, because a delegated task's most useful index is
*when it was handed over*.

## File shape

```markdown
# {Task Name}

**Assignee:** {name}
**Delegated:** {YYYY-MM-DD}
**Status:** Pending

## Task Overview
...
## Task List
- [ ] ...
## Rules
## Skills
```

`**Assignee:**` and `**Status:**` are **load-bearing** — `pick-up-task` matches on the assignee
line (case-insensitive) and treats a task as pending when unchecked `- [ ]` items remain. Rename
either field and handoff silently stops working.

## How pick-up works

Newest first: scan year folders descending, then date folders descending, walking back until a
file matching the assignee with unchecked items is found. If none is pending, the most recently
completed task for that assignee is shown instead, so the answer is never just "nothing".

## Why files rather than memory

A delegated task has to survive being read by **a different agent, in a different session, with
no shared context**. Everything needed to act — overview, tasks, rules, and which skills to use
with what project/component/feature context — is written into the file at delegation time.

If a task needs a skill, the delegating session records the context that skill will require. The
picking-up agent should not have to reconstruct it.

## Status is in the file here

Unlike `project-plans/` and `brainstorming/`, this folder does **not** move files between state
directories. Completion is the `**Status:**` field plus checked items. The tradeoff is deliberate
— date partitioning is the useful index, and moving a file would destroy the handover date.
