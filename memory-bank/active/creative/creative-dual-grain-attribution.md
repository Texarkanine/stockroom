# Algorithm Decision: Dual-Grain Model Attribution

## Problem

Compute two compatible grains of model usage for the dashboard window:

| Grain | Output | Meaning |
|-------|--------|---------|
| Conversation | count of main sessions that used model M | “which models appear in my chats” |
| Message | count of model-produced turns attributed to M | “which models get turn-level attention” |

**Inputs:** `sessions` (`models VARCHAR[]`, `is_subagent`, activity time) and `messages` (`model TEXT`, `role`, `ts`, ordinal join keys), filtered by harness selection and activity window (same `ACTIVITY_TIME_SQL` / `parse_window` conventions as existing `models()`).

**Invariants:**
- Do not invent per-message Cursor models that were never stored.
- Subagent sessions never contribute.
- Conversation grain stays once-per-session (no double-count from repeating a model inside one session).
- Both grains and both chart families (#67 bars, #68 area) share the same attribution rules.
- Prefer a reusable helper over duplicated SQL CASE sprawl.

**Harness facts:** Claude populates `messages.model` on assistant turns and leaves `sessions.models` NULL. Cursor leaves `messages.model` NULL and may populate `sessions.models` via enrichment (0..N models per session).

## Options Evaluated

- **A — Recorded-only messages**: Conversation = current union. Message = count only where `messages.model = M`. Cursor ≈ absent from message grain.
- **B — Sole-session-model fallback**: Like A, plus when `messages.model` is NULL and `sessions.models` has exactly one model, attribute that assistant turn to that model. Multi-model / empty Cursor sessions contribute nothing to message grain.
- **C — Fan-out**: Every Cursor assistant turn counts once for each model in `sessions.models`. Inflates multi-model sessions.
- **D — Proportional split**: Split each Cursor session’s assistant-turn count across its `sessions.models`. Fractional/guessy; more code for little honesty gain.

## Analysis

| Criterion | A Recorded-only | B Sole-model fallback | C Fan-out | D Proportional |
|-----------|-----------------|----------------------|-----------|----------------|
| Correctness (honest warehouse) | Best | Good (fallback only when enrichment is unambiguous) | Weak (over-attributes) | Weak (invents fractions) |
| Product fit (#67 “Composer all day”) | Poor for Cursor | Good for single-model Cursor days | Distorts multi-model | Opaque |
| Simplicity | Best | Good | Medium | Worst |
| Reuse / DRY | Easy helper | Easy helper | Easy but wrong semantics | Harder |
| Parallel Claude/Cursor | Asymmetric (Cursor empty) | Asymmetric but explained | Fake symmetry | Fake symmetry |

Key insights:
- Conversation grain already unifies both schema fields once per session — keep it.
- Message grain should count **assistant** turns (model-produced), not every row in `messages`.
- Multi-model Cursor sessions remain visible in conversation grain; omitting them from message grain is the honest “we don’t know which turn was which” stance.
- C/D optimize for a filled chart at the cost of lying about attention.

## Decision

**Selected**: B — Sole-session-model fallback (assistant turns only)

**Rationale**: Preserves harness-honest NULLs, still gives Cursor message volume when enrichment says the whole conversation used one model (the common “Composer all day” case), and keeps multi-model sessions from polluting message rankings. Shared by #67 and #68.

**Tradeoff**: Multi-model Cursor chats and Cursor chats with empty `sessions.models` contribute to conversation grain only. Message charts lean Claude + single-model Cursor — documented in panel copy if needed, not papered over with fan-out.

## Implementation Notes

- **Conversation grain (unchanged semantics):** session uses M iff M ∈ `sessions.models` or any child `messages.model`; count once per `(harness, session_id)`; exclude `is_subagent`; window on session activity time.
- **Message grain:** for each assistant message in a non-subagent session whose session activity falls in the window:
  1. If `messages.model` is non-NULL/non-empty → attribute to that model.
  2. Else if `sessions.models` filters to exactly one non-empty model → attribute to that model.
  3. Else → skip (no message-grain contribution).
- **Time series:** conversation series bucket by session activity date/week; message series bucket by message `ts` when present, else session activity (match existing dashboard timestamp honesty).
- **Helper shape:** shared Python attribution that yields conversation sets and attributed assistant turns; ranking and bucketing stay thin wrappers (extend `models()` / add `model_trends()` or equivalent).
- **UI honesty:** titles/subtitles can say “by conversation” / “by message”; optional empty-state or range note is enough — no fake Cursor parity badge required unless creative UI asks for it.
