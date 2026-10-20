# Project Brief

## User Story

As an operator whose nightly stockroom job runs unattended, I want that job to heal a missing torch before it embeds, so a night still produces vectors after an exact sync has stripped torch from the engine environment.

Authoritative spec: [issue #146](https://github.com/Texarkanine/stockroom/issues/146).

## Use-Case(s)

### Nightly heal before ingest

The nightly entry runs `stockroom shim ensure-env`, then `stockroom ingest`, then `stockroom embed`. A failed heal still lets ingest run. A failed ingest still skips embed.

### Stale entry is visible

`stockroom schedule status` reports an installed entry from before this change as out of date and offers a reinstall.

## Requirements

1. `render_payload` in `skills/sr-search/src/stockroom/schedule.py` runs `stockroom shim ensure-env` as its own step, before ingest.
2. The rendered command is `(date; stockroom shim ensure-env; stockroom ingest && stockroom embed)`, with the log redirection covering every command inside the subshell and the log path shell-quoted.
3. The payload stays free of `%`.
4. Both the cron line and the launchd plist use that payload.
5. `schedule status` shows an entry rendered before this change as out of date. Include whatever that comparison and its tests need.
6. Tests cover the rendered payload, including a log path that contains a space and one that contains a quote.

## Constraints

1. Ship this on its own, ahead of the warehouse-footprint issue (#147).
2. Land independently of #144 (the torch failure message). Do not fold that work in.
3. Do not make `make format` or the pre-commit hook torch-safe as the fix. Do not call `ensure-env` from inside `embed`.
4. Keep the existing subshell and the shell grouping `date`, then `ensure-env`, then `ingest && embed`.

## Acceptance Criteria

1. The rendered cron line and the launchd plist both run `stockroom shim ensure-env`, then `stockroom ingest`, then `stockroom embed`.
2. A failing `ensure-env` does not skip ingest. A failing ingest still skips embed.
3. `schedule status` shows an entry from before this change as out of date.
4. Tests cover the rendered payload, including a log path that contains a space and one that contains a quote.
