# Current Task: Schema field enumeration + locked DDL

**Complexity:** Level 3

Milestone 1 of the `p1-data-backbone` L4 project. Plan/creative content is produced by the L3 Plan phase. The operator has requested a hard stop once the initial schema is drafted, to review all enumerated fields and the recommended kept subset before the DDL is locked.

## Carried-forward advisories (from L4 preflight)

- Milestone 1 authors the DDL directly as the `migrations/0001` file (keeps milestones 1 and 2 non-overlapping; no later file move).
- Milestone 1 commits the field-enumeration record and shared real + pathological transcript fixtures as durable artifacts, reused by milestone 3's ingest tests and future-harness onboarding.
- Clean-room boundary: Claude Code support reverse-engineered from the harness's own on-disk format only; `cursor-warehouse` schema reused only via the operator-vetted provenance procedure; schema derived empirically regardless.
