"""Unit tests for :mod:`stockroom.shim`: render + install/rectify policy.

The shim is baked-only and succeed-or-refuse (no runtime resolution — an
operator hard constraint), so *all* policy lives in this tested Python layer:
what gets rendered, who may write the destination (ownership), when a takeover
of a foreign shim is permitted (dead incumbent + explicit flag only), and when
the hook-driven ``rectify`` may act (owner match + content drift only, never
creating). Everything writes to tmp destinations via explicit ``dest`` — the
real ``~/.local/bin`` is never touched.
"""

import os
from pathlib import Path

import pytest

import stockroom
from stockroom import shim


@pytest.fixture
def engine_dir(tmp_path: Path) -> Path:
    """An 'alive' fixture engine dir: pyproject.toml + duckdb-ready stub venv."""
    d = tmp_path / "engine-alive"
    (d / "src").mkdir(parents=True)
    (d / "pyproject.toml").write_text("[project]\nname = 'stockroom'\n")
    venv_bin = d / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    py = venv_bin / "python"
    py.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    py.chmod(0o755)
    return d


@pytest.fixture
def other_engine_dir(tmp_path: Path) -> Path:
    """A second alive engine dir, for takeover/rectify-move scenarios."""
    d = tmp_path / "engine-alive-2"
    (d / "src").mkdir(parents=True)
    (d / "pyproject.toml").write_text("[project]\nname = 'stockroom'\n")
    venv_bin = d / ".venv" / "bin"
    venv_bin.mkdir(parents=True)
    py = venv_bin / "python"
    py.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    py.chmod(0o755)
    return d


@pytest.fixture
def dead_dir(tmp_path: Path) -> Path:
    """A 'dead' baked dir: exists but has no pyproject.toml."""
    d = tmp_path / "engine-dead"
    d.mkdir()
    return d


@pytest.fixture
def dest(tmp_path: Path) -> Path:
    """A tmp shim destination (parent dir not yet created)."""
    return tmp_path / "bin" / "stockroom"


@pytest.fixture
def no_dest_on_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Point PATH away from every test dest so installs skip the verify."""
    elsewhere = tmp_path / "not-the-dest"
    elsewhere.mkdir(exist_ok=True)
    monkeypatch.setenv("PATH", str(elsewhere))


# ---------------------------------------------------------------------------
# render
# ---------------------------------------------------------------------------


class TestRender:
    def test_bakes_app_dir_and_owner_markers(self, engine_dir: Path) -> None:
        """The rendered script carries the baked APP_DIR and the
        machine-readable owner header marker."""
        text = shim.render(engine_dir, "cursor")
        assert str(engine_dir) in text
        assert "# STOCKROOM_OWNER=cursor" in text
        assert f"# STOCKROOM_APP_DIR={engine_dir}" in text

    def test_carries_torch_safe_exec_contract(self, engine_dir: Path) -> None:
        """The exec line preserves the torch-safe run contract verbatim:
        --no-sync, --no-config, PYTHONPATH to src, exec into uv run. Also
        refuses when the engine env cannot import duckdb."""
        text = shim.render(engine_dir, "cursor")
        assert "--no-sync" in text
        assert "--no-config" in text
        assert 'PYTHONPATH="$APP_DIR/src"' in text
        assert "exec uv run" in text
        assert "import duckdb" in text
        assert "engine env" in text

    def test_stamps_generator_version(self, engine_dir: Path) -> None:
        """The generator version is stamped so drift is diagnosable."""
        text = shim.render(engine_dir, "cursor")
        assert stockroom.__version__ in text

    def test_remedy_matches_owner(self, engine_dir: Path) -> None:
        """The staleness remedy names the owner-appropriate healing action:
        sr-initialize for harness owners, make shim for dev."""
        assert "sr-initialize" in shim.render(engine_dir, "cursor")
        assert "make shim" in shim.render(engine_dir, "dev")


# ---------------------------------------------------------------------------
# install policy
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("no_dest_on_path")
class TestInstall:
    def test_absent_dest_writes_executable_rendered_shim(
        self, dest: Path, engine_dir: Path
    ) -> None:
        """Install to an absent dest writes the rendered content, 0o755."""
        report = shim.install(dest, engine_dir, "cursor")
        assert report.action == "installed"
        assert dest.is_file()
        assert dest.stat().st_mode & 0o777 == 0o755
        assert dest.read_text() == shim.render(engine_dir, "cursor")

    def test_reinstall_same_owner_replaces_cleanly(
        self, dest: Path, engine_dir: Path, other_engine_dir: Path
    ) -> None:
        """Re-install by the same owner is idempotent: content replaced,
        no temp debris left beside the dest."""
        shim.install(dest, engine_dir, "cursor")
        report = shim.install(dest, other_engine_dir, "cursor")
        assert report.action == "installed"
        assert dest.read_text() == shim.render(other_engine_dir, "cursor")
        assert [p.name for p in dest.parent.iterdir()] == [dest.name]

    def test_foreign_owner_alive_dir_refuses_untouched(
        self, dest: Path, engine_dir: Path, other_engine_dir: Path
    ) -> None:
        """A different owner may not replace a shim whose baked dir is alive;
        the refusal names the incumbent owner and the dest is untouched."""
        shim.install(dest, engine_dir, "cursor")
        before = dest.read_text()
        report = shim.install(dest, other_engine_dir, "claude")
        assert report.action == "refused"
        assert "cursor" in report.reason
        assert dest.read_text() == before

    def test_foreign_owner_alive_dir_refuses_even_with_takeover(
        self, dest: Path, engine_dir: Path, other_engine_dir: Path
    ) -> None:
        """--takeover never clobbers a *working* foreign shim."""
        shim.install(dest, engine_dir, "cursor")
        report = shim.install(dest, other_engine_dir, "claude", takeover=True)
        assert report.action == "refused"

    def test_foreign_owner_dead_dir_requires_explicit_takeover(
        self, dest: Path, dead_dir: Path, engine_dir: Path
    ) -> None:
        """A dead incumbent is still refused by default; takeover succeeds
        only with the explicit flag."""
        shim.install(dest, dead_dir, "cursor")
        refused = shim.install(dest, engine_dir, "claude")
        assert refused.action == "refused"

        taken = shim.install(dest, engine_dir, "claude", takeover=True)
        assert taken.action == "installed"
        assert dest.read_text() == shim.render(engine_dir, "claude")

    def test_corrupt_header_treated_as_foreign(
        self, dest: Path, engine_dir: Path
    ) -> None:
        """An existing dest with an unreadable header is foreign: refuse
        without --takeover, never crash."""
        dest.parent.mkdir(parents=True)
        dest.write_text("#!/bin/sh\necho not a stockroom shim\n")
        report = shim.install(dest, engine_dir, "cursor")
        assert report.action == "refused"

    def test_default_app_dir_is_running_engine_dir(self) -> None:
        """The default app dir resolves to the engine dir that contains the
        running stockroom package (run-in-place layout)."""
        app_dir = shim.default_app_dir()
        assert (app_dir / "pyproject.toml").is_file()
        assert (app_dir / "src" / "stockroom").is_dir()


class TestInstallPathAndVerify:
    def test_dest_off_path_reports_and_skips_verify(
        self,
        dest: Path,
        engine_dir: Path,
        no_dest_on_path: None,
    ) -> None:
        """When the dest dir is not on PATH the report says so and the
        --version verify is skipped with a reason."""
        report = shim.install(dest, engine_dir, "cursor")
        assert report.action == "installed"
        assert report.path_ok is False
        assert report.verify_attempted is False
        assert "PATH" in report.verify_detail

    def test_dest_on_path_attempts_version_verify(
        self,
        dest: Path,
        engine_dir: Path,
        stub_uv: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When the dest dir is on PATH the install verifies via
        ``stockroom --version`` through PATH (stub uv makes it succeed)."""
        monkeypatch.setenv("PATH", os.pathsep.join([str(dest.parent), str(stub_uv)]))
        report = shim.install(dest, engine_dir, "cursor")
        assert report.action == "installed"
        assert report.path_ok is True
        assert report.verify_attempted is True
        assert report.verify_ok is True


