---
name: save-project-management
description: "MUST use when user says 'save project' or 'save project management'. Auto-suggest after any session where project-related work was done (feature implementation, project-management file changes, commits, component/design updates, or an investigation). Appends the session record to the active project's Timeline.md, and routes durable findings into the Feature Overviews and ecosystem notes they belong in. Bare 'save' belongs to save-memory."
---

# Save Project Management — Skill Plugin
*Records the session in Timeline.md, and files anything durable where it will be read again.*

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

Then **classify every bullet**, because the two files answer different questions:

| | `Timeline.md` | `Features/*/Overview.md` |
|---|---|---|
| Answers | *what happened, and when* | *what is true now* |
| Shape | dated log, append-only | living state |
| Example | "Committed `a1b2c3d`; the suite passes" | "The service builds against the system toolchain, not the project-local one" |

- **log** — the act itself: commits and hashes, what was run, what was decided in the room,
  what is pending on the user. Timeline only.
- **durable state** — a fact that stays true after this session closes: a constraint, a trap, a
  behaviour, a new capability, a key file, an environment gotcha. Timeline **and** Step 5.

The test: *would someone reading this feature cold next month need to know it?* If yes it is
durable, whatever session discovered it. If it only makes sense next to a date, it is log.

### Step 5: File the Durable Findings

For every bullet tagged **durable state**, update the file that owns it. Apply the edit, then
report it in Step 7 — do not ask first, and do not leave it for the user to copy across.

| Finding | Destination |
|---------|-------------|
| Feature behaviour, constraint, trap, gotcha | `project-management/{name}/Features/{Feature}/Overview.md` → **Constraints** |
| A file that matters to the feature | same file → **Key files** table |
| The feature gained a real sub-capability | same file → a new `## Section` (e.g. `## Audit log`) |
| Divergence between ecosystem members; one member having what another lacks | `ecosystem/{slug}/features/{feature}.md` |
| Changes how members relate to each other | `ecosystem/{slug}/map.md` → **Cross-Project Rules** |
| Project-wide, not feature-scoped (build, env, repo layout) | `General.md` or `Components.md` |

- [ ] Route each durable bullet to its destination; one finding may legitimately land in two files
      (repo-scoped in the Overview, cross-repo in the ecosystem note) — say the same thing at the
      altitude each file is written for, do not paste it twice verbatim
- [ ] **Additive only.** Never rewrite or delete what is already there. If a finding contradicts
      existing content, add it and flag the contradiction to the user — a documented fact going
      stale is a decision for them, not a silent overwrite
- [ ] Match the file's existing tone and structure — these files are hand-written prose and tables,
      not generated output
- [ ] If the project has no `Features/` entry for the work, say so rather than scaffolding one —
      creating feature files belongs to `document-project`

**Drift check.** Before writing, scan the previous **two** Timeline entries for feature work whose
substance never reached an Overview. Feature work recorded only as a dated bullet is invisible to
anyone reading the feature cold. If you find drift, offer to backfill it in the same pass.

### Step 5a: Offer Findings to Linked Learning Topics

_Only when `learning/` exists._

- [ ] Search `learning/*/Projects.md` (skip folders starting with `_`) for a line ``- `{project}` …``
      naming the active project
- [ ] If any topic links it and Step 4 produced durable bullets, ask once: "Add any of these
      findings to {topic} notes?" and list the durable bullets, numbered
- [ ] For each one the user picks: write or update `learning/{topic}/Notes/{concept}.md` from
      `learning/_template/note.md` (additive). Then, in `Progress.md`: if the concept's row is at
      `—` (planned, not yet studied), set it to `shaky` with today's date; if it has no row, add
      `| {concept} | {current module} | shaky | {today} | Notes/{concept}.md |`, where the current
      module is the first `## M…` heading in `Study-Plan.md` without ` ✓`. Never change a row that
      is already rated
- [ ] **Never copy automatically** — a topic note is study material, and the user decides what
      belongs there. Report the notes written in Step 7

### Step 6: Write Timeline Entry

- [ ] Read `project-management/{name}/Timeline.md`
- [ ] If today's date section (`## YYYY-MM-DD`) already exists → append bullets to it
- [ ] If not → **follow the ordering the file already uses.** Read its `## YYYY-MM-DD` headers: if
      they run oldest-first, append the new section at the end; if newest-first, insert it at the
      top below the header. Both conventions exist across projects, and imposing the wrong one
      leaves a file that reads in two directions at once
  ```
  ## YYYY-MM-DD
  - bullet 1
  - bullet 2
  ```
- [ ] Write updated file

- [ ] **Sync upload**: if `device/sync.md` exists, run the **Upload** in `session-briefing` Step 0s with the label `save project {name}`

### Step 7: Confirm

- [ ] Report: "Saved **{project-name}** — timeline updated, {N} file(s) updated."
- [ ] List every documentation file touched and what went into each, so the user can review what
      moved out of the timeline and into the permanent record
- [ ] If nothing was durable, say "timeline updated, no documentation changes" — that is a normal
      outcome, not a failure

## Rules

1. Only run if project-related work actually happened — do not create empty or near-empty entries
2. Keep bullets brief — one line, verb-first, no padding
3. Append to today's section if it exists; never overwrite existing entries
4. Always ask which project if ambiguous — never assume
5. **The timeline is not the record, it is the log.** A finding that only lands in `Timeline.md`
   is filed under a date nobody will search. Anything that stays true after the session closes
   belongs in the Overview as well
6. **Documentation edits are additive.** Existing Overview content is never rewritten or deleted
   by this skill; contradictions are surfaced to the user, not resolved silently
7. **Not everything is durable.** An exploration with no ratified direction stays in `notes/` and
   the timeline — promoting an undecided option into an Overview states it as fact
8. Never create a `Features/` entry here — that is `document-project`'s job

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| `Timeline.md` missing | Warn and stop — do not create it silently |
| Today's section already exists | Append new bullets below existing ones |
| Multiple projects worked on | Ask which project, run once per project if user wants both |
| No commit hash available | Skip hash — just describe the work |
| Durable finding, but no matching `Features/` entry | Put it in the timeline, say the feature is undocumented, suggest `document-project` |
| Finding contradicts existing Overview content | Add it, flag the contradiction, let the user resolve it |
| Finding spans several projects | Write the repo-scoped half in each Overview and the cross-repo half in `ecosystem/{slug}/features/{feature}.md` |
| Ecosystem note does not exist for a shared domain | Note it and suggest `document-ecosystem-feature` — do not create it here |

## Level History

- **Lv.3** — Timeline only. Durable findings stayed in the dated log and never reached the
  feature documentation, so a feature file could go stale while its timeline looked current
- **Lv.4** — Step 4 classifies each bullet as log or durable state; Step 5 routes the durable ones
  into the Feature Overviews, ecosystem notes and map, and Step 6 follows the timeline's existing order
- **Lv.5** — Current behaviour: Step 5a offers durable findings to learning topics that link this project, writing only the ones the user picks
