---
name: continue-project
description: "MUST use when user says 'continue project', 'continue project [name]', 'resume project [name]', 'load project [name]', 'open project [name]', or 'pick up project [name]'. This is the entry point for resuming work on any existing project — it handles project context loading, component selection, feature branch resumption, and completion commits."
---

# Continue Project — Skill Plugin

_Loads project context, surfaces active development branches, and suggests the next relevant skill._

## Activation

When this skill activates, output:

`"_(continue-project activates)_"`

## Context Guard

| Context                                   | Status  |
| ----------------------------------------- | ------- |
| **User says "continue project"**          | ACTIVE  |
| **User says "continue project [name]"**   | ACTIVE  |
| **User says "resume project [name]"**     | ACTIVE  |
| **User says "load project [name]"**       | ACTIVE  |
| **User says "open project [name]"**       | ACTIVE  |
| **User says "pick up project [name]"**    | ACTIVE  |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### Step 1: Resolve Project Name

- [ ] If project name given in trigger → use it
- [ ] If no name given → ask: "Which project do you want to continue?"

### Step 2: Find Project Folder

- [ ] Search `project-management/` for a folder matching the name (case-insensitive, partial match)
- [ ] If not found:
  - List all folder names under `project-management/` as suggestions
  - Ask: "I couldn't find '{name}'. Did you mean one of these? [list]"
- [ ] If double confirm fails → say: "Sorry, I couldn't find a project matching '{name}'. Please check the name and try again." → abort

### Step 3: Load Project Context

- [ ] Check `ecosystem/*/map.md` for a Members table containing this project. If found, surface once:
      its label, the sibling members with their roles, and any Cross-Project Rules. If not, stay silent
- [ ] If `ecosystem/{slug}/features/{domain}.md` exists for a domain matching the component being
      loaded, read **only its `## Traps` section** — not the whole note. The per-project
      `Features/{Component}/Overview.md` already carries this repo's depth
- [ ] Read the bodies of any `context/` modules declaring `load: on_project_load` — the condition is
      now satisfied — and report them: `Context: +{module} (on_project_load)`
- [ ] Read `project-management/{name}/General.md`
- [ ] Read the header of `project-management/{name}/Design.md` (above its first `##`) and hold
      its `**Layers**` value for the session — `design-preferences` loads those layer files when a
      design session starts. Do not load them now. No `**Layers**` line → stay silent
- [ ] For each Repositories row, look up its git origin in `device/paths.md`. If a row has no path
      on this device, ask once — *"Where is {repo} on this laptop? (path, or 'not here')"* — and
      record the answer with `sync_device.set_path` (asked lazily, first open per laptop)
- [ ] Extract: project name, description, tech stack (skip repo detail)
- [ ] Output a 2-line project summary to user

### Step 4: Ask Feature, Hotfix, or Investigation

- [ ] Ask: "Are you continuing a Feature, a Hotfix, or an Investigation? (default: Feature)"
- [ ] **Investigation** = read-only analysis of a repo — reading code, tracing flows, auditing a
      module. No feature file, no branch, no tasks. If chosen → jump to **Step 4i** and skip
      Steps 4a–8 entirely.

### Step 4i: Investigation Session

_Only when the user picked Investigation._

- [ ] Ask: "What are you investigating?" — use the answer to derive a slug
- [ ] Check `notes/{slug}.md`:
  - If it exists → read it and present a 2-line recap of what was already found
  - If not → create it with a title header and today's date section
- [ ] Work the session normally (read-only — do not edit the repo under investigation)
- [ ] At the end, or when the user says `save project`:
  - Append findings to `notes/{slug}.md` under today's date
  - Append one line to `project-management/{name}/Timeline.md`:
    `- Investigated {topic} — findings in \`notes/{slug}.md\``
- [ ] Report: "Investigation logged to `notes/{slug}.md` and {name}'s timeline."

### Step 4a: Select Component

- [ ] Read `project-management/{name}/Components.md`
- [ ] List all component names and descriptions, ask: "Which component does this belong to? [list]"
- [ ] If `Components.md` is missing or empty → warn: "No components defined yet. You can add components to `Components.md`. For now, enter a component name manually."
- [ ] Store selected component name for use in folder paths and commit message

### Step 4b: Load Component Overview

- [ ] Check if `project-management/{name}/Features/{component}/Overview.md` exists
- [ ] If found → read it; present a brief summary (Workflow bullets + any Backlog items) as context for the session
- [ ] If not found → ask: "No Overview.md found for **{component}**. Would you like to brainstorm the component overview now?"
  - If yes →
    - Check if `project-management/{name}/Plans` files exists → if yes, read it and use it as context for the brainstorm
    - If no plan exists → read `project-management/{name}/General.md` for context instead
    - Then suggest the `brainstorm` skill, passing that context so the brainstorm is grounded in the project
  - If no → continue without it

