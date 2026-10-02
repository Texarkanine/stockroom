# Task: semantic-lookup-ids

* Task ID: semantic-lookup-ids
* Complexity: Level 2
* Type: simple enhancement

Every `stockroom semantic` shape (`tsv`, `table`, `json`) prints `session_id` and `message_id` so a hit can be opened with `stockroom query` without a second search. Default stays `tsv`. Preview truncation stays read-time only.


## Test Plan (TDD)

### Behaviors to Verify

- Default and explicit `tsv`: `format_semantic` with no `fmt`, and with `fmt="tsv"`, leads with `rank\tscore\tharness\tsession_id\tmessage_id\trole\tpreview`, and the data row contains that hit's `session_id` and `message_id` → header and values match; no `(N result` trailer and no ` | `.
- Table: `format_semantic(..., fmt="table")` → header and the data row include `session_id` and `message_id`; the `(N results)` trailer stays.
- JSON regression: `format_semantic(..., fmt="json")` → each result still has `session_id` and `message_id` (existing `test_semantic_json_shape`).
- CLI default: `semantic.main` with no `--format` on a warehouse row `s1` / `s1#0` → stdout header matches the new tsv header and the row contains `s1` and `s1#0`.
- Empty tsv: `format_semantic([], fmt="tsv")` → the header line alone, including `session_id` and `message_id`.
- Empty table: `format_semantic([], fmt="table")` → header names `session_id` and `message_id`, plus `(0 results)`.
- Elision does not eat identifiers: a hit whose text is far over the snippet budget → `session_id` and `message_id` appear verbatim, and the preview still contains the elision marker.
- Score regression: a zero-distance hit → tsv still shows `1.000`. `-k` still prints one header line plus one line per row.

### Test Infrastructure

- Framework: pytest (engine `addopts` include `-n auto`; override with `-n0` when iterating one test)
- Test location: `skills/sr-search/tests/`
- Conventions: `test_*.py`, function names `test_*`, a docstring on each test stating the behavior. Render tests build `SemanticHit` via `_hit`. CLI tests call `semantic.main(..., encoder_factory=FakeEncoder)` against `warehouse_home`.
- New test files: none

## Implementation Plan

### 1. Semantic render identifiers — executable

- Files: `skills/sr-search/tests/test_render.py`, `skills/sr-search/tests/test_semantic.py`, `skills/sr-search/src/stockroom/render.py`

1. Stub tests: In `test_render.py`, add empty `test_semantic_tsv_includes_lookup_ids`, `test_semantic_tsv_empty_header_includes_lookup_ids`, `test_semantic_tsv_lookup_ids_survive_preview_elision`, and `test_semantic_table_includes_lookup_ids`, each with a docstring and a body of `pass`. In `test_semantic.py`, add empty `test_cli_default_tsv_includes_lookup_ids` the same way. Leave the existing header assertions untouched until the next substep.
2. Stub interface: none. `SemanticHit.session_id` and `SemanticHit.message_id` already exist. `format_semantic`'s signature stays.
3. Write tests and run red: Fill the new tests and update `test_semantic_tsv_header_and_no_trailer`, `test_cli_prints_ranked_results`, and `test_cli_default_output_is_tsv` to the behaviors above. Column order is `rank`, `score`, `harness`, `session_id`, `message_id`, `role`, `preview` (same order as today's JSON fields; `preview` stays the wide last column; JSON keeps the field name `text`). Run the new and updated tests. They fail because `_SEMANTIC_COLUMNS` is still `("rank", "score", "harness", "role", "preview")`.
4. Write code and run green: Set `_SEMANTIC_COLUMNS` to that order. Include `hit.session_id` and `hit.message_id` in the tsv row and the table row, between harness and role. Update the `format_semantic` docstring so it no longer says only JSON carries the identifiers. Do not change the JSON payload, score formatting, truncation, or the default format. Re-run the semantic render and CLI tests, then `make test` from the repo root.

### 2. One-search handoff docs — prose/policy

- Files: `skills/sr-semantic/SKILL.md`, `docs/advanced/cli.md`
- No tests: prose/policy artifact

1. In `skills/sr-semantic/SKILL.md`, put `session_id` and `message_id` on the default `tsv` header description. Stop saying JSON is where the identifiers appear. The full-text handoff takes `message_id` from the results already printed, then `stockroom query`. Update the worked examples that re-run `--format json` only to obtain an id.
2. In `docs/advanced/cli.md`, rewrite the "The Default was for Agents" tip so it no longer says only `--format json` carries a foreign key. Keep the separate advice that previews are truncated and that `--format json --detail raw` is how a human gets exact stored text.

## Technology Validation

No new technology - validation not required

## Dependencies

- None. Identifiers are already joined onto `SemanticHit` in `stockroom.semantic.run_semantic_search`.

## Challenges & Mitigations

- Positional tsv consumers: inserting columns changes the header and shifts `role` and `preview`. Mitigation: this is the requested contract change. Put the new columns in the JSON field order so the three shapes agree, and keep `preview` last.
- Docs that re-teach the two-step: `skills/sr-semantic/SKILL.md` and the tip in `docs/advanced/cli.md` ("nothing that works as a foreign key … except with `--format json`"). Mitigation: step 2 updates both. Do not change `docs/advanced/cli.md`'s truncation advice into a claim that the default is now full text.
- Untracked `.cursor/skills/stockroom-local/` mirrors engine files. Mitigation: edit only `skills/` and `docs/`. Do not touch that tree.
- TSV escaping: a tab inside an id would split a row. Mitigation: do not add an escaping layer. `message_id` is `{session_id}#{ordinal}`; do not invent quoting.

## Pre-Mortem

- The plan "succeeds" by switching the default format to JSON, which keeps identifiers but breaks the stream-friendly default the skills and pipes rely on. Response: step 1 keeps `DEFAULT_FORMAT` as `tsv` and only adds columns. A test that default `format_semantic` equals explicit `tsv` already exists (`test_semantic_defaults_to_tsv`); the new default-header assertion locks the columns onto that shape.
- The plan updates the renderer and leaves the agent skill telling operators to re-run `--format json` for ids, so the UX the operator complained about survives in the instructions. Response: step 2 is required, not a follow-up, and it names both the skill and the human CLI page that state the old rule.
- Already covered by the positional-consumer challenge: putting the ids in a different order per format, so a reader cannot move between shapes.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [ ] Build
- [ ] QA
