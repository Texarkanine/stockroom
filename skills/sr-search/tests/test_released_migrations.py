"""The released-migrations gate: released SQL never changes, comments may.

The gate lives at repo-root ``scripts/check_released_migrations.py`` (stdlib,
not an engine package). Tests load it via importlib, as the ERD generator's
tests do. Each case builds a throwaway git repository with a tag, so the
tests go red when the gate breaks, not when a migration is edited.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

_MIGRATIONS = "skills/sr-search/src/stockroom/migrations"
_SCHEMAS = "skills/sr-search/src/stockroom/schemas"

_M1 = f"{_MIGRATIONS}/0001_initial.sql"
_M2 = f"{_MIGRATIONS}/0002_more.sql"

_M1_SQL = """-- 0001: the first tables.
CREATE TABLE sessions (
    session_id VARCHAR NOT NULL,
    started_at TIMESTAMP,
    PRIMARY KEY (session_id)
);
"""

_M2_SQL = """ALTER TABLE sessions ADD COLUMN cwd TEXT;
ALTER TABLE sessions ADD COLUMN model TEXT;
"""


@pytest.fixture(scope="session")
def gate(repo_root: Path) -> ModuleType:
    """Load ``scripts/check_released_migrations.py`` as a module."""
    path = repo_root / "scripts" / "check_released_migrations.py"
    spec = importlib.util.spec_from_file_location("check_released_migrations", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _git(repo: Path, *args: str) -> None:
    """Run git in ``repo`` with an identity and no signing or hooks.

    CI runners have no global git identity, and a developer's config may
    sign or run hooks, so every setting a commit or tag needs is passed here.
    """
    subprocess.run(
        [
            "git",
            "-C",
            str(repo),
            "-c",
            "user.name=Gate Test",
            "-c",
            "user.email=gate-test@example.invalid",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "tag.gpgsign=false",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "init.defaultBranch=main",
            *args,
        ],
        check=True,
        capture_output=True,
    )


def _release(repo: Path, files: dict[str, str], tag: str) -> None:
    """Write ``files`` (repo-relative path to text), commit them, tag ``tag``."""
    if not (repo / ".git").exists():
        _git(repo, "init", "-q")
    for rel, text in files.items():
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    _git(repo, "add", "--all")
    _git(repo, "commit", "-q", "--allow-empty", "-m", f"release {tag}")
    _git(repo, "tag", tag)


def _write(repo: Path, rel: str, text: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_sql_tokens_drop_comments_and_whitespace(gate: ModuleType) -> None:
    """G1: comments, blank lines, and runs of spaces leave the bare tokens.

    A ``--`` or ``/*`` inside a string literal or quoted identifier stays in
    that token, and a doubled quote does not end a literal.
    """
    bare = "CREATE TABLE t (a INT, b TEXT DEFAULT 'x');"
    noisy = """-- leading comment
    /* a block
       comment */
    CREATE   TABLE t (   -- trailing comment
        a INT,

        b TEXT DEFAULT 'x' /* inline */
    );
    """
    assert gate.sql_tokens(noisy) == gate.sql_tokens(bare)
    assert gate.sql_tokens(bare) == [
        "CREATE",
        "TABLE",
        "t",
        "(",
        "a",
        "INT",
        ",",
        "b",
        "TEXT",
        "DEFAULT",
        "'x'",
        ")",
        ";",
    ]

    literal = "SELECT '-- not a comment', '/* nor */', 'it''s' FROM \"a--b\";"
    assert gate.sql_tokens(literal) == [
        "SELECT",
        "'-- not a comment'",
        ",",
        "'/* nor */'",
        ",",
        "'it''s'",
        "FROM",
        '"a--b"',
        ";",
    ]
    assert gate.sql_tokens('SELECT "x""y" -- gone') == ["SELECT", '"x""y"']


def test_comment_only_change_passes(gate: ModuleType, tmp_path: Path) -> None:
    """G2: a released migration changed only in comments and spacing passes."""
    _release(tmp_path, {_M1: _M1_SQL, _M2: _M2_SQL}, "v1.0.0")
    _write(
        tmp_path,
        _M1,
        "-- 0001: the first tables, with a new note.\n"
        "-- @rel-none sessions\n"
        "CREATE TABLE sessions (\n"
        "    session_id VARCHAR   NOT NULL,  -- the key\n\n"
        "    started_at TIMESTAMP,\n"
        "    PRIMARY KEY (session_id)\n"
        ");\n",
    )
    assert gate.problems(tmp_path) == []
    assert gate.main(["--repo", str(tmp_path)]) == 0


@pytest.mark.parametrize(
    ("edit", "old", "new"),
    [
        ("type", "started_at TIMESTAMP", "started_at TIMESTAMPTZ"),
        ("column", "started_at TIMESTAMP", "begun_at TIMESTAMP"),
        ("dropped statement", "PRIMARY KEY (session_id)", ""),
    ],
)
def test_token_change_fails_and_names_file(
    gate: ModuleType,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    edit: str,
    old: str,
    new: str,
) -> None:
    """G3: any token change fails, and the output names the file."""
    _release(tmp_path, {_M1: _M1_SQL, _M2: _M2_SQL}, "v1.0.0")
    assert old in _M1_SQL, edit
    _write(tmp_path, _M1, _M1_SQL.replace(old, new))

    assert gate.main(["--repo", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert _M1 in err
    assert "v1.0.0" in err
    assert _M2 not in err


@pytest.mark.parametrize("how", ["deleted", "renamed"])
def test_missing_released_file_fails(
    gate: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str], how: str
) -> None:
    """G4: a released migration deleted or renamed fails, naming its path."""
    _release(tmp_path, {_M1: _M1_SQL, _M2: _M2_SQL}, "v1.0.0")
    if how == "deleted":
        (tmp_path / _M2).unlink()
    else:
        (tmp_path / _M2).rename(tmp_path / _MIGRATIONS / "0002_renamed.sql")

    assert gate.main(["--repo", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert _M2 in err
    assert _M1 not in err


def test_migration_added_after_tag_is_not_checked(
    gate: ModuleType, tmp_path: Path
) -> None:
    """G5: a migration the tag does not hold is not compared with anything."""
    _release(tmp_path, {_M1: _M1_SQL}, "v1.0.0")
    _write(tmp_path, _M2, _M2_SQL)
    _write(tmp_path, f"{_SCHEMAS}/schema_0002.sql", "CREATE TABLE anything (x INT);")

    assert gate.problems(tmp_path) == []
    assert gate.main(["--repo", str(tmp_path)]) == 0


def test_latest_tag_is_highest_release_in_version_order(
    gate: ModuleType, tmp_path: Path
) -> None:
    """G6: ``v2.10.0`` beats ``v2.9.0``; other tag shapes are ignored."""
    _release(tmp_path, {_M1: _M1_SQL}, "v1.0.0")
    _release(tmp_path, {_M2: _M2_SQL}, "v2.10.0")
    _release(tmp_path, {}, "v2.9.0")
    _release(tmp_path, {}, "v3.0.0-rc.1")
    _release(tmp_path, {}, "release-9")
    _release(tmp_path, {}, "v10")

    assert gate.latest_release_tag(tmp_path) == "v2.10.0"
    assert set(gate.released_sql_files(tmp_path, "v2.10.0")) == {_M1, _M2}
    assert set(gate.released_sql_files(tmp_path, "v1.0.0")) == {_M1}


def test_no_release_tag_fails_and_says_fetch_tags(
    gate: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G7: a clone without ``vX.Y.Z`` tags fails and says to fetch tags."""
    _release(tmp_path, {_M1: _M1_SQL}, "not-a-release")

    assert gate.main(["--repo", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert "git fetch --tags" in err


def test_released_schema_file_change_fails(
    gate: ModuleType, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """G8: a released file under ``schemas/`` is frozen like a migration."""
    schema = f"{_SCHEMAS}/schema_0001.sql"
    _release(tmp_path, {_M1: _M1_SQL, schema: _M1_SQL}, "v1.0.0")
    _write(tmp_path, schema, _M1_SQL.replace("VARCHAR", "TEXT"))

    assert gate.main(["--repo", str(tmp_path)]) == 1
    err = capsys.readouterr().err
    assert schema in err
    assert _M1 not in err
