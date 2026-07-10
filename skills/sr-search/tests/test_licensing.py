"""Layered REUSE/SPDX licensing is enforced, not merely asserted.

The whole committed tree must be REUSE-compliant (``reuse lint`` clean), and
the two-layer model must actually resolve: AGPL-3.0-or-later is the base on
all code, while prompt-shaped skill content (SKILL.md) is PPL-S — with
code-shaped paths inside ``skills/**`` re-asserted back to AGPL.
"""

import subprocess
from pathlib import Path

import pytest


def _run_reuse(repo_root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["reuse", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )


def _spdx_license_map(repo_root: Path) -> dict[str, set[str]]:
    """Map each repo-relative path to its REUSE-resolved SPDX licenses."""
    proc = _run_reuse(repo_root, "spdx")
    assert proc.returncode == 0, f"`reuse spdx` failed:\n{proc.stderr}"
    licenses: dict[str, set[str]] = {}
    current: str | None = None
    for line in proc.stdout.splitlines():
        if line.startswith("FileName:"):
            current = line.split(":", 1)[1].strip().removeprefix("./")
            licenses.setdefault(current, set())
        elif line.startswith("LicenseInfoInFile:") and current is not None:
            licenses[current].add(line.split(":", 1)[1].strip())
    return licenses


@pytest.fixture(scope="module")
def license_map(repo_root: Path) -> dict[str, set[str]]:
    return _spdx_license_map(repo_root)


def test_reuse_lint_passes(repo_root: Path) -> None:
    """The entire committed tree is REUSE-compliant."""
    proc = _run_reuse(repo_root, "lint")
    assert proc.returncode == 0, f"`reuse lint` failed:\n{proc.stdout}\n{proc.stderr}"


def test_code_inside_skill_resolves_agpl(license_map: dict[str, set[str]]) -> None:
    """A .py file inside skills/** is re-asserted to AGPL, not PPL-S."""
    target = "skills/sr-search/src/stockroom/__init__.py"
    assert target in license_map, f"{target} not in SPDX report"
    assert "AGPL-3.0-or-later" in license_map[target]
    assert "LicenseRef-PPL-S" not in license_map[target]


def test_prompt_skill_resolves_ppls(license_map: dict[str, set[str]]) -> None:
    """The skeleton SKILL.md (prompt-shaped content) resolves to PPL-S."""
    target = "skills/sr-search/SKILL.md"
    assert target in license_map, f"{target} not in SPDX report"
    assert "LicenseRef-PPL-S" in license_map[target]


def test_shell_inside_skill_resolves_agpl(license_map: dict[str, set[str]]) -> None:
    """The shim template (.sh inside skills/**) is software: re-asserted to
    AGPL, not PPL-S."""
    target = "skills/sr-search/src/stockroom/shim_template.sh"
    assert target in license_map, f"{target} not in SPDX report"
    assert "AGPL-3.0-or-later" in license_map[target]
    assert "LicenseRef-PPL-S" not in license_map[target]


def test_authored_dashboard_assets_resolve_agpl(
    license_map: dict[str, set[str]],
) -> None:
    """Authored dashboard HTML/modules and JavaScript tests are AGPL software."""
    targets = [
        "skills/sr-search/src/stockroom/dashboard/static/index.html",
        "skills/sr-search/src/stockroom/dashboard/static/dashboard.mjs",
        "skills/sr-search/src/stockroom/dashboard/static/dashboard-core.mjs",
        "skills/sr-search/src/stockroom/dashboard/static/dashboard-data.mjs",
        "skills/sr-search/tests-js/dashboard-core.test.mjs",
        "skills/sr-search/tests-js/dashboard-data.test.mjs",
    ]
    for target in targets:
        assert target in license_map, f"{target} not in SPDX report"
        assert license_map[target] == {"AGPL-3.0-or-later"}


def test_vendored_chartjs_resolves_only_mit(
    license_map: dict[str, set[str]],
) -> None:
    """The exact upstream Chart.js artifact retains its MIT identity."""
    target = "skills/sr-search/src/stockroom/dashboard/static/chart-4.5.1.umd.min.js"
    assert target in license_map, f"{target} not in SPDX report"
    assert license_map[target] == {"MIT"}
