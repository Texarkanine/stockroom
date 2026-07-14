# UI/UX Decision: Architecture Page IA

## User & Context

- **Users**: Advanced systems-level users/contributors who already know (or can ignore) User Guide how-to. Goal: load the whole Stockroom *system* mental model.
- **Task**: Read Architecture as a coherent atlas — map first, then dive by concern — without hunting procedures.
- **Context**: Sits beside User Guide, Advanced, Contributing on the properdocs site. Current `docs/architecture/` is a thin stub. Topic set is fixed by `creative-architecture-scope-ownership.md` (~20 include topics).
- **Constraints**: WHAT-first voice; scannable nav; no dashboard-of-docs clutter; properdocs `.pages` nav; Advanced deferred.

## Design System

No separate docs visual design system. Authority is existing `docs/` patterns: section `index.md` funnel + few thematic pages (Contributing: Preparation / Iteration / Licensing) and properdocs markdown (Mermaid OK). Dashboard design system in techContext does not apply.

## Options Evaluated

- **A — Single long page**: Rewrite only `docs/architecture/index.md` as one continuous atlas.
- **B — Overview + fine-grained satellites**: One page per major topic (~10–15 nav entries).
- **C — Overview + thematic clusters**: `index` (map + pointers) plus a small set of concern-shaped pages that group related doctrines.

Sketch for **C**:

```
Architecture/
  index.md          map, audience, piece list, outbound pointers
  packaging.md      plugin layout, engine-in-skill, lock, torch, shim
  lifecycle.md      hooks, schedule/ingest, dashboard launch
  warehouse.md      ETL, schema doctrines, concurrency, ingest, identity
  embeddings.md     model/dim/VSS, staleness, search-surface split, render note
```

## Analysis

| Criterion | A Long page | B Fine-grained | C Thematic |
| --- | --- | --- | --- |
| Usability (load whole model) | Strong linear read; exhausting | Fragmented; hard to assemble | Map then deep-dive by concern |
| Clarity | TOC-dependent | Too many peers | Few nav peers, clear jobs |
| Consistency w/ docs site | Unlike Contributing multi-page | Over-splits vs Contributing | Matches Contributing grain |
| Feasibility | Easy | High authoring/nav cost | Moderate |
| Simplicity | Simple structure, heavy page | Complex nav | Right-sized |

Key insights:
- ~20 topics is too much for one undifferentiated page without becoming a wall; too little to justify per-topic pages.
- Mental model loads best as: **see the graph once**, then **open the subsystem you need**.
- Contributing’s 3–4 page grain is the local precedent that works.

### Choice Pre-Mortem

- **Wrong because readers never leave index and miss depth**: mitigated — index must be a real map with explicit “read next” links into each cluster, not a stub that points only at agent system-model.
- **Wrong because packaging vs lifecycle split feels arbitrary**: checked — packaging = how code arrives and runs; lifecycle = when things fire in the running machine; warehouse/embeddings = data plane. Distinct change surfaces.
- **Wrong because five pages still feels like a mini-book**: accepted tradeoff vs A’s wall; nav stays ≤5 content pages.

## Decision

**Selected**: C — Overview + thematic clusters
**Rationale**: Best loadability + consistency with Contributing grain; matches “systems atlas” without nav sprawl.
**Tradeoff**: Some cross-links between packaging (torch/shim) and lifecycle (hooks calling rectify/dashboard) are required; accepted.

## Implementation Notes

### Page contracts

| Page | One job |
| --- | --- |
| `index.md` | Audience; control-flow Mermaid; short piece list; pointers to satellites + agent `system-model.md` + Contributing/UG/Advanced ownership |
| `packaging.md` | Dual-manifest / run-in-place; engine in `sr-search`; uv lock hermeticity; torch out of lock + freeze/heal implications; shim baked-only (`rectify`, `ensure-env`) |
| `lifecycle.md` | Hook doctrine (F&F, idempotent, concurrent, fault-tolerant); why ingest is scheduled not session-start; dashboard session-hook launch + offline static + torch-safe env |
| `warehouse.md` | Rebuildable ETL; RO readers; no truncation at rest; harness identity/provenance; two-layer lock / `open` vs `open_current`; ingest parsers→writer / outlives sources; verify-don’t-invert; UTC; migration chokepoint |
| `embeddings.md` | sentence-transformers / BGE-small / 384-dim; VSS/HNSW; embed vs ingest lag; search-surface split; brief render/truncate chokepoint |

### Nav (`docs/architecture/.pages`)

Explicit order matching the mental-model path: Overview → Packaging → Lifecycle → Warehouse → Embeddings.

### Voice / depth

- Each page: WHAT first; WHY only for unusual constraints.
- Prefer one primary Mermaid on `index`; secondary diagrams only if a page’s relationships are non-obvious.
- Outbound links to UG/Contributing/Advanced for procedures; no recipe blocks.
- Licensing: one sentence + link to Contributing licensing from `index` or `packaging`, not a page.

### Stub migration

Replace the current stub body of `index.md` entirely; keep the section title “Architecture”. Remove “Doctrines worth knowing” as a thin list once doctrines live on satellites — index should not duplicate them.
