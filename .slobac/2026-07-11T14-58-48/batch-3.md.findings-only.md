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

