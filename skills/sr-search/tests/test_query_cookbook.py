"""Structural discoverability and drift checks for the sr-query cookbook.

Pins the dual-audience contract:

- Recipe SSOT lives under ``skills/sr-query/references/cookbook/``.
- Agents find it via ``skills/sr-query/SKILL.md`` → cookbook index.
- Humans get the same files as Advanced → Cookbook pages via symlinks under
  ``docs/advanced/cookbook/``.
- Claude skill SQL must list every member of
  ``stockroom.dashboard.skill_usage._CLAUDE_BUILTIN_COMMANDS`` so the
  recipe denylist cannot silently omit a builtin the extractor excludes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stockroom.dashboard.skill_usage import _CLAUDE_BUILTIN_COMMANDS

COOKBOOK_SSOT = Path("skills/sr-query/references/cookbook")
COOKBOOK_DOCS = Path("docs/advanced/cookbook")

#: Recipe pages that must exist in the skill SSOT and as docs symlinks.
RECIPE_FILES = (
    "index.md",
    "token-usage.md",
    "tools.md",
    "skills-claude.md",
    "skills-cursor.md",
)


@pytest.mark.parametrize("name", RECIPE_FILES)
def test_cookbook_recipe_exists(repo_root: Path, name: str) -> None:
    """Each cookbook recipe file is present under the skill SSOT tree."""
    path = repo_root / COOKBOOK_SSOT / name
    assert path.is_file(), f"missing cookbook recipe: {path}"


@pytest.mark.parametrize("name", RECIPE_FILES)
def test_docs_cookbook_page_symlinks_to_ssot(repo_root: Path, name: str) -> None:
    """Each Advanced cookbook page is a symlink to the skill SSOT file."""
    link = repo_root / COOKBOOK_DOCS / name
    target = (repo_root / COOKBOOK_SSOT / name).resolve()
    assert link.is_symlink(), f"expected symlink: {link}"
    assert link.resolve() == target, (
        f"{link} should resolve to {target}, got {link.resolve()}"
    )


def test_sr_query_skill_links_cookbook_index(repo_root: Path) -> None:
    """``sr-query/SKILL.md`` links the cookbook index so agents can find it."""
    skill_md = repo_root / "skills" / "sr-query" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    assert "references/cookbook/index.md" in text, (
        "sr-query/SKILL.md must link references/cookbook/index.md"
    )


def test_docs_advanced_nav_lists_cookbook_section(repo_root: Path) -> None:
    """Advanced awesome-pages nav lists the Cookbook section directory."""
    pages = repo_root / "docs" / "advanced" / ".pages"
    text = pages.read_text(encoding="utf-8")
    assert "Cookbook" in text, "docs/advanced/.pages must list Cookbook"
    assert "cookbook" in text, "docs/advanced/.pages must reference cookbook section"
    assert "cookbook.md" not in text, (
        "docs/advanced/.pages must use the cookbook/ section, not cookbook.md"
    )


def test_docs_cookbook_section_nav_lists_recipes(repo_root: Path) -> None:
    """Cookbook section `.pages` lists the index and each recipe page."""
    pages = repo_root / COOKBOOK_DOCS / ".pages"
    assert pages.is_file(), f"missing section nav: {pages}"
    text = pages.read_text(encoding="utf-8")
    for name in RECIPE_FILES:
        assert name in text, f"docs/advanced/cookbook/.pages must list {name}"


def test_claude_builtin_denylist_synced_in_skills_claude_recipe(
    repo_root: Path,
) -> None:
    """Every extractor builtin appears in the Claude skills recipe denylist."""
    recipe = repo_root / COOKBOOK_SSOT / "skills-claude.md"
    assert recipe.is_file(), f"missing Claude skills recipe: {recipe}"
    text = recipe.read_text(encoding="utf-8")
    missing = sorted(name for name in _CLAUDE_BUILTIN_COMMANDS if name not in text)
    assert not missing, (
        "skills-claude.md must mention every "
        "stockroom.dashboard.skill_usage._CLAUDE_BUILTIN_COMMANDS member; "
        f"missing: {missing}"
    )
