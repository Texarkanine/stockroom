# Project Brief

## User Story

As a stockroom user, I want Claude Code token totals to count each API response once, so that session and dashboard token figures match what Claude actually used.

## Use-Case(s)

### Confirm the report

Determine whether `.scratch/bureport.md` describes a real bug: Claude Code writes one transcript line per content block, each line repeats that response's usage, and stockroom stores and sums those copies.

### Fix ingestion if the bug is real

If the overcount is real, change ingestion so each API response's tokens are counted once. Include the forked-subagent copy case if that is also real.

### Correct rows that can still be recomputed

Sessions whose source transcripts are still on disk should be corrected by re-ingest.

### Correct vanished transcripts only when certain

A direct rewrite of warehouse rows whose transcripts are already gone is in scope only when the correction is fully correct and idempotent. An approximate collapse does not meet that bar. If that bar cannot be met, leave those rows alone and say so.

## Requirements

1. Investigate the report against the current ingest, schema, and token rollup before changing code.
2. If the bug is real, fix it so Claude token figures count each API response once.
3. Re-ingest or otherwise recompute sessions whose source transcripts still exist.
4. Do not rewrite vanished-transcript rows unless the correction is fully correct and idempotent.

## Constraints

1. Warehouse correction for sessions gone from disk is valid only at full confidence, and only if the operation is idempotent.
2. An approximate collapse of consecutive assistant rows is not that correction.
3. Cursor token figures are out of scope unless investigation shows the same bug there.

## Acceptance Criteria

1. The investigation states whether the reported overcount is a real bug, with evidence from the code and a reproduction shaped like the report.
2. If it is real, new ingestion of a multi-block Claude response counts that response's tokens once, including a forked-subagent copy if that case is real.
3. Sessions whose transcripts remain on disk can be brought in line with the corrected counts.
4. Vanished-transcript rows are rewritten only by a correction that is fully correct and idempotent; otherwise they are left unchanged and the limit is stated.
