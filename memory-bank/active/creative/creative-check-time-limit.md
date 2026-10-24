# Decision: Check time limit

## Context

The check pass sets `signal.alarm` and leaves the default terminate action in place. The decision is the integer number of seconds that alarm waits.

A healthy pass on this machine's post-drop tables copies about 288 MiB in 5.7 s and then releases the writer flock. The alarm matters when the pass is stuck, and when a legitimate copy is slower than the ceiling. Overrun is final for that check version. The next session start does nothing until someone deletes the record file. A ceiling that fires during a real copy stops the conversion. A ceiling that is very long is how long ingest, embed, or the nightly job waits behind a stuck pass.

Constraints: the process dies, including inside a DuckDB call, and the OS releases the flock. No signal handler may keep the pass alive. One constant is preferable to a formula. The work machine's warehouse file is 88 GB; the copy size follows live data, which is not measured on that machine.

## Options Evaluated

- **15 minutes**: one constant, short enough that a stuck pass barely delays the nightly job.
- **1 hour**: one constant, enough for an 88 GB file at roughly 100 MB/s across a few full reads.
- **4 hours**: one constant, enough for an 88 GB file at roughly 30 MB/s across about four full reads (copy, verify, and the hash).
- **Scaled to live bytes**: the ceiling grows with `doctor.live_bytes`, so a large file gets more time.

## Analysis

| Criterion | 15 minutes | 1 hour | 4 hours | Scaled to live bytes |
| --- | --- | --- | --- | --- |
| False final overrun | Likely if live data is tens of GB on a slow disk | Possible below about 100 MB/s on an 88 GB live file | Unlikely on the operator's machines; still possible below about 25 MB/s | Lowest, if the rate in the formula is honest |
| Wait while stuck | 15 minutes | 1 hour | 4 hours | Unbounded if live bytes are large |
| Simplicity | One constant | One constant | One constant | A rate, a pass count, and a floor to test |
| Data loss | None. The original stays. | None | None | None |

Key insights:

- The alarm is not the expected runtime. A pass that finishes clears the flock when it finishes. The constant is only the stuck-pass ceiling.
- Overrun does not delete a warehouse, and it also does not retry. A false overrun is the failure that needs a person. A long wait needs nobody if the pass is merely slow.
- Phase B reads the original more than once (build, verify, then the hash). A one-pass estimate is short.
- A scaled ceiling adds a second design (what rate, what happens when live bytes are wrong) for a number that a constant can cover on the machines this project runs on.

## Decision

**Selected**: 4 hours
**Rationale**: 14400 seconds is one constant, and it sits above a slow multi-pass copy of an 88 GB live file at about 30 MB/s. The shorter constants can mark that copy final. The scaled formula is more machinery for the same goal.
**Tradeoff**: a stuck pass holds the writer flock for up to 4 hours. Ingest, embed, and the nightly job wait that long, then continue. That wait is accepted because a shorter ceiling can stop the conversion until the record file is deleted.

## Implementation Notes

- `TIME_LIMIT_SECONDS = 14400` lives in the check module.
- The process entry point calls `signal.alarm(TIME_LIMIT_SECONDS)` and does not install a handler. It calls `signal.alarm(0)` after a pass that returns. A pass that is still inside `alarm` dies with the default action, and the `finally` does not run.
- `run_check` does not set an alarm. In-process tests call `run_check`. The limit test runs the entry point in a child process with a short limit and a copy that sleeps.
