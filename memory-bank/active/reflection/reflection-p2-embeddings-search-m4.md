---
task_id: p2-embeddings-search-m4
date: 2026-06-30
complexity_level: 2
---

# Reflection: `sr-query` skill

## Summary

Authored `skills/sr-query/SKILL.md` — the safe, LLM-ergonomic wrapper over the existing read-only SQL surface (`python -m stockroom.query`) — covering routing, the engine-invocation contract, `--format`/`--detail` output discipline, guardrails, an introspection-first schema map, and verified worked examples. Succeeded; the build also surfaced and corrected a real, repo-wide bug in the documented engine-invocation contract.

## Requirements vs Outcome

Delivered every milestone requirement: when/how to use, `--format`/`--detail` guidance, context-blowout + wasted-tool-call guardrails, `--detail full` escalation, and `--format table`/`json`-on-request. Helper `scripts/` were explicitly (and correctly) deferred — the surface is a single command behind the resolution preamble, so prose sufficed. One unplanned addition earned its place: a `tool_input` JSON-extraction guardrail (`json_extract_string` over a `tool_name`-filtered subquery), discovered when the naive `->>'key'` form cast-errored across heterogeneous tool shapes.

## Plan Accuracy

The 7-step plan was accurate and well-sequenced; no reordering needed. The preflight amendment (introspection-first schema map) paid off — it both future-proofs the skill against new migrations and pre-empted the "example drift" challenge. The one real surprise came from outside the plan's anticipated challenges: the engine-invocation contract documented across `sr-search/SKILL.md`, `systemPatterns.md`, and the README is **incomplete** (`package = false` ⇒ `stockroom` not on `sys.path` ⇒ bare `python -m` fails). The plan assumed "copy the contract faithfully"; faithfully copying a broken contract would have shipped a broken skill. Verifying examples live (the plan's own mitigation) is exactly what caught it.

## Build & QA Observations

Build was smooth: a live 380 MB warehouse let me execute every example before writing it in, so QA found zero accuracy issues. The friction was entirely the invocation-contract discovery — three probes (`--directory`, `PYTHONPATH`, CWD-in-`src`) to pin the working form. QA was clean (no trivial fixes, no rework). Running `make ci` strips out-of-band torch as a side effect; restoring with the freshly-added `make torch` target closed the loop without leaving the environment degraded.

## Insights

### Technical
- **`package = false` projects need `PYTHONPATH=<dir>/src` for `python -m` invocation.** pytest hides this via `[tool.pytest.ini_options] pythonpath`, so the gap stayed invisible until a non-test caller (this skill) ran the module directly. Any future doc or skill that invokes the engine must carry `PYTHONPATH="$APP_DIR/src"`.
- **DuckDB `tool_input->>'key'` is unsafe on heterogeneous JSON** — the planner may evaluate the extraction on a wrong-shaped row and raise a cast error. Filter `tool_name` in a subquery and use `json_extract_string`.

### Process
- **"Copy the existing contract faithfully" is only safe if the existing contract is verified.** The plan trusted three docs that agreed with each other and were all wrong. Live verification (already a plan step for examples) is what saved it — worth making "verify the invocation, not just the examples" an explicit early step for any skill that shells out.

### Million-Dollar Question

Had "the engine is invoked by external callers, not just pytest" been a foundational assumption, the project would have given the engine a **single canonical entrypoint** — either `[project.scripts]` console scripts (so `package = false` is reconsidered) or one committed launcher (`scripts/sr` resolving `APP_DIR` + `PYTHONPATH` once) that every skill and the README/`systemPatterns` reference. Instead the run incantation is copy-pasted prose in N places, which is exactly how it drifted into being wrong in N places at once. The next wrapper skills (`sr-semantic`, `sr-search`) will re-paste the same preamble; a shared launcher is the obvious consolidation, and the `sr-search` skill (which delegates to siblings) is the natural place to force the question.
