# Algorithm Decision: Context-Aware Read-Time Truncation for `sr-search`

## Problem

The phase's headline promise: **truncation is repositioned from a destructive storage
default into a deliberate read-time feature** — full content preserved in the store,
"sensibly trimmed on output … enough to answer without flooding the caller's context
window."

- **Input**: a ranked list of `SearchHit`s, each carrying the **whole** message `text`
  (could be bytes to ~hundreds of KB); a caller-selected detail preference; `-k` limit.
- **Output**: a rendered, ranked table whose per-result text is bounded, with trimming
  made **visible** (an honest marker), never silently dropping content from the store.
- **Invariant (hard)**: *no truncation at rest.* The store and the in-memory `SearchHit`
  keep the full text; only the **rendered** string is trimmed. The full text must stay
  recoverable (the whole reason the feature is a *read-time* choice).

"Correct" = a 200 KB field never floods the output; the user can dial the amount of text;
full text is always reachable; trimming is signposted.

## Options Evaluated

- **A — Discrete detail levels** (`--detail {compact, snippet, full}`): each level sets a
  per-result character cap (`compact` = one-line preview; `snippet` = bounded multi-line
  default; `full` = verbatim, opt-out). The caller picks how much context to spend.
- **B — Total output budget** (`--budget N` chars/tokens for the whole output): distribute
  the budget across the `k` results, trimming each to `budget/k`.
- **C — Auto per-result cap scaled by `k`**: per-hit cap = f(k); fewer results → more text
  each, no explicit knob.

## Analysis

| Criterion | A — detail levels | B — total budget | C — auto-scaled cap |
|-----------|-------------------|------------------|---------------------|
| Correctness (bounds output, full reachable) | ✓ | ✓ | ✓ |
| Simplicity (KISS) | ✓ small enum + cap | ~ distribution logic, uneven content | ~ opaque formula |
| Predictability / honesty | ✓ explicit, repeatable | ✗ a hit's length depends on its siblings' | ✗ surprising |
| Testability (deterministic) | ✓ trivial per-level assertions | ~ distribution edge cases | ~ |
| "Context-aware" fit | ✓ the *levels* are the context choice | ✓ literally budget-aware | ~ |
| User control | ✓ direct | indirect | none |

Key insights:

- **"Context-aware truncation *level*" is, by its own wording, a level selector** — Option
  A. The caller who needs little spends `compact`; who needs the exchange uses `snippet`
  (default); who needs everything uses `full`. That *is* the context-awareness, made
  explicit and predictable rather than inferred.
- **The hard invariant is satisfied identically by all options** by trimming only at
  render time — but A keeps the trim a pure, local function of one hit + one level
  (`_truncate(text, level)`), which is the simplest thing that is also obviously correct
  and the easiest to assert in tests.
- **B (total budget) is the genuinely tempting alternative** and the best "automatic"
  story, but its value over A is marginal here: the user already controls volume via `-k`
  *and* the level, the per-hit text is the only thing that can flood, and uneven content
  makes fair distribution fiddly. It is a clean **future enhancement** (a `--budget` mode
  layered over the same render path), not a v1 requirement — YAGNI.

## Decision

**Selected**: Option A — discrete detail levels with a per-result character cap, default
`snippet`.

**Rationale**: It is the simplest design that bounds output, keeps full text reachable
(`full` level + the untouched store/`SearchHit`), makes trimming explicit and honest, and
is trivially deterministic to test — while matching the literal "truncation level"
framing. It optimizes the top-ranked attributes (simplicity, predictability, testability)
without sacrificing correctness.

**Tradeoff**: No automatic total-output budgeting (Option B). Accepted: `-k` + the level
already give the caller direct control, and `--budget` can be added later over the same
render path if a real need appears.

## Implementation Notes

- **Levels & caps** (module constants, so they are named, not magic):
  - `compact` — single-line preview, whitespace collapsed, ~120 chars (a slightly longer
    sibling of m2's `_preview`/`PREVIEW_CHARS`; the search table's one-liner).
  - `snippet` — **default** — line structure preserved, capped at a bounded
    `SNIPPET_CHARS` (~500) with a visible trailing marker.
  - `full` — verbatim, no cap (the explicit opt-out; the demonstration that nothing is
    lost at rest).
- **`_truncate(text, level) -> str`**: pure, total (`None` → `""`), deterministic. Trims
  on a character boundary and appends a **visible marker** (`…` plus `(+N more chars)`)
  so trimming is never silent. This is the single function the truncation tests target.
- **Invariant enforcement**: `SearchHit.text` always holds the **whole** text; truncation
  lives **only** in the `_format_*`/render path. A test asserts the hit object retains
  full text while the rendered output is bounded — the "demonstrably a feature" proof.
- **CLI**: `--detail {compact,snippet,full}` (default `snippet`); the level is a render
  concern, so `run_search` returns full-text hits and the CLI passes the level to the
  formatter (keeps the library entry presentation-free, mirroring how `query`/`semantic`
  separate `run_*` from `_format_*`).
- **Default rationale**: at the default `-k 10`, `snippet`≈500 chars/hit ⇒ ~5 KB of text
  — substantial enough to answer, comfortably clear of flooding a context window; that
  sizing is the "context-aware" default.
