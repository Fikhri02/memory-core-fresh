"""Device identity, followed items, local repo paths and the device registry for memory-core sync.

Stdlib only. Everything under device/ is machine-only (git-ignored). devices/{id}.md is synced —
one file per device, written only by that device, so the registry never causes a merge conflict.
"""

from __future__ import annotations

import json
import platform
import re
import socket
import uuid
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit

DEVICE_DIR = "device"
REGISTRY_DIR = "devices"
KINDS = {"project-management": "Projects", "ecosystem": "Ecosystems"}
KV_LINE = re.compile(r"^([a-z_]+):[ \t]*(.*)$", re.M)
FOLLOW_ITEM = re.compile(r"^- \[([ xX])\] +(\S+)[ \t]*$")
PATH_ROW = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$")
SAFE_TRANSPORTS = {"stdio", "http", "sse"}
STATUS = re.compile(r"\*\*Status\*\*: (\w+)")
LAST_SYNC = re.compile(r"\*\*Last sync\*\*: (\d{4}-\d{2}-\d{2}[^·\n]*?)\s*·")
ID_FIELD = re.compile(r"\*\*Id\*\*: ([0-9a-f-]{36})")


def read_kv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    return {k: v.strip() for k, v in KV_LINE.findall(path.read_text(encoding="utf-8"))}


def write_kv(path: Path, values: dict[str, str], title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"{k}: {v}" for k, v in values.items())
    path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")


def slug_name(text: str) -> str:
    text = text.lower().removesuffix(".local")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-") or "device"


def ensure_identity(root: Path, name: str | None = None, today: date | None = None) -> dict[str, str]:
    path = root / DEVICE_DIR / "id.md"
    current = read_kv(path)
    if current.get("id"):
        return current
    identity = {
        "id": str(uuid.uuid4()),
        "name": slug_name(name or socket.gethostname()),
        "registered": (today or date.today()).isoformat(),
    }
    write_kv(path, identity, "Device identity — never synced")
    return identity


def read_follow(root: Path) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {kind: [] for kind in KINDS}
    path = root / DEVICE_DIR / "follow.md"
    if not path.is_file():
        return result
    titles = {title: kind for kind, title in KINDS.items()}
    current = None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            current = titles.get(line[3:].strip())
            continue
        m = FOLLOW_ITEM.match(line)
        if current and m and m.group(1) in "xX" and m.group(2) not in result[current]:
            result[current].append(m.group(2))
    return result


def write_follow(root: Path, follows: dict[str, list[str]]) -> None:
    lines = ["# Followed on this device — never synced", ""]
    for kind, title in KINDS.items():
        lines += [f"## {title}", ""]
        lines += [f"- [x] {slug}" for slug in sorted(set(follows.get(kind, [])))] or ["_(none)_"]
        lines.append("")
    path = root / DEVICE_DIR / "follow.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def read_paths(root: Path) -> dict[str, str]:
    path = root / DEVICE_DIR / "paths.md"
    if not path.is_file():
        return {}
    result = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = PATH_ROW.match(line)
        if not m or set(m.group(1)) <= {"-"} or m.group(1) == "Git origin":
            continue
        result[m.group(1).strip("`")] = m.group(2).strip("`")
    return result


def set_path(root: Path, key: str, local: str) -> None:
    paths = read_paths(root)
    paths[key] = local
    rows = [f"| `{k}` | `{v}` |" for k, v in sorted(paths.items())]
    text = "\n".join(["# Repo locations on this device — never synced", "",
                      "| Git origin | Local path |", "|------------|------------|", *rows, ""])
    (root / DEVICE_DIR).mkdir(parents=True, exist_ok=True)
    (root / DEVICE_DIR / "paths.md").write_text(text, encoding="utf-8")


def _json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _source(src: dict) -> str:
    kind = src.get("source", "")
    if kind == "github":
        return f"github {src.get('repo', '')}".strip()
    if kind in ("git", "url"):
        parts = urlsplit(str(src.get("url", "")))
        return f"git {parts.hostname or ''}{parts.path}".strip()
    if kind == "directory":
        return "local directory"
    return kind or "unknown"


