"""Coverage-collection plumbing for Codecov dual-root uploads.

Subprocesses the root Make targets that CI will use, so local Make, CI, and
these tests share one SSOT for how engine and dashboard-js lcov reports are
produced.

Output dirs are overridden per test (``COVERAGE_ENGINE_DIR`` /
``COVERAGE_JS_DIR``) so xdist workers do not race on the default
``coverage/`` / ``coverage-js/`` paths under the engine tree.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

_ENGINE = Path("skills/sr-search")
_DEFAULT_JS_COV = _ENGINE / "coverage-js"

# Narrow engine run: one cheap test that imports stockroom package code.
_NARROW_ENGINE_ARGS = "-n0 tests/test_dashboard_cli.py::test_default_port_is_58008"


def _sf_paths(lcov_text: str) -> list[str]:
    return [
        line.removeprefix("SF:").strip()
        for line in lcov_text.splitlines()
        if line.startswith("SF:")
    ]


def _run_make(repo_root: Path, *targets: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", *targets],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_coverage_engine_emits_lcov_with_stockroom_sf_paths(
    repo_root: Path, tmp_path: Path
) -> None:
    """``make coverage-engine`` writes lcov whose SF: paths cover ``src/stockroom/``."""
    out_dir = tmp_path / "coverage"
    lcov_path = out_dir / "lcov.info"

    result = _run_make(
        repo_root,
        f"COVERAGE_ENGINE_DIR={out_dir}",
        f"COVERAGE_PYTEST_ARGS={_NARROW_ENGINE_ARGS}",
        "coverage-engine",
    )
    assert result.returncode == 0, (
        f"make coverage-engine failed:\n{result.stdout}\n{result.stderr}"
    )
    assert lcov_path.is_file(), f"missing {lcov_path}"
    text = lcov_path.read_text(encoding="utf-8")
    sf = _sf_paths(text)
    assert sf, "lcov has no SF: entries"
    assert any(
        "src/stockroom/" in path or path.endswith("stockroom/") or "/stockroom/" in path
        for path in sf
    ), f"expected stockroom source SF paths, got: {sf[:20]}"
    # Tests are not the primary covered package.
    assert not all("/tests/" in path or path.startswith("tests/") for path in sf), (
        "lcov SF paths look like tests-only coverage"
    )


def test_coverage_dashboard_js_emits_lcov_with_static_sf_paths(
    repo_root: Path, tmp_path: Path
) -> None:
    """``make coverage-dashboard-js`` writes lcov whose SF: paths cover static ESM."""
    out_dir = tmp_path / "coverage-js"
    lcov_path = out_dir / "lcov.info"

    result = _run_make(
        repo_root,
        f"COVERAGE_JS_DIR={out_dir}",
        "coverage-dashboard-js",
    )
    assert result.returncode == 0, (
        f"make coverage-dashboard-js failed:\n{result.stdout}\n{result.stderr}"
    )
    assert lcov_path.is_file(), f"missing {lcov_path}"
    sf = _sf_paths(lcov_path.read_text(encoding="utf-8"))
    assert sf, "lcov has no SF: entries"
    assert any("src/stockroom/dashboard/static/" in path for path in sf), (
        f"expected static SF paths, got: {sf[:20]}"
    )


def test_coverage_dashboard_js_excludes_test_files_from_sf_paths(
    repo_root: Path, tmp_path: Path
) -> None:
    """Dashboard JS lcov does not treat ``tests-js/*.test.mjs`` as covered surface."""
    out_dir = tmp_path / "coverage-js"
    lcov_path = out_dir / "lcov.info"

    result = _run_make(
        repo_root,
        f"COVERAGE_JS_DIR={out_dir}",
        "coverage-dashboard-js",
    )
    assert result.returncode == 0, (
        f"make coverage-dashboard-js failed:\n{result.stdout}\n{result.stderr}"
    )
    sf = _sf_paths(lcov_path.read_text(encoding="utf-8"))
    assert any("src/stockroom/dashboard/static/" in path for path in sf), (
        f"expected static modules in SF, got: {sf[:20]}"
    )
    test_sf = [p for p in sf if "tests-js/" in p or p.endswith(".test.mjs")]
    assert test_sf == [], f"test files should be excluded from SF: {test_sf}"


def test_make_test_dashboard_js_has_no_required_lcov_side_effect(
    repo_root: Path,
) -> None:
    """Default ``make test-dashboard-js`` still passes without writing default lcov."""
    js_cov_dir = repo_root / _DEFAULT_JS_COV
    if js_cov_dir.is_dir():
        shutil.rmtree(js_cov_dir)

    result = _run_make(repo_root, "test-dashboard-js")
    assert result.returncode == 0, (
        f"make test-dashboard-js failed:\n{result.stdout}\n{result.stderr}"
    )
    assert not (js_cov_dir / "lcov.info").exists(), (
        "make test-dashboard-js must not require writing coverage-js/lcov.info"
    )
