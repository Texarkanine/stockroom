# Algorithm Decision: Swap Backup Cleanup

## Problem

After a successful warehouse swap, `warehouse.issue147-swap.duckdb` is the pre-swap warehouse under a second name. Stockroom never removes it. On a machine that had an 88 GB warehouse, that file stays at about that size next to the new `warehouse.duckdb`. Coworkers will find an unexplained multi-gigabyte file and ask what it is.

The outcome required: once a swap has succeeded and a fortnight has passed in which a person could put the original back, remove that backup without anyone having to know its name. The exploration used 30 days. The operator set the window to 14 days.

Input is the stockroom home: `check.json`, `warehouse.duckdb`, and `warehouse.issue147-swap.duckdb`. Output is either no change, or that backup name unlinked. Nothing else is removed. `check.json` stays.

Correct means all of the following:

- The live `warehouse.duckdb` is still there, byte for byte, after the cleanup pass.
- The backup is removed only after the check record says this check version finished a swap, and only after 14 days from that swap.
- A record that is `linked`, `started`, `rehearsed`, `skip`, `mismatch`, or `already-new` keeps the backup.
- A missing backup is a no-op.
- The same pass is safe to run again.

Invariants that do not depend on the option:

- Doctor stays read-only. It already reports `backup: absent` when the name is gone.
- The backup name is exactly `warehouse.issue147-swap.duckdb`. A user's own `warehouse.duckdb.bak` is not this file.
- `os.link` does not change the file's data modification time. The backup's mtime is the old warehouse's last write, which can be long before the swap or minutes before it. It is not the swap clock. Phase B stores the swap clock in the swapped record's `started_at` (`skills/sr-search/src/stockroom/check.py`).
- On APFS, a read updates access time only when the stored access time is earlier than the modification time, unless the volume is mounted `strictatime`. macOS data volumes are not mounted that way. After the first read that follows the last write, later reads do not move access time. Access time is not "the last time someone looked." ([APFS access time](https://eclecticlight.co/2024/08/12/whats-the-time-mr-apfs-with-a-new-version-of-precize/), [`mount` `strictatime`](https://ss64.com/mac/mount.html))
- Newer rows are the wrong proof of success. The new file starts as a copy of the old one. A quiet machine adds no rows and would keep the backup forever. A bad file can still accept an ingest.
- The nightly job is optional, and an installed schedule entry is not rewritten until re-install. The job runs the on-path shim, whose engine directory is the one baked at the last rectify. The session-start hook runs `python -m stockroom.check` from the plugin root it loaded, which is the code that already performs the swap.

## Options Evaluated

- **Ingest sketch**: The next ingest that writes deletes an issue 147 backup when the backup looks a month old, the new warehouse has newer rows, and nothing has accessed the backup lately.
- **Check-pass retention**: The existing check pass, on a `swapped` record whose `started_at` is at least 14 days ago, unlinks the backup when its inode is not the live warehouse's inode.
- **Delete at swap**: The pass that writes `swapped` unlinks the backup in that same pass.

## Analysis

| Criterion | Ingest sketch | Check-pass retention | Delete at swap |
|-----------|---------------|----------------------|----------------|
| Correctness | Misses quiet machines. Backup mtime can already be a month old at the moment of the swap, so the next write can delete it immediately. Access time does not mean a recent look. | Removes the backup a fortnight after the swap the record already describes. Leaves it in place for every unfinished or failed state. | Removes the rollback in the same pass that creates it. No interval in which a person can put the original back. |
| Simplicity | A new policy inside ingest, with three clocks, two of which do not mean what they appear to mean. | One predicate on the record the check pass already loaded, under the flock it already holds. | The fewest lines. It drops the retention the cleanup exists to preserve. |
| Reuse | Ingest does not own this file. | The check pass already treats `swapped` as stop and already names this backup. | Same pass that writes `swapped`. |
| Maintainability | Two subsystems have to agree on "the migration is finished." | One owner. The user guide's "never deletes" sentence is the contract that changes. | The restore procedure becomes false as soon as the swap finishes. |
| Time | One stat and a row scan of the warehouse on a night that writes. | Two stats and a timestamp compare. No warehouse read. | One unlink on the swap pass. |
| Space | None beyond the process that is already ingesting. | None. | None. |

Key insights:

- The goal is "a fortnight after a finished swap, the extra copy is gone." It is not "the next ingest observed new chats" and it is not "nobody opened the old file."
- Backup mtime fails an idle-then-swap machine: the file can be older than a month when phase B runs, and the next ingest that writes deletes the only rollback immediately.
- APFS access time sticks after the first post-write read. A person who inspected the backup yesterday can still show an access time from weeks ago. Requiring a stale access time does not protect them, and a fresh one can block cleanup forever on a volume that does update it.
- Newer rows never appear on a machine that is done ingesting history and has no new chats. That is a successful migration. The gate would keep the 88 GB file.
- A new line in the nightly schedule does not reach jobs already installed. Ingest code does not run from the updated plugin until the shim is rebaked. The check hook does run from the plugin root that just loaded. The machines that already swapped are machines where that hook ran.
- `check.json` is the latch that keeps a restored old warehouse from being swapped again, and it is the clock for this cleanup. It is tiny. Cleaning it up is a different decision. This one leaves it, with status `swapped`.

## Decision

**Selected**: Check-pass retention
**Rationale**: The check record's `started_at` is the swap time the program wrote, and the session-start check is the pass that already decides the swap is finished. A fortnight later that same pass unlinks the one backup name, after confirming it is not the live warehouse's inode. The operator set 14 days; the exploration had used 30.
**Tradeoff**: A machine that never starts another session keeps the backup until one does. That is the same hook the swap already depends on. Ingest, file mtime, newer rows, and access time are not part of the predicate.

## Implementation Notes

- Constant beside `PHASE_B_WAIT_SECONDS`: 14 days, `14 * 86400` seconds. Compare the same way as the rehearsal wait: delete when `now >= started_at + retention`.
- Run it from `_acquired` while the writer flock is held, only when `next_action` returned `stop` because status is `swapped`. Do not run it for `mismatch` or `already-new`.
- Require `check_version` 1 and a numeric `started_at`. A `swapped` record without `started_at` keeps the backup.
- `stat` the backup and `warehouse.duckdb`. Unlink the backup only when both are files and their inode numbers differ. Same inode means the backup name is still a link to the live file; leave it.
- Unlink only `warehouse.issue147-swap.duckdb`. Do not glob `warehouse.issue147-*`. Do not remove `check.json`, `warehouse.duckdb`, or a `.wal`.
- A missing backup is success. Do not rewrite `check.json` on the way out. Doctor then reports `backup: absent` and the check word stays `swapped`.
- The published restore steps say that a `swapped` check does not touch the backup, and they tell the reader to keep `check.json`. After this ships, those steps are true only inside the fortnight. The guide has to say that the backup is removed after that, and that putting the original back has to happen before then. Opening a new session after the deadline can remove the file in the background.
- Deleting that file by hand while the check word is `swapped` is the same end state. A work machine does not have to wait for the fortnight.
