# SLOBAC audit report

- **Scope invoked:** all
- **Target suite root:** `skills/sr-search/tests` + `skills/sr-search/tests-js`
- **Audit date:** 2026-07-11
- **Suite manifest:** 57 files, 436,126 chars, 544 tests

## Summary

60 findings total (3 `conditional-logic`, 34 `deliverable-fossils`, 5 `implementation-coupled`, 6 `loose-text-oracle`, 2 `naming-lies`, 1 `presentation-coupled`, 5 `prose-pin`, 2 `semantic-redundancy`, 2 `vacuous-assertion`). No findings for scope `tautology-theatre`. No findings for scope `over-specified-mock`. No findings for scope `pseudo-tested`. No findings for scope `monolithic-test-file`. No findings for scope `shared-state`. No findings for scope `wrong-level`. No findings for scope `mystery-guest`. No findings for scope `rotten-green`. Orchestration: 3 batch assessors ran against a 256k-token context window (content budget ≈512k chars / ~250 tests per batch at `standard` richness); the binding budget was output tests (suite 544 tests > 250-cap), not input chars (436,126 < 512k). Step 8 integrity gate passed cleanly (544/544 behavior-summary rows, no retry). Cross-suite assessor ran and consumed richness: `standard`.

## Findings

### 1. `tests/test_doctor.py :: test_probe_never_imports_torch_eagerly (line 190)` — conditional-logic

- **Location:** `tests/test_doctor.py` :: `test_probe_never_imports_torch_eagerly` (line 190)
- **Smell:** `conditional-logic`
- **Rationale:** Body gates the isolation assertion with `if not already_loaded: assert "torch" not in sys.modules`, so one path never reaches that assertion (vacuous by omission). Signal: IfStatement whose consequent asserts and alternate is absent. See https://texarkanine.github.io/slobac/taxonomy/conditional-logic/.
- **Prescribed remediation:** Pin the precondition (e.g. ensure torch not preloaded via fixture/monkeypatch) and assert unconditionally, or split into two tests with explicit runner skip when torch is already loaded.
- **Why this isn't a false positive:** Not a runner-native skipif — silent `if` around an assert; pytest.skip is not used, so the weaker path still reports green.

### 2. `tests/test_ingest_sources.py:102 (test_mtime_is_naive_utc)` — conditional-logic

- **Location:** `tests/test_ingest_sources.py:102` (`test_mtime_is_naive_utc`)
- **Smell:** `conditional-logic`
- **Rationale:** The UTC-vs-local assertion is gated behind `if datetime.now().astimezone().utcoffset() != timezone.utc...`, so on UTC hosts that branch never asserts and the path is vacuous by omission. Signal: IfStatement inside the test body whose consequent asserts and whose alternate is absent. See https://texarkanine.github.io/slobac/taxonomy/conditional-logic/.
- **Prescribed remediation:** Split into two tests (or pin a frozen non-UTC offset via monkeypatch) so the naive-UTC ≠ local-naive claim always asserts; remove the platform/timezone `if` from the body.
- **Why this isn't a false positive:** Not a runner-native skip (`pytest.mark.skipif`); the branch silently passes as green on UTC machines rather than reporting skipped.

### 3. `tests/test_query.py:68 (test_run_query_no_con_is_read_only)` — conditional-logic

- **Location:** `tests/test_query.py:68` (`test_run_query_no_con_is_read_only`)
- **Smell:** `conditional-logic`
- **Rationale:** Uses `try: run_query(...); except duckdb.Error: raised = True` then `assert raised` without an explicit fail after a successful return — if the write unexpectedly succeeds, the except never runs and only the final flag assert fails after mutation risk; the classic shape is try/catch without fail-after-SUT. Prefer `pytest.raises`. See https://texarkanine.github.io/slobac/taxonomy/conditional-logic/.
- **Prescribed remediation:** Replace with `with pytest.raises(duckdb.Error): run_query("CREATE TABLE ...")` (and optionally assert warehouse state unchanged).
- **Why this isn't a false positive:** Not the cured `try: sut(); assert.fail(...)` form — there is no fail-after-success path inside the try.

