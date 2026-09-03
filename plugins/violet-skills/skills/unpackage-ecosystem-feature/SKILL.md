---
name: unpackage-ecosystem-feature
description: "Use when user says 'unpackage feature [X]', 'unpackage ecosystem feature', 'import feature [X]', 'import migration', or drops a .pkg.md into migrations/in/. Imports one packaged ecosystem feature into this memory-core — creating the ecosystem if it is absent, asking where each member repo lives, and replacing only the regions the package owns. Never creates project entries; that stays document-project's job."
---

# Unpackage Ecosystem Feature — Skill Plugin
*Imports one packaged ecosystem feature, whether or not this machine knows the ecosystem.*

## Activation

When this skill activates, output:

`"_(unpackage-ecosystem-feature activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "unpackage feature [X]"** | ACTIVE |
| **User says "import feature [X]"** or **"import migration"** | ACTIVE |
| **User points at a `.pkg.md` file** | ACTIVE |
| **`migrations/in/` has files and the user asks what is pending** | SUGGEST — list them, never import unasked |
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

- [ ] Locate the package: the named file, or `migrations/in/*.pkg.md`. If several are pending, ask
      which
- [ ] Read and validate the frontmatter: `package`, `version`, `ecosystem`, `feature`, `members`.
      **Refuse a malformed package** and say which field is wrong — never guess the shape
- [ ] Resolve the ecosystem:
  - `ecosystem/{slug}/` exists → use it
  - absent → plan to create `ecosystem/{slug}/map.md` from the package's `ecosystem` and `members`
    blocks. This is the intended path, not a fallback
- [ ] If the feature note already exists, read its `source:` frontmatter and compare versions —
      see **Re-import** below

### Phase 2 — Locate

For each member in the package, in order:

- [ ] Ask where that repo lives on this machine, showing its `git_origin` so it can be recognised:

  ```
  acme-api — https://github.com/acme/acme-api.git
  Where is this repo on this machine? (path, or "not here")
  ```

- [ ] Resolve to one of three outcomes:

  | Repo on disk | `project-management/{project}/` entry | Outcome |
  |---|---|---|
  | yes | yes | record the path in the map, place Overview + `Components.md` line |
  | yes | no | record the path in the map, flag for `document-project`, skip the Overview |
  | no | — | mark `_(not on this machine)_` in the map's Members `Location`, skip the Overview |

- [ ] **Never scaffold a project entry.** Creating `project-management/{project}/` is
      `document-project`'s job — say so and move on
- [ ] **Never invent a path.** "not here" is a valid, recorded answer

### Phase 3 — Plan and confirm

- [ ] Show every file to be written, every region to be replaced, every absence to be marked, and
      every conflict found
- [ ] **Wait.** Nothing is written on reconnaissance alone

### Phase 4 — Write

- [ ] `ecosystem/{slug}/map.md` — created from the package if absent, otherwise the owned regions
      replaced. Bump `updated:`
- [ ] `ecosystem/{slug}/features/{feature}.md` — wholly owned; write `source:` into its frontmatter
- [ ] Per placeable member: `Features/{Component}/Overview.md` and the `Components.md` line, each
      wrapped in its marker
- [ ] Move the package `migrations/in/` → `migrations/applied/`
- [ ] Report: what was written, what was marked absent, and which projects to run
      `document-project` for

## Re-import

Every owned region carries `sha:` — the hash of its content at import. Compare before writing:

| Region hash | Incoming version | Action |
|---|---|---|
| matches the marker | newer than local | replace the region, update the marker |
| matches the marker | equal to local | no-op — say so, do not rewrite |
| matches the marker | older than local | skip, warn |
| **differs** | any | **conflict** — never overwrite; show the diff and offer keep-local / take-incoming / stop |

A differing hash means the region was edited here after import. That case always stops and asks.

## Rules

1. **Import never creates a project entry.** `document-project` owns that boundary
2. **Import never invents a local path.** It asks; "not here" is recorded, not guessed
3. **Never write on reconnaissance alone.** The plan is confirmed first
4. **Never overwrite a locally edited region.** A hash mismatch always stops and asks
5. **Only owned regions are touched.** Everything outside a marker belongs to this machine
6. **Bump the map's `updated:`** on any map write
7. **Creating the ecosystem is in scope; inventing members is not.** Members come from the package
8. **Never mark work Completed** — status is the user's call
9. A package that fails validation is refused whole. A half-applied package is worse than none

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| Ecosystem absent | Create `map.md` from the package. This is the designed path |
| Ecosystem exists under a different label | Keep the local label; import the feature into it and report the difference |
| Feature note already exists at the same version, unmodified | No-op. Say so and move the package to `applied/` |
| Feature note edited locally since import | Conflict — show the diff, never overwrite |
| Member repo present but no project entry | Record the path, flag for `document-project`, skip the Overview. Re-import after documenting it |
| Member marked "not here", later cloned | Re-import places it — everything already applied is a no-op |
| Package names a member already in the map under another component name | Keep the local component name; report the difference rather than renaming |
| Two packages own overlapping map regions | Second import conflicts on the overlap; resolve by hand. Markers make the owner explicit |
| `migrations/in/` empty | Say so and list `applied/` instead of guessing |
| Package carries `Local Path` values | Malformed — a correct export strips them. Refuse and report |

## Level History

- **Lv.1** — Base: single-feature import with ecosystem creation, interactive member location, and hash-guarded re-import
