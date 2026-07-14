# Architecture Decision: advanced-page-ia

## Requirements & Constraints

**Functional**
- Preserve agreed **shape**: landing page + sub-pages for specific advanced usages.
- Content not locked to current scaffold prose; may rename/split/replace `cli.md`.
- Deliver the Option B topic inventory: (1) out-of-band stockroom CLI, (2) DuckDB CLI — no `uv` page.

**Quality attributes (ranked)**
1. **One job per page** — each sub-page = one advanced usage; landing frames audience and TOC.
2. **Discoverability** — inbound links from Architecture / UG / Search must resolve cleanly.
3. **Minimalism** — no filler pages; no mega-page that mixes unrelated tools.
4. **Maintainability** — stable slugs where possible; avoid churn of many thin stubs.

**Constraints**
- Existing inbound targets point at `docs/advanced/cli.md` (and Advanced index).
- DuckDB content must not be buried under a “CLI encyclopedia” that also owns heal commands.
- properdocs `.pages` nav must list Overview then satellites.

**Boundaries**
- In: file layout, titles, what lives on landing vs each satellite.
- Out: prose voice details beyond “power-user UG”; Architecture page count.

## Components

Landing (`index.md`) frames audience and links satellites. Each satellite owns one escape hatch. Cross-section links retarget to the right satellite.

## Options Evaluated

- **A — Keep single `cli.md`**: Landing + one satellite that covers stockroom CLI *and* nested DuckDB (current scaffold). Shape technically satisfied; “specific advanced usages” blurred.
- **B — Two satellites by tool**: Landing + `cli.md` (stockroom out-of-band) + `duckdb.md` (raw DuckDB). Matches confirmed topics 1:1 with pages.
- **C — Rename for clarity**: Landing + `stockroom-cli.md` + `duckdb.md`. Clearer titles; breaks or redirects more inbound links than B.
- **D — Landing-heavy**: Put most guidance on `index.md` with thin satellites. Fights “sub-pages for specific advanced usage” and prior docs IA lessons (Architecture satellites are the body).

## Analysis

| Criterion | A One cli.md | B cli + duckdb | C Rename | D Landing-heavy |
| --- | --- | --- | --- | --- |
| One job / page | Weak | Strong | Strong | Weak |
| Discoverability | OK (existing slug) | Strong; keep `cli.md` slug | Weaker (rename) | Weak |
| Minimalism | Medium (mixed topics) | Strong | Strong | Weak (dump) |
| Link churn | None | Low (add duckdb; keep cli) | Higher | Medium |

Key insights:
- Two confirmed usages → two satellites is the natural 1:1 mapping under the locked shape.
- Keeping the `cli.md` filename preserves most existing inbound links; DuckDB gets a dedicated page Architecture can point at more precisely later.
- Nesting DuckDB under CLI (A) was the scaffold’s convenience, not a content lock — operator said content isn’t set in stone.
- Renaming to `stockroom-cli.md` is nicer English but not worth the link audit vs keeping `cli.md`.

### Choice Pre-Mortem

- **DuckDB page too thin to justify a satellite**: checked — RO open + path + caveats vs `stockroom query` is enough for a focused page; if prose stays tiny, still better than burying under CLI. Can fold back later (reversible).
- **Users look for DuckDB under CLI and miss the sibling**: checked — landing TOC + “see also” cross-links on both satellites; Architecture change-surfaces can say DuckDB explicitly.
- **Keeping `cli.md` name confuses (sounds like all subcommands)**: checked — page title/H1 should be about out-of-band stockroom usage, not “every subcommand”; short orientation pointer for other commands.

## Decision

**Selected**: Option B — Landing + `cli.md` + `duckdb.md`

**Rationale**: Best fit to ranked “one job per page” and confirmed topic duo; preserves `cli.md` slug for inbound links; adds a clear DuckDB home without inventing a third maybe-page.

**Tradeoff**: Slight link updates where Architecture/UG said “CLI” but meant DuckDB specifically (optional precision); `cli.md` title must not claim encyclopedia scope.

## Implementation Notes

- **`docs/advanced/index.md`**: Audience (power users after initialize); what Advanced is/isn’t; TOC to CLI + DuckDB; outbound to Architecture / UG / Contributing as needed.
- **`docs/advanced/cli.md`**: Out-of-band stockroom shim invocation; `query`/`semantic` depth + format/detail; env overrides; brief “other subcommands → UG / `--help` / initialize” — not full table of heal recipes.
- **`docs/advanced/duckdb.md`** *(new)*: Warehouse path (link Installed layout); DuckDB CLI RO recipe; prefer `stockroom query` for routine; locks/migrations/presentation caveats.
- **`.pages`**: Overview → CLI → DuckDB (or DuckDB → CLI if alphabetical preference — prefer usage order: stockroom first, then raw DuckDB).
- **Delete nothing required** beyond rewriting scaffold prose; add `duckdb.md`.
- **Inbound audit**: Update Architecture/UG pointers that currently dump both topics onto `cli.md` so DuckDB points at `duckdb.md` where appropriate.
