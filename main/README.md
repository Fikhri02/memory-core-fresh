# Main Memory

Your companion's identity and working memory. This is the folder that makes the AI *yours* rather
than generic.

**Most of this folder does not exist until you run `python setup.py`.** Only the format
references ship with a fresh install.

---

## After setup

| File | What it holds | Loads |
|------|---------------|-------|
| `main-memory.md` | Identity, personality, your profile, communication style | Every session |
| `current-session.md` | **RAM** — the 3 most recent session recaps | Every session |
| `session-archive.md` | Older recaps, moved out verbatim | On demand |
| `preferences.md` | Output format, design language, writing rules | Design / documentation sessions only |
| `projects-context.md` | Per-project hints — which project needs `preferences.md` | When a project is loaded |

## Shipped with the repo

| File | What it is |
|------|-----------|
| `main-memory-format.md` | Reference structure for rebuilding `main-memory.md` |
| `session-format.md` | Reference structure for rebuilding `current-session.md`, plus the 500-line protocol |
| `session-brief-core.md` | The step-by-step protocol `session-briefing` executes at session start |

These are **references, not memory**. They are read when a file needs rebuilding, not every
session.

## The RAM / archive split

`current-session.md` is deliberately bounded — **3 sessions, 500 lines**. `save-memory` moves
older recaps to `session-archive.md` **verbatim**, never summarised on the way in. Summarising at
write time destroys detail you cannot get back; the archive stays lossless and is read only when
you ask for it.

If the file passes 500 lines, the AI preserves the `## Session Recap` section, rebuilds from
`session-format.md`, and continues. Working memory is cheap to lose because the recap survives.

## What belongs where

| Fact | Home |
|------|------|
| Who you are, how you like to work | `main-memory.md` |
| What we did last session | `current-session.md` — written by `save-memory` |
| A rule that should shape *every* session | `context/` — not here |
| Anything about one project | `project-management/{name}/` |

`context/` and `main/` overlap in spirit and differ in mechanics: `context/` modules are small,
hand-written, and load on a condition; `main/` is larger, partly AI-maintained, and loads by
role. A durable rule belongs in `context/`; a fact about *you* belongs here.

## Editing

`main-memory.md` and `preferences.md` are yours — edit them freely, they are only rewritten if
you ask. `current-session.md` and `session-archive.md` are managed by `save-memory`; hand-editing
them is allowed but will be overwritten at the next save.
