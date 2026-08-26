# Contributing

Want to contribute? We'd love to see it! Thoughtful issues and PRs that make the project better are enthusiastically welcomed here!

## Issues

Open an issue for a bug, an idea, or a question. Please use one of the issue templates — they ask for the details that make the report usable.

## Pull requests

1. Fork the repository. If you already have write access, a branch on the origin is fine.
2. Open a pull request against `main` and fill in the pull request template.
3. Title the PR as a [conventional commit](https://www.conventionalcommits.org/): `feat`, `fix`, or `chore`. This repository uses release-please: `feat` and `fix` cut a release; `chore` does not.

Keep the change focused: one concern per pull request when practical.

In this repository:

- Use `feat` or `fix` to cut a release (changelog + docs site publish with it); `chore` when the change must not release. Do not use `docs` — it will not release, so Pages will not republish.
- Update the docs site (under `docs/`) when behavior or contributor contracts change — preview with `make docs`, gate with `make docs-build`.
- Prefer path aggregates in [`REUSE.toml`](REUSE.toml) over per-file SPDX headers when adding many files. Licensing detail: [Licensing](https://texarkanine.github.io/stockroom/contributing/licensing/).

Day-to-day checkout work (localdev enter/exit, engine/Torch/docs loops, licensing) lives on the docs site:

* [Contributing](https://texarkanine.github.io/stockroom/contributing/) - the landing page
	1. [Preparation](https://texarkanine.github.io/stockroom/contributing/preparation/) - to get ready to hack on Stockroom
	2. [Iteration](https://texarkanine.github.io/stockroom/contributing/iteration/) - how to actually make and validate changes to the various parts of Stockroom

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

## License

By opening a pull request, you license your contribution under this repository's license, and you grant Texarkanine a perpetual, worldwide, non-exclusive right to relicense that contribution as part of this project under any [OSI-approved](https://opensource.org/licenses) license. You keep your copyright.
