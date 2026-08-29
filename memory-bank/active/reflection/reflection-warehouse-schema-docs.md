---
task_id: warehouse-schema-docs
date: 2026-08-29
complexity_level: 3
---

# Reflection: warehouse-schema-docs

## Summary

Shipped a query-facing Mermaid ERD generated from the head schema golden and `-- @rel` / `-- @rel-none` comments in the migration SQL, committed as the `sr-query` skill SSOT and exposed to humans via an Advanced docs symlink, with Make/CI lockstep. Two QA rounds failed for real reasons (a non-rendered view marker, then dropped column-meaning guardrails); both were fixed before PASS.

## Requirements vs Outcome

Every brief requirement landed: visual schema in the skill and in human docs; migrations remain DDL source of truth; generator is stdlib `python3` with no dummy DuckDB, no plugin install, and no engine venv; CI/`make schema-docs-check` fail on drift; hub layout still equals install layout. Live `information_schema` stayed as a verify query.

Two additions were not in the original brief and were the right ones: `@rel` comments as the edge SSOT (operator took a preflight advisory instead of a Python `RELATIONSHIPS` list), and a compact SKILL meaning note after QA showed that deleting the catalog also deleted facts the ERD cannot draw. `-- @doc` / harvesting inline SQL comments as a data dictionary was proposed in preflight and rejected: layered migrations are a write log, not a glossary.

## Plan Accuracy

The 10-step TDD sequence (parser and renderer, then real `@rel` coverage, then SSOT, symlink, Make, CI, skill, docs, contributor loop, memory-bank pointers) matched the files that actually changed. Surprises were almost all about *visibility* and *residual prose*, not about missing components:

- `UV_RUN` cwd is `skills/sr-search`, so repo `scripts/` is `../../scripts`, not `../scripts`.
- CI does not call `make lint`, so the ruff lane for `scripts/` had to be duplicated on the engine job.
- `docs/advanced/.pages` has no wildcard, so the nav entry had to land with the symlink.
- Empty-PK → "view" was planned; implementing it as `%% view:` satisfied a source-text test and failed a reader.

The identified challenges (Mermaid type sanitization, no DB FKs, view-vs-table in the golden) were real. The two that actually delayed acceptance were not on that list: comments that do not render, and catalog deletion that also deleted guardrails.

## Creative Phase Review

Creative was skipped: dummy DuckDB vs head golden was decided in complexity analysis, dual-audience placement followed the cookbook, and the operator chose `@rel` from a preflight advisory. That was enough. The gap creative would have been useful for — "what must remain in prose when the catalog dies" — was not flagged as an open question, so it waited for QA.

## Build and QA Observations

Build of the structural pipeline was smooth once the plan named `@rel` and the CI ruff path. Tests are behavioral (render, parser, coverage failures, write/check, symlink, Make pin) and did not lock SKILL wording or CI YAML text.

QA round 1 caught that `%%` is a Mermaid comment, so `session_token_usage` looked like a table. The existing view test matched `view` anywhere in the fence, including comments. Rework used official entity aliases `name["name (view)"]`.

QA round 2 accepted the aliases and failed the catalog deletion: `project_id` / `cwd` / `workspace_key` / `entrypoint` roles, thinking not captured, and tool-inputs-only had vanished from the skill payload. Plan unit 7 said keep join rules, token-grain guidance, the `tool_input` JSON guardrail, and `_sync_state`; it did not list those other meanings. Compact guardrails restored them without bringing back the version-pinned column dump.

QA round 3 passed. Advisories (uniform `||--o{` cardinality, duplicated `_contradiction` in coverage, two ruff invocations vs CI's one) were not blocking.

## Cross-Phase Analysis

Preflight paid for itself: it found the unlinted generator, the link-free dual-audience body, the missing `.pages` entry, and the `@rel` idea. Operator-folded advisories became plan steps; the `@rel` rewrite added a tenth unit and a second preflight. That cost was cheaper than discovering a Python edge list nobody updates.

The first QA failure was an implementation shortcut against a plan that said "drawn as views" without specifying a rendered Mermaid construct. The second was a planning gap: "delete the catalog" without an explicit residual-prose list. Both are the same shape — a generated picture replaced something humans used to read, and we under-specified what must still be readable.

Skipping creative did not hurt the ERD. It did mean the structure-vs-meaning split was discovered in QA instead of written into unit 7.

## Insights

### Technical

- Mermaid `%%` never appears in the rendered ERD. A visible view label is an entity alias (`name["name (view)"]`); relationship lines keep the SQL name. Tests must assert that alias and reject comment markers, not search for the word `view` in the source.
- Schema documentation splits cleanly: goldens plus `@rel` own current *structure*; SKILL / Architecture own *meanings* the boxes cannot say. Do not generate a glossary from the migration chain — older files can still contain a sentence a later migration made false.
- From `skills/sr-search` (`uv --directory` / Make `UV_RUN`), repo `scripts/` is `../../scripts`. `../scripts` is `skills/scripts`.

### Process

- When a plan deletes a hand-maintained catalog in favor of a generated picture, write the residual prose list in that same unit: which facts the picture cannot carry and where they live. "Keep join rules" is not enough.
- A test that can pass on non-rendered syntax is not a test of the visual. Assert the construct the renderer will show.
- Preflight advisories the operator accepts should be folded before Build; this task's `@rel` rewrite was the right kind of cheap radicalism.
