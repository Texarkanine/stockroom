Process details: [CONTRIBUTING.md](../CONTRIBUTING.md)

## What & why

<!-- 1–3 sentences. Link issues with #N. -->

## Checklist

- [ ] PR title is a [conventional commit](https://www.conventionalcommits.org/) — `feat` / `fix` / `chore` / `docs` only. **Squash-merge uses this as the changelog entry.**
- [ ] Tests written before the fix/feature (and they failed first)
- [ ] `make ci` passes
- [ ] `make docs-build` passes — update `docs/` if behavior or a contributor contract changed
- [ ] `make reuse` passes — prefer `REUSE.toml` path aggregates for new files
- [ ] Change stays in its stated scope

<!-- Niko/memory-bank: if you touch memory-bank/, follow .cursor/rules/shared/niko/memory-bank/ and .cursor/skills/shared/niko/references/core/reconcile-persistent.md -->
