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
