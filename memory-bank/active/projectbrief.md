# Project Brief

## User Story

As a prospective user or contributor landing on the GitHub repo, I want a polished README that sells stockroom, shows what it looks like, and points me at the published docs site so that I understand the product and know where to go next without digging through raw `docs/` paths.

## Use-Case(s)

### Browse the repo homepage

A visitor opens `README.md` on GitHub and should immediately get the pitch, see product graphics, and find clear links into [texarkanine.github.io/stockroom](https://texarkanine.github.io/stockroom/).

### Jump to docs from README

Deep-dive topics (quickstart, architecture, contributing, licensing) should send readers to the published site pages, matching the pattern already used in `CONTRIBUTING.md`.

## Requirements

1. Rewrite `README.md` as a sales-forward first impression (pitch + value props), not just a functional index.
2. Include graphics; reuse existing `docs/img/` screenshots where they fit; request new screenshots from the operator if gaps remain.
3. Prefer published docs-site URLs (`https://texarkanine.github.io/stockroom/...`) over raw `docs/` relative paths for reader-facing links.
4. Keep install/quickstart and skill orientation accurate for Cursor and Claude Code.
5. Preserve licensing pointer (site or accurate repo path as appropriate).

## Constraints

1. Scope is primarily `README.md` (and any asset wiring needed for README graphics on GitHub); do not redesign the docs site itself.
2. Do not invent product claims that contradict `memory-bank/productContext.md` or the live docs.
3. New graphics only if existing assets are insufficient — operator will screenshot on request.

## Acceptance Criteria

1. README opens with a clear product pitch and visible graphics that convey dashboard / recall / offline query value.
2. Primary documentation links resolve to the published docs site (same spirit as `CONTRIBUTING.md`).
3. Quickstart and skills table remain correct and actionable.
4. Operator is asked only for screenshots that are actually missing for the chosen README layout.
