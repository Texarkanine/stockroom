---
task_id: advanced-usage-docs
complexity_level: 3
date: 2026-07-14
status: completed
---

# TASK ARCHIVE: advanced-usage-docs

## SUMMARY

Brought the Advanced docs section to presentation quality as an escape-hatch duo for post-initialize power users: landing + out-of-band `stockroom` CLI + new DuckDB RO satellite. Built to creative Option B (topic inventory + page IA); strict `make docs-build` green; QA PASS. Post-reflect polish moved manual shim bind into User Guide troubleshooting (nested under `command not found`) and struck Advanced env-override lists that were not actionable recipes.

## REQUIREMENTS

From the project brief:

1. Deliver Advanced to the same reviewed quality bar as User Guide / Contributing / Architecture.
2. Cover confirmed topics: stockroom CLI out-of-band of an agent harness; DuckDB CLI against the warehouse.
3. Decide include/exclude for successful direct `uv` (default lean: omit).
4. Keep landing + sub-pages shape; content not locked to scaffold prose.
5. Audience: smart users doing advanced things with good reason (power-user UG voice).
6. Minimalism: omit uncertain paths and anything UG already owns; not a second onboarding track.
7. Constraints: docs-only; no clone `make`/`uv` as initialize substitute; no ownership blur with UG / Architecture / Contributing.

## IMPLEMENTATION

### Approach

Docs-only L3: dual creative (topics + IA) → plan → preflight → TDD-style content checklist (B1–B6) → stubs → fill per satellite → inbound link audit → strict build → QA → reflect → post-reflect polish → archive.

### Key files

| Area | Paths |
| --- | --- |
| Landing | `docs/advanced/index.md` — audience, is/isn’t, TOC |
| CLI satellite | `docs/advanced/cli.md` — OOB shim invocation; `query`/`semantic` + format/detail; other-commands pointer |
| DuckDB satellite | `docs/advanced/duckdb.md` *(new)* — path → Installed layout; `duckdb -readonly`; prefer `stockroom query`; caveats |
| Nav | `docs/advanced/.pages` — Overview → CLI → DuckDB |
| Inbound | Architecture escape-hatch / change-surfaces retarget DuckDB to `duckdb.md`; UG troubleshooting gained nested shim-bind recipe |
| Persistent MB | No surgical edits required |

### Creative decisions (inlined)

**Topic inventory — selected B: Escape-hatch duo**

- Options: A full CLI encyclopedia; B duo (CLI OOB + DuckDB RO); C trio (+ end-user `uv`); D CLI reference + task recipes.
- Rationale: Matches confirmed asks and ranked #1 attribute (minimalism / ownership). UG already owns catch-up ingest/embed, dashboard, torch; Contributing owns checkout `uv`/`make`; direct end-user `uv` is the footgun the shim exists to prevent.
- Include: OOB stockroom invocation + read/search presentation; DuckDB RO open + caveats.
- Exclude / link-out: catch-up, dashboard, torch heal, contributor `uv`, migrate/shim/torch/doctor/schedule deep dives (orientation pointers only).
- Tradeoff: No Advanced `uv` page; heal hackers get pointers, not recipes. Reversible if a concrete `uv` scenario appears.

**Page IA — selected B: Landing + `cli.md` + `duckdb.md`**

- Options: A single `cli.md` with nested DuckDB; B two satellites by tool; C rename to `stockroom-cli.md` + `duckdb.md`; D landing-heavy.
- Rationale: One job per page; keep `cli.md` slug for inbound links; DuckDB gets a clear home Architecture can name.
- Tradeoff: Slight inbound precision updates where “CLI” meant DuckDB; page title must not claim encyclopedia scope.

### Post-reflect polish

- Struck Advanced env-override name-only lists; transcript-root env recipes live on UG ingest where the command is owned.
- Manual shim bind moved to UG troubleshooting under `stockroom: command not found` as last-resort `####` (H3s remain symptoms only).
- Intentional bind for end users is not a happy Advanced path — initialize / Contributing localdev own that.
- Operator landing trim + troubleshooting wording/indent tweaks.

## TESTING

Docs-only verification (no new pytest):

1. **Build checklist B1–B6** — landing frames Advanced; CLI OOB depth (no encyclopedia / no uv); DuckDB RO page; ownership boundaries; nav + inbound; `make docs-build`.
2. **`make docs-build`** — strict PASS (build, QA, and post-reflect polish).
3. **`/niko-preflight`** — PASS; amended plan for checklist → stubs → fill → verify ordering; advisory home DuckDB caption deferred.
4. **`/niko-qa`** — PASS; two trivial prose fixes (process-meta phrase; STOCKROOM_HOME fallback consistency).
5. **Ownership spot-check** — Advanced does not re-own UG catch-up, Architecture doctrines, or Contributing `uv`/`make`.

## LESSONS LEARNED

### Technical

- Confirmed `duckdb -readonly` and `$STOCKROOM_HOME/warehouse.duckdb` against local install — plan assumptions held.
- Name-only env lists fail the “actionable” bar; put recipes where the command is owned (UG ingest / troubleshooting), not Advanced orientation pages.

### Process

- Docs-only L3 works well when creative locks topic cut *and* page IA before plan: Build stays fill-and-link, not redesign.
- Docs TDD (unchecked B* checklist → stubs → fill → verify per page) prevents write-then-invent-tests drift.
- User-facing docs can leak process meta (“Advanced-owned depth”); worth a one-line QA voice pass for docs tasks.
- Troubleshooting H3s should be symptoms; remedies nest — procedures must not peer with symptoms.

### Creative phase held

- Duo cut prevented encyclopedia regress; pointer table gave orientation without re-owning UG.
- Keeping `cli.md` slug minimized inbound churn while `duckdb.md` gave Architecture a precise target.

## PROCESS IMPROVEMENTS

- Keep post-reflect operator polish in the same task until archive rather than opening a new task for ownership/heading tweaks alone.
- For docs QA: scan once for process-speak leaking into user prose.

## TECHNICAL IMPROVEMENTS

None required for this docs task. Preflight advisory (home-page DuckDB caption/link for discoverability) remains optional polish outside Advanced-section focus.

## NEXT STEPS

None for this task. Optional later: home `docs/index.md` one-line “Advanced → DuckDB” caption if discoverability still feels weak. Type `/niko` to begin the next task.
