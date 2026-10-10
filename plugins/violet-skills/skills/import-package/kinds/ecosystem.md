# Kind: ecosystem

An ecosystem's map, every cross-repo feature note, and each documented member project in full.

**Id:** `{slug}@ecosystem` · **Export file:** `migrations/out/{slug}@ecosystem.v{n}.pkg.md`

`PKG` = `python3 plugins/violet-skills/skills/import-package/scripts/pkgtool.py`, run from the memory root.

## Export — collect

- [ ] Read `ecosystem/{slug}/map.md` → the Members table. A member whose **Documented** cell names a
      `project-management/` entry is **documented**; any other member is **undocumented**
- [ ] Show every member and let the user untick any. Undocumented members cannot carry files; they
      travel as a line in `members:` only
- [ ] Stage `ecosystem/{slug}/map.md` and `ecosystem/{slug}/features/*.md`, then run
      `PKG strip {file} --column "Local Path" --column Location --write` on each — the map's
      `Location` column is machine-bound
- [ ] For each ticked, documented member: collect it exactly as `kinds/project.md` **Export — collect**
      says, for the same audience, into the same staging folder. Its links go in the same `links` list
- [ ] For `share`: `PKG scan` every staged file

## Export — header

```json
{"header": {"package": "{slug}@ecosystem", "kind": "ecosystem", "audience": "{self|share}",
            "version": N, "exported": "YYYY-MM-DD", "format": 2},
 "header_extra": "label: \"{map label}\"\nmembers:\n  - {project: acme-admin, documented: true, git_origin: \"https://…\"}\n  - {project: acme-api, documented: false, git_origin: \"\"}",
 "links": []}
```

`git_origin` comes from each documented member's `General.md` Repositories table (first row); it is
empty for undocumented members.

## Import — place

- [ ] If `ecosystem/{slug}/` exists under a different label, keep the local label and report the difference
- [ ] **Member targets.** For each documented member in `members:`, confirm its target folder exactly
      as `kinds/project.md` **Import — place** says; collect every `--rename` into one list
- [ ] Run `PKG plan {package} --root . [--rename …]` once and act on each line using the table in
      `kinds/project.md`
- [ ] **Map Location column.** After `map.md` is written, add the `Location` column back to its Members
      table: `→ General.md` for documented members now present here; for undocumented members ask for
      a path, or write `_(not on this machine)_`. Bump the map's `updated:` to today
- [ ] **Repositories** for each member's `General.md`, as in `kinds/project.md`
- [ ] **Record** written and unchanged targets with `PKG record` — never kept-local ones
- [ ] A member present in the package but declined by the user is reported in the ledger note as skipped
