# Brainstorm — Implementation Details

Concrete reference facts gathered from the two prior tools and this environment, framed as **reuse / fix / avoid**, plus the clean-room boundary and the open technical questions. Feeds the Tech Brief and the build.

## Clean-Room Boundary (read first)

- **`cursor-warehouse`** is the operator's own work (currently MIT). We **may freely port, adapt, and relicense** its original code into stockroom under AGPLv3. Concrete patterns below are fair game to reuse.
- **`claude-warehouse`** is third-party MIT (by Stéphane Derosiaux). We must **NOT copy its code, its schema DDL, or its unique/novel ideas** — only generally-public, commonplace concepts that would appear in any such tool. All `claude-warehouse` notes below are deliberately conceptual and limited to commonplace patterns.
- Note: `cursor-warehouse` is itself a port of `claude-warehouse`. When porting from `cursor-warehouse`, prefer reimplementing anything that is obviously a thin transliteration of the upstream MIT code, to keep the clean-room boundary honest.

## Reuse (from the operator's `cursor-warehouse`)

- **DuckDB + VSS + HNSW** vector stack; cosine metric; `SET hnsw_enable_experimental_persistence = true`; reinstall/load VSS so deletes work with a live index.
- **Embedding approach:** `all-MiniLM-L6-v2` (384-dim, `FLOAT[384]`), chunk long text (~800 chars, ~100 overlap), mean-pool to one vector.
- **Incremental sync** via per-source watermarks `(last_mtime, last_path)`; `--full` to reset; silent, graceful exit when the DB is locked by a concurrent run.
- **General normalized shape** (a `sessions` / `messages` / `tool_calls` / `embeddings` split plus a watermark table, all `harness`-labeled) is a commonplace pattern to reproduce **independently** — design ours fresh from the two harness formats (D20), not by transliterating reference DDL, and extend it with subagent↔parent linkage, model-per-chain, a harness-labeled **plan-documents** table, and explicit **conversation-reconstruction** keys (D21).
- **Message identity contract:** message UUID = `{session_id}:{line_idx}`, relied on by embed/search. Keep an explicit, stable identity contract.
- **Torch handling:** the user-level `~/.config/uv/uv.toml` `[[index]]` → `download.pytorch.org/whl/<accel>` pattern, plus a torch/CUDA **smoke test** script. This is the seed of the D6/O9 solution (torch outside the lock).
- **Cursor source layout:** `~/.cursor/projects/<workspace-slug>/agent-transcripts/<session-id>/<session-id>.jsonl`; subagents under `.../subagents/`; the SQLite `~/.cursor/ai-tracking/ai-code-tracking.db` with a WSL mount fallback (`/mnt/<drive>/Users/*/.cursor/...`).
- **Read-only dashboard access** with retry/backoff against DB locks.

## Fix (improve on `cursor-warehouse` in stockroom)

- **Add the lockfile.** This is the entire reason stockroom exists as a separate, productized tool (D5).
- **Don't truncate stored content (D19).** The references hard-cap fields (see Empirical Findings); stockroom stores the fields it keeps in full, and truncates only at *read* time (context-aware).
- **Richer linkage than the references (D21).** Add subagent↔parent linkage, model-per-chain, harness-specific plan documents, and explicit conversation-reconstruction keys — *without* storing a verbatim raw copy or tool outputs (ETL into our schema, not mirroring).
- **Add a real migration system** (D12) — `cursor-warehouse` has none (only idempotent `CREATE TABLE IF NOT EXISTS` plus one ad-hoc `ALTER`).
- **Harness-neutral DB location** (O1 resolved → `~/.stockroom/`) — don't bury it under `~/.cursor/`.
- **Nightly scheduled freshness** as the primary mechanism (D14), rather than leaning on a session-start hook to sync.
- **Fix the dashboard port inconsistency** — `cursor-warehouse` binds `3142` but the launcher/docs reference `3141`, which causes duplicate processes and stale URLs. Pick one port, probe it correctly.
- **Vendor front-end assets** (O6) instead of pulling Chart.js from a CDN — offline-capable and consistent with the no-injection ethos.

## Avoid / Decide Later (conceptual, from `claude-warehouse`)

- `claude-warehouse` tracks **more entity types** conceptually (hook events, todos, debug-log metadata, research/markdown history, deleted-session tombstones, per-file byte offsets for tail-ingest). These are **out of v1**; revisit only if a real need appears. Do not import its DDL.
- Its **dashboard-auto-runs-while-coding** behavior is what the operator found excessive; stockroom's session-start launch is deliberately lighter (idempotent, fire-and-forget) and freshness is handled by the nightly job instead.
- Its **uvx/loose-PEP723, no-lockfile** dependency model is the explicit anti-pattern stockroom corrects.

