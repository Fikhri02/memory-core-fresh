# Brainstorming

Persistent, categorised brainstorm sessions, written by the `brainstorm` skill
(**"let's brainstorm"**, **"continue brainstorm [name]"**).

---

## Lifecycle

```
active/     open — you can return to it in a later session
archived/   parked, not abandoned
done/       concluded
```

**The folder is the status.** Moving the file is the only state change.

A brainstorm in `archived/` or `done/` can still be reopened — the skill warns you about its
status first, then moves it back to `active/` if you continue.

## File shape

One file per topic, `{name}.md`, carrying:

- **Status**, **Created**, **Linked Project**
- **Task List** — actions the brainstorm produced
- **Session Log** — appended each time you return, so the thinking is preserved rather than
  overwritten

The log is why these are files and not chat scrollback: a brainstorm you return to three weeks
later still has its reasoning attached.

## Name collisions

`brainstorm` checks all three folders for `{name}.md` before creating anything and asks for
confirmation on a match. Names are global across the lifecycle, not per-folder.

## Relationship to `superpowers:brainstorming`

If the `superpowers` plugin is installed, its brainstorming output is redirected here —
`brainstorming/active/{name}.md`, **not** `docs/superpowers/specs/`. One store for brainstorms,
regardless of which tool produced them.

## When it becomes a plan

A brainstorm that has reached decisions should stop being a brainstorm. Say
**"plan brainstorm [name]"** and `project-planning` turns it into a phased plan under
`project-plans/active/`. See [`../project-plans/README.md`](../project-plans/README.md).
