# Progress

Start the check from the Claude Code and Cursor session-start hooks. Session start returns at once. The launch detaches the way the dashboard does, in a new session that keeps none of the hook's output streams. Cursor's `beforeSubmitPrompt` hook does not launch the check. A test runs the launched entry point against a final record and proves it does not build. A stockroom home with no warehouse still ingests from the schema file, embed and semantic answer, and the launched check records the warehouse as already new and builds nothing.

**Complexity:** Level 2

## 2026-10-24 - COMPLEXITY-ANALYSIS - COMPLETE

* Work completed
    - Checked milestone 6 after its reflect phase
    - Removed the milestone 6 sub-run files
    - Classified milestone 7, the session-start launch, as Level 2
* Decisions made
    - Level 2. The check pass already exists. This sub-run starts that pass from the two session-start hooks and returns at once. The L4 milestone already fixes the detach, which hooks launch, and the new-install proof, so this sub-run does not reopen architecture
* Insights
    - Shipping this milestone turns the rehearsal and the swap on for every install that updates
