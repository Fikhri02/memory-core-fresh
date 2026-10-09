# debugging/

Searchable records of debugging sessions, written by the `log-debugging` skill.

- `open/` — the cause is not yet known, or no fix is in place
- `resolved/` — cause found and fixed; `Root cause` is filled in

Logs are named for the **symptom**, not the cause: you come back to these having seen an error,
not having understood it. Grep the `Symptom` sections first — they hold verbatim error text.

A log whose project is tracked under `project-management/` is also symlinked into that project's
`Debugging/` folder.
