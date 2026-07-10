# Stockroom — Product Brief

*The authoritative product context for stockroom: who it serves, what they can do with it, why it is worth building, what "done" means, and the constraints and non-goals that bound v1.*

## What Stockroom Is

Stockroom turns your agentic-coding history into a local, private data warehouse you can search, query, and visualize. Git records the *artifacts* of your work — the code that survived and the commits that landed — but says nothing about the *process* that produced them: the prompts you wrote, the reasoning the agent worked through, the tool calls it made, the approaches you tried and threw away, the long exchange in which a hard bug was finally understood. That process is where most of the genuinely hard thinking lives, and today it drains away into harness-specific log files that are awkward to search, trivial to lose, and impossible to analyze in aggregate.

Stockroom captures that process and makes it durable, faithfully recorded, and queryable on your own machine. Its defining promise is fidelity: when you recall something, you get the *real content* — the whole prompt, the whole response, the whole tool input — never a truncated stub that forces you back into the raw transcripts. It ingests history from both Cursor and Claude Code, stores it in full, and exposes it through a small set of intuitively named skills — blended search, semantic search, raw SQL, and an at-a-glance dashboard — all running entirely on your machine with no cloud, no telemetry, and no external API calls. It is **personal-first software built to a productization standard**: good enough to be the operator's daily tool, and clean enough to publish for anyone who finds it.

## The Problem

Heavy users of agentic coding harnesses accumulate an enormous and genuinely valuable trail of conversation: how a bug was actually diagnosed, why one approach was chosen over another, what was attempted and abandoned and the reasoning for it. This record is the closest thing there is to a memory of *how the work was really done* — and it is almost entirely unmanaged. It lives in harness-specific on-disk formats, scattered per-project and per-session; it is hard to search beyond crude text matching, easy to lose to a cleanup or a reinstall, and impossible to analyze across sessions or across tools.

The tools that exist to address this fall short in two ways. They tend to be either third-party and casually packaged — MIT scripts with loose, unpinned dependencies re-resolved fresh on essentially every run, an alarming supply-chain posture for software that reads *every one of your conversations* — or they are bound to a single harness and brittle across its updates.

The deeper failure is fidelity: the reference tools **truncate the very content they keep**. Measured on the operator's own live warehouse (2026-06-22, roughly 24,700 messages), user prompts and agent responses are hard-capped at 2,000 characters and tool inputs at 500 — not merely in display, but *in storage*. About **17%** of messages exceed that 2,000-character cap and are silently clipped, while the true content runs far larger: a median around half a kilobyte, a p99 near 14 KB, and a long tail up to roughly **200 KB** in a single field. The practical consequence is that these tools can tell you *how much* AI you used but cannot faithfully show you *what actually happened* — the moment a recalled answer matters, you are back in the original logs anyway. Truncation is the line between a fun toy and a memory you can trust, and erasing that line is stockroom's reason to exist.

## Target Audience

Stockroom is built first for a specific person, and by extension for people who work the way they do.

- **Primary user — the power user of agentic coding.** The operator (Texarkanine) and people like them: developers who lean heavily on agentic harnesses day to day and accumulate history fast enough that it becomes worth searching, analyzing, and reflecting on. They are the kind of user who already wishes they could grep their own past conversations.
- **Disposition — privacy-conscious and supply-chain-aware.** They want a tool that runs entirely on their own machine, and they care *how* it is built. A tool that reads all of your conversations earns trust only if it is local by construction and its dependency surface is pinned and auditable — these users notice the difference and will not run something that isn't.
- **Environment — plugin-comfortable and cross-platform.** They are at ease installing a Cursor or Claude Code plugin and running an initialization skill. Their machines are heterogeneous, with a real WSL/Windows-mount contingent, so path and platform realities cannot be hand-waved.
- **Standard — personal-first, productization-grade.** This is not a tool chasing mass adoption. It is personal-first software held to a publishable standard: reliable, honest, and polished enough that someone who stumbles onto it in the marketplace gets a real product, not a personal script with the serial numbers filed off.

## Use Cases

Stockroom's surface is a small set of friendly skills, each mapped to a concrete thing a user wants to do.

- **Find that conversation.** "Where did I work through the auth race condition?" The friendly `sr-search` entrypoint blends keyword and semantic matching and ranks the results, so the default tool for "find it" simply works. Because kept content is stored in full, what you find is the *real* exchange rather than a 2,000-character stub — and `sr-search` returns a sensible amount, enough to answer the question without dumping a 200 KB blob into your context window.
- **Recall by meaning.** When you know the exact words won't match — you remember the *shape* of a problem, not its vocabulary — `sr-semantic` runs pure vector search over your history. It is named deliberately so that someone reaching for plain keyword search won't grab it by mistake.
- **Ask arbitrary questions.** `sr-query` runs raw SQL against the warehouse for any analysis the prepared skills don't cover: counts, trends, slices by harness or model or time. It is the power-user escape hatch and the proof that the data is genuinely yours to interrogate.
- **See what you've been up to.** `sr-dashboard` opens a local, at-a-glance view of recent activity and patterns — the v1 "look back," and the metric substrate that a future time-series recap will be built on.
- **Stay current automatically.** A nightly job re-ingests and re-embeds new history, so the warehouse stays fresh without anyone remembering to run anything. Freshness is the default state, not a chore.
- **Survive upgrades.** When a new release changes the schema, stockroom migrates the local database in place — safely, and without forcing an expensive re-embed — rather than breaking or stranding the data you have accumulated.

