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
- [ ] **Step 2**: Update own RAM (`session-briefing` Step 0a; `python3 mcp-spike/ram.py ensure` creates it):
      session recap, active project, what was done. Add the new session block **above** the older
      ones. Then refresh the header: `python3 mcp-spike/ram.py stamp "<one-line summary of this session>"`

      **Rewrite** — never append to — the `## Session RAM Status` section. It holds exactly three keys:

      ```markdown
      ## Session RAM Status
      **Focus**: <one line: what the next session most likely picks up>
      **Repos**:
      - `~/path/to/repo` · branch-name
      **Open loops**:
      - <something waiting on the user or on a date — at most 5>
      ```

      Repos lists at most 5 repos touched recently, **path and branch only** — never clean, dirty,
      committed, merged or a HEAD hash (Rule 5). Per-project detail (worktrees, plan numbers, test
      counts, decisions) belongs in that project's Timeline through `save project`, not here
- [ ] **Step 3**: Update if the user's profile or the companion's preferences evolved — `main/main-memory.md` *(condition: if_profile_evolved)*
- [ ] **Step 4**: Trim: `python3 mcp-spike/ram.py trim`. It keeps the **3 most recent** session blocks
      and moves the rest unchanged to the top of `main/session-archive.md`, adding the device tag
      (`### YYYY-MM-DD · {device} — …`). Any Status key other than Focus, Repos and Open loops moves
      out the same way, verbatim, as one `### YYYY-MM-DD · {device} — status moved out of RAM` block.
      Then `python3 mcp-spike/ram.py check`: if it still reports issues (a Focus longer than one line,
      more than 5 repos or open loops), fix them by hand before uploading.
      Fallback without Python: do the same by hand
- [ ] **Step 5**: If project work happened this session, suggest — but do not run — `save project` so the project Timeline gets its own entry. If study on a learning topic happened, likewise suggest `save learning`. If job-search work happened — a search run, a tailored CV, a status change — likewise suggest `save career`
- [ ] **Sync upload**: if `device/sync.md` exists, run the **Upload** in `session-briefing` Step 0s with the label `save memory`.
      A `blocked` result naming a `main/ram/` file means another laptop's RAM was edited. Show the reason
      and stop. Its `Undo with: git restore …` command is the way out: offer it, and run it only after the
      user confirms that any text worth keeping has been copied into their own RAM first
- [ ] **Step 6**: Report: 'Memory saved.'

## Rules

1. Only update main-memory.md when genuine new knowledge about the user or the companion has emerged
2. Own RAM is always updated on save. Another laptop's RAM file is never edited. If one needs
   changing, stop and tell the user
3. RAM is RAM, not a log: at most 3 session blocks. Older blocks move to `main/session-archive.md`
   unchanged, device-tagged. Never summarise or delete them on the way out
4. Bare `"save"` belongs to this skill. It never writes project or learning files — it suggests `save project` or `save learning` and lets the user decide
5. **RAM never records git state.** "Uncommitted", "clean", "merged as abc123" are stale the moment
   work happens on another laptop or in another session. RAM names the repo and branch; the brief
   reads the state from git
6. The Status section is rewritten each save, not appended to. A paragraph labelled "superseded"
   is a sign it should have been replaced

## Level History

- **Lv.2** — Session RAM with a 3-session cap and verbatim archive; suggests `save project`
- **Lv.3** — Also suggests `save learning` after a study session
- **Lv.4** — Current behaviour: a fixed Status shape (Focus, Repos, Open loops), rewritten each
  save; `trim` moves anything else out verbatim and `check` lints the result; no git state in RAM
