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

      **Own RAM.** Session RAM is per laptop: `main/ram/{name}.md`, where `{name}` is `name:` in
      `device/id.md`, or `main/ram/unregistered.md` when there is no `device/id.md`. Run
      `python3 mcp-spike/ram.py path` to print it. Every skill uses this rule; none hard-code a RAM path.
      Each laptop writes only its own RAM file. Never edit another laptop's.

- [ ] **Step 0g**: **Gather — one call (preferred).** From the memory root run
      `python3 mcp-spike/brief.py --cwd "<the session's working directory>"`. It runs the sync
      download, creates own RAM if missing, and prints one JSON object with everything Steps 0s, 1,
      1b, 2 and 4 read: `sync` (the download result), `time`, `ram` (header, Focus, Open loops and a
      shape `check`), `repos` (live git state), `others`, `learning` and `career`.
      When it succeeds, act on `sync.status` exactly as Step 0s describes (the download has already
      run — do not run it again), then take Steps 1, 1b, 2 and the Step 4 flags from its fields
      instead of reading the files by hand. When Python is unavailable or the script fails, run
      those steps by hand: they stay the fallback (Rule 4).

- [ ] **Step 0s**: **Sync** — the one place the sync hook is written; the save skills point here.
      Skip silently when `device/sync.md` does not exist (sync not set up on this device).

      **Download** (here, before Context Load): run
      `python3 mcp-spike/sync_git.py pull` from the memory root and act on `status`:
      `up-to-date` / `merged` → continue silently (if `regenerate` is true, run
      `.venv/bin/python adapters/generate.py all`); `needs-answers` → hand over to `sync-memory`
      merge questions before the brief; `setup-incomplete` → one line suggesting `sync setup`;
      `offline` → one line, *"offline — working locally, will upload next save"*; anything else →
      one line with the reason, then continue.

      **Upload** (run by every save skill after it writes): `python3 mcp-spike/sync_git.py save
      "<what was saved>"`. `pushed` → silent. `rejected` → run the download above, then save once
      more. `needs-answers` → the open merge questions come first (`sync-memory`); nothing uploads
      until they are answered. `offline` → one line. `blocked` → stop and show the reason — never
      work around it.

      A `blocked` upload naming a `main/ram/` file means another laptop's RAM was edited here. Its
      reason ends with `Undo with: git restore …`; offer that command and run it only on the user's yes.

      A `blocked` upload naming a **binary file** means a new image, PDF, archive or other non-text
      file was about to sync outside `design/`. Memory holds text: offer to move the file into the
      project's own repo (or `outputs/`, which never syncs) and leave a link in its place, or, if the
      user wants it synced, add a glob for it to `.memory-core/binary-allow`. Never pick for them.
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
- [ ] **Step 1**: Extract last session recap (1-2 lines) from own RAM (Step 0a). If it does not
      exist yet, run `python3 mcp-spike/ram.py ensure`

      **Repo state is read live, never from RAM** (Rule 9). Do not repeat what RAM prose says about a
      repo — clean, uncommitted, merged, a HEAD hash. Report it from `repos`, or on the fallback path
      run `git -C <path> status -sb` and `git log -1 --oneline` for each repo under RAM's
      `**Repos**:` and for the working directory. A live branch that differs from the one RAM lists
      is worth one line. When `ram.check.ok` is false (fallback: `python3 mcp-spike/ram.py check`),
      add one line before the footer: `🧹 RAM needs tidying — {n} issue(s); the next save trims it`
- [ ] **Step 1b**: **Other laptops.** Run `python3 mcp-spike/ram.py others` (fallback: read the first 3
      lines of every other `main/ram/*.md`, skipping devices marked retired in `devices/`). Hold the
      lines. When a brief is delivered, add them as an "Other laptops" footer, at most 3, newest first.
      "What was I doing on {device}" loads `main/ram/{device}.md` in full
- [ ] **Step 2**: Determine time period, adjust tone
- [ ] **Step 3**: Classify first message intent — code/debug, documentation/design, memory/architecture, or general.
      Now that intent is known, resolve the deferred modules: call `context_load` again with
      `session_type` set (`design` / `code` / `general`), or read the matching bodies by hand on
      the fallback path. Report anything that newly loaded
- [ ] **Step 4**: Compose and deliver relevance-filtered brief (max 12 lines).
      **Learning flags:** for each `learning/*/General.md` with `**Status**: active` (skip folders
      starting with `_`), read the concept table in its `Progress.md`. If any concept is `shaky`
      with `Last reviewed` 7 or more days ago, add one line:
      `📚 {topic} — {n} shaky concept(s), oldest reviewed {d} days ago`.
      These share the brief's limit of 3 flags with idle-project flags, most overdue first. Skip
      silently when `learning/` does not exist

      **Career flag:** when `career/` exists, read `career/tracker.md` and the **most recent**
      `## YYYY-MM-DD` entry in `career/timeline.md`. Emit at most one line:
      `💼 Career — {n} ready · {n} awaiting reply · {company} follow-up due {date} · {n} open questions`.
      **Fire it only when something is time-sensitive or unresolved** — a `Next action` date that
      has been reached or passed, or one or more `Open:` bullets in that latest entry. A standing
      count of jobs at `ready` never fires it alone; counts are context once the line is earned.
      Omit any clause whose count is zero. `Open:` bullets in older entries are already resolved
      and are not read. This shares the brief's limit of 3 flags with idle-project and learning
      flags. Skip the whole line silently when `career/` does not exist. When `career/timeline.md`
      **is missing or has no entries**, do not read it;
      **that suppresses only the open-questions clause** — a due follow-up lives in `tracker.md`
      and must still fire the line,
      or a fresh install that never ran `save career` would go silent on the date it matters

      Then the "Other laptops" footer from Step 1b, when there is one.

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
9. **RAM names a repo and its branch; git says what state it is in.** Anything RAM says about
   commits, cleanliness or merges was true when written and goes stale the moment work happens
   elsewhere — check git before saying it

## Level History

- **Lv.3** — Context load, recap, time-of-day tone, intent-filtered brief
- **Lv.4** — Adds learning flags for active topics whose shaky concepts have gone 7+ days without review
- **Lv.5** — Adds a career flag for job-search state, fired only by a due follow-up or an
  unresolved `Open:` question, never by a standing count of ready applications
- **Lv.6** — Current behaviour: one `brief.py` call gathers the sync download, RAM, other laptops,
  learning and career flags; repo state is checked live against git instead of repeated from RAM;
  a RAM that has outgrown its shape gets a one-line tidy flag
