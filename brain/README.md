# Brain

Theoretical thinking, accumulated. Architecture, frameworks, databases, UI/UX — reasoned about
rather than built.

Written by the `brain` skill (**"brain on [topic]"**, **"save brain"**).
Read by the `brain-recall` skill (**"what do I think about [topic]"**, **"list brain"**).

---

## What belongs here

Thinking that is not attached to a deliverable and is not meant to become one. A comparison of
event-sourcing against a mutable-state model. Why a modular monolith beats microservices at your
team size. What multi-tenancy actually costs at the database layer.

**This store builds nothing.** The `brain` skill never writes code, never scaffolds a project,
never creates a plan. When a discussion turns genuinely actionable it records the consequence
under `## Implications` and offers — once — to start a brainstorm. Decline and it drops the
subject.

## What belongs elsewhere

| If it is... | It goes to |
|-------------|-----------|
| An idea you intend to build | `brainstorming/` — it graduates into `project-plans/` |
| Findings about code that actually exists | `notes/` — evidence, not theory |
| A debugging hunt and its root cause | `debugging/` |
| A repository's real architecture | `notes/architecture-review/` |

## Layout

```
brain/
  README.md              this file
  {domain}/{topic}.md    one file per topic
```

Domains are exactly **one level deep**: a topic is `brain/{domain}/{topic}.md`, never
`brain/{domain}/{sub}/{topic}.md`. A topic that wants a sub-domain is a sign the domain should be
split, not nested — `brain-recall`'s browse walks one level and a nested file would be invisible
to it.

Domains are **free-form** — created on demand, not from a fixed list. The skill proposes an
existing domain before inventing a new one, matching case-insensitively and across
singular/plural, so `database/` never gains a `databases/` sibling. A new domain requires your
explicit yes.

## File shape

```markdown
# Event Sourcing

**Domain**: database
**Status**: evolving          # evolving | settled | parked
**Project**: acme-shop        # optional — omitted entirely when not project-bound
**Created**: 2026-09-26
**Related**: [[cqrs]], [[multi-tenancy]]

---

## Current Thinking
_(1–3 lines. Rewritten only when the view actually changes — not on every save.)_

## Open Questions
- [ ] ...

## Implications
_(What this would mean if built. Written only when a discussion turns actionable.
Empty is the normal state.)_

## Log
### YYYY-MM-DD
**Explored**:
**Landed on**:
**Rejected**:
**Still open**:
```

`Current Thinking` is the only rewritable region. Everything under `Log` is append-only — a
position you have since abandoned stays on the record, with the date you held it.

**The log has no "Next Steps".** Its fourth field is **Still open** — a question, not a task.
That is the wall between this store and `brainstorming/`, written into the file format itself.

## Status is a field, not a folder

Everywhere else in memory-core the folder *is* the status — `brainstorming/active|archived|done`,
`project-plans/`, `migrations/in|out|applied`. Here the folder carries the **domain**, so status
lives in the header instead.

This is a deliberate divergence. Domain is the axis you actually browse by, and a topic is rarely
"done" the way a plan is — it settles, or it gets parked, and either can reopen.

## Links

`**Related**: [[cqrs]]` uses a bare slug, never `[[database/cqrs]]`. Because domains are
free-form, a topic can be reclassified later; a bare slug survives the move and a pathed one does
not. `brain-recall` resolves links by filename and reports an ambiguity rather than guessing when
two domains hold the same slug.

A `[[link]]` with no file behind it is an **opportunity, not an error** — it marks a topic worth
writing. `"stale brain"` lists them as such.

## Privacy

Only this README is tracked in git. Your topic files are personal content and stay untracked,
the same as `main/` and `project-management/{project}/`. Note that they are untracked by
discipline, not by `.gitignore` — `git add -A` would sweep them in.
