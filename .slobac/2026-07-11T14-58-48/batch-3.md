## Findings

### `tests/test_torch_source.py`

**Location:** `tests/test_torch_source.py` :: `test_write_read_index_round_trip`
**Smell:** `deliverable-fossils`
**Rationale:** Docstring opens with checklist id `T1:` rather than a durable product claim; the body verifies write/read round-trip of the torch index under `STOCKROOM_HOME`. Signal: docstring citing design-doc/AC identifiers. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
**Prescribed remediation:** Phase A rename — strip `T1:` and keep a behavior-shaped docstring (e.g. recorded index survives under `STOCKROOM_HOME`); do not regroup in this pass.
**Why this isn't a false positive:** Not domain vocabulary — `T1` appears only as work/checklist labeling in the docstring, not as a product term in the SUT.

**Location:** `tests/test_torch_source.py` :: `test_ensure_torch_noop_when_importable`
**Smell:** `deliverable-fossils`
**Rationale:** Docstring is keyed to checklist id `F5:` while the body verifies importable-torch noop (no pip). Signal: docstring AC/checklist identifiers. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
**Prescribed remediation:** Phase A — remove `F5:` and name the product claim (noop when torch importable; no pip).
**Why this isn't a false positive:** `F5` is sprint/checklist vocabulary, not a product entity or API version in the SUT.

**Location:** `tests/test_torch_source.py` :: `test_ensure_torch_installs_from_freeze`
**Smell:** `deliverable-fossils`
**Rationale:** Docstring leads with `F3:`; body verifies hashed freeze install via `--require-hashes -r`. Signal: checklist id in docstring. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
**Prescribed remediation:** Phase A — drop `F3:` and keep the behavior claim about hashed freeze install.
**Why this isn't a false positive:** Not the "refactor safety" carve-out; `F3` labels the work item, not a behavior property under test.

**Location:** `tests/test_torch_source.py` :: `test_ensure_torch_fails_without_freeze`
**Smell:** `deliverable-fossils`
**Rationale:** Docstring leads with `F4:`; body verifies soft-fail without freeze and no pip. Signal: checklist id in docstring. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
**Prescribed remediation:** Phase A — strip `F4:` from the docstring; retain the product-facing failure claim.
**Why this isn't a false positive:** Fossil id is work vocabulary only; it does not appear as product terminology in production code.

**Location:** `tests/test_torch_source.py` :: `test_ensure_torch_fails_without_freeze`
**Smell:** `loose-text-oracle`
**Rationale:** After `report.action == "failed"`, the test identifies the freeze-missing failure via unanchored reason substrings (`"sr-initialize" or "docs/torch.md"`, then `"freeze" or "torch-requirements"`). Those tokens are the differentiator from other `failed` paths (e.g. corrupt freeze), so the message match is the kind identifier — Signal: shared-token / underdetermined text as failure identity. Manifesto: https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/
**Prescribed remediation:** Prefer a stable machine code / typed reason field (or structured report attribute) for the freeze-missing case; keep human text only as supplementary datum beside that code.
**Why this isn't a false positive:** Not the typed-primary+supplementary carve-out — `action == "failed"` alone does not identify which failure; the OR-substring chain is what claims "missing freeze."

**Location:** `tests/test_torch_source.py` :: `test_freeze_torch_writes_hashed_requirements`
**Smell:** `deliverable-fossils`
**Rationale:** Docstring leads with `F1:`; body verifies hashed requirements + index sidecar write. Signal: checklist id in docstring. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
**Prescribed remediation:** Phase A — remove `F1:` and keep the freeze-write behavior statement.
**Why this isn't a false positive:** `F1` is delivery-checklist labeling, not domain vocabulary from the SUT.

**Location:** `tests/test_torch_source.py` :: `test_freeze_torch_refuses_without_torch`
**Smell:** `deliverable-fossils`
**Rationale:** Docstring leads with `F2:`; body verifies soft-fail with no freeze file and no compile. Signal: checklist id in docstring. Manifesto: https://texarkanine.github.io/slobac/taxonomy/deliverable-fossils/
**Prescribed remediation:** Phase A — strip `F2:`; keep the "refuses without importable torch" claim.
**Why this isn't a false positive:** Checklist id is work history, not a product term.

