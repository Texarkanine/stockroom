"""Discovery, path resolution, and watermark filtering for ingest.

This is the "extract" front of the ETL: given a harness root (the operator's
``~/.cursor/projects`` / ``~/.claude/projects``, overridable via env vars for
tests), it walks the real on-disk layout and yields one
:class:`DiscoveredSession` per conversation — the session file, its subagent
transcripts, the decoded project path, and the file mtime that drives the
incremental watermark.

On-disk layouts (reverse-engineered, clean-room):

* **Cursor** — ``<root>/<encoded-project>/agent-transcripts/<conv>/<conv>.jsonl``
  with subagents at ``<conv>/subagents/*.jsonl``. The conversation id is the
  file stem (which equals its directory name).
* **Claude** — ``<root>/<encoded-cwd>/<sessionId>.jsonl`` with subagents at
  ``<sessionId>/subagents/agent-*.jsonl`` (each beside a ``.meta.json``). The
  nested ``<sessionId>/`` directory is *not* itself a session.

The encoded project-dir name decodes to a plausible absolute path (lossy —
dashes that were really hyphens in the path can't be recovered). For Claude the
authoritative ``cwd`` comes from the records (the parser's job); this decode is
the only ``project_path`` source for Cursor.
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

#: Env vars overriding the harness roots (mirroring warehouse's STOCKROOM_HOME).
CURSOR_ROOT_ENV_VAR = "STOCKROOM_CURSOR_ROOT"
CLAUDE_ROOT_ENV_VAR = "STOCKROOM_CLAUDE_ROOT"


@dataclass
class DiscoveredSession:
    """One discovered conversation: where it is and when it last changed.

    ``subagent_paths`` holds the child transcript ``.jsonl`` files (Claude's
    ``.meta.json`` sidecar is derived from each path by the orchestrator).
    ``mtime`` is the session file's modification time and, with
    ``session_path``, forms the ``(mtime, path)`` watermark key.
    """

    harness: str
    session_path: Path
    subagent_paths: list[Path] = field(default_factory=list)
    project_path: str | None = None
    mtime: datetime | None = None

    @property
    def source_path(self) -> str:
        """The session file path as a string (the watermark tie-break key)."""
        return str(self.session_path)


def _resolve_root(env_var: str, default: Path) -> Path:
    override = os.environ.get(env_var)
    return Path(override) if override else default


def cursor_root() -> Path:
    """Return the Cursor projects root (``STOCKROOM_CURSOR_ROOT`` or default)."""
    return _resolve_root(CURSOR_ROOT_ENV_VAR, Path.home() / ".cursor" / "projects")


def claude_root() -> Path:
    """Return the Claude projects root (``STOCKROOM_CLAUDE_ROOT`` or default)."""
    return _resolve_root(CLAUDE_ROOT_ENV_VAR, Path.home() / ".claude" / "projects")


def decode_project_dir(name: str) -> str:
    """Decode an encoded project-dir name to a plausible absolute path.

    Both harnesses map path separators to dashes; Cursor additionally drops the
    leading slash while Claude keeps it as a leading dash. The decode is
    therefore ``'-' -> '/'`` with a leading slash ensured. It is lossy by
    construction (a literal hyphen in a real directory name is indistinguishable
    from a separator) and best-effort — never a join key.
    """
    decoded = name.replace("-", "/")
    if not decoded.startswith("/"):
        decoded = "/" + decoded
    return decoded


def _mtime(path: Path) -> datetime:
    """Return a file's modification time as a naive-local datetime."""
    return datetime.fromtimestamp(path.stat().st_mtime)


def _discover_cursor(root: Path) -> list[DiscoveredSession]:
    sessions: list[DiscoveredSession] = []
    if not root.is_dir():
        return sessions
    for project_dir in root.iterdir():
        if not project_dir.is_dir():
            continue
        project_path = decode_project_dir(project_dir.name)
        transcripts = project_dir / "agent-transcripts"
        if not transcripts.is_dir():
            continue
        for conv_dir in transcripts.iterdir():
            if not conv_dir.is_dir():
                continue
            session_file = conv_dir / f"{conv_dir.name}.jsonl"
            if not session_file.is_file():
                continue
            subagents_dir = conv_dir / "subagents"
            subagents = (
                sorted(subagents_dir.glob("*.jsonl")) if subagents_dir.is_dir() else []
            )
            sessions.append(
                DiscoveredSession(
                    harness="cursor",
                    session_path=session_file,
                    subagent_paths=subagents,
                    project_path=project_path,
                    mtime=_mtime(session_file),
                )
            )
    return sessions


def _discover_claude(root: Path) -> list[DiscoveredSession]:
    sessions: list[DiscoveredSession] = []
    if not root.is_dir():
        return sessions
    for project_dir in root.iterdir():
        if not project_dir.is_dir():
            continue
        project_path = decode_project_dir(project_dir.name)
        for session_file in project_dir.glob("*.jsonl"):
            if not session_file.is_file():
                continue
            subagents_dir = project_dir / session_file.stem / "subagents"
            subagents = (
                sorted(subagents_dir.glob("agent-*.jsonl"))
                if subagents_dir.is_dir()
                else []
            )
            sessions.append(
                DiscoveredSession(
                    harness="claude",
                    session_path=session_file,
                    subagent_paths=subagents,
                    project_path=project_path,
                    mtime=_mtime(session_file),
                )
            )
    return sessions


def discover(harness: str, root: Path | None = None) -> list[DiscoveredSession]:
    """Enumerate every session under a harness root, sorted by path.

    ``root`` defaults to the env-resolved harness root. The deterministic
    path-sorted order keeps downstream ingest (and the golden snapshot)
    reproducible across machines.
    """
    if harness == "cursor":
        resolved = root if root is not None else cursor_root()
        found = _discover_cursor(Path(resolved))
    elif harness == "claude":
        resolved = root if root is not None else claude_root()
        found = _discover_claude(Path(resolved))
    else:
        raise ValueError(f"unknown harness: {harness!r}")
    found.sort(key=lambda d: str(d.session_path))
    return found


def select_new(
    sessions: list[DiscoveredSession],
    *,
    last_mtime: datetime | None,
    last_path: str | None,
) -> list[DiscoveredSession]:
    """Keep sessions strictly newer than the ``(last_mtime, last_path)`` mark.

    A session is selected when ``(mtime, source_path) > (last_mtime,
    last_path)`` — mtime first, the path as a stable tie-break so two files
    sharing an mtime are still ordered deterministically. When ``last_mtime`` is
    ``None`` (no prior watermark, or a ``--full`` run) every session is kept.
    """
    if last_mtime is None:
        return list(sessions)
    floor_path = last_path or ""
    return [s for s in sessions if (s.mtime, s.source_path) > (last_mtime, floor_path)]
