---
task_id: warehouse-file-growth-m4
date: 2026-10-23
complexity_level: 2
---

# Reflection: warehouse-file-growth, milestone 4 (doctor storage report)

## Summary

`stockroom doctor probe` now reports warehouse file size, block use, reclaimable space, storage format, free disk, and the swap backup, and it does not write. The report matches the milestone 4 plan. QA passed with advisories and no build change.

## Requirements vs Outcome

Every planned behavior shipped. The check-record line stayed out for milestone 6. The preflight overhead constant stayed out, so `reclaimable-bytes` is the file size minus the distinct persistent block-id union. A healthy new warehouse therefore reports most of its file as reclaimable; milestone 6's low-disk test inherits that estimate. One extra test covers a pragma failure after connect. The plan required that outcome, and the connect-failure test does not reach it. Help uses a raw description so the storage phrases survive wrapping.

## Plan Accuracy

The sequence and the file list were right. The named challenges were the ones that mattered: do not call `home_dir` or `open_current`, release the writer flock before the read-only connect, and point existing probe callers at an empty temp home. The surprise was argparse wrapping `--help` and splitting `free disk` across lines.

## Build & QA Observations

The new tests failed on the empty stubs for the missing fact keys, then passed together. `make ci` passed: 1098 pytest passed, 39 skipped, and 134 JavaScript tests passed. QA passed on the first run. Its advisories (the schema-head branch falls through, the reclaimable formula, the duplicated block-id oracle) match decisions already in the plan.

## Insights

### Technical

argparse's default help formatter replaces a space with a newline, so a test for a two-word phrase can fail on a correct sentence. `RawDescriptionHelpFormatter` keeps the phrase. A future `--help` assertion should assume wrapping, or the description should be raw.

### Process

Nothing notable.

### Million-Dollar Question

If probe had taken the warehouse home as an argument from the start, a test could not open the live warehouse by forgetting `STOCKROOM_HOME`. The existing `probe_facts` signature was left alone, and `storage_facts` takes the home and an injectable connect instead. That split is the smaller change against the signature the plan froze.
