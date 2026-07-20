"""Cookbook dual-audience wiring and Claude denylist drift checks.

- Recipe bodies under ``docs/advanced/cookbook/`` must symlink to the skill SSOT.
- ``skills-claude.md`` must list every ``_CLAUDE_BUILTIN_COMMANDS`` member.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from stockroom.dashboard.skill_usage import _CLAUDE_BUILTIN_COMMANDS

COOKBOOK_SSOT = Path("skills/sr-query/references/cookbook")
COOKBOOK_DOCS = Path("docs/advanced/cookbook")

SYMLINKED_RECIPES = (
    "token-usage.md",
    "tools.md",
    "skills-claude.md",
    "skills-cursor.md",
)


@pytest.mark.parametrize("name", SYMLINKED_RECIPES)
def test_docs_cookbook_page_symlinks_to_ssot(repo_root: Path, name: str) -> None:
    """Each Advanced cookbook recipe page is a symlink to the skill SSOT file."""
    link = repo_root / COOKBOOK_DOCS / name
    target = (repo_root / COOKBOOK_SSOT / name).resolve()
    assert link.is_symlink(), f"expected symlink: {link}"
    assert link.resolve() == target, (
        f"{link} should resolve to {target}, got {link.resolve()}"
    )


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
