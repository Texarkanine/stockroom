"""Structural-only probe to lock the project-dir `encode` transform.

Reads ONLY directory names and the `cwd` path field from real transcripts
(never conversation content). For Claude, each project dir name is the encoded
form of the authoritative record `cwd`, so comparing the two derives the exact
transform empirically. Also enumerates the distinct characters present in real
slugs/paths so we can see whether anything beyond `/` and `.` is escaped.
"""

import json
import re
from collections import Counter
from pathlib import Path

CURSOR_ROOT = Path.home() / ".cursor" / "projects"
CLAUDE_ROOT = Path.home() / ".claude" / "projects"


def encode(path: str) -> str:
    """Hypothesis: collapse '/' and '.' to '-' (leading sep -> leading '-')."""
    return re.sub(r"[/.]", "-", path)


def first_cwd(jsonl: Path) -> str | None:
    """Return the first `cwd` path found in a .jsonl (structural field only)."""
    try:
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or '"cwd"' not in line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and isinstance(obj.get("cwd"), str):
                return obj["cwd"]
    except OSError:
        return None
    return None


def char_diff(real_path: str, slug: str) -> list[tuple[str, str]]:
    """Per-position (real_char, slug_char) where they differ (best-effort)."""
    diffs: list[tuple[str, str]] = []
    for rc, sc in zip(real_path, slug):
        if rc != sc:
            diffs.append((rc, sc))
    return diffs


def probe_claude() -> None:
    print("=== CLAUDE: encode(cwd) == dirname? ===")
    match = mismatch = no_cwd = 0
    offending: Counter = Counter()
    for project_dir in sorted(CLAUDE_ROOT.iterdir()):
        if not project_dir.is_dir():
            continue
        jsonls = sorted(project_dir.glob("*.jsonl"))
        cwd = next((c for c in (first_cwd(j) for j in jsonls) if c), None)
        if cwd is None:
            no_cwd += 1
            print(f"  [no cwd] {project_dir.name}")
            continue
        candidate = encode(cwd)
        # Claude keeps the leading separator as a leading '-'.
        if candidate == project_dir.name:
            match += 1
        else:
            mismatch += 1
            diffs = char_diff(cwd, project_dir.name)
            for rc, sc in diffs:
                offending[(rc, sc)] += 1
            print(f"  [MISMATCH] cwd={cwd!r}")
            print(f"             slug={project_dir.name!r}")
            print(f"             enc ={candidate!r}")
            print(f"             diffs={diffs}")
    print(f"  match={match} mismatch={mismatch} no_cwd={no_cwd}")
    if offending:
        print(f"  offending (real_char -> slug_char): {dict(offending)}")


def enumerate_slug_chars() -> None:
    print("\n=== Distinct characters in real slugs ===")
    for label, root in (("cursor", CURSOR_ROOT), ("claude", CLAUDE_ROOT)):
        chars: Counter = Counter()
        for project_dir in root.iterdir():
            if project_dir.is_dir():
                chars.update(project_dir.name)
        printable = {c: n for c, n in sorted(chars.items())}
        print(f"  [{label}] {printable}")


def enumerate_cwd_chars() -> None:
    print("\n=== Distinct NON-alphanumeric chars in real Claude cwds ===")
    chars: Counter = Counter()
    for project_dir in CLAUDE_ROOT.iterdir():
        if not project_dir.is_dir():
            continue
        for jsonl in sorted(project_dir.glob("*.jsonl")):
            cwd = first_cwd(jsonl)
            if cwd:
                chars.update(c for c in cwd if not c.isalnum())
                break
    print(f"  {dict(sorted(chars.items()))}")


if __name__ == "__main__":
    probe_claude()
    enumerate_slug_chars()
    enumerate_cwd_chars()
