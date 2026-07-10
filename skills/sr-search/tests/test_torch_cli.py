"""CLI tests for ``stockroom torch record``."""

from __future__ import annotations

from pathlib import Path

import pytest

from stockroom import torch_cli, torch_source


@pytest.fixture
def stockroom_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("STOCKROOM_HOME", str(home))
    return home


def test_record_writes_index(stockroom_home: Path) -> None:
    url = "https://download.pytorch.org/whl/cu126"
    code = torch_cli.main(["record", "--index", url])
    assert code == 0
    assert torch_source.read_index() == url


def test_record_rejects_bad_url(stockroom_home: Path) -> None:
    code = torch_cli.main(["record", "--index", "not-a-url"])
    assert code == 2
    assert torch_source.read_index() is None
