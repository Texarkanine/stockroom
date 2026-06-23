"""Cross-artifact packaging contract: dual manifests, skeleton skill, versions.

Driven from the engine's pytest but asserts against repo-root artifacts via
the ``repo_root`` fixture. Proves the committed layout is a valid install
layout for both Cursor and Claude Code, that the engine-bearing skill is
honestly present from Phase 0, and that all version sources agree.
"""

from __future__ import annotations

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


def test_manifest_versions_match(
    cursor_manifest: dict, claude_manifest: dict
) -> None:
    """The two manifest versions are in lockstep with each other."""
    assert cursor_manifest["version"] == claude_manifest["version"]


def test_cursor_skills_pointer_resolves(
    cursor_manifest: dict, repo_root: Path
) -> None:
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
