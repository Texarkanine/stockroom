# Project Brief

## User Story

As a stockroom user, I want every `stockroom semantic` result to include the identifiers needed to open that hit, so that I can look up the conversation with `stockroom query` without running the search a second time.

## Use-Case(s)

### Scan, then open one hit

Run `stockroom semantic` at the default output shape, read the ranked previews, and use the printed identifiers in a follow-up `stockroom query` to fetch the conversation.

### Same identifiers on every shape

`--format table` and `--format json` carry the same lookup fields as the default, so choosing a shape is about presentation, not about whether the hit can be opened.

## Requirements

1. Every `stockroom semantic` output shape (`tsv`, `table`, and `json`) includes `session_id` and `message_id` for each hit.
2. Those fields are enough to look up the conversation with `stockroom query`.
3. The `sr-semantic` skill stops instructing a second semantic run solely to obtain those identifiers.

## Constraints

1. Truncation stays a read-time preview. Full text remains in the warehouse and is still fetched through `stockroom query`.
2. `stockroom query` itself does not change.
3. Ranking, scores, and preview detail stay as they are.

## Acceptance Criteria

1. The default `tsv` header includes `session_id` and `message_id`, and each row carries the hit's values.
2. `--format table` includes the same identifiers.
3. `--format json` still includes `session_id` and `message_id`.
4. `sr-semantic` describes a one-search handoff: take the identifiers from the results already printed, then query.