### 4. `tests/test_doctor.py :: test_probe_degrades_gracefully_on_smi_failure (line 138)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_probe_degrades_gracefully_on_smi_failure` (line 138)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B4:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B4` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 5. `tests/test_doctor.py :: test_probe_never_imports_torch_eagerly (line 190)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_probe_never_imports_torch_eagerly` (line 190)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B7:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B7` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 6. `tests/test_doctor.py :: test_probe_reports_gpu_and_driver_when_smi_parseable (line 119)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_gpu_and_driver_when_smi_parseable` (line 119)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B2:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B2` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 7. `tests/test_doctor.py :: test_probe_reports_gpu_none_when_smi_absent (line 129)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_gpu_none_when_smi_absent` (line 129)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B3:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B3` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 8. `tests/test_doctor.py :: test_probe_reports_os_and_arch (line 110)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_os_and_arch` (line 110)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B1:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B1` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 9. `tests/test_doctor.py :: test_probe_reports_torch_not_installed (line 145)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_torch_not_installed` (line 145)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B5:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B5` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 10. `tests/test_doctor.py :: test_probe_reports_torch_version_and_cuda (line 152)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_torch_version_and_cuda` (line 152)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B6:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B6` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 11. `tests/test_doctor.py :: test_smoke_encoder_construction_failure_is_caught (line 257)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_smoke_encoder_construction_failure_is_caught` (line 257)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B9:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B9` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 12. `tests/test_doctor.py :: test_smoke_encoder_failure_names_error_and_next_action (line 243)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_smoke_encoder_failure_names_error_and_next_action` (line 243)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B9:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B9` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 13. `tests/test_doctor.py :: test_smoke_happy_path_reports_version_cuda_and_ok (line 287)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_smoke_happy_path_reports_version_cuda_and_ok` (line 287)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B11:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B11` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 14. `tests/test_doctor.py :: test_smoke_real_model_end_to_end (line 301)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_smoke_real_model_end_to_end` (line 301)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B12:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B12` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 15. `tests/test_doctor.py :: test_smoke_torch_missing_is_ratcheted_diagnosis (line 230)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_smoke_torch_missing_is_ratcheted_diagnosis` (line 230)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B8:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B8` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 16. `tests/test_doctor.py :: test_smoke_wrong_width_vector_is_a_failure (line 274)` — deliverable-fossils

- **Location:** `tests/test_doctor.py` :: `test_smoke_wrong_width_vector_is_a_failure` (line 274)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B10:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B10` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### 17. `tests/test_doctor_cli.py :: test_help_documents_both_actions (line 69)` — deliverable-fossils

- **Location:** `tests/test_doctor_cli.py` :: `test_help_documents_both_actions` (line 69)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring is checklist-shaped (`B15: …`) instead of a product behavior title. Signal: AC/checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: remove `B15` and rename the claim to the CLI behavior under test (exit code + printed keys/remedy/help).
- **Why this isn't a false positive:** Not product vocabulary — B-numbers are plan checklist labels, not doctor CLI domain terms.

### 18. `tests/test_doctor_cli.py :: test_probe_exits_zero_and_prints_fact_keys (line 39)` — deliverable-fossils

- **Location:** `tests/test_doctor_cli.py` :: `test_probe_exits_zero_and_prints_fact_keys` (line 39)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring is checklist-shaped (`B13: …`) instead of a product behavior title. Signal: AC/checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: remove `B13` and rename the claim to the CLI behavior under test (exit code + printed keys/remedy/help).
- **Why this isn't a false positive:** Not product vocabulary — B-numbers are plan checklist labels, not doctor CLI domain terms.

### 19. `tests/test_doctor_cli.py :: test_smoke_torch_free_env_fails_loudly_with_remedy (line 56)` — deliverable-fossils

- **Location:** `tests/test_doctor_cli.py` :: `test_smoke_torch_free_env_fails_loudly_with_remedy` (line 56)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring is checklist-shaped (`B14: …`) instead of a product behavior title. Signal: AC/checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: remove `B14` and rename the claim to the CLI behavior under test (exit code + printed keys/remedy/help).
- **Why this isn't a false positive:** Not product vocabulary — B-numbers are plan checklist labels, not doctor CLI domain terms.

### 20. `tests/test_engine_env.py :: test_ensure_invokes_torch_ensure_after_deps (line 104)` — deliverable-fossils

- **Location:** `tests/test_engine_env.py` :: `test_ensure_invokes_torch_ensure_after_deps` (line 104)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with deliverable id `T5:` from the engine-env checklist rather than naming the ensure/heal contract. Signal: checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: strip `T5` and keep a behavior sentence about uv sync/--inexact/torch ensure outcomes.
- **Why this isn't a false positive:** Not SUT domain terms — B/T ids only appear in test documentation, not in engine_env exports.

### 21. `tests/test_engine_env.py :: test_heal_command_never_omits_inexact (line 92)` — deliverable-fossils

- **Location:** `tests/test_engine_env.py` :: `test_heal_command_never_omits_inexact` (line 92)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with deliverable id `B3:` from the engine-env checklist rather than naming the ensure/heal contract. Signal: checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: strip `B3` and keep a behavior sentence about uv sync/--inexact/torch ensure outcomes.
- **Why this isn't a false positive:** Not SUT domain terms — B/T ids only appear in test documentation, not in engine_env exports.

### 22. `tests/test_engine_env.py :: test_heals_with_inexact_sync_when_check_fails (line 71)` — deliverable-fossils

- **Location:** `tests/test_engine_env.py` :: `test_heals_with_inexact_sync_when_check_fails` (line 71)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with deliverable id `B2:` from the engine-env checklist rather than naming the ensure/heal contract. Signal: checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: strip `B2` and keep a behavior sentence about uv sync/--inexact/torch ensure outcomes.
- **Why this isn't a false positive:** Not SUT domain terms — B/T ids only appear in test documentation, not in engine_env exports.

### 23. `tests/test_engine_env.py :: test_noop_when_inexact_check_passes (line 53)` — deliverable-fossils

- **Location:** `tests/test_engine_env.py` :: `test_noop_when_inexact_check_passes` (line 53)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with deliverable id `B1:` from the engine-env checklist rather than naming the ensure/heal contract. Signal: checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: strip `B1` and keep a behavior sentence about uv sync/--inexact/torch ensure outcomes.
- **Why this isn't a false positive:** Not SUT domain terms — B/T ids only appear in test documentation, not in engine_env exports.

### 24. `tests/test_query_cli.py:73 (test_query_proves_end_to_end_queryability)` — deliverable-fossils

- **Location:** `tests/test_query_cli.py:73` (`test_query_proves_end_to_end_queryability`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Name/docstring frame the test as a "Phase-1 proof" deliverable rather than a durable product claim about DISTINCT harness visibility after ingest. Signal: sprint/phase vocabulary in title/docstring. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Rename to a behavior claim (e.g. `test_query_lists_ingested_cursor_and_claude_harnesses`) and drop Phase-1 checklist wording from the docstring.
- **Why this isn't a false positive:** Not domain vocabulary: "Phase-1 proof" names the delivery milestone, not a product entity that appears in the SUT.

### 25. `tests/test_schedule_cli.py:70 (test_help_documents_actions_and_time_flag)` — deliverable-fossils

- **Location:** `tests/test_schedule_cli.py:70` (`test_help_documents_actions_and_time_flag`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B15:` tying the help contract to a plan item rather than the product help surface. Signal: checklist/ticket vocabulary in the docstring. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Strip the `B15:` prefix; keep a behavior-shaped docstring about documented actions and `--time` default.
- **Why this isn't a false positive:** Not product domain vocabulary: B15 is work-item labeling from the schedule plan, not an SUT term.

