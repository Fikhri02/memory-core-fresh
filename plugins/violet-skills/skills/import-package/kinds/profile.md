# Kind: profile

The companion memory under `main/`.

**Id:** `profile@{user-slug}` for `self`, `profile@shared` for `share` — a share id must not carry the
name the export strips. **Export file:** `migrations/out/{id}.v{n}.pkg.md`

`PKG` = `python3 plugins/violet-skills/skills/import-package/scripts/pkgtool.py`, run from the memory root.

Names come from `memory-core.yaml` → `identity.name` (companion) and `identity.user.name` (user).

## Export — collect

| Source | self | share | Staged as |
|---|:-:|:-:|---|
| `main/main-memory.md`, each `## ` section | ✓ | companion sections ✓, user sections → template | `main/main-memory.md#{heading}` |
| `main/preferences.md` | ✓ | ✓ (names → placeholders) | `main/preferences.md` |
| `main/projects-context.md` | ✓ | — | same path |
| `main/current-session.md`, `main/session-archive.md` | ✓ | — | same path |

Never staged: `main/README.md`, `main-memory-format.md`, `session-format.md`, `session-brief-core.md`
— they ship with the repo.

- [ ] Run `PKG profile-headings main/main-memory.md --companion "{companion}"`. Every heading marked
      `user` that is not one of `Identity & Relationship`, `{user} Profile`, `Relationship Context` is
      **unknown** — list it in the manifest; it is treated as user (the safe default)
- [ ] For each heading, write the section (heading line through the line before the next `## `) to
      `migrations/.staging/{id}/main/main-memory.md#{heading}`:
  - `self`: the section as-is
  - `share`, `companion`: the section, then `PKG placeholders {staged} --user "{user}" --companion "{companion}" --write`
  - `share`, `user`: the matching section from `main/main-memory-format.md` — `Identity & Relationship`
    → same heading; `{user} Profile` → `[YOUR_NAME] Profile`, renamed to `{{USER_NAME}} Profile`;
    `Relationship Context` → same heading — with `[AI_NAME]` → `{{COMPANION_NAME}}` and
    `[YOUR_NAME]` → `{{USER_NAME}}`. No template match: the heading line, a blank line, and
    `<!-- left blank in a shared profile -->`
- [ ] Stage the whole files the table allows for the audience; for `share`, run `PKG placeholders … --write` on each
- [ ] For `share`: `PKG scan` every staged file
- [ ] For `self`: warn once — "This file holds your personal history. Do not commit it to a repo or
      put it on a shared drive."

## Export — header

```json
{"header": {"package": "profile@{user-slug}|profile@shared", "kind": "profile",
            "audience": "{self|share}", "version": N, "exported": "YYYY-MM-DD", "format": 2,
            "source_install": "{user}@{host}"},
 "header_extra": "", "links": []}
```

`source_install` for `self` only.

## Import — place

- [ ] If `main/main-memory.md` does not exist, create it with
      `# {companion} - Main Memory` and `*Unified identity, relationship, and personality*` before
      writing any section. In a share package, ask the user for both names first and substitute them
      for `{{COMPANION_NAME}}` / `{{USER_NAME}}` in everything written
- [ ] Run `PKG plan {package} --root .` and act per audience:

  **self**

  | Action | Do |
  |---|---|
  | `new`, `update` | `PKG extract {package} {target}` |
  | `unchanged`, `skip-older` | nothing |
  | `conflict` on a `main-memory.md#…` section | ask keep-local / take-incoming / keep both. take-incoming → `extract`. keep both → append the incoming section's body to the local section under `### Imported {YYYY-MM-DD}` |
  | `conflict` on `current-session.md` or `session-archive.md` | ask replace-whole / skip. Never merge |
  | `conflict` on `preferences.md`, `projects-context.md` | ask keep-local / take-incoming |

  **share** — only `new` targets are written (`extract`, then substitute names). Every `conflict` is
  skipped and reported: a template never replaces a filled section.

- [ ] **Record** written and unchanged targets with `PKG record` — never kept-local or keep-both ones
