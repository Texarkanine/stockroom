# Task: dashboard-lifecycle-after-plugin-move

* Task ID: dashboard-lifecycle-after-plugin-move
* Complexity: Level 2
* Type: bug fix / reliability enhancement

After plugin-root move, heal already updates the shim/env, but a detached dashboard from the old engine keeps port 6767. Extend `stockroom dashboard` with start-time identity-aware replace (creative Option B): record owned listener identity under stockroom home; on launch, replace when owned-but-stale; never stop-on-close; never kill foreign listeners.

Design authority: `memory-bank/active/creative/creative-dashboard-lifecycle-after-plugin-move.md`.

## Test Plan (TDD)

### Behaviors to Verify

- **B1 free port**: probe false → spawn foreground re-exec with current interpreter; print URL; exit 0 (existing, must not regress).
- **B2 same identity**: probe true + identity matches current `app_dir` (+ version) and pid still looks owned → no spawn, no kill; print URL; exit 0.
- **B3 stale owned**: probe true + identity present with different `app_dir` (or version) + pid verifies as stockroom dashboard → SIGTERM that pid, wait until probe false (or timeout), spawn; print URL; exit 0.
- **B4 foreign / unknown**: probe true + no usable identity (missing/corrupt) OR identity pid does not verify as stockroom dashboard → no kill, no spawn; print URL; exit 0.
- **B5 kill failure degrades**: stale owned but kill/wait fails → no hard failure; print URL; exit 0 (hook contract).
- **B6 identity write on bind**: foreground successful bind → identity file under stockroom home records pid, absolute `app_dir`, and `stockroom.__version__`.
- **B7 EADDRINUSE race**: foreground bind race still exit 0 + print URL (existing).
- **B8 identity helpers**: read/write/clear round-trip; missing file → None; corrupt → treated as absent.

### Edge Cases

- Stale pidfile (pid dead) but port still up → treat as foreign/unknown (no kill by pidfile alone without verify).
- `app_dir` match but version mismatch → replace (covers same-path versioned upgrades).
- Concurrent double-launch after kill → existing EADDRINUSE success path.

### Test Infrastructure

- Framework: pytest (engine suite under `skills/sr-search/tests/`)
- Test location: `skills/sr-search/tests/`
- Conventions: `test_<area>.py`; injectable seams on `main(...)`; `warehouse_home` / `STOCKROOM_HOME` fixtures from `conftest.py`
- New test files: prefer extend `test_dashboard_cli.py`; add `test_dashboard_identity.py` if identity module warrants isolation
- Modify: `test_dashboard_cli.py` (decision matrix with injectable probe/spawn/kill/identity)

## Implementation Plan

Each numbered unit is one TDD cycle: **write/extend failing tests → implement → refactor**. Do not implement a unit before its tests exist and fail for the right reason.

1. **Identity module + current engine resolution (TDD: B8)**
   - Tests first: `tests/test_dashboard_identity.py` — round-trip write/read/clear; missing/corrupt → None; `current_app_dir()` resolves to engine root; identity record includes `port`
   - Then implement: `skills/sr-search/src/stockroom/dashboard/identity.py` — `IDENTITY_FILENAME` (or port-scoped name) under `warehouse.home_dir()`; dataclass `DashboardIdentity(pid, app_dir, version, port)`; `path()`, `read()`, `write()`, `clear()`; atomic write (`temp + os.replace`); `current_app_dir()` via `Path(stockroom.__file__).resolve().parents[2]`; version from `stockroom.__version__`
   - Port must be part of identity so `--port` overrides cannot clobber or mis-replace the default 6767 listener

2. **Launcher decision matrix + verify-before-kill (TDD: B2–B5)**
   - Tests first: extend `tests/test_dashboard_cli.py` — same identity → no kill/spawn; stale owned + verify true → kill/wait/spawn; foreign/unverified → no kill; kill failure → exit 0; preserve B1 free-port spawn
   - Then implement in `skills/sr-search/src/stockroom/dashboard/__main__.py`: injectable `read_identity` / `write_identity` / `kill_fn` / `verify_owned_fn` / `wait_port_free_fn`; default `verify_owned(pid)` reads `/proc/{pid}/cmdline` for `stockroom.dashboard` when available; **only SIGTERM pid from our identity file** when port matches and identity is stale; detach spawn unchanged (child writes identity in unit 3)

3. **Foreground writes identity on bind (TDD: B6, B7)**
   - Tests first: extend `test_dashboard_cli.py` — successful foreground bind writes identity (pid/app_dir/version/port); EADDRINUSE path unchanged (no identity write required)
   - Then implement: after successful `serve_impl` bind, `write()` identity for `os.getpid()` + current app_dir/version/port before `serve_forever`

4. **Docs**
   - Files: `docs/using.md`
   - Changes: one short note — dashboard is machine-scoped; after plugin moves, next session start replaces a stale owned listener; no stop-on-close; pre-identity leftovers may need one manual kill

5. **Verification**
   - Run targeted dashboard tests, then full suite / lint per build phase

## Preflight Amendments

- Folded former “resolve app_dir” / “spawn pid” / “verify” steps into TDD-ordered units 1–3 (blocking TDD encoding fix).
- Identity is **port-scoped** (field and/or filename) so non-default `--port` cannot corrupt the 6767 singleton record.

## Technology Validation

No new technology - validation not required (stdlib `os.kill`, existing `home_dir()`, pytest injectables).

## Dependencies

- Creative decision Option B (already documented)
- `stockroom.warehouse.home_dir` for durable identity path
- Existing dashboard probe/spawn/foreground seams
- No hook JSON changes; no close hooks

## Challenges & Mitigations

- **Pre-feature dashboard has no identity file**: cannot safely prove ownership → leave alone (B4). Mitigation: document one-time manual kill; after first successful new launch, identity exists and future moves heal.
- **`/proc` cmdline verify is Linux-specific**: macOS may not verify → refuse kill without proof. Mitigation: injectable verify; macOS still gets correct behavior when identity was written by our process and we add a second check (pid alive + recorded app_dir was ours at write time). Prefer: kill only if identity exists AND (cmdline verifies OR recorded app_dir equals a path we recognize as prior stockroom engine — still only SIGTERM our recorded pid, never scan-kill by port). Safest rule: **only SIGTERM the pid named in our identity file**, and only if that pid’s cmdline verifies as stockroom.dashboard when `/proc` exists; if `/proc` missing, require identity app_dir ≠ current (stale) AND `os.kill(pid, 0)` succeeds (process exists) — slightly weaker but pid came from our write.
- **Kill/wait race with hook timeout**: keep wait short (e.g. ≤2s); on timeout degrade to exit 0.
- **Same-path upgrade without version bump**: mitigated by including `__version__` in identity; pure file edits without version bump remain a known residual (creative pre-mortem).

## Pre-Mortem

- **Plan assumed identity file alone is enough for the operator’s already-running old dashboard**: already covered by Challenge 1 — first transition may need manual kill; do not invent unsafe port-wide kills in this L2.
- **Plan put lifecycle in hooks instead of launcher**: rejected by creative; plan keeps all logic in `stockroom.dashboard` — no change.
- **Verify-before-kill too weak on non-Linux and we kill the wrong pid**: already covered by Challenge 2 — only signal pid from our identity file.

## Open Questions

None — creative resolved architecture; no further creative phase needed.

## Status

- [x] Initialization complete
- [x] Test planning complete (TDD)
- [x] Implementation plan complete
- [x] Technology validation complete
- [x] Pre-Mortem complete
- [x] Preflight
- [ ] Build
- [ ] QA
