# Contributing

Thanks for contributing to Stockroom. This page orients you; procedural depth lives under [`docs/contributing/`](docs/contributing/development.md).

## Before you change code

1. Read [Development](docs/contributing/development.md) — Makefile targets, torch-safe `uv` contract, on-path shim.
2. If you touch embeddings or heal: [Torch](docs/contributing/torch.md).
3. Licensing is layered — [Licensing](docs/contributing/licensing.md) and root [`REUSE.toml`](REUSE.toml). Prefer path aggregates over per-file SPDX headers when adding many files.

## Documentation ownership

One owner per fact — do not fork operational manuals into a second copy.

| Home | Owns |
| --- | --- |
| `skills/*/SKILL.md` | Agent operational how + short recovery tables |
| `skills/sr-search/references/system-model.md` | Shared *why* for the **using** agent (plugin runtime) |
| `memory-bank/systemPatterns.md` | Maintainer briefing for the **maintaining** agent (checkout / Niko work) |
| `docs/**` | Human user-guide, architecture tour, advanced CLI, contributor guide |
| `README.md` / this file | Funnel and contributor entry — not a second skill manual |

**`system-model.md` vs `systemPatterns.md`:** same thematic doctrines, different audience and altitude. Do not merge, snippet, or treat them as one SSOT. Update both deliberately when a *doctrine* changes; update only systemPatterns (and code/docs) when an *implementation* detail changes. Do not point plugin agents at `memory-bank/`.

Do **not** add a human user-guide corpus under `skills/**/references/`. Do **not** copy `SKILL.md` flag tables into `docs/`.

## Engine vs docs toolchain

- **Engine:** `skills/sr-search/` (`pyproject.toml` + `uv.lock`) — runtime and tests.
- **Docs site:** repo-root stub `pyproject.toml` + docs dependency group + `properdocs.yaml` — `make docs` / `make docs-build`.

## Checks

```bash
make ci          # engine gate (matches CI)
make docs-build  # strict properdocs build
make reuse       # licensing lint
```

## Pull requests

Use conventional commits (`feat`, `fix`, `chore`, `docs`, `refactor`, `test`, …). Keep changes focused; update docs when behavior or contributor contracts change.
