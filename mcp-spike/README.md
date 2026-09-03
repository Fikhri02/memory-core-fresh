# MCP Spike — throwaway

**This is a probe, not a feature.** It exists to answer one question and can be deleted without
consequence. Nothing in the framework depends on it.

## The question

Does moving context-module loading out of 12 markdown guards and into a typed MCP tool make the
skills simpler — and can it run with no dependency beyond the stdlib?

## What it is

`server.py` — a dependency-free MCP server over stdio exposing two tools. `context_load` reuses
`adapters/context_modules.py`, so there is no second implementation of the parsing rules.
`health.py` holds the drift checks.

```
context_load(session_type?, project_loaded?)
  -> { report, loaded[], deferred[], warnings[] }

health_check()                       # no arguments — read-only
  -> { summary, root, findings[{check, severity, path, detail}] }
```

### The permission boundary

`health_check` takes **no path**. The repo it scans is fixed when the *operator* launches the
server (`--root=` or `MEMORY_CORE_ROOT`), never by a tool argument — a model talking to this
server cannot redirect it at another folder. The tools decide what CAN be done; the launch decides
WHERE. Both tools are read-only; nothing here writes.

## Try it

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"x","version":"0"}}}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"context_load","arguments":{}}}' \
  | python3 mcp-spike/server.py
```

To register it in Claude Code (then restart the session):

```bash
claude mcp add memory-core-context -- python3 /absolute/path/to/memory-core-fresh/mcp-spike/server.py
```

## What health_check found

Pointed read-only at the working `memory-core` repo, it reported **28 findings — 5 high, 12
medium, 11 low**, every one a real issue found by hand earlier:

- **5 high** — `analyze-component`, `delegate-task`, `document-project`, `pick-up-task`,
  `save-project-management` exist as SKILL.md but not in the spec. This is the footgun: running
  `generate.py codex` would silently delete all five from AGENTS.md.
- **12 medium** — features 100% task-complete but never moved out of `Development/`.
- **11 low** — project timelines 95–148 days stale.

Scanning the fresh repo itself: **No drift detected.** Injecting an unindexed memory file was
detected immediately as `memory_not_indexed` — the check that would have caught
`feedback_session_briefing.md` sitting inert.

## What the probe showed

- The protocol handshake works with no framework and no dependencies — ~150 lines of stdlib.
- Conditional modules resolve correctly: `on_design_session` sits in `deferred` for a general
  session and moves to `loaded` when `session_type: design` is passed.
- Malformed modules degrade the same way as the markdown path — a bad `load:` value is loaded as
  `always` and reported, never silently dropped.
- The two-phase design survives: phase 1 is `context_load()`, phase 2 is
  `context_load(session_type=...)` once intent is known.

## What it does NOT settle

- Whether the skills actually get simpler in practice — that needs a week of real use.
- The ChatGPT/Gemini problem. They cannot run this, so the markdown and inlining paths must stay.
  Two implementations is the risk that would sink an MCP layer if it grew unchecked.
- Whether one tool call is cheaper than the markdown guard once tool-list tokens are counted.

## A bug the probe found in itself

The first cross-repo run crashed: the server put the *target* repo's `adapters/` on `sys.path` and
tried to import its own code from there. Pointing it at an older checkout broke it instantly. Code
root and data root are now separate — server modules always load from beside `server.py`, only the
data root varies. Worth remembering for any real version.

## Backlog

### B — tools that own the paths *(deferred, 2026-08-29)*

**Pending.** Not started; recorded so the reasoning is not lost.

`context_load` already proves the shape: the skill calls a tool and gets content, so the model
never builds a path and the working directory is irrelevant. The rest of the framework still hands
the model paths to construct — `project-management/{name}/General.md`,
`Features/{component}/Development/`, `Timeline.md`. Option A (memory-root resolution from the
injected base directory, shipped 2026-08-29) makes that inference reliable. B removes the
inference entirely.

Candidate surface, in priority order — **the write operations are the ones worth doing**:

```
append_timeline(project, bullets[])           # wrong path here silently loses the session record
complete_feature(project, path, confirmed)    # refuses without confirmed=true
```

Read-side tools (`list_projects`, `read_project`, `list_features`, `read_feature`) are mostly
convenience now that the root resolves correctly. Add them only if the markdown path proves
unreliable in practice.

**Why the write ops first:** this is where the permission model earns its keep. "Never mark a
feature Completed unless the user says so" is currently Rule 2 in a markdown file — a request a
model can skip. As a tool signature requiring `confirmed=true`, it is a constraint. Likewise,
`context/` has no write tool, so nothing can write to it.

**Costs, unchanged from the original assessment:**

- Tool definitions consume context in *every* session, including ones that never touch
  memory-core. Six tools is a real budget; two is not. Add one at a time.
- ChatGPT and Gemini are permanently excluded — no filesystem, no MCP. They keep the inlined
  prompt path regardless.
- Any new tool must share its implementation with the markdown fallback, the way `context_load`
  imports `adapters/context_modules.py`. Two implementations of the same rule is the disease this
  layer is supposed to cure.

**Unverified assumption:** whether Codex speaks MCP. If it does, B gives Codex the same
absolute-root guarantee as Claude Code. If it does not, B does nothing for Codex and A's "open the
memory repo" limit stands. Check before relying on it.

---

## If it graduates

Move to `mcp/`, replace the `## Context Load` block in the 12 SKILL.md files with a single "call
`context_load`" line, and consider a `--fix` counterpart for the mechanical findings — though
note that moving a feature to `Completed/` must stay a human decision, so that one stays
report-only.
