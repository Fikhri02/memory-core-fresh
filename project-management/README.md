# Project Management

The project index. One folder per project, scaffolded from `_template/` and maintained by the
`document-project`, `continue-project`, `save-project-management`, and `sync-git` skills.

---

## Creating a project

Say **"new project [name]"** or **"document project [name]"**. Both route to `document-project`,
which reads `_template/structure.yaml` and builds the folder. There is one creation path on
purpose — a second one is how two projects end up with different shapes.

## Shape of a project

```
{project-name}/
  General.md        what it is, stack, status
  Components.md     the functional areas — this file drives the folder structure
  Design.md         design language and decisions
  Timeline.md       dated log, appended by save-project-management and sync-git
  Plans/            symlinks to project-plans/active/*.md
  Feedbacks/
  Features/{Component}/Development/    active work
  Features/{Component}/Completed/      finished work
  Features/{Component}/Archived/       abandoned
  Features/{Component}/Overview.md     component workflow, backlog, notes
  Hotfix/{Component}/...               same three states
```

**Component folders are not pre-created.** They appear when a component is added to
`Components.md` or when a feature is first created under one. `_template/structure.yaml` only
declares `Plans/`, `Feedbacks/`, and the four root files.

## Features carry no status field

**The folder is the status.** A file in `Development/` is active; moving it to `Completed/` is
the only completion signal. There is no `status:` line to forget to update, and no way for the
field and the folder to disagree.

The cost is that a finished feature can sit in `Development/` forever. `health_check` catches it
(`complete_feature_in_development`) — it found 12 in the previous repo.

**Moving a feature to `Completed/` is a human decision.** Every task being checked is not
sufficient; the skills propose the move and wait.

## What's next lives in the Backlog

Each feature file has a `## Backlog` section split into **Pending** and **Ready to pick up**.
That is where `continue-project` looks when it suggests work — not at unchecked tasks, which
describe the current feature rather than what comes after it.

## Component-level loading

`continue-project` loads `Features/{Component}/Overview.md` for the selected component only, not
every component's context. That is the token budget working: a project with eight components
costs the same to open as one with two.

## Timeline

Append-only, newest section last, one `## YYYY-MM-DD` header per day. Written by
`save-project-management` ("save project") and `sync-git`. Read by `session-briefing` to compute
idle days and raise 🟡 / 🔴 flags.

A stale timeline is the signal that work happened outside the framework. `health_check` reports
any project past 60 days.
