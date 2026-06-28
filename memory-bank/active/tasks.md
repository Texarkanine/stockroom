# Current Task: Workspace identity vs. real path (`project_id` + `cwd` recovery)

* Task ID: `p1-data-backbone-m4-cwd-recovery`
* Complexity: Level 2
* Type: enhancement (schema `0002` migration + ingest path-model fix)

Split `sessions.project_path` (lossy, fabricated) into `project_id` (verbatim slug grouping identity) and best-effort `cwd` (real path, NULL when unknown); drop the lossy `decode_project_dir`; ship as a forward `0002` migration through the m2 framework. Design + evidence: `planning/spikes/cwd-recovery/README.md`.

<!-- Stub created at COMPLEXITY-ANALYSIS. The Level 2 PLAN phase populates the checklist per the level-2 planning rules. -->
