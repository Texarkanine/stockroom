# Active Context

## Current Task: warehouse-file-growth, milestone 4 (doctor storage report)
**Phase:** QA - COMPLETE (PASS)

## What Was Done
- `stockroom doctor probe` reports file size, used blocks, free blocks, a reclaimable estimate, the storage format, free disk, and `warehouse.issue147-swap.duckdb` when that file exists
- The report does not create a home, open a missing warehouse, migrate a behind-head file, or keep the writer lock
- `live_bytes` is the distinct persistent block-id union times `block_size`. The preflight overhead advisory stays advisory
- Help text and the contributor probe comment name the storage facts
- `make ci` passed: 1098 pytest passed, 39 skipped; 134 JavaScript tests passed

## Files
- `/home/mobaxterm/git/stockroom/skills/sr-search/src/stockroom/doctor.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_doctor.py`
- `/home/mobaxterm/git/stockroom/skills/sr-search/tests/test_doctor_cli.py`
- `/home/mobaxterm/git/stockroom/docs/contributing/preparation.md`

## Key decisions
- Doctor reads with `resolve_home` and `duckdb.connect(..., read_only=True)`. It does not call `home_dir` or `open_current`
- A missing warehouse is `warehouse: absent` and is not opened. A held `.warehouse.lock` is `warehouse: busy`. A connect or pragma failure is `warehouse: unavailable`
- `--help` uses `RawDescriptionHelpFormatter` so argparse wrapping cannot split the storage phrases

## Deviations
- One extra test covers a pragma failure after connect. The plan required that outcome, and the connect-failure test does not reach it
- Help uses a raw description formatter so `free disk` stays one phrase. `stockroom backfill` already uses that formatter

## Next Step
- Reflect on the doctor storage report.
