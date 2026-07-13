#!/usr/bin/env python3
"""Install or strip PATH-based localdev project hooks (Cursor + Claude).

Managed entries are tagged with ``stockroom-localdev-managed`` in the command
string so clean can remove them without wiping unrelated hooks. Hooks call
on-path ``stockroom`` only (no PLUGIN_ROOT) — see creative-localdev-hooks-and-force.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MARKER = "stockroom-localdev-managed"
CMD = (
    f": {MARKER}; "
    'export PATH="$HOME/.local/bin:/usr/bin:/bin:$PATH"; '
    "{ stockroom shim rectify --owner dev; stockroom dashboard; } "
    ">/dev/null 2>&1 || true"
)


def install_cursor(path: Path) -> None:
    data: dict = {"version": 1, "hooks": {}}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data.setdefault("hooks", {})
    entries = [
        e
        for e in hooks.get("sessionStart", [])
        if MARKER not in str(e.get("command", ""))
    ]
    entries.append({"command": CMD, "timeout": 300})
    hooks["sessionStart"] = entries
    data["version"] = data.get("version", 1)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def clean_cursor(path: Path) -> None:
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    entries = [
        e
        for e in hooks.get("sessionStart", [])
        if MARKER not in str(e.get("command", ""))
    ]
    if entries:
        hooks["sessionStart"] = entries
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return
    hooks.pop("sessionStart", None)
    if not hooks:
        path.unlink(missing_ok=True)
    else:
        data["hooks"] = hooks
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def install_claude(path: Path) -> None:
    data: dict = {}
    if path.is_file():
        data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data.setdefault("hooks", {})
    groups = []
    for group in hooks.get("SessionStart", []):
        nested = [
            h
            for h in group.get("hooks", [])
            if MARKER not in str(h.get("command", ""))
        ]
        if nested:
            groups.append({**group, "hooks": nested})
    groups.append({"hooks": [{"type": "command", "command": CMD, "timeout": 300}]})
    hooks["SessionStart"] = groups
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def clean_claude(path: Path) -> None:
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    hooks = data.get("hooks", {})
    groups = []
    for group in hooks.get("SessionStart", []):
        nested = [
            h
            for h in group.get("hooks", [])
            if MARKER not in str(h.get("command", ""))
        ]
        if nested:
            groups.append({**group, "hooks": nested})
    if groups:
        hooks["SessionStart"] = groups
        data["hooks"] = hooks
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        return
    hooks.pop("SessionStart", None)
    if not hooks and set(data.keys()) <= {"hooks"}:
        path.unlink(missing_ok=True)
        return
    if hooks:
        data["hooks"] = hooks
    else:
        data.pop("hooks", None)
    if data:
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    else:
        path.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("install", "clean"))
    parser.add_argument(
        "--cursor-hooks",
        type=Path,
        default=Path(".cursor/hooks.json"),
    )
    parser.add_argument(
        "--claude-settings",
        type=Path,
        default=Path(".claude/settings.local.json"),
    )
    args = parser.parse_args(argv)
    if args.action == "install":
        install_cursor(args.cursor_hooks)
        install_claude(args.claude_settings)
    else:
        clean_cursor(args.cursor_hooks)
        clean_claude(args.claude_settings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
