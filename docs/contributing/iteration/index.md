# Development Iteration Cycles

This secion is day-to-day work **after** your local checkout is wired up. Don't know what that means? Go through the [Preparation](preparation.md) process first!

## Prerequisites

- A local checkout already on the [Preparation](preparation.md) and wired up in your harness of choice.
- [uv](https://docs.astral.sh/uv/) for the engine and docs toolchains.
- **Node 22** for dashboard JS tests and the full `make test` / `make ci` gate

Machine onboarding for a *released* install (torch pick, doctor smoke, schedule, first ingest) is still [`sr-initialize`](https://github.com/Texarkanine/stockroom/blob/main/skills/sr-initialize/SKILL.md) — not `make`. Contributors use Make against a checkout they already own, in order to develop and test changes.

## Mental Models

From the **repo root**, the [`Makefile`](https://github.com/Texarkanine/stockroom/blob/main/Makefile) is the usual entrypoint — it handles the `skills/sr-search/` directory and the `--no-config` / `--no-sync` flags. Run `make help` anytime for the full target list; the sections below only name the targets that matter for that surface.

### Two uv projects

| Project | Path | Purpose |
| --- | --- | --- |
| Engine | `skills/sr-search/` | Runtime + tests; torch held out of lock |
| Docs | repo root | `properdocs` site only (`uv sync --group docs`) |

## Things You can Iterate On

| Surface   | Description |
| --------- | ----------- |
| [Engine](engine.md)    | The Python code that powers Stockroom's engine, including ingesting data and the CLI |
| [Docs](docs.md)      | The documentation site |
| [Dashboard](dashboard.md) | The web interface for Stockroom's data |
| [Skills](skills.md)    | The how-to for Stockroom's agent-facing surfaces |
| [Backfills](backfill-adapters.md) | The code that powers Stockroom's backfill functionality |