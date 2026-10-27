# Active Context

## Current Task: Fortnight backup reclaim and finished-home short-circuit
**Phase:** BUILD - IN-PROGRESS

## What Was Done
- Preflight passed with advisory. The checkpoint before build was already committed.
- Build is applying the advisories: one `_swap_backup_due` for the gate and the unlink, parent `OSError` from `stat` starts the child, the existing expired-start test carries a fortnight-old `started_at`, and `docs/architecture/lifecycle.md` gets one sentence.

## Next Step
- Unit 3: say the backup stays for a fortnight, and that a session during that fortnight does not remove it. One sentence in `docs/architecture/lifecycle.md`.
