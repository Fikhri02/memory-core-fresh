# Kind: project

One `project-management/{slug}/` entry, plus the files its `Plans/` and `Debugging/` links point at.

**Id:** `{slug}@project` · **Export file:** `migrations/out/{slug}@project.v{n}.pkg.md`

`PKG` = `python3 plugins/violet-skills/skills/import-package/scripts/pkgtool.py`, run from the memory root.

## Export — collect

Stage into `migrations/.staging/{id}/`, mirroring each file's path from the memory root.

| Source under `project-management/{slug}/` | self | share |
|---|:-:|:-:|
| `General.md`, `Components.md`, `Design.md` | ✓ | ✓ |
| `Features/**/*.md`, `Hotfix/**/*.md` — every state folder | ✓ | ✓ |
| `Timeline.md` | ✓ | — |
| `Feedbacks/**` | ✓ | — |
| Each symlink in `Plans/` and `Debugging/` | ✓ | ✓ |

- [ ] Copy each regular file to the same relative path under staging
- [ ] For each symlink in `Plans/` and `Debugging/`: resolve it. If the target is inside the memory
      root, copy the **target** to its home path under staging (e.g. `project-plans/active/x.md`) and
      add `["project-management/{slug}/Plans/x.md", "project-plans/active/x.md"]` to the spec's
      `links`. A dangling link, or one pointing outside the memory root, is a **gap**: report it, skip it
- [ ] A non-text file (image, PDF) is a **gap**: report it, do not stage it
- [ ] Run `PKG strip {staged file} --write` on every staged `.md` file — this removes the `Local Path`
      column, package markers and absence markers
- [ ] For `share`: run `PKG scan {staged file}` on every staged file and collect the hits for the manifest

## Export — header

```json
{"header": {"package": "{slug}@project", "kind": "project", "audience": "{self|share}",
            "version": N, "exported": "YYYY-MM-DD", "format": 2, "source_install": "{user}@{host}"},
 "header_extra": "",
 "links": [["project-management/{slug}/Plans/x.md", "project-plans/active/x.md"]]}
```

`source_install` is set for `self` only; omit the key for `share`.

## Import — place

- [ ] **Target folder.** Default `project-management/{slug}/`. If it exists and is a different project
      (its `General.md` describes something else), ask for a new slug and pass
      `--rename project-management/{slug}=project-management/{new}` to every `plan`, `extract` and
      `merge-timeline` call. If it is the same project, keep the slug — the plan handles conflicts
- [ ] Run `PKG plan {package} --root .` and act on each line:

  | Action | Do |
  |---|---|
  | `new`, `update` | `PKG extract {package} {target}` |
  | `unchanged` | nothing |
  | `merge-timeline` | `PKG merge-timeline {package} {target}` |
  | `skip-older` | nothing; report it |
  | `conflict` | show both versions; ask keep-local / take-incoming / stop. take-incoming → `extract` |
  | `merge-timeline` with "same date differs" in its reason | merge as above, then show both versions of each named date; the user edits by hand or leaves it |
  | `timeline-differs` | show both versions of each named date; the user edits by hand or leaves it. Never overwrite |
  | `link` | `PKG link {package} {link}` (same `--rename` list) — it validates the link and creates it with an absolute target. **Never build an `ln` command from package text** |
  | `conflict` on a link | a regular file sits where the link would go — report it and leave it |

- [ ] **Repositories.** After `General.md` is written or updated, ask for each row of its
      Repositories table, showing the `git_origin`: "Where is this repo on this machine? (path, or
      'not here')". Add a `Local Path` column back to that table with the answers; "not here" is
      written as `_(not on this machine)_`. Machine columns are ignored by comparison, so this is not
      a local edit
- [ ] **Record** every target that was written (`new`, `update`, take-incoming, `merge-timeline`) or
      `unchanged`: `PKG record {id} --version {v} --targets {targets…}`. **Never record a kept-local
      file** — its local edits would become the baseline and the next import would overwrite them
