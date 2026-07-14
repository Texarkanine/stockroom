# Contributing

Thanks for contributing to Stockroom.

Day-to-day checkout work (localdev enter/exit, engine/Torch/docs loops, licensing) lives on the docs site:

* [Contributing](https://texarkanine.github.io/stockroom/contributing/) - the landing page
	1. [Preparation](https://texarkanine.github.io/stockroom/contributing/preparation/) - to get ready to hack on Stockroom
	2. [Iteration](https://texarkanine.github.io/stockroom/contributing/iteration/) - how to actually make and validate changes to the various parts of Stockroom

## Pull requests

1. Fork (or use a branch on a write-enabled clone) and open a PR against `main`.
2. Keep the change focused: one concern per PR when practical.
3. Use [conventional commits](https://www.conventionalcommits.org/) (`feat`, `fix`, `chore`, `docs` only!).
4. Update the docs site (under `docs/`) when behavior or contributor contracts change — preview with `make docs`, gate with `make docs-build`.
5. Prefer path aggregates in [`REUSE.toml`](REUSE.toml) over per-file SPDX headers when adding many files. Licensing detail: [Licensing](https://texarkanine.github.io/stockroom/contributing/licensing/).

## Checks

CI runs the engine gate and a strict docs build. Locally:

```bash
make ci          # engine gate (matches CI)
make docs-build  # strict properdocs build
make reuse       # licensing lint
```

## Reviews

Expect review on correctness, docs ownership (do not fork a second SSOT), and whether the PR stays in its stated scope. Link related issues in the PR body (`#N`).

## Niko & memory-bank

The [Niko agentic workflow engine](https://github.com/Texarkanine/.cursor-rules/tree/main/rulesets/niko) manages the [memory-bank](memory-bank/) in this repository. You're welcome to use any development process you like, but please ensure you and/or your agents abide by the [relevant rules](.cursor/rules/shared/niko/memory-bank/) and [procedures](.cursor/skills/shared/niko/references/core/reconcile-persistent.md) if you modify memory-bank files.
