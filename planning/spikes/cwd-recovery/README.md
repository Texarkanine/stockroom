# Spike — Workspace Identity vs. Real Path (`project_id` + `cwd` recovery)

Durable planning artifact for a **new `p1-data-backbone` milestone**, discovered while exercising
the post-ingest warehouse (the `sr-query`-style grouping query). It supersedes the ephemeral
creative doc `memory-bank/active/creative/creative-cursor-workspace-path-recovery.md` (that file
is reaped when `/niko` Step 2a checks off the Trace-ingest milestone; this one is permanent).

## Problem

Conversations are stored under an **encoded project-dir slug** where path separators **and `.`**
collapse to `-`. The current ingest decode (`stockroom.ingest.sources.decode_project_dir`) is a
naive `name.replace("-", "/")`, which **fabricates paths that never existed**:

```
~/.cursor/projects/home-mobaxterm-Documents-git-lite-rpg
  naive decode -> /home/mobaxterm/Documents/git/lite/rpg   ← WRONG (no such dir)
  real         -> /home/mobaxterm/Documents/git/lite-rpg
```

The encoding is many-to-one (`lite-rpg`, `lite/rpg`, `lite.rpg` all encode to `…-lite-rpg`), so
**no pure string transform can invert it.** A wrong-but-plausible path is worse than no path.

## Empirical findings (this spike's investigation)

- **Encoding observed:** `/` → `-` and `.` → `-` (e.g. `…Workspaces-1774194512166-workspace-json`
  is really `…/Workspaces/1774194512166/workspace.json`; Claude `-home-mobaxterm-git--cursor-rules`
  shows `.cursor` → `-cursor`, hence the double dash). **Still to confirm before coding:** whether
  `_` or any other character is also escaped. This is the one genuine prerequisite.
- **Claude has an authoritative real path:** every record carries `"cwd":"…"` (verified). The
  parser already extracts it. It survives directory deletion (it's in the record).
- **Cursor has NO structured path field:** records are only `{role, message}` + a `turn_ended`
  marker. Cursor's `Workspace Path:` user-info line is **not** reliably stored (1/45 projects,
  and that one was a false match on system-prompt template text). Terminal-file `cwd` headers
  exist but are **unreliable** (terminals `cd` anywhere — one lite-rpg terminal showed a
  cursor-warehouse cwd). `ide_state.json` is global/recent, not per-session.
- **cursor-warehouse's approach (filesystem-probing greedy reconstruction) is rejected:** it only
  works while the directory still exists on disk — it fails for deleted/moved projects and
  unmounted Windows paths, the exact failure the operator called out.
- **Re-encode-and-match works and is deletion-proof:** collect candidate real paths from the
  *stored transcript content* (in-band absolute paths) and accept a candidate **only if
  `encode(candidate) == slug`**. Verification, not guessing — structurally cannot emit a fake
  path. Measured: **28/40** Cursor projects recovered from in-band content alone (≤3 files each),
  and it nailed every ambiguous case naive decode breaks: `lite-rpg`, `asuswrt-merlin.ng`
  (recovered the dot), `client-side-mdc-render`, `nuclear-pyramid-archive`,
  `inquirerjs-checkbox-search`, `my-streamdeck-drivers`. The misses are genuinely-ambiguous slugs
  with no in-band evidence (e.g. `cursor-rules`) — correctly left unresolved.

## Decision

### Data model (`sessions` table)

Split the one muddy concept into two single-meaning columns, per the project's
one-meaning-per-column / honestly-NULL doctrine:

- **`project_id`** (NEW, replaces `project_path`) — the harness's grouping **identity**: the
  encoded dir name stored **verbatim** (Cursor `home-mobaxterm-Documents-git-lite-rpg`; Claude
  `-mnt-v-users-Austin-Documents-git-lite-rpg`). An id, not a path: always present, never
  fabricated, lossless, the correct GROUP BY key. Matches the `_id` naming convention. For Claude
  it *happens* to encode a path; for Cursor it's the dashed slug — treated as opaque either way.
- **`cwd`** (re-semantic) — the **absolute filesystem path of the project root**, best-effort,
  **NULL when unknown**. One uniform meaning across harnesses. NULL costs nothing because grouping
  rides on `project_id`.
- **`project_path`** — **dropped** (implied a real path but held a fabricated one for Cursor;
  redundant with `cwd`).

Today's columns are effectively redundant: Cursor sets `project_path == cwd ==` the lossy decode
(byte-identical); Claude sets `project_path` = lossy decode while `cwd` = authoritative — same
concept, two fidelities. The split fixes that.

