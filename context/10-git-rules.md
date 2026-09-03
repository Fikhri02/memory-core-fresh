---
module: git-rules
load: always
summary: How commits, branches, and pushes are handled.
---

# Git Rules

<!-- Edit these to match how you actually work. Delete this file if you don't want git rules. -->

- **Never commit or push unless explicitly asked.** Leave changes in the working tree; the user
  decides when history is written.
- **Never work directly on `main` or `master`.** Branch first — `feature/{slug}` or `hotfix/{slug}`.
- **Never force-push a shared branch.**
- Prefer staging specific files over `git add .`.
- Do not skip hooks (`--no-verify`) unless explicitly asked.