## Empirical Findings (measured 2026-06-22)

Queried the operator's live `cursor-warehouse` DuckDB (`~/.cursor/cursor-warehouse.duckdb`, ~144 MB, ~24.7k messages) and the source JSONL via `cw-query` plus a scan script.

- **Truncation caps (storage, not just display):** `messages.text_content` and `messages.user_query` max out at exactly **2000** chars; `tool_calls.tool_input` at exactly **500**; the longest values in each are all *exactly* the cap. Tool outputs/results have no column at all — which stockroom matches deliberately (we capture tool *inputs* only); the harm to fix here is the **content truncation**, not the dropped outputs.
- **Impact:** ~**17%** of messages exceed 2000 chars and were truncated.
- **True sizes (source JSONL, 706 transcripts, 24,751 events, ~37 MB):** record length median ~514 chars, p95 ~6 KB, p99 ~14 KB, p99.9 ~46 KB, **max ~202 KB**; largest single atomic string field ~**202 KB**; nothing over 1 MB.
- **DuckDB limits (confirmed via docs):** `VARCHAR` has no length limit (4 GB ceiling, UTF-8); specifying a length does nothing; DB files scale to terabytes. Large strings only hurt when *sorted/joined/filtered on*, so keep big blobs out of join/order keys and chunk for embedding — but store them whole.
- **Conclusion:** untruncated capture is cheap and safe in DuckDB; the references' truncation was a choice, not a constraint.

## Environment Facts (this machine)

- Two git roots: `/home/mobaxterm/git` (fast, **WSL-internal**, lost if WSL is removed) and `/home/mobaxterm/Documents/git` → `/mnt/v/users/Austin/Documents/git` (a **slow Windows-visible mount**). **We build stockroom only in the fast WSL-internal root** (D18).
- The existing `cursor-warehouse` nightly cron is pinned to the *slow* `Documents` path (legacy install location) and stays there; irrelevant to stockroom dev but a live example of the **absolute-path-resolution hazard** the scheduler install must handle on real user machines.
- This is WSL (no `launchd`); Linux scheduling = cron. macOS support = launchd. The skill must detect platform and resolve paths accordingly.

## Distribution Facts (from `slobac`)

- Dual manifests: `.cursor-plugin/plugin.json` (includes `displayName`, `category`, explicit `"skills": "./skills/"`) and a slimmer `.claude-plugin/plugin.json`. Shared top-level `skills/<name>/SKILL.md`. **No build step; committed layout = install layout.**
- Versioning via **release-please** (`release-please-config.json` + `.release-please-manifest.json`), syncing the version into both `plugin.json` files on release.
- Marketplace is a **separate repo** (`txrk9-agent-plugins`) with `.cursor-plugin/marketplace.json` + `.claude-plugin/marketplace.json` entries pointing at the GitHub source repo. Users add that marketplace URL, then install the plugin.
- Invocation differs by harness (Cursor `/<skill>` vs Claude `<plugin>:<skill>`); verify the exact `/sr-*` forms empirically.
- Dev rules under `.cursor/` are **not** shipped as plugin payload.

## Open Technical Questions

All README Open Items are **resolved except O9** (see `README.md` for the full resolution table). The technically-framed items that still need work during the Tech Brief / build:

- **O9 (torch) — the one genuine spike.** Mechanism for "lock everything except torch." Candidates: uv `required-environments`/environment markers, optional dependency groups excluded from the default lock, an `explicit = true` torch index, or torch declared as externally provided. Must keep `sentence-transformers` working. **Gates embedding work; first task of the TB.**
- **Migration lock primitive** on DuckDB (advisory lock table vs file lock) and exact wait/backoff semantics for readers during a migration. (Implementation detail, not a scope decision — settle during the migration build.)
- **Both-harness ingest (O12 resolved → both):** v1 parses Cursor *and* Claude Code. Claude Code's native on-disk format must be enumerated and parsed **clean-room** — reverse-engineering the *harness's* format (a public on-disk artifact), **not** reusing `claude-warehouse`'s parser or schema DDL.
- **Schema field enumeration (D20/D22):** the concrete first build step — point an agent at real Cursor and Claude Code logs, list the exposed fields, and lock the table design (core fields + subagent↔parent linkage + plan documents + reconstruction keys). Use `cursor-warehouse`'s schema freely; do **not** use `claude-warehouse`'s.
