---
name: sync-memory
description: "Use when user says 'sync setup', 'sync', 'sync status', 'follow project [X]', 'follow ecosystem [X]', 'unfollow [X]', 'upload project [X]', 'upload ecosystem [X]', 'retire device [X]', 'install missing plugins', or 'undo sync'; and whenever session-briefing's Sync download returns needs-answers. Keeps one memory-core in step across several laptops through a private GitHub repo — core memory always, projects and ecosystems by choice — and asks, one item at a time, wherever two laptops changed the same judgement."
---

# Sync Memory — Skill Plugin
_One memory across laptops: download at session start, upload at every save, ask only where both sides changed the same thing._

## Activation

When this skill activates, output:

`"_(sync-memory activates)_"`

## Context Guard

| Context | Mode |
|---------|------|
| **"sync setup"** | setup |
| **"sync"** | sync |
| **"sync status"** | status |
| **"follow project X" / "follow ecosystem X"** | follow |
| **"unfollow X"** | unfollow |
| **"upload project X" / "upload ecosystem X"** | upload |
| **"retire device X"** | retire |
| **"install missing plugins"** | plugins |
| **"undo sync"** | undo |
| **session-briefing Sync download returned `needs-answers`** | merge questions |
| **Mid-conversation (no trigger)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Every command below is `python3 mcp-spike/sync_git.py --root <memory root> <command>`, and prints
one JSON object. Read its `status` and act on it — never guess past an error.

## Mode: setup

- [ ] If `device/sync.md` exists with `state: active` → say sync is already set up, show `sync status`,
      stop. With `state: pending`, setup was interrupted — resume it from the next step
- [ ] Ask once: *"Create a new private repo, or connect to an existing one?"*
  - **New**: ask the name and the GitHub account, then `gh repo create {account}/{name} --private`
    (with `GH_TOKEN=$(gh auth token --user {account})`). Use the returned URL
  - **Existing**: ask for its URL and account
- [ ] Run `setup {url} --account {account} --name {device name}` (ask the device name; default the hostname)
  - `refused` → show the reason verbatim and stop. Never retry with another remote on your own.
    `first-upload` / `first-merge` can also refuse: a project already in this repo's history that
    was not ticked — explain it; never untick-and-continue silently
  - `unreachable` → check the URL and the account's access, then stop
  - `empty-remote` → show **checkboxes** of `local` projects and ecosystems to upload, then
    `first-upload --projects a,b --ecosystems c`
  - `remote-has-content` → show **two checkbox lists**: local-only items to upload, and remote items
    to download. Then `first-merge --projects … --ecosystems …`, which may return `needs-answers`
    (run **merge questions**)
- [ ] Report: device name and id, what was uploaded or followed, and that the trial push succeeded
      (a `pushed` status). If the status is `blocked`, `failed` or `offline`, say so — setup is not
      done until a push succeeds

## Mode: sync

- [ ] `pull` → `up-to-date` / `merged` / `needs-answers` (merge questions) / `offline` / `not-set-up`
- [ ] If `merged` and `regenerate` is true → `.venv/bin/python adapters/generate.py all`
- [ ] `save "sync"` → `pushed`, or `rejected` → run `pull` again, then `save` again (once; if still
      rejected, report it)
- [ ] One line: what came down, what went up

## Mode: merge questions

For each unit in `units`, **one at a time**:

```
{path} — {key}   (ask 1 of N)
  this laptop:   {ours, or "deleted"}
  other laptop:  {theirs, or "deleted"}
  [keep mine / take theirs / keep both / edit]
```

- [ ] Map the answer to `ours` / `theirs` / `both` / `edit:<text>`
- [ ] For `(structure)` units, say the file's layout changed on both sides and offer a whole-file
      choice with a short diff
- [ ] For `current-session.md` `header`, show both status blocks; `both` keeps both
- [ ] After the last answer: `resolve '{"<path>": {"<key>": "<choice>"}}'` with every choice
      collected. Never resolve a unit the user did not answer
- [ ] If more than 10 units share one path, offer a default for the rest of that path (`"*"`)
- [ ] `merged` → if the notes say `recompute ranked tables`, recompute `design/palettes.md` and
      `design/type.md` ranked tables from the entries and run `design_drift`. Then run the health
      check and report anything new before continuing

## Mode: status

- [ ] `status` → show:
  - remote, last sync, ahead and behind
  - following vs available, and local-only items (suggest `upload` for those)
  - the devices table: name, last sync, status
  - every line of `differences`

## Mode: follow / unfollow / upload

- [ ] **follow** → `follow project|ecosystem {slug}`. `not-found` → show `available` and suggest `sync` first
- [ ] **unfollow** → confirm first (*"removes it from this laptop only; it stays in GitHub"*), then
      `unfollow …`. `refused` → show the reason; suggest `sync` first
- [ ] **upload** → `upload project|ecosystem {slug}`. `already-tracked` → suggest `follow`

## Mode: retire

- [ ] Confirm the device name, then `retire {name}`. Its file stays, marked retired

## Mode: plugins

- [ ] From `status` → `differences`, list what this device is missing. For each plugin, on yes:
      `claude plugin install {plugin}@{marketplace}`. For each MCP server: say which device has it
      and that its settings are not synced (they can hold secrets) — the user adds it by hand

## Mode: undo

- [ ] **Confirm first** — this resets the working tree to the restore point from before the last
      sync, discarding anything since. Then `undo` → report the restore point used

## Rules

1. **While merge questions are open, nothing else moves.** `save`, `follow`, `unfollow` and `upload`
   return `needs-answers` until every question is answered — finish them (or `undo sync`) first
2. **Never push anywhere but the configured remote, never add or change a remote outside setup,
   never force-push, never copy files into memory-core-clean.** The pre-push hook enforces the
   first; these rules cover the rest
3. **Never answer a merge question for the user.** Unanswered units stay unresolved
4. **Setup is only done when a push succeeds**
5. `undo` and `unfollow` always confirm first. `undo` refuses once the merge
   was uploaded (that needs a revert commit) or when there are unsaved edits — say so plainly
6. Paths are relative to the memory root
7. Offline never blocks a session — one line, then carry on

## Level History

- **Lv.1** — Base: setup with checkboxes, automatic download/upload via session-briefing, merge
  questions by unit, follow/unfollow/upload, device registry with plugin/MCP differences, undo,
  framework guardrail
