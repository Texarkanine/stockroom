"""sr-initialize Step 2: the engine dir and shim owner, as the skill resolves them.

Harnesses do not put plugin-root variables in an agent's shell (Claude Code:
they "aren't present in the environment of commands Claude runs through the
Bash tool"). What a harness gives the agent is the skill text itself:

* Claude Code substitutes the exact tokens ``${CLAUDE_SKILL_DIR}`` (every
  skill) and ``${CLAUDE_PLUGIN_ROOT}`` (plugin skills only) when it loads the
  skill, inside code fences too. Bare ``$CLAUDE_PLUGIN_ROOT`` stays literal.
* Other harnesses (Cursor) substitute nothing: the agent fills the block's
  angle-bracket placeholder with the directory it read SKILL.md from, and the
  harness may or may not export ``CURSOR_PLUGIN_ROOT``.

Each test renders the shipped Step 2 fence the way one harness would, runs it
under every installed POSIX-family shell with a minimal environment, then runs
the one line it prints — the agent's interface to every later step — in a
fresh shell and asserts the ``OWNER`` / ``APP_DIR`` that line sets.

The owner rule (operator decisions):

* Inside a harness's default plugins folder the path decides:
  ``…/.claude/plugins/cache/<marketplace>/<plugin>/<version>`` and
  ``…/.claude/plugins/synced/…`` (claude.ai sync) are ``claude``;
  ``…/.cursor/plugins/cache/…`` is ``cursor``.
* An install-shaped copy anywhere else is ``claude`` when Claude Code's
  install record (``installed_plugins.json`` in the plugins root, beside
  ``cache/``) lists its exact path, and ``cursor`` when the exported
  ``CURSOR_PLUGIN_ROOT`` holds it. Otherwise it gets no owner: in Claude Code
  the agent asks the user, and other harnesses name themselves. Claude Code's
  substituted plugin root alone is not proof, because ``--plugin-dir``
  substitutes a checkout the same way.
* Anything else run from a checkout (``--plugin-dir``, Cursor
  ``plugins/local``, a local-path marketplace, the localdev mirror) is ``dev``.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

SKILL_MD = Path("skills") / "sr-initialize" / "SKILL.md"
_BASH_FENCE_RE = re.compile(r"^```bash\n(.*?)^```", re.DOTALL | re.MULTILINE)
_PLACEHOLDER_RE = re.compile(r"<[^<>\n]+>")


def _step2_block(repo_root: Path) -> str:
    """Return the single bash fence in sr-initialize that assigns ``SKILL_DIR=``."""
    text = (repo_root / SKILL_MD).read_text(encoding="utf-8")
    blocks = [
        block
        for block in _BASH_FENCE_RE.findall(text)
        if re.search(r"^SKILL_DIR=", block, re.MULTILINE)
    ]
    assert len(blocks) == 1, (
        f"expected exactly one bash fence assigning SKILL_DIR= in {SKILL_MD}, "
        f"found {len(blocks)}"
    )
    return blocks[0]


def _render_claude(block: str, *, skill_dir: Path, plugin_root: Path | None) -> str:
    """Substitute Claude Code's skill-text tokens: the skill dir always, the
    plugin root only for a plugin skill (``plugin_root`` given)."""
    rendered = block.replace("${CLAUDE_SKILL_DIR}", str(skill_dir))
    if plugin_root is not None:
        rendered = rendered.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin_root))
    return rendered


def _fill_placeholder(block: str, skill_dir: Path) -> str:
    """Do what an agent in a non-substituting harness does: replace the
    angle-bracket placeholder with the skill's directory."""
    return _PLACEHOLDER_RE.sub(lambda _match: str(skill_dir), block)


