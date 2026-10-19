# Session RAM — Format

Each laptop keeps its working memory in `main/ram/{device}.md` (see `main/ram/README.md`).
`save-memory` writes it; `session-briefing` reads it through `python3 mcp-spike/brief.py`.

```markdown
# Session RAM — {device}
**Device**: {device} · `{device-id}` · **Last activity**: YYYY-MM-DD HH:MM
**Last session**: <one line — `ram.py stamp` writes these three lines>

## Session RAM Status
**Focus**: <one line: what the next session most likely picks up>
**Repos**:
- `~/path/to/repo` · branch-name
**Open loops**:
- <something waiting on the user or on a date>

## Session Recap (For AI Restart)
*Quick summary when the AI loads after a close/reopen*

### YYYY-MM-DD — <session title>
- <what was done, decided, left open>

### YYYY-MM-DD — <older session>
- …
```

## Limits

| Part | Limit | Enforced by |
|------|-------|-------------|
| Header | 3 lines | `ram.py stamp` rewrites it |
| Status | Focus, Repos, Open loops only; Focus one line; at most 5 repos and 5 loops | `ram.py trim` moves other keys out; `ram.py check` reports the rest |
| Session blocks | 3 newest | `ram.py trim` moves older ones out |

Nothing is summarised or deleted on the way out: `trim` moves it verbatim, device-tagged, to the top
of `main/session-archive.md`.

## What does not belong in RAM

- **Git state.** RAM names a repo and its branch. Whether it is clean, committed or merged is read
  live from git by the brief — prose about it goes stale as soon as work happens elsewhere.
- **Per-project detail.** Worktrees, plan numbers, test counts and decisions go in the project's
  `Timeline.md` through `save project`.
- **Binary files.** Memory holds text; see `.memory-core/binary-allow`.
