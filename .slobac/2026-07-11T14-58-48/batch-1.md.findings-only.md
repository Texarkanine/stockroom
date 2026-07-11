## Findings

### `tests-js/dashboard-core.test.mjs`

- **Location:** `tests-js/dashboard-core.test.mjs` :: `PANEL_HELP documents efficiency and first-prompt buckets` (line 506)
- **Smell:** `loose-text-oracle`
- **Rationale:** Asserts unanchored keyword/regex presence in `PANEL_HELP` strings (`/short/i`, `/100|500/`, etc.). Many unrelated help texts sharing those tokens would pass. Signal: substring/regex as sole meaning proxy on free text. See https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/.
- **Prescribed remediation:** If help copy is the product, lock a reviewed full-string golden; otherwise assert structured bucket metadata the UI consumes rather than English tokens.
- **Why this isn't a false positive:** Not a full golden/approval of UX copy — these are underdetermined token matches, the loose-text failure mode rather than presentation-coupled exactness.

### `tests/test_dashboard_metrics.py`

- **Location:** `tests/test_dashboard_metrics.py` :: `test_iso_appends_z_for_naive_utc_datetimes` (line 150)
- **Smell:** `implementation-coupled`
- **Rationale:** Calls private helper `metrics._iso` directly and asserts its return. Signal: underscore-prefixed access reaching past the public metrics API. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Assert datetime wire formatting through public metrics payloads (e.g. overview/session fields that emit ISO strings) or promote a deliberate public helper if the format is a contract.
- **Why this isn't a false positive:** Not sanctioned VisibilityForTesting / same-module convention — this is cross-package reach into a private function from the test suite.

### `tests/test_dashboard_server.py`

- **Location:** `tests/test_dashboard_server.py` :: `test_session_api_returns_detail_and_client_errors` (line 275)
- **Smell:** `loose-text-oracle`
- **Rationale:** Missing `session` vs missing `harness` both return HTTP 400; which failure occurred is identified only by `"session" in payload["error"]` / `"harness" in payload["error"]`. Shared-token substrings underdetermine meaning. Signal: message substring as sole identifier of failure kind beside a shared status. See https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/.
- **Prescribed remediation:** Prefer stable error codes/fields (e.g. `error_code` / missing-param name) or exact structured error payloads; keep message text supplementary only.
- **Why this isn't a false positive:** Not typed-primary+supplementary-datum — status is identical for both failures, so the substring *is* the discriminator.

### `tests/test_dashboard_static.py`

- **Location:** `tests/test_dashboard_static.py` :: `test_session_pane_toolbar_and_bubble_layout_contracts` (line 142)
- **Smell:** `presentation-coupled`
- **Rationale:** Pins exact emoji toolbar copy (`⬅️ Back to metrics`, etc.) and cosmetic CSS (`width: 90%`, `align-self: flex-end`, overflow rules) in raw HTML/source strings. Signal: raw HTML/CSS presentation assertions when the real claim is layout/affordance semantics. See https://texarkanine.github.io/slobac/taxonomy/presentation-coupled/.
- **Prescribed remediation:** Assert semantic structure (button ids/roles, turn class presence, tool scroll container) via the HTML parser; keep presentation goldens only if rendering is the deliberate contract and tier them separately.
- **Why this isn't a false positive:** Not a formatter/ANSI library whose deliverable is the string — this is dashboard shell markup; cosmetic CSS/emoji edits would fail without behavior change.

- **Location:** `tests/test_dashboard_static.py` :: `test_write_read_chart_aria_describes_ratio_not_absolute_volumes` (line 209)
- **Smell:** `loose-text-oracle`
- **Rationale:** Oracle is `"ratio" in label or "share" in label` (plus a negative phrase). Opposite or unrelated aria text containing those tokens would still pass. Signal: underdetermined substring as semantic stand-in. See https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/.
- **Prescribed remediation:** Assert a stable aria-label contract string (exact or structured attribute equality) that encodes ratio semantics.
- **Why this isn't a false positive:** Not vacuous absence-only — there is a positive match, but it does not lock the intended meaning.

### `tests/test_dispatcher_cli.py`

- **Location:** `tests/test_dispatcher_cli.py` :: `test_top_level_help_lists_all_subcommands` (line 58)
- **Smell:** `naming-lies`
- **Rationale:** Docstring claims help lists 'all five subcommands' but `SUBCOMMANDS` has ten entries and the body asserts all ten. Title/doc over-promises a stale count. Signal: title/docstring claim mismatches body. See https://texarkanine.github.io/slobac/taxonomy/naming-lies/.
- **Prescribed remediation:** Rename/fix the docstring to 'all registered subcommands' (or list the actual count); body is already correct.
- **Why this isn't a false positive:** Not under-specified naming — it asserts a specific false quantity ('five') that contradicts the fixture tuple.

