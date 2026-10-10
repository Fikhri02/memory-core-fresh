---
name: import-package
description: "Use when user says 'import [name]', 'unpackage [name]', 'import migration', 'import feature [X]', 'unpackage feature [X]', 'unpackage ecosystem feature', drops a .pkg.md into migrations/in/, or asks 'migration log' / 'list migrations'. Reads a package's kind and audience label, then places a project, an ecosystem, a feature or the profile into this memory-core — asking before anything is written, never overwriting local edits — and records it in the local migration ledger."
---

# Import Package — Skill Plugin
*Reads a labelled package and places it, safely, wherever its kind belongs.*

## Activation

When this skill activates, output:

`"_(import-package activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "import [name]" / "unpackage [name]" / "import migration"** | ACTIVE |
| **User says "import feature [X]" / "unpackage feature [X]"** | ACTIVE |
| **User points at a `.pkg.md` file** | ACTIVE |
| **User says "migration log" / "list migrations"** | ACTIVE — Migration Log only |
| **`migrations/in/` has files and the user asks what is pending** | SUGGEST — list them, never import unasked |
| **User wants to export** | DORMANT — hand to `export-package` |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

Run every command from the memory root. `PKG` means
`python3 plugins/violet-skills/skills/import-package/scripts/pkgtool.py`. Kind handlers are in
`kinds/` beside this file.

## Protocol

### Step 1 — Locate and validate

- [ ] Locate the package: the named file, or `migrations/in/*.pkg.md`. Several pending → ask which
- [ ] `PKG validate {package}`. On exit 1: report the reason, log
      `PKG log --dir in --package {id or "?"} --kind {kind or "?"} --audience {audience or "?"} --version {v or 0} --result refused --note "{reason}"`
      and stop. **A malformed package is refused whole**
- [ ] Read `kinds/{kind}.md`. Format-1 packages report `kind=feature`

### Step 2 — Audience check

- [ ] `self`: ask "Is this your own install?" and show `source_install` if present. "No" → offer to
      import it as share: personal sections are skipped (session files, timelines, feedbacks, user
      profile sections), not written
- [ ] `share`: nothing to ask

### Step 3 — Plan, then wait

- [ ] Follow **Import — place** in the kind file up to its first write: resolve targets and renames,
      run `PKG plan` (all kinds but feature), work out repo locations to ask
- [ ] Show the whole plan: every target and its action, every conflict with its reason, every rename,
      every member marked not-here, every gap
- [ ] **Wait.** Nothing is written on reconnaissance alone

### Step 4 — Write, move, record

- [ ] Carry out **Import — place** in the kind file, resolving each conflict with the user
- [ ] Move the package `migrations/in/` → `migrations/applied/` (skip if it was imported from elsewhere
      on disk; copy it into `applied/` instead)
- [ ] Ledger result:

  | What happened | Result |
  |---|---|
  | every target `unchanged` | `no-op` |
  | everything written, no conflicts | `applied` |
  | conflicts resolved, nothing declined | `conflict-resolved` |
  | any member not here, any target skipped or kept-local | `partial` |

  `PKG log --dir in --package {id} --kind {kind} --audience {audience} --version {v} --result {result} --note "{counts: written, unchanged, conflicts and how resolved, members not here}"`
- [ ] Report: what was written, what was skipped and why, which projects to run `document-project` for

### Migration Log

- [ ] "migration log" / "list migrations": print `migrations/ledger.md`'s rows, newest last. Filter by
      kind, package or direction when asked. No ledger → "No migrations recorded on this machine."
      Read-only — never edits the ledger

## Rules

1. **The label decides.** `kind` and `audience` come from the package header — never inferred
2. **Refuse a malformed package whole** — a half-applied package is worse than none
3. **Nothing is written before the plan is confirmed**
4. **Never overwrite a local edit.** A `conflict` always stops and asks
5. **Paths are checked before anything is read or written.** `plan` and `extract` refuse absolute
   paths, `..`, infrastructure folders, and anything outside the kind's allowed roots
6. **Never invent a local path** — ask; "not here" is recorded
7. **Feature imports never create project entries.** Project and ecosystem imports may, after the
   target folder is confirmed
8. **Record only what was written or unchanged** — never a kept-local file
9. **Every import attempt is a ledger row**, including refusals
10. **Never mark work Completed** — status is the user's call

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| Package `format` newer than this importer | Refused, logged; ask the sender for an older export or update memory-core |
| Project slug taken by an unrelated project | Ask for a new slug; `--rename` on every call |
| Same version re-imported, nothing changed | Every target `unchanged` → `no-op` |
| Same version, different content | Each differing target is a `conflict` — the exporter reused a version |
| Self package, user says not their install | Offer share import; personal sections skipped |
| Package imported straight from Downloads | Copy into `applied/` after import; the original is left alone |
| `in/` holds several packages | List them; import one at a time |

## Level History

- **Lv.1** — Base: four kinds routed by label, self/share audience check, path-safe plan via pkgtool, manifest-based re-import for whole files and profile sections, timeline merge, local ledger and migration log. Replaces `unpackage-ecosystem-feature`
