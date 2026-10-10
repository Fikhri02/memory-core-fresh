---
name: export-package
description: "Use when user says 'export [name]', 'package [name]', 'export project [name]', 'export ecosystem [name]', 'export my profile', 'package feature [X]', 'export feature [X]', 'package ecosystem feature', or 'export ecosystem feature'. Packages a project, an ecosystem, one ecosystem feature, or the companion profile into a single labelled file under migrations/out/ — for yourself on another machine (self) or for someone else (share, personal data stripped) — and records it in the local migration ledger."
---

# Export Package — Skill Plugin
*Turns a project, an ecosystem, a feature or the profile into one labelled, portable file.*

## Activation

When this skill activates, output:

`"_(export-package activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "export [name]" / "package [name]"** | ACTIVE |
| **User says "export my profile"** | ACTIVE — kind is profile |
| **User says "package feature [X]" / "export feature [X]"** | ACTIVE — kind is feature |
| **User wants to move a whole memory-core** | DORMANT — that is git's job |
| **User wants to import** | DORMANT — hand to `import-package` |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

Run every command from the memory root. `PKG` means
`python3 plugins/violet-skills/skills/import-package/scripts/pkgtool.py`. The kind handlers live in
`plugins/violet-skills/skills/import-package/kinds/` — read the one for the resolved kind.

## Protocol

### Step 1 — Resolve the kind

- [ ] "profile", "my profile", "main" → **profile**
- [ ] "feature [X]" phrasing → **feature**; resolve `X` against `ecosystem/*/features/{X}.md`
- [ ] Otherwise match the name against `project-management/*/` (skip `_`-prefixed), `ecosystem/*/`
      and `ecosystem/*/features/*.md`:
  - exactly one match → use it and say so: "Exporting **wikipetia** as a project package."
  - several → ask which, listing each with its kind
  - none → ask. **Never guess**
- [ ] Read `kinds/{kind}.md`

### Step 2 — Ask the audience

- [ ] Ask: "Is this for you (another machine of yours), or to share with someone else?" — no default.
      `self` carries everything; `share` strips personal data and session history
- [ ] Profile id: `profile@{user-slug}` for self, `profile@shared` for share

### Step 3 — Collect and strip

- [ ] Version: `PKG next-version {id}`
- [ ] Create `migrations/.staging/{id}/` (empty it first if a previous run left it)
- [ ] Follow **Export — collect** in the kind file: stage, strip, gather gaps, and for `share` gather
      scan hits

### Step 4 — Manifest, then wait

- [ ] Show, in one block:
  - kind, id, audience, version, output path `migrations/out/{id}.v{n}.pkg.md`
  - every staged file or section
  - everything stripped and why (machine-bound column, timeline/session for share, user section
    blanked, …)
  - gaps (dangling link, binary file, missing Overview or `git_origin`, unknown profile heading)
  - for `share`: every scan hit as `file:line kind excerpt`, and the sentence "The scan is a check,
    not a guarantee — read the list."
- [ ] For each scan hit, the user chooses strip (edit the staged file) or keep
- [ ] **Wait for confirmation.** Nothing is written to `out/` before it

### Step 5 — Write and record

- [ ] Write the spec JSON from **Export — header** to `migrations/.staging/{id}.spec.json`
- [ ] `PKG pack --spec migrations/.staging/{id}.spec.json --staging migrations/.staging/{id} --out migrations/out/{id}.v{n}.pkg.md`
- [ ] `PKG log --dir out --package {id} --kind {kind} --audience {audience} --version {n} --result written --note "out/{id}.v{n}.pkg.md"`
- [ ] Delete `migrations/.staging/{id}/` and its spec file
- [ ] Report: path, version, what was stripped, gaps

## Rules

1. **The kind is resolved, never guessed.** One match is used and announced; anything else asks
2. **The audience is asked every time.** It is written into the package and changes what travels
3. **Nothing is written before the manifest is confirmed**
4. **Exports are never overwritten.** Each export is a new version file; `pack` refuses an existing path
5. **Machine-bound data never travels** — `Local Path`, the map's `Location`, absence markers, package
   markers, absolute paths. `git_origin` travels instead
6. **`brain/`, `notes/`, `learning/`, `career/`, `context/` never travel** in any kind
7. **Never package an undocumented feature** — hand off to `document-ecosystem-feature`
8. **Every export is a ledger row.** `migrations/ledger.md` is local and git-ignored
9. **A self profile export warns** that the file holds personal history

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| Name matches a project and an ecosystem | Ask which |
| Staging folder left over from a failed run | Empty it and start again |
| `pack` refuses (invalid header, binary file) | Report the reason; fix staging; nothing is in `out/` |
| A link in `Plans/` dangles | Gap — reported, skipped, export continues |
| Ecosystem with every member unticked | Valid — map and notes only |
| Share profile with an unknown `main-memory.md` heading | Treated as user (blanked); named in the manifest |

## Level History

- **Lv.1** — Base: four kinds (project, ecosystem, feature, profile), self/share audience, versioned exports, deterministic packing via pkgtool, local ledger. Replaces `package-ecosystem-feature`