**Robustness:** `project_id` is the raw dir name (no transform) so it can never be wrong. Only
`cwd` recovery uses `encode`, and its failure mode is a clean NULL — so the design is robust to
any imperfection in the `encode` transform.

### `cwd` population algorithm

Candidate sourcing, in priority order, **all gated by `encode(candidate) == slug`**:

1. **Claude:** record `cwd` — authoritative, short-circuits (no matching needed).
2. **Cursor:** absolute paths scraped from the transcript text (`/home`, `/mnt`, `/tmp`,
   single-letter `/s/…` drive roots); for each, walk ancestors and keep the one whose `encode`
   equals the slug. Stop at first hit.
3. *(optional)* live-FS greedy walk (cursor-warehouse style) as an additional candidate generator
   — never the sole source, since it fails on deletion.
4. *(optional, later)* cross-conversation corpus (other sessions' resolved paths).
5. No match → `cwd = NULL`.

### Migration route — RESOLVED

**A new forward migration `0002`**, not a `0001` rewrite. Operator decision: honor the
`milestones.md` line-10 invariant ("schema changes only via a new numbered, forward-only
migration; no milestone mutates an existing migration") rather than waive it. The buildout thrash
will be **squashed at initial release** (a sanctioned future cleanup), and the embedding milestone
already verifies the migration machinery — so there's no need to preserve this churn just to
"prove it works." DuckDB `ALTER TABLE … ADD/DROP/RENAME COLUMN` + a backfill `UPDATE`.

(The operator's local DB has been deleted; a `--full` re-ingest rebuilds it. The warehouse is
derived ETL output — reconstructable from source logs — so no data is at risk regardless.)

## Implementation sketch (for the sub-run, TDD)

1. **Confirm the `encode` transform empirically** (prerequisite) — enumerate which characters
   Cursor and Claude escape to `-` (`/` and `.` confirmed; check `_` and others) across many real
   slugs. Lock it as the canonical `encode(path)` (Cursor strips the leading separator; Claude
   keeps it as a leading `-`, doubled for a leading-dot segment).
2. **`0002` migration** — drop `project_path`, add `project_id`, keep `cwd`; backfill.
   Add the `0002` schema snapshot; keep `0001_snapshot.json` untouched.
3. **Ingest population** — `sources`/discovery stamps `project_id` = verbatim dir name; remove
   `decode_project_dir`. A focused `cwd` resolver (favor a dedicated `paths.py` so `sources` stays
   discovery-I/O and the `cursor.py`/`claude.py` parsers stay pure) implements re-encode-and-match;
   Claude uses record `cwd`. Subagents inherit parent `project_id` + `cwd`.
4. **Update the orchestrator** — and fix the latent bug where Claude `project_path`/`cwd` were both
   stamped from the lossy decode (`ingest/__init__.py:111`).
5. **Tests / determinism** — Cursor `cwd` recovery must resolve from **fixture content**, never the
   host filesystem, so `expected_rows.json` stays machine-independent. Add: a fixture with an
   in-band absolute path (locks a non-NULL recovery incl. a hyphenated + a dotted leaf), and an
   ambiguous fixture with no evidence (locks `cwd = NULL`). Regenerate `expected_rows.json`.
6. **Sweep all `project_path` references** — orchestrator, `writer.py`, `model.py`, docs, snapshots.
7. **Green gate** `make ci`.

## Caveats

- `encode` is many-to-one, so two distinct real paths can collapse to one `project_id`
  (`…/cursor-rules` vs `…/cursor.rules`). Benign for grouping (it merges them) — note, don't engineer
  around it.
- Many Cursor chats legitimately yield `cwd = NULL` (no terminal/skill/attachment exposing a path).
  That is the intended, correct outcome — "work in general; if we can't, leave it blank."

## References

- Superseded creative doc (ephemeral): `memory-bank/active/creative/creative-cursor-workspace-path-recovery.md`
- Locked schema: `skills/sr-search/src/stockroom/migrations/0001_initial_schema.sql` (`sessions`)
- Current decode + discovery: `skills/sr-search/src/stockroom/ingest/sources.py`
- Orchestrator stamping: `skills/sr-search/src/stockroom/ingest/__init__.py`
- cursor-warehouse greedy reconstruction (rejected primary, optional generator):
  `~/Documents/git/cursor-warehouse/scripts/sync.py` (`_reconstruct_project_name`)
