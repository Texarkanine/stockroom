---
task_id: semantic-lookup-ids
date: 2026-10-02
complexity_level: 2
---

# Reflection: semantic-lookup-ids

## Summary

Every `stockroom semantic` shape now prints `session_id` and `message_id`, and the skill plus CLI page tell you to query with the ids already printed. QA passed with no rework.

## Requirements vs Outcome

The brief's four acceptance criteria are met. Default `tsv` and `table` carry the identifiers; JSON still does; the handoff no longer starts with a second semantic run. Nothing was added. The preflight advisory (a neighboring-turn SQL recipe) stayed out.

## Plan Accuracy

The plan named the right files: `render.py`, the two test modules, `skills/sr-semantic/SKILL.md`, and `docs/advanced/cli.md`. Column order matching the existing JSON fields held. The challenges that mattered were the ones named: do not switch the default format to JSON, and do not leave the docs teaching the two-step. No surprise files turned up. Empty-table coverage was folded into `test_semantic_table_includes_lookup_ids` instead of a separate function.

## Build & QA Observations

The tests went red for the missing columns, then green after the tuple and both row builders were updated. `make lint` was clean. `make test` was 870 passed, 4 skipped, plus 134 dashboard JS tests. QA re-ran that gate and found no defect. The pre-existing parallel `tsv` and `table` row lists were extended in the same order; QA treated that as existing structure, not a new duplication.

## Insights

### Technical
- The identifiers were already on `SemanticHit` and already in the JSON object. The gap was `_SEMANTIC_COLUMNS` plus two documents that said JSON was where the ids lived.

### Process
- When the complaint is "I have to run it again with a different flag," search the skill and the human docs for the sentence that prescribes that second run. A renderer-only fix would have left the documented workflow in place.

### Million-Dollar Question

If lookup ids had been a foundational assumption, one ordered field list would have driven `tsv`, `table`, and JSON, so a shape could not grow an identifier the others lack. What shipped is the small version of that: the shared column tuple and the JSON keys are the same order, and the two row lists were updated together. Unifying the row builders was not required to make the contract true.
