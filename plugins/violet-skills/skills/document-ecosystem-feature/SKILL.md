---
name: document-ecosystem-feature
description: "Use when user says 'document feature [X] across [ecosystem]', 'document ecosystem feature', or 'document shared domain'. Documents one feature across every member of an ecosystem — reconnaissance per member, one cross-repo note under ecosystem/{slug}/features/, and repo-scoped Overviews in each member project. Also suggested by manage-ecosystem's Cross-Project Check when a shared domain has no note."
---

# Document Ecosystem Feature — Skill Plugin
*Documents one feature across every member of an ecosystem — one cross-repo note, and a repo-scoped Overview per participating member.*

## Activation

When this skill activates, output:

`"_(document-ecosystem-feature activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "document feature [X] across [ecosystem]"** | ACTIVE |
| **User says "document ecosystem feature"** | ACTIVE |
| **User says "document shared domain"** | ACTIVE |
| **`manage-ecosystem` Cross-Project Check finds a domain with no note** | SUGGEST — offer, never start |
| **Feature lives in one project only** | DORMANT — that is a plain `Features/{C}/Overview.md` |
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

- [ ] Resolve the ecosystem. If `ecosystem/` is empty or nothing matches, hand off to
      `manage-ecosystem` → new, then resume here. **Never invent an ecosystem.**
- [ ] If several ecosystems could match, ask. Never guess
- [ ] Resolve the feature label and slug (`DEP (Device Enrollment Program)` → `dep`)
- [ ] If `ecosystem/{slug}/features/{feature}.md` exists → offer **Update** or **Cancel**.
      Never silently overwrite

### Phase 2 — Recon

- [ ] Read the members from the map's **Members table**. This is the only source of membership
- [ ] For each member, resolve its repo path from `project-management/{project}/General.md` →
      Repositories table
- [ ] A member whose `Location` is an inline path rather than `→ General.md` is undocumented →
      offer `document-project` for it first; proceed without it only if the user declines
- [ ] Search each member repo for the feature. Record **hits and misses**, and what was searched
- [ ] A member with zero hits is a **finding**, not an error: it goes to `non_members` with its
      evidence. A member whose repo is missing from disk is **unknown**, not a non-member

### Phase 3 — Draft and confirm

- [ ] Present the participation table, the component name proposed per member, and every file
      that will be written or amended
- [ ] **Wait.** Nothing is written on reconnaissance alone

### Phase 4 — Write

- [ ] `ecosystem/{slug}/features/{feature}.md` — the required core, plus only those optional
      sections reconnaissance actually filled. Format: `ecosystem/README.md` → Feature notes
- [ ] Per participating member: `Features/{Component}/Overview.md` — repo-scoped, **appended**,
      carrying the pointer to the note
- [ ] Per participating member: the `Components.md` line
- [ ] `map.md`: the Shared Domains entry with its `Deep note:`, plus any new Relations and
      Cross-Project Rules; bump `updated:`
- [ ] Per participating member: a `Timeline.md` entry

## Rules

1. **Membership comes from the Members table.** Never inferred from directory names, git remotes,
   or import graphs — a wrong member is worse than a missing one, because the user stops trusting
   the map
2. **Non-participation is a finding.** Record it in `non_members` with the evidence. The next
   person must not have to re-run the search
3. **The note owns cross-repo depth; the Overview stays repo-scoped.** Comparative material —
   divergence tables, side-by-side models — lives in the note and nowhere else
4. **Never write on reconnaissance alone.** The participation table is confirmed first
5. **Append, never overwrite** existing Overview or Components content
6. **Bump the map's `updated:`** on every write
7. **A required section with nothing in it says so as a finding** — "No divergence found; all
   three members share the same status strings". Never pad with `-`
8. **Never mark work Completed** — status is the user's call
9. This skill does **not** judge staleness. `health_check` owns that via `updated:`

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| No ecosystem exists | Hand off to `manage-ecosystem` → new. Never invent one |
| Feature matches no member | Report it and stop — nothing to document, and the feature may be misnamed |
| Feature found in exactly one member | Say so; this is a single-project feature. Offer a plain `Features/{C}/Overview.md` instead of a note |
| A member repo is missing from disk | Record as unknown, not as a non-member — absence of a checkout is not absence of the feature |
| Member is undocumented (inline path) | Offer `document-project` first; proceed without it only if the user declines |
| Note already exists | Offer Update or Cancel; on Update, append and re-verify participation |
| Component name differs per member | Allowed — record each member's own name in its Overview, and the domain name in the map |
| Ecosystem folder has no `map.md` | Stop; `manage-ecosystem` owns repairing that |
| A project belongs to two ecosystems | Ask which one this feature belongs to; never write into both |

## Level History

- **Lv.1** — Base: ecosystem-scoped feature documentation across members, with participation recorded as a finding
