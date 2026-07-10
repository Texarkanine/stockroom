---
task_id: fix-plugin-env-heal-after-move
complexity_level: 2
date: 2026-07-10
status: completed
---

# TASK ARCHIVE: fix-plugin-env-heal-after-move

## SUMMARY

Closed [#17](https://github.com/Texarkanine/stockroom/issues/17): after a plugin-root move, one hook/session cycle leaves a runnable engine without manual full re-init. Initial work added locked-deps heal via `ensure_engine_env`; operator rework extended scope to durable torch restoration. Final contract: **hashed torch freeze** under stockroom home — heal replays the exact smoke-accepted torch stack with `--require-hashes`, not a floating index URL that could pull a newer wheel.

## REQUIREMENTS

From the project brief (including rework sections):

1. Verify issue #17 claims; evaluate approaches; implement the best fix for stockroom — not blind trust of the issue text.
2. After plugin-root move without `.venv`, one hook/session cycle leaves `stockroom` runnable (locked deps + torch when previously provisioned).
3. No silent empty `.venv` masking failure; torch-safe sync rules preserved (inexact only after torch).
4. Claude and Cursor hooks share the same healing contract.
5. **Rework:** Persist torch install source outside the disposable plugin tree; heal torch after venv recreation.
6. **Hashed freeze rework:** After smoke at onboard/`make torch`, freeze accepted torch stack to `{stockroom_home}/torch-requirements.txt`; heal always uses `--require-hashes -r` that file; no floating heal fallback for legacy index-only installs.

## IMPLEMENTATION

Three iterations: (1) deps-only heal; (2) index-only `torch-index` record; (3) hashed freeze — final delivery.

### Core mechanisms

| Piece | Location / behavior |
| --- | --- |
| Locked-deps heal | `ensure_engine_env` in Python; `--frozen --inexact` sync; called from `rectify` |
| Torch freeze | `freeze_torch()` in `torch_source.py`; `uv pip compile --generate-hashes --emit-index-url` → `torch-requirements.txt` + sidecar `torch-index` |
| Torch heal | `ensure_torch()` installs only from freeze via `--require-hashes -r`; soft-fail if freeze missing |
| CLI | `stockroom torch freeze --app-dir --index` (replaced `record`) |
| Writers | `sr-initialize`: install → smoke → freeze; `make torch`: install then freeze |
| Hooks | Rectify via `python3 -m stockroom` (not `uv run --no-sync`); timeout 300s; PATH parity |

### Key files

| Area | Files |
| --- | --- |
| Engine env | `skills/sr-search/src/stockroom/engine_env.py` |
| Torch freeze/heal | `skills/sr-search/src/stockroom/torch_source.py`, `torch_cli.py` |
| Rectify/shim | `skills/sr-search/src/stockroom/shim.py`, hook JSON |
| Onboard | `skills/sr-initialize/SKILL.md`, `Makefile` |
| Docs | `docs/torch.md`, `docs/development.md`, `docs/using.md`, `memory-bank/systemPatterns.md` |
| Tests | `test_engine_env.py`, `test_torch_source.py`, `test_torch_cli.py` |

### Design decisions

- Heal path always `--inexact` (never exact sync after torch).
- No floating heal fallback for legacy index-only homes — operator must freeze once or re-run `sr-initialize`.
- Doctor's floating `pip install torch --index` kept for first-time provision (pre-freeze).
- Project `uv.lock` stays torch-free; freeze pins some PyPI transitives shared with lock — install freeze after inexact sync, documented in `docs/torch.md`.

## TESTING

- TDD throughout: injectable runners stub `uv pip compile` / `uv pip install` (no network in unit tests).
- Behaviors F1–F7: freeze writes, freeze refuses without torch, heal from freeze, heal without freeze, heal noop, CLI freeze, writer onboarding.
- Full suite: **456 passed, 3 skipped**; ruff clean.
- Manual repro: empty `.venv` from `--no-sync` → `ensure-env` → `import duckdb` ok.
- Live tech validation: `uv pip compile --generate-hashes` for `torch==2.7.1+cpu` succeeded.
- `/niko-qa` semantic review PASS (trivial Makefile comment polish only).

## LESSONS LEARNED

### Technical

- Index URL alone is not a pin — heal must replay a hashed freeze or you silently drift past the smoke-accepted torch.
- Inexact `--check` is the torch-safe readiness probe; exact `--check` wants to uninstall torch (footgun).
- Hook bootstrap `uv run --no-sync` creates empty `.venv` before Python starts; ensure must detect incompleteness, not directory presence.
- Freeze also pins some PyPI transitives shared with `uv.lock`; install freeze after inexact sync and document acceptable drift.
- `make sync` still strips torch; operators need `make torch` (now freezes) after sync before embed/semantic.

### Process

- Operator "why" on floating heal was the right challenge: product break is overnight embed failure, not import-time convenience.
- Three iterations were necessary because each scope expansion (deps → index → hashed freeze) addressed a real gap the prior fix left open.

## PROCESS IMPROVEMENTS

From the million-dollar question: from day one, initialize would smoke then freeze; rectify would always ensure deps + replay freeze. Same contract, fewer reworks. For similar heal/persistence work, nail the durable artifact contract in plan before first build.

## TECHNICAL IMPROVEMENTS

- Legacy index-only installs need one-time `stockroom torch freeze` or re-initialize before heal restores torch.
- Consider integration smoke that validates `--require-hashes` install selects correct platform wheel from multi-hash compile output (unit tests stub compile; uv behavior assumed).

## NEXT STEPS

None. Task complete and archived.
