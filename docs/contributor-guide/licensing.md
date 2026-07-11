# Licensing

Stockroom uses layered licensing, enforced by `reuse lint` (see [`REUSE.toml`](https://github.com/Texarkanine/stockroom/blob/main/REUSE.toml) at the repo root).

## Layers

| Layer | What | License |
| --- | --- | --- |
| Default | Code, docs, memory-bank, and everything else | [AGPL-3.0-or-later](https://github.com/Texarkanine/stockroom/blob/main/LICENSES/AGPL-3.0-or-later.txt) |
| Prompt carveout | `skills/**/SKILL.md` and `skills/**/references/**` only | Public Prompt License (PPL-S) |
| Vendored Chart.js / markdown-it | Exact upstream dashboard artifacts | MIT (upstream) |
| `.cursor/**` | Vendored agent tooling | NOASSERTION |

The PPL-S carveout is intentionally **narrow**: skill prompts and agent references, not the whole `skills/**` tree. Contributor and human user-guide prose under `docs/` stays AGPL with the rest of the tree.

## Checks

From a checkout:

```bash
make reuse
```

Prefer path aggregates in `REUSE.toml` over per-file SPDX headers when adding many new files.
