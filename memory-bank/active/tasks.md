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

1. **Identity module (TDD: B8)**
   - Files: `skills/sr-search/src/stockroom/dashboard/identity.py` (new), `tests/test_dashboard_identity.py` (new)
   - Changes: `IDENTITY_FILENAME` under `warehouse.home_dir()`; dataclass `DashboardIdentity(pid, app_dir, version)`; `path()`, `read()`, `write()`, `clear()`; atomic write pattern consistent with shim/torch durable files

2. **Resolve current engine identity**
   - Files: `identity.py` (or small helper used by `__main__.py`)
   - Changes: `current_app_dir()` from `Path(stockroom.__file__).resolve()` → engine root (`…/src/stockroom` → parents[1] = `src`, parents[2] = app dir); version from `stockroom.__version__`

3. **Launcher decision matrix (TDD: B2–B5)**
   - Files: `skills/sr-search/src/stockroom/dashboard/__main__.py`, `tests/test_dashboard_cli.py`
   - Changes: injectable `read_identity` / `write_identity` / `kill_fn` / `verify_owned_fn` / `wait_port_free_fn`; when probe true, classify reuse vs replace vs leave; replace = verify owned → kill → wait → spawn; all paths print URL and return 0

4. **Foreground writes identity (TDD: B6)**
   - Files: `__main__.py`, tests
   - Changes: after successful `serve_impl` bind (before `serve_forever`), write identity for `os.getpid()` + current app_dir/version; on clean shutdown optionally clear (nice-to-have; not required for heal — next start can overwrite)

5. **Spawn returns / records pid**
   - Files: `__main__.py`
   - Changes: keep detached `Popen`; child is authoritative writer on bind (step 4). Parent does not need to write if child always does. After replace spawn, no parent-side identity write required.

6. **Ownership verify before kill**
   - Files: `__main__.py` (or `identity.py`)
   - Changes: default `verify_owned(pid)` checks Linux `/proc/{pid}/cmdline` contains `stockroom.dashboard` (WSL/Linux primary); if unverifiable, do not kill (B4). Keep injectable for tests.

7. **Docs**
   - Files: `docs/using.md` (and `docs/development.md` only if launch contract is documented there)
   - Changes: one short note — dashboard is machine-scoped; after plugin moves, next session start replaces a stale owned listener; no stop-on-close; pre-identity leftovers may need one manual kill

8. **Verification**
   - Run targeted dashboard tests, then full `make test` / lint as required by build phase

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
- [ ] Preflight
- [ ] Build
- [ ] QA