**Location:** `tests/test_torch_source.py` :: `test_freeze_torch_soft_fails_on_compile_timeout`
**Smell:** `loose-text-oracle`
**Rationale:** Distinguishes timeout soft-fail from other `failed` outcomes primarily via `"timed out" or "timeout"` in `report.reason` (side-effect checks — no freeze file — are shared with the compile-error sibling). Signal: shared-token message match as failure-kind identity. Manifesto: https://texarkanine.github.io/slobac/taxonomy/loose-text-oracle/
**Prescribed remediation:** Expose a stable reason code / exception type for timeout vs compile failure; assert that code (optionally keep a supplementary datum from the underlying error).
**Why this isn't a false positive:** Not a dynamic-parameter inclusion beside a typed oracle — the substring alternatives are what identify "timeout" among soft-fails.

### `tests/test_torch_writers.py`

**Location:** `tests/test_torch_writers.py` :: `test_makefile_torch_freezes_after_install`
**Smell:** `prose-pin`
**Rationale:** Reads committed `Makefile` bytes and asserts keyword presence/absence (`"torch freeze"`, `"TORCH_INDEX"`, `"torch record" not in text`) — editorial wording as oracle, not a behavioral invocation of freeze/install. Signal: phrase checklist on committed prose. Manifesto: https://texarkanine.github.io/slobac/taxonomy/prose-pin/
**Prescribed remediation:** Delete the unit-suite pin (or move surviving wording policy to docs-lint). Re-ground any real claim by exercising `make torch` / freeze behavior and asserting product outcomes.
**Why this isn't a false positive:** Not prose-as-SUT temp fixtures; not a documented architectural fitness-function with an explicit `.because()`-style rationale — it is a feature-mention pin on repo prose.

**Location:** `tests/test_torch_writers.py` :: `test_sr_initialize_freezes_after_smoke`
**Smell:** `prose-pin`
**Rationale:** Reads committed `skills/sr-initialize/SKILL.md` and pins phrase presence plus prose order (`doctor smoke` index before `torch freeze`). Signal: feature-mention and order pins on committed skill prose. Manifesto: https://texarkanine.github.io/slobac/taxonomy/prose-pin/
**Prescribed remediation:** Delete the order/keyword pin from the unit suite; if the claim is "freeze runs after smoke," cover it with a behavioral or docs-as-tests path, or enforce wording in docs-lint.
**Why this isn't a false positive:** An editorial reorder that preserves meaning would fail CI with no product change — classic prose-pin, not executable docs-as-tests.

**Location:** `tests/test_torch_writers.py` :: `test_docs_torch_covers_freeze_contract`
**Smell:** `prose-pin`
**Rationale:** Reads committed `docs/torch.md` and asserts a keyword checklist (`torch-requirements.txt`, `--require-hashes`, `sr-initialize`, `torch freeze`). Signal: docs keyword checklist as oracle. Manifesto: https://texarkanine.github.io/slobac/taxonomy/prose-pin/
**Prescribed remediation:** Delete from the unit suite; tier remaining terminology policy under docs-lint, or re-ground on behavioral coverage of the freeze/heal contract.
**Why this isn't a false positive:** Not schema/manifest validation and not running embedded doc examples — green only means the phrases still appear in the file.

No findings for scope `tautology-theatre`.
No findings for scope `implementation-coupled`.
No findings for scope `over-specified-mock`.
No findings for scope `pseudo-tested`.
No findings for scope `vacuous-assertion`.
No findings for scope `conditional-logic`.
No findings for scope `monolithic-test-file`.
No findings for scope `naming-lies`.
No findings for scope `presentation-coupled`.
No findings for scope `shared-state`.
No findings for scope `mystery-guest`.
No findings for scope `rotten-green`.

## Behavior Summaries

