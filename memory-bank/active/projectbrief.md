# Project Brief

## User Story

As a stockroom maintainer, I want the local dashboard default port changed from 6767 to 58008 so that the published default uses the chosen port, with a clean break and no migration for existing hosts.

## Use-Case(s)

### Fresh install / session-start launch

A host with no prior dashboard listener launches on 58008 and prints `http://127.0.0.1:58008/`.

### Existing orphan on 6767

A host still running an old 6767 listener is left alone; new launches bind 58008. No migration or kill of the old port.

## Requirements

1. Change the dashboard default port from `6767` to `58008` everywhere it appears in the working tree except `memory-bank/archive/`.
2. Prefer a dead-simple find/replace (e.g. sed) — no behavioral redesign.
3. No migration path, identity cleanup, or dual-port logic.

## Constraints

1. Do not edit `memory-bank/archive/` (historical records stay as written).
2. No new launcher behavior beyond the constant/docs/tests reflecting 58008.

## Acceptance Criteria

1. Default launch (no `--port`) binds and advertises `58008`.
2. Tests, skills, and non-archive docs that referenced `6767` as the dashboard default now reference `58008`.
3. `memory-bank/archive/` is untouched.
4. Suite still passes.
