# Brainstorm — Product

Raw material for the **Product Brief**. Organized to map onto the Niko `productContext` template (Target Audience, Use Cases, Key Benefits, Success Criteria, Key Constraints), with extra non-goal and positioning material.

## Elevator Pitch

Stockroom turns your agentic-coding history into a local, private data warehouse you can search, query, and visualize. Git records the *artifacts* of your work; stockroom records the *process* — the prompts, the reasoning, the tool calls, the conversations — and makes that history durable, faithfully captured, and queryable on your own machine — when you recall something, you get the real content, never a truncated stub.

## The Problem

Heavy users of agentic coding harnesses accumulate an enormous, valuable trail of conversations: how a bug was actually diagnosed, why an approach was chosen, what was tried and abandoned. This lives in harness-specific on-disk formats, is hard to search, easy to lose, and impossible to analyze in aggregate. Existing tools that address this are either third-party/MIT with weak supply-chain hygiene, or single-harness and fragile across updates. Worse, they **truncate the content they do keep** — measured on the reference tool, user prompts and agent responses are cut at 2000 characters and tool inputs at 500 — so they can tell you *how much* AI you used but cannot faithfully recall *what actually happened*; you end up back in the original transcripts. Truncation is the line between a fun toy and a real, trustworthy memory.

## Target Audience

- **Primary:** the operator (Texarkanine) and people like them — power users who lean heavily on agentic coding and want to search, analyze, and reflect on their own history.
- **Disposition:** privacy-conscious and supply-chain-aware; they want a tool that runs entirely locally and that they can trust to read *all* of their conversations.
- **Environment:** comfortable installing a Cursor or Claude Code plugin and running an initialization skill; cross-platform with a real WSL/Windows-mount contingent.
- This is **personal-first** software built to a **productization standard**, so it is reliable enough to publish for others who find it — not a tool chasing mass adoption.

## Use Cases

- **Find that conversation.** "Where did I work through the auth race condition?" via a single friendly `search` entrypoint that blends keyword and semantic matching. The kept content is stored **in full** (never a 2000-char stub), and the entrypoint returns a sensible amount — enough to answer, without dumping a 200 KB blob into your context.
- **Semantic recall.** Deliberately find conversations *by meaning* via `semantic` when you know exact words won't match.
- **Ad-hoc analysis.** Run raw SQL via `query` for arbitrary questions about your own usage.
- **See what you've been up to.** Open the `dashboard` for an at-a-glance summary of recent activity and patterns — the v1 "look back," and the basis for a future time-series recap.
- **Stay current automatically.** A nightly job re-ingests and re-embeds new history so the warehouse is fresh without manual effort.
- **Survive upgrades.** When the schema changes in a new release, the tool migrates the local database safely and automatically rather than breaking.

## Key Benefits

- **Faithful recall.** The content stockroom keeps — prompts, responses, tool inputs — is stored **in full**, never truncated at rest, so you can find and re-read what actually happened instead of a 2000-character stub or a trip back to the raw logs. Reads apply sensible, context-aware truncation so a huge field never floods your context window. This is the headline differentiator.
- **Local and private.** All data and all embedding computation stay on the user's machine. No external API calls for core function; no telemetry.
- **Supply-chain safe.** The tool ships as a fully pinned, hash-verified `uv` project (lockfile committed), so a tool that reads every one of your conversations cannot have arbitrary fresh dependencies pulled into it at run time.
- **Doesn't break you.** First-class database migrations with concurrency-safe locking mean a schema change in an update never corrupts or strands a user's local warehouse, and never silently forces an expensive full re-embed.
- **Trustworthy provenance.** Clean-room, AGPLv3, copyleft — auditable and free.
- **Built to extend.** Harness-labeled storage means Cursor *and* Claude Code today, more harnesses later, without re-architecture.

## Success Criteria

- Installs from the marketplace; `sr-initialize` sets up nightly freshness and performs a first ingest + embed without hand-holding.
- Reliably ingests real history from **both Cursor and Claude Code**; `search`, `semantic`, `query`, and `dashboard` all work against it.
- **The content stockroom keeps is complete (no truncation at rest)** — so getting an answer never requires going back to the original transcript.
- **Never corrupts the warehouse** — including across a schema-changing upgrade applied via migrations under load from parallel agents.
- Good enough for daily personal use, and clean enough to publish on the operator's marketplace.

## Key Constraints

- **No truncation at rest.** The fields stockroom keeps are stored in full; storage, schema, and embedding are designed around full-fidelity text. Truncation belongs only at *read* time, where it is a deliberate, context-aware feature.
- **Local-only, no telemetry, no cloud.** The only acceptable network activity is `uv` fetching pinned dependencies and the user's own browser hitting the local dashboard.
- **AGPLv3.** Strong copyleft, also covering the network-served dashboard.
- **Clean-room vs `claude-warehouse`.** No code or schema DDL from the MIT reference may be copied; nor unique ideas - only generally public concepts that just happen to show up.
- **uv-locked except torch.** Everything is pinned via the lockfile; torch is the deliberate, documented exception (never locked across platforms).
- **v1 ingests both Cursor and Claude Code.** The schema is designed against both so it is not single-harness-biased, and both plugin manifests ship.
- **Hook discipline.** Anything triggered on session start must be idempotent, fire-and-forget, bounded by the hook timeout, and must never error.

## Non-Goals (v1)

- **Recap / wrapped / report** — deferred; later realized as a time-series view over dashboard metrics.
- **Storing the raw original record.** Ingest is ETL — extract the fields we care about and munge them into our schema; we do not mirror the source's every field or keep a verbatim raw copy.
- **Capturing tool *outputs*.** Tool *inputs* are kept; outputs are intentionally not stored (high bulk, low recall value).
- **Multi-harness ingest beyond Cursor + Claude Code** (Codex, Windsurf, etc.) — the schema is designed to extend to them, but they are not shipped in v1.
- **Token/cost estimation** — messy across subscription vs API models; out.
- **AI-code attribution** (% AI-written) — out.
- **Source-file purge / disk reclamation** — out.
