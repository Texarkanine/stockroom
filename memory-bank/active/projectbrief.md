# Project Brief

## User Story

As an agent running `stockroom semantic` or `stockroom embed`, I want a torch import or load failure to tell me the command that fixes it, so that I heal the environment instead of stopping on a raw traceback and re-running `sr-initialize`.

## Use-Case(s)

### Use-Case 1

`stockroom semantic` (and the same path in `stockroom embed`) fails because torch is not importable. The process exits non-zero with one short remedy on stderr. When a hashed freeze exists, that remedy is `stockroom shim ensure-env`. When it does not, the remedy is `sr-initialize`.

### Use-Case 2

The text an agent actually follows (`skills/sr-semantic/SKILL.md`, and the torch-contract sentence in `skills/sr-search/references/system-model.md`) names the same remedy the command prints. `docs/user-guide/troubleshooting/torch.md` does not give two different next steps for the same failure.

## Requirements

1. Resolve [issue #144](https://github.com/Texarkanine/stockroom/issues/144).
2. Before implementing, judge whether the ticket's options are optimal. Implement the optimal fix, and record why it is better if it differs from the ticket.
3. When the work is finished, open a non-draft pull request.

## Constraints

1. The one-command heal already exists: `stockroom shim ensure-env` when a hashed freeze exists. `sr-initialize` remains the path when ensure-env cannot help (no freeze, or a bad wheel).
2. `stockroom doctor smoke` already maps these cases. Do not add a new doctor command for this failure.
3. Test-driven: tests before behavior changes.

## Acceptance Criteria

1. A missing or unloadable torch on `stockroom semantic` and `stockroom embed` does not end as an uncaught traceback. The process prints the matching remedy and exits non-zero.
2. The skill text an agent follows names that remedy, and the torch troubleshooting page agrees with itself.
3. The chosen design is the one justified as optimal for this failure, including a better design than the ticket's options when that design is justified.
4. A non-draft pull request is open for the change.
