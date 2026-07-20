"""Structural discoverability and drift checks for the sr-query cookbook.

Pins the dual-audience contract from the query-cookbook plan:

- Recipe SSOT lives under ``skills/sr-query/references/cookbook/``.
- Agents find it via ``skills/sr-query/SKILL.md`` → cookbook index.
- Humans get the same bodies via ``pymdownx.snippets`` includes in
  ``docs/advanced/cookbook.md``, listed in Advanced nav.
- Claude skill SQL must list every member of
  ``stockroom.dashboard.skill_usage._CLAUDE_BUILTIN_COMMANDS`` so the
  recipe denylist cannot silently omit a builtin the extractor excludes.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stockroom.dashboard.skill_usage import _CLAUDE_BUILTIN_COMMANDS

COOKBOOK_DIR = Path("skills/sr-query/references/cookbook")

#: Recipe bodies that must exist on disk for agents (and for snippet includes).
RECIPE_FILES = (
    "index.md",
    "token-usage.md",
    "tools.md",
    "skills-claude.md",
    "skills-cursor.md",
)

#: Recipe bodies (not the index) that docs must snippet-include.
SNIPPET_RECIPES = (
    "token-usage.md",
    "tools.md",
    "skills-claude.md",
    "skills-cursor.md",
)


@pytest.mark.parametrize("name", RECIPE_FILES)
def test_cookbook_recipe_exists(repo_root: Path, name: str) -> None:
    """Each cookbook recipe file is present under the skill SSOT tree."""
    path = repo_root / COOKBOOK_DIR / name
    assert path.is_file(), f"missing cookbook recipe: {path}"


def test_sr_query_skill_links_cookbook_index(repo_root: Path) -> None:
    """``sr-query/SKILL.md`` links the cookbook index so agents can find it."""
    skill_md = repo_root / "skills" / "sr-query" / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    assert "references/cookbook/index.md" in text, (
        "sr-query/SKILL.md must link references/cookbook/index.md"
    )


def test_docs_advanced_cookbook_snippets_each_recipe(repo_root: Path) -> None:
    """Advanced cookbook wrapper snippet-includes every recipe body."""
    cookbook_md = repo_root / "docs" / "advanced" / "cookbook.md"
    assert cookbook_md.is_file(), f"missing docs wrapper: {cookbook_md}"
    text = cookbook_md.read_text(encoding="utf-8")
    for name in SNIPPET_RECIPES:
        marker = f'--8<-- "{COOKBOOK_DIR.as_posix()}/{name}"'
        assert marker in text, (
            f"docs/advanced/cookbook.md must include snippet marker {marker!r}"
        )


def test_docs_advanced_nav_lists_cookbook(repo_root: Path) -> None:
    """Advanced awesome-pages nav lists the Cookbook entry."""
    pages = repo_root / "docs" / "advanced" / ".pages"
    text = pages.read_text(encoding="utf-8")
    assert "Cookbook" in text, "docs/advanced/.pages must list Cookbook"
    assert "cookbook.md" in text, "docs/advanced/.pages must reference cookbook.md"


def test_claude_builtin_denylist_synced_in_skills_claude_recipe(
    repo_root: Path,
) -> None:
    """Every extractor builtin appears in the Claude skills recipe denylist."""
    recipe = repo_root / COOKBOOK_DIR / "skills-claude.md"
    assert recipe.is_file(), f"missing Claude skills recipe: {recipe}"
    text = recipe.read_text(encoding="utf-8")
    missing = sorted(name for name in _CLAUDE_BUILTIN_COMMANDS if name not in text)
    assert not missing, (
        "skills-claude.md must mention every "
        "stockroom.dashboard.skill_usage._CLAUDE_BUILTIN_COMMANDS member; "
        f"missing: {missing}"
    )
