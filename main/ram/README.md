# Session RAM — one file per laptop

Each laptop keeps its working memory in `main/ram/{device-name}.md`, where the name comes from
`device/id.md`. A clone without a device identity uses `unregistered.md`.

- **Written only by its own laptop.** Sync blocks an upload that edits another laptop's file, and a
  conflict on a RAM file always keeps its owner's version.
- **Header.** The first three lines name the device, its last activity and a one-line last session.
  `session-briefing` shows other laptops' headers as an "Other laptops" footer.
- **Bounded.** At most 3 session blocks, and a Status section with only **Focus**, **Repos** and
  **Open loops**. `save-memory` runs `python3 mcp-spike/ram.py trim` to move older blocks and any
  other Status keys, verbatim and device-tagged, into `main/session-archive.md`;
  `python3 mcp-spike/ram.py check` lints what is left. Format: `main/session-format.md`.
- **No git state.** Repos lists path and branch only; the brief reads the rest live from git.
- `main/current-session.md` is a pointer kept for old copies of the skills; never write to it.
