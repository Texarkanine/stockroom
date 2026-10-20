# Progress

Make torch import and load failures on `stockroom semantic` and `stockroom embed` print the command that fixes them, and make the agent-facing text name that same command. Judge the ticket's options first and implement the justified design. Open a non-draft pull request when the work is finished.

**Complexity:** Level 2

## 2026-10-20 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Restated the request against issue #144 and recorded the operator's addition: a better design is allowed when it is justified.
    - Classified the task as Level 2.
* Decisions made
    - Level 2, not Level 3. The change stays inside one subsystem (torch failure reporting on semantic and embed). The design choice is which existing surface should carry the remedy, not a new architecture.
* Insights
    - `doctor smoke` already names `stockroom shim ensure-env` when a freeze exists. The gap is the traceback the agent actually sees, and the skill row that tells it not to retry.

## 2026-10-20 - PLAN - COMPLETE

* Work completed
    - Traced the failure to the uncaught `encoder_factory()` calls in `semantic.main` and `embed.main`, and to the `sr-semantic` row that matches the traceback.
    - Wrote the test-first plan in `memory-bank/active/tasks.md`.
* Decisions made
    - Do not use the ticket's two-way split for every encoder failure. A usable freeze plus an encoder exception is a bad wheel; `stockroom shim ensure-env` would reinstall it.
    - Share `doctor smoke`'s two remedy strings from `embed.py`. Only `ModuleNotFoundError` for `torch` takes the missing-import branch. Other construction exceptions take the re-pick branch. Other import errors propagate.
    - Update the skill, the torch-contract sentence, and the disagreeing torch-page headings. Do not add a `doctor` command or an `sr-search` error row.
* Insights
    - Catching inside `BgeEncoder.__init__` would change `doctor smoke` and the live constructor tests. The CLI call is the layer that today prints the traceback.

## 2026-10-20 - PREFLIGHT - COMPLETE

* Work completed
    - Validated implementation plan against codebase conventions and existing tests in `test_semantic.py`, `test_embed.py`, and `test_doctor.py`.
    - Verified TDD plan ordering, stubbing, and separation between executable units and prose documentation.
    - Wrote `PASS WITH ADVISORY` to `memory-bank/active/.preflight-status`.
* Decisions made
    - Validated that sharing remedies from `stockroom.embed` avoids import cycles and cleanly centralizes `doctor` and CLI diagnostics.
* Insights
    - Supplying an optional `app_dir` parameter to `encoder_construction_error` allows decoupling environment resolution for cleaner test isolation.

## 2026-10-20 - BUILD - COMPLETE

* Work completed
    - Added the shared torch remedy in `embed.py` and wired `semantic.main`, `embed.main`, and `doctor.run_smoke` to it.
    - Tests cover missing torch with and without a usable freeze, an unusable freeze, an encoder load failure, a non-torch import error, and a space in the engine path.
    - Aligned the semantic skill, the torch contract, the torch troubleshooting page, and the load-page sentence.
    - `make ci` passed (1018 pytest passed, 38 skipped).
* Decisions made
    - Left `encoder_construction_error` calling `default_app_dir()` itself. The preflight advisory for an injected path is not needed; the quoting test monkeypatches the function.
    - `docs/user-guide/load/basic.md` was not in the plan file list. It quoted the old heading, so the sentence now matches the page.
* Insights
    - The two propagate tests were already green before the catch existed. They stay as the lock that a missing locked dependency is not relabeled as torch.

## 2026-10-20 - QA - COMPLETE (PASS WITH ADVISORY)

* Work completed
    - Reviewed the build diff against the plan on KISS/DRY/YAGNI/completeness/regression/integrity/documentation; no implementation edits made.
    - Re-ran `test_semantic.py`, `test_embed.py`, `test_doctor.py`: 96 passed, 4 skipped. Ruff check and format clean on all five touched Python files.
    - Wrote `memory-bank/active/.qa-validation-status` and recorded the result in `tasks.md`.
* Decisions made
    - PASS WITH ADVISORY: no build changes required. The single advisory is a test-coverage nit (no test pins the `torch.<submodule>` prefix branch), not an acceptance blocker.
* Insights
    - The `try` wrapping only `encoder_factory()` on both CLIs is what keeps a search-time bug from being mislabeled a wheel remedy; worth keeping that narrow in future edits.

## 2026-10-20 - REFLECT - COMPLETE

* Work completed
    - Compared the build to the plan and wrote `memory-bank/active/reflection/reflection-torch-failures-help.md`.
    - Left `productContext.md`, `systemPatterns.md`, and `techContext.md` unchanged. The new error line is a torch-subsystem contract already stated in `system-model.md` and `embed.py`. Nothing in the three persistent files is now false.
* Decisions made
    - The ticket's two-way split stays rejected. ensure-env is only the missing-import remedy.
* Insights
    - The agent followed the skill row, not the troubleshooting page. Both the stderr line and that row had to name the command.
