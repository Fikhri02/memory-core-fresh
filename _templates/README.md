# Templates

Unrendered source files carrying `{{PLACEHOLDER}}` tokens. `setup.py` copies each one out,
substitutes your answers, and writes the result elsewhere.

**Nothing here is ever mutated.** Setup reads from this folder and writes to a destination, so
re-running it always starts from a clean source. That is what makes `--reset` safe.

---

## What goes where

| Source | Destination | Written by |
|--------|-------------|------------|
| `main/*.md` (5 files) | `main/` | `step_write_memory_files` |
| `USER-GUIDE.md` | `USER-GUIDE.md` (repo root) | same step — root-level `*.md` are rendered too |

The spec is handled separately: `memory-core-template.yaml` sits at the repo root, not here, and
renders to `memory-core.yaml`.

## The tokens

| Token | Source | Required |
|-------|--------|----------|
| `{{COMPANION_NAME}}` | prompt | yes |
| `{{USER_NAME}}` | prompt | yes |
| `{{USER_EMAIL}}` | prompt | no |
| `{{USER_COMPANY}}` | prompt | no |
| `{{USER_ROLE}}` | prompt, defaults to `Developer` | no |
| `{{USER_GIT_USERNAME}}` / `{{GIT_USERNAME}}` | prompt — both map to one answer | no |
| `{{USER_LOCATION}}` | always empty | no |
| `{{SETUP_DATE}}` | today's date | auto |

Optional tokens that you skip are replaced with an **empty string**, not left as `{{...}}`. A
literal `{{` surviving into a rendered file means a token was used here but never declared in
`collect_inputs()`.

## Adding a template

1. Put the file in `_templates/main/` (or `_templates/` for a root-level doc).
2. Use only tokens from the table above, or add a new one to `collect_inputs()` in `setup.py`.
3. Re-run `python setup.py --reset`.

`step_write_memory_files` globs `*.md`, so a new file is picked up with no code change — but a
new *token* is not. Adding `{{FAVOURITE_COLOUR}}` without touching `setup.py` ships the literal
text to the user.

## The re-run guard

`is_already_setup()` decides whether setup has run by checking one thing: whether
`memory-core.yaml` still contains `{{COMPANION_NAME}}`. That is why the token must survive
verbatim in the template — renaming it breaks the guard, and setup will re-prompt every time.
