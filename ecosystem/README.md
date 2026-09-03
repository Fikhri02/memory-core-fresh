# Ecosystems

An **ecosystem** groups projects that belong together — an org, a company, a product line — and
records how they relate. Every **folder** here is one ecosystem: `{slug}/map.md` is the map, and
`{slug}/features/*.md` are its cross-repo feature notes.

```
ecosystem/
  README.md
  acme/
    map.md                  the map — members, relations, shared domains, rules
    features/
      dep.md                one cross-repo note per shared feature
```

This is a **map, not a manual.** One line per relation, one line per domain, linking out to a note
for depth. The moment it starts describing call chains it becomes a stale second copy of those
notes.

---

## What it owns, and what it does not

| Concern | Owner |
|---------|-------|
| Where a repo lives | `project-management/{project}/General.md` → Repositories table |
| What a project is, its components and features | `project-management/{project}/` |
| **Who relates to whom, and how** | **Here** |
| **Which domains span several projects** | **Here** |
| Deep architecture, call chains, file locations | `ecosystem/{slug}/features/*.md`, linked from the map |

A member that has a `project-management/` entry is **referenced by name** — its location resolves
from `General.md`. Only members *without* an entry (a teammate's repo, a third-party service)
carry an inline path, because nothing else records them.

Never restate a location that `General.md` already holds. Two copies diverge the first time a
repo moves.

## File format

```markdown
---
ecosystem: acme                  # required — stable id, matches the filename
label: Acme Inc                  # required — the org, company or product line
updated: 2026-08-29              # required — bump on every edit
---

# Acme Ecosystem

## Members

| Project | Role | Documented | Location |
|---------|------|-----------|----------|
| Acme Admin | Admin surface — staff configuration | `acme-admin` | → General.md |
| Acme API | Backend API and data owner | — | `~/projects/acme-api` |
| Acme Terminal | Point-of-sale terminal | — | `~/projects/acme-terminal` |

## Relations

<!-- One line each. Direction matters: who calls whom, who owns what. -->
- Acme Admin → Acme API: promotion configuration write
- Acme Terminal → Acme API: promotion discovery and discount calculation
- Acme API → Billing: invoice sync

## Shared Domains

<!-- A domain that spans several members. This is what powers the cross-project warning. -->
- **Promotion** — Acme Admin configures · Acme API stores and calculates · Acme Terminal applies
  Deep note: `features/promotion.md`

## Cross-Project Rules

<!-- Constraints that hold across members and are easy to violate from inside one of them. -->
- DB tables and JSON wire keys keep their original prefix even after a product rename
```

### Fields

| Field | Required | Purpose |
|-------|----------|---------|
| `ecosystem` | yes | Stable id, independent of the label |
| `label` | yes | The org, company, or product line the group belongs to |
| `updated` | yes | Bumped on every edit — `health_check` flags ecosystems stale past 180 days |

### Sections

- **Members** — every project in the group, with a one-line role. `Documented` is the
  `project-management/` folder name, or `—` for an outsider. `Location` is `→ General.md` for
  documented members, an actual path for outsiders.
- **Relations** — one line per edge, direction first. `A → B: what flows`.
- **Shared Domains** — the load-bearing section. A domain listed here spans several members, so
  `continue-project` warns when you create a feature under it.
- **Cross-Project Rules** — constraints easy to break from inside a single repo.

## Why Shared Domains matter most

Members and Relations are documentation. **Shared Domains are executable.** When you start a
feature under a component that matches a listed domain, `continue-project` tells you which sibling
projects usually need matching work. That warning is the entire reason this folder exists — a
promotion change that lands in the admin app and nowhere else is the failure it prevents.

Keep domain names close to the component names you actually use, so the match works.

---

## Feature notes

A **feature note** is the cross-repo view of one feature: how the members' implementations fit,
where they diverge, and what breaks if you assume they match. One file per feature, at
`ecosystem/{slug}/features/{feature}.md`, linked from its Shared Domains entry.

The map stays a map. The note is where the depth goes.

### Format

```markdown
---
ecosystem: acme                  # required — matches the folder name
feature: dep                     # required — matches the filename
label: DEP (Device Enrollment Program)
members: [acme-admin, acme-api, acme-oms]
non_members: [acme-terminal]     # required when a member was checked and found clean
updated: 2026-09-03              # required — bump on every edit
---

# {Label} — cross-ecosystem note

> **Participates**: … · **Does not participate**: … (with the evidence)
> **Per-project depth**: `{project}/Features/{Component}/Overview.md`

## What the domain is        REQUIRED
## Divergence                REQUIRED
## Traps                     REQUIRED
## Open questions            REQUIRED

## Flow per path             optional — only if reconnaissance filled it
## Shared vocabulary         optional
## Where to look             optional
```

### Required sections, and what belongs in each

| Section | Holds | Does not hold |
|---------|-------|---------------|
| What the domain is | The business meaning, and what follows from it | Per-repo implementation |
| Divergence | Where members differ while appearing to agree | A list of what each member does |
| Traps | Ordered by likelihood of being hit, not by severity | Anything not cross-repo |
| Open questions | What the code did not settle — inference kept out of the findings | Speculation dressed as fact |

### Rules

- **A required section with nothing in it says so as a finding** — "No divergence found; all three
  members share the same status strings" — and is never padded with `-`. An empty `Divergence` is
  real information about an ecosystem.
- **`non_members` is load-bearing.** Participation is a *finding*. Recording that a member was
  checked and has no code for the feature stops the next person re-running the search, and lets
  `health_check` flag it if that project later grows one.
- **The note owns cross-repo depth; `Features/{Component}/Overview.md` stays repo-scoped.**
  Comparative material — divergence tables, side-by-side models — lives in the note and nowhere
  else. Duplicating it into the Overviews is how it goes stale.

## Maintenance

Use the `manage-ecosystem` skill for the map: `new ecosystem`, `add to ecosystem`,
`edit ecosystem`, `remove from ecosystem`, `list ecosystems`. Use `document-ecosystem-feature`
for the notes under `features/`. Editing by hand is fine too — the folder is the registry and
nothing caches it.

Enrolment is always **explicit**. Nothing infers ecosystem membership from git remotes or import
graphs; a wrong relation is worse than a missing one, because you stop trusting the warnings.
