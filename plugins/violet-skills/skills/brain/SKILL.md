---
name: brain
description: "Use when user says 'brain on [topic]', 'open brain [topic]', 'think through [topic]', 'discuss [topic] theoretically', 'continue brain [topic]', 'save brain', 'mark brain [topic] settled', or 'park brain [topic]'. Captures theoretical discussion — architecture, frameworks, databases, UI/UX — as accumulating topic files under brain/. Builds nothing: never writes code, scaffolds a project, or creates a plan."
---

# Brain — Skill Plugin

_Theoretical thinking, accumulated. The store that builds nothing._

## Activation

When this skill activates, output:

`"_(brain activates)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "brain on {topic}"** | ACTIVE → brain-start |
| **User says "open brain {topic}"** | ACTIVE → brain-start |
| **User says "think through {topic}"** | ACTIVE → brain-start |
| **User says "discuss {topic} theoretically"** | ACTIVE → brain-start |
| **User says "continue brain {topic}"** | ACTIVE → brain-resume |
| **User says "save brain"** | ACTIVE → brain-save |
| **User says "mark brain {topic} settled"** | ACTIVE → status-transition |
| **User says "park brain {topic}"** | ACTIVE → status-transition |
| **Implementation work in progress** | DORMANT |
| **Mid-conversation (no trigger context)** | DORMANT |

**DORMANT rows win.** When a phrase in this table matches during implementation or debugging
work, the DORMANT row takes precedence and the skill stays silent — `"let me think through why
this lock is held"` mid-debugging is not a brain trigger. `"let's think about X"` is deliberately
**not** a trigger at all, for the same reason. Bare `"save"` belongs to `save-memory`.

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### brain-start

- [ ] **Step 1**: Slugify the topic (lowercase, hyphenated).
- [ ] **Step 2**: Search `brain/**/` for `{slug}.md`. If exactly one file matches, hand to
      **brain-resume** — never create a second file for a topic that already exists. If **two or
      more domains hold the same slug**, stop and list every path, then ask which one is meant.
      Never pick one: the writer appends to an append-only log, so guessing wrong puts the entry
      on the wrong topic's record permanently.
- [ ] **Step 3**: **Resolve the domain.** List the existing folders under `brain/`. Match the topic
      against them case-insensitively and across singular/plural. Propose an existing domain
      before inventing one — `database/` must never gain a `databases/` sibling. Inventing a new
      domain requires an explicit yes from the user.
- [ ] **Step 4**: Discuss. **Write nothing.** Track insights silently for the flush.

**The file is created on save, not on start.** A discussion abandoned after two messages leaves
nothing behind — no empty stubs to clean up later.

---

### brain-save

- [ ] **Step 1**: Identify every topic the session touched. A session that was half implementation
      and half theory captures only the theory threads, and names which threads it ignored.
- [ ] **Step 2**: If nothing theoretical was discussed, say so and write nothing. Stop here.
- [ ] **Step 3**: Create `brain/` and `brain/README.md` if the store does not exist yet.
- [ ] **Step 4**: **Resolve the domain for every topic Step 1 discovered that was not already
      resolved this session** — run brain-start Step 3's normalisation for each, so a topic the
      conversation drifted into cannot create `ux/` beside an existing `ui-ux/`. Then **present
      the write plan and wait for confirmation** — every path, marked new or existing, with the
      last-touched date on existing files, and any newly-invented domain called out by name so
      the confirmation is a taxonomy decision and not just a file list:

  ```
  This session touched 3 topics:
    database/event-sourcing.md      (new)
    database/multi-tenancy.md       (exists, last 2026-08-11)
    ux/onboarding-patterns.md       (new — creates new domain "ux")

  Write all 3?  [y / pick / rename]
  ```

- [ ] **Step 5**: Per topic, append one dated `## Log` entry scoped to **only that thread** of the
      conversation. If a section for today's date already exists — a second save in one day —
      extend that section rather than opening a duplicate one:

  ```
  ### YYYY-MM-DD
  **Explored**: [what was reasoned about]
  **Landed on**: [the position reached, and why]
  **Rejected**: [what was considered and dropped, with the reason]
  **Still open**: [the question that remains — a question, never a task]
  ```

- [ ] **Step 6**: Smart-check `## Current Thinking` — rewrite it (1–3 lines) only if the position
      actually moved this session. If the discussion refined detail without changing the view,
      leave it alone.
- [ ] **Step 7**: Update `## Open Questions` — add what surfaced, check off what was resolved.
- [ ] **Step 8**: If the discussion turned genuinely actionable, write `## Implications` capturing
      what it would mean if built, then offer the handoff **once**:
      "This could become a brainstorm — want me to start one?" If declined, drop it and do not
      raise it again for that topic this session. **On yes, invoke the `brainstorm` skill's
      brainstorm-start and let it author the file** — `brain` never writes into `brainstorming/`
      itself, because the brainstorm format is that skill's to own and a file written in brain's
      format cannot be reopened by `brainstorm-resume`.
- [ ] **Step 9**: If `**Project**:` is set and `project-management/{project}/` exists, offer to add
      one line to that project's `Timeline.md` pointing back at the brain file. Never automatic.
      If the named project has no entry, keep the field, skip the offer, and say why.
- [ ] **Step 10**: Cross-link the topics touched in this session into each other's `**Related**`.
- [ ] **Step 11**: Report: files written, topics created, offers made.

---

### brain-resume

- [ ] **Step 1**: Locate `brain/**/{slug}.md`. If no file exists, offer to start the topic —
      never create it silently. If two or more domains hold the slug, list every path and ask
      which is meant before recapping anything — resuming the wrong file recaps the wrong position
      and then appends this session to it.
- [ ] **Step 2**: Read `## Current Thinking` and the most recent `## Log` entry. Deliver a two-line
      recap: the current position, and the question left open.
- [ ] **Step 3**: Continue the discussion. Writes still happen only on `"save brain"`.

---

### status-transition

- [ ] **"mark brain {topic} settled"**: set `**Status**: settled`.
- [ ] **"park brain {topic}"**: ask for a reason, set `**Status**: parked`, append
      `**Parked Reason**: {reason}` to the header block.

Nothing moves on the filesystem — the folder carries the domain, not the status.

## Rules

1. **Builds nothing.** Never writes code, scaffolds a project, or creates a brainstorm or plan on
   its own initiative. The handoff in brain-save Step 8 is an offer, made once, and dropped when
   declined.
2. Never invents a domain folder without an explicit yes.
3. `## Log` entries append. A prior dated entry is never rewritten or deleted — a position since
   abandoned stays on the record with the date it was held.
4. `## Current Thinking` is the only rewritable **prose** region. Header fields (`**Status**`,
   `**Related**`, `**Project**`) and the checkboxes under `## Open Questions` are maintained in
   place; everything under `## Log` is append-only.
5. Files are created on save, never on start.
6. Never writes into `project-management/` beyond the single offered Timeline line.
7. The log's fourth field is **Still open** — a question. Never "Next Steps", never a task.
8. Bare `"save"` belongs to `save-memory`; brain-save requires the explicit `"save brain"`.

## Level History

- **Lv.1** — Base: topic files in free-form domain folders, passive capture flushed on save,
  multi-topic split with a confirmed write plan, offered project Timeline line, and a
  single-offer handoff to `brainstorm`.
