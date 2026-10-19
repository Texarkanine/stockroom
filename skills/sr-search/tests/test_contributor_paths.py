"""Contributor commands take the checkout path as one word.

``sr-initialize`` Step 7 sends a contributor to ``make shim``, and the
localdev flow prints a ``claude --plugin-dir …`` command to copy. A checkout
path commonly holds a space (``~/My Projects/stockroom``, or a Windows
profile such as ``/mnt/c/Users/Jane Doe/…`` under WSL) or a ``'``
(``O'Brien``), and every one of these commands must still pass that path as
one shell word.

The Make cases copy the shipped ``Makefile`` alone into such a folder and run
each target with ``UV=`` pointed at ``conftest.py``'s ``stub_uv``, which
prints its ``PYTHONPATH`` and arguments and runs nothing. The stub also sits
first on ``PATH``, so a recipe can never reach the real ``uv`` (and with it
the real shim or the live dashboard). Counting the stub's calls matters: with
a ``'`` in the path, plain ``make shim`` used to exit 0 having run nothing,
because the recipe's two ``'`` paired up into one variable assignment.
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest

#: Checkout folder names: a plain one, and the two characters a real path
#: commonly holds that the commands' shell text must survive.
_FOLDERS = pytest.mark.parametrize(
    "folder", ["plain", "Jane Doe", "O'Brien"], ids=["plain", "space", "apostrophe"]
)


def _uv_calls(stdout: str) -> list[tuple[str, list[str]]]:
    """Parse ``stub_uv``'s labelled lines out of make's stdout.

    Each call starts with one ``UV_PYTHONPATH:<value>`` line, followed by one
    ``UV_ARG:<arg>`` line per argument. Returns ``(PYTHONPATH, args)`` per
    call, in order. Make's own echoed recipe lines never start with ``UV_``.
    """
    calls: list[tuple[str, list[str]]] = []
    for line in stdout.splitlines():
        if line.startswith("UV_PYTHONPATH:"):
            calls.append((line.removeprefix("UV_PYTHONPATH:"), []))
        elif line.startswith("UV_ARG:"):
            calls[-1][1].append(line.removeprefix("UV_ARG:"))
    return calls


@_FOLDERS
@pytest.mark.parametrize(
    ("target", "calls"),
    [
        ("shim", [(True, True)]),
        ("torch", [(False, False), (True, False)]),
        ("local-engine", [(True, True), (True, True)]),
        ("local-dashboard", [(True, False)]),
    ],
    ids=["shim", "torch", "local-engine", "local-dashboard"],
)
def test_make_targets_take_the_checkout_path_as_one_word(
    tmp_path: Path,
    repo_root: Path,
    stub_uv: Path,
    folder: str,
    target: str,
    calls: list[tuple[bool, bool]],
) -> None:
    """Each Make target that passes the checkout's absolute engine path to
    the engine exits 0 and makes exactly the expected uv calls, in order:
    ``calls`` holds one ``(PYTHONPATH, --app-dir)`` pair per call, saying
    whether that call carries each one (``local-engine`` runs ``shim`` first,
    then ``ensure-env``; ``torch`` installs, then freezes). A call that should
    carry one gets the whole path, even when the checkout path holds a space
    or ``'``; a call that should not carry it gets none."""
    if shutil.which("make") is None:
        pytest.skip("make is not installed")
    checkout = tmp_path / folder / "stockroom"
    checkout.mkdir(parents=True)
    shutil.copy(repo_root / "Makefile", checkout / "Makefile")
    result = subprocess.run(
        ["make", "--no-print-directory", target, f"UV={stub_uv / 'uv'}"],
        cwd=checkout,
        env={
            "PATH": f"{stub_uv}{os.pathsep}{os.environ['PATH']}",
            "HOME": str(tmp_path),
        },
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    uv_calls = _uv_calls(result.stdout)
    assert len(uv_calls) == len(calls), f"stdout={result.stdout!r}"
    engine = checkout / "skills" / "sr-search"
    for (pythonpath, args), (wants_pythonpath, wants_app_dir) in zip(uv_calls, calls):
        assert pythonpath == (str(engine / "src") if wants_pythonpath else ""), args
        if wants_app_dir:
            assert args.count("--app-dir") == 1, args
            assert args[args.index("--app-dir") + 1] == str(engine), args
        else:
            assert "--app-dir" not in args, args


@_FOLDERS
def test_localdev_claude_hint_is_a_runnable_command(
    tmp_path: Path, repo_root: Path, folder: str
) -> None:
    """``localdev.sh skills --harness claude`` prints a ``claude --plugin-dir
    <checkout>`` command between backticks for the contributor to copy; it
    splits as shell words into exactly that command, with the checkout path
    as one word."""
    checkout = tmp_path / folder / "stockroom"
    checkout.mkdir(parents=True)
    result = subprocess.run(
        [
            "sh",
            str(repo_root / "scripts" / "localdev.sh"),
            "skills",
            "--harness",
            "claude",
            "--repo-root",
            str(checkout),
        ],
        env={"PATH": os.environ["PATH"], "HOME": str(tmp_path)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    (line,) = result.stdout.splitlines()
    command = line.split("`")[1]
    assert shlex.split(command) == ["claude", "--plugin-dir", str(checkout)]
