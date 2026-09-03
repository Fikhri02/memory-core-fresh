#!/usr/bin/env python3
"""
SPIKE — throwaway probe, not production code.

A dependency-free MCP server over stdio exposing two tools: context_load and health_check.
The question it answers: does moving context-module loading out of 12 markdown
guards and into a typed tool make the skills simpler, and can it run with no
dependencies beyond the stdlib?

Deliberately minimal: implements only the three methods a client needs
(initialize, tools/list, tools/call) and no framework.

Run:  python3 mcp-spike/server.py          (speaks JSON-RPC on stdin/stdout)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# The repo this server serves is fixed when the OPERATOR starts it — by argv or env,
# never by a tool argument. A model talking to this server cannot redirect it at another
# folder. That is the permission boundary the whole idea rests on: the tools decide what
# CAN be done, the launch decides WHERE.
def _resolve_root() -> Path:
    for arg in sys.argv[1:]:
        if arg.startswith("--root="):
            return Path(arg.split("=", 1)[1]).expanduser().resolve()
    env = os.environ.get("MEMORY_CORE_ROOT")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


# Data root: which repo this server reads. Varies by launch.
REPO_ROOT = _resolve_root()

# Code root: where the server's own modules live. Always beside this file — never the
# target repo, which may be an older checkout that does not have them.
SERVER_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SERVER_DIR))
sys.path.insert(0, str(SERVER_DIR.parent / "adapters"))

import context_modules  # noqa: E402  — path set above
import health  # noqa: E402


PROTOCOL_VERSION = "2025-06-18"
SERVER_INFO = {"name": "memory-core-context", "version": "0.0.1-spike"}

TOOLS = [
    {
        "name": "context_load",
        "description": (
            "Load the always-on memory modules from context/. Returns each module's "
            "id, summary and body, plus a one-line report and any warnings. Call once "
            "per session; pass session_type or project_loaded to also resolve "
            "conditional modules."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_type": {
                    "type": "string",
                    "enum": ["design", "code", "general"],
                    "description": "Classified session type, if known. Resolves on_design_session / on_code_session modules.",
                },
                "project_loaded": {
                    "type": "boolean",
                    "description": "True once a project has been resolved. Resolves on_project_load modules.",
                },
            },
            "additionalProperties": False,
        },
    },
    {
        "name": "health_check",
        "description": (
            "Scan this memory-core repo for structural drift: broken symlinks, memory files "
            "missing from MEMORY.md, skills missing from the spec, features that are 100% "
            "complete but still in Development/, and stale project timelines. Read-only — "
            "reports findings, never fixes them. Takes no path: the repo is fixed at launch."
        ),
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
]


def _condition_met(load: str, session_type: str | None, project_loaded: bool) -> bool:
    if load == "always":
        return True
    if load == "on_design_session":
        return session_type == "design"
    if load == "on_code_session":
        return session_type == "code"
    if load == "on_project_load":
        return project_loaded
    return False


def context_load(session_type: str | None = None, project_loaded: bool = False) -> dict:
    modules = context_modules.read_modules(REPO_ROOT)

    loaded, deferred = [], []
    for m in modules:
        if _condition_met(m.load, session_type, project_loaded):
            loaded.append(
                {"module": m.module, "load": m.load, "summary": m.summary, "body": m.body}
            )
        else:
            deferred.append({"module": m.module, "load": m.load, "summary": m.summary})

    names = " · ".join(m["module"] for m in loaded)
    report = f"Context: {names} ({len(loaded)} modules)" if loaded else "Context: no modules"

    warnings = context_modules.warnings_for(modules)
    if warnings:
        report += " — " + "; ".join(warnings)

    return {
        "report": report,
        "loaded": loaded,
        "deferred": deferred,
        "warnings": warnings,
    }


def handle(request: dict) -> dict | None:
    method = request.get("method")
    req_id = request.get("id")

    # Notifications carry no id and expect no reply.
    if req_id is None:
        return None

    def ok(result):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    if method == "initialize":
        return ok(
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            }
        )

    if method == "tools/list":
        return ok({"tools": TOOLS})

    if method == "tools/call":
        params = request.get("params", {})
        name = params.get("name")
        args = params.get("arguments") or {}

        if name == "context_load":
            result = context_load(
                session_type=args.get("session_type"),
                project_loaded=bool(args.get("project_loaded", False)),
            )
        elif name == "health_check":
            result = health.run_all(REPO_ROOT)
        else:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32602, "message": f"unknown tool: {name}"},
            }
        return ok(
            {
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}],
                "structuredContent": result,
            }
        )

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"method not found: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
