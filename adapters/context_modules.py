"""
context_modules.py — read and render the always-on memory modules in context/.

Claude Code and Codex read context/ live, so they only need the Context Load instruction.
ChatGPT, Gemini, and any generic LLM cannot list a directory, so their prompts get the
`always` module contents inlined at generation time.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


DEFAULT_PATH = "context/"
DEFAULT_LOAD = "always"
KNOWN_CONDITIONS = {"always", "on_design_session", "on_code_session", "on_project_load"}


@dataclass
class ContextModule:
    filename: str
    module: str
    load: str
    summary: str
    body: str
    warnings: list[str] = field(default_factory=list)

    @property
    def is_always(self) -> bool:
        return self.load == "always"


def _split_frontmatter(text: str) -> tuple[dict[str, str], str, list[str]]:
    """Return (fields, body, warnings). Tolerates a missing or malformed block."""
    warnings: list[str] = []
    if not text.startswith("---"):
        return {}, text.strip(), ["no frontmatter — treated as load: always"]

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip(), ["unterminated frontmatter — treated as load: always"]

    fields: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, parts[2].strip(), warnings


def read_modules(memory_root: Path, path: str = DEFAULT_PATH) -> list[ContextModule]:
    """Read every module in context/, in filename order. README.md is not a module."""
    root = Path(memory_root) / path
    if not root.is_dir():
        return []

    modules: list[ContextModule] = []
    for file in sorted(root.glob("*.md")):
        if file.name.lower() == "readme.md":
            continue

        fields, body, warnings = _split_frontmatter(file.read_text(encoding="utf-8"))
        load = fields.get("load", DEFAULT_LOAD)
        if load not in KNOWN_CONDITIONS:
            warnings.append(f"unrecognised load value '{load}' — treated as always")
            load = DEFAULT_LOAD
        if "module" not in fields:
            warnings.append("no module id — falling back to the filename")

        modules.append(
            ContextModule(
                filename=file.name,
                module=fields.get("module", file.stem),
                load=load,
                summary=fields.get("summary", ""),
                body=body,
                warnings=warnings,
            )
        )
    return modules


def _clean_body(body: str) -> str:
    """Strip authoring noise so the prompt gets the rules, not the scaffolding.

    Removes HTML comments (editing hints for the human) and a leading H1, which would
    otherwise sit redundantly under the ### heading render_inline already emits.
    """
    import re

    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    body = re.sub(r"\A\s*#\s+.*?\n", "", body)
    return "\n".join(line.rstrip() for line in body.strip().splitlines())


def render_inline(modules: list[ContextModule]) -> str:
    """Full text of the always-on modules, plus a note about conditional ones.

    Used by the prompt-based platforms, which have no filesystem to read.
    """
    always = [m for m in modules if m.is_always]
    conditional = [m for m in modules if not m.is_always]

    if not always and not conditional:
        return ""

    out = ["## Context Modules", ""]
    out.append(
        "Always-on memory. These rules apply to every session — treat them as standing "
        "instructions, not reference material."
    )
    out.append("")

    for m in always:
        out.append(f"### {m.module}")
        if m.summary:
            out.append(f"*{m.summary}*")
        out.append("")
        out.append(_clean_body(m.body))
        out.append("")

    if conditional:
        out.append("### Available on request")
        out.append("")
        for m in conditional:
            desc = f" — {m.summary}" if m.summary else ""
            out.append(f"- **{m.module}** (loads `{m.load}`){desc}")
        out.append("")
        out.append(
            "These are not included above. Ask the user for the module's contents if the "
            "session turns out to need it."
        )
        out.append("")

    return "\n".join(out).rstrip() + "\n"


def render_instruction(path: str = DEFAULT_PATH) -> str:
    """The Context Load step, for platforms that can read the folder themselves."""
    return (
        f"At the start of every session, before anything else: if `{path}` has not been read "
        f"this session, list `{path}*.md` and read each module in filename-prefix order.\n\n"
        "- A module with `load: always` (the default) is read immediately.\n"
        "- A module declaring a condition (`on_design_session`, `on_code_session`, "
        "`on_project_load`) is noted now and read once that condition is satisfied.\n"
        "- `README.md` is documentation, not a module — skip it.\n"
        "- A module with no frontmatter, or an unrecognised `load:` value, is treated as "
        "`always` and reported as a warning — never silently dropped.\n\n"
        "Report the loaded set in one line, e.g. "
        "`Context: git-rules · working-preferences (2 modules)`. "
        "Modules load once per session; re-check and skip if already loaded.\n"
    )


def warnings_for(modules: list[ContextModule]) -> list[str]:
    """Flatten per-module warnings for the generator to surface."""
    return [f"{m.filename}: {w}" for m in modules for w in m.warnings]
