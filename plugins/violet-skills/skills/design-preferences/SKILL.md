---
name: design-preferences
description: "Use during any UI, mockup or visual design work, and when user says 'check design', 'seed design', 'design directions', 'rank palettes', 'rank fonts', 'rank [id]', or 'harvest design'. Also use the moment the user reacts to something visual ('too boring', 'hover is weak', 'I like this'). Loads design/ taste by layer (general → website / web-app / mobile → project Design.md), checks UI against it before showing, files new rules inline with confirmation, seeds contrasting design directions with their reasoning and a journal entry, and ranks palettes and type pairings on a 1–10 scorecard."
---

# Design Preferences — Skill Plugin
_Your design taste: applied before UI is shown, captured as you react, stretched when seeding, ranked together._

## Activation

When this skill activates, output:

`"_(design-preferences activates)_"`

Apply mode activates silently on a design session — output the activation line only for an
explicit trigger.

## Context Guard

| Context | Mode |
|---------|------|
| **Design session** (UI, mockup, screenshot, screen build) | apply — silently |
| **User says "check design"** | apply — explicitly, with a full report |
| **User reacts to something visual** — praise or complaint about colour, type, spacing, motion, layout | capture |
| **User says "seed design" / "design directions"**, or new UI work on a project whose Design.md is empty | seed |
| **User says "rank palettes" / "rank fonts" / "rank [id]"** | rank |
| **User says "harvest design"** | harvest |
| **Reaction about code, wording of a doc, or process** — not visual | DORMANT |
| **Mid-conversation (no trigger context)** | DORMANT |

## Memory Root & Context Load

**Paths in this skill are relative to the memory root, not your working directory.** Derive the
root by stripping `/plugins/violet-skills/skills/<skill-name>` from the `Base directory for this
skill` line above — see `session-briefing` Step 0a for the full rule and its fallback.

Then ensure the always-on `context/` modules are loaded this session — call the `context_load`
tool if available, otherwise use the folder-scan fallback in `session-briefing` Step 0b. Skip if
already loaded. `context/30-design.md` carries the load order this skill follows.

If any `design/` file is missing, recreate it from the shape described in `design/README.md`
before the first write — never write a rule into a file that is not there.

## Load Stack

Every mode starts here:

1. `design/general.md`
2. The layer files named in the project's `Design.md` header — `**Layers**: web-app, mobile` →
   `design/web-app.md`, `design/mobile.md`. `none` → no layer files
3. `project-management/{project}/Design.md`

Later overrides earlier. **Layers sit side by side, not on top of each other** — each applies in
its own context. On a `web-app, mobile` project, `mobile.md` governs the phone breakpoint and
`web-app.md` the desktop view; neither overrides the other. No project loaded → infer layers from the task (Flutter screen → mobile;
Blazor, admin or CMS page → web-app; portfolio or docs page → website) and say so. A project whose
header has no `**Layers**` line → infer, say so, and offer to add the line (on yes only).

`palettes.md`, `type.md` and `journal.md` load only in seed and rank.

---

## Mode: apply (guardrail)

- [ ] Load the stack
- [ ] Before showing any UI — mockup, screenshot, built screen — check it against every loaded
      rule. Fix violations first; do not show and then apologise
- [ ] Hand over with one line:
      `Checked against: general · web-app · mobile · acme-cms`
      plus `Bent: {rule} — {why}` for any rule deliberately not followed
- [ ] A project rule that contradicts a general or layer rule wins — but flag it once per session:
      *"acme-cms uses {x}, which goes against your general rule '{rule}'. Intended?"*
- [ ] On **"check design"**: list every loaded rule that applies to the current UI with ✓ / ✗ and
      the fix for each ✗

## Mode: capture (inline)

- [ ] When the user reacts to something visual, stop and ask immediately — one line:

  ```
  File as **{layer}** rule: '{Rule} — {detail}' ("{their words}")?
  [yes / edit / other layer / project-only / no]
  ```

  Pick the layer by scope: holds on any platform → general; only on a phone or a narrow
  breakpoint → mobile; only in dense tools → web-app; only on expressive sites → website; only
  because of this one product → project-only.
- [ ] **yes** → append under the right section of the layer file, in the rule format:
      `- **{Rule}**: {detail}. "{their words}" ({YYYY-MM-DD})`
- [ ] **edit** → take their wording, show the final line, write on yes
- [ ] **other layer** → ask which, write there
- [ ] **project-only** → append to the active project's `Design.md` under the matching section
- [ ] **no** → drop it; do not ask about the same reaction again this session
- [ ] **Conflict** with an existing rule → show both and offer: *replace / keep both, scoped
      ({how}) / skip*

## Mode: seed (creative directions)

