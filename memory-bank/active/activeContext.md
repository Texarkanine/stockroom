# Active Context

## Current Task: `sr-query` skill (p2-embeddings-search m4)
**Phase:** PLAN - COMPLETE

## What Was Done
- Surveyed the wrapped surface (`stockroom.query` CLI: positional `sql`/`-`, `--format {tsv,json,table}` default `tsv`, `--detail {compact,snippet,full}` default `snippet`; exit codes 0/1/2; the three exact stderr forms), the existing `sr-search` SKILL.md front-matter + inline invocation contract, the architecture decision record, `print-for-who.md`, `REUSE.toml`, and both plugin manifests.
- Wrote the full Level 2 plan to `tasks.md`: author `skills/sr-query/SKILL.md` as the safe LLM wrapper over `python -m stockroom.query`, in 7 ordered steps (front-matter → routing/when-to-use → invocation contract → `--format`/`--detail` discipline → guardrails → schema map + verified examples → cross-ref edit to `sr-search` SKILL.md).

## Key Decisions (this session)
- **Prose-only — no helper `scripts/`** this sub-run (a bash resolver re-introduces the resolution problem; adding Python would drag in the TDD obligation for no gain). Recorded the future home as `skills/<skill>/scripts/`. Resolves the milestone's "where helper scripts live" open question.
- **Front-matter `enable-model-invocation: true`** (live skill, unlike the `sr-search` skeleton's `false`).
- **No `plugin.json` edit** (both manifests auto-discover `./skills/`) and **no `REUSE.toml` edit** (new file covered by the `skills/**` → PPL-S glob; `make reuse` must still confirm).
- **Verification is artisanal** (project invariant): prompt-skill behavior exercised by the operator; TDD binds Python only and this sub-run writes none. Automated gate = `make ci` green + `make reuse`.

## Next Step
- Preflight validation (`niko-preflight`) runs next per the Level 2 workflow.
