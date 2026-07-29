"""Structural contracts for the PR template and conventional-commit title CI.

Pins headings, CONTRIBUTING link, absence of checklists, and the title-lint
workflow — not instructional prose (#103: don't test prose).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REQUIRED_HEADINGS = (
    "## Goal",
    "## What's here",
    "## How I know it works",
    "## What changes for a user",
    "## Effect on an existing warehouse",
)

# CONTRIBUTING release gate: feat/fix release; chore must-not; docs discouraged.
REQUIRED_TITLE_TYPES = frozenset({"feat", "fix", "chore"})
DISALLOWED_TITLE_TYPES = frozenset({"docs"})


@pytest.fixture(scope="module")
def pr_template(repo_root: Path) -> str:
    path = repo_root / ".github" / "pull_request_template.md"
    assert path.is_file(), f"PR template missing: {path}"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def pr_title_workflow(repo_root: Path) -> dict:
    path = repo_root / ".github" / "workflows" / "pr-title.yaml"
    assert path.is_file(), f"PR title workflow missing: {path}"
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(loaded, dict), "pr-title.yaml must parse as a mapping"
    return loaded


def test_pr_template_has_unautomatable_only_headings(pr_template: str) -> None:
    for heading in REQUIRED_HEADINGS:
        assert heading in pr_template, f"missing heading: {heading}"


def test_pr_template_links_contributing(pr_template: str) -> None:
    assert "CONTRIBUTING.md" in pr_template
    assert "](" in pr_template and "CONTRIBUTING" in pr_template


def test_pr_template_has_no_checklist(pr_template: str) -> None:
    assert "- [ ]" not in pr_template
    assert "- [x]" not in pr_template


def test_pr_title_workflow_uses_semantic_pull_request(pr_title_workflow: dict) -> None:
    jobs = pr_title_workflow.get("jobs") or {}
    uses: list[str] = []
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if isinstance(step, dict) and "uses" in step:
                uses.append(str(step["uses"]))
    assert any("amannn/action-semantic-pull-request" in u for u in uses), (
        f"expected semantic-pull-request action; found uses={uses}"
    )


def test_pr_title_workflow_types_match_contributing(
    repo_root: Path, pr_title_workflow: dict
) -> None:
    path = repo_root / ".github" / "workflows" / "pr-title.yaml"
    raw = path.read_text(encoding="utf-8")
    # Prefer structured parse of the action's `types` input when present.
    types_block = ""
    jobs = pr_title_workflow.get("jobs") or {}
    for job in jobs.values():
        if not isinstance(job, dict):
            continue
        for step in job.get("steps") or []:
            if not isinstance(step, dict):
                continue
            if "amannn/action-semantic-pull-request" not in str(step.get("uses", "")):
                continue
            with_ = step.get("with") or {}
            types_block = str(with_.get("types") or "")
    assert types_block or "types:" in raw
    declared = {
        line.strip()
        for line in types_block.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    if not declared:
        # Fallback: scan the YAML text under a `types: |` block.
        in_types = False
        for line in raw.splitlines():
            if line.strip().startswith("types:"):
                in_types = True
                continue
            if in_types:
                if line and not line[0].isspace() and not line.startswith(" "):
                    break
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    declared.add(stripped)
    assert REQUIRED_TITLE_TYPES <= declared, (
        f"missing required types; declared={sorted(declared)}"
    )
    assert not (DISALLOWED_TITLE_TYPES & declared), (
        f"disallowed types present; declared={sorted(declared)}"
    )
