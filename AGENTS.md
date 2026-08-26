# Project Memory

Shared memory for this repository is managed through SumMem, invoked as `.summem/summem`.

## At Session Start: Activating SumMem (mandatory)

Run `.summem/summem wake` from the repository root. If you can see a prior project-root SumMem wake in this conversation's history, do not run it again.

## While Working: Register Memories (mandatory)

`.summem/summem note "…"` records one short line for a fact another contributor would still need. Personal, machine-local, and user preference facts stay out. `note` may sometimes print further instructions; always follow them.

Never invent filenames, rewrite note bytes, or delete memory files by hand. The script is the only writer. The files it writes are part of your work; do not leave them untracked.

# Agent context

Tracked agent-facing project knowledge lives under `memory-bank/`. Prefer those files over inventing project facts.

## Persistent files

- `memory-bank/productContext.md` — business context: users, use cases, success criteria, constraints
- `memory-bank/systemPatterns.md` — architecture and naming patterns in use
- `memory-bank/techContext.md` — stack, tools, and how to work in this repo

## Archives

Completed work is summarized under `memory-bank/archive/<kind>/YYYYMMDD-<task-id>.md`.

## Active work

`memory-bank/active/` holds the current-task execution trace. If those files exist, an in-flight task may be underway — consult them before starting work that could collide.

## When to load

When the task needs project, architecture, or stack context, read the relevant persistent file(s). Do not load every memory-bank file on every chat.
