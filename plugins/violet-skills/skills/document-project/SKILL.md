---
name: document-project
description: "MUST use when user says 'document project [name]', 'document this project', 'start documenting', 'new project [name]', or 'create project'. Also suggested when a project is not found during continue-project. This is the single entry point for creating a project-management/ entry — it scaffolds from _template/structure.yaml and then builds documentation incrementally as work progresses."
---

# Document Project — Skill Plugin
*Creates a lightweight project-management entry and builds documentation progressively as the companion learns about the project during the session.*

## Activation

When this skill activates, output:

`"_(document-project activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "document project [name]"** | ACTIVE |
| **User says "document this project"** | ACTIVE |
| **User says "start documenting"** | ACTIVE |
| **User says "new project [name]"** | ACTIVE |
| **User says "create project"** | ACTIVE |
| **continue-project suggests it after a not-found** | ACTIVE (on user confirmation) |
| **Mid-conversation (no trigger)** | DORMANT |

---

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### Phase 1 — Init

#### Step 1: Resolve Name

- [ ] If name given in trigger → use it as `{name}`
- [ ] If no name given → infer from current working directory basename
- [ ] If cwd is ambiguous (e.g. `/`) → ask: "What's the project name?"
- [ ] Slugify `{name}` → `{slug}` (lowercase, hyphens, no spaces)

#### Step 2: Duplicate Check

- [ ] Check `project-management/{slug}/` for an existing entry
- [ ] If found → offer:
  - **Continue** — load existing entry and resume discovery mode
  - **Cancel** — abort
- [ ] If not found → proceed to Step 3

#### Step 3: Scan and Draft

Scan the project root (infer path from cwd or ask):

- [ ] Read `README*` — extract first meaningful paragraph as description
- [ ] Read manifest files to infer tech stack:
  - `pubspec.yaml` → Flutter / Dart
  - `package.json` / `next.config.*` / `vite.config.*` → Node.js / React / Next.js / Vue
  - `*.csproj` / `*.sln` → .NET / C#
  - `pyproject.toml` / `requirements.txt` → Python
  - `Cargo.toml` → Rust
  - `go.mod` → Go
  - `pom.xml` / `build.gradle` → Java / Kotlin
- [ ] Get git `origin` URL if available: `git remote get-url origin`
- [ ] Record the absolute local path in `device/paths.md` keyed by the git origin (`sync_device.set_path`) — never in `General.md`

If the scan finds nothing (a brand-new project with no repo yet — the `"new project"` path), ask
directly instead of guessing:

- [ ] "Short description of the project?"
- [ ] "Repository name(s), local path(s), and git origin(s)? (can be multiple, or none yet)"
- [ ] "Technology stack?"

Present the draft and wait for confirmation:

```
Here's what I found for {name}:

  Name:         {name}
  Description:  {extracted or "_(not found — please fill in)_"}
  Technology:   {extracted or "_(not found — please fill in)_"}
  Path:         {absolute local path}
  Git origin:   {origin url or blank}

Confirm, or tell me what to change.
```

#### Step 4: Scaffold

On confirmation:

- [ ] Read `project-management/_template/structure.yaml` — it defines the folders and files every
      project gets. Never hardcode the scaffold here; the template is the source of truth.
- [ ] Create every folder listed under `folders:` (currently `Plans`, `Feedbacks`)
- [ ] Create every file listed under `files:` from its named template:
  - `General.md` from `_template/general.md` — name, description, technology, Repositories table
    (name + git origin only — the local path goes to `device/paths.md`), empty Dev Notes, empty Backlog
  - `Timeline.md` from `_template/timeline.md` — one entry dated today: "Project created"
    (or "Session opened — documentation started" when entered via `document project`)
  - `Components.md` from `_template/components.md` — template defaults, or inferred components if
    the scan made them obvious
  - `Design.md` from `_template/design.md` — template defaults, then ask once: *"Which design
    layers apply? (website / web-app / mobile / none — several are fine)"* and fill the
    `**Layers**` line with the answer. A project with no UI gets `none`
- [ ] Create symlinks in `Plans/` for any matching planning files:
  - `brainstorming/active/{slug}.md` → `Plans/{slug}-brainstorm.md`
  - `project-plans/active/{slug}.md` → `Plans/{slug}-plan.md`
  - Shell, from the memory root: `ln -s "../../../{source-path}" "project-management/{slug}/Plans/{filename}"`
    — always a **relative** link, so it still resolves on every synced laptop
  - **Only create a symlink when the source file actually exists** — never create one speculatively,
    it just leaves a dangling link
- [ ] If `ecosystem/` holds any ecosystem folders, ask once: "Does this project belong to one of these?
      [list labels] — or none." On a yes, hand off to `manage-ecosystem` → add. Never enrol silently
- [ ] Set session flag: **document-project active** for `{slug}`

Report:

```
Documenting {name}. I'll build up what I learn as we work.
```

---

### Phase 2 — Discover (Passive, during session)

Runs silently whenever document-project is active. Do not announce each append — only report on save.

| Discovery | Target |
|-----------|--------|
| New functional area, layer, or module identified | Append to `Components.md` |
| Design rule, colour, UX pattern, or visual constraint found | Append to `Design.md` |
| Dev constraint, coding standard, or recurring rule encountered | Append to `General.md` Dev Notes |
| New repository identified | Add a row (name + git origin) to `General.md` Repositories; its local path goes to `device/paths.md` |

**Rules**:
- Never overwrite existing entries — append only
- Never remove or reorder existing content
- Infer component name from file/folder structure when possible
- One append per discovery — do not duplicate if already noted

---

### Phase 3 — Save

**Triggers**: `"save project"` , `"save project management"` , end of session — when document-project is active

Bare `"save"` belongs to `save-memory` and does not trigger this phase.

- [ ] Flush all pending discover-phase entries to their target files
- [ ] Append a session entry to `Timeline.md`:
  - Date (today)
  - What was worked on (1–3 bullets)
  - What was discovered or decided (1–3 bullets, skip if none)
- [ ] Report: "Project documentation updated."

---

## Rules

1. Always confirm the draft before creating any files
2. Never overwrite existing documentation entries — append only
3. Passive discovery runs silently — do not announce every append; only surface on save
4. If continue-project is also active for the same project, document-project discovery defers to that session's loaded context and does not duplicate it
5. Do not ask the user to fill in missing fields during init — leave them as `_(not found — please fill in)_` and update during discovery

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| `project-management/{slug}/` already exists | Offer Continue (resume discovery) or Cancel — never overwrite |
| No README and no manifest found | Leave description and tech as `_(not found — please fill in)_`; proceed |
| Project root not clear from cwd | Ask for path before scanning |
| User corrects the draft name | Re-slugify and re-check for duplicates with the new name |
| `"save project"` triggered but nothing was discovered | Still append a minimal Timeline entry; report "Project documentation updated." |
| Entered via `"new project"` with no existing repo | Skip the scan, ask the three draft questions directly, scaffold the same way |
| `structure.yaml` missing | Warn and fall back to the four core files (General, Timeline, Components, Design) + `Plans/`, `Feedbacks/` |
| Discovery finds same component already in Components.md | Skip — do not duplicate |

## Level History

- **Lv.2** — Current behaviour, as described in the Protocol and Rules above