# ---------------------------------------------------------------------------
# rectify policy
# ---------------------------------------------------------------------------


@pytest.mark.usefixtures("no_dest_on_path")
class TestRectify:
    @pytest.fixture(autouse=True)
    def _stub_ensure_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Path-policy tests must not invoke real uv sync against fixture dirs."""
        from stockroom.engine_env import EnsureReport

        def fake_ensure(app_dir, **kwargs):  # noqa: ANN001
            return EnsureReport(action="noop", app_dir=Path(app_dir))

        monkeypatch.setattr(shim, "ensure_engine_env", fake_ensure)

    def test_owner_match_content_drift_rewrites(
        self, dest: Path, engine_dir: Path, other_engine_dir: Path
    ) -> None:
        """A moved root (or template change) under the same owner re-bakes."""
        shim.install(dest, engine_dir, "cursor")
        report = shim.rectify(dest, other_engine_dir, "cursor")
        assert report.action == "rectified"
        assert dest.read_text() == shim.render(other_engine_dir, "cursor")

    def test_owner_match_identical_content_noop(
        self, dest: Path, engine_dir: Path
    ) -> None:
        """Steady state: rendered content already matches → no write."""
        shim.install(dest, engine_dir, "cursor")
        mtime = dest.stat().st_mtime_ns
        report = shim.rectify(dest, engine_dir, "cursor")
        assert report.action == "noop"
        assert dest.stat().st_mtime_ns == mtime

    def test_owner_mismatch_never_touches_foreign_shim(
        self, dest: Path, engine_dir: Path, other_engine_dir: Path
    ) -> None:
        """rectify by a non-owner is a silent no-op even when content differs."""
        shim.install(dest, engine_dir, "cursor")
        before = dest.read_text()
        report = shim.rectify(dest, other_engine_dir, "claude")
        assert report.action == "noop"
        assert dest.read_text() == before

    def test_absent_dest_never_creates(self, dest: Path, engine_dir: Path) -> None:
        """rectify never creates a missing shim — install is the only gate."""
        report = shim.rectify(dest, engine_dir, "cursor")
        assert report.action == "noop"
        assert not dest.exists()

    def test_always_ensures_engine_env(
        self,
        dest: Path,
        engine_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """B4: rectify always runs ensure_engine_env for app_dir first,
        including when the dest is absent (path noop)."""
        from stockroom.engine_env import EnsureReport

        calls: list[Path] = []

        def fake_ensure(app_dir, **kwargs):  # noqa: ANN001
            calls.append(Path(app_dir))
            return EnsureReport(action="synced", app_dir=Path(app_dir))

        monkeypatch.setattr(shim, "ensure_engine_env", fake_ensure)
        report = shim.rectify(dest, engine_dir, "cursor")
        assert report.action == "noop"
        assert len(calls) == 1
        assert Path(os.path.abspath(calls[0])) == Path(os.path.abspath(engine_dir))
