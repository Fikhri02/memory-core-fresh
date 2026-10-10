---
name: brainstorm
description: "Triggers on 'Let's brainstorm', 'Start brainstorm', 'plan an idea', 'save brainstorm', 'continue brainstorm [name]', 'archive brainstorm [name]', 'mark brainstorm [name] done', 'link brainstorm [name] to [project]'."
---

# Brainstorm — Skill Plugin

_Manages brainstorming sessions as persistent, categorized files. Extends superpowers:brainstorming._

## Activation

When this skill activates, output:

`"_(brainstorm activates)_"`

## Context Guard

| Context                                             | Status                     |
| --------------------------------------------------- | -------------------------- |
| **User says "Let's brainstorm"**                    | ACTIVE → brainstorm-start  |
| **User says "Start brainstorm"**                    | ACTIVE → brainstorm-start  |
| **User says "plan an idea"**                        | ACTIVE → brainstorm-start  |
| **User says "save brainstorm"**                     | ACTIVE → brainstorm-save   |
| **User says "save brainstorm"** (bare "save" belongs to save-memory) | ACTIVE → brainstorm-save   |
| **User says "continue brainstorm {name}"**          | ACTIVE → brainstorm-resume |
| **User says "archive brainstorm {name}"**           | ACTIVE → status-transition |
| **User says "mark brainstorm {name} done"**         | ACTIVE → status-transition |
| **User says "link brainstorm {name} to {project}"** | ACTIVE → status-transition |
| **Mid-conversation (no trigger context)**           | DORMANT                    |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### brainstorm-start

- [ ] **Step 1**: Prompt user for brainstorm name
- [ ] **Step 2**: Check `brainstorming/active/`, `brainstorming/archived/`, `brainstorming/done/` for `{name}.md` — if found, ask for confirmation before proceeding
- [ ] **Step 3**: Create `brainstorming/active/{name}.md` with standard file format (Status: active, Created: today, Linked Project: none, empty Task List, empty Session Log)
- [ ] **Step 4**: Invoke `superpowers:brainstorming` skill — the full thinking/design process runs through that flow
- [ ] **Step 5**: Save outputs (design notes, decisions, task list) into the Session Log under today's date — do NOT save to `docs/superpowers/specs/`

**File format to use when creating:**

```markdown
# {Brainstorm Name}

**Status**: active
**Created**: YYYY-MM-DD
**Linked Project**: none
**Overall Summary**: _(not yet written)_

---

## Task List

_(empty — populate during brainstorm session)_

---

## Session Log

### YYYY-MM-DD

**Summary**:
**Decisions**:
**Rejected Ideas**:
**Next Steps**:
```

---

### brainstorm-save

- [ ] **Step 1**: Write today's structured session entry into the Session Log — always append, never overwrite

  ```
  ### YYYY-MM-DD
  **Summary**: [what was explored and decided this session]
  **Decisions**: [non-obvious choices made and why]
  **Rejected Ideas**: [what was considered and dropped, with reason]
  **Next Steps**: [what to work on next]
  ```

- [ ] **Step 2**: Smart-check — did anything significant change? (new decision, direction shift, tasks added/completed)
  - If yes → rewrite Overall Summary (1–3 lines) to reflect latest state
  - If no → leave Overall Summary unchanged
- [ ] **Sync upload**: if `device/sync.md` exists, run the **Upload** in `session-briefing` Step 0s with the label `save brainstorm {name}`
- [ ] **Step 3**: Confirm: "Brainstorm saved."

---

### brainstorm-resume

- [ ] **Step 1**: Locate `{name}.md` — search `brainstorming/active/` first, then `archived/`, then `done/`. If found in `archived/` or `done/`, warn the user of its status before continuing.
- [ ] **Step 2**: If today's date does not exist in Session Log → open a new date section with empty fields
- [ ] **Step 3**: Read Overall Summary + last session entry → deliver 1–2 line recap (last task worked on + next task)
- [ ] **Step 4**: Ask: "Want to continue the brainstorm or review the task list first?"
  - If continue → re-invoke `superpowers:brainstorming` with existing decisions as context
  - If task list → display unchecked tasks only

---

### status-transition

- [ ] **"link brainstorm {name} to {project}"**:
  1. Find `{name}.md` in any folder
  2. Update `**Linked Project**:` field to `{project}`
  3. Move file from current location to `brainstorming/active/{name}.md`
  4. Confirm: "Brainstorm {name} linked to {project} and moved to active."

- [ ] **"archive brainstorm {name}"**:
  1. Find `{name}.md`
  2. Prompt: "Reason for archiving?"
  3. Append `**Archive Reason**: {reason}` to the header block
  4. Move file to `brainstorming/archived/{name}.md`
  5. Confirm: "Brainstorm {name} archived."

- [ ] **"mark brainstorm {name} done"**:
  1. Find `{name}.md`
  2. Update `**Status**:` field to `done`
  3. Move file to `brainstorming/done/{name}.md`
  4. Confirm: "Brainstorm {name} marked as done."

---

## Rules

1. Never overwrite existing session log entries — always append
2. brainstorm-start must check all three folders (active, archived, done) before creating
3. superpowers:brainstorming output saves to `brainstorming/active/{name}.md`, not `docs/superpowers/specs/`
4. Archived files retain all session history — only a reason note is added
5. brainstorm-resume on an archived/done file warns the user of its status before continuing
6. Bare "save" belongs to `save-memory` — brainstorm-save requires the explicit "save brainstorm"

## Level History

- **Lv.1** — Current behaviour, as described in the Protocol and Rules above
