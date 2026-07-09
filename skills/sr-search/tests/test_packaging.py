"""Cross-artifact packaging contract: dual manifests, skeleton skill, versions.

Driven from the engine's pytest but asserts against repo-root artifacts via
the ``repo_root`` fixture. Proves the committed layout is a valid install
layout for both Cursor and Claude Code, that the engine-bearing skill is
honestly present from Phase 0, and that all version sources agree.
"""

import json
from pathlib import Path

import pytest
import yaml

REQUIRED_MANIFEST_KEYS = {
    "name",
    "description",
    "version",
    "author",
    "homepage",
    "repository",
    "license",
}


@pytest.fixture(scope="module")
def cursor_manifest(repo_root: Path) -> dict:
    path = repo_root / ".cursor-plugin" / "plugin.json"
    assert path.is_file(), f"Cursor manifest missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def claude_manifest(repo_root: Path) -> dict:
    path = repo_root / ".claude-plugin" / "plugin.json"
    assert path.is_file(), f"Claude manifest missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def _front_matter(md_path: Path) -> dict:
    text = md_path.read_text(encoding="utf-8")
    assert text.startswith("---"), f"{md_path} has no YAML front-matter"
    _, fm, _ = text.split("---", 2)
    return yaml.safe_load(fm)


def test_both_manifests_carry_required_keys(
    cursor_manifest: dict, claude_manifest: dict
) -> None:
    """Both manifests parse and carry the required plugin keys."""
    assert REQUIRED_MANIFEST_KEYS <= cursor_manifest.keys()
    assert REQUIRED_MANIFEST_KEYS <= claude_manifest.keys()


def test_manifests_name_and_license(
    cursor_manifest: dict, claude_manifest: dict
) -> None:
    """Both manifests name the plugin ``stockroom`` and declare AGPL."""
    assert cursor_manifest["name"] == "stockroom"
    assert claude_manifest["name"] == "stockroom"
    assert cursor_manifest["license"] == "AGPL-3.0-or-later"
    assert claude_manifest["license"] == "AGPL-3.0-or-later"


def test_manifest_versions_match(cursor_manifest: dict, claude_manifest: dict) -> None:
    """The two manifest versions are in lockstep with each other."""
    assert cursor_manifest["version"] == claude_manifest["version"]


def test_cursor_skills_pointer_resolves(cursor_manifest: dict, repo_root: Path) -> None:
    """The Cursor manifest's skills pointer is ``./skills/`` and that dir exists."""
    assert cursor_manifest.get("skills") == "./skills/"
    assert (repo_root / "skills").is_dir()


def test_skeleton_skill_front_matter(repo_root: Path) -> None:
    """The engine-bearing skill ships a SKILL.md with valid front-matter."""
    skill_md = repo_root / "skills" / "sr-search" / "SKILL.md"
    assert skill_md.is_file(), f"skeleton skill missing: {skill_md}"
    fm = _front_matter(skill_md)
    assert isinstance(fm.get("name"), str) and fm["name"]
    assert isinstance(fm.get("description"), str) and fm["description"]


@pytest.fixture(scope="module")
def release_manifest(repo_root: Path) -> dict:
    path = repo_root / ".release-please-manifest.json"
    assert path.is_file(), f"release-please manifest missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def release_config(repo_root: Path) -> dict:
    path = repo_root / "release-please-config.json"
    assert path.is_file(), f"release-please config missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_version_sources_in_lockstep(
    cursor_manifest: dict, claude_manifest: dict, release_manifest: dict
) -> None:
    """Both manifests and the release-please manifest carry the same version."""
    root_version = release_manifest["."]
    assert cursor_manifest["version"] == root_version
    assert claude_manifest["version"] == root_version


@pytest.fixture(scope="module")
def cursor_hooks(repo_root: Path) -> dict:
    path = repo_root / "hooks" / "cursor-hooks.json"
    assert path.is_file(), f"Cursor hook config missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def claude_hooks(repo_root: Path) -> dict:
    path = repo_root / "hooks" / "claude-hooks.json"
    assert path.is_file(), f"Claude hook config missing: {path}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_manifests_point_at_hook_configs(
    cursor_manifest: dict, claude_manifest: dict
) -> None:
    """Both manifests carry a hooks pointer to their harness's config."""
    assert cursor_manifest.get("hooks") == "./hooks/cursor-hooks.json"
    assert claude_manifest.get("hooks") == "./hooks/claude-hooks.json"