## Key Benefits

- **Faithful recall — the headline differentiator.** The content stockroom keeps (prompts, responses, tool inputs) is stored *in full*, never truncated at rest. You can find and re-read what actually happened instead of a clipped fragment, and you never have to fall back to the raw logs. Reads apply sensible, context-aware truncation so that retrieving a huge field never floods an agent's context window — truncation is repositioned from a destructive storage default into a deliberate read-time feature.
- **Local and private.** All data and *all* embedding computation stay on your machine. There are no external API calls for core functionality and no telemetry of any kind; the only network traffic is your package manager fetching pinned dependencies and your own browser loading the local dashboard.
- **Supply-chain safe.** Stockroom ships as a fully pinned, hash-verified `uv` project with its lockfile committed, so a tool that reads every one of your conversations cannot have fresh, unaudited dependencies pulled into it at run time. This is a direct, deliberate correction of the loose-dependency posture of the reference tools.
- **Doesn't break you.** First-class database migrations with concurrency-safe locking mean a schema change in an update never corrupts or strands your local warehouse — and never silently forces an expensive full re-embed of everything you have accumulated.
- **Trustworthy provenance.** Stockroom is clean-room and AGPLv3 — copyleft, auditable, and free. You can read exactly what it does, and so can anyone else.
- **Built to extend.** Storage is harness-labeled from day one, so Cursor and Claude Code coexist now and additional harnesses can be added later without re-architecture.

## Success Criteria

Stockroom v1 is successful when all of the following hold.

- **It installs and self-configures.** A user installs stockroom from the marketplace, runs `sr-initialize`, and that single step sets up nightly freshness and performs a first ingest and embed — no hand-holding, no manual configuration.
- **It ingests both harnesses, and the surface works.** It reliably ingests real history from *both* Cursor and Claude Code, and `sr-search`, `sr-semantic`, `sr-query`, and `sr-dashboard` all work against that data.
- **What it keeps is complete.** The content stockroom stores is faithfully whole — there is no truncation at rest — so getting an answer never requires going back to the original transcript. This is the criterion that separates success from a near-miss.
- **It never corrupts the warehouse.** The local database survives normal use *and* a schema-changing upgrade applied through migrations, including under concurrent load from parallel agents. "Never breaks your data" is a promise, not an aspiration.
- **It is good enough to live in, and clean enough to ship.** It is reliable and pleasant enough for the operator's daily personal use, and polished enough to publish on the operator's marketplace without reservation.

## Key Constraints

These are firm boundaries on how v1 is built:

- **No truncation at rest.** The fields stockroom keeps are stored in full; storage, schema, and embedding are all designed around full-fidelity text. Truncation exists only at *read* time, where it is a deliberate, context-aware feature rather than a lossy default.
- **Local-only, no telemetry, no cloud.** The only acceptable network activity is `uv` fetching pinned dependencies and the user's own browser hitting the local dashboard. Embedding is computed locally; nothing about the user's history leaves the machine.
- **AGPLv3.** Strong copyleft, explicitly extending to the network-served dashboard. The license is already in the repository and is non-negotiable.
- **Clean-room with respect to `claude-warehouse`.** No code, schema DDL, or unique ideas may be copied from the third-party MIT reference — only commonplace, generally-public concepts that would appear in any tool of this kind. (The operator's own `cursor-warehouse`'s *original content* may be freely reused and relicensed.)
- **uv-locked except torch.** Everything is pinned through the committed lockfile, with torch as the single deliberate, documented exception — never locked across platforms, because cross-platform torch wheels (CPU/CUDA/MPS) make that a known dead end. The exact mechanism is the one genuinely open question (O9), to be settled empirically while authoring the Tech Brief.
- **v1 ingests both Cursor and Claude Code.** The schema is designed against both harnesses so it is not single-harness-biased, and both plugin manifests ship from the start.
- **Hook discipline.** Anything triggered on session start must be idempotent, fire-and-forget, bounded by the hook timeout, and must never error. The session-start hook only launches the dashboard; it never ingests and never migrates.

## v1 Non-Goals

The following are explicitly out of scope for v1. Several are deferrals with a known future shape; others are deliberate, lasting exclusions.

- **Recap, wrapped, or report.** Deferred, and reconceived for later as a time-series view over the dashboard's metrics rather than a separate feature.
- **Storing the raw original record.** Ingest is ETL — extract the fields that matter and reshape them into stockroom's schema. There is no verbatim mirror of the source's every field; faithfully keeping the fields we *do* care about is what removes the need to revisit originals.
- **Capturing tool outputs.** Tool *inputs* are kept; outputs are intentionally dropped as high-bulk, low-recall-value.
- **Harnesses beyond Cursor and Claude Code.** The schema is designed to extend to others (Codex, Windsurf, and the like), but no additional harness ships in v1.
- **Token and cost estimation.** Too messy to do honestly across the subscription-versus-API split; out.
- **AI-code attribution.** The "percent AI-written" question is out of scope.
- **Source-file purge or disk reclamation.** Stockroom reads source traces; it does not delete or reclaim them.
