"""
setup.py — memory-core First-Run Setup Wizard
Run once to personalize your AI companion.

Usage:
    python setup.py
    python setup.py --reset   (re-run and overwrite existing setup)
"""

from __future__ import annotations

import json
import sys
import os
import shutil
import subprocess
from pathlib import Path
from datetime import date


# =============================================================================
# Dependency check
# =============================================================================

def ensure_pyyaml() -> None:
    try:
        import yaml
    except ImportError:
        print("PyYAML is required but not installed.")
        answer = input("Install it now? (y/n): ").strip().lower()
        if answer == "y":
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyyaml"])
            print()
        else:
            print("Please run: pip install pyyaml")
            sys.exit(1)


def check_python_version() -> None:
    if sys.version_info < (3, 8):
        print(f"Warning: Python 3.8+ recommended. You have {sys.version}.")
        print("Setup will continue but some features may not work correctly.")
        print()


# =============================================================================
# Input collection
# =============================================================================

def prompt_required(label: str) -> str:
    while True:
        value = input(f"  {label}: ").strip()
        if value:
            return value
        print(f"  '{label}' is required. Please enter a value.")


def prompt_optional(label: str, default: str = "") -> str:
    display = f"  {label} (press Enter to skip): "
    value = input(display).strip()
    return value if value else default


def collect_inputs() -> dict[str, str]:
    print("=" * 55)
    print("  Welcome to the memory-core setup!")
    print("  You are about to create your own AI companion.")
    print("=" * 55)
    print()
    print("Required:")
    companion_name = prompt_required("Companion name (e.g. Violet, Nova, Aria, Max)")
    user_name = prompt_required("Your name")

    print()
    print("Optional (press Enter to skip):")
    user_email = prompt_optional("Your email")
    user_company = prompt_optional("Company / organisation")
    user_role = prompt_optional("Your role", default="Developer")
    user_git = prompt_optional("Git username")

    return {
        "{{COMPANION_NAME}}": companion_name,
        "{{USER_NAME}}": user_name,
        "{{USER_EMAIL}}": user_email,
        "{{USER_COMPANY}}": user_company,
        "{{USER_ROLE}}": user_role,
        "{{USER_GIT_USERNAME}}": user_git,
        "{{GIT_USERNAME}}": user_git,
        "{{USER_LOCATION}}": "",
        "{{SETUP_DATE}}": date.today().isoformat(),
    }


# =============================================================================
# Re-run guard
# =============================================================================

def is_already_setup(root: Path) -> bool:
    spec = root / "memory-core.yaml"
    if not spec.exists():
        return False
    content = spec.read_text(encoding="utf-8")
    return "{{COMPANION_NAME}}" not in content


def confirm_overwrite() -> bool:
    print("Setup has already been run for this companion.")
    answer = input("Re-run and overwrite existing setup? (y/n): ").strip().lower()
    return answer == "y"


# =============================================================================
# Placeholder replacement
# =============================================================================

def replace_placeholders(content: str, tokens: dict[str, str]) -> str:
    for placeholder, value in tokens.items():
        content = content.replace(placeholder, value)
    return content


def process_template_file(src: Path, dst: Path, tokens: dict[str, str]) -> None:
    content = src.read_text(encoding="utf-8")
    content = replace_placeholders(content, tokens)
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(content, encoding="utf-8")


# =============================================================================
# Setup steps
# =============================================================================

def step_write_spec(root: Path, tokens: dict[str, str]) -> None:
    template = root / "memory-core-template.yaml"
    spec = root / "memory-core.yaml"
    if not template.exists():
        print("  ERROR: memory-core-template.yaml not found.")
        sys.exit(1)
    process_template_file(template, spec, tokens)
    print("  [1/6] Writing memory-core.yaml...          done")


def step_write_memory_files(root: Path, tokens: dict[str, str]) -> None:
    templates_dir = root / "_templates" / "main"
    target_dir = root / "main"

    if not templates_dir.exists():
        print("  WARNING: _templates/main/ not found — skipping memory file generation.")
        return

    count = 0
    for template_file in templates_dir.glob("*.md"):
        dst = target_dir / template_file.name
        process_template_file(template_file, dst, tokens)
        count += 1

    # Root-level docs that carry placeholders (USER-GUIDE.md, etc.)
    # README.md is skipped: it documents _templates/ itself and is not a template.
    # Rendering it would overwrite the repo's own README.md.
    for template_file in (root / "_templates").glob("*.md"):
        if template_file.name == "README.md":
            continue
        process_template_file(template_file, root / template_file.name, tokens)
        count += 1

    print(f"  [2/6] Generating memory files...           done ({count} files)")


