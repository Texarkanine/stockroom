# Project Brief

## User Story

As a human querying the warehouse (and secondarily as an agent using `sr-query`), I want a visual warehouse schema in the docs and in the `sr-query` skill so I can form SQL without rediscovering tables and relationships each time.

## Use-Case(s)

### Use-Case 1

A human opens the documentation, sees an ERD of the warehouse, and writes a join query from that picture.

### Use-Case 2

An agent following `sr-query` has a committed schema resource at skill runtime (hub layout equals install layout) and does not have to rediscover the schema via `information_schema` first — though live introspection remains valid as a check.

### Use-Case 3

A contributor changes a migration. They regenerate the schema artifacts locally. CI fails the PR if the committed schema docs/skill resource differ from what the generator produces.

## Requirements

1. Show a visual warehouse schema (Mermaid ERD or equivalent proper diagram) in the `sr-query` skill (a ride-along resource is acceptable).
2. Show the same visual schema in human docs.
3. Authoritative DDL remains the migration chain; generated artifacts are derived, committed, and kept in lockstep.
4. CI fails when schema-affecting changes land without a commensurate generator output update (diff against regenerated artifacts).
5. An average local developer can run the same generator CI runs, so they can update the committed artifacts and clear the diff.
6. Prefer a generation technique that does not require standing up a dummy DuckDB warehouse if an equally faithful approach exists; technique is secondary to (4) and (5).
7. Generator and CI work without a local stockroom plugin install on the contributor machine.

## Constraints

1. Dual-manifest plugin: committed layout equals install layout. Do not generate skill files on main after install; the skill resource must be a committed file.
2. Do not break the "what you see on the hub is what you get" contract.
3. Skill payload under `skills/**/SKILL.md` and `skills/**/references/**` is PPL-S; generator/docs/CI stay in their existing license lanes.
4. Architecture currently does not list DDL in `docs/architecture/warehouse.md`; the visual belongs where humans consult it to form queries, without turning Architecture into a DDL dump.
5. This checkout is not set up for local stockroom development; implementation should not assume a working on-path `stockroom` or a live warehouse.
6. Forward-only numbered SQL migrations under `skills/sr-search/src/stockroom/migrations/` remain the schema source of truth.

## Acceptance Criteria

1. A visual schema (ERD or equivalent) is present in `sr-query` (skill or ride-along reference) and in human docs.
2. The visual reflects the migrated warehouse schema (tables, views, keys, relationships), not a hand-maintained sketch that can silently drift.
3. A documented, locally runnable generator produces those committed artifacts.
4. CI regenerates (or equivalently verifies) and fails if the working tree differs.
5. Plugin install still requires no build step; skill consumers see the committed resource as-is.
6. Live `information_schema` discovery in `sr-query` may remain as a check, but is no longer the only schema picture.
