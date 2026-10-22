---
task_id: warehouse-file-growth
date: 2026-10-22
complexity_level: 3
---

# Reflection: Drop the HNSW index and remove vss from the engine (warehouse-file-growth, milestone 1)

## Summary

Migration `0009` drops the HNSW index, `0003` is retired, the engine loads no `vss`, and semantic search is one exact path. The build was proved on a copy of this machine's 43 GB warehouse, then landed, and the live warehouse was migrated and verified. QA passed with two advisories, neither blocking.

## Requirements vs Outcome

Every item of milestone 1's done list was delivered: the drop migration, the retired `0003`, no `vss` anywhere in the engine, the exact dedup-first search for every scope, B1 to B16, the docs and context, the shadow strip, the live-copy proof, and `make ci` on DuckDB 1.5.4. Nothing was descoped.

Two additions beyond the plan: a byte diff showing that the landed `src` matches the code the proof ran, and a tie analysis of the harness-scope results. The docs go one step further than the plan's wording: they say "vector index" and do not name HNSW or `vss`, following the operator's instruction to strip everything about the index except the migration that drops it.

## Plan Accuracy

The six steps, their order, and the file list held. Two small removals were added to the shadow strip (`LOCK_ERROR` and the child prelude's `one_line`, which only deleted code used). One docstring reword moved from step 4 to step 3, because the snapshot it described changed there.

The risks the plan named were the right ones: the live working tree, writes failing against an unbound index, and same-process DuckDB instance sharing in the tests. None of them caused trouble, because the plan's landing order and child-process fixtures handled them.

The surprises came from elsewhere:
- **The engine venv had no torch.** The pre-commit hook's exact sync removes it on this machine. The proof's `stockroom semantic` step needs the real model, so the build ran `stockroom shim ensure-env` first. The plan did not mention it.
- **The proof script had a bug.** DuckDB's Python client drew a progress bar on the child's stdout during the long `EXCEPT ALL` queries, which broke the JSON parse. The script was fixed and resumed from that check on the already-migrated copy.
- **The new and old statements returned different sets under `--harness claude`.** Planning had compared shapes with one sampled query vector and seen the same 100 owners. Eight vectors showed that every difference sat exactly at the cut distance, and that the nearer-than-cut sets were equal. The live data has many identical vectors (one sample had 150 owners at distance 0), so ties at the cut are common.
- **The session hit its usage limit mid-step 4.** That was after the proof and before the landing. The build stopped there, wrote a handoff, and resumed cleanly.

## Creative Phase Review

No creative phase ran. The plan settled its three open choices (statement shape, orphan guard, `0003`'s filename) from measurements and operator decisions, and all three held in build.

## Build & QA Observations

Went well:
- The TDD red runs failed for the reasons the plan predicted: step 1 (B1, B2), step 3 (24 failures on the `vss`-only `SET`), and step 4 (16 failures).
- The child-process fixtures (v2.1.2 chain builder, killed embed, killed migrator) worked on the first run.
- The landing itself took one command, and the live migrate took 0.9 s.

Took iteration:
- Only the proof script's stdout parsing.

QA findings:
- No defects.
- Advisory: dead leftovers in the shadow script, which milestone 2 owns.
- Advisory: `_vss_loaded` and `_non_primary_indexes` are duplicated across two test modules.

## Cross-Phase Analysis

- **Preflight advisory 1 decided the landing's safety.** It said to write `0009` before removing `ensure_vss`, and the calls before the function. That removed every unsafe in-between state. As a result, the usage-limit interruption could only matter at one point, and the build stopped before it.
- **Planning measured with too few query vectors.** "Every shape returned the same 100 owners" came from one sampled vector, and it surfaced in build as an unexplained set difference. The cost was one extra script and one open item, not a defect, because the tie-break was already in the plan.
- **The radical advisory (build in a worktree) was declined.** Its main benefit was that the proof runs the exact code that lands. `land.py` delivered that benefit in place: one transformation, applied first to a scratch copy and then to the checkout, with a byte diff between them.

## Insights

### Technical
- To remove a capability that existing on-disk state depends on (here, `vss` for a file with an HNSW index), land the migration that removes the dependency first, then remove the capability. Every state in between still works, so an interruption cannot break a live install.
- To compare two rankings on real data, compare the owners strictly nearer than the cut, and treat owners at the cut distance as ties. Use several query vectors. This history has many identical messages, so ties at the cut are common, and a single-vector "same set" check gives false alarms.
- DuckDB's Python client draws a progress bar on stdout for long queries. A child process whose stdout is parsed needs `SET enable_progress_bar = false`.
- A drop on a fresh, cold copy can take far longer at close than the same drop on the live file: 19.6 s against 0.9 s here. Timings measured on a fresh copy are an upper bound.

### Process
- When the working tree is live, make the landing one scripted command, and run the same script against the proof copy first. Then an interruption can only fall before or after the landing, and a byte diff proves that the proved code is the code that landed.
- Before a proof that runs the real encoder, check that the engine venv has torch. On this machine every commit's pre-commit sync removes it.
