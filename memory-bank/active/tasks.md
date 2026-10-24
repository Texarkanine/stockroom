# Current Task: warehouse-file-growth, milestone 6 (check pass)

**Complexity:** Level 3

## Open Questions

### 1. Check time limit — resolved

**Decision:** 4 hours (`14400` seconds). See `memory-bank/active/creative/creative-check-time-limit.md`.

The pass ends itself with `signal.alarm` and the default terminate action. The milestone does not say how many seconds that limit is.

Why it is ambiguous: the alarm is a ceiling for a stuck pass, not the normal runtime. A short ceiling can mark a slow but healthy copy as a final overrun. A long ceiling is how long a writer waits when the pass is stuck. Both are viable.

Constraints:

- Overrun and a crash are final for that check version. A false overrun does not retry until the record file is deleted.
- The process must actually die, including during a DuckDB call, so the OS releases the writer flock.
- No handler may catch the alarm and keep going.
- Measured on this machine after the index drop: a zstd copy of the live tables was 288 MiB and took 5.7 s. The work machine's warehouse file is 88 GB, and that file is not the size the disk check uses.
- Take the simpler option whenever it cannot lose a warehouse.

### 2. Free-disk margin

The brief says free disk must cover the new file plus a margin, and the new file's size is estimated from live data size, not from the warehouse file size. The margin is not a number.

Why it is ambiguous: `doctor.live_bytes` is the persistent block-id union. Milestone 4 found that a healthy new file reports most of its size as reclaimable, so live bytes can sit well below the file that gets written. A mid-copy disk-full leaves a started entry, and that entry becomes final once the time limit passes. A margin that is too large skips, and a skip retries.

Constraints:

- Skip when free disk is short. A skip is not final.
- Use `doctor.live_bytes`, not the original file size. The work machine's 88 GB file must not skip merely because the file is large.
- Do not start a copy that is expected to run out of space.

### 3. Doctor label for an expired started entry

Before it builds, the pass writes a started entry with its phase, start time, and time limit. The alarm's default action kills the process, so the pass cannot write a later status. Doctor shows a started entry that is still inside its limit as running, not as a crash. The milestone also names overrun as its own final outcome.

Why it is ambiguous: crash and overrun leave the same started entry. Two labels would require a handler, and a Python handler does not interrupt a DuckDB call.

Constraints:

- Inside the limit, the line says running.
- Past the limit, later runs do nothing except delete a leftover sibling.
- Doctor stays read-only and prints one line in the storage section.
