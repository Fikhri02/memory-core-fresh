---
module: design
load: on_design_session
summary: Where your design taste lives and how to load it.
---

# Design Taste

Your design preferences live in `design/` under the memory root. Load them before producing
any UI — mockup, screenshot, built screen.

- **Load, in this order** (later overrides earlier): `design/general.md` → the layer files the
  project's `Design.md` header declares under `**Layers**` (`website`, `web-app`, `mobile`) →
  the project's own `Design.md`. `none` means no layer files. Layers sit side by side: on a
  `web-app, mobile` project, mobile rules govern the phone breakpoint and web-app rules the desktop view.
- **No project loaded** → infer layers from the task (Flutter screen → mobile, Blazor or admin
  page → web-app, portfolio or docs page → website) and say which you loaded.
- **Before showing UI**, check it against the loaded rules and fix violations first. Hand over with
  one line: `Checked against: general · web-app · mobile · {project}`, plus any rule bent and why.
- **When the user reacts to something visual**, offer to file it as a rule immediately — see the
  `design-preferences` skill. Never write a rule without their yes.
- `design/palettes.md`, `type.md` and `journal.md` are for seeding and ranking only — do not load
  them for everyday UI work.
