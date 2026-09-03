# Outputs

Generated platform prompts. **Everything here is written by `adapters/generate.py` — do not edit
by hand.** The next `generate.py all` overwrites it without asking.

---

| File | Platform | How to use it |
|------|----------|---------------|
| `chatgpt-system-prompt.md` | ChatGPT | Paste into Custom GPT → Instructions. Upload `main/*.md` as Knowledge. |
| `gemini-system-instruction.md` | Gemini | Paste into System Instructions. Attach `main/*.md`. |
| `generic-prompt.md` | Any LLM | Use as the system prompt. |

Two platforms are generated *outside* this folder: Codex reads `AGENTS.md` at the repo root, and
Claude Code reads `plugins/violet-skills/` directly.

## Why these are files and not live reads

ChatGPT and Gemini cannot list a directory. They cannot scan `context/` for always-on modules or
open a project folder on demand. So the adapters **inline** the always-on context modules into
these prompts at generation time.

The consequence: **editing a module in `context/` does nothing for ChatGPT or Gemini until you
re-run `python adapters/generate.py all`.** Claude Code and Codex read the folder live and need
no regeneration.

## Regenerating

```bash
python adapters/generate.py all
```

If a prompt looks stale, this is almost always why.
