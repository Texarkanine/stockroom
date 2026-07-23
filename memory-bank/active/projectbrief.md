# Project Brief

## User Story

As an operator running `stockroom doctor smoke`, I want a missing-torch failure to recommend `stockroom shim ensure-env` when a machine-local freeze already exists, so that I heal from the frozen index instead of a raw `uv pip install torch` one-liner that can drift CPU vs CUDA.

## Use-Case(s)

### Use-Case 1

Torch is missing from the engine env after `uv sync` / `make test`, but `torch-requirements.txt` and `torch-index` exist under stockroom home. `doctor smoke` fails and names `stockroom shim ensure-env` (optionally still mentioning `sr-initialize` as the re-pick path).

### Use-Case 2

Torch is missing and no freeze exists. `doctor smoke` keeps pointing at `sr-initialize` / explicit provision (current behavior).

## Requirements

1. When smoke's missing-torch diagnosis runs and a freeze is present, the remedy must recommend `stockroom shim ensure-env`.
2. When no freeze is present, keep the existing `sr-initialize` / explicit provision guidance.
3. Optionally still mention `sr-initialize` when freeze is present as the re-pick path.

## Constraints

1. Scope is the smoke errmsg ratchet (and its tests); do not redesign torch provisioning.
2. Align with the heal path already documented in `docs/user-guide/troubleshooting/torch.md`.

## Acceptance Criteria

1. With freeze present, missing-torch smoke output recommends `stockroom shim ensure-env`.
2. Without freeze, missing-torch smoke output still points at `sr-initialize` / explicit provision.
3. Existing doctor/smoke tests updated or extended so the freeze-aware remedy is locked in.

**Source:** https://github.com/Texarkanine/stockroom/issues/86
