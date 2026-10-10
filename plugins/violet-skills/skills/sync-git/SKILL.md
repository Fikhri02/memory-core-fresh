---
name: sync-git
description: "Use when user says 'sync git', 'update from git', 'sync development', or after a merge, pull, or new branch. Reads the commits on the current branch since the last sync, attributes them by author, appends them to the feature's Log and the project Timeline, and proposes — never applies — task and completion updates."
---

# Sync Git — Skill Plugin
*Reconciles project-management with what git actually says happened.*

## Activation

When this skill activates, output:

`"_(sync-git activates)_"`

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

This skill is unusual: it reads a **code repository** (your working directory) and writes to the
**memory root**. Keep the two straight. Every `git` command runs in the code repo; every file
written lives under the memory root.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Context Guard

| Context | Status |
|---------|--------|
| **User says "sync git"** | ACTIVE |
| **User says "update from git"** | ACTIVE |
| **User says "sync development"** | ACTIVE |
| **After a merge, pull, or new branch — user asks to sync** | ACTIVE |
| **`continue-project` finds commits newer than the last Log row** | SUGGEST |
| **Working directory is not a git repository** | DORMANT |
| **Mid-conversation (no trigger context)** | DORMANT |

## Protocol

### Step 1: Confirm the Code Repo

- [ ] Run `git rev-parse --is-inside-work-tree` — if it fails, say "Not a git repository — nothing
      to sync" and stop
- [ ] Record `git remote get-url origin` (may be empty) and the absolute repo path

### Step 2: Identify the Project

- [ ] Read the **Repositories** table in each `project-management/*/General.md`
- [ ] Match on git origin first; fall back to the local path recorded in `device/paths.md`
- [ ] If exactly one matches → use it
- [ ] If several match → list them and ask which
- [ ] If none match → say: "This repo isn't linked to any project. Add it to a project's
      Repositories table, or run `document project` to create one." → stop.
      **Never scaffold a project folder from here.**

### Step 3: Identify the Feature

- [ ] Run `git branch --show-current`
- [ ] Search the project's feature files (`Features/*/Development/*.md`, `Hotfix/*/Development/*.md`)
      for one whose `**Branch**:` field matches
- [ ] If found → that is the target feature
- [ ] If not found → this is an **unmapped branch**. Report it and offer:
  - "Create a feature file for this branch?" → hand off to `continue-project` Step 5a
  - "Sync to the project Timeline only?" → skip the feature Log, still write the Timeline
  - "Skip it" → stop
- [ ] If two features claim the same branch → list both and ask; never guess

### Step 4: Find the Watermark

- [ ] Read the target feature's `## Log` table
- [ ] Take the most recent row of the form `Synced to <sha>` — that sha is the watermark
- [ ] If no such row exists → use `git merge-base HEAD main` (or `master`) as the baseline
- [ ] If there is no merge-base (shallow clone, unrelated histories) → ask the user for a starting
      point rather than dumping the entire history

### Step 5: Collect the Commits

- [ ] Run: `git log <watermark>..HEAD --no-merges --date=short --pretty=format:'%h|%an|%ad|%s'`
- [ ] For each commit, also read the body (`git log -1 --format=%b <sha>`) and look for an
      `Author:` trailer — your completion-commit format writes one
- [ ] **Attribution**, in priority order:
  1. The `Author:` trailer if present — this is what distinguishes one agent from another, since
     several may commit under the same git identity
  2. Otherwise the git author name (`%an`) — this is the normal case for teammates
- [ ] Count merge commits separately (`git log <watermark>..HEAD --merges --oneline | wc -l`) —
      they are skipped, but reported as a count
- [ ] If there are no new commits → say "Already up to date with `<sha>`" and stop

### Step 6: Write the Feature Log

_Skipped for unmapped branches._

- [ ] Append one row to the feature's `## Log` table:

  ```
  | 2026-08-29 | Synced to a1b2c3d (4 commits · Sam, Aisyah) — signature capture, offline queue |
  ```

- [ ] The sha in that row is the new watermark. **Write it only after the Timeline write
      succeeds** — a half-finished sync must be repeatable, not silently skipped next time

### Step 7: Write the Project Timeline

- [ ] Append to `project-management/{project}/Timeline.md`, under today's `## YYYY-MM-DD` heading
      (create it if absent, at the top)
- [ ] **One bullet per commit, every author attributed:**

  ```
  ## 2026-08-29
  - Implemented signature capture on receiving (a1b2c3d · Sam)
  - Fixed offline queue flush ordering (e4f5g6h · Danial)
  - Merged upstream auth refactor (9f8e7d6 · Aisyah)
  - Corrected i18n string keys (3c2b1a0 · Wei Jie)
  ```

- [ ] If merge commits were skipped, add a final line: `- (+3 merge commits, not listed)`
- [ ] The 10-bullet cap in `save-project-management` does **not** apply here — that governs
      session summaries; this is a commit log and must be complete

### Step 8: Propose — Never Apply

Report these as questions. Each needs an explicit yes before anything changes:

- [ ] **Tasks that look done** — unchecked tasks whose wording matches commit subjects or changed
      files. Present as "these look done, confirm?" and check only what the user confirms
- [ ] **Feature complete** — all tasks checked → "Move to `Completed/`?" (see `continue-project`
      Step 8; the move is the only completion signal)
- [ ] **Branch merged** — if `git branch --merged main` includes this branch, flag it: "This branch
      is merged into main. Close the feature out?"
- [ ] **Backlog items** — commits that look like they cleared a `## Backlog` entry

### Step 9: Report

```
Synced {project} · {feature} — {N} commits ({authors})
  Feature Log:  1 row added, watermark now {sha}
  Timeline:     {N} bullets added under {date}
  Proposed:     {M} task(s), {completion/merge flags}
```

## Rules

1. **Read-only on the code repo.** Never commit, stage, checkout, pull, or edit code from this
   skill. It reads git history and writes memory files, nothing else
2. **Never check a task checkbox or move a feature to `Completed/` on its own.** A diff can look
   like a finished task without being one — Step 8 proposes, the user decides
3. **Never create project or feature entries for branches that aren't the user's.** Teammates do
   not use this system; their branches get reported as unmapped, never scaffolded
4. Timeline and Log writes are **append-only** — never rewrite or reorder existing rows
5. The watermark advances **only after** a successful write. A failed sync must be safe to re-run
6. Attribution prefers the `Author:` trailer, falls back to the git author name. Never guess an
   author, and never collapse several authors into one
7. Merge commits are skipped and counted, not listed — they carry no content of their own
8. If the same sync would produce no bullets, write nothing at all rather than an empty entry

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| Not a git repository | Report and stop |
| Detached HEAD | Report the sha, ask which feature it belongs to before syncing |
| Branch matches no feature file | Unmapped — offer feature creation, Timeline-only, or skip |
| Two features claim the same branch | List both, ask, never guess |
| No project matches this repo | Report; suggest adding it to a Repositories table or `document project` |
| Shallow clone, no merge-base | Ask for a starting commit rather than dumping all history |
| No new commits since the watermark | "Already up to date with `<sha>`" and stop |
| Commits authored entirely by teammates | Still sync — attribution makes it useful |
| Rebased branch, watermark sha no longer exists | Say the watermark is unreachable and fall back to merge-base, warning that some commits may repeat |
| Feature file has no `## Log` table | Create the table from `_template/feature.md` before appending |

## Level History

- **Lv.1** — Base: project and feature resolution from git, Log watermark, commit sync to both timelines with per-author attribution, propose-only task and completion updates