### `tests/test_doctor.py`

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_os_and_arch` (line 110)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B1:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B1` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_gpu_and_driver_when_smi_parseable` (line 119)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B2:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B2` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_gpu_none_when_smi_absent` (line 129)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B3:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B3` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_probe_degrades_gracefully_on_smi_failure` (line 138)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B4:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B4` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_torch_not_installed` (line 145)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B5:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B5` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_probe_reports_torch_version_and_cuda` (line 152)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B6:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B6` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_probe_never_imports_torch_eagerly` (line 190)
- **Smell:** `conditional-logic`
- **Rationale:** Body gates the isolation assertion with `if not already_loaded: assert "torch" not in sys.modules`, so one path never reaches that assertion (vacuous by omission). Signal: IfStatement whose consequent asserts and alternate is absent. See https://texarkanine.github.io/slobac/taxonomy/conditional-logic/.
- **Prescribed remediation:** Pin the precondition (e.g. ensure torch not preloaded via fixture/monkeypatch) and assert unconditionally, or split into two tests with explicit runner skip when torch is already loaded.
- **Why this isn't a false positive:** Not a runner-native skipif — silent `if` around an assert; pytest.skip is not used, so the weaker path still reports green.

- **Location:** `tests/test_doctor.py` :: `test_probe_never_imports_torch_eagerly` (line 190)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B7:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B7` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_smoke_torch_missing_is_ratcheted_diagnosis` (line 230)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B8:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B8` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_smoke_encoder_failure_names_error_and_next_action` (line 243)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B9:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B9` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_smoke_encoder_construction_failure_is_caught` (line 257)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B9:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B9` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_smoke_wrong_width_vector_is_a_failure` (line 274)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B10:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B10` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_smoke_happy_path_reports_version_cuda_and_ok` (line 287)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B11:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B11` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

- **Location:** `tests/test_doctor.py` :: `test_smoke_real_model_end_to_end` (line 301)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring leads with checklist id `B12:` rather than a durable product claim; Signal: docstrings citing AC/checklist identifiers. Body verifies doctor probe/smoke behavior, but naming reflects a gone plan checklist. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A rename: strip `B12` from the docstring and keep a behavior-shaped claim (e.g. what fact/exit/remedy is verified). Do not regroup yet (Phase B is cross-suite).
- **Why this isn't a false positive:** Not domain vocabulary — `B#` appears only in test docs/section headers, not in the doctor SUT API.

### `tests/test_doctor_cli.py`

- **Location:** `tests/test_doctor_cli.py` :: `test_probe_exits_zero_and_prints_fact_keys` (line 39)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring is checklist-shaped (`B13: …`) instead of a product behavior title. Signal: AC/checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: remove `B13` and rename the claim to the CLI behavior under test (exit code + printed keys/remedy/help).
- **Why this isn't a false positive:** Not product vocabulary — B-numbers are plan checklist labels, not doctor CLI domain terms.

- **Location:** `tests/test_doctor_cli.py` :: `test_smoke_torch_free_env_fails_loudly_with_remedy` (line 56)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring is checklist-shaped (`B14: …`) instead of a product behavior title. Signal: AC/checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: remove `B14` and rename the claim to the CLI behavior under test (exit code + printed keys/remedy/help).
- **Why this isn't a false positive:** Not product vocabulary — B-numbers are plan checklist labels, not doctor CLI domain terms.

- **Location:** `tests/test_doctor_cli.py` :: `test_help_documents_both_actions` (line 69)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring is checklist-shaped (`B15: …`) instead of a product behavior title. Signal: AC/checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: remove `B15` and rename the claim to the CLI behavior under test (exit code + printed keys/remedy/help).
- **Why this isn't a false positive:** Not product vocabulary — B-numbers are plan checklist labels, not doctor CLI domain terms.

### `tests/test_engine_env.py`

- **Location:** `tests/test_engine_env.py` :: `test_noop_when_inexact_check_passes` (line 53)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with deliverable id `B1:` from the engine-env checklist rather than naming the ensure/heal contract. Signal: checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: strip `B1` and keep a behavior sentence about uv sync/--inexact/torch ensure outcomes.
- **Why this isn't a false positive:** Not SUT domain terms — B/T ids only appear in test documentation, not in engine_env exports.

