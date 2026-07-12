# Troubleshooting

Human-oriented recovery for common failure modes. Agents already carry short recovery tables in each `SKILL.md`; this page is the longer catalog with UI and environment checks.

When in doubt: re-run **`sr-initialize`**. It re-probes and only does what is still missing.

## Plugin / hooks

| Symptom | What to check |
| --- | --- |
| Skills missing after marketplace install | Reload the window; confirm the plugin is enabled in the harness plugin UI |
| Cursor hooks / auto-dashboard never fire | Enable **Include third-party Plugins, Skills, and other configs** (see [Quickstart](quickstart.md) screenshot) |
| “Add plugins from folder” rejects this repo | Expected — stockroom is a plugin, not a marketplace. Install via `txrk9-agent-plugins` |
| Local Cursor copy does not load | Ensure `.cursor-plugin/plugin.json` is at `~/.cursor/plugins/local/stockroom/.cursor-plugin/plugin.json`; prefer `rsync` over a symlink to a path outside that tree |

## `stockroom` command / shim

| Symptom | What to do |
| --- | --- |
| `stockroom: command not found` | Machine is not initialized — run `sr-initialize` |
| Shim refuses with a one-line remedy | Follow the remedy (usually re-init or open a new session so `shim rectify` can heal after a plugin path move) |
| Engine env cannot import locked deps | Let session-start heal run, or re-run `sr-initialize` |

## Torch / embeddings

| Symptom | What to do |
| --- | --- |
| Semantic search or embed fails citing torch / environment | Torch is out-of-lock and per-machine — re-run `sr-initialize` (do not retry the query hoping torch appears). Details: [Torch](torch.md) |
| Heal soft-fails: no freeze / corrupt freeze | Re-run `sr-initialize` (pick → install → smoke → freeze). Details: [Torch](torch.md) |
| Heal soft-fails: hash mismatch / yanked wheel | Re-pick a working index, reinstall, smoke, freeze again — do not edit hashes by hand ([Torch](torch.md)) |
| Weak semantic results for *recent* work | Silent staleness is possible: ingest may have new messages that are not embedded yet. Check coverage / run embed before concluding the content is absent |

## Warehouse / search quality

| Symptom | What to do |
| --- | --- |
| Empty or sparse results after first install | Confirm first ingest+embed finished (`sr-initialize`); wait for nightly schedule or run ingest/embed via the agent / [CLI](../advanced/cli.md) |
| SQL errors on write-looking statements | Read surfaces open the warehouse read-only by construction — use ingest/embed for writes |
| Truncated-looking cells in output | Truncation is read-time only; use a higher `--detail` (or refetch a targeted row). Full content remains in the warehouse |

## Dashboard

| Symptom | What to do |
| --- | --- |
| Port 58008 already in use / stale UI after plugin update | Session start should replace an owned listener; if a pre-identity-tracking process remains, stop the old `stockroom.dashboard` process once, then `/sr-dashboard` |
| Auto-start missing on Cursor | Third-party plugins setting (above); then `/sr-dashboard` or `stockroom dashboard` |

## Still stuck

- Ask the agent with `/sr-search` (or Claude `/stockroom:sr-search`) and describe the error text.
- Contributors debugging from a checkout: [Development](../contributing/development.md). Torch contract for everyone: [Torch](torch.md).
