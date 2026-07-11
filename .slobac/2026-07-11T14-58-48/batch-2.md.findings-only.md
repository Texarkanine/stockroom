## Findings

### `tests/test_ingest_sources.py`

- **Location:** `tests/test_ingest_sources.py:102` (`test_mtime_is_naive_utc`)
- **Smell:** `conditional-logic`
- **Rationale:** The UTC-vs-local assertion is gated behind `if datetime.now().astimezone().utcoffset() != timezone.utc...`, so on UTC hosts that branch never asserts and the path is vacuous by omission. Signal: IfStatement inside the test body whose consequent asserts and whose alternate is absent. See https://texarkanine.github.io/slobac/taxonomy/conditional-logic/.
- **Prescribed remediation:** Split into two tests (or pin a frozen non-UTC offset via monkeypatch) so the naive-UTC ≠ local-naive claim always asserts; remove the platform/timezone `if` from the body.
- **Why this isn't a false positive:** Not a runner-native skip (`pytest.mark.skipif`); the branch silently passes as green on UTC machines rather than reporting skipped.

- **Location:** `tests/test_ingest_sources.py:102` (`test_mtime_is_naive_utc`)
- **Smell:** `implementation-coupled`
- **Rationale:** The body calls `sources._mtime(path)`, reaching a single-underscore private helper rather than the public discovery surface that stamps `DiscoveredSession.mtime`. Signal: `_private_method(` access from a separate test module. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Drive mtime through `sources.discover(...)` (or another public API) and assert on the returned `DiscoveredSession.mtime`; keep `_mtime` untested as a private detail.
- **Why this isn't a false positive:** Not same-module / `#[cfg(test)]`-style sanctioned access: the test module is outside `stockroom.ingest.sources` and bypasses the public discover contract.

### `tests/test_migrate_cli.py`

- **Location:** `tests/test_migrate_cli.py:64` (`test_migrate_help_mentions_migration`)
- **Smell:** `loose-text-oracle`
- **Rationale:** Help success is identified only by `assert "migrat" in result.stdout.lower()` — a shared-token substring that would also match unrelated help text ("migratory", "immigrate", typos). The match is the sole semantic oracle for which help was shown. See https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/.
- **Prescribed remediation:** Assert structured argparse contract (subcommand/epilog presence via exact known phrases or parsed help sections), or pin a full golden of `--help` output as an explicit presentation contract.
- **Why this isn't a false positive:** Not a typed-error-plus-datum pattern: there is no error type/code; the truncated token alone identifies the claim.

### `tests/test_packaging.py`

- **Location:** `tests/test_packaging.py:76` (`test_skeleton_skill_front_matter`)
- **Smell:** `prose-pin`
- **Rationale:** Reads committed `SKILL.md` and only asserts front-matter `name`/`description` are non-empty strings — the packaging/front-matter non-empty checklist called out as a prose-pin weaker sibling. See https://texarkanine.github.io/slobac/taxonomy/prose-pin/.
- **Prescribed remediation:** Validate front-matter via a schema/parser (required keys, types, length bounds, name slug rules) or delete the vacuous non-empty string checks if schema validation lives elsewhere.
- **Why this isn't a false positive:** Not architectural fitness-function negatives and not prose-as-SUT temp fixtures: this asserts on committed skill prose fields without structural schema validation.

### `tests/test_query.py`

- **Location:** `tests/test_query.py:68` (`test_run_query_no_con_is_read_only`)
- **Smell:** `conditional-logic`
- **Rationale:** Uses `try: run_query(...); except duckdb.Error: raised = True` then `assert raised` without an explicit fail after a successful return — if the write unexpectedly succeeds, the except never runs and only the final flag assert fails after mutation risk; the classic shape is try/catch without fail-after-SUT. Prefer `pytest.raises`. See https://texarkanine.github.io/slobac/taxonomy/conditional-logic/.
- **Prescribed remediation:** Replace with `with pytest.raises(duckdb.Error): run_query("CREATE TABLE ...")` (and optionally assert warehouse state unchanged).
- **Why this isn't a false positive:** Not the cured `try: sut(); assert.fail(...)` form — there is no fail-after-success path inside the try.

### `tests/test_query_cli.py`

- **Location:** `tests/test_query_cli.py:59` (`test_query_happy_path_prints_result`)
- **Smell:** `vacuous-assertion`
- **Rationale:** After a successful exit, content oracles are only `"n" in result.stdout` and `"1" in result.stdout`, which many wrong TSV/table/json renderings would still satisfy. Sibling tests already lock exact TSV lines; this happy-path oracle stays weak. See https://texarkanine.github.io/slobac/taxonomy/vacuous-assertion/.
- **Prescribed remediation:** Assert the exact default TSV lines (e.g. `splitlines() == ["n", "1"]`) or parse structured output; drop bare substring presence checks.
- **Why this isn't a false positive:** Not a side-effect-absence contract: the name claims printed column/value output, which deserves a strong structured oracle.

