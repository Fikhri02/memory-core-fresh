# Learning

One folder per topic you're learning. Started by `start-learning` (**"start learning [topic]"**),
resumed by `continue-learning` (**"continue learning [topic]"**), recorded by `save-learning`
(**"save learning"**).

```
learning/
  _template/           scaffold every topic is built from (structure.yaml + file templates)
  {topic}/
    General.md         goal, why, level, source, resources — and the topic's Status
    Study-Plan.md      modules in order, objectives as checkboxes, concepts per module
    Progress.md        one row per concept (confidence + last reviewed), then a dated log
    Projects.md        projects that exercise the topic, by project-management/ name
    Notes/             one file per concept — what the quizzes draw from
    Exercises/Active/  drills in progress, each with a self-check
    Exercises/Done/    moved here when the self-check passes and you say so
```

## Confidence

`—` not yet studied · `shaky` · `okay` · `solid`. A concept enters at `shaky` when first learned.
After that it changes only when you confirm the result of a quiz, which is 2–3 questions drawn
from its note. `continue learning` quizzes shaky concepts first. The session brief flags an
active topic once a shaky concept goes 7 days without review.

## Status

`General.md` carries `**Status**: active | paused | done`. This is the one place memory-core uses
a field instead of a folder for status, because projects and the brief link to topic paths, so
topic folders never move. Exercises still use folders: `Active/` → `Done/`.

## Projects

`Projects.md` links projects by name: ``- `acme-auth` — realms, SPIs, brute-force``. Their
content stays in `project-management/`. When you `save project` on a linked project,
save-project-management offers to turn durable findings into notes here. It never copies
them on its own.

## Health

`health_check` reports `learning_note_missing` (a rated concept whose note doesn't exist,
so it can't be quizzed) and `learning_project_missing` (a link to a project that isn't
under `project-management/`).
