# Current Task: pr-14-docs-review-rework

**Complexity:** Level 1

## Fix

**What broke:** Two CodeRabbit review comments on PR #14 — misleading torch-safe `uv` examples and ambiguous ingest/storage wording.

**Why:** (1) Short `uv run` / `uv sync` forms in `docs/development.md` looked like repo-root commands but need `--project skills/sr-search` and `PYTHONPATH` for `python -m stockroom…`. (2) `systemPatterns.md` said “tool inputs only, no outputs,” which can be read as omitting assistant responses, contradicting `productContext.md` and the ingest code (`tool_result` dropped; prompts/responses kept).

**What changed:** Expanded the torch-safe examples to the full repo-root form; rewrote the ingest sentence to name `messages`, `tool_input`, and `tool_result` explicitly.

**Files affected:**
- `docs/development.md`
- `memory-bank/systemPatterns.md`
