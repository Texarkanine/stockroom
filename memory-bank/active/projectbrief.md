# Project Brief

## User Story

As a stockroom user who updates or reinstalls the Cursor/Claude plugin (or rsyncs a local plugin tree without `.venv`), I want one session/workspace-open cycle to leave a runnable on-path `stockroom` engine so that I do not hit missing-dependency failures after path-only rectify healing.

## Use-Case(s)

### Use-Case 1 — Marketplace / cache move

Plugin content-hash directory changes; auto-dashboard hook fires; shim path is rebaked to the new engine dir; engine deps are provisioned when safe; `stockroom doctor smoke` / `stockroom dashboard` succeed without a manual full `sr-initialize`.

### Use-Case 2 — Local rsync without `.venv`

Developer copies plugin into `~/.cursor/plugins/local/stockroom` excluding `.venv`; same healing contract as Use-Case 1.

### Use-Case 3 — Already-healthy engine

Hook/session cycle is a no-op for env when a usable synced venv already exists; torch-safe rules are not violated (no exact sync after torch).

## Requirements

1. Verify issue [#17](https://github.com/Texarkanine/stockroom/issues/17) claims against the codebase before trusting them (do not implement the issue’s preferred approach by default).
2. Evaluate proposed solutions (hook/rectify env heal vs shim-runtime refusal vs alternatives) and implement the **best** fix within stockroom’s constraints and goals — not merely the issue’s preferred option.
3. After a plugin-root move, one hook/session cycle leaves the engine runnable without a manual full re-init.
4. Do not leave users with a silent empty `.venv` that masks the real failure.
5. Preserve torch-safe sync rules from `sr-initialize` / `docs/development.md`.
6. Claude and Cursor hooks share the same healing contract (or document a deliberate difference).

## Constraints

1. Exact `uv sync --frozen` only when safe (missing env / pre-torch); never exact-sync after torch exists.
2. Hooks must not fail the triggering event (`|| true` / silenced output today).
3. Hook timeout budget is tight (currently 10s) — cold `uv sync` may not fit; design must account for this.
4. `doctor` remains read-only (no install/sync/write).
5. `rectify` must not create a shim where none exists (existing policy).
6. Prefer durable, reusable ownership over one-off shell duplication in both hook JSON files.
7. Operator directive: verify claims; evaluate approaches; choose best solution for stockroom — not blind trust of the issue text.

## Acceptance Criteria

1. After a plugin-root move without `.venv`, one hook/session cycle leaves `stockroom doctor smoke` (or equivalent) working without a manual full re-init.
2. Empty/missing engine env does not produce a silent empty `.venv` that masks the failure mode.
3. Torch-safe sync rules from `sr-initialize` / `docs/development.md` are preserved.
4. Claude and Cursor hooks share the same healing contract (or a documented, justified difference).
5. Chosen design is justified against verified root cause and stockroom goals (not merely “what #17 suggested”).

## Rework

### Operator feedback (2026-07-10)

Durable torch installation source must persist on disk and be used to self-heal torch after plugin-root moves. Scenario: initialize + pick torch → works → plugin updates → rectify recreates venv → torch missing → overnight embed fails unnoticed → semantic breaks. Manual torch reinstall on every plugin update is a nonstarter; fixing that is part of [#17](https://github.com/Texarkanine/stockroom/issues/17).

### Rework requirements

1. Persist the chosen torch wheel index outside the disposable plugin/engine tree (stockroom home / XDG).
2. Record the index when torch is provisioned via the guided path (`sr-initialize`) and `make torch`.
3. On env heal (`ensure_engine_env` / `shim rectify`), if torch is missing in the engine venv and a recorded index exists, reinstall torch from that index.
4. If torch is missing and no index is recorded, fail soft with an explicit remedy (run `sr-initialize`) — do not guess a wheel.
5. After a plugin-root move with a prior recorded index, one heal cycle leaves torch importable again (embed/semantic path viable without manual re-pick).

### Rework — hashed freeze (2026-07-10)

Operator confirmed: index-only record is insufficient (heal could pull a newer torch). Required contract:

1. After smoke passes at onboard / `make torch`, **freeze** the accepted torch stack to a machine-local hashed requirements file under stockroom home.
2. Shim/env heal always reinstalls from that freeze (`--require-hashes`) — same bits as install time.
3. If freeze missing or replay fails → do not guess; operator re-runs `sr-initialize` (pick → install → smoke → freeze) or follows manual freeze/install in `docs/torch.md`.
4. All writers (`sr-initialize`, `make torch`, CLI) must produce the freeze; project `uv.lock` stays torch-free.
