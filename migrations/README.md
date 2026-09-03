# Migrations

Packaged ecosystem features in transit between machines. One file is one feature's cross-repo
knowledge, made portable.

Written by `package-ecosystem-feature` (**"package feature [X]"**).
Read by `unpackage-ecosystem-feature` (**"unpackage feature [X]"**, **"import feature [X]"**).

---

## Layout

```
migrations/
  out/        packages exported from this machine, ready to send
  in/         packages received, awaiting import
  applied/    imported successfully — the record of what landed here
```

State directories rather than a flat folder, matching `brainstorming/` and `project-plans/`. A
package moves `in/` → `applied/` on a successful import, so "what is still pending here" is
answered by listing one directory.

`applied/` is an audit trail, not the source of truth. What is actually installed is recorded by
the markers in the files themselves.

## File shape

One self-contained Markdown file, `{feature}@{ecosystem}.pkg.md` — readable by a human with no
memory-core at all, and diffable in git.

```markdown
---
package: dep@acme
version: 2
exported: 2026-09-03
ecosystem:
  slug: acme
  label: "Acme Inc — POS platform"
feature:
  slug: dep
  label: "DEP (Device Enrollment Program)"
members:
  - {project: acme-admin, component: DEP, git_origin: "https://github.com/.../acme-admin.git"}
non_members:
  - {project: acme, evidence: "searched DeviceEnroll|Enrollment across *.dart, zero hits"}
---

## note
## map
## overview: {project}
## components: {project}
```

`version` is **load-bearing** — it is what lets a re-import tell an update from a no-op. Bump it on
every export of the same feature.

## What never travels

| Left behind | Why |
|-------------|-----|
| `Local Path` in the Repositories table | True only on the exporting machine |
| `_(not on this machine)_` absence markers | Local state written by a previous import |
| `Timeline.md` entries | Session history, not knowledge |
| Anything under `main/` | Companion memory, not project knowledge |

`git_origin` travels in its place. It is the portable half of the Repositories table, and the only
thing that lets the receiving user recognise which repo they are being asked to locate.

## Owned regions

An imported package owns specific regions of the files it wrote, and nothing else:

```markdown
<!-- pkg:dep@acme v2 sha:ab12cd34 -->
- **DEP (Device Enrollment Program)** — Admin drives · Middleware owns the data
<!-- /pkg:dep@acme -->
```

The feature note is wholly owned, so it carries the same provenance in its frontmatter instead:

```yaml
source: {package: dep@acme, version: 2, imported: 2026-09-03, sha: ab12cd34}
```

`sha` is the first 8 characters of the SHA-256 of the region, with trailing whitespace and
surrounding blank lines normalised away. Re-import compares it before writing:

| Region hash | Incoming version | Action |
|---|---|---|
| matches the marker | newer | replace the region |
| matches the marker | same | no-op |
| matches the marker | older | skip, warn |
| **differs** | any | **conflict** — never overwritten; you choose |

A hash that no longer matches means the region was edited here after import. That is the one case
that always stops and asks, because overwriting it would destroy work silently.

`health_check` reports the same conditions: `package_region_drift`, `package_marker_unclosed`, and
`package_orphan_marker`.

## Import never creates projects

Import asks where each member repo lives on this machine and records the answer. It does **not**
scaffold `project-management/{project}/` — that is `document-project`'s job. A member that is not
on this machine is marked `_(not on this machine)_` in the map and skipped.

Run `document-project` for it later and re-import: everything already applied is a no-op, and the
Overview lands where it now belongs.
