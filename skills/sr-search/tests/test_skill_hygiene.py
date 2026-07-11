"""Wrapper-skill hygiene: zero invocation plumbing in the wrapper skills.

The Phase-3 m5 invariant, regression-pinned: `sr-query`, `sr-semantic`,
`sr-search`, and `sr-dashboard` invoke the engine only as
``stockroom <subcommand>`` — the shim owns the whole invocation contract, so
no wrapper SKILL.md may carry any token of the pre-shim incantation
(engine-dir resolution, ``PYTHONPATH``, uv flags, or raw ``python -m`` module
invocations). This is the m6 "grep-verifiable no-invocation-token check"
promoted into a permanent test.

``sr-initialize`` is deliberately NOT covered: it owns environment setup and
carries the one sanctioned pre-shim invocation (the shim does not exist yet
on the machines it targets).
"""

from pathlib import Path

import pytest

#: The wrapper skills bound by the "no invocation plumbing" contract.
WRAPPER_SKILLS = ("sr-query", "sr-semantic", "sr-search", "sr-dashboard")

#: Tokens of the pre-shim incantation, none of which may appear in a wrapper
#: SKILL.md. ``python -m stockroom`` also catches dotted module forms
#: (``python -m stockroom.query`` etc.) by prefix.
FORBIDDEN_TOKENS = (
    "APP_DIR",
    "PYTHONPATH",
    "uv run",
    "--no-sync",
    "--no-config",
    "CURSOR_PLUGIN_ROOT",
    "CLAUDE_PLUGIN_ROOT",
    "find -L",
    "python -m stockroom",
)


@pytest.mark.parametrize("skill", WRAPPER_SKILLS)
def test_wrapper_skill_has_no_invocation_plumbing(repo_root: Path, skill: str) -> None:
    """Each wrapper SKILL.md is free of every pre-shim invocation token."""
    skill_md = repo_root / "skills" / skill / "SKILL.md"
    assert skill_md.is_file(), f"wrapper skill missing: {skill_md}"
    text = skill_md.read_text(encoding="utf-8")

    offenses = [token for token in FORBIDDEN_TOKENS if token in text]
    assert not offenses, (
        f"{skill}/SKILL.md carries invocation plumbing {offenses} — wrapper "
        "skills invoke the engine only as `stockroom <subcommand>` (the shim "
        "owns the contract; on a missing command the next action is sr-initialize)"
    )


@pytest.mark.parametrize("skill", ("sr-query", "sr-semantic"))
def test_read_skills_document_exact_text_raw_detail(
    repo_root: Path, skill: str
) -> None:
    """Read-surface skills name ``--detail raw`` as the exact-whitespace path."""
    skill_md = repo_root / "skills" / skill / "SKILL.md"
    text = skill_md.read_text(encoding="utf-8")
    assert "--detail raw" in text
    assert "--format json" in text
