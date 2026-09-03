---
name: manage-ecosystem
description: "Use when user says 'new ecosystem', 'add to ecosystem', 'edit ecosystem', 'remove from ecosystem', or 'list ecosystems'. Maintains ecosystem/{slug}/map.md — the map of which projects belong together, how they relate, and which domains span several of them. Also suggested when a project is documented or a feature is created under a shared domain."
---

# Manage Ecosystem — Skill Plugin
*Maintains the map of which projects belong together and how they relate.*

## Activation

When this skill activates, output:

`"_(manage-ecosystem activates)_"`

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Context Guard

| Context | Status |
|---------|--------|
| **User says "new ecosystem"** | ACTIVE → new |
| **User says "add to ecosystem"** | ACTIVE → add |
| **User says "edit ecosystem"** | ACTIVE → edit |
| **User says "remove from ecosystem"** | ACTIVE → remove |
| **User says "list ecosystems"** | ACTIVE → list |
| **`document-project` finishes a new project** | SUGGEST — offer enrolment |
| **A feature is created under a shared domain** | SUGGEST — surface siblings, do not edit |
| **Mid-conversation (no trigger context)** | DORMANT |

## Protocol

### new — Create an ecosystem

- [ ] Ask for the **label** (the org, company, or product line) and derive a slug
- [ ] Check `ecosystem/{slug}/map.md` — if it exists, offer to edit it instead
- [ ] Ask which projects belong to it. For each, resolve whether it has a
      `project-management/` entry:
  - **Documented** → reference by folder name; `Location` is `→ General.md`
  - **Not documented** → ask for its local path or git origin, recorded inline
- [ ] Ask for a one-line **role** per member — what it *is*, not what it does in detail
- [ ] Ask for **relations** between members, one line each, direction first
- [ ] Ask for **shared domains** — anything that spans two or more members. For each, ask whether
      a `notes/` file already covers it and link that
- [ ] Show the full draft and wait for confirmation
- [ ] Write `ecosystem/{slug}/map.md` using the format in `ecosystem/README.md`, creating the
      `{slug}/` folder and its empty `features/` subfolder

### add — Add a member, relation, domain, or rule

- [ ] Resolve which ecosystem (ask if several exist and it is ambiguous)
- [ ] Ask what is being added: member · relation · shared domain · cross-project rule
- [ ] For a member, run the documented/undocumented resolution above
- [ ] Append to the right section, keep the table aligned, bump `updated:`
- [ ] Report what was added

### edit — Change an existing entry

- [ ] Resolve the ecosystem and the entry
- [ ] Show the current line, ask for the replacement, confirm before writing
- [ ] Bump `updated:`

### remove — Remove a member, relation, domain, or rule

- [ ] Resolve the ecosystem and the entry
- [ ] **If removing a member**, first list every relation and shared domain that names it, and ask
      whether those go too — a member removed while its relations remain leaves the map lying
- [ ] Confirm, remove, bump `updated:`
- [ ] Removing the last member leaves an empty ecosystem: ask whether to delete the file

### list — Show all ecosystems

- [ ] List each `ecosystem/*/map.md` with its label, member count, shared-domain
      count, and `updated:` date
- [ ] Flag anything not updated in over 180 days as `(stale)`

## Cross-Project Check

_Used by other skills. Does not edit anything._

When a feature is being created or amended under component `{C}` of project `{P}`:

- [ ] Find the ecosystem whose Members table contains `{P}` — if none, stay silent
- [ ] Match `{C}` against the Shared Domains section (case-insensitive, substring both ways)
- [ ] On a match, surface once:

  ```
  {C} is a shared domain in {label}: {member} · {member} · {member}
  Changes here usually need matching work in the others.
  Deep note: ecosystem/{slug}/features/{feature}.md
  ```

- [ ] Also surface any Cross-Project Rules mentioning `{C}` or a matched member
- [ ] If the matched domain has **no** `ecosystem/{slug}/features/{domain}.md`, add one line:
      `No cross-ecosystem note for {C} yet — "document ecosystem feature {C}" writes one.`
- [ ] **Never block, never edit.** This is a warning, not a gate

## Rules

1. **A map, not a manual.** One line per relation, one line per domain. Anything longer belongs in
   an `ecosystem/{slug}/features/{feature}.md` note that the entry links to
2. **Never restate a location that `General.md` already holds.** Documented members are referenced
   by name; only undocumented outsiders carry an inline path
3. **Enrolment is always explicit.** Never infer membership from git remotes, import graphs, or
   shared naming — a wrong relation is worse than a missing one, because the user stops trusting
   the warnings
4. Always confirm the full draft before writing a new ecosystem file
5. Bump `updated:` on every change — `health_check` uses it to flag stale maps
6. The cross-project check never edits and never blocks; it surfaces once and gets out of the way
7. A project may belong to more than one ecosystem, but say so when it happens — it is usually a
   sign the grouping is wrong

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| `ecosystem/` does not exist | Create it with the README from the template before writing |
| `ecosystem/{slug}/` exists but has no `map.md` | Report it; offer to recreate the map or remove the folder |
| Member named that has no `project-management/` entry | Fine — record the inline path, mark `Documented` as `—` |
| Member references a project folder that was deleted | Report on `list`; offer to fix the reference or drop the member |
| Same project in two ecosystems | Allowed, but flag it — usually a grouping mistake |
| Shared domain names a `notes/` file that does not exist | Warn once; keep the entry, the note may be written later |
| Removing a member still named in relations | List them and ask before removing |
| Two ecosystems claim the same label | Ask which to use; do not merge automatically |

## Level History

- **Lv.1** — Base: new/add/edit/remove/list, documented-vs-outsider member resolution, and the cross-project check used by continue-project
