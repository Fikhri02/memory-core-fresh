---
name: save-learning
description: "MUST use when user says 'save learning'. Records a study session on a learning topic: ticks the objectives you confirm, writes concept notes, adds new concepts at shaky, appends the dated log, and asks before closing a module or the topic. Bare 'save' belongs to save-memory, which suggests this skill instead of running it."
---

# Save Learning — Skill Plugin
_Records what you studied: objectives met, concepts learned, and the log._

## Activation

When this skill activates, output:

`"_(save-learning activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "save learning"** | ACTIVE |
| **User says "save" (bare)** | DORMANT — belongs to save-memory, which suggests this skill |
| **No study happened this session** | DORMANT — say there is nothing to record |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### Step 1: Identify the Topic

- [ ] Use the topic worked on this session. If several, or none is clear, ask which

### Step 2: Objectives

- [ ] List the objectives in `Study-Plan.md` that look met this session, with the evidence (an
      explanation given back, an exercise passed)
- [ ] Ask: "Tick these?" — tick **only** the ones the user confirms

### Step 3: Concept Notes

- [ ] For each concept studied: write or update `Notes/{concept}.md` from
      `learning/_template/note.md`. Updates are additive — never delete what a note already says
- [ ] Each note's **Check yourself** gets 2–3 questions whose answers are in the note. These are
      what `continue-learning` asks later
- [ ] A concept learned for the first time: set its `Progress.md` row to `shaky` with today's date.
      If the concept has no row, add one: `| {concept} | M{n} | shaky | {today} | Notes/{concept}.md |`
- [ ] Never change an existing rating here — ratings change only through confirmed quizzes

### Step 4: Log

- [ ] Append to the `## Log` in `Progress.md`, under today's `### YYYY-MM-DD` (create it if
      absent), one line each for what was studied, reviewed (with any rating changes), and
      exercised

### Step 5: Closing Modules and the Topic

- [ ] If every objective of the current module is ticked, ask: "Close M{n}?" On a yes, add ` ✓`
      to its heading
- [ ] If every module is closed, ask: "Mark {topic} done?" On a yes, set `**Status**: done` in
      `General.md`

### Step 6: Report

- [ ] "Saved **{topic}** — {o} objective(s) ticked, {c} concept note(s), {n} new at shaky."
      Then list every file touched and what went into each

## Rules

1. Objectives are ticked only on the user's confirmation
2. New concepts enter at `shaky`; existing ratings are never changed here
3. Every rated concept has a note — a row is added only together with its note
4. Notes are additive; the log is append-only
5. Closing a module or finishing a topic is always asked, never assumed
6. Bare "save" belongs to save-memory — this skill runs only on "save learning"
7. Paths are relative to the memory root

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| No study happened | Say "Nothing to record for learning this session" and stop |
| A concept isn't in the study plan | Add its row under the current module and say so — plans grow as you learn |
| The topic is `paused` | Record the session and ask whether to set it back to `active` |

## Level History

- **Lv.1** — Base: confirmed objective ticks, additive concept notes with quiz questions, new concepts at shaky, append-only log, asked module and topic closure