| File | Line | Test ID | Behavior | Tier | Smells Found |
|------|------|---------|----------|------|--------------|
| tests/test_torch_source.py | 38 | test_write_read_index_round_trip | Writes torch index URL under STOCKROOM_HOME and reads it back. SUT: `torch_source.write_index`, `read_index`. Asserts path equals `stockroom_home/torch-index` and round-tripped URL. | unit | deliverable-fossils |
| tests/test_torch_source.py | 46 | test_read_index_none_when_missing | Reads torch index when no sidecar exists. SUT: `torch_source.read_index`. Asserts return is `None`. | unit | — |
| tests/test_torch_source.py | 50 | test_write_index_rejects_non_https | Rejects non-HTTPS index URL. SUT: `torch_source.write_index`. Asserts `ValueError` matching `https://`. | unit | — |
| tests/test_torch_source.py | 55 | test_ensure_torch_noop_when_importable | Noops when torch import succeeds despite freeze present. SUT: `torch_source.ensure_torch` with runner double. Asserts `action=="noop"`, first call ends with `import torch`, no pip calls. | unit | deliverable-fossils |
| tests/test_torch_source.py | 82 | test_ensure_torch_installs_from_freeze | Installs from hashed freeze when import fails. SUT: `ensure_torch` + runner. Asserts `action=="installed"`, pip argv has `--require-hashes`/`-r`/freeze path/`--no-config`/`--directory`, not bare index install. | unit | deliverable-fossils |
| tests/test_torch_source.py | 120 | test_ensure_torch_fails_without_freeze | Soft-fails when torch missing and freeze absent. SUT: `ensure_torch` + runner. Asserts `action=="failed"`, reason substrings for initialize/docs and freeze, and no pip calls. | unit | deliverable-fossils, loose-text-oracle |
| tests/test_torch_source.py | 141 | test_ensure_torch_fails_on_corrupt_freeze | Soft-fails on freeze lacking hashes; skips pip. SUT: `ensure_torch` + runner. Asserts `action=="failed"` and no pip in runner calls. | unit | — |
| tests/test_torch_source.py | 172 | test_freeze_torch_writes_hashed_requirements | Freezes importable torch into hashed requirements and index sidecar. SUT: `freeze_torch` + runner. Asserts `action=="written"`, requirements content/hashes/URL, `read_index`, and `uv pip compile` flags/input. | unit | deliverable-fossils |
| tests/test_torch_source.py | 220 | test_freeze_torch_refuses_without_torch | Refuses freeze when torch is not importable. SUT: `freeze_torch` + runner. Asserts `action=="failed"`, `"torch"` in reason, no requirements file, no compile calls. | unit | deliverable-fossils |
| tests/test_torch_source.py | 239 | test_freeze_torch_soft_fails_on_compile_error | Soft-fails when `uv pip compile` returns non-zero; writes no freeze. SUT: `freeze_torch` + runner. Asserts `action=="failed"`, compile reason text, and missing requirements file. | unit | — |
| tests/test_torch_source.py | 262 | test_freeze_torch_soft_fails_on_compile_timeout | Soft-fails when compile raises `TimeoutExpired`; writes no freeze. SUT: `freeze_torch` + runner. Asserts `action=="failed"`, timeout/timed-out reason tokens, and missing requirements file. | unit | loose-text-oracle |
| tests/test_torch_writers.py | 8 | test_makefile_torch_freezes_after_install | Pins committed Makefile wording for freeze-after-install. SUT: none (reads `Makefile`). Asserts `torch freeze`/`TORCH_INDEX` present and `torch record` absent. | unknown | prose-pin, wrong-level? |
| tests/test_torch_writers.py | 16 | test_sr_initialize_freezes_after_smoke | Pins sr-initialize skill prose order and freeze mention. SUT: none (reads `SKILL.md`). Asserts `torch freeze` present, `torch record` absent, and `doctor smoke` before `torch freeze`. | unknown | prose-pin, wrong-level? |
| tests/test_torch_writers.py | 28 | test_docs_torch_covers_freeze_contract | Pins docs/torch.md keyword checklist for freeze/heal. SUT: none (reads `docs/torch.md`). Asserts file exists and phrases `torch-requirements.txt`, `--require-hashes`, `sr-initialize`, `torch freeze`. | unknown | prose-pin, wrong-level? |
| tests/test_truncate.py | 19 | test_level_widths_keys_match_detail_levels | Keeps LEVEL_WIDTHS keys aligned with DETAIL_LEVELS. SUT: module constants `LEVEL_WIDTHS`, `DETAIL_LEVELS`. Asserts set equality of keys. | unit | — |
| tests/test_truncate.py | 24 | test_default_detail_is_snippet | Default detail level is snippet. SUT: `DEFAULT_DETAIL`. Asserts equals `"snippet"`. | unit | — |
| tests/test_truncate.py | 29 | test_full_is_unbounded | Full level has no width budget. SUT: `LEVEL_WIDTHS["full"]`. Asserts value is `None`. | unit | — |
| tests/test_truncate.py | 37 | test_short_value_returned_unchanged | Returns short values unchanged without elision. SUT: `truncate_cell`. Asserts `"hi"` unchanged and `ELISION` absent. | unit | — |
| tests/test_truncate.py | 43 | test_over_width_keeps_width_chars_then_marker | Truncates over-budget values to width then marker. SUT: `truncate_cell`. Asserts prefix of width chars, full run absent, `ELISION` present. | unit | — |
| tests/test_truncate.py | 53 | test_hidden_count_is_accurate | Elision marker reports exact hidden character count. SUT: `truncate_cell`. Asserts exact `width + ELISION(+hidden)` string. | unit | — |
| tests/test_truncate.py | 62 | test_full_level_never_truncates | Full level preserves long content without marker. SUT: `truncate_cell`. Asserts 5000-char equality and no `ELISION`. | unit | — |
| tests/test_truncate.py | 69 | test_collapses_whitespace_and_newlines_at_bounded_and_full | Collapses whitespace/newlines for non-raw levels. SUT: `truncate_cell` for compact/snippet/full. Asserts each yields `"a b c"`. | unit | — |
| tests/test_truncate.py | 75 | test_level_ordering_keeps_fewer_chars_for_terser_levels | Compact keeps fewer chars than snippet; full unbounded. SUT: `LEVEL_WIDTHS`, `truncate_cell`. Asserts width ordering and matching hidden-count markers / full equality. | unit | — |
| tests/test_truncate.py | 88 | test_exact_width_boundary_not_truncated | Exact width unchanged; width+1 truncates with `(+1)`. SUT: `truncate_cell`. Asserts both boundary outcomes exactly. | unit | — |
| tests/test_truncate.py | 96 | test_empty_string | Empty input yields empty output. SUT: `truncate_cell`. Asserts `""`. | unit | — |
| tests/test_truncate.py | 101 | test_raw_preserves_whitespace | Raw preserves newlines and multi-spaces. SUT: `truncate_cell`. Asserts exact `"a\n\nb  c"`. | unit | — |
| tests/test_truncate.py | 106 | test_raw_is_unbounded | Raw has no width budget and never elides. SUT: `LEVEL_WIDTHS["raw"]`, `truncate_cell`. Asserts `None` width, 5000-char equality, no `ELISION`. | unit | — |
| tests/test_warehouse_concurrency.py | 29 | test_reader_times_out_with_warehouse_busy_during_migration | Short-timeout reader raises while RW hold is active. SUT: `warehouse.open(read_only=True)` vs worker `hold_rw`. Asserts `WarehouseBusyError`. | integration | — |
| tests/test_warehouse_concurrency.py | 45 | test_reader_succeeds_after_migration_releases | Patient reader opens after RW hold clears. SUT: `warehouse.open(read_only=True)`, `migrate.current_version`. Asserts version equals head (`_HEAD_VERSION`). | integration | — |
| tests/test_warehouse_concurrency.py | 64 | test_writer_times_out_with_typed_error_while_readers_held | Writer times out to typed busy error while RO held. SUT: `warehouse.open(read_only=False)` vs `hold_ro`. Asserts `WarehouseBusyError`. | integration | — |
| tests/test_warehouse_concurrency.py | 84 | test_racing_migrators_serialize_without_double_apply | Racing migrators both land at head without double-apply. SUT: worker `migrate_report`, `warehouse.open`, schema queries. Asserts both exit 0/head version, schema_version row count == head, product tables present. | integration | — |
| tests/test_warehouse_home_xdg.py | 15 | test_resolve_home_prefers_stockroom_home_over_xdg | STOCKROOM_HOME wins over XDG_DATA_HOME. SUT: `warehouse.resolve_home`. Asserts path equals override and source is `HOME_SOURCE_OVERRIDE`. | unit | semantic-redundancy? |
| tests/test_warehouse_home_xdg.py | 28 | test_resolve_home_uses_xdg_data_home_when_override_unset | Uses `$XDG_DATA_HOME/stockroom` when override unset. SUT: `resolve_home`. Asserts path and `HOME_SOURCE_XDG`. | unit | — |
| tests/test_warehouse_home_xdg.py | 40 | test_resolve_home_defaults_under_local_share_when_xdg_unset | Defaults to `~/.local/share/stockroom` when both unset. SUT: `resolve_home` with patched `Path.home`. Asserts path and `HOME_SOURCE_DEFAULT`. | unit | — |
| tests/test_warehouse_home_xdg.py | 54 | test_resolve_home_does_not_create_directory | resolve_home reports path without creating it. SUT: `resolve_home`. Asserts path equals target and neither target nor xdg exists. | unit | — |
| tests/test_warehouse_home_xdg.py | 68 | test_home_dir_creates_resolved_path | home_dir creates resolved home including parents. SUT: `warehouse.home_dir`. Asserts returned path equals target and is a directory. | unit | semantic-redundancy? |
| tests/test_warehouse_home_xdg.py | 82 | test_warehouse_and_lock_paths_live_under_resolved_home | warehouse_path and lock_path nest under resolved home. SUT: `home_dir`, `warehouse_path`, `lock_path`. Asserts home and filename children under home. | unit | semantic-redundancy? |
| tests/test_warehouse_lock.py | 37 | test_flock_is_exclusive_while_held_and_releases_on_exit | Held `_flock` blocks second non-blocking acquire; exit releases. SUT: `warehouse._flock`. Asserts `OSError` while held, then successful reacquire. | unit | — |
| tests/test_warehouse_lock.py | 55 | test_open_with_backoff_returns_connection_when_unlocked | Successful open returns usable connection. SUT: `warehouse._open_with_backoff`. Asserts `SELECT 42` returns 42. | unit | — |
| tests/test_warehouse_lock.py | 65 | test_open_with_backoff_raises_warehouse_busy_on_persistent_lock | Persistent lock conflict past timeout raises WarehouseBusyError after retries. SUT: `_open_with_backoff` with fake `duckdb.connect`/clock. Asserts `WarehouseBusyError` and `calls["n"] >= 2`. | unit | — |
| tests/test_warehouse_lock.py | 93 | test_open_with_backoff_reraises_non_lock_ioexception | Non-lock IOException is re-raised without busy wrapping. SUT: `_open_with_backoff` with fake connect. Asserts `duckdb.IOException` matching injected message. | unit | — |
| tests/test_warehouse_open.py | 39 | test_warehouse_busy_error_is_an_exception | WarehouseBusyError is an Exception subclass. SUT: `warehouse.WarehouseBusyError`. Asserts `issubclass(..., Exception)`. | unit | — |
| tests/test_warehouse_open.py | 44 | test_paths_resolve_under_stockroom_home | Paths live under STOCKROOM_HOME fixture dir. SUT: `home_dir`, `warehouse_path`, `lock_path`. Asserts home and `warehouse.duckdb` / `.warehouse.lock` children. | unit | semantic-redundancy? |
| tests/test_warehouse_open.py | 51 | test_home_dir_is_auto_created | home_dir creates absent home directory. SUT: `warehouse.home_dir`. Asserts previously missing path becomes a directory. | unit | semantic-redundancy?, deliverable-fossils? |
| tests/test_warehouse_open.py | 62 | test_open_writer_on_fresh_path_returns_migrated_connection | Writer open on fresh path migrates to head schema. SUT: `warehouse.open(read_only=False)`, `migrate.current_version`. Asserts head version, product tables subset, warehouse file exists. | integration | deliverable-fossils? |
| tests/test_warehouse_open.py | 76 | test_open_reader_on_current_warehouse_returns_working_connection | Reader open on current warehouse yields usable RO conn. SUT: `warehouse.open(read_only=True)`. Asserts head version and `sessions` count 0. | integration | deliverable-fossils? |
| tests/test_warehouse_open.py | 91 | test_open_reader_on_current_warehouse_does_not_invoke_runner | Reader on current warehouse skips apply_pending. SUT: `warehouse.open` with monkeypatched `apply_pending`. Asserts head version and that runner raises if called. | integration | deliverable-fossils? |
| tests/test_warehouse_open.py | 109 | test_open_reader_has_vss_loaded | Reader open loads vss and persistence setting. SUT: `warehouse.open(read_only=True)`. Asserts extension loaded and `hnsw_enable_experimental_persistence` is true. | integration | — |
| tests/test_warehouse_open.py | 135 | test_open_with_migrate_false_skips_the_gate | migrate=False bypasses apply_pending. SUT: `warehouse.open(..., migrate=False)` with monkeypatched runner. Asserts sessions count 0 without runner. | integration | — |
| tests/test_warehouse_open.py | 153 | test_open_current_returns_read_only_current_connection | open_current yields RO connection at head. SUT: `warehouse.open_current`. Asserts head version and write raises `duckdb.Error`. | integration | — |
| tests/test_warehouse_open.py | 168 | test_open_current_refuses_stale_schema_without_migrating | open_current refuses behind-head warehouse without migrating. SUT: `warehouse.open_current`. Asserts `WarehouseStaleError` fields, message contains `stockroom migrate`, and schema stays at version 1 without later columns. | integration | — |
| tests/test_warehouse_open.py | 208 | test_migrated_warehouse_matches_locked_snapshot | Fresh open product schema matches locked head snapshot JSON. SUT: `warehouse.open`, `_introspect_schema`. Asserts introspected schema equals `SNAPSHOT_PATH` JSON. | integration | — |
