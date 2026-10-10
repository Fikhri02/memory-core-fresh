# Kind: feature

One documented ecosystem feature: its cross-repo note, the map entries that place it, and each
member's Overview and `Components.md` line. This is the format-1 package, now labelled.

**Id:** `{feature}@{ecosystem}` · **Export file:** `migrations/out/{feature}@{ecosystem}.v{n}.pkg.md`

`PKG` = `python3 plugins/violet-skills/skills/import-package/scripts/pkgtool.py`, run from the memory root.

Feature packages write **regions inside files this machine owns**, so they keep in-file markers.
`PKG plan` refuses them; follow this file instead.

## Export — collect

- [ ] Require `ecosystem/{slug}/features/{feature}.md`. If missing, hand off to
      `document-ecosystem-feature` and stop — **never package an undocumented feature**
- [ ] Read `members:` and `non_members:` from the **note's frontmatter** — the only source of
      membership. A member named there but absent from the map: report and stop; fix the map first
- [ ] Stage, under `migrations/.staging/{id}/`:
  - `@note.md` — the note body
  - `@map.md` — the Shared Domains entry for this feature, the Relations naming these members, and the
    Cross-Project Rules naming this feature
  - `@overview/{project}.md` — each member's `Features/{Component}/Overview.md` body
  - `@components/{project}.md` — the `Components.md` line naming that component
- [ ] `PKG strip {file} --column "Local Path" --column Location --write` on every staged file
- [ ] A missing Overview or `git_origin` is a gap: report it and continue
- [ ] For `share`: `PKG scan` every staged file. Audience otherwise changes nothing — a feature never
      carries a timeline

## Export — header

```json
{"header": {"package": "{feature}@{ecosystem}", "kind": "feature", "audience": "{self|share}",
            "version": N, "exported": "YYYY-MM-DD", "format": 2},
 "header_extra": "ecosystem:\n  slug: acme\n  label: \"Acme Inc\"\nfeature:\n  slug: dep\n  label: \"DEP\"\nmembers:\n  - {project: acme-admin, component: DEP, git_origin: \"https://…\"}\nnon_members:\n  - {project: acme, evidence: \"searched DeviceEnroll across *.dart, zero hits\"}",
 "links": []}
```

## Import — place

Format-1 packages (no `format:` field) are read as this kind.

- [ ] Run `PKG feature-targets {package}`. It validates the ecosystem, feature, every member slug and
      component name, and prints the **only** paths this import may write (`map`, `note`, and per
      member `overview` and `components`). If it refuses, the package is refused. **Never build a
      path from package text yourself** — use these lines
- [ ] Resolve the ecosystem: `ecosystem/{slug}/` exists → use it; absent → plan to create
      `ecosystem/{slug}/map.md` from the package's `ecosystem` and `members` blocks. This is the
      intended path, not a fallback
- [ ] For each member, ask where that repo lives, showing its `git_origin`:

  | Repo on disk | `project-management/{project}/` entry | Outcome |
  |---|---|---|
  | yes | yes | record the path in `device/paths.md`, place Overview + `Components.md` line |
  | yes | no | record the path in `device/paths.md`, flag for `document-project`, skip the Overview |
  | no | — | record `not here` in `device/paths.md`, skip the Overview |

- [ ] **Never scaffold a project entry** from a feature package — that is `document-project`'s job.
      **Never invent a path** — "not here" is a recorded answer
- [ ] Before writing any owned region, compare hashes (`PKG sha {file} --section …` or by region):

  | Region hash | Incoming version | Action |
  |---|---|---|
  | matches the marker | newer than local | replace the region, update the marker |
  | matches the marker | equal to local | no-op — say so, do not rewrite |
  | matches the marker | older than local | skip, warn |
  | **differs** | any | **conflict** — never overwrite; show the diff and offer keep-local / take-incoming / stop |

- [ ] Write:
  - `ecosystem/{slug}/map.md` — created from the package if absent, else the owned regions replaced.
    Bump `updated:`
  - `ecosystem/{slug}/features/{feature}.md` — wholly owned; write
    `source: {package: {id}, version: {v}, imported: {date}, sha: {sha}}` into its frontmatter
  - per placeable member: `Features/{Component}/Overview.md` and the `Components.md` line, each wrapped:

    ```markdown
    <!-- pkg:{id} v{version} sha:{sha} -->
    …
    <!-- /pkg:{id} -->
    ```

- [ ] Only owned regions are touched; everything outside a marker belongs to this machine
