# Plugins

A Claude Code **plugin marketplace** — the delivery mechanism that gets the skills into Claude
Code. The skills themselves live in [`violet-skills/`](violet-skills/README.md).

---

## Layout

```
.claude-plugin/marketplace.json    declares this folder as a local marketplace
violet-skills/
  .claude-plugin/plugin.json       the plugin manifest
  skills/{name}/SKILL.md           13 skills
  skill-format.md                  the structure every SKILL.md follows
  README.md                        the skill table
```

Two manifests, two jobs: the **marketplace** says "plugins live here"; the **plugin** says "this
one is called violet-skills, here is its version".

## Installation

`setup.py` does both of these for you:

```bash
# register this folder as a marketplace, at this machine's absolute path
#   -> written into .claude/settings.json as extraKnownMarketplaces
claude plugin add --local plugins/violet-skills
```

The marketplace path **cannot be committed**. It is absolute and differs on every machine, and a
stale path points Claude Code at a folder that does not exist — silently, with no skills loaded.
That is why `step_write_claude_settings` writes it at setup time rather than shipping it.

## Only Claude Code reads this

| Platform | Entry point |
|----------|-------------|
| **Claude Code** | this folder |
| Codex | `AGENTS.md` |
| ChatGPT / Gemini / other | `outputs/*.md` |

The other four are generated from `memory-core.yaml` by `adapters/`. This folder is
**hand-written and canonical** — see the two-sources-of-truth rule in
[`../adapters/README.md`](../adapters/README.md).

## Adding a skill

1. `mkdir violet-skills/skills/{name}/` and write `SKILL.md` — see `skill-format.md`.
2. **Add the skill to `memory-core.yaml` too.** A skill present here but absent from the spec is
   silently deleted from `AGENTS.md` on the next `generate.py codex`.
3. Add it to `violet-skills/README.md`.
4. `python adapters/generate.py all`

Steps 2 and 3 are the ones that get skipped. `health_check` catches step 2
(`skill_missing_from_spec`, high). Nothing catches step 3 — the skill table in
`violet-skills/README.md` currently lists 13 skills and must be updated by hand.