### Step 5: List Development Branches

- [ ] Scan `project-management/{name}/Features/{component}/Development/` (for Feature) or `project-management/{name}/Hotfix/{component}/Development/` (for Hotfix)
- [ ] Collect all `.md` files found
- [ ] If none found:
  - Ask: "No {features/hotfixes} currently in development under **{component}** for {project-name}. Want to start a new one?"
  - If yes → proceed to **Step 5a: Create New Branch**
  - If no → stop
- [ ] If one found → ask: "Continuing [{name}] — confirm?"
- [ ] If multiple found → list them with name + one-line description (first line under `## Description`), ask which
- [ ] Add option: "Or type 'new' to create a new feature branch"
  - If user types 'new' → proceed to **Step 5a: Create New Branch**

#### Step 5a: Create New Branch

- [ ] Read `project-management/{name}/General.md` and check if a `## Backlog` section exists with items whose `**Component**:` matches the selected component
- [ ] If matching backlog items exist → ask: "Would you like to pick from the backlog? [list matching item names] — or type 'new' for a fresh feature"
  - If user picks a backlog item → pre-fill name, description, and task list from that item
  - If user picks 'new' → proceed with free-form input below
- [ ] If no matching backlog items → skip the backlog question and proceed directly
- [ ] **Cross-project check** — run the check in `manage-ecosystem`: if the selected component
      matches a Shared Domain of this project's ecosystem, surface the sibling projects before the
      feature is created:

      > `Stock Count` is a shared domain in Acme Inc: Acme API · Acme Terminal.
      > Changes here usually need matching work in the others.

      Warn only. Never block, never create anything in the sibling projects
- [ ] Ask: "What is the name of the new feature/hotfix? (e.g. `add-login-screen`)" — skip if pre-filled from backlog
- [ ] Suggest a branch name derived from the input: `feature/{slugified-name}` or `hotfix/{slugified-name}`
- [ ] Ask user to confirm the branch name
- [ ] Run: `git checkout -b {branch-name}`
- [ ] Confirm: "Branch `{branch-name}` created and checked out."
- [ ] Create feature file at `project-management/{name}/Features/{component}/Development/{feature-name}.md` (or Hotfix equivalent) from `project-management/_template/feature.md` — fill in `{feature-name}`, `{component}`, branch, and created date; remove the template placeholder rows
- [ ] If `Features/{component}/Overview.md` does not exist → create it from `_template/overview.md` with the component name filled in

### Step 6: Load Branch Context

- [ ] Read the selected feature/hotfix file
- [ ] Present:
  - Name + description
  - Unchecked tasks only (lines starting with `- [ ]`)
  - `## Backlog` items, if any — **Ready to pick up** first, then **Pending** with their blockers
  - Last log table row (if any entries exist)
- [ ] Compare the feature's last `Synced to <sha>` Log row against `git log -1 --format=%h`. If the
      branch has moved on since, suggest — do not run — `sync git` to bring the Log and Timeline up
      to date before continuing
- [ ] Check `## User testing Feedbacks` section — collect feedback items whose checkbox is `[]` (open) or `- [ ]` (open)
- [ ] If open feedback items exist → present them as a numbered list under "Open feedback:" and flag: "User testing is in progress — open items need hotfix before closure."
- [ ] Check `## Hotfix Sessions` — find the last session; if its `- [ ] Ready for retest` is checked (`- [x]`), surface it: "Hotfix ready for retest — waiting for user sign-off on: #{feedback numbers}"

### Step 6a: Branch Verification (Git Check)

- [ ] Run `git branch --show-current` to get the active branch
- [ ] Compare active branch against the expected branch for the selected feature (derived from feature file name or a `branch:` field if present)
- [ ] If active branch matches → continue
- [ ] If active branch is `main` or `master` → show warning:

  > **Warning:** You are currently on `main`. Development work should never happen directly on `main`.

  Then ask:
  - "Switch to `{expected-branch}`?" → run `git checkout {expected-branch}` if it exists, or `git checkout -b {expected-branch}` if not
  - "Stay on `main` and proceed without switching?" → allow but remind again at Step 7

- [ ] If active branch is a different feature branch → ask:
  - "You are on `{active-branch}` but this feature is associated with `{expected-branch}`. Switch to `{expected-branch}`?"
  - If yes → `git checkout {expected-branch}` (or offer to create if not found)
  - If no → continue on current branch

### Step 7: Ask What to Do + Suggest Skill

