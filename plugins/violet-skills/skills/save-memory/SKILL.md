---
name: save-memory
description: "MUST use when user says 'save', 'save memory', 'save progress', 'update memory', or when important information needs to be preserved to memory files."
---

# Save Memory — Skill Plugin
*MUST use when user says 'save', 'save memory', 'save progress', 'update memory',...*

## Activation

When this skill activates, output:

`"Saving memory..."`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "save"** | ACTIVE |
| **User says "save memory"** | ACTIVE |
| **User says "save progress"** | ACTIVE |
| **User says "update memory"** | ACTIVE |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

- [ ] **Step 1**: Review conversation for new preferences, decisions, or context worth preserving
- [ ] **Step 2**: Update session recap, active project, what was done — `main/current-session.md`
- [ ] **Step 3**: Update if the user's profile or the companion's preferences evolved — `main/main-memory.md` *(condition: if_profile_evolved)*
- [ ] **Step 4**: Trim session history — keep the **3 most recent** session blocks in `main/current-session.md`; move anything older, verbatim, to the top of `main/session-archive.md`
- [ ] **Step 5**: If project work happened this session, suggest — but do not run — `save project` so the project Timeline gets its own entry
- [ ] **Step 6**: Report: 'Memory saved.'

## Rules

1. Only update main-memory.md when genuine new knowledge about the user or the companion has emerged
2. current-session.md always updated on save
3. `current-session.md` is RAM, not a log — at most 3 prior session blocks. Older blocks move to `main/session-archive.md` unchanged; never summarise or delete them on the way out
4. Bare `"save"` belongs to this skill. It never writes project files — it suggests `save project` and lets the user decide

## Level History

- **Lv.2** — Current behaviour, as described in the Protocol and Rules above
