---
name: brain-recall
description: "Use when user says 'what do I think about [topic]', 'recall brain [topic]', 'list brain', 'search brain [term]', 'what have I thought about for [project]', or 'stale brain'. Reads the theoretical topic files under brain/ — lookup, browse, search, project view, and health. Strictly read-only: never writes a file."
---

# Brain Recall — Skill Plugin

_Reads the brain. Never writes to it._

## Activation

When this skill activates, output:

`"_(brain-recall activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "what do I think about {topic}"** | ACTIVE → lookup |
| **User says "recall brain {topic}"** | ACTIVE → lookup |
| **User says "list brain"** or **"list brain {domain}"** | ACTIVE → browse |
| **User says "search brain {term}"** | ACTIVE → search |
| **User says "what have I thought about for {project}"** | ACTIVE → project-view |
| **User says "stale brain"** | ACTIVE → health |
| **Mid-conversation (no trigger context)** | DORMANT |

`"recall {topic}"` without the word `brain` is **not** a trigger. `AGENTS.md` documents a broader
`"recall [topic]"` command covering all of memory; this skill does not claim it.

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## The Invariant

**This skill never writes a file.** Not a brain topic, not a project file, not a note. When it
finds a problem it reports it and at most suggests running `brain` to fix it.

If `brain/` does not exist, say so and stop. Do not create it — that is `brain`'s job.

## Protocol

### lookup

- [ ] **Step 1**: Slugify the topic; find `brain/**/{slug}.md`.
- [ ] **Step 2**: If two domains hold the same slug, **report the ambiguity and list both paths**.
      Never pick one.
- [ ] **Step 3**: If nothing matches, say so and offer the three closest slugs by name similarity.
- [ ] **Step 4**: Return `## Current Thinking`, the unchecked items under `## Open Questions`, and
      the date of the most recent `## Log` entry. **Not the whole file** — the point is the
      position, not the transcript.

---

### browse

- [ ] **Step 1**: Walk `brain/*/` (or the single named domain).
- [ ] **Step 2**: Per topic print slug, `**Status**`, and the date of its latest `## Log` entry.
- [ ] **Step 3**: Group by domain, domains alphabetical, topics newest-touched first:

  ```
  database/
    event-sourcing        evolving   2026-09-26
    multi-tenancy         settled    2026-08-11
  ux/
    onboarding-patterns   evolving   2026-09-26
  ```

---

### search

- [ ] **Step 1**: Search `brain/**/*.md` for the term, case-insensitively.
- [ ] **Step 2**: Rank hits by **where they landed**, not by count:
      `## Current Thinking` > `## Open Questions` > `## Implications` > `## Log`.
      A match in the current position outranks one buried in a two-year-old log entry.
- [ ] **Step 3**: Print the topic path, the section the hit landed in, and the matching line.

---

### project-view

- [ ] **Step 1**: Collect every topic whose header carries `**Project**: {project}`.
- [ ] **Step 2**: Print each with its `## Current Thinking` line.
- [ ] **Step 3**: If the project has a `project-management/` entry, say so. If it does not, say
      that too — the field is allowed to name an untracked project.

---

### health

- [ ] **Step 1**: Topics with `**Status**: evolving` whose latest `## Log` entry is more than 90
      days old.
- [ ] **Step 2**: `[[links]]` in any `**Related**` field with no matching file. Report these as
      **opportunities, not errors** — a link with nothing behind it marks a topic worth writing.
- [ ] **Step 3**: Slugs appearing in two or more domains, with both paths.
- [ ] **Step 4**: Report all three groups. Suggest `brain` for anything worth acting on. **Fix
      nothing.**

## Rules

1. **Never writes a file.** This is the skill's defining property, not a guideline.
2. Never creates `brain/` — if the store is absent, report and stop.
3. Ambiguous slugs are reported with both paths, never resolved by guessing.
4. Unresolved `[[links]]` are opportunities, not errors.
5. lookup returns the position, not the whole file.
6. `"recall {topic}"` without `brain` is not this skill's trigger.

## Level History

- **Lv.1** — Base: lookup, browse, search with section-ranked hits, project view, and health
  across staleness, unresolved links, and cross-domain slug collisions.