### 26. `tests/test_schedule_cli.py:79 (test_invalid_action_is_clean_error)` — deliverable-fossils

- **Location:** `tests/test_schedule_cli.py:79` (`test_invalid_action_is_clean_error`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `B15:` checklist vocabulary for an argparse invalid-action behavior. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Rename/reword the docstring to the product claim (invalid action → exit 2, no traceback) without the plan-item prefix.
- **Why this isn't a false positive:** Not under-specified title alone: the fossil id is explicit work vocabulary.

### 27. `tests/test_schedule_cli.py:87 (test_status_against_empty_environment)` — deliverable-fossils

- **Location:** `tests/test_schedule_cli.py:87` (`test_status_against_empty_environment`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `B15:` framing status CLI coverage as a checklist item. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Drop the `B15:` prefix; describe the empty-environment status facts the body verifies.
- **Why this isn't a false positive:** Not domain synonymy: B15 is plan numbering, not schedule product language.

### 28. `tests/test_shim.py:272 (TestRectify::test_always_ensures_engine_env)` — deliverable-fossils

- **Location:** `tests/test_shim.py:272` (`TestRectify::test_always_ensures_engine_env`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with `B4:` checklist labeling for ensure_engine_env-on-rectify behavior. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Remove the `B4:` fossil prefix; keep the behavior claim about always ensuring the engine env.
- **Why this isn't a false positive:** Not a refactor-safety property test: B4 names a work item, not the behavior under test.

### 29. `tests/test_shim_cli.py:88 (test_ensure_env_exits_zero_without_owner)` — deliverable-fossils

- **Location:** `tests/test_shim_cli.py:88` (`test_ensure_env_exits_zero_without_owner`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with `B5:` checklist id for ensure-env CLI wiring. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Strip `B5:`; name the durable CLI contract (ensure-env without --owner exits 0 and invokes ensure).
- **Why this isn't a false positive:** Not product API versioning vocabulary; B5 is delivery checklist labeling.

### 30. `tests/test_shim_runtime.py:157 (test_env_not_ready_one_line_owner_remedy)` — deliverable-fossils

- **Location:** `tests/test_shim_runtime.py:157` (`test_env_not_ready_one_line_owner_remedy`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with `B6:` checklist id for the duckdb-not-ready refuse path. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Remove `B6:`; keep the one-line owner-remedy refuse behavior description.
- **Why this isn't a false positive:** Not domain vocabulary appearing in the SUT; B6 is plan-item scaffolding.

### 31. `tests/test_torch_cli.py:33 (test_freeze_invokes_freeze_torch)` — deliverable-fossils

- **Location:** `tests/test_torch_cli.py:33` (`test_freeze_invokes_freeze_torch`)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `F6:` ticket/checklist vocabulary for freeze CLI wiring. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Drop `F6:`; rename/reword to the product claim (freeze forwards --app-dir/--index to freeze_torch).
- **Why this isn't a false positive:** Not a regression bug-id comment citing a fixed defect with behavioral body; F6 is sprint checklist labeling.

### 32. `tests/test_torch_source.py :: test_ensure_torch_fails_without_freeze` — deliverable-fossils

- **Location:** `tests/test_torch_source.py` :: `test_ensure_torch_fails_without_freeze`
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `F4:`; body verifies soft-fail without freeze and no pip. Signal: checklist id in docstring. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
- **Prescribed remediation:** Phase A — strip `F4:` from the docstring; retain the product-facing failure claim.
- **Why this isn't a false positive:** Fossil id is work vocabulary only; it does not appear as product terminology in production code.

### 33. `tests/test_torch_source.py :: test_ensure_torch_installs_from_freeze` — deliverable-fossils

- **Location:** `tests/test_torch_source.py` :: `test_ensure_torch_installs_from_freeze`
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `F3:`; body verifies hashed freeze install via `--require-hashes -r`. Signal: checklist id in docstring. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
- **Prescribed remediation:** Phase A — drop `F3:` and keep the behavior claim about hashed freeze install.
- **Why this isn't a false positive:** Not the "refactor safety" carve-out; `F3` labels the work item, not a behavior property under test.

### 34. `tests/test_torch_source.py :: test_ensure_torch_noop_when_importable` — deliverable-fossils

- **Location:** `tests/test_torch_source.py` :: `test_ensure_torch_noop_when_importable`
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring is keyed to checklist id `F5:` while the body verifies importable-torch noop (no pip). Signal: docstring AC/checklist identifiers. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
- **Prescribed remediation:** Phase A — remove `F5:` and name the product claim (noop when torch importable; no pip).
- **Why this isn't a false positive:** `F5` is sprint/checklist vocabulary, not a product entity or API version in the SUT.

### 35. `tests/test_torch_source.py :: test_freeze_torch_refuses_without_torch` — deliverable-fossils

- **Location:** `tests/test_torch_source.py` :: `test_freeze_torch_refuses_without_torch`
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `F2:`; body verifies soft-fail with no freeze file and no compile. Signal: checklist id in docstring. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
- **Prescribed remediation:** Phase A — strip `F2:`; keep the "refuses without importable torch" claim.
- **Why this isn't a false positive:** Checklist id is work history, not a product term.

### 36. `tests/test_torch_source.py :: test_freeze_torch_writes_hashed_requirements` — deliverable-fossils

- **Location:** `tests/test_torch_source.py` :: `test_freeze_torch_writes_hashed_requirements`
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with `F1:`; body verifies hashed requirements + index sidecar write. Signal: checklist id in docstring. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
- **Prescribed remediation:** Phase A — remove `F1:` and keep the freeze-write behavior statement.
- **Why this isn't a false positive:** `F1` is delivery-checklist labeling, not domain vocabulary from the SUT.

### 37. `tests/test_torch_source.py :: test_write_read_index_round_trip` — deliverable-fossils

- **Location:** `tests/test_torch_source.py` :: `test_write_read_index_round_trip`
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with checklist id `T1:` rather than a durable product claim; the body verifies write/read round-trip of the torch index under `STOCKROOM_HOME`. Signal: docstring citing design-doc/AC identifiers. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
- **Prescribed remediation:** Phase A rename — strip `T1:` and keep a behavior-shaped docstring (e.g. recorded index survives under `STOCKROOM_HOME`); do not regroup in this pass.
- **Why this isn't a false positive:** Not domain vocabulary — `T1` appears only as work/checklist labeling in the docstring, not as a product term in the SUT.

### 38. `tests/test_dashboard_metrics.py :: test_iso_appends_z_for_naive_utc_datetimes (line 150)` — implementation-coupled

- **Location:** `tests/test_dashboard_metrics.py` :: `test_iso_appends_z_for_naive_utc_datetimes` (line 150)
- **Smell:** `implementation-coupled`
- **Rationale:** Calls private helper `metrics._iso` directly and asserts its return. Signal: underscore-prefixed access reaching past the public metrics API. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Assert datetime wire formatting through public metrics payloads (e.g. overview/session fields that emit ISO strings) or promote a deliberate public helper if the format is a contract.
- **Why this isn't a false positive:** Not sanctioned VisibilityForTesting / same-module convention — this is cross-package reach into a private function from the test suite.

### 39. `tests/test_ingest_claude.py :: test_parse_ts_offset_converts_to_naive_utc (line 29)` — implementation-coupled

- **Location:** `tests/test_ingest_claude.py` :: `test_parse_ts_offset_converts_to_naive_utc` (line 29)
- **Smell:** `implementation-coupled`
- **Rationale:** Invokes `claude._parse_ts` (module-private) as the SUT. Signal: underscore-prefixed private helper called from tests. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Cover timestamp normalization via public `parse_session`/`ingest` outputs, or extract a public pure helper if timestamp parsing is a published contract.
- **Why this isn't a false positive:** Python `_` privacy is conventional; cross-module test calls still couple to an undocumented private API rather than the parser's public surface.

### 40. `tests/test_ingest_claude.py :: test_parse_ts_rejects_non_strings (line 36)` — implementation-coupled

- **Location:** `tests/test_ingest_claude.py` :: `test_parse_ts_rejects_non_strings` (line 36)
- **Smell:** `implementation-coupled`
- **Rationale:** Invokes `claude._parse_ts` (module-private) as the SUT. Signal: underscore-prefixed private helper called from tests. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Cover timestamp normalization via public `parse_session`/`ingest` outputs, or extract a public pure helper if timestamp parsing is a published contract.
- **Why this isn't a false positive:** Python `_` privacy is conventional; cross-module test calls still couple to an undocumented private API rather than the parser's public surface.

### 41. `tests/test_ingest_claude.py :: test_parse_ts_z_suffix_is_naive_utc (line 22)` — implementation-coupled

- **Location:** `tests/test_ingest_claude.py` :: `test_parse_ts_z_suffix_is_naive_utc` (line 22)
- **Smell:** `implementation-coupled`
- **Rationale:** Invokes `claude._parse_ts` (module-private) as the SUT. Signal: underscore-prefixed private helper called from tests. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Cover timestamp normalization via public `parse_session`/`ingest` outputs, or extract a public pure helper if timestamp parsing is a published contract.
- **Why this isn't a false positive:** Python `_` privacy is conventional; cross-module test calls still couple to an undocumented private API rather than the parser's public surface.

### 42. `tests/test_ingest_sources.py:102 (test_mtime_is_naive_utc)` — implementation-coupled

- **Location:** `tests/test_ingest_sources.py:102` (`test_mtime_is_naive_utc`)
- **Smell:** `implementation-coupled`
- **Rationale:** The body calls `sources._mtime(path)`, reaching a single-underscore private helper rather than the public discovery surface that stamps `DiscoveredSession.mtime`. Signal: `_private_method(` access from a separate test module. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Drive mtime through `sources.discover(...)` (or another public API) and assert on the returned `DiscoveredSession.mtime`; keep `_mtime` untested as a private detail.
- **Why this isn't a false positive:** Not same-module / `#[cfg(test)]`-style sanctioned access: the test module is outside `stockroom.ingest.sources` and bypasses the public discover contract.

### 43. `tests-js/dashboard-core.test.mjs :: PANEL_HELP documents efficiency and first-prompt buckets (line 506)` — loose-text-oracle

- **Location:** `tests-js/dashboard-core.test.mjs` :: `PANEL_HELP documents efficiency and first-prompt buckets` (line 506)
- **Smell:** `loose-text-oracle`
- **Rationale:** Asserts unanchored keyword/regex presence in `PANEL_HELP` strings (`/short/i`, `/100|500/`, etc.). Many unrelated help texts sharing those tokens would pass. Signal: substring/regex as sole meaning proxy on free text. See https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/.
- **Prescribed remediation:** If help copy is the product, lock a reviewed full-string golden; otherwise assert structured bucket metadata the UI consumes rather than English tokens.
- **Why this isn't a false positive:** Not a full golden/approval of UX copy — these are underdetermined token matches, the loose-text failure mode rather than presentation-coupled exactness.

### 44. `tests/test_dashboard_server.py :: test_session_api_returns_detail_and_client_errors (line 275)` — loose-text-oracle

- **Location:** `tests/test_dashboard_server.py` :: `test_session_api_returns_detail_and_client_errors` (line 275)
- **Smell:** `loose-text-oracle`
- **Rationale:** Missing `session` vs missing `harness` both return HTTP 400; which failure occurred is identified only by `"session" in payload["error"]` / `"harness" in payload["error"]`. Shared-token substrings underdetermine meaning. Signal: message substring as sole identifier of failure kind beside a shared status. See https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/.
- **Prescribed remediation:** Prefer stable error codes/fields (e.g. `error_code` / missing-param name) or exact structured error payloads; keep message text supplementary only.
- **Why this isn't a false positive:** Not typed-primary+supplementary-datum — status is identical for both failures, so the substring *is* the discriminator.

### 45. `tests/test_dashboard_static.py :: test_write_read_chart_aria_describes_ratio_not_absolute_volumes (line 209)` — loose-text-oracle

- **Location:** `tests/test_dashboard_static.py` :: `test_write_read_chart_aria_describes_ratio_not_absolute_volumes` (line 209)
- **Smell:** `loose-text-oracle`
- **Rationale:** Oracle is `"ratio" in label or "share" in label` (plus a negative phrase). Opposite or unrelated aria text containing those tokens would still pass. Signal: underdetermined substring as semantic stand-in. See https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/.
- **Prescribed remediation:** Assert a stable aria-label contract string (exact or structured attribute equality) that encodes ratio semantics.
- **Why this isn't a false positive:** Not vacuous absence-only — there is a positive match, but it does not lock the intended meaning.

### 46. `tests/test_migrate_cli.py:64 (test_migrate_help_mentions_migration)` — loose-text-oracle

- **Location:** `tests/test_migrate_cli.py:64` (`test_migrate_help_mentions_migration`)
- **Smell:** `loose-text-oracle`
- **Rationale:** Help success is identified only by `assert "migrat" in result.stdout.lower()` — a shared-token substring that would also match unrelated help text ("migratory", "immigrate", typos). The match is the sole semantic oracle for which help was shown. See https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/.
- **Prescribed remediation:** Assert structured argparse contract (subcommand/epilog presence via exact known phrases or parsed help sections), or pin a full golden of `--help` output as an explicit presentation contract.
- **Why this isn't a false positive:** Not a typed-error-plus-datum pattern: there is no error type/code; the truncated token alone identifies the claim.

### 47. `tests/test_torch_source.py :: test_ensure_torch_fails_without_freeze` — loose-text-oracle

- **Location:** `tests/test_torch_source.py` :: `test_ensure_torch_fails_without_freeze`
- **Smell:** `loose-text-oracle`
- **Rationale:** After `report.action == "failed"`, the test identifies the freeze-missing failure via unanchored reason substrings (`"sr-initialize" or "docs/torch.md"`, then `"freeze" or "torch-requirements"`). Those tokens are the differentiator from other `failed` paths (e.g. corrupt freeze), so the message match is the kind identifier — Signal: shared-token / underdetermined text as failure identity. Manifesto: https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/
- **Prescribed remediation:** Prefer a stable machine code / typed reason field (or structured report attribute) for the freeze-missing case; keep human text only as supplementary datum beside that code.
- **Why this isn't a false positive:** Not the typed-primary+supplementary carve-out — `action == "failed"` alone does not identify which failure; the OR-substring chain is what claims "missing freeze."

### 48. `tests/test_torch_source.py :: test_freeze_torch_soft_fails_on_compile_timeout` — loose-text-oracle

- **Location:** `tests/test_torch_source.py` :: `test_freeze_torch_soft_fails_on_compile_timeout`
- **Smell:** `loose-text-oracle`
- **Rationale:** Distinguishes timeout soft-fail from other `failed` outcomes primarily via `"timed out" or "timeout"` in `report.reason` (side-effect checks — no freeze file — are shared with the compile-error sibling). Signal: shared-token message match as failure-kind identity. Manifesto: https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/
- **Prescribed remediation:** Expose a stable reason code / exception type for timeout vs compile failure; assert that code (optionally keep a supplementary datum from the underlying error).
- **Why this isn't a false positive:** Not a dynamic-parameter inclusion beside a typed oracle — the substring alternatives are what identify "timeout" among soft-fails.

### 49. `tests/test_dispatcher_cli.py :: test_top_level_help_lists_all_subcommands (line 58)` — naming-lies

- **Location:** `tests/test_dispatcher_cli.py` :: `test_top_level_help_lists_all_subcommands` (line 58)
- **Smell:** `naming-lies`
- **Rationale:** Docstring claims help lists 'all five subcommands' but `SUBCOMMANDS` has ten entries and the body asserts all ten. Title/doc over-promises a stale count. Signal: title/docstring claim mismatches body. See https://texarkanine.github.io/slobac/taxonomy/naming-lies/.
- **Prescribed remediation:** Rename/fix the docstring to 'all registered subcommands' (or list the actual count); body is already correct.
- **Why this isn't a false positive:** Not under-specified naming — it asserts a specific false quantity ('five') that contradicts the fixture tuple.

### 50. `tests/test_ingest_orchestrator.py :: test_on_progress_none_emits_nothing (line 104)` — naming-lies

- **Location:** `tests/test_ingest_orchestrator.py` :: `test_on_progress_none_emits_nothing` (line 104)
- **Smell:** `naming-lies`
- **Rationale:** Name claims `on_progress=None` emits nothing, but the body only asserts a successful Claude ingest (`sessions > 0`) and never observes callback emissions. Signal: title promises X, body verifies weaker Y. See https://texarkanine.github.io/slobac/taxonomy/naming-lies/.
- **Prescribed remediation:** Rename to match the body (e.g. completes without an on_progress callback) or strengthen by installing a callback spy and asserting zero calls.
- **Why this isn't a false positive:** Not synonymy — 'emits nothing' is a specific negative claim the assertions never check.

### 51. `tests/test_dashboard_static.py :: test_session_pane_toolbar_and_bubble_layout_contracts (line 142)` — presentation-coupled

- **Location:** `tests/test_dashboard_static.py` :: `test_session_pane_toolbar_and_bubble_layout_contracts` (line 142)
- **Smell:** `presentation-coupled`
- **Rationale:** Pins exact emoji toolbar copy (`⬅️ Back to metrics`, etc.) and cosmetic CSS (`width: 90%`, `align-self: flex-end`, overflow rules) in raw HTML/source strings. Signal: raw HTML/CSS presentation assertions when the real claim is layout/affordance semantics. See https://texarkanine.github.io/slobac/taxonomy/presentation-coupled/.
- **Prescribed remediation:** Assert semantic structure (button ids/roles, turn class presence, tool scroll container) via the HTML parser; keep presentation goldens only if rendering is the deliberate contract and tier them separately.
- **Why this isn't a false positive:** Not a formatter/ANSI library whose deliverable is the string — this is dashboard shell markup; cosmetic CSS/emoji edits would fail without behavior change.

### 52. `tests/test_packaging.py:76 (test_skeleton_skill_front_matter)` — prose-pin

- **Location:** `tests/test_packaging.py:76` (`test_skeleton_skill_front_matter`)
- **Smell:** `prose-pin`
- **Rationale:** Reads committed `SKILL.md` and only asserts front-matter `name`/`description` are non-empty strings — the packaging/front-matter non-empty checklist called out as a prose-pin weaker sibling. See https://texarkanine.github.io/slobac/taxonomy/prose-pin/.
- **Prescribed remediation:** Validate front-matter via a schema/parser (required keys, types, length bounds, name slug rules) or delete the vacuous non-empty string checks if schema validation lives elsewhere.
- **Why this isn't a false positive:** Not architectural fitness-function negatives and not prose-as-SUT temp fixtures: this asserts on committed skill prose fields without structural schema validation.

### 53. `tests/test_skill_hygiene.py:55 (test_read_skills_document_exact_text_raw_detail)` — prose-pin

- **Location:** `tests/test_skill_hygiene.py:55` (`test_read_skills_document_exact_text_raw_detail`)
- **Smell:** `prose-pin`
- **Rationale:** Treats committed wrapper `SKILL.md` bytes as oracle via `assert "--detail raw" in text` and `assert "--format json" in text` — feature-mention pins that fail on editorial rewrites without proving the flags work. See https://texarkanine.github.io/slobac/taxonomy/prose-pin/.
- **Prescribed remediation:** Delete the mention pins; re-ground on CLI/behavioral tests that exercise `--detail raw` / `--format json` (already present in query/semantic suites) or move wording policy to docs-lint.
- **Why this isn't a false positive:** Not a documented forbidden-token fitness function (those are the sibling `test_wrapper_skill_has_no_invocation_plumbing`); these are positive feature-mention checklist asserts.

### 54. `tests/test_torch_writers.py :: test_docs_torch_covers_freeze_contract` — prose-pin

- **Location:** `tests/test_torch_writers.py` :: `test_docs_torch_covers_freeze_contract`
- **Smell:** `prose-pin`
- **Rationale:** Reads committed `docs/torch.md` and asserts a keyword checklist (`torch-requirements.txt`, `--require-hashes`, `sr-initialize`, `torch freeze`). Signal: docs keyword checklist as oracle. Manifesto: https://texarkanine.github.io/slobac/taxonomy/prose-pin/
- **Prescribed remediation:** Delete from the unit suite; tier remaining terminology policy under docs-lint, or re-ground on behavioral coverage of the freeze/heal contract.
- **Why this isn't a false positive:** Not schema/manifest validation and not running embedded doc examples — green only means the phrases still appear in the file.

### 55. `tests/test_torch_writers.py :: test_makefile_torch_freezes_after_install` — prose-pin

- **Location:** `tests/test_torch_writers.py` :: `test_makefile_torch_freezes_after_install`
- **Smell:** `prose-pin`
- **Rationale:** Reads committed `Makefile` bytes and asserts keyword presence/absence (`"torch freeze"`, `"TORCH_INDEX"`, `"torch record" not in text`) — editorial wording as oracle, not a behavioral invocation of freeze/install. Signal: phrase checklist on committed prose. Manifesto: https://texarkanine.github.io/slobac/taxonomy/prose-pin/
- **Prescribed remediation:** Delete the unit-suite pin (or move surviving wording policy to docs-lint). Re-ground any real claim by exercising `make torch` / freeze behavior and asserting product outcomes.
- **Why this isn't a false positive:** Not prose-as-SUT temp fixtures; not a documented architectural fitness-function with an explicit `.because()`-style rationale — it is a feature-mention pin on repo prose.

### 56. `tests/test_torch_writers.py :: test_sr_initialize_freezes_after_smoke` — prose-pin

- **Location:** `tests/test_torch_writers.py` :: `test_sr_initialize_freezes_after_smoke`
- **Smell:** `prose-pin`
- **Rationale:** Reads committed `skills/sr-initialize/SKILL.md` and pins phrase presence plus prose order (`doctor smoke` index before `torch freeze`). Signal: feature-mention and order pins on committed skill prose. Manifesto: https://texarkanine.github.io/slobac/taxonomy/prose-pin/
- **Prescribed remediation:** Delete the order/keyword pin from the unit suite; if the claim is "freeze runs after smoke," cover it with a behavioral or docs-as-tests path, or enforce wording in docs-lint.
- **Why this isn't a false positive:** An editorial reorder that preserves meaning would fail CI with no product change — classic prose-pin, not executable docs-as-tests.

### 57. `tests/test_warehouse_home_xdg.py:68 (test_home_dir_creates_resolved_path) ↔ tests/test_warehouse_open.py:51 (test_hom...` — semantic-redundancy

- **Location:** `tests/test_warehouse_home_xdg.py:68` (`test_home_dir_creates_resolved_path`) ↔ `tests/test_warehouse_open.py:51` (`test_home_dir_is_auto_created`)
- **Smell:** `semantic-redundancy`
- **Rationale:** Both tests assert the same observable: `warehouse.home_dir()` creates a previously absent resolved home and returns that directory. Fixture shape differs (XDG env vs `warehouse_home`/`STOCKROOM_HOME`), but the claim is identical — Signal: cross-file behavior-sentence cluster with equivalent SUT entry point and assertion set. See https://texarkanine.github.io/slobac/taxonomy/semantic-redundancy/.
- **Prescribed remediation:** Keep `tests/test_warehouse_home_xdg.py:68` as canonical (dedicated path-resolution file; stronger parent-creation coverage when XDG root is absent). Delete `tests/test_warehouse_open.py:51` as a strict subset left from the open file’s “step 4” path scaffolding.
- **Why this isn't a false positive:** Not same-surface/different-concept — both guard home-dir mkdir semantics, not open()/migration; not mirrored multi-product suites.

### 58. `tests/test_warehouse_home_xdg.py:82 (test_warehouse_and_lock_paths_live_under_resolved_home) ↔ tests/test_warehouse_o...` — semantic-redundancy

- **Location:** `tests/test_warehouse_home_xdg.py:82` (`test_warehouse_and_lock_paths_live_under_resolved_home`) ↔ `tests/test_warehouse_open.py:44` (`test_paths_resolve_under_stockroom_home`)
- **Smell:** `semantic-redundancy`
- **Rationale:** Both assert `home_dir()`, `warehouse_path()`, and `lock_path()` nest under the resolved home (duckdb + lock filenames). Again only the home-selection fixture differs — Signal: same SUT entry points with assertion sets that are mutual subsets. See https://texarkanine.github.io/slobac/taxonomy/semantic-redundancy/.
- **Prescribed remediation:** Keep `tests/test_warehouse_home_xdg.py:82` as canonical (uses `WAREHOUSE_FILENAME` / `LOCK_FILENAME` and sits with the resolve_home matrix). Delete `tests/test_warehouse_open.py:44`; leave `WarehouseBusyError` / open-gate tests in `test_warehouse_open.py`.
- **Why this isn't a false positive:** Not contract-duplication of production constants as a drift guard — the open copy hardcodes filename literals while re-proving path nesting already covered under the XDG suite.

### 59. `tests/test_query_cli.py:183 (test_query_reads_sql_from_stdin)` — vacuous-assertion

- **Location:** `tests/test_query_cli.py:183` (`test_query_reads_sql_from_stdin`)
- **Smell:** `vacuous-assertion`
- **Rationale:** Success is asserted via returncode plus only `assert "1" in result.stdout`, accepting any stdout that happens to contain the digit. See https://texarkanine.github.io/slobac/taxonomy/vacuous-assertion/.
- **Prescribed remediation:** Assert the exact TSV (or JSON) rendering of `SELECT 1 AS n` from stdin, matching the stronger format tests in this file.
- **Why this isn't a false positive:** Not under-specified-title alone: the body itself under-delivers on a knowable exact result shape.

### 60. `tests/test_query_cli.py:59 (test_query_happy_path_prints_result)` — vacuous-assertion

- **Location:** `tests/test_query_cli.py:59` (`test_query_happy_path_prints_result`)
- **Smell:** `vacuous-assertion`
- **Rationale:** After a successful exit, content oracles are only `"n" in result.stdout` and `"1" in result.stdout`, which many wrong TSV/table/json renderings would still satisfy. Sibling tests already lock exact TSV lines; this happy-path oracle stays weak. See https://texarkanine.github.io/slobac/taxonomy/vacuous-assertion/.
- **Prescribed remediation:** Assert the exact default TSV lines (e.g. `splitlines() == ["n", "1"]`) or parse structured output; drop bare substring presence checks.
- **Why this isn't a false positive:** Not a side-effect-absence contract: the name claims printed column/value output, which deserves a strong structured oracle.

## Tests considered but not flagged

None.

## Out-of-scope requests

None.