- [ ] Ask: "What do you want to do next?"
- [ ] Suggest relevant skill based on state:
  - Open feedback items exist → "User testing is in progress. Suggest addressing open feedback via hotfix: implement fix → add a Hotfix Session entry → mark `Ready for retest` → user retests → on pass, mark the feedback checkbox done. Repeat until all feedback passes."
  - Has unchecked tasks → "You have [N] pending tasks. Suggest: `subagent-driven-development` for a fresh subagent per task."
  - No tasks defined yet → "No tasks defined yet. Suggest: `brainstorm` to plan the feature, or `project-planning` for structured phases."
  - All tasks checked AND no open feedback → proceed to **Step 8: Commit Completion**
  - Hotfix category → append: "For bugs, `systematic-debugging` may also help."

### Step 8: Commit Completion

_Triggers only when all tasks in the feature file are checked (`- [x]`)._

- [ ] Collect all completed tasks (lines starting with `- [x]`) from the feature file
- [ ] Ask: "Who implemented this?" — the user, their AI companion, or another agent. Use whatever
      names they work under; the answer becomes the `Author:` line
  - The name given → `Author: {name}`
  - If the user does not care → omit the `Author:` line entirely
- [ ] Present the commit message for review:

  ```
  Feature: {component} - {feature-name}

  Author: {name}
  Task:
  - {completed task 1}
  - {completed task 2}
  ...
  ```

- [ ] Ask: "Ready to commit? (yes / edit / skip)"
  - **yes** → stage and commit with the message above (subject: first line; body: Author + Task block)
  - **edit** → let user adjust the message, then commit
  - **skip** → skip commit, remind user to commit manually
- [ ] After successful commit → ask: "Move this feature to `Completed/`?" — move the file only if
      the user explicitly confirms. The move is the completion signal; there is no status field to set.
- [ ] If the feature still has open `## Backlog` items, name them before asking, so the user is
      not closing out work that is still queued.

## Rules

1. Never create or modify project files without user confirmation
2. **Never move a feature to `Completed/` unless the user explicitly says so** — all tasks being checked does not imply the user has declared the feature done. Feature files carry no status field: living in `Development/` means active, and the move to `Completed/` is the only completion signal.
3. Double-confirm before aborting — give user one chance to correct the name
4. Show unchecked tasks only in Step 6 — do not list completed tasks
5. Suggest skills, never auto-invoke them
6. If `project-management/` folder does not exist: say "The project-management folder hasn't been set up yet. Use 'new project [name]' to create a project first."
7. **NEVER commit directly to `main` or `master`.** If the active branch is `main` or `master` when Step 8 runs, issue three escalating warnings before proceeding — and only proceed if the user explicitly confirms all three:

   > **Warning #1:** You are about to commit directly to `main`. This is highly discouraged. Are you sure?

   > **⚠ WARNING #2: COMMITTING TO MAIN IS DANGEROUS.** Direct commits to `main` bypass branch protection, break team workflows, and cannot be easily undone on shared repos. Do you REALLY want to continue?

   > **🚨 FINAL WARNING — LAST CHANCE TO STOP 🚨** You are about to commit directly to `main`. This will affect the main branch permanently. Type 'YES I UNDERSTAND THE RISK' to proceed, or anything else to cancel.

   If the user does not explicitly type `YES I UNDERSTAND THE RISK` on the third prompt → abort the commit entirely.

## Edge Cases

| Situation                                      | Behavior                                                                                  |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `project-management/` folder missing           | Inform user, suggest 'new project [name]'                                                 |
| Project folder exists but `General.md` missing | Warn: "General.md not found — project may be incomplete. Continuing with available data." |
| `Components.md` missing or empty               | Warn and allow manual component name entry                                                |
| Component folder does not exist yet            | Create it when first feature under that component is created                              |
| Feature file has no `## Description` section   | Skip description line in Step 5                                                           |
| Feature file has no log rows                   | Skip log row in Step 5                                                                    |
| `git` not available or not a git repo          | Skip Step 5a branch creation, Step 6a branch check, and Step 8 commit; warn user          |
| Branch name from feature file not found in git | Offer to create it with `git checkout -b`                                                 |
| User on `main`, expected branch also `main`    | Treat as no branch set — ask user to create a feature branch before starting work         |
| Mix of checked and unchecked tasks at Step 7   | Show only unchecked tasks; Step 8 does not trigger until all are checked                  |
| Feature file has no `## Backlog` section       | Skip the backlog lines in Step 6 — do not create the section unprompted                   |
| Investigation chosen but project has no `notes/` entry yet | Create `notes/{slug}.md` from scratch; still log the Timeline line                        |

## Level History

- **Lv.12** — Current behaviour, as described in the Protocol and Rules above
