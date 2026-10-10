# Design Preferences

Your design taste, in one place every platform can read. Written by the `design-preferences`
skill — every rule, score and journal entry is confirmed by you before it lands here.

## Files

| File | Holds | Loaded |
|------|-------|--------|
| `general.md` | Taste that holds everywhere | Every design session |
| `website.md` | Expressive sites — portfolio, docs site | When the project declares `website` |
| `web-app.md` | Dense tools — CMS, admin, tables, filters, forms | When the project declares `web-app` |
| `mobile.md` | Native apps and the mobile breakpoints of web projects | When the project declares `mobile` |
| `palettes.md` | Ranked palette library | Seed and rank only |
| `type.md` | Ranked type-pairing library | Seed and rank only |
| `journal.md` | Seed sessions — shown, picked, rejected, why | Seed only |

## Layers are contexts, not project types

A project declares every layer it uses, in the header of its `Design.md` (before the first `##`):

```
**Layers**: web-app, mobile
**Palette**: {palette-id} · **Type**: {type-id}
```

Valid layers: `website`, `web-app`, `mobile`, `none`. A project with no UI declares `none`.

## Precedence

Later overrides earlier:

1. `general.md`
2. the declared layer files — only those
3. the project's own `Design.md`

Layers sit side by side, not on top of each other: each applies in its own context. On a
`web-app, mobile` project, `mobile.md` governs the phone breakpoint and `web-app.md` the desktop
view. With no project loaded, layers are inferred from the task and the loaded set is reported.

## Rule format

One bullet per rule, under the section it belongs to, dated, with your own words when they exist:

```
- **Hover must be unmistakable**: lift, shadow and colour together. "a more apparent effect when hovering over a clickable button" (2026-09-06)
```

A rule about one project goes in that project's `Design.md`, not here.

## Scoring rubric (1–10)

**Palettes**

| Criterion | By | Meaning |
|-----------|----|---------|
| Contrast & accessibility | AI | WCAG ratio of every text-on-surface pair. 10 = all AAA, 7 = all AA, any AA failure caps at 4 |
| Completeness | AI | All roles, semantic colours and interaction states defined |
| Dark-mode readiness | AI | A real dark variant that holds contrast, not a straight inversion |
| Mood fit | You | Feels like what the product is |
| Distinctiveness | You | Memorable, not something any product could use |
| Held up in use | You | After living with it, still liked |

**Type pairings**

| Criterion | By | Meaning |
|-----------|----|---------|
| Legibility | AI | Small UI sizes and data: x-height, tabular numerals, I/l/1 and 0/O distinct |
| Coverage | AI | Weights, italics, and the characters your languages need |
| Availability | AI | Licence, web and Flutter support, load weight |
| Personality fit | You | The voice the product needs |
| Pairing harmony | You | Heading and body work together |
| Held up in use | You | After living with it, still liked |

Rank = average of all six; ties go to the higher subjective average. Unranked until all six are
scored. Scores are whole numbers.

## Health checks

`health_check` reports: a project with no `Layers` (`design_layers_missing`), an unknown layer
name (`design_layer_unknown`), a `Palette`/`Type` id with no library entry (`design_ref_unknown`),
a ranked table out of step with its scores (`design_rank_stale`), a score that is not a whole
number 1–10 (`design_score_invalid`), and a library `## ` heading that is not a kebab-case id
(`design_entry_invalid`).
