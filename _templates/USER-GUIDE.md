# memory-core — User Guide
*How to set up and use {{COMPANION_NAME}} on any AI platform*

---

## What is {{COMPANION_NAME}}?

{{COMPANION_NAME}} is a persistent AI companion system built on top of any LLM. It gives the AI:
- **Memory** — persistent context across sessions via markdown files
- **Skills** — structured behaviors that trigger on specific commands
- **Identity** — a consistent personality that loads from a single wake word

The system is platform-agnostic. The same memory files work on Claude, Codex, ChatGPT, Gemini, or any LLM. Only the behavior layer (how skills are loaded) differs per platform.

---

## Setup: Claude Code

### Step 1 — Clone or locate memory-core
```
memory-core/          ← this repo
  memory-core.yaml    ← source of truth
  plugins/violet-skills/  ← Claude Code plugin
  main/               ← memory files
  AGENTS.md           ← Codex entry point
  outputs/            ← ChatGPT, Gemini, Generic prompts
```

### Step 2 — Install the plugin
```bash
cd memory-core
claude plugin add --local plugins/violet-skills
```

### Step 3 — Verify installation
```bash
claude plugin list
# Should show: violet-skills@violet-local (enabled)
```

### Step 4 — Open any project in Claude Code

Start a new conversation and type:
```
{{COMPANION_NAME}}
```

Claude will load the memory files and deliver a session brief.

### How skills activate in Claude Code
Each skill has a `SKILL.md` with a `description:` frontmatter field. Claude Code reads these descriptions and injects the full skill into context when the trigger condition is matched. Skills fire automatically — you do not need to load them manually.

---

## Setup: Codex

### Step 1 — Ensure AGENTS.md is at the repo root
`AGENTS.md` is auto-generated from the spec. It should already exist at `memory-core/AGENTS.md`.

To regenerate:
```bash
python adapters/generate.py codex
```

### Step 2 — Open the memory-core folder as your working directory in Codex
Codex auto-loads `AGENTS.md` from the working directory root.

### Step 3 — Start a session
Type:
```
{{COMPANION_NAME}}
```

Codex will read the session start instructions from AGENTS.md and load the memory files.

### Note on auto-triggers in Codex
Unlike Claude Code, Codex does not have a plugin system with automatic skill injection. Skills are defined inline in AGENTS.md. {{COMPANION_NAME}} will follow them when the trigger phrase is matched, but may require the explicit phrase — passive auto-triggers are best-effort.

---

## Setup: ChatGPT (Custom GPT or API)

### Option A — Custom GPT

1. Go to ChatGPT → Explore GPTs → Create a GPT
2. In the **Instructions** field, paste the contents of `outputs/chatgpt-system-prompt.md`
3. In the **Knowledge** section, upload:
   - `main/main-memory.md`
   - `main/current-session.md`
4. Save the GPT

### Option B — API system prompt

```python
import openai

with open("outputs/chatgpt-system-prompt.md") as f:
    system_prompt = f.read()

client = openai.OpenAI()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "{{COMPANION_NAME}}"},
    ]
)
```

### Limitations on ChatGPT
- No file write access — {{COMPANION_NAME}} cannot update memory files directly
- No git access — commit and push skills are descriptive only
- Skills work as instructions, not as code execution

---

## Setup: Gemini

### Option A — Google AI Studio

