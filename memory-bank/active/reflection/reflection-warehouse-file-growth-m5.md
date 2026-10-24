---
task_id: warehouse-file-growth-m5
date: 2026-10-24
complexity_level: 3
---

# Reflection: warehouse-file-growth, milestone 5 (verified newer-format copy)

## Summary

`copy_warehouse` builds `warehouse.copy.duckdb` from the schema file, copies the original's rows, checks the sibling, and leaves it. The original stays read-only. QA passed with advisories and no build change.

## Requirements vs Outcome

The plan shipped. `apply_pending` and `build_warehouse` take keyword-only `through` and still apply every later migration by default. The sibling is created at the storage version, migrated only through the original's schema version, and filled from the current database's base tables. `EXCEPT ALL` runs both ways. Columns, full constraint rows, non-primary indexes, zstd-stripped table SQL, the view name, and view columns are compared with nothing attached. View SQL is not compared. Success returns both sizes and both durations and leaves the sibling. Failure deletes it. The backup, the flock, and the live path stay out. A populated large column must store persistent zstd. An empty column has no data segment and does not fail, which is what the one-row chain needs. That empty-column rule is the one behavior the plan's sentence did not spell out. The two-generation test still requires zstd on both columns.

## Plan Accuracy

The sequence and the file list were right. The preflight revision held: after `ATTACH`, `duckdb_tables()` lists both databases, and `constraint_index` shifts, so the row copy filters to the current database and the catalog compare opens each file alone. The first implementation passed those tests. The test surprise was local. A monkeypatch of `migrations_dir` whose callable calls `discover()` recurses, because `discover()` calls `migrations_dir()`. The existing later-migration test builds the folder first. The new tests had to do the same. The named challenges (vss only in the child, no checkpoint on the schema-8 file, no `COPY FROM DATABASE`, no rename onto the original) did not become defects.

## Creative Phase Review

No creative phase. The Level 4 milestone had already fixed the design, and preflight closed the catalog question before build.

## Build & QA Observations

The `through` test went red because version 10 was applied, then green when the predicate landed. The copy tests went red on `NotImplementedError`, then green together: 22 storage tests, then the engine suite (1110 passed, 36 skipped, torch installed), 4 coverage-collection tests, and 134 JavaScript tests. Ruff, schema docs, released migrations, and REUSE passed. QA passed on the first run. Its advisories match gaps the plan and the preflight already named: the ceiling is not positively tested, a dropped view is not fault-injected, the schema-8 assertion catches the `CopyError` base class, and `verify_copy`'s docstring omits the empty-column case.

## Cross-Phase Analysis

Preflight's fixable failure is what kept the row copy from inserting each table twice. The revised plan was the one that built. The `through` advisory was written during preflight, left out of the plan on purpose, and returned by QA unchanged. It did not become a defect, and build did not widen the tests to swallow it. The empty-column zstd rule came from the one-row fixture the plan required, not from a new design.

## Insights

### Technical

Patching `migrations.migrations_dir` with a callable that calls `discover()` recurses. Build the folder, then point the patch at that path.

An empty zstd column has no data segment. A check that requires a segment rejects a warehouse that has no tool calls. Milestone 6's "already new" test has the same shape: zstd is visible only where rows exist.

### Process

The preflight loop did the expensive work. The `ATTACH` double-list would have failed the first green run. The advisory that stayed out of the plan came back from QA as an advisory, not as rework.
