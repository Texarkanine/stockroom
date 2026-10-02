---
task_id: semantic-lookup-ids
complexity_level: 2
date: 2026-10-02
status: completed
---

# TASK ARCHIVE: semantic-lookup-ids

## SUMMARY

Every `stockroom semantic` shape now prints `session_id` and `message_id`, so a hit can be opened with `stockroom query` without a second search. The default stays `tsv`. Preview truncation is unchanged. QA passed with no rework.

## REQUIREMENTS

- `tsv`, `table`, and `json` each include `session_id` and `message_id`.
- Those fields are enough to look the conversation up with `stockroom query`.
- `sr-semantic` no longer says to re-run semantic as JSON just to obtain the ids.
- Truncation stays read-time. `stockroom query` itself does not change. Ranking, scores, and preview detail stay as they were.

## IMPLEMENTATION

`_SEMANTIC_COLUMNS` in `skills/sr-search/src/stockroom/render.py` is now `rank`, `score`, `harness`, `session_id`, `message_id`, `role`, `preview`. The `tsv` row and the table row insert `hit.session_id` and `hit.message_id` in that order. JSON already had the same keys and was left alone. `preview` stays the wide last column.

`skills/sr-semantic/SKILL.md` and `docs/advanced/cli.md` describe a one-search handoff: take `message_id` from the results already printed, then query. `--format json --detail raw` remains the way to get exact stored text.

After reflection, CI went red because unpinned `setup-uv` installed uv 0.12.22, and `uv lock --refresh` rewrote the root lockfile revision. The root `uv.lock` revision is now 5, and both workflows pin uv to 0.12.22. The engine lock consumers sync is still revision 3. Bump that pin only in the same commit that regenerates the locks with that exact uv.

## TESTING

New and updated cases in `skills/sr-search/tests/test_render.py` and `skills/sr-search/tests/test_semantic.py` cover the default `tsv` header and row, empty `tsv`, elision leaving the ids intact, the table header and empty table, and the CLI default. Existing `test_semantic_json_shape` still guards JSON. The new tests failed on the old columns, then passed after the renderer change.

`make lint` was clean. `make test` was 870 passed, 4 skipped, plus 134 dashboard JS tests. `/niko-qa` re-ran that gate and passed. The docs build and the engine job passed again after the lock revision bump and the uv pin.

## LESSONS LEARNED

The identifiers were already on `SemanticHit` and already in the JSON object. The gap was `_SEMANTIC_COLUMNS`, plus `sr-semantic` and the CLI page saying JSON was where the ids lived. A renderer-only fix would have left the documented two-step in place.

When the complaint is "I have to run it again with a different flag," search the skill and the human docs for the sentence that prescribes that second run.

## PROCESS IMPROVEMENTS

Search the docs that teach a workaround before changing the command they describe.

Pin CI's uv. `uv lock --refresh` rewrites the lockfile revision to the running uv's format, and an unpinned `setup-uv` will adopt that format on the day of a release.

## TECHNICAL IMPROVEMENTS

One ordered field list could drive `tsv`, `table`, and JSON, so a shape could not grow an identifier the others lack. What shipped is the smaller version: the shared column tuple and the JSON keys are the same order, and the two row lists were updated together. Unifying the row builders was not required to make the contract true.

## NEXT STEPS

Draft pull request: https://github.com/Texarkanine/stockroom/pull/133
