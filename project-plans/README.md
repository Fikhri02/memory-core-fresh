# Project Plans

Phase-by-phase plans, written and advanced by the `project-planning` skill
(**"new project plan"**, **"plan brainstorm [name]"**).

---

## Lifecycle

```
active/     being worked through — one file per plan
archived/   paused or abandoned
done/       every phase complete
```

**The folder is the status.** A plan moves between folders; nothing carries a `status:` field
that could disagree with where the file actually sits.

## Two plan shapes

| Shape | Phases |
|-------|--------|
| UX / Product | 8 |
| Software feature | 4 |

The skill asks which one at the start and drives the phases in order.

## The symlink to the project

When a plan is created for a project that exists, `project-planning` links it into that project:

```bash
ln -s "$(pwd)/project-plans/active/{name}.md" "project-management/{name}/Plans/{name}-plan.md"
```

One file, two paths. The plan lives here and is *visible* from the project folder, so opening the
project surfaces it without a second copy to keep in sync.

`document-project` links plans into `Plans/` the same way. These are the only symlinks the
framework creates, and they are the one fragile thing in the layout: moving a plan between
`active/`, `archived/`, and `done/` breaks the link unless it is re-pointed, and a broken symlink
is invisible until something tries to read it. `health_check` scans for exactly this — run it
after moving plans.

## Plans vs brainstorms

| | Goes to |
|---|---|
| Exploring an idea, no decisions yet | `brainstorming/` |
| Decisions made, phases and sequence | `project-plans/` |

`project-planning` accepts **"plan brainstorm [name]"** to promote a finished brainstorm into a
plan — the intended path from one to the other.
