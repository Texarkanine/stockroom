# Project Brief

## User Story

As someone reading a reconstructed Cursor conversation in the stockroom dashboard, I want backslash filesystem paths to render as stored so that hidden-dot directories like `.cursor` stay visible instead of gluing onto the parent folder name.

## Use-Case(s)

### Session reconstruction of a Cursor skill attachment

Opening [604ead72-0402-49f2-bceb-c22ebed2ec33](http://localhost:58008/?view=session&harness=cursor&session=604ead72-0402-49f2-bceb-c22ebed2ec33#msg-0) shows the first user turn's skill Path as `\home\mobaxterm\git\SumMem.cursor\skills\…`. The warehouse and Cursor JSONL still have `SumMem\.cursor`. After this work, that pill shows the stored path (`.cursor` intact).

### Other hidden-dot path segments

The same render must not eat `\.` before `.git`, `.local`, `.claude`, `.config`, `.summem`, or any other ASCII-punctuation path segment.

## Requirements

1. Fix the session-view display bug where markdown-it treats `\.` as an escape.
2. Change only the render path. Do not rewrite warehouse rows or ingest.
3. Prefer the most elegant, future-proof, and minimal approach that still prevents the same class of escape.

## Constraints

1. Kept content stays whole at rest; this is a read-time display fix.
2. Offline, committed ES modules under `stockroom/dashboard/static/`; no new front-end dependencies; no markdown-it plugins (existing comment in `dashboard.mjs`).
3. This machine has one `stockroom` shim and one live dashboard. Another worker owns those processes. Do not rectify/reinstall the shim, and do not start/stop/restart the dashboard on 58008. Prefer worktree-local tests; live dashboard validation waits its turn.

## Acceptance Criteria

1. Rendering the stored Path `\home\…\SumMem\.cursor\skills\shared\niko-build\SKILL.md` keeps `.cursor` (does not produce `SumMem.cursor`).
2. Warehouse `messages.text` is unchanged; no ingest rewrite.
3. Other CommonMark in session bodies still renders (this is not "turn markdown off").
