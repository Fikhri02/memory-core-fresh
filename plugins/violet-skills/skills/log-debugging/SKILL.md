---
name: log-debugging
description: "Use when user says 'log debugging', 'log this debug', 'debug log', 'save debug log', or 'continue debug log [slug]'. Records a debugging session — symptom, root cause, solution, dead ends, and the step-by-step hunt — as a searchable file under debugging/ for future reference. Also suggested, never applied, after a session that took several diagnostic steps to reach a root cause."
---

# Log Debugging — Skill Plugin
*Turns a debugging session into a searchable record: what broke, what it turned out to be, and every path walked on the way.*

## Activation

When this skill activates, output:

`"Logging the debug session..."`

## Context Guard

| Context | Status |
|---------|--------|
| **User says "log debugging"** | ACTIVE → log-write |
| **User says "log this debug"** | ACTIVE → log-write |
| **User says "debug log"** | ACTIVE → log-write |
| **User says "save debug log"** | ACTIVE → log-write |
| **User says "continue debug log {slug}"** | ACTIVE → log-resume |
| **User says "resolve debug log {slug}"** | ACTIVE → status-transition |
| **User says "list debug logs"** | ACTIVE → log-list |
| **Debugging reached a root cause after 3+ diagnostic steps** | SUGGEST — offer once, never write |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

This skill is like `sync-git`: it reads a **code repository** (your working directory) and writes
to the **memory root**. Keep the two straight.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded.

## Protocol

### log-write

- [ ] **Step 1**: Derive the slug — `{project}-{symptom-in-3-or-4-words}`, lowercase, hyphenated.
      Prefer the symptom over the cause: the cause is often unknown when the log is opened, and a
      reader searches by what they saw. `staylokal-emulator-killed-exit-137`, not
      `staylokal-duplicate-cli`
- [ ] **Step 2**: Check `debugging/open/` and `debugging/resolved/` for `{slug}.md`. If it exists,
      switch to **log-resume** rather than creating a second file
- [ ] **Step 3**: Resolve the project. Match the working directory or its `git remote get-url origin`
      against the **Repositories** table in each `project-management/*/General.md`. On a match, use
      that project name and origin. On no match, record the raw path and origin and leave
      `Project:` as `_(not tracked)_` — **never scaffold a project entry from here**
- [ ] **Step 4**: Write `debugging/open/{slug}.md` in the file format below. Fill only what is
      actually known — an unresolved hunt legitimately has an empty `Root cause` and `Solutions`
- [ ] **Step 5**: If the project matched, symlink the log into it:
      `ln -s "{absolute-source}" "project-management/{project}/Debugging/{slug}.md"`.
      Create `Debugging/` if absent. **Only symlink when the source file exists**
- [ ] **Step 6**: If the root cause is known and a fix is in place, offer to move it to
      `debugging/resolved/` — ask, do not move on your own
- [ ] **Step 7**: Report the path written and whether it landed open or resolved

### log-resume

- [ ] **Step 1**: Locate `{slug}.md` — search `debugging/open/` first, then `debugging/resolved/`.
      Warn if it is already resolved before appending
- [ ] **Step 2**: Append to **Step by step log** under a new dated heading — never rewrite earlier
      steps, even ones that turned out to be wrong. A path that led nowhere is the record's value
- [ ] **Step 3**: Update `Root cause`, `Solutions`, and `Dead ends` if the session changed them
- [ ] **Step 4**: Offer the move to `resolved/` if the cause is now known

### status-transition

- [ ] **"resolve debug log {slug}"**: require a non-empty `Root cause`; refuse and say so if it is
      blank. Set `Status: resolved`, stamp `Resolved:` with today's date, move the file to
      `debugging/resolved/{slug}.md`, and repoint the project symlink
- [ ] **"list debug logs"**: list `open/` then `resolved/`, one line each — slug, project, symptom,
      date

## File Format

```markdown
# {Title — the symptom, in plain words}

**Project**: {project name, or _(not tracked)_}
**Git repo link**: {origin URL, or local path when there is no remote}
**Status**: open | resolved
**Opened**: YYYY-MM-DD
**Resolved**: YYYY-MM-DD

---

## Symptom

{What was actually observed. Include the literal error text, exit codes, and log lines —
this is the field future-you greps. Verbatim, not paraphrased.}

## Root cause

{The actual cause, once known. Blank while the hunt is open.}

## Solutions

{What fixed it. Commands, diffs, config. Enough to apply again without re-deriving.}

## Dead ends

{Theories pursued that turned out wrong, each with how it was ruled out. This is what stops
the next person — usually you — walking the same paths.}

## Step by step log

### YYYY-MM-DD

1. **Did**: {action} → **Found**: {result}
2. **Did**: {action} → **Found**: {result}

## Related

- [[other-debug-log]]
- [[brainstorm-or-plan]]
```

## Rules

1. **Never fabricate a step.** The log records what was actually run and actually observed. If a
   detail was not captured, write `not recorded` rather than a plausible reconstruction
2. **Symptom is verbatim.** Copy the real error text, exit code, and command. A paraphrase is not
   greppable, and grep is how this file gets found
3. **Dead ends are never pruned.** They are not clutter; they are the reason the log beats memory
4. **Append, never rewrite.** `log-resume` adds a dated section. Earlier steps stand as written,
   including the wrong ones
5. **A log is never auto-resolved.** Moving to `resolved/` needs the user's word, and a root cause
   that is actually filled in
6. **Never create project entries.** Match against existing ones or record the raw path — that is
   `document-project`'s job, as in `sync-git`
7. **The passive trigger only suggests.** After a multi-step hunt, offer once: "Worth logging this?"
   Do not write, and do not ask twice in a session
8. Read-only on the code repo — this skill inspects and writes memory files, nothing else

## Edge Cases

| Situation | Behavior |
|-----------|----------|
| Log for this slug already exists | Switch to log-resume; never create a second file |
| Working directory is not a git repository | Record the absolute path; leave the repo link blank |
| Repo matches no tracked project | `Project: _(not tracked)_`, no symlink, still write the log |
| Root cause never found | Keep it in `open/` with the cause blank — an unresolved log is still worth having |
| `resolve` requested with an empty root cause | Refuse, say why, leave the file in `open/` |
| Several projects share the repo | List them, ask which; never guess |
| Bug turns out to be in a dependency, not the project | Log it anyway; put the upstream issue link under **Related** |

## Level History

- **Lv.1** — Base: write, resume, and resolve a debug log; project matching by git origin; symptom-first slugs; append-only step log with preserved dead ends
