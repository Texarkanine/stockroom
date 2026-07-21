# The Stockroom System Model

How the system is put together: engine packaging, the invocation contract, and the data doctrines that shape what queries and searches can see. Skills hold the *do* — operational rules, flags, and error recoveries live there, not here. Read this when you need to understand or debug the system, not to run it.

## One Engine, One Command

All `sr-*` skills share a single Python engine that lives in the `sr-search` skill directory (`src/stockroom/`) — the sibling skills have no Python of their own. Every invocation goes through the on-path `stockroom` command: a small generated shim (installed by `sr-initialize` to `~/.local/bin/stockroom`) that owns the entire invocation contract — engine-directory resolution, `PYTHONPATH`, and the uv flags — in exactly one place, then dispatches to the engine's subcommand modules. The shim is **baked-only and succeed-or-refuse**: it never scans or re-resolves at runtime. After a plugin update moves the install directory, the harness session/workspace hook runs `stockroom shim rectify`, which re-bakes the owned shim's `APP_DIR` and ensures the engine's locked uv environment (torch-safe inexact sync). Until that heal runs, a stale or empty env refuses with a one-line remedy naming `sr-initialize` / a new session.

The shim is the *only* holder of that contract. Skills carry **no fallback incantation**: if `stockroom` is not on `PATH`, the machine is not initialized, and the only correct next action is to run `sr-initialize`.

## Run-in-Place Packaging

The engine is not an installed Python package: `[tool.uv] package = false`, no build step, no console-script entry points. The committed repository layout **is** the install layout — what the plugin manager copies to disk is exactly what runs. Consequently `stockroom` is never on `sys.path` by installation; making it importable is part of the invocation contract the shim owns.

## The Torch Contract

Torch is required for embedding (writing vectors, and encoding queries at semantic-search time) but is **held out of the dependency lock**: the correct torch build is a per-machine choice (CUDA generation, CPU, MPS) that no single lockfile can make. It is provisioned out-of-band by `sr-initialize`, and every run avoids an exact dependency sync, because an exact sync removes anything not in the lock — including the provisioned torch.

A missing torch is therefore an *environment* problem, never a query problem: no amount of retrying, rephrasing, or reformatting a call can bring torch back. The fix is re-provisioning (re-run `sr-initialize`), and the skills' error tables route there.

## ETL, and Read-Only by Construction

The warehouse (a single-file DuckDB database) is rebuildable ETL output: ingestion re-derives it from the harnesses' own session records, so it is never the system of record. The read surfaces (`query`, `semantic`) open it read-only at the connection level — DuckDB itself rejects any write attempted through them. "You cannot corrupt anything by querying" is a property of the connection mode, not of good behavior.

Cursor Agent CLI chats (`store.db`) are parsed best-effort: locked, corrupt, or layout-drifted stores skip that session and leave the chats watermark unadvanced so a later ingest can retry — they do not abort the whole Cursor batch. Empty/meta-only stores still land as sessions with zero messages. Fixture tests fail loudly when the known root-hash layout changes; production ingest does not.

## No Truncation at Rest

Everything is stored whole: full message text, full tool inputs. Truncation happens only at *read time*, as a display bound that keeps one fat column from flooding an agent's context window. The elision marker (`…(+N)`) reports exactly how much was withheld, which is what makes the scan-narrow-then-refetch pattern safe: the full content is always still there, one targeted re-fetch away. `--detail full` is unbounded but still single-line (table/TSV-safe); `--format json --detail raw` is the exact-whitespace escape hatch when newlines must match storage.

## Embedding Pipeline and Staleness

Semantic search only sees what has been embedded, and embedding is a separate, heavier pass than ingestion (it needs torch and real compute). The two are allowed to lag: ingestion may have captured recent sessions whose messages have no vectors yet. This is the *silent staleness* failure mode — recent content that exists in the warehouse but is invisible to semantic search — and it is why weak semantic results for recent work warrant a coverage check before concluding the content is absent.

Re-ingest invalidates embeddings only for removed or text-changed messages — unchanged history keeps its vectors, so embed lag after ingest is a small hole rather than a wiped session.

Messages are embedded as one or more chunks (long messages get several vectors); search embeds the query with the same local model, runs cosine KNN over an HNSW index, and dedups chunks back to messages. Scores are cosine similarity — meaningful only *relative to each other within one query*, which is why thresholding on an absolute score is unsound. The model is asymmetric: stored passages and incoming queries get different prefixes, applied automatically by the engine on each side.

## Identity and Provenance

The warehouse imposes one uniform identity scheme across harnesses: `(harness, session_id)` for sessions, `message_id = '{session_id}#{ordinal}'` for messages. The harnesses' own native identifiers (e.g. Claude's `uuid`) are demoted to `source_*` provenance columns — kept for traceability, never used as join keys, because they exist at different grains and formats per harness. The same honesty applies to per-harness fields: a value that only exists for one harness is `NULL` for the other, never fabricated.
