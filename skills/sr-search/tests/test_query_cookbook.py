"""Cookbook dual-audience wiring and Claude denylist drift checks.

- Every skill cookbook recipe body (not the agent index) must appear under
  ``docs/advanced/cookbook/`` as a symlink to that SSOT file.
- ``skills-claude.md`` must list every ``_CLAUDE_BUILTIN_COMMANDS`` member.
"""

from __future__ import annotations

from pathlib import Path

from stockroom.dashboard.skill_usage import _CLAUDE_BUILTIN_COMMANDS

COOKBOOK_SSOT = Path("skills/sr-query/references/cookbook")
COOKBOOK_DOCS = Path("docs/advanced/cookbook")


def _ssot_recipe_names(repo_root: Path) -> list[str]:
    """Return skill cookbook recipe filenames, excluding the agent index."""
    ssot = repo_root / COOKBOOK_SSOT
    return sorted(
        path.name
        for path in ssot.glob("*.md")
        if path.is_file() and path.name != "index.md"
    )


def test_docs_cookbook_pages_symlink_to_ssot_recipes(repo_root: Path) -> None:
    """Each skill recipe body is exposed to docs via a symlink to the SSOT."""
    recipes = _ssot_recipe_names(repo_root)
    assert recipes, f"expected recipe bodies under {COOKBOOK_SSOT}"
    for name in recipes:
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
