"""Tests for the project-dir ``encode`` transform and the ``cwd`` resolver.

``stockroom.ingest.paths`` turns the un-invertible project-dir slug problem into
a *verifiable lookup*: we cannot invert the harness's lossy ``encode`` (path
separators and other non-alphanumerics all collapse to ``-``), but we can
compute it forward. So a candidate real path is accepted as ``cwd`` only when
``encode_for(harness, candidate) == slug`` — verification, never guessing, which
makes a fabricated path structurally impossible (its failure mode is a clean
``None``). The transform was locked empirically against the operator's real
history (see ``planning/spikes/cwd-recovery/``): the real slug alphabet is
exactly ``[A-Za-z0-9-]``.
"""

from stockroom.ingest import paths


def test_encode_collapses_every_nonalnum_to_dash() -> None:
    """Every non-alphanumeric char (``/``, ``.``, ``_``, ``-``) becomes ``-``."""
    assert paths.encode("/home/user/lite-rpg") == "-home-user-lite-rpg"
    assert (
        paths.encode("/home/user/asuswrt-merlin.ng") == "-home-user-asuswrt-merlin-ng"
    )
    assert paths.encode("/home/user/a_b") == "-home-user-a-b"


def test_encode_for_cursor_strips_leading_separator() -> None:
    """Cursor's slug drops the leading path separator (slugs start with a word)."""
    assert paths.encode_for("cursor", "/home/user/lite-rpg") == "home-user-lite-rpg"


def test_encode_for_claude_keeps_leading_separator() -> None:
    """Claude's slug keeps the leading separator as a leading ``-``."""
    assert paths.encode_for("claude", "/home/user/project") == "-home-user-project"


def test_resolve_cursor_recovers_hyphen_leaf() -> None:
    """A hyphenated leaf is recovered from an in-band path (naive decode breaks)."""
    slug = "home-user-lite-rpg"
    texts = ["see /home/user/lite-rpg/src/main.py for details"]
    assert paths.resolve_cwd("cursor", slug, texts=texts) == "/home/user/lite-rpg"


def test_resolve_cursor_recovers_dot_leaf() -> None:
    """A dotted leaf is recovered too (``.`` also collapses to ``-`` on encode)."""
    slug = "home-user-asuswrt-merlin-ng"
    texts = ["cd /home/user/asuswrt-merlin.ng && make"]
    assert (
        paths.resolve_cwd("cursor", slug, texts=texts) == "/home/user/asuswrt-merlin.ng"
    )


def test_resolve_cursor_walks_ancestors_to_project_root() -> None:
    """A deeper in-band path resolves to the ancestor whose encode == slug."""
    slug = "home-user-lite-rpg"
    texts = ["error in /home/user/lite-rpg/a/b/c.txt"]
    assert paths.resolve_cwd("cursor", slug, texts=texts) == "/home/user/lite-rpg"


def test_resolve_cursor_null_when_no_inband_path() -> None:
    """No in-band absolute path -> honest ``None`` (never a fabricated guess)."""
    slug = "home-user-cursor-rules"
    texts = ["no absolute paths here", "just discussing cursor-rules in the abstract"]
    assert paths.resolve_cwd("cursor", slug, texts=texts) is None


def test_resolve_claude_record_cwd_short_circuits() -> None:
    """Claude's authoritative record ``cwd`` is returned directly."""
    assert (
        paths.resolve_cwd(
            "claude", "-home-user-project", record_cwd="/home/user/project"
        )
        == "/home/user/project"
    )


def test_resolve_is_deletion_proof_no_filesystem_access() -> None:
    """Recovery works purely from stored text, even for a path absent on disk.

    This is the survive-deletion invariant: ``cwd`` is recoverable from the
    transcript after the project directory has been deleted/moved, so the
    resolver must never consult the live filesystem.
    """
    slug = "home-user-deleted-proj"
    texts = ["was working in /home/user/deleted-proj before it was removed"]
    assert paths.resolve_cwd("cursor", slug, texts=texts) == "/home/user/deleted-proj"
