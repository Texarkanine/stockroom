"""CLI tests for ``stockroom torch freeze``."""

from __future__ import annotations

from pathlib import Path

import pytest

from stockroom import torch_cli, torch_source
from stockroom.torch_source import TorchFreezeReport


@pytest.fixture
def stockroom_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("STOCKROOM_HOME", str(home))
    return home


@pytest.fixture
def app_dir(tmp_path: Path) -> Path:
    d = tmp_path / "engine"
    d.mkdir()
    (d / "pyproject.toml").write_text("[project]\nname='stockroom'\n")
    py = d / ".venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.write_text("#!/bin/sh\n")
    py.chmod(0o755)
    return d


def test_freeze_invokes_freeze_torch(
    app_dir: Path, stockroom_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """F6: ``torch freeze --app-dir --index`` invokes freeze_torch (stubbed)."""
    url = "https://download.pytorch.org/whl/cpu"
    seen: dict[str, object] = {}

    def fake_freeze(app_dir_arg, index_url, **kwargs):  # noqa: ANN001
        seen["app_dir"] = Path(app_dir_arg)
        seen["index"] = index_url
        seen["runner"] = kwargs.get("runner")
        dest = stockroom_home / "torch-requirements.txt"
        dest.write_text(
            f"--index-url {url}\ntorch==2.7.1+cpu \\\n    --hash=sha256:deadbeef\n",
            encoding="utf-8",
        )
        return TorchFreezeReport(
            action="written", reason="2.7.1+cpu", requirements_path=dest
        )

    monkeypatch.setattr(torch_cli, "freeze_torch", fake_freeze)
    code = torch_cli.main(["freeze", "--app-dir", str(app_dir), "--index", url])
    assert code == 0
    assert Path(seen["app_dir"]) == Path(app_dir)
    assert seen["index"] == url


def test_freeze_defaults_app_dir_to_engine(
    stockroom_home: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Preflight: omitted --app-dir uses default_app_dir()."""
    engine = tmp_path / "default-engine"
    engine.mkdir()
    url = "https://download.pytorch.org/whl/cpu"
    seen: list[Path] = []

    def fake_freeze(app_dir_arg, index_url, **kwargs):  # noqa: ANN001
        seen.append(Path(app_dir_arg))
        return TorchFreezeReport(action="written", reason="ok")

    monkeypatch.setattr(torch_cli, "freeze_torch", fake_freeze)
    monkeypatch.setattr(torch_cli, "default_app_dir", lambda: engine)
    code = torch_cli.main(["freeze", "--index", url])
    assert code == 0
    assert seen == [engine]


def test_freeze_propagates_soft_failure(
    app_dir: Path, stockroom_home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CLI exits non-zero when freeze_torch soft-fails."""

    def fake_freeze(app_dir_arg, index_url, **kwargs):  # noqa: ANN001
        return TorchFreezeReport(action="failed", reason="no torch")

    monkeypatch.setattr(torch_cli, "freeze_torch", fake_freeze)
    code = torch_cli.main(
        [
            "freeze",
            "--app-dir",
            str(app_dir),
            "--index",
            "https://download.pytorch.org/whl/cpu",
        ]
    )
    assert code == 1


def test_freeze_rejects_bad_url(app_dir: Path, stockroom_home: Path) -> None:
    code = torch_cli.main(["freeze", "--app-dir", str(app_dir), "--index", "not-a-url"])
    assert code == 2
    assert torch_source.read_freeze_path() is None


def test_record_action_removed(stockroom_home: Path) -> None:
    """``record`` is no longer a valid action (prefer freeze)."""
    with pytest.raises(SystemExit):
        torch_cli.main(["record", "--index", "https://download.pytorch.org/whl/cpu"])
    assert torch_source.read_index() is None
    assert torch_source.read_freeze_path() is None
