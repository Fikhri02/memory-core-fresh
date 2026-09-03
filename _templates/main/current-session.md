# {{COMPANION_NAME}} Current Session Memory - RAM
*Temporary working memory — holds the 3 most recent sessions. Older recaps move to `main/session-archive.md`.*

## Session RAM Status
**Current Session**: New — no previous session
**Last Activity**: Never
**Session Focus**: —
**Context State**: Fresh start

## Session Recap (For AI Restart)
*Quick summary when the AI loads after a close/reopen*

- **Last Session**: None — this is your first session with {{COMPANION_NAME}}
- **Next Logical Step**: Say "{{COMPANION_NAME}}" to begin

## Active Project
- None

## Session Memory Limit

- **Prior sessions kept here**: 3 (older ones move verbatim to `main/session-archive.md`)
- **Maximum**: 500 lines
- **Format Reference**: See `main/session-format.md` for rebuild structure

### Auto-Reset Behaviour
```
IF current-session.md line count > 500:
    1. Read the current Session Recap section
    2. Move all but the 3 most recent session blocks to main/session-archive.md
    3. If still over the limit, rebuild from main/session-format.md
    4. Continue the session with clean working memory
```

---

**Memory Type**: RAM — temporary working memory
**Persistence**: Recent recaps only; detail moves to the archive
**Line Limit**: 500 lines
