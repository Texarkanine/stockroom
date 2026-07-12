# Quickstart

Get Stockroom installed and running in a few minutes.

## Prerequisites

- [Cursor](https://cursor.com/) or [Claude Code](https://code.claude.com/)
- A POSIX shell and network access for the first-time setup (torch wheel + first ingest)

## Install and initialize

1. Add the [`txrk9-agent-plugins`](https://github.com/Texarkanine/txrk9-agent-plugins) marketplace (that README shows the Cursor and Claude Code UI steps), then install the `stockroom` plugin from it.
2. **Cursor only:** enable **Include third-party Plugins, Skills, and other configs** (Cursor Settings). Plugin hooks do not register without this until [Cursor’s plugin-hooks bug](https://forum.cursor.com/t/plugin-hooks-not-loading-into-cursor-ide/156702) is fixed:

   ![Include third-party Plugins, Skills, and other configs — toggle on](../img/3rd-party-configs.png)

3. Run first-time setup:
    - **Cursor:** `/sr-initialize`
    - **Claude Code:** `/stockroom:sr-initialize`
4. Ask the agent something about past work, or slash-invoke `/sr-search` (Claude: `/stockroom:sr-search`).

`sr-initialize` checks prerequisites, provisions the per-machine torch wheel, puts `stockroom` on your PATH, offers nightly ingest+embed scheduling, and runs the first full ingest + embed. Re-runs are safe: it re-probes and only does what is still missing.

## What to try next

- Prefer **`sr-search`** when you are unsure whether the question is structured SQL or meaning-based recall.
- Open the local metrics UI with **`sr-dashboard`** (also launched automatically on session start when hooks are registered).
- Curious what landed on disk? See [Installed layout](installed-layout.md).
- If something fails, see [Troubleshooting](troubleshooting.md).