- **Location:** `tests/test_query_cli.py:73` (`test_query_proves_end_to_end_queryability`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Name/docstring frame the test as a "Phase-1 proof" deliverable rather than a durable product claim about DISTINCT harness visibility after ingest. Signal: sprint/phase vocabulary in title/docstring. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Rename to a behavior claim (e.g. `test_query_lists_ingested_cursor_and_claude_harnesses`) and drop Phase-1 checklist wording from the docstring.
- **Why this isn't a false positive:** Not domain vocabulary: "Phase-1 proof" names the delivery milestone, not a product entity that appears in the SUT.

- **Location:** `tests/test_query_cli.py:183` (`test_query_reads_sql_from_stdin`)
- **Smell:** `vacuous-assertion`
- **Rationale:** Success is asserted via returncode plus only `assert "1" in result.stdout`, accepting any stdout that happens to contain the digit. See https://texarkanine.github.io/slobac/taxonomy/vacuous-assertion/.
- **Prescribed remediation:** Assert the exact TSV (or JSON) rendering of `SELECT 1 AS n` from stdin, matching the stronger format tests in this file.
- **Why this isn't a false positive:** Not under-specified-title alone: the body itself under-delivers on a knowable exact result shape.

### `tests/test_schedule_cli.py`

- **Location:** `tests/test_schedule_cli.py:70` (`test_help_documents_actions_and_time_flag`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B15:` tying the help contract to a plan item rather than the product help surface. Signal: checklist/ticket vocabulary in the docstring. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Strip the `B15:` prefix; keep a behavior-shaped docstring about documented actions and `--time` default.
- **Why this isn't a false positive:** Not product domain vocabulary: B15 is work-item labeling from the schedule plan, not an SUT term.

- **Location:** `tests/test_schedule_cli.py:79` (`test_invalid_action_is_clean_error`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `B15:` checklist vocabulary for an argparse invalid-action behavior. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Rename/reword the docstring to the product claim (invalid action → exit 2, no traceback) without the plan-item prefix.
- **Why this isn't a false positive:** Not under-specified title alone: the fossil id is explicit work vocabulary.

- **Location:** `tests/test_schedule_cli.py:87` (`test_status_against_empty_environment`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `B15:` framing status CLI coverage as a checklist item. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Drop the `B15:` prefix; describe the empty-environment status facts the body verifies.
- **Why this isn't a false positive:** Not domain synonymy: B15 is plan numbering, not schedule product language.

### `tests/test_shim.py`

- **Location:** `tests/test_shim.py:272` (`TestRectify::test_always_ensures_engine_env`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with `B4:` checklist labeling for ensure_engine_env-on-rectify behavior. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Remove the `B4:` fossil prefix; keep the behavior claim about always ensuring the engine env.
- **Why this isn't a false positive:** Not a refactor-safety property test: B4 names a work item, not the behavior under test.

### `tests/test_shim_cli.py`

- **Location:** `tests/test_shim_cli.py:88` (`test_ensure_env_exits_zero_without_owner`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with `B5:` checklist id for ensure-env CLI wiring. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Strip `B5:`; name the durable CLI contract (ensure-env without --owner exits 0 and invokes ensure).
- **Why this isn't a false positive:** Not product API versioning vocabulary; B5 is delivery checklist labeling.

### `tests/test_shim_runtime.py`

- **Location:** `tests/test_shim_runtime.py:157` (`test_env_not_ready_one_line_owner_remedy`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with `B6:` checklist id for the duckdb-not-ready refuse path. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Remove `B6:`; keep the one-line owner-remedy refuse behavior description.
- **Why this isn't a false positive:** Not domain vocabulary appearing in the SUT; B6 is plan-item scaffolding.

### `tests/test_skill_hygiene.py`

- **Location:** `tests/test_skill_hygiene.py:55` (`test_read_skills_document_exact_text_raw_detail`)
- **Smell:** `prose-pin`
- **Rationale:** Treats committed wrapper `SKILL.md` bytes as oracle via `assert "--detail raw" in text` and `assert "--format json" in text` — feature-mention pins that fail on editorial rewrites without proving the flags work. See https://texarkanine.github.io/slobac/taxonomy/prose-pin/.
- **Prescribed remediation:** Delete the mention pins; re-ground on CLI/behavioral tests that exercise `--detail raw` / `--format json` (already present in query/semantic suites) or move wording policy to docs-lint.
- **Why this isn't a false positive:** Not a documented forbidden-token fitness function (those are the sibling `test_wrapper_skill_has_no_invocation_plumbing`); these are positive feature-mention checklist asserts.

### `tests/test_torch_cli.py`

- **Location:** `tests/test_torch_cli.py:33` (`test_freeze_invokes_freeze_torch`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `F6:` ticket/checklist vocabulary for freeze CLI wiring. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Drop `F6:`; rename/reword to the product claim (freeze forwards --app-dir/--index to freeze_torch).
- **Why this isn't a false positive:** Not a regression bug-id comment citing a fixed defect with behavioral body; F6 is sprint checklist labeling.

No findings for scope `tautology-theatre`.

No findings for scope `over-specified-mock`.

No findings for scope `pseudo-tested`.

No findings for scope `monolithic-test-file`.

No findings for scope `naming-lies`.

No findings for scope `presentation-coupled`.

No findings for scope `shared-state`.

No findings for scope `mystery-guest`.

No findings for scope `rotten-green`.