def plugin_rows(claude_dir: Path, settings_path: Path) -> list[tuple[str, str, str]]:
    installed = _json(claude_dir / "plugins" / "installed_plugins.json").get("plugins", {})
    markets = _json(claude_dir / "plugins" / "known_marketplaces.json")
    enabled = _json(settings_path).get("enabledPlugins", {})
    rows = []
    for key in sorted(installed):
        name, _, market = key.partition("@")
        if name == "violet-skills":
            continue
        source = _source(markets.get(market, {}).get("source", {}))
        rows.append((name, f"{market} ({source})", "yes" if enabled.get(key) else "no"))
    return rows


def _executable(command: str) -> str:
    for token in command.split():
        if "=" not in token:
            return Path(token).name
    return "—"


def _mcp_row(name: str, scope: str, server: dict) -> tuple[str, str, str, str]:
    transport = server.get("type", "stdio")
    if transport not in SAFE_TRANSPORTS:
        transport = "other"
    if server.get("url"):
        runs = urlsplit(str(server["url"])).hostname or "—"
    else:
        runs = _executable(str(server.get("command", "")))
    return (name, scope, transport, runs)


def mcp_rows(claude_json: Path, repo_root: Path, claude_dir: Path) -> list[tuple[str, str, str, str]]:
    config = _json(claude_json)
    rows = [_mcp_row(n, "user", s) for n, s in sorted(config.get("mcpServers", {}).items()) if isinstance(s, dict)]
    for project in config.get("projects", {}).values():
        servers = project.get("mcpServers", {}) if isinstance(project, dict) else {}
        rows += [_mcp_row(n, "project", s) for n, s in sorted(servers.items()) if isinstance(s, dict)]
    repo = _json(repo_root / ".mcp.json").get("mcpServers", {})
    rows += [_mcp_row(n, "repo", s) for n, s in sorted(repo.items()) if isinstance(s, dict)]
    installed = _json(claude_dir / "plugins" / "installed_plugins.json").get("plugins", {})
    for key in sorted(installed):
        entries = installed[key] if isinstance(installed[key], list) else [installed[key]]
        install_path = entries[0].get("installPath", "") if entries and isinstance(entries[0], dict) else ""
        if not install_path:
            continue
        bundle = _json(Path(install_path) / ".mcp.json")
        servers = bundle.get("mcpServers", bundle)
        plugin = key.partition("@")[0]
        rows += [_mcp_row(n, f"plugin {plugin}", s) for n, s in sorted(servers.items())
                 if isinstance(s, dict) and ("command" in s or "url" in s)]
    return rows


def os_label() -> str:
    if platform.system() == "Darwin" and platform.mac_ver()[0]:
        return f"macOS {platform.mac_ver()[0]}"
    return f"{platform.system()} {platform.release()}".strip()


def device_record(identity: dict, follows: dict, plugins: list, mcps: list, last_sync: str,
                  os_name: str, status: str = "active") -> str:
    items = list(follows.get("project-management", [])) + [f"ecosystem {e}" for e in follows.get("ecosystem", [])]
    lines = [
        f"# {identity['name']}",
        "",
        f"**Id**: {identity['id']} · **Registered**: {identity['registered']} · **Last sync**: {last_sync} · **Status**: {status}",
        f"**OS**: {os_name}",
        "",
        "## Follows",
        "",
        f"- {' · '.join(items)}" if items else "- _(core only)_",
        "",
        "## Plugins",
        "",
        "| Plugin | Marketplace (source) | Enabled |",
        "|--------|----------------------|---------|",
    ]
    lines += [f"| {p} | {m} | {e} |" for p, m, e in plugins] or ["| _(none)_ | | |"]
    lines += ["", "## MCP servers", "", "| Server | Scope | Transport | Runs |", "|--------|-------|-----------|------|"]
    lines += [f"| {n} | {s} | {t} | {r} |" for n, s, t, r in mcps] or ["| _(none)_ | | | |"]
    return "\n".join(lines) + "\n"


def registry_path(root: Path, device_id: str) -> Path:
    return root / REGISTRY_DIR / f"{device_id}.md"