- **Location:** `tests/test_engine_env.py` :: `test_heals_with_inexact_sync_when_check_fails` (line 71)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with deliverable id `B2:` from the engine-env checklist rather than naming the ensure/heal contract. Signal: checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: strip `B2` and keep a behavior sentence about uv sync/--inexact/torch ensure outcomes.
- **Why this isn't a false positive:** Not SUT domain terms — B/T ids only appear in test documentation, not in engine_env exports.

- **Location:** `tests/test_engine_env.py` :: `test_heal_command_never_omits_inexact` (line 92)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with deliverable id `B3:` from the engine-env checklist rather than naming the ensure/heal contract. Signal: checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: strip `B3` and keep a behavior sentence about uv sync/--inexact/torch ensure outcomes.
- **Why this isn't a false positive:** Not SUT domain terms — B/T ids only appear in test documentation, not in engine_env exports.

- **Location:** `tests/test_engine_env.py` :: `test_ensure_invokes_torch_ensure_after_deps` (line 104)
- **Smell:** `deliverable-fossils`
- **Rationale:** Docstring opens with deliverable id `T5:` from the engine-env checklist rather than naming the ensure/heal contract. Signal: checklist identifiers in docstrings. See https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/.
- **Prescribed remediation:** Phase A: strip `T5` and keep a behavior sentence about uv sync/--inexact/torch ensure outcomes.
- **Why this isn't a false positive:** Not SUT domain terms — B/T ids only appear in test documentation, not in engine_env exports.

### `tests/test_ingest_claude.py`

- **Location:** `tests/test_ingest_claude.py` :: `test_parse_ts_z_suffix_is_naive_utc` (line 22)
- **Smell:** `implementation-coupled`
- **Rationale:** Invokes `claude._parse_ts` (module-private) as the SUT. Signal: underscore-prefixed private helper called from tests. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Cover timestamp normalization via public `parse_session`/`ingest` outputs, or extract a public pure helper if timestamp parsing is a published contract.
- **Why this isn't a false positive:** Python `_` privacy is conventional; cross-module test calls still couple to an undocumented private API rather than the parser's public surface.

- **Location:** `tests/test_ingest_claude.py` :: `test_parse_ts_offset_converts_to_naive_utc` (line 29)
- **Smell:** `implementation-coupled`
- **Rationale:** Invokes `claude._parse_ts` (module-private) as the SUT. Signal: underscore-prefixed private helper called from tests. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Cover timestamp normalization via public `parse_session`/`ingest` outputs, or extract a public pure helper if timestamp parsing is a published contract.
- **Why this isn't a false positive:** Python `_` privacy is conventional; cross-module test calls still couple to an undocumented private API rather than the parser's public surface.

- **Location:** `tests/test_ingest_claude.py` :: `test_parse_ts_rejects_non_strings` (line 36)
- **Smell:** `implementation-coupled`
- **Rationale:** Invokes `claude._parse_ts` (module-private) as the SUT. Signal: underscore-prefixed private helper called from tests. See https://texarkanine.github.io/slobac/taxonomy/implementation-coupled/.
- **Prescribed remediation:** Cover timestamp normalization via public `parse_session`/`ingest` outputs, or extract a public pure helper if timestamp parsing is a published contract.
- **Why this isn't a false positive:** Python `_` privacy is conventional; cross-module test calls still couple to an undocumented private API rather than the parser's public surface.

### `tests/test_ingest_orchestrator.py`

- **Location:** `tests/test_ingest_orchestrator.py` :: `test_on_progress_none_emits_nothing` (line 104)
- **Smell:** `naming-lies`
- **Rationale:** Name claims `on_progress=None` emits nothing, but the body only asserts a successful Claude ingest (`sessions > 0`) and never observes callback emissions. Signal: title promises X, body verifies weaker Y. See https://texarkanine.github.io/slobac/taxonomy/naming-lies/.
- **Prescribed remediation:** Rename to match the body (e.g. completes without an on_progress callback) or strengthen by installing a callback spy and asserting zero calls.
- **Why this isn't a false positive:** Not synonymy — 'emits nothing' is a specific negative claim the assertions never check.

No findings for scope `tautology-theatre`.

No findings for scope `over-specified-mock`.

No findings for scope `prose-pin`.

No findings for scope `pseudo-tested`.

No findings for scope `vacuous-assertion`.

No findings for scope `monolithic-test-file`.

No findings for scope `shared-state`.

No findings for scope `mystery-guest`.

No findings for scope `rotten-green`.

