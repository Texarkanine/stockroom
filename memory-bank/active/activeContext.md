# Active Context

## Current Task: plugin-root-resolution
**Phase:** PLAN - COMPLETE (third revision, operator-approved design)

## What Was Done
- Intent confirmed by the operator: reassess how `CLAUDE_PLUGIN_ROOT` reaches each plugin surface, then fix `sr-initialize` and the hook configuration where they set users up to fail.
- Verified the model against the Claude Code docs, a headless probe on 2.1.301, Cursor forum and staff statements, and warehouse history. The details are in `tasks.md` under "Evidence that shaped the plan".
- Plan revised for preflight: the mirror test expects the logical path, Step 7 sorts shims by header owner and baked dir, and a plugin root counts only when it holds this engine. Tests run under sh, bash and zsh.
- ~~Decision A2 (agent-made): `claude --plugin-dir <checkout>` resolves to `claude`.~~ Overruled by the operator, below.
- Second preflight: FAIL (fixable). Claude Code also substitutes `$ARGUMENTS` and `$N` when a skill gets arguments.

## Operator decisions (2026-10-16)
- **Contributors always get `dev`.** A marketplace install must be distinguishable as a real installation. Anything installed from a checkout with intent to develop or iterate is `dev`. That includes `claude --plugin-dir`, Cursor `plugins/local`, local-path marketplaces loaded in place, and the mirror.
- **Argument substitution is not a real concern**: none of our skills take arguments. Drop the with-arguments test and the hygiene guard. The Step 2 block stays function-free anyway.
- **Hook behavior for dev loads:** the operator asked for a failure-mode analysis of entering and leaving dev before deciding whether `rectify` should skip dev loads. The analysis was delivered in chat.
- **No separate dev data (option E rejected):** entering dev means all code comes from the checkout and runs against the real warehouse, which is why the docs say to back up first. That is intended.
- **Doubts about option B (rectify no-op on dev loads):** it would stop a broken dev setup from healing through rectify. The operator's aim is that casual contributors, the "make the dashboard pink" kind, never get stuck going in or out. Hackers of the hook code are on their own.
- Operator's mental model: to leave dev, break or remove the dev shim, and the real harness's hook rectifies back. Today only *removing* it works. A *dead* dev shim is never touched by hooks, which is the stuck path.
- **Approved by the operator ("Yes"), 2026-10-16:**
    1. Hooks unchanged (B dropped).
    2. `rectify` replaces a dead shim of any owner.
    3. Option A, the install-layout rule (`…/cache/<marketplace>/<plugin>/<version>`), applies to `sr-initialize` only.
    4. Step 7 sorts the existing shim.
    5. E dropped.

## Next Step
- Preflight the revised plan (subagent), then Build.
