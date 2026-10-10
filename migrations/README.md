# Migrations

Packages in transit between machines and people. One file is one labelled package — a project, an
ecosystem, one ecosystem feature, or the companion profile.

Written by `export-package` (**"export [name]"**, **"package feature [X]"**).
Read by `import-package` (**"import [name]"**, **"import migration"**, **"migration log"**).

---

## Layout

```
migrations/
  out/          packages exported from this machine — {id}.v{n}.pkg.md, every version kept
  in/           packages received, awaiting import
  applied/      imported packages
  manifests/    {id}.yaml — what each whole-file import wrote, with hashes
  ledger.md     one row per export or import, append only
```

**All of it is local and git-ignored.** Packages can hold personal history; manifests and the ledger
hold this machine's state. Only the folder skeleton (`.gitkeep`) is committed.

## Kinds and audiences

| Kind | Id | Carries |
|------|----|---------|
| `project` | `{slug}@project` | one `project-management/{slug}/` entry plus the plans, brainstorms and debug logs it links |
| `ecosystem` | `{slug}@ecosystem` | the map, every feature note, and each documented member project in full |
| `feature` | `{feature}@{ecosystem}` | one feature's note, map entries, each member's Overview and Components line |
| `profile` | `profile@{user}` / `profile@shared` | `main/` — companion and user profile, preferences, sessions |

Every export asks **for you, or to share?**

- `self` — everything travels, including timelines, feedbacks and session history.
- `share` — timelines, feedbacks, session history and user-profile details are stripped; a scan lists
  likely personal data for you to review. A share profile is a template: names become
  `{{USER_NAME}}` / `{{COMPANION_NAME}}`.

Never in any kind: `brain/`, `notes/`, `learning/`, `career/`, `context/`, and machine-bound data —
`Local Path`, the map's `Location`, absence markers, package markers. `git_origin` travels instead.

## File shape

````markdown
---
package: wikipetia@project
kind: project
audience: self
version: 3
exported: 2026-10-10
format: 2
source_install: "irfan@macbook"
---

## file: project-management/wikipetia/General.md

```pkg
# WikiPetia
…
```

## link: project-management/wikipetia/Plans/x.md -> project-plans/active/x.md
````

Each section's content sits in a `pkg` fence longer than any backtick run inside it. Profile sections
are `## section: main/main-memory.md#{heading}`. Feature packages use `## note`, `## map`,
`## overview: {project}`, `## components: {project}`.

**Format 1** — packages with no `format:` field, from before this change — are read as
`kind: feature`, `audience: share`.

`version` is load-bearing: it is what lets a re-import tell an update from a no-op.

## Re-import

Whole files and profile sections are recorded in `manifests/{id}.yaml` with a hash of what was
written (machine columns ignored). Feature packages keep in-file markers instead, because they write
regions inside files this machine owns:

```markdown
<!-- pkg:dep@acme v2 sha:ab12cd34 -->
…
<!-- /pkg:dep@acme -->
```

| Local hash vs record | Incoming version | Action |
|---|---|---|
| matches | newer | replace |
| matches | same, identical | no-op |
| matches | older | skip, warn |
| **differs** | any | **conflict** — never overwritten; you choose |

`Timeline.md` is the exception: new dated sections are merged in, existing ones are never touched,
and local growth is never a conflict.

`health_check` reports `package_region_drift`, `package_marker_unclosed`, `package_orphan_marker`
(judged against the ledger) and `package_manifest_drift`.

## The helper

`plugins/violet-skills/skills/import-package/scripts/pkgtool.py` does everything that must be exact —
validation, packing, stripping, scanning, hashing, planning, timeline merge, the ledger. Run it with
`--help` for the command list.