- [ ] Load the stack, plus `palettes.md`, `type.md` and the last five `journal.md` entries
- [ ] Prepare **2–3 deliberately contrasting directions**. Each has a name, a palette (existing
      id or new), a type pairing (existing id or new), one sample screen of the real task, and
      **Why it works** — two or three principles named plainly (e.g. *"60-30-10 split; serif
      headings add an editorial voice; generous leading slows the reader"*)
- [ ] **At least one direction must go beyond the current rules** — label it
      `Stretch: breaks '{rule}' because {reason}`. Seeding exists to widen taste, not mirror it
- [ ] Show them in the brainstorming visual companion. If it is unavailable (Codex, plain CLI),
      write one HTML file per direction to `outputs/design/{project}/` and give a text table
- [ ] Ask the user to pick, mix or reject. Ask *why* for each rejection if they have not said
- [ ] Draft the journal entry and show it; append to `journal.md` on yes:

  ```
  ## YYYY-MM-DD — {project} / {screen or scope}
  **Shown**: A {name} · B {name} · C {name}
  **Picked**: {letter}. "{their words}"
  **Rejected**: {letter}, {reason} · {letter}, {reason}
  **Learned**: {principle, or —}
  ```

- [ ] A new palette or pairing in the pick → offer to add it to its library, unranked, with the
      AI criteria scored. On yes, also offer to set the project header's `**Palette**` /
      `**Type**`
- [ ] Any rule their choice implies → run capture for it

## Mode: rank

- [ ] Load `palettes.md` or `type.md` (both for "rank [id]" when the library is unclear)
- [ ] Choose the entries: the named id; else every unranked entry; else, if they ask for a
      re-rank, all of them
- [ ] Render them — swatches on their own surfaces, light and dark, or type samples at body,
      heading and small-data sizes — in the visual companion (fallback: HTML to
      `outputs/design/rank/`)
- [ ] Score the AI criteria first and show the working:
  - **Contrast & accessibility** — compute the WCAG ratio of every text role on bg and surface,
    both modes. 10 = all ≥ 7:1 (AAA), 7 = all ≥ 4.5:1 (AA), any pair < 4.5:1 caps at 4. List the
    ratios in Notes
  - **Completeness** — count defined roles, semantic colours and states; say what is missing
  - **Dark-mode readiness** — real dark variant that holds contrast = high; inverted or absent = low
  - **Legibility / Coverage / Availability** (type) — name the evidence: x-height, tabular
    figures, I/l/1 and 0/O, weights and italics, the glyphs your languages need, licence, web and Flutter packages
- [ ] Ask the user for their three scores, one entry at a time. **Never infer their scores**
- [ ] Show the updated entry and ranked table; write on yes:
  - Scores into the entry's criterion table
  - Rescore → previous scores kept in **Notes**: `YYYY-MM-DD: 7/8/6 · 8/9/7 → avg 7.5`
  - All six scored → move it from Unranked to Ranked. Avg = mean of six, one decimal.
    Objective and Subjective = mean of their three. Order by Avg; ties by Subjective.
    Renumber ranks
- [ ] Report the new table's top three and where the scored entries landed

## Mode: harvest (one-time migration)

- [ ] Ask which projects to harvest — only projects whose design the user actually shaped; the
      rules in other projects' Design.md are not their taste. Projects outside the list are not
      read, not given headers, and not mentioned again
- [ ] Read every source:
  - `main/preferences.md` — **Visual Design Language** section
  - the chosen projects' `Design.md`
  - for a chosen project whose `Design.md` is still the empty template, its `General.md`,
    `Features/*/Overview.md` and any `notes/*.md` naming it — and, read-only, the theme or colour
    file in its repo (path from `General.md` Repositories), so its palette can be registered
  - Claude auto-memory feedback files, if present (`~/.claude/projects/*memory-core*/memory/feedback_*.md`)
- [ ] Sort each candidate into **general / website / web-app / mobile / project-only**, with its
      source and date. Project-only candidates stay where they are — list them, do not move them
- [ ] Collect every palette and type pairing in the project Design.md files as library entries
      (ids proposed in kebab-case, e.g. `acme-navy`), with the AI criteria pre-scored
- [ ] Propose a header for each chosen project: `**Layers**`, `**Palette**`, `**Type**`
- [ ] Flag every conflict with both sides and their dates
- [ ] Present the whole list grouped by destination. The user approves, edits or drops items —
      one review, then write only what was approved
- [ ] After writing:
  - Replace `main/preferences.md`'s Visual Design Language section with one line:
    `Moved to design/ ({date}) — see design/README.md.`
  - Add `**Layers**` / `**Palette**` / `**Type**` to each approved project header, directly under
    the `# Design — {name}` title
  - Report counts per destination and any conflict left open

## Rules

1. **Nothing is written without the user's yes** — no rule, score, journal entry or header line
2. **Their scores are theirs** — the subjective criteria are asked, never inferred
3. **Layer files hold taste; project files hold the project.** A rule true only because of one
   product goes in that project's `Design.md`
4. **Never write to `context/`**
5. **Seeding must stretch** — at least one direction beyond the current rules, labelled as such
6. **Show, do not describe** — seed and rank are rendered, never hex codes in prose alone
7. Append, do not rewrite — journal entries and rescore history are never edited after the fact
8. Paths are relative to the memory root, never the working repo
9. After any write to `design/` or a project header, run the `health_check` tool if available and
   report only `design_*` findings on the files just written — projects outside the harvest keep a
   standing `design_layers_missing` that is never repeated

## Level History

- **Lv.1** — Base: layered load stack, apply guardrail, inline capture, seed with contrasting
  directions and journal, 1–10 rank scorecard, one-time harvest