def step_run_adapters(root: Path) -> None:
    generate_script = root / "adapters" / "generate.py"
    if not generate_script.exists():
        print("  ERROR: adapters/generate.py not found.")
        sys.exit(1)

    print("  [3/6] Running adapters (Codex, ChatGPT, Gemini, generic)...")
    print("        Claude Code reads plugins/violet-skills/skills/*/SKILL.md directly —")
    print("        those are hand-written and are not generated from the spec.")
    platforms = ["codex", "chatgpt", "gemini", "generic"]
    for platform in platforms:
        result = subprocess.run(
            [sys.executable, str(generate_script), platform],
            capture_output=True, text=True, cwd=root
        )
        status = "done" if result.returncode == 0 else "FAILED"
        label = f"        - {platform.title()} output"
        print(f"{label:<40} {status}")
        if result.returncode != 0:
            print(f"          {result.stderr.strip()}")


def step_write_claude_settings(root: Path) -> None:
    """Register the local plugin marketplace at this machine's actual path.

    This cannot ship in the repo: the path differs on every device, and a stale absolute
    path silently points Claude Code at a folder that does not exist.
    """
    settings_dir = root / ".claude"
    settings_dir.mkdir(exist_ok=True)
    settings_file = settings_dir / "settings.json"

    existing = {}
    if settings_file.exists():
        try:
            existing = json.loads(settings_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print("  WARNING: .claude/settings.json is not valid JSON — leaving it alone.")
            return

    existing.setdefault("extraKnownMarketplaces", {})["violet-local"] = {
        "source": {"source": "directory", "path": str(root / "plugins")}
    }
    settings_file.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print("  [4/6] Writing .claude/settings.json...        done")


def step_register_mcp(root: Path) -> None:
    """Offer to register the context/health MCP server for this machine."""
    server = root / "mcp-spike" / "server.py"
    if not server.exists():
        return

    print()
    answer = input("  Register the memory-core MCP server (context_load, health_check)? (y/n): ").strip().lower()
    if answer != "y":
        print("  [5/6] Registering MCP server...              skipped by choice")
        print("        To do it later:")
        print(f"          claude mcp add --scope user memory-core-context -- \\")
        print(f"            {sys.executable} \\")
        print(f"            {server} --root={root}")
        return

    try:
        result = subprocess.run(
            ["claude", "mcp", "add", "--scope", "user", "memory-core-context", "--",
             sys.executable, str(server), f"--root={root}"],
            capture_output=True, text=True,
        )
    except FileNotFoundError:
        print("  [5/6] Registering MCP server...              skipped (claude CLI not found)")
        return
    if result.returncode == 0 or _already_done(result):
        print("  [5/6] Registering MCP server...              done")
    else:
        print("  [5/6] Registering MCP server...              FAILED")
        print(f"          {(result.stderr or result.stdout).strip()}")


PLUGIN_ID = "violet-skills@violet-local"


def _print_manual_install(root: Path) -> None:
    print()
    print("  To install manually, run:")
    print(f"    claude plugin marketplace add {root / 'plugins'}")
    print(f"    claude plugin install {PLUGIN_ID}")


def _already_done(result: subprocess.CompletedProcess) -> bool:
    """The CLI exits non-zero when the marketplace or plugin is already there.
    Re-running setup must not report that as a failure."""
    return "already" in f"{result.stdout}\n{result.stderr}".lower()


def step_install_plugin(root: Path) -> None:
    """Register the plugins/ folder as a marketplace, then install violet-skills from it."""
    print("  [6/6] Installing Claude Code plugin...", end="", flush=True)
    commands = [
        ["claude", "plugin", "marketplace", "add", str(root / "plugins")],
        ["claude", "plugin", "install", PLUGIN_ID],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True)
        except FileNotFoundError:
            print("      skipped (claude CLI not found)")
            _print_manual_install(root)
            return
        if result.returncode != 0 and not _already_done(result):
            print("      FAILED")
            print(f"          {(result.stderr or result.stdout).strip()}")
            _print_manual_install(root)
            return
    print("      done")


# =============================================================================
# Success summary
# =============================================================================

def print_summary(tokens: dict[str, str]) -> None:
    name = tokens["{{COMPANION_NAME}}"]
    user = tokens["{{USER_NAME}}"]

    print()
    print("=" * 55)
    print("  Setup complete!")
    print(f"  Your companion's name is: {name}")
    print(f"  Wake word: \"{name}\"")
    print("=" * 55)
    print()
    print("Next steps:")
    print(f"  Claude Code:  Open this folder, type \"{name}\"")
    print(f"  Codex:        Open this folder in Codex, type \"{name}\"")
    print("  ChatGPT:      Paste outputs/chatgpt-system-prompt.md into")
    print("                Custom GPT Instructions, upload main/ files as Knowledge")
    print("  Gemini:       Paste outputs/gemini-system-instruction.md into")
    print("                System Instructions, attach main/ files")
    print("  Any LLM:      Use outputs/generic-prompt.md as your system prompt")
    print()
    print("  Full guide:   USER-GUIDE.md")
    print()


# =============================================================================
# Main
# =============================================================================

def step_mark_context(root: Path) -> None:
    """A personalised install is a context install — never the framework (sync and its guard rely on it)."""
    marker = root / ".memory-core" / "kind"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("context\n", encoding="utf-8")


def clone_for_sync(url: str, dest: str) -> int:
    """Clone the private memory repo sparsely, with every core folder checked out (no projects yet),
    so the clone's own setup.py, adapters/ and mcp-spike/ exist before setup runs."""
    cloned = subprocess.run(["git", "clone", "--sparse", url, dest])
    if cloned.returncode != 0:
        return cloned.returncode
    listing = subprocess.run(["git", "-C", dest, "ls-tree", "-d", "-z", "--name-only", "HEAD"],
                             capture_output=True, text=True).stdout
    opt_in = ("project-management", "ecosystem")
    patterns = [d for d in listing.split("\0") if d and d not in opt_in]
    patterns += [f"{kind}/_template" for kind in opt_in
                 if subprocess.run(["git", "-C", dest, "cat-file", "-e", f"HEAD:{kind}/_template"],
                                   capture_output=True).returncode == 0]
    return subprocess.run(["git", "-C", dest, "sparse-checkout", "set", "--cone", *patterns]).returncode


def _clone_kind(root: Path) -> str | None:
    """A fresh sparse clone has not checked .memory-core/ out yet, so fall back to git."""
    marker = root / ".memory-core" / "kind"
    if marker.is_file():
        return marker.read_text(encoding="utf-8").strip()
    proc = subprocess.run(["git", "-C", str(root), "show", "HEAD:.memory-core/kind"], capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def step_join_sync(root: Path) -> None:
    """New laptop: this folder is a sparse clone of the private context repo."""
    if _clone_kind(root) != "context":
        print("This folder is not a memory-core context clone (.memory-core/kind is not 'context').")
        print("Clone your private memory repo first:  python3 setup.py --sync <repo URL> [folder]")
        return
    step_run_adapters(root)
    step_write_claude_settings(root)
    step_register_mcp(root)
    step_install_plugin(root)
    name = prompt_optional("Name for this device", "")
    account = prompt_optional("GitHub account that owns the private repo", "")
    args = [sys.executable, str(root / "mcp-spike" / "sync_git.py"), "--root", str(root), "join"]
    if name:
        args += ["--name", name]
    if account:
        args += ["--account", account]
    subprocess.run(args)
    print()
    print("Device registered. In a Claude Code session here, say 'sync status' and then")
    print("'follow project <name>' for each project this laptop should have.")


def main() -> None:
    check_python_version()
    ensure_pyyaml()

    root = Path(__file__).parent
    if "--sync" in sys.argv:
        rest = sys.argv[sys.argv.index("--sync") + 1:]
        if rest:
            url = rest[0]
            dest = rest[1] if len(rest) > 1 else str(Path.cwd() / "memory-core")
            if clone_for_sync(url, dest) == 0:
                subprocess.run([sys.executable, str(Path(dest) / "setup.py"), "--sync"])
            else:
                print(f"Could not clone {url} — check the URL and your access to it.")
        else:
            step_join_sync(root)
        return
    force_reset = "--reset" in sys.argv

    if not force_reset and is_already_setup(root):
        if not confirm_overwrite():
            print("Setup cancelled.")
            sys.exit(0)
        print()

    tokens = collect_inputs()
    print()
    print("Setting up your companion...")

    step_write_spec(root, tokens)
    step_write_memory_files(root, tokens)
    step_mark_context(root)
    step_run_adapters(root)
    step_write_claude_settings(root)
    step_register_mcp(root)
    step_install_plugin(root)

    print_summary(tokens)


if __name__ == "__main__":
    main()
