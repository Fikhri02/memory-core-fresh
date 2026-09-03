---
name: package-ecosystem-feature
description: "Use when user says 'package feature [X]', 'package ecosystem feature', 'export feature [X]', or 'export ecosystem feature'. Packages one documented ecosystem feature — its cross-repo note, the map entries that place it, and each member's Overview and Components line — into a single portable file under migrations/out/, with machine-bound paths stripped. Read back by unpackage-ecosystem-feature on another machine."
---

# Package Ecosystem Feature — Skill Plugin
*Turns one documented ecosystem feature into a single portable file.*

## Activation

When this skill activates, output:

`"_(package-ecosystem-feature activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "package feature [X]"** | ACTIVE |
| **User says "package ecosystem feature"** | ACTIVE |
| **User says "export feature [X]"** | ACTIVE |
| **Feature has no note under `ecosystem/{slug}/features/`** | DORMANT — hand off to `document-ecosystem-feature` |
| **User wants to move a whole memory-core** | DORMANT — that is git's job, not this skill's |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### Phase 1 — Resolve

- [ ] Resolve the ecosystem and the feature. If several could match, ask. Never guess
- [ ] Require `ecosystem/{slug}/features/{feature}.md` to exist. If it does not, hand off to
      `document-ecosystem-feature` and stop — **never package an undocumented feature**
- [ ] If `migrations/out/{feature}@{slug}.pkg.md` already exists, read its `version:` and plan to
      write `version + 1`. Otherwise `version: 1`

### Phase 2 — Collect

- [ ] Read `members:` and `non_members:` from the **note's frontmatter**. This is the only source
      of membership — never the map, never inferred from folder names
- [ ] For each member, collect:
  - `project-management/{project}/Features/{Component}/Overview.md` — its body
  - the `Components.md` line naming that component
  - `git_origin` from `General.md` → Repositories table
- [ ] From `map.md`, collect the Shared Domains entry for this feature, the Relations naming these
      members, and the Cross-Project Rules naming this feature
- [ ] **Strip everything machine-bound**: the `Local Path` column, any `_(not on this machine)_`
      marker, and any `<!-- pkg:... -->` markers left by a previous import on this machine
- [ ] A member whose Overview is missing is a **finding**, not an error: report it and continue.
      A member with no `git_origin` is reported too — the receiver will have nothing to recognise

### Phase 3 — Confirm

- [ ] Show the manifest: every section that will be written, every member and its component, every
      field being stripped, and anything found missing
- [ ] **Wait.** Nothing is written until the manifest is confirmed

### Phase 4 — Write

- [ ] Write `migrations/out/{feature}@{slug}.pkg.md` in the format in `migrations/README.md`
- [ ] Report the path and the version, and say what was stripped

## Rules

1. **Membership comes from the note's frontmatter.** Never the map, never inferred — the note is
   what was actually verified by reconnaissance
2. **Never package an undocumented feature.** The note is the payload; without it there is nothing
   to move
3. **Machine-bound data never travels.** `Local Path`, absence markers, and existing package
   markers are stripped. `git_origin` goes in their place
4. **`Timeline.md` never travels.** It is session history, not knowledge
5. **Nothing under `main/` ever travels.** That is companion memory
6. **Bump `version:` on every export of the same feature.** It is what lets a re-import tell an
   update from a no-op
7. **Never write on reconnaissance alone.** The manifest is confirmed first
8. A missing Overview or `git_origin` is reported and the export continues — a partial package is
   more useful than none, as long as the gap is stated

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| No note for the feature | Hand off to `document-ecosystem-feature`. Never invent the note |
| Note exists, map has no Shared Domains entry for it | Package the note and Overviews; report the gap. `manage-ecosystem` owns repairing the map |
| A member has no `project-management/` entry | No Overview to collect — record it in `members:` anyway with its `git_origin`, so the receiver can still locate it |
| A member's repo is absent from this machine | Irrelevant — packaging reads documentation, not repos |
| `git_origin` missing from `General.md` | Report it; the member travels without one and the receiver must identify it by name |
| Package for this feature already in `out/` | Bump `version:`; never silently overwrite at the same version |
| Feature note names a member the map does not list | Report it and stop. `health_check` flags this as `ecosystem_feature_note_member_unknown` — fix the map first |
| Ecosystem folder has no `map.md` | Stop; `manage-ecosystem` owns repairing that |

## Level History

- **Lv.1** — Base: single-feature packaging with machine-bound data stripped and versioned re-export