1. Open [Google AI Studio](https://aistudio.google.com)
2. Click **System instructions**
3. Paste the contents of `outputs/gemini-system-instruction.md`
4. Upload `main/main-memory.md` and `main/current-session.md` as context files

### Option B — API

```python
import google.generativeai as genai

with open("outputs/gemini-system-instruction.md") as f:
    system_instruction = f.read()

model = genai.GenerativeModel(
    model_name="gemini-1.5-pro",
    system_instruction=system_instruction
)
chat = model.start_chat()
response = chat.send_message("{{COMPANION_NAME}}")
```

---

## Setup: Any Other LLM

Use the generic prompt at `outputs/generic-prompt.md`.

1. Paste it into the system prompt / custom instructions field
2. Attach or paste `main/main-memory.md` as additional context
3. Attach or paste `main/current-session.md` as additional context
4. Type `"{{COMPANION_NAME}}"` to start

This works with any LLM that has a system prompt field.

---

## Daily Workflow

The minimum viable workflow — what to do each session:

```
Session start:
  Type "{{COMPANION_NAME}}"
  → AI loads memory, delivers brief

During work:
  Type "load project [name]"     if working on a specific project
  Do your work normally

Session end:
  Type "save"                    to save memory and session context
  Type "save project"            to update project duration/status (optional)
```

That's it. Two commands per session keeps everything tracked.

---

## Skill Command Reference

### Memory & Session

| Command | What it does |
|---------|-------------|
| `"{{COMPANION_NAME}}"` | Full memory restoration + session brief |
| `"skip brief"` | Suppress session brief for this session |
| `"brief"` | Re-deliver brief mid-session |
| `"save"` | Save memory and session context to files |

### Context Modules

| Command | What it does |
|---------|-------------|
| _(automatic)_ | Every `context/*.md` module loads at session start and before any skill runs |
| `"reload context"` | Re-read the modules mid-session, after editing one |

Add a module by creating `context/NN-name.md` with `module:` frontmatter. It loads next session —
nothing else to update. Run `python adapters/generate.py all` afterwards so the ChatGPT and Gemini
prompts pick it up.

### Memory Recall

| Command | What it does |
|---------|-------------|
| `"recall [topic]"` | Search session memory and notes for past sessions on a topic |
| `"check history"` | Broad search across current-session, session-archive, notes, and project timelines |

### Project Management

| Command | What it does |
|---------|-------------|
| `"new project [name]"` | Create a project — document-project scaffolds it from the template |
| `"load project [name]"` | Resume project — fuzzy search, moves to #1 |
| `"save project"` | Append this session's work to the project `Timeline.md` |
| `"list projects"` | List projects by last activity, with active/completed feature counts |

Every project lives in `project-management/{name}/`. There is no separate registry or archive limit.

### Forge (Self-Improvement)

| Command | What it does |
|---------|-------------|
| `"create skill [name]"` | Propose a new skill |
| `"level up [skill]"` | Propose an improvement to an existing skill |
| `"self improve"` | Review recent patterns and propose improvements |

Human-in-the-loop: {{COMPANION_NAME}} proposes, you approve. Never creates skills autonomously.

---

## Maintaining the Spec

### When to edit memory-core.yaml

- Adding a new skill
- Levelling up an existing skill (new behavior, new trigger)
- Changing identity details (name, email, communication style)
- Adding a new memory file

### Workflow

```bash
# 1. Edit the spec
nano memory-core.yaml

# 2. Validate (no files written)
python adapters/generate.py validate

# 3. Generate all platform files
python adapters/generate.py all

# 4. Commit
git add memory-core.yaml AGENTS.md outputs/ plugins/violet-skills/skills/
git commit -m "feat: ..."
```

### Never edit generated files directly

These files are generated — manual edits will be overwritten on the next `generate.py all`:
- `AGENTS.md`
- `outputs/chatgpt-system-prompt.md`
- `outputs/gemini-system-instruction.md`
- `outputs/generic-prompt.md`
- `plugins/violet-skills/skills/*/SKILL.md`

---

## File Structure Reference

```
memory-core/
  memory-core.yaml          ← source of truth for all skills and identity
  AGENTS.md                 ← Codex entry point (generated)
  USER-GUIDE.md             ← this file

  adapters/                 ← adapter engine
    generate.py             ← CLI: python adapters/generate.py [platform|all|validate]
    spec_loader.py          ← parses memory-core.yaml into Python dataclasses
    claude_adapter.py       ← generates SKILL.md files
    codex_adapter.py        ← generates AGENTS.md
    chatgpt_adapter.py      ← generates ChatGPT system prompt
    gemini_adapter.py       ← generates Gemini system instruction
    generic_adapter.py      ← generates universal markdown prompt

  outputs/                  ← generated platform prompts (do not edit)
    chatgpt-system-prompt.md
    gemini-system-instruction.md
    generic-prompt.md

  context/                  ← always-on memory modules (edit freely)
    README.md               ← the convention
    NN-name.md              ← one module per file, numeric prefix sets load order

  main/                     ← memory store (edit freely)
    main-memory.md          ← identity and {{USER_NAME}} profile
    current-session.md      ← session RAM (3 most recent sessions)
    session-archive.md      ← older session recaps, moved out by save-memory
    preferences.md          ← PPTX/design preferences
    projects-context.md     ← project context mapping

  plugins/violet-skills/    ← Claude Code plugin (generated)
    skills/*/SKILL.md

  project-management/       ← the project index
    {name}/                 ← General.md · Components.md · Design.md · Timeline.md
      Features/{Component}/Development/   ← active feature files
      Features/{Component}/Completed/     ← finished feature files
      Plans/                ← symlinks to brainstorms and plans

  project-plans/            ← phase-by-phase plans (active / archived / done)

  brainstorming/            ← brainstorm sessions (active / archived / done)

```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| {{COMPANION_NAME}} doesn't fire session brief | Check plugin is installed: `claude plugin list` |
| Skills not triggering | Ensure plugin is enabled in `~/.claude/settings.json` |
| AGENTS.md out of date | Run `python adapters/generate.py codex` |
| Skill behavior changed unexpectedly | Check if you edited a generated file — re-run `generate.py all` |
| Memory not persisting | Ensure you type `"save"` before ending session |
| Project not found on load | Use partial name — fuzzy matching is active |
| Plan not resuming correctly | Check `Project Resources/project-plan.md` exists and has `[ ]` items |

---

*One word restores everything: `"{{COMPANION_NAME}}"`*
