# Task: Cursor state.vscdb one-shot backfill

* Task ID: cursor-vscdb-backfill
* Complexity: Level 3
* Type: feature

One-shot, opt-in backfill of legacy Cursor `state.vscdb` composers into the warehouse ([#84](https://github.com/Texarkanine/stockroom/issues/84)), selecting every composer the warehouse does not already have — tokens are not a selection gate. Core nightly ingest is untouched.

## Pinned Info

### Corpus facts (probed 2026-07-25 on this machine)

Source: the operator's Cursor `globalStorage/state.vscdb` (5.7 GB), reached over a WSL→Windows mount.

| Fact | Value |
|---|---|
| `composerData` keys | 2,039 |
| Already in warehouse (by `session_id`) | 1,131 |
| **Backfill candidates** | **908** |
| ...with ≥1 resolvable bubble | 609 (+26 legacy inline) |
| ...empty drafts (0 bubbles) | 273 |
| Bubbles to reconstruct | ~75,800 |
| Candidates with nonzero bubble tokens | 418 |
| Date span | 2025-03 → 2026-07 |
| `cwd` resolvable via `workspaceStorage` | 437 |
| Warehouse messages today (all harnesses) | 43,892 |

### Data flow

```mermaid
flowchart LR
    subgraph vscdb["state.vscdb (SQLite, read-only)"]
        CH["composerHeaders (table)<br/>composerId → workspaceId"]
        CD["cursorDiskKV<br/>composerData:{id}<br/>name, createdAt,<br/>fullConversationHeadersOnly[]"]
        BB["cursorDiskKV<br/>bubbleId:{composerId}:{bubbleId}<br/>type, text, toolFormerData,<br/>thinking, tokenCount, createdAt"]
    end
    WJ["../workspaceStorage/{workspaceId}/<br/>workspace.json → folder URI"]

    CD -->|ordered bubbleIds| BB
    CH --> WJ
    CD --> P["ingest.cursor_vscdb<br/>(new parser)"]
    BB --> P
    WJ --> P
    P -->|NormalizedSession| BF["backfill<br/>(new orchestrator + CLI)"]
    WH[("warehouse<br/>existing session_ids")] -->|skip set| BF
    BF --> W[["ingest.writer.write_session<br/>(unchanged)"]]
    W --> DB[(warehouse.duckdb)]
    BF -.->|never| SS["_sync_state watermarks"]
```

## Component Analysis

### Affected Components

- **`stockroom.ingest.cursor_vscdb` (NEW)**: clean-room parser turning one composer plus its bubbles into a `NormalizedSession`; owns its read-only SQLite access and `workspace.json` lookups.
- **`stockroom.backfill` (NEW)**: one-shot orchestrator + `main(argv)` CLI. Resolves the vscdb path, selects composers absent from the warehouse, parses, writes, prints a summary. Deliberately a **sibling of** `stockroom.ingest`, not a member: nothing on the nightly path imports it.
- **`stockroom.__main__`**: dispatcher `SUBCOMMANDS` table → add `backfill`.
- **`stockroom.ingest.writer`**: **unchanged**, reused (`write_session`). `update_watermark` deliberately never called.
- **`stockroom.ingest.model`**: **unchanged**, reused as the parser/writer contract.
- **`stockroom.ingest.paths`**: **unchanged**; `workspace_key_for` continues to run inside the writer.
- **`stockroom.config`**: add `[cursor].state_vscdb` (no discoverable default exists on WSL→Windows, where the DB lives on the Windows side).
- **`stockroom.warehouse`**: **unchanged**, reused via `open(read_only=False)`.
- **Docs**: `docs/user-guide/ingest.md`, `docs/user-guide/installed-layout.md`, `docs/advanced/cli.md`, `docs/architecture/lifecycle.md`, `docs/contributing/iteration.md`.
- **Tests**: new parser / orchestrator / CLI modules, a shared vscdb-builder fixture, and the dispatcher `SUBCOMMANDS` ratchet.

### Cross-Module Dependencies

- `backfill` → `ingest.cursor_vscdb` → `ingest.model`
- `backfill` → `ingest.writer.write_session` → DuckDB (only SQL touchpoint for session rows)
- `backfill` → `warehouse.open(read_only=False)` (flock single-writer invariant)
- `backfill` → `config` / env / CLI flag for the vscdb path
- `__main__` → `backfill` (lazy import at dispatch)
- **No edge** from `ingest.ingest()` or `schedule` to any new module — that absence *is* the "not nightly" guarantee, and is asserted by tests.

### Boundary Changes

- **New public CLI surface**: `stockroom backfill`.
- **New config key**: `[cursor].state_vscdb`, plus `STOCKROOM_CURSOR_STATE_VSCDB` env override and a `--state-vscdb` flag.
- **No schema change**; no change to `ingest.ingest()`.

### Invariants & Constraints

1. `schedule.render_payload()` must continue to render exactly `stockroom ingest && stockroom embed`.
2. `ingest.ingest()` behavior and Cursor `_sync_state` watermarks must be unaffected.
3. Backfill never deletes or overwrites a session it did not create; composers already in the warehouse are skipped.
4. The writer stays the single SQL touchpoint for session persistence.
5. `state.vscdb` is opened strictly read-only; operator Cursor state is never mutated.
6. No truncation at rest.
7. Thinking/reasoning blocks are never stored.
8. Tool *results* are never stored; tool *inputs* are stored whole.
9. Session `*_tokens` only from Σ of nonzero allowlisted bubble `tokenCount`; message tokens NULL; `tokenCountUpUntilHere` / `contextUsagePercent` never mapped.
10. Fail-soft: absent, unreadable, or actively-written vscdb yields a clear message and nonzero exit — never a traceback.

## Open Questions

- [x] **OQ1 — How do bubbles become warehouse messages?** → Resolved: one *storable* bubble (non-empty text or a tool call) becomes one message; thinking-only and empty bubbles are dropped; tool calls stay on their own bubble-message rather than being merged into the preceding turn. See `memory-bank/active/creative/creative-vscdb-message-reconstruction.md`.
- [x] **OQ2 — What are `project_id`, `cwd`, `workspace_key`?** → Resolved: `project_id` = native `composerHeaders.workspaceId` (same hash-as-project_id precedent as Cursor CLI chats), `cwd` = folder resolved from `../workspaceStorage/{workspaceId}/workspace.json`, `workspace_key` left to the writer's existing derivation so vscdb sessions converge with same-`cwd` transcript sessions. See `memory-bank/active/creative/creative-vscdb-workspace-identity.md`.

## Decisions Taken In Plan (evidence-backed)

- **D1 — Read strategy: `mode=ro`, falling back to `immutable=1`.** Measured against the live 5.7 GB DB on the mount:

  | Open mode | Result |
  |---|---|
  | `file:…?mode=ro` | ❌ `disk I/O error` (WAL locking unsupported on the mount) |
  | `file:…?mode=ro&nolock=1` | ❌ `unable to open database file` |
  | **`file:…?immutable=1`** | ✅ 669,928 rows counted in 4.2 s |
  | copy 5.7 GB locally, then `mode=ro` | ⚠️ 60 s, and yielded `database disk image is malformed` when Cursor wrote mid-copy |

  `mode=ro` is correct where it works (local DBs, WAL respected); `immutable=1` is the only thing that works on the mount. Its caveat — the `-wal` tail is invisible, so the newest writes are not seen — is harmless for a historical backfill. Copying is strictly worse: slower *and* less reliable.
- **D2 — Key reads use index range bounds, never `LIKE`.** Measured on the mount for one composer's bubbles: `key >= 'bubbleId:{cid}:' AND key < 'bubbleId:{cid};'` → **0.05 s** (`SEARCH … USING INDEX`), vs `key LIKE 'bubbleId:{cid}:%'` → **2.88 s** (`SCAN`). SQLite will not use an index for `LIKE` under the default case-insensitive setting. This retires the "hybrid prefix vs full scan" pain recorded in the aborted `enhance-cursor-tokens` archive — that work was slow because it used `LIKE`.
- **D3 — Surface: a `stockroom backfill` subcommand in its own top-level module.** Rejected: a flag on `stockroom ingest` (puts legacy vscdb reads one typo from the nightly command) and a separate package (packaging cost, no user benefit).
- **D4 — Provenance: `entrypoint = 'ide'`, `source_path = <vscdb path>`.** `entrypoint` means *surface*, and these are genuinely IDE conversations; a third value would corrupt the column's meaning. `source_path` is what makes backfilled rows identifiable (and trivially reversible: one `DELETE … WHERE source_path = …`).
- **D5 — Selection: skip composers already in the warehouse; skip composers with zero reconstructable messages** (273 of 908 are empty drafts).
- **D6 — Tokens: session-grain Σ of nonzero allowlisted bubble `tokenCount` only**; message-grain stays NULL.

## Test Plan (TDD)

### Test Infrastructure

- Framework: `pytest` (+`pytest-xdist`, `-n auto`) configured in `skills/sr-search/pyproject.toml`.
- Test location: `skills/sr-search/tests/`.
- Conventions: one module per parser (`test_ingest_*.py`); module + per-test docstrings; assertions directly on `NormalizedSession` attributes; unreadable sources return `None`/typed errors rather than raising; orchestrator tests inject the `migrated_con` fixture; CLI tests run the real command as a subprocess with `STOCKROOM_HOME` pointed at `tmp_path`.
- New test files: `tests/test_ingest_cursor_vscdb.py`, `tests/test_backfill.py`, `tests/test_backfill_cli.py`.
- Modified: `tests/conftest.py` (vscdb-builder fixture), `tests/test_config.py`, `tests/test_dispatcher_cli.py`.
- Fixtures are **synthesized in-test** via a `build_vscdb(...)` conftest factory (composers, bubbles, headers, workspace.json), not committed as a binary — the shapes under test are numerous and a hand-built SQLite file keeps each case legible.
- The ingest golden snapshot (`fixtures/ingest/expected_rows.json`) is **not** extended: backfill is not part of the default corpus ingest.

### Behaviors to Verify

**Parser — identity & structure**

- Composer with bubbles → session with `harness='cursor'`, `session_id=<composerId>`, `entrypoint='ide'`, `source_path=<vscdb path>`.
- Bubble `type` 1/2 → message `role` `user`/`assistant`; unknown type → no message.
- Kept messages get dense 0-based ordinals and a linear `parent_ordinal` chain.
- Composer `name` → session `title`; absent → `None`.

**Parser — the OQ1 keep/drop contract**

- Bubble with non-empty text → message with that text stored whole.
- Bubble with only `thinking` → **no message**, and the thinking text appears nowhere.
- Wholly empty bubble → no message.
- Tool bubble (empty text + `toolFormerData`) → assistant message with one tool call.
- Tool bubble with text → message with text **and** tool call at `ordinal=1`; tool-only bubble → tool call at `ordinal=0`.
- Tool call carries `tool_name` from `name`, `source_tool_use_id` from `toolCallId`, and `tool_input` parsed from `rawArgs` (falling back to `params`, then the raw string).
- `toolFormerData.result` is **not** present anywhere in the emitted session.

**Parser — ordering & robustness**

- Order follows `fullConversationHeadersOnly`.
- Headers absent but legacy inline `conversation[]` present → messages come from the inline array.
- Header referencing a nonexistent bubble row → that entry is skipped, the rest survive.
- Corrupt (non-JSON) bubble value → skipped, rest survive.
- Composer with neither headers nor inline conversation, or with no storable bubbles → parser returns `None`.

**Parser — timestamps & tokens**

- Bubble ISO `createdAt` → message `ts` as naive UTC; session `started_at`/`ended_at` = min/max.
- No bubble timestamps → `started_at` falls back to `composerData.createdAt` (epoch ms); `ended_at` `None`.
- Bubbles with nonzero `tokenCount` → session `input_tokens`/`output_tokens` = sums; message tokens stay `None`.
- All-zero `tokenCount` → session token fields `None` (not `0`).
- `tokenCountUpUntilHere` present → ignored entirely.

**Parser — workspace identity (OQ2)**

- `composerHeaders.workspaceId` → session `project_id`.
- `workspace.json` `{"folder": "vscode-remote://wsl%2Bubuntu/home/u/p"}` → `cwd == "/home/u/p"`.
- `{"folder": "file:///tmp/p"}` → `cwd == "/tmp/p"`.
- Multi-root `{"workspace": …}`, missing file, missing `workspaceStorage` dir, or no `workspaceId` → `cwd is None`, no exception.
- Composer with no `composerHeaders` row → `project_id is None`.

**Parser — read ladder (D1)**

- A normal local DB opens via `mode=ro`.
- When `mode=ro` raises `sqlite3.OperationalError`, the reader retries with `immutable=1` and succeeds.
- A non-SQLite file raises the typed backfill error, not a bare `sqlite3` exception.

**Orchestrator**

- Composers absent from the warehouse are written: `sessions`, `messages`, `tool_calls` rows appear.
- A composer whose `session_id` already exists is skipped, and the pre-existing row is **byte-identical** afterwards (proves no delete-then-insert clobber).
- `_sync_state` is unchanged by a run (no rows added, existing watermark untouched).
- Running twice produces identical warehouse contents and a second summary reporting everything as skipped.
- Summary reports candidates / written / skipped-existing / skipped-empty plus message and tool-call counts.
- `--dry-run` writes nothing but reports what it would write.
- Absent vscdb path → typed error naming the flag, env var, and config key.

**Guard tests (encode the invariants)**

- `schedule.render_payload(home)` contains no `backfill` token.
- The `stockroom.ingest` package source contains no reference to `backfill` (no import edge onto the nightly path).

**CLI**

- `stockroom backfill --help` exits 0 and mentions `--dry-run`.
- End-to-end subprocess run against a synthesized vscdb writes rows into a `STOCKROOM_HOME` warehouse and prints a summary.
- Missing/unreadable vscdb → nonzero exit, one-line message, no traceback.
- Dispatcher lists `backfill` in top-level help and forwards to it.

### Integration Tests

- **Parser → writer → warehouse** (`migrated_con`): a synthesized composer round-trips into `sessions`/`messages`/`tool_calls` with correct `message_id` expansion and a writer-derived `workspace_key` matching a same-`cwd` session written by ordinary ingest (proves the OQ2 convergence claim).
- **Backfill alongside ingest**: run ordinary `ingest.ingest()` over the fixture corpus, then backfill; assert ingest-authored rows are untouched and watermarks unmoved.

## Implementation Plan

1. **Config key** — TDD cycle: `[cursor].state_vscdb`
    - Files: `src/stockroom/config.py`, `tests/test_config.py`
    - Changes: add `cursor_state_vscdb: Path | None` to `Settings`; extractor mirroring `_ai_tracking_dbs_from_table` (string → `Path.expanduser()`, invalid → `None`); never raise.
2. **vscdb reader + composer discovery** — TDD cycle
    - Files: `src/stockroom/ingest/cursor_vscdb.py` (new), `tests/test_ingest_cursor_vscdb.py` (new), `tests/conftest.py` (add `build_vscdb` factory fixture)
    - Changes: `open_readonly(path)` implementing the D1 ladder; `composer_ids(con)` and `composer_headers(con)` using D2 range bounds; module docstring recording the source shape and both creative decisions.
3. **Message reconstruction** — TDD cycle (the OQ1 contract)
    - Files: `src/stockroom/ingest/cursor_vscdb.py`, `tests/test_ingest_cursor_vscdb.py`
    - Changes: `parse_composer(con, composer_id, *, source_path, workspace_root)` → `NormalizedSession | None`; bubble ordering from headers with legacy-inline fallback; keep/drop predicate; tool-call extraction (result dropped); ISO timestamp parsing via `stockroom.timestamps`; token sums.
    - Creative ref: `creative-vscdb-message-reconstruction.md`
4. **Workspace identity** — TDD cycle
    - Files: `src/stockroom/ingest/cursor_vscdb.py`, `tests/test_ingest_cursor_vscdb.py`
    - Changes: `workspace_folder(workspace_root, workspace_id)` with URI decoding and memoization; wire `project_id`/`cwd` into `parse_composer`; leave `workspace_key` to the writer.
    - Creative ref: `creative-vscdb-workspace-identity.md`
5. **Orchestrator** — TDD cycle
    - Files: `src/stockroom/backfill.py` (new), `tests/test_backfill.py` (new)
    - Changes: `BackfillError`, `BackfillSummary`, `resolve_state_vscdb()` (flag → env → config), `backfill(*, state_vscdb=None, con=None, dry_run=False, on_progress=None)`; existing-`session_id` skip set; per-composer fail-soft; **no** `update_watermark` call; guard tests for the schedule payload and the ingest import edge.
6. **CLI + dispatcher** — TDD cycle
    - Files: `src/stockroom/backfill.py` (`main`), `src/stockroom/__main__.py`, `tests/test_backfill_cli.py` (new), `tests/test_dispatcher_cli.py` (ratchet)
    - Changes: argparse with `--state-vscdb`, `--dry-run`, `--verbose`; summary print; errors → exit 1 with a one-line remedy; add `backfill` to `SUBCOMMANDS` with a one-line summary; add name + `--dry-run` fingerprint to the dispatcher test.
7. **Documentation**
    - Files: `docs/user-guide/ingest.md` (new "Backfill legacy Cursor history" section: what it recovers, that the corpus is finite and the command is not scheduled, the `immutable=1` staleness caveat, the embed backlog it creates, and how to undo it), `docs/user-guide/installed-layout.md` (`[cursor].state_vscdb` in the config table), `docs/advanced/cli.md` (subcommand entry), `docs/architecture/lifecycle.md` (explicitly outside the nightly path), `docs/contributing/iteration.md` (subcommand list).

## Technology Validation

No new dependencies: `sqlite3` is stdlib (already used by `cursor_chats` and `enrich`), DuckDB and the writer already exist. Proof-of-concept executed against the live 5.7 GB DB during planning and recorded above as D1/D2 — open-mode ladder verified, index range-scan verified at 0.05 s per composer with `EXPLAIN QUERY PLAN` confirming index use.

## Challenges & Mitigations

- **The DB is written by a running Cursor while we read it**: torn or malformed reads are real (observed during planning). Mitigation: the D1 ladder plus per-composer `try/except` so one bad row cannot abort the run, and a top-level handler that reports "close Cursor and re-run" rather than a traceback.
- **Multi-GB DB on a slow 9p mount**: mitigated by D2 range bounds (0.05 s per composer ⇒ ~30 s for 609 composers) and by streaming per composer instead of loading all bubbles.
- **Corpus roughly doubles**: ~60k new messages against 43,892 today, so the next `stockroom embed` will run far longer than usual. Mitigation: backfill never embeds; the docs state the expectation explicitly.
- **No discoverable default path on WSL→Windows**: mitigated by three explicit inputs (flag, env, config) and an error message naming all three.
- **A buggy skip set could clobber ingest-authored rows** (the writer deletes by `(harness, session_id)`): mitigated by the byte-identical-after-skip test.
- **Composer ids share a namespace with agent-transcript session ids** — that is *why* 1,131 already match. This is a feature: it makes "skip existing" exact rather than heuristic.

## Pre-Mortem

- **We backfilled ~900 sessions and the operator wants them gone.** No undo exists in the plan. Response: `--dry-run` is in scope (step 6), and the docs must document the one-line reversal (`DELETE FROM … WHERE source_path = '<vscdb>'`), which D4 makes exact.
- **A composer backfilled today later shows up in agent-transcripts and duplicates.** It cannot: both write the same `session_id`, and the writer's delete-then-insert means ordinary ingest simply supersedes the backfilled row with the higher-fidelity transcript version. Recorded as an insight rather than a plan change.
- **The premise is wrong because those 908 composers are junk.** Partly true and already handled: 273 are empty drafts and D5 skips them. The remaining 635 have a median of 28 bubbles, which is real conversation.
- **`immutable=1` silently returns a stale snapshot and we under-backfill.** Accepted and bounded: what is missing is the WAL tail, i.e. the newest activity, which ordinary ingest already covers. Re-running the one-shot picks it up later; idempotency makes that safe.
- **Ceremony exceeds the payoff — this could have been a script.** Rejected on the operator's explicit "no code golf, good-quality software" instruction, and because the thing writes to the shared warehouse: skip-set correctness and watermark isolation are exactly where a throwaway script would do damage.

## Status

- [x] Component analysis complete
- [x] Open questions resolved
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [ ] Preflight
- [ ] Build
- [ ] QA
