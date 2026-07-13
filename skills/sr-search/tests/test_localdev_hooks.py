"""Tests for hooks/localdev_hooks.py — PATH-based localdev project hooks.

Managed entries are tagged with ``stockroom-localdev-managed``; install must
not use PLUGIN_ROOT; clean must preserve unrelated hooks.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def localdev_hooks(repo_root: Path):
    """Load hooks/localdev_hooks.py as a module (not on PYTHONPATH)."""
    path = repo_root / "hooks" / "localdev_hooks.py"
    spec = importlib.util.spec_from_file_location("localdev_hooks", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_install_adds_path_based_managed_hook_without_plugin_root(
    localdev_hooks, tmp_path: Path
) -> None:
    """Install writes Cursor+Claude managed hooks that call on-path stockroom."""
    cursor = tmp_path / "hooks.json"
    claude = tmp_path / "settings.local.json"
    assert localdev_hooks.main(
        [
            "install",
            "--cursor-hooks",
            str(cursor),
            "--claude-settings",
            str(claude),
        ]
    ) == 0
    c = json.loads(cursor.read_text(encoding="utf-8"))
    cmd = c["hooks"]["sessionStart"][0]["command"]
    assert localdev_hooks.MARKER in cmd
    assert "stockroom shim rectify --owner dev" in cmd
    assert "stockroom dashboard" in cmd
    assert "PLUGIN_ROOT" not in cmd
    cl = json.loads(claude.read_text(encoding="utf-8"))
    cl_cmd = cl["hooks"]["SessionStart"][0]["hooks"][0]["command"]
    assert localdev_hooks.MARKER in cl_cmd
    assert "PLUGIN_ROOT" not in cl_cmd


def test_clean_removes_managed_preserves_unrelated(
    localdev_hooks, tmp_path: Path
) -> None:
    """Clean strips managed entries and leaves unrelated sessionStart hooks."""
    cursor = tmp_path / "hooks.json"
    claude = tmp_path / "settings.local.json"
    cursor.write_text(
        json.dumps(
            {
                "version": 1,
                "hooks": {
                    "sessionStart": [{"command": "echo other", "timeout": 10}]
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    claude.write_text(
        json.dumps(
            {
                "hooks": {
                    "SessionStart": [
                        {
                            "hooks": [
                                {
                                    "type": "command",
                                    "command": "echo other",
                                    "timeout": 10,
                                }
                            ]
                        }
                    ]
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    assert localdev_hooks.main(
        [
            "install",
            "--cursor-hooks",
            str(cursor),
            "--claude-settings",
            str(claude),
        ]
    ) == 0
    assert localdev_hooks.main(
        [
            "clean",
            "--cursor-hooks",
            str(cursor),
            "--claude-settings",
            str(claude),
        ]
    ) == 0
    c = json.loads(cursor.read_text(encoding="utf-8"))
    assert c["hooks"]["sessionStart"] == [{"command": "echo other", "timeout": 10}]
    cl = json.loads(claude.read_text(encoding="utf-8"))
    assert cl["hooks"]["SessionStart"][0]["hooks"][0]["command"] == "echo other"


def test_clean_removes_file_when_only_managed(
    localdev_hooks, tmp_path: Path
) -> None:
    """When only managed content remains, clean deletes the hook files."""
    cursor = tmp_path / "hooks.json"
    claude = tmp_path / "settings.local.json"
    assert localdev_hooks.main(
        [
            "install",
            "--cursor-hooks",
            str(cursor),
            "--claude-settings",
            str(claude),
        ]
    ) == 0
    assert cursor.is_file() and claude.is_file()
    assert localdev_hooks.main(
        [
            "clean",
            "--cursor-hooks",
            str(cursor),
            "--claude-settings",
            str(claude),
        ]
    ) == 0
    assert not cursor.exists()
    assert not claude.exists()
