# Project Brief

## User Story

As a Stockroom user or maintainer, I want the docs-only root `uv.lock` to resolve ordinary packages from PyPI (not a PyTorch wheel registry), and I want installing Stockroom on a machine not to write or rely on user-level uv extra indexes, so that other projects on the same machine stay hermetic.

## Use-Case(s)

### Use-Case 1

A maintainer regenerates or reviews the root lock and sees `certifi`, `requests`, `urllib3`, `jinja2`, `markupsafe`, and similar packages sourced from PyPI — not `https://download.pytorch.org/whl/cu126`.

### Use-Case 2

Someone installs or initializes Stockroom on a machine that already has other uv projects. Those other projects' `uv lock` / `uv add` runs do not pick up a Stockroom-originated PyTorch `[[index]]` from user-level uv configuration.

## Requirements

1. Fix [issue #130](https://github.com/Texarkanine/stockroom/issues/130): regenerate the committed root `uv.lock` hermetically so ordinary dependencies return to PyPI.
2. Keep the Torch wheel index scoped to Stockroom's torch install / compiled freeze, not user-level uv configuration.
3. If any leftover setup path or guidance still creates a user-level `[[index]]` for a PyTorch URL, remove that write; if retaining one is unavoidable, set `explicit = true`.
4. Installing Stockroom on a machine must not leak or bleed into the uv configs of other projects on that machine.

## Constraints

1. Root project is docs-only and does not declare Torch.
2. Existing contract: lock with `uv lock --no-config`; torch provisioned per-machine and held out of the engine lock.
3. Do not invent a global uv index write that current HEAD does not already perform.

## Acceptance Criteria

1. Committed root `uv.lock` has no `download.pytorch.org` registry sources for ordinary packages.
2. Root lock regeneration uses `uv lock --no-config` (or the repo's equivalent Make target).
3. Torch install / freeze / heal paths do not write a non-explicit user-level PyTorch `[[index]]`.
4. No installer or setup guidance instructs writing such a user-level index unless it is `explicit = true`.