def _hook_command_entries(config: dict, harness: str) -> list[dict]:
    """Extract the sessionStart command-hook entries per harness schema.

    Cursor: ``{"version": 1, "hooks": {"sessionStart": [{"hooks": [entry]}]}}``.
    Claude: ``{"hooks": {"SessionStart": [{"hooks": [entry]}]}}``.
    """
    key = "sessionStart" if harness == "cursor" else "SessionStart"
    groups = config["hooks"][key]
    return [entry for group in groups for entry in group["hooks"]]


def _assert_combined_rectify_then_dashboard(
    cmd: str, *, plugin_root_token: str, owner: str
) -> None:
    """Shared shape for the single session-start command per harness.

    Rectify keeps the plugin-root bootstrap (chicken-egg heal). Dashboard
    launch is on-path ``stockroom dashboard`` after rectify, not folded into
    the ``uv run`` / ``PYTHONPATH`` bootstrap.
    """
    assert plugin_root_token in cmd
    assert "shim rectify" in cmd
    assert f"--owner {owner}" in cmd
    assert "stockroom dashboard" in cmd
    rectify_at = cmd.find("shim rectify")
    dashboard_at = cmd.find("stockroom dashboard")
    assert 0 <= rectify_at < dashboard_at, "rectify must precede dashboard launch"
    launch_half = cmd[dashboard_at:]
    assert "uv run" not in launch_half
    assert "PYTHONPATH=" not in launch_half
    assert "python -m stockroom" not in launch_half
    assert ">/dev/null 2>&1" in cmd, "hook output must be silenced"
    assert "|| true" in cmd, "hook must never fail session start"


def test_cursor_hook_schema_and_combined_command(cursor_hooks: dict) -> None:
    """Cursor sessionStart is one silenced timed-out command: rectify then
    on-path ``stockroom dashboard``."""
    assert cursor_hooks.get("version") == 1
    entries = _hook_command_entries(cursor_hooks, "cursor")
    assert len(entries) == 1, "exactly one combined sessionStart command"
    entry = entries[0]
    assert entry["type"] == "command"
    assert entry.get("timeout"), "hook must set a timeout"
    _assert_combined_rectify_then_dashboard(
        entry["command"],
        plugin_root_token="${CURSOR_PLUGIN_ROOT}",
        owner="cursor",
    )


def test_claude_hook_schema_and_combined_command(claude_hooks: dict) -> None:
    """Claude SessionStart is one silenced timed-out command: rectify then
    on-path ``stockroom dashboard``."""
    entries = _hook_command_entries(claude_hooks, "claude")
    assert len(entries) == 1, "exactly one combined SessionStart command"
    entry = entries[0]
    assert entry["type"] == "command"
    assert entry.get("timeout"), "hook must set a timeout"
    _assert_combined_rectify_then_dashboard(
        entry["command"],
        plugin_root_token="${CLAUDE_PLUGIN_ROOT}",
        owner="claude",
    )


def test_planning_docs_use_dashboard_port_6767(repo_root: Path) -> None:
    """Roadmap and tech-brief cite port 6767, not the superseded 3143."""
    for rel in ("planning/roadmap.md", "planning/tech-brief.md"):
        text = (repo_root / rel).read_text(encoding="utf-8")
        assert "6767" in text, f"{rel} must cite dashboard port 6767"
        assert "3143" not in text, f"{rel} must not cite superseded port 3143"


def test_release_config_syncs_both_manifests(release_config: dict) -> None:
    """release-please writes ``$.version`` into both plugin manifests."""
    extra_files = release_config["packages"]["."]["extra-files"]
    targets = {
        (ef.get("path"), ef.get("jsonpath"))
        for ef in extra_files
        if ef.get("type") == "json"
    }
    assert (".cursor-plugin/plugin.json", "$.version") in targets
    assert (".claude-plugin/plugin.json", "$.version") in targets
