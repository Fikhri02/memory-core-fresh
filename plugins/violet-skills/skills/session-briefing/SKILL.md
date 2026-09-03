---
name: session-briefing
description: "MUST use automatically at the start of every new conversation session, before processing the user's first message. Also triggers when user says 'brief', 'session brief', 'what did we do last time', 'where did we left off', or 'reload context'. Suppressed when user says 'skip brief'."
---

# Session Briefing — Skill Plugin
*MUST use automatically at the start of every new conversation session, before pr...*

## Activation

When this skill activates, output:

`"_(activates silently)_"`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "brief"** | ACTIVE |
| **User says "session brief"** | ACTIVE |
| **User says "what did we do last time"** | ACTIVE |
| **User says "where did we leave off"** | ACTIVE |
| **User says "reload context"** | ACTIVE — run Step 0 only, then stop |
| **User says "skip brief"** | Step 0 STILL RUNS — only Steps 1-4 are suppressed |
| **Session Start** | ACTIVE |
| **Mid-conversation (no trigger context)** | DORMANT |

## Protocol

- [ ] **Step 0a**: **Resolve the memory root.** Every skill invocation is prefixed with
      `Base directory for this skill: <path>`. Strip the trailing
      `/plugins/violet-skills/skills/<skill-name>` from it — what remains is the **memory root**.

      **Every path in every skill is relative to that root, never to the current working
      directory.** You will usually be working in a different repo; that is the normal case, not
      an error. `context/`, `main/`, `project-management/`, `notes/`, `brainstorming/`,
      `project-plans/`, and `delegate-task/` all live under the memory root.

      *Fallback:* if no base directory was provided, use the working directory **only if** it
      contains `project-management/`. Otherwise say the memory root cannot be determined and stop
      — never create memory files in whatever repo happens to be open.

- [ ] **Step 0b**: **Context Load** — this is the one place the full rule is written; the other
      skills point here rather than repeating it.

      **Preferred — the `context_load` tool.** If the `memory-core-context` MCP server is
      connected, call `context_load`. It parses the frontmatter, applies prefix order, resolves
      `load:` rules, and returns `loaded`, `deferred`, and `warnings` already sorted out. Use what
      it returns and move on.

      **Fallback — folder scan.** If the tool is not available (Codex, a fresh clone with no
      server registered, ChatGPT), do it by hand: list `context/*.md`; read every module with
      `load: always` (the default) in prefix order; skip `README.md`; note which modules declare a
      condition but do not read their bodies yet; treat missing frontmatter or an unrecognised
      `load:` value as `always` and warn.

      Either way, report the loaded set in one line, resolved against the memory root:
      `Context: git-rules · working-preferences (2 modules)`
- [ ] **Step 1**: Extract last session recap (1-2 lines) — `main/current-session.md`
- [ ] **Step 2**: Determine time period, adjust tone
- [ ] **Step 3**: Classify first message intent — code/debug, documentation/design, memory/architecture, or general.
      Now that intent is known, resolve the deferred modules: call `context_load` again with
      `session_type` set (`design` / `code` / `general`), or read the matching bodies by hand on
      the fallback path. Report anything that newly loaded
- [ ] **Step 4**: Compose and deliver relevance-filtered brief (max 12 lines)

## Rules

1. **Paths are relative to the memory root, not the working directory.** This is the single most
   common way to corrupt a memory-core install: scaffolding `project-management/` or writing
   `notes/` into whatever repo is open. When in doubt, stop and ask
2. **Step 0 is not part of the brief.** Context modules load even when the brief is suppressed
   (`"skip brief"`) or turned off entirely — suppressing a recap must never silently disable
   always-on memory. Only Steps 1-4 are suppressible
3. Context modules load once per session — a skill invoked later re-checks and skips
4. **The tool is an optimisation, not a dependency.** The folder-scan fallback must keep working:
   Codex, ChatGPT, and any clone without the MCP server registered rely on it. Never write a skill
   step that only functions when the tool is present
5. A module with no frontmatter, or an unrecognised `load:` value, is treated as `always` and reported as a warning — never silently dropped
6. `context/README.md` is documentation, not a module — skip it
7. Never write to `context/` — modules are added and edited deliberately, not generated
8. `"reload context"` re-runs Step 0b alone — use it after editing a module mid-session; it does not re-deliver the brief

## Level History

- **Lv.3** — Current behaviour, as described in the Protocol and Rules above
