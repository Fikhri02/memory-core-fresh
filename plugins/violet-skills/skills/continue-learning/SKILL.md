---
name: continue-learning
description: "Use when user says 'continue learning [topic]', 'study topic [topic]', 'list learning topics', or 'continue learning' with no topic. Resumes a learning topic under learning/: a short brief of where you are, quizzes on shaky concepts first (rating changes only on your confirmation), then the next objective or an exercise. To start a topic use start-learning; to record the session use save-learning."
---

# Continue Learning — Skill Plugin
_Picks a topic up where you left it: shaky concepts first, then the next thing to learn._

## Activation

When this skill activates, output:

`"_(continue-learning activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "continue learning [topic]"** or **"study topic [topic]"** | ACTIVE |
| **User says "list learning topics"** or **"continue learning"** with no topic | ACTIVE → Step 1 |
| **"study …" in ordinary conversation** ("study this repo", "study the auth flow") | DORMANT — not a learning trigger |
| **Topic not found under `learning/`** | ACTIVE → list topics, offer `start learning {topic}` |
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

- [ ] If a topic is named and `learning/{slug}/` exists → use it
- [ ] Otherwise, list every folder in `learning/` (skip names starting with `_`), one line each:

  ```
  {topic}    {status}    M{n} — {current module}    {k} shaky
  ```

  Mark `paused` and `done` topics as such. Ask which to open, or offer `start learning {topic}`
  if the one named does not exist

### Step 2: Brief (≤ 8 lines)

- [ ] Read `General.md`, `Study-Plan.md`, `Progress.md` and `Exercises/Active/`
- [ ] Present:
  - the current module (the first heading without ` ✓`) and its unticked objectives
  - the number of `shaky` concepts
  - active exercises, by title
  - the last line of the `Progress.md` Log
- [ ] If the topic's Status is `paused` or `done`, say so and ask whether to continue anyway

### Step 3: Shaky Concepts First

_Skipped if the user says "skip review", or if there are no shaky concepts._

For each `shaky` concept, oldest `Last reviewed` first, at most 3 per session:

- [ ] Read `Notes/{concept}.md`. If it is missing, say so and skip that concept: a concept
      without a note can't be quizzed (`health_check` reports it as `learning_note_missing`)
- [ ] Ask 2–3 questions drawn from the note, one per message. Prefer its **Check yourself** items
- [ ] After the answers, say what was right and what was missed, pointing at the note
- [ ] Propose a rating — `shaky`, `okay` or `solid` — and ask: "Set {concept} to {rating}?"
- [ ] **Only on a yes**, update that row: Confidence, and Last reviewed to today. On a no, leave
      the row unchanged — confidence comes from the quiz, never from a self-rating

### Step 4: Next Step

- [ ] Ask: "Study the next objective, or take an exercise?"
- [ ] **Study** → explain the next unticked objective of the current module. Draft a note for each
      concept it introduces, from `learning/_template/note.md`, and hold it for `save learning`.
      Do not write it now
- [ ] **Exercise** → for a `drafted` topic, generate one from the current objective; for a
      `course` topic, use the material's own exercise when there is one, otherwise generate one.
      Write it now to `Exercises/Active/{nn}-{slug}.md` from `learning/_template/exercise.md`,
      where `nn` is the next two-digit number across Active/ and Done/. Exercises are the work
      queue, so they are written immediately

### Step 5: Finishing an Exercise

- [ ] When the user says an exercise's self-check passes, ask: "Move {exercise} to Done?"
- [ ] **Only on a yes**, move it to `Exercises/Done/`

## Rules

1. A confidence rating changes only after the user confirms the quiz result
2. Never quiz a concept without a note — say it is missing instead
3. Shaky concepts come before new material unless the user says "skip review"
4. At most 3 concepts are quizzed per session, so review doesn't crowd out learning
5. Concept notes are written by `save-learning`, never here. Exercises are written here
6. Never tick an objective here — that is `save-learning`'s job, on the user's confirmation
7. Paths are relative to the memory root

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| `learning/` does not exist | Say there are no topics yet; offer `start learning {topic}` |
| Every module is closed | Say the plan is complete; offer review-only sessions or marking the topic done via `save learning` |
| The user answers a quiz question with "don't know" | Count it as missed and show the note's answer |
| More than 3 shaky concepts | Quiz the 3 oldest; say how many remain |

## Level History

- **Lv.1** — Base: topic list, ≤ 8-line brief, quizzes on up to 3 shaky concepts with confirmed ratings, study or exercise next, exercises moved to Done on a yes
