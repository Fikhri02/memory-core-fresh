---
name: start-learning
description: "Use when user says 'start learning [topic]' or 'new learning topic [topic]'. Creates a learning topic under learning/ — goal and level, a study plan drafted from research or mirrored from a named course, a concept table for confidence tracking, and links to projects that exercise it. To resume a topic use continue-learning; to record a study session use save-learning."
---

# Start Learning — Skill Plugin
_Creates a learning topic: goal, study plan, the concepts to track, and the projects that exercise it._

## Activation

When this skill activates, output:

`"_(start-learning activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "start learning [topic]"** | ACTIVE |
| **User says "new learning topic [topic]"** | ACTIVE |
| **User says "learn …" or "new topic …" in ordinary conversation** | DORMANT — only the explicit phrases above start a topic |
| **The topic already exists under `learning/`** | DORMANT — offer `continue learning {topic}` instead |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### Step 1: Resolve the Topic

- [ ] Use the topic given, else ask: "What do you want to learn?"
- [ ] Slugify it: `Keycloak` → `keycloak`, `Rust async` → `rust-async`
- [ ] If `learning/{slug}/` exists → say so and offer `continue learning {slug}`. **Never overwrite**

### Step 2: Goal and Level

Ask one question per message:

- [ ] "What do you want to be able to do when you're done?" → **Goal**
- [ ] "Why now?" → **Why** (one line)
- [ ] "Where are you starting from?" → current level
- [ ] "Where do you want to get to?" → target level

### Step 3: Choose the Source

- [ ] Ask: "Should I draft a study plan, or are you following a course, book or docs?"
- [ ] **Drafted** → research the topic with web search, and the `deep-research` skill when it is
      available: official docs first, then a recognised course outline, then one or two
      practitioner sources. Propose 4–8 modules in a sensible order. Each module has 2–4 objectives
      phrased as abilities ("Explain …", "Configure …") and the concepts it introduces, as
      kebab-case ids. Record every source with its URL and today's date for **Resources**
- [ ] **Course** → ask for the course, book or docs and its chapter list, or read the table of
      contents if a URL is given. One module per chapter or section; objectives come from the
      material's own stated outcomes. **Invent nothing beyond it.** Where the material states no
      outcome, the single objective is "Complete {chapter}"

### Step 4: Present the Draft

- [ ] Show:

  ```
  Topic:     {Topic} ({slug})
  Goal:      {goal}
  Level:     {current} → {target}
  Source:    drafted | course — {name}
  Modules:
    M1 — {name}: {n} objectives · concepts: {a}, {b}
    M2 — …
  Resources: {n} cited

  Confirm, or tell me what to change.
  ```

- [ ] **Wait.** No file is written before the user confirms

### Step 5: Scaffold

- [ ] Read `learning/_template/structure.yaml`. **Never hardcode the folder or file list**
- [ ] Create every folder under `folders:` and every file under `files:` from its template
- [ ] Fill `General.md`: Status `active`, Source, Started (today), Goal, Why, Level, and the Resources table
- [ ] Fill `Study-Plan.md`: one `## M{n} — {name}` heading per module, objectives as `- [ ]`, then `Concepts: a, b`
- [ ] Fill `Progress.md`: one row per concept, `| {concept} | M{n} | — | — | Notes/{concept}.md |`. Leave the Log empty

### Step 6: Link Projects

- [ ] List the folders in `project-management/`, skipping names that start with `_`. Ask:
      "Do any of these exercise {topic}? (names, or none)"
- [ ] For each one picked, write a line to `Projects.md`: ``- `{project}` — {what it exercises, in the user's words}``.
      Never copy project content

### Step 7: Report

- [ ] "Started **{topic}** — {m} modules, {c} concepts, {p} linked project(s). Say `continue learning {slug}` to begin M1."

## Rules

1. Nothing is written before the draft is confirmed
2. A course-sourced plan mirrors the material — never add modules or objectives it does not contain
3. A drafted plan cites every source with its URL and the date accessed
4. Every concept starts at `—`; only `save-learning` and confirmed quizzes change confidence
5. Projects are linked by name only; `project-management/` is never written from here
6. Paths are relative to the memory root — never scaffold `learning/` in the repo that happens to be open

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| `learning/_template/` is missing | Say the install is incomplete and stop |
| The slug matches an existing topic | Offer `continue learning {slug}`, or ask for a different name |
| No projects under `project-management/` | Skip Step 6; leave `Projects.md` as its template |
| Research finds nothing authoritative | Say so; propose a smaller plan from what was found, and note "thin sources" under Resources |

## Level History

- **Lv.1** — Base: topic scaffold from `learning/_template/`, a drafted (researched, cited) or course-mirrored study plan, a concept table at `—`, and projects linked by name
