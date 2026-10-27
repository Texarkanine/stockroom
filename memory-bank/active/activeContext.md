# Active Context

## Current Task: Fortnight backup reclaim and finished-home short-circuit
**Phase:** PLAN - IN-PROGRESS

## What Was Done
- Operator revised the parent gate after the first preflight. The hook stays. The process it already starts returns when a child would leave the disk alone, including a swapped backup still inside the fortnight.
- The child still starts for an unfinished migration, and when a version-1 `swapped` backup is a file, `started_at` is a number, the fortnight has elapsed, and the inodes differ.
- The previous preflight status does not cover this gate.

## Next Step
- Rewrite the Level 3 plan to that gate.

