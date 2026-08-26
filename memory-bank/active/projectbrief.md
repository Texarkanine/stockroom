# Project Brief

## User Story

As a Stockroom user, I want Cursor sessions ingested after ~20 August 2026 to carry model information again, so that search, SQL, and the dashboard can still attribute work to a model.

## Use-Case(s)

### Diagnose the cutoff

Determine why Cursor rows after ~2026-08-20 have no model fields while older rows still do. The working guess is a Cursor schema or spec change; confirm or replace that guess with evidence.

### Restore ingest if Stockroom is the gap

If Stockroom's Cursor ingest is missing the new shape, patch it so model fields populate again.

## Requirements

1. Diagnose the actual cause of missing Cursor model information after ~2026-08-20.
2. If ingest is the problem, patch Stockroom so it extracts model fields from the current Cursor format.
3. Keep reading the pre-change Cursor format as well as the post-change format.

## Constraints

1. Backwards compatibility is required: both Cursor formats must be understood.
2. Patch only if required — do not change ingest if Cursor simply stopped writing model data.
3. Stay inside the existing harness-labeled warehouse meaning of `messages.model` / `sessions.models`.

## Acceptance Criteria

1. The cause of the August 20 cutoff is identified with evidence (source files, schema, or ingest path).
2. If a Stockroom patch is required, new Cursor sessions ingest with model fields populated, and fixtures or sessions in the old format still ingest correctly.
3. If no Stockroom patch is required, that conclusion is documented and no speculative parser change ships.
