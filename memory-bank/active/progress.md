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