def write_registry(root: Path, identity: dict, *, follows: dict, plugins: list, mcps: list,
                   now: datetime, os_name: str, status: str | None = None) -> Path:
    path = registry_path(root, identity["id"])
    if status is None:
        m = STATUS.search(path.read_text(encoding="utf-8")) if path.is_file() else None
        status = m.group(1) if m else "active"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(device_record(identity, follows, plugins, mcps, now.strftime("%Y-%m-%d %H:%M"), os_name, status),
                    encoding="utf-8")
    return path


def _table_first_cells(text: str) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    section = None
    for line in text.splitlines():
        if line.startswith("## "):
            section = line[3:].strip()
            continue
        if not section or not line.startswith("|"):
            continue
        first = line.strip().strip("|").split("|")[0].strip()
        if not first or set(first) <= set("-: ") or first in ("Plugin", "Server") or first.startswith("_("):
            continue
        result.setdefault(section, set()).add(first)
    return result


def read_registry(root: Path) -> list[dict]:
    devices = []
    for f in sorted((root / REGISTRY_DIR).glob("*.md")):
        text = f.read_text(encoding="utf-8")
        found = ID_FIELD.search(text)
        if not found:
            continue
        cells = _table_first_cells(text)
        status = STATUS.search(text)
        last = LAST_SYNC.search(text)
        devices.append({
            "id": found.group(1),
            "name": text.splitlines()[0].removeprefix("# ").strip(),
            "status": status.group(1) if status else "active",
            "last_sync": last.group(1).strip() if last else "",
            "plugins": cells.get("Plugins", set()),
            "mcp": cells.get("MCP servers", set()),
            "path": f,
        })
    return devices


def registry_differences(devices: list[dict]) -> list[str]:
    active = [d for d in devices if d["status"] == "active"]
    diffs = []
    for field, label in (("plugins", "plugin"), ("mcp", "MCP server")):
        everything = set().union(*(d[field] for d in active)) if active else set()
        for d in active:
            diffs += [f"{d['name']} is missing {label} {item}" for item in sorted(everything - d[field])]
    return diffs


REPO_HEADER = re.compile(r"^\|\s*Name\s*\|\s*Local Path\s*\|\s*Git Origin\s*\|\s*$", re.I)
NO_ORIGIN = {"", "—", "-", "*(not set)*", "_(not set)_", "(not set)"}


def _first_path(cell: str) -> str:
    ticked = re.search(r"`([^`]+)`", cell)
    text = ticked.group(1) if ticked else cell.split(" (", 1)[0]
    text = text.strip()
    return "" if text in NO_ORIGIN else text


def migrate_general_paths(root: Path, write: bool = False) -> list[tuple[str, str, str]]:
    found: list[tuple[str, str, str]] = []
    for general in sorted((root / "project-management").glob("*/General.md")):
        project = general.parent.name
        if project.startswith("_"):
            continue
        lines = general.read_text(encoding="utf-8").split("\n")
        start = next((i for i, line in enumerate(lines) if REPO_HEADER.match(line)), None)
        if start is None:
            continue
        end = start + 2
        while end < len(lines) and lines[end].startswith("|"):
            end += 1
        rows = []
        for row in lines[start + 2:end]:
            cells = [c.strip() for c in row.strip().strip("|").split("|")]
            if len(cells) < 3:
                rows.append(row)
                continue
            name, local_cell, origin_cell = cells[0], cells[1], cells[2]
            local = _first_path(local_cell)
            origin = _first_path(origin_cell)
            if origin and not ("://" in origin or "@" in origin or origin.endswith(".git")):
                origin = ""  # a placeholder such as "_(no remote yet)_", not a remote
            if local:
                found.append((project, origin or f"{project}/{name}", local))
            rows.append(f"| {name} | {origin_cell} |")
        if write:
            new = lines[:start] + ["| Name | Git Origin |", "|------|------------|"] + rows + lines[end:]
            general.write_text("\n".join(new), encoding="utf-8")
    if write:
        for _, key, local in found:
            set_path(root, key, local)
    return found