def _run_block(
    shell: str, block: str, home: Path, env: dict[str, str] | None = None
) -> tuple[str, str]:
    """Run ``block`` under ``shell`` with only PATH, HOME and ``env`` set, then
    run the one ``APP_DIR=…; OWNER=…`` line it prints in a fresh ``shell``;
    return the ``(OWNER, APP_DIR)`` that line sets."""
    result = subprocess.run(
        [shell, "-c", block],
        env={"PATH": os.environ["PATH"], "HOME": str(home), **(env or {})},
        cwd=home,
        capture_output=True,
        text=True,
    )
    printed = [
        line for line in result.stdout.splitlines() if line.startswith("APP_DIR=")
    ]
    assert len(printed) == 1, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    readback = subprocess.run(
        [shell, "-c", printed[0] + '\nprintf "%s\\n%s\\n" "$OWNER" "$APP_DIR"\n'],
        env={"PATH": os.environ["PATH"]},
        capture_output=True,
        text=True,
    )
    lines = readback.stdout.splitlines()
    assert len(lines) >= 2, f"printed={printed[0]!r} stderr={readback.stderr!r}"
    return lines[-2], lines[-1]


def _plugin_tree(root: Path) -> Path:
    """Lay out an installed stockroom tree at ``root`` (engine with
    ``pyproject.toml`` beside sr-initialize); return the sr-initialize dir."""
    skill_dir = root / "skills" / "sr-initialize"
    skill_dir.mkdir(parents=True)
    engine = root / "skills" / "sr-search"
    engine.mkdir(parents=True)
    (engine / "pyproject.toml").write_text("[project]\nname = 'stockroom'\n")
    return skill_dir


def _checkout_tree(root: Path) -> Path:
    """A contributor checkout: the plugin tree plus ``Makefile`` and ``.git``
    (which marketplace copies carry too, so neither marks a checkout)."""
    skill_dir = _plugin_tree(root)
    (root / "Makefile").write_text("shim:\n")
    (root / ".git").mkdir()
    return skill_dir


def _record_install(plugins_root: Path, *install_paths: Path) -> None:
    """Write Claude Code's install record, ``installed_plugins.json`` in the
    plugins root beside ``cache/``, listing ``install_paths`` the way Claude
    Code 2.1.302 writes it (2-space indent, non-ASCII left as is)."""
    record = {
        "version": 2,
        "plugins": {
            "stockroom@txrk9": [
                {"scope": "user", "installPath": str(path), "version": path.name}
                for path in install_paths
            ]
        },
    }
    (plugins_root / "installed_plugins.json").write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


@pytest.fixture(params=["sh", "bash", "zsh"])
def shell(request: pytest.FixtureRequest) -> str:
    """Each POSIX-family shell an agent's Bash tool may run; skip absent ones."""
    path = shutil.which(request.param)
    if path is None:
        pytest.skip(f"{request.param} is not installed")
    return path


@pytest.fixture
def step2(repo_root: Path) -> str:
    """The shipped Step 2 fence."""
    return _step2_block(repo_root)


@pytest.fixture
def home(tmp_path: Path) -> Path:
    """A fixture HOME holding every harness's plugin folders."""
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    return home_dir


def test_claude_marketplace_install(shell: str, step2: str, home: Path) -> None:
    """A Claude Code marketplace copy (``~/.claude/plugins/cache/…``) is a
    real ``claude`` install with the cache engine dir."""
    root = home / ".claude" / "plugins" / "cache" / "txrk9" / "stockroom" / "2.1.1"
    skill_dir = _plugin_tree(root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, home) == (
        "claude",
        str(root / "skills" / "sr-search"),
    )


def test_claude_marketplace_without_substitution(
    shell: str, step2: str, home: Path
) -> None:
    """With no substitution at all (an older Claude Code; the agent fills the
    placeholder), the cache layout alone still says ``claude``."""
    root = home / ".claude" / "plugins" / "cache" / "txrk9" / "stockroom" / "2.1.1"
    skill_dir = _plugin_tree(root)
    block = _fill_placeholder(step2, skill_dir)
    assert _run_block(shell, block, home) == (
        "claude",
        str(root / "skills" / "sr-search"),
    )


