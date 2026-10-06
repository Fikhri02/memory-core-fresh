"""
spec_loader.py
Loads and parses memory-core.yaml into typed Python dataclasses.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
import yaml


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class Trigger:
    explicit: list[str] = field(default_factory=list)
    passive: str | None = None


@dataclass
class ProtocolStep:
    step: int
    description: str
    action: str
    target: str | None = None
    command: str | None = None
    condition: str | None = None


@dataclass
class Skill:
    name: str
    description: str
    tier: str                              # always_active | on_demand
    level: int
    triggers: Trigger
    activation_message: str | None
    protocol: list[ProtocolStep]
    rules: list[str]
    output_format: str | None
    level_history: dict[int, str]
    raw: dict                              # full raw YAML block for adapter use


@dataclass
class MemoryFile:
    path: str
    purpose: str
    load: str
    line_limit: int | None = None


@dataclass
class SessionStart:
    steps: list[dict]
    time_tone: dict[str, dict]
    suppressors: list[dict]
    re_triggers: list[dict]


@dataclass
class VioletSpec:
    version: str
    identity: dict
    memory_files: dict[str, list[MemoryFile]]
    session_start: SessionStart
    skills: dict[str, Skill]
    raw: dict                              # full raw YAML for adapters that need it


# =============================================================================
# Loader
# =============================================================================

def load_spec(spec_path: str | Path) -> VioletSpec:
    """Load memory-core.yaml and return a parsed VioletSpec."""
    spec_path = Path(spec_path)
    if not spec_path.exists():
        raise FileNotFoundError(f"Spec file not found: {spec_path}")

    with open(spec_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    return VioletSpec(
        version=raw.get("version", "1.0"),
        identity=raw.get("identity", {}),
        memory_files=_parse_memory_files(raw.get("memory_files", {})),
        session_start=_parse_session_start(raw.get("session_start", {})),
        skills=_parse_skills(raw.get("skills", {})),
        raw=raw,
    )


def _parse_memory_files(raw: dict) -> dict[str, list[MemoryFile]]:
    result: dict[str, list[MemoryFile]] = {}
    for category, entries in raw.items():
        result[category] = [
            MemoryFile(
                path=e["path"],
                purpose=e.get("purpose", ""),
                load=e.get("load", ""),
                line_limit=e.get("line_limit"),
            )
            for e in entries
        ]
    return result


def _parse_session_start(raw: dict) -> SessionStart:
    return SessionStart(
        steps=raw.get("steps", []),
        time_tone=raw.get("time_tone", {}),
        suppressors=raw.get("suppressors", []),
        re_triggers=raw.get("re_triggers", []),
    )


def _parse_skills(raw: dict) -> dict[str, Skill]:
    skills: dict[str, Skill] = {}
    for name, data in raw.items():
        trigger_raw = data.get("triggers", {})
        triggers = Trigger(
            explicit=trigger_raw.get("explicit", []),
            passive=trigger_raw.get("passive"),
        )

        protocol_raw = data.get("protocol", [])
        protocol = [
            ProtocolStep(
                step=s.get("step", i + 1),
                description=s.get("description", ""),
                action=s.get("action", ""),
                target=s.get("target"),
                command=s.get("command"),
                condition=s.get("condition"),
            )
            for i, s in enumerate(protocol_raw)
        ]

        level_history_raw = data.get("level_history", {})
        level_history = {int(k): v for k, v in level_history_raw.items()} if level_history_raw else {}

        skills[name] = Skill(
            name=name,
            description=_clean_description(data.get("description", "")),
            tier=data.get("tier", "on_demand"),
            level=data.get("level", 1),
            triggers=triggers,
            activation_message=data.get("activation_message"),
            protocol=protocol,
            rules=data.get("rules", []),
            output_format=data.get("output_format"),
            level_history=level_history,
            raw=data,
        )
    return skills


def _clean_description(desc: str) -> str:
    """Collapse multi-line YAML block scalars into a single clean string."""
    return " ".join(desc.split())


# =============================================================================
# Validation
# =============================================================================

def validate_spec(spec: VioletSpec, memory_root: Path) -> list[str]:
    """
    Validate the spec against the filesystem.
    Returns a list of warning strings (empty = all good).
    """
    warnings: list[str] = []

    for category, files in spec.memory_files.items():
        for mf in files:
            if not (memory_root / mf.path).exists():
                warnings.append(f"MISSING memory file: {mf.path}")

    # Compare names, not a count: a hard-coded total went stale every time a skill was added.
    skills_root = memory_root / "plugins" / "violet-skills" / "skills"
    on_disk = ({d.name for d in skills_root.iterdir() if (d / "SKILL.md").is_file()}
               if skills_root.is_dir() else set())
    for name in sorted(set(spec.skills) - on_disk):
        warnings.append(f"MISSING skill directory: plugins/violet-skills/skills/{name}/")
    for name in sorted(on_disk - set(spec.skills)):
        warnings.append(f"MISSING from spec: plugins/violet-skills/skills/{name}/ has no entry in memory-core.yaml")

    return warnings


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    import sys

    spec_file = Path(__file__).parent.parent / "memory-core.yaml"
    memory_root = spec_file.parent

    spec = load_spec(spec_file)
    print(f"Loaded memory-core.yaml v{spec.version}")
    print(f"Skills: {len(spec.skills)}")
    for name, skill in spec.skills.items():
        print(f"  [{skill.tier[:2].upper()}] {name} (Lv.{skill.level}) — {len(skill.protocol)} steps")

    warnings = validate_spec(spec, memory_root)
    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  ! {w}")
    else:
        print("\nValidation: all OK")
