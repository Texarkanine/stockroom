"""F7: writer surfaces document/produce hashed torch freeze (not index-only)."""

from __future__ import annotations

from pathlib import Path


def test_makefile_torch_freezes_after_install(repo_root: Path) -> None:
    """``make torch`` installs then freezes with TORCH_INDEX."""
    text = (repo_root / "Makefile").read_text(encoding="utf-8")
    assert "torch freeze" in text
    assert "TORCH_INDEX" in text
    assert "torch record" not in text


def test_sr_initialize_freezes_after_smoke(repo_root: Path) -> None:
    """sr-initialize: install → smoke → freeze (freeze after successful smoke)."""
    text = (repo_root / "skills" / "sr-initialize" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "torch freeze" in text
    assert "torch record" not in text
    smoke_at = text.index("doctor smoke")
    freeze_at = text.index("torch freeze")
    assert smoke_at < freeze_at, "freeze must be documented after smoke"


def test_docs_torch_covers_freeze_contract(repo_root: Path) -> None:
    """docs/torch.md covers freeze location, heal, and failure remedy."""
    path = repo_root / "docs" / "torch.md"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "torch-requirements.txt" in text
    assert "--require-hashes" in text
    assert "sr-initialize" in text
    assert "torch freeze" in text
