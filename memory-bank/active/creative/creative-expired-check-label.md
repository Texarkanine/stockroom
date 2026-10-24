# Decision: Doctor label for an expired started entry

## Context

The pass writes a started entry before it builds, with the phase, the start time, and the time limit. `signal.alarm` then uses the default terminate action. The process cannot write a second status when the alarm fires, and a Python handler would not interrupt a DuckDB call.

Doctor has to show that entry on one read-only line. Inside the limit the line says running, not crash. The milestone also lists crash and overrun as final outcomes. The decision is the word doctor prints once the limit has passed, and the word a later pass treats as final.

## Options Evaluated

- **crash**: after the limit, the line says crash. Overrun is the same entry under another name.
- **overrun**: after the limit, the line says overrun. A crash that nobody observed inside the window uses that same word once the limit has passed.
- **flock distinguishes them**: inside the limit, a held writer flock means running and a free flock means crash. After the limit the line says overrun.

## Analysis

| Criterion | crash | overrun | flock distinguishes them |
| --- | --- | --- | --- |
| Inside the limit | running | running | running only while the flock is held. A dead pass would say crash, which the milestone forbids for a started entry still inside its limit |
| Uses a signal handler | No | No | No |
| One cause, one word | The clock and a crash share the word crash, so overrun never appears | The clock's word is overrun. A crash seen only after the limit shares it | Two words, and the inside-limit word depends on a flock other writers also hold |
| Later pass | Expired started is final | Expired started is final | Same, with an extra way to be wrong while ingest holds the flock |

Key insights:

- The only durable signal is the started entry plus the clock. The alarm does not get to write.
- The milestone's sentence is about the inside-limit line: say running, not crash. It does not require the past-limit line to say crash.
- Overrun is the outcome the clock can actually show. Crash, as a separate spelling, would need to know that the process died early. The flock cannot say that, because ingest, embed, and the nightly job hold the same flock.

## Decision

**Selected**: overrun
**Rationale**: After the limit, doctor prints overrun and a later pass treats the entry as final. Inside the limit, doctor prints running and a later pass does not build, so a dead pass is not called crash while its limit still has time left.
**Tradeoff**: A pass that dies in the first second is shown as running until the limit, then as overrun. The word crash is not printed. Both causes stay final, and deleting the record file is still how a person runs the check again.

## Implementation Notes

- Doctor reads the record and does not write it.
- `started` and `now < started_at + limit_seconds` displays `running`.
- `started` and `now >= started_at + limit_seconds` displays `overrun`.
- `run_check` treats both of those entries as "do not build". The expired one is final, so the pass does not replace it. The unexpired one is left in place so the owner of the flock can finish.
- The line is one `check` fact. The value carries the display word, the measurements the record has, and the record path.