def test_claude_custom_plugins_root_gets_no_owner(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """Under ``CLAUDE_CODE_PLUGIN_CACHE_DIR`` the cache lives outside
    ``~/.claude``. With no install record listing the copy, Claude Code's
    substituted plugin root is not proof of an install there
    (``--plugin-dir`` substitutes a checkout the same way), so the copy gets
    no owner and the agent asks the user."""
    root = tmp_path / "plugin-root" / "cache" / "txrk9" / "stockroom" / "2.1.1"
    skill_dir = _plugin_tree(root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, tmp_path) == (
        "",
        str(root / "skills" / "sr-search"),
    )


@pytest.mark.parametrize(
    "plugins_root",
    [Path("claude-work") / "plugins", Path("plugin-cache")],
    ids=["config-dir", "cache-dir"],
)
def test_claude_recorded_custom_root_install(
    shell: str, step2: str, tmp_path: Path, plugins_root: Path
) -> None:
    """A copy in a custom plugins root (``CLAUDE_CONFIG_DIR`` puts the root
    at ``<dir>/plugins``, ``CLAUDE_CODE_PLUGIN_CACHE_DIR`` at ``<dir>``) is a
    ``claude`` install when Claude Code's install record beside ``cache/``
    lists its exact path."""
    root_dir = tmp_path / plugins_root
    root = root_dir / "cache" / "txrk9" / "stockroom" / "2.1.1"
    skill_dir = _plugin_tree(root)
    _record_install(root_dir, root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, tmp_path) == (
        "claude",
        str(root / "skills" / "sr-search"),
    )


def test_claude_recorded_install_without_substitution(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """The record alone says ``claude`` when nothing is substituted: a Cursor
    agent reading Claude Code's copy, or an older Claude Code."""
    root_dir = tmp_path / "claude-work" / "plugins"
    root = root_dir / "cache" / "txrk9" / "stockroom" / "2.1.1"
    skill_dir = _plugin_tree(root)
    _record_install(root_dir, root)
    block = _fill_placeholder(step2, skill_dir)
    assert _run_block(shell, block, tmp_path) == (
        "claude",
        str(root / "skills" / "sr-search"),
    )


def test_claude_recorded_install_with_quotes_in_the_path(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """A recorded copy whose path holds ``'`` and a space is still found:
    JSON stores both unescaped."""
    root_dir = tmp_path / "O'Brien files" / "claude" / "plugins"
    root = root_dir / "cache" / "txrk9" / "stockroom" / "2.1.1"
    skill_dir = _plugin_tree(root)
    _record_install(root_dir, root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, tmp_path) == (
        "claude",
        str(root / "skills" / "sr-search"),
    )


def test_claude_orphaned_custom_root_copy_gets_no_owner(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """An old version that an update left in a custom plugins root
    (``.orphaned_at``) is not recorded, so it gets no owner: the record lists
    only the new version, and ``…/2.1.1`` must not match inside ``…/2.1.10``."""
    root_dir = tmp_path / "claude-work" / "plugins"
    old = root_dir / "cache" / "txrk9" / "stockroom" / "2.1.1"
    skill_dir = _plugin_tree(old)
    (old / ".orphaned_at").write_text("1792198859985")
    new = root_dir / "cache" / "txrk9" / "stockroom" / "2.1.10"
    _plugin_tree(new)
    _record_install(root_dir, new)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=old)
    assert _run_block(shell, block, tmp_path) == (
        "",
        str(old / "skills" / "sr-search"),
    )


def test_claude_plugin_dir_checkout_is_dev(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """``claude --plugin-dir <checkout>`` is a contributor load: ``dev``,
    even though Claude Code substitutes the checkout as the plugin root."""
    root = tmp_path / "git" / "stockroom"
    skill_dir = _checkout_tree(root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, tmp_path) == (
        "dev",
        str(root / "skills" / "sr-search"),
    )


def test_claude_plugin_dir_checkout_under_synced_is_dev(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """A ``--plugin-dir`` checkout whose path merely contains a ``synced``
    folder is still ``dev``: only ``…/.claude/plugins/synced/…`` is a
    claude.ai-synced copy."""
    root = tmp_path / "projects" / "synced" / "stockroom"
    skill_dir = _checkout_tree(root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, tmp_path) == (
        "dev",
        str(root / "skills" / "sr-search"),
    )


def test_checkout_in_a_cache_shaped_path_gets_no_owner(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """A ``--plugin-dir`` checkout three levels below a folder named
    ``cache`` looks like an install, but Claude Code's substituted root does
    not prove it: no ``claude`` label, and the agent asks the user."""
    root = tmp_path / "src" / "cache" / "acme" / "widgets" / "stockroom"
    skill_dir = _checkout_tree(root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, tmp_path) == (
        "",
        str(root / "skills" / "sr-search"),
    )


def test_printed_line_survives_quotes_in_the_path(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """The printed line is valid shell for a path holding ``'`` and a space
    (a Windows user name under WSL), so every later step can start with it."""
    root = tmp_path / "O'Brien files" / "stockroom"
    skill_dir = _checkout_tree(root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, tmp_path) == (
        "dev",
        str(root / "skills" / "sr-search"),
    )


def test_claude_local_marketplace_in_place_is_dev(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """A plugin loaded in place from a local-path marketplace is ``dev``."""
    root = tmp_path / "src" / "market" / "plugins" / "stockroom"
    skill_dir = _plugin_tree(root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, tmp_path) == (
        "dev",
        str(root / "skills" / "sr-search"),
    )


def test_claude_synced_plugin(shell: str, step2: str, home: Path) -> None:
    """A Claude Code copy synced from claude.ai is a real ``claude`` install."""
    root = home / ".claude" / "plugins" / "synced" / "bucket-1" / "stockroom"
    skill_dir = _plugin_tree(root)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    assert _run_block(shell, block, home) == (
        "claude",
        str(root / "skills" / "sr-search"),
    )


def test_claude_synced_plugin_without_substitution(
    shell: str, step2: str, home: Path
) -> None:
    """The synced path alone says ``claude``, also when the agent fills the
    placeholder (Cursor agents read skills from Claude Code's plugin folders)."""
    root = home / ".claude" / "plugins" / "synced" / "bucket-1" / "stockroom"
    skill_dir = _plugin_tree(root)
    block = _fill_placeholder(step2, skill_dir)
    assert _run_block(shell, block, home) == (
        "claude",
        str(root / "skills" / "sr-search"),
    )


def test_cursor_marketplace_install(shell: str, step2: str, home: Path) -> None:
    """A Cursor marketplace copy (``~/.cursor/plugins/cache/…``) is a real
    ``cursor`` install even with no plugin-root variable in the shell."""
    root = home / ".cursor" / "plugins" / "cache" / "txrk9" / "stockroom" / "672cf3aa"
    skill_dir = _plugin_tree(root)
    block = _fill_placeholder(step2, skill_dir)
    assert _run_block(shell, block, home) == (
        "cursor",
        str(root / "skills" / "sr-search"),
    )


def test_cursor_custom_cache_with_env(shell: str, step2: str, tmp_path: Path) -> None:
    """A cache copy outside ``~/.cursor`` is ``cursor`` when the exported
    ``CURSOR_PLUGIN_ROOT`` holds this very engine."""
    root = tmp_path / "elsewhere" / "cache" / "txrk9" / "stockroom" / "672cf3aa"
    skill_dir = _plugin_tree(root)
    block = _fill_placeholder(step2, skill_dir)
    env = {"CURSOR_PLUGIN_ROOT": str(root)}
    assert _run_block(shell, block, tmp_path, env) == (
        "cursor",
        str(root / "skills" / "sr-search"),
    )


def test_cursor_local_plugin_is_dev(shell: str, step2: str, home: Path) -> None:
    """Cursor's plugin-development folder (``~/.cursor/plugins/local``) is
    ``dev`` even when Cursor exports its plugin root."""
    root = home / ".cursor" / "plugins" / "local" / "stockroom"
    skill_dir = _plugin_tree(root)
    block = _fill_placeholder(step2, skill_dir)
    env = {"CURSOR_PLUGIN_ROOT": str(root)}
    assert _run_block(shell, block, home, env) == (
        "dev",
        str(root / "skills" / "sr-search"),
    )


def test_cursor_localdev_mirror_is_dev(shell: str, step2: str, tmp_path: Path) -> None:
    """The ``make localdev`` mirror is ``dev``; APP_DIR stays the logical
    mirror path and resolves into the checkout."""
    repo = tmp_path / "git" / "stockroom"
    _checkout_tree(repo)
    mirror = repo / ".cursor" / "skills" / "stockroom-local"
    mirror.mkdir(parents=True)
    for name in ("sr-initialize", "sr-search"):
        (mirror / name).symlink_to(Path("..") / ".." / ".." / "skills" / name)
    block = _fill_placeholder(step2, mirror / "sr-initialize")
    owner, app_dir = _run_block(shell, block, tmp_path)
    assert (owner, app_dir) == ("dev", str(mirror / "sr-search"))
    assert Path(app_dir).resolve() == (repo / "skills" / "sr-search").resolve()


def test_localdev_mirror_in_a_cache_named_dir_is_dev(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """A checkout cloned straight into a directory named ``cache`` still
    yields ``dev`` through its localdev mirror: a marketplace copy always has
    the plugin layout ``<root>/skills/sr-search``, which the mirror lacks."""
    repo = tmp_path / "cache" / "stockroom"
    _checkout_tree(repo)
    mirror = repo / ".cursor" / "skills" / "stockroom-local"
    mirror.mkdir(parents=True)
    for name in ("sr-initialize", "sr-search"):
        (mirror / name).symlink_to(Path("..") / ".." / ".." / "skills" / name)
    block = _fill_placeholder(step2, mirror / "sr-initialize")
    assert _run_block(shell, block, tmp_path) == ("dev", str(mirror / "sr-search"))


def test_leaked_cursor_root_is_ignored(shell: str, step2: str, tmp_path: Path) -> None:
    """A ``CURSOR_PLUGIN_ROOT`` inherited from some other plugin labels
    nothing: a Claude Code custom-root copy it does not hold gets no owner."""
    root = tmp_path / "plugin-root" / "cache" / "txrk9" / "stockroom" / "2.1.1"
    skill_dir = _plugin_tree(root)
    other = tmp_path / "elsewhere" / "cache" / "other" / "stockroom" / "1.0.0"
    _plugin_tree(other)
    block = _render_claude(step2, skill_dir=skill_dir, plugin_root=root)
    env = {"CURSOR_PLUGIN_ROOT": str(other)}
    assert _run_block(shell, block, tmp_path, env) == (
        "",
        str(root / "skills" / "sr-search"),
    )


def test_unattributed_install_has_no_owner(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """A cache copy no harness vouches for gets no owner (the agent names
    its harness, or in Claude Code asks the user), but the engine dir is
    still resolved."""
    root = tmp_path / "elsewhere" / "cache" / "txrk9" / "stockroom" / "2.1.1"
    skill_dir = _plugin_tree(root)
    block = _fill_placeholder(step2, skill_dir)
    assert _run_block(shell, block, tmp_path) == (
        "",
        str(root / "skills" / "sr-search"),
    )


def test_missing_engine_resolves_nothing(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """A skill dir with no sibling engine yields neither owner nor engine."""
    skill_dir = tmp_path / "lonely" / "sr-initialize"
    skill_dir.mkdir(parents=True)
    block = _fill_placeholder(step2, skill_dir)
    assert _run_block(shell, block, tmp_path) == ("", "")


def test_unfilled_placeholder_resolves_nothing(
    shell: str, step2: str, tmp_path: Path
) -> None:
    """Run verbatim outside Claude Code (placeholder left in), the block
    finds no engine instead of guessing."""
    assert _run_block(shell, step2, tmp_path) == ("", "")
