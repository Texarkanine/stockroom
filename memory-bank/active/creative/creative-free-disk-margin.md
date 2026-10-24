# Decision: Free-disk margin

## Context

The check skips when free disk cannot hold the new file plus a margin. The estimate of the new file is `doctor.live_bytes` (distinct persistent block ids, times the block size), not the warehouse's file size. The decision is the comparison that counts as "short".

A skip retries at the next session start. A copy that runs out of space mid-build leaves the started entry, and that entry is final once the time limit passes. Skipping too eagerly retries. Starting a copy that cannot fit stops the conversion until someone deletes the record.

Measured in this checkout on 2026-10-24, on a schema-file warehouse with 2000 rows of 10,000 `x` characters:

- Source file 1,847,296 bytes, live bytes 524,288
- Sibling file 1,323,008 bytes, live bytes 524,288
- Peak extra files during the copy: the sibling plus `warehouse.copy.duckdb.wal` at 20,203,821 bytes

The wal tracked the logical row text. Live bytes tracked the compressed blocks. That source was already zstd, so the check will not copy it (`already new`). The files the check does copy store `messages.text` uncompressed, so their live bytes count those blocks.

## Options Evaluated

- **One times live bytes**: skip when free space is below the live-byte estimate.
- **Two times live bytes**: skip when free space is below twice the estimate, leaving room for a wal about the size of the data plus the finished sibling.
- **Two times live bytes, plus 64 MiB**: the same comparison, with a fixed floor so a tiny estimate still leaves room for the new file's overhead.
- **Forty times live bytes**: skip unless free space covers the wal measured on the already-zstd fixture.

## Analysis

| Criterion | 1× live bytes | 2× live bytes | 2× live bytes + 64 MiB | 40× live bytes |
| --- | --- | --- | --- | --- |
| Room for the wal on an uncompressed source | The wal can be about one more copy of the rows | Wal plus a smaller zstd sibling | Same, plus overhead when the estimate is tiny | Far more than the copy needs |
| False skip on the work machine | Least likely | Only if free space is under about twice the live data | Same, unless free space is under 64 MiB | Likely. The 40× figure is the compression ratio of repeated `x`, on a file the check does not copy |
| False start, then a final overrun | Likely. The measured wal was the logical rows, not the live bytes | Unlikely for an uncompressed source | Unlikely | Unlikely |
| Simplicity | One comparison | One comparison | One comparison and one constant | One comparison, justified by the wrong fixture |

Key insights:

- The original file is already on disk. Free space has to hold the sibling and its wal, not a second copy of the original file.
- The 20 MB wal appeared because the inserted text was highly compressible and the source was already zstd. Live bytes were 40× smaller than the logical text. The check's `already new` path does not copy that file.
- On a file the check does copy, `messages.text` is uncompressed, so live bytes include those blocks. The wal is that text again, and the sibling ends smaller because it is zstd. Twice the live bytes covers both.
- A live-byte estimate of 0 would make `2 × 0` demand no free space. The copy still creates a file. A fixed 64 MiB covers that overhead without asking the work machine for another 88 GB.

## Decision

**Selected**: Two times live bytes, plus 64 MiB
**Rationale**: Twice the live bytes is the wal plus the sibling for the files this pass copies. The extra 64 MiB is the margin when the estimate is tiny. The 40× ratio is real and it belongs to a file the pass will not copy.
**Tradeoff**: A source the pass does copy whose logical rows are much larger than its live bytes can still fill the disk. That becomes a final started entry. Accepted, because the alternative is a margin taken from a fixture the pass skips.

## Implementation Notes

- Skip when `disk_free < 2 * live_bytes + 64 * 1024 * 1024`.
- Read `live_bytes` from a read-only connection while the writer flock is held. Do not migrate.
- A low-disk result is a skip. It writes the skip and does not create the sibling.
- The constant lives next to the time limit in the check module.
