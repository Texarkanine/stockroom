# stockroom — dev shortcuts (engine lives in skills/sr-search/)
#
# All lock/sync/run targets use --no-config so ambient ~/.config/uv/uv.toml
# cannot leak into resolution. Run targets use --no-sync so out-of-lock torch
# (provisioned later, per-machine) is never stripped by an exact sync.

ENGINE := skills/sr-search
UV := uv
UV_NO_CFG := --no-config
UV_DIR := $(UV) --directory $(ENGINE) $(UV_NO_CFG)
UV_RUN := $(UV_DIR) run --no-sync

# Per-machine torch wheel index (--no-config bypasses the lock override).
# Override for CUDA, e.g.: make torch TORCH_INDEX=https://download.pytorch.org/whl/cu126
# CPU-only (default): https://download.pytorch.org/whl/cpu
TORCH_INDEX ?= https://download.pytorch.org/whl/cpu

.PHONY: help sync lock lock-check test lint format format-check reuse ci torch

help: ## List targets
	@printf "stockroom dev targets (engine: %s)\n\n" "$(ENGINE)"
	@grep -E '^[a-zA-Z0-9_.-]+:.*##' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

sync: ## Install deps from the committed lock (torch-free; re-run make torch after)
	$(UV_DIR) sync --frozen

torch: ## Install torch out-of-band (embed/semantic; stripped by make sync)
	$(UV_DIR) pip install torch --index $(TORCH_INDEX)

lock: ## Regenerate uv.lock hermetically
	$(UV_DIR) lock

lock-check: ## Fail if uv.lock is stale vs pyproject.toml
	$(UV_DIR) lock --locked

test: sync ## Run pytest
	$(UV_RUN) pytest

lint: sync ## Run ruff check
	$(UV_RUN) ruff check

format: sync ## Apply ruff format
	$(UV_RUN) ruff format

format-check: sync ## Check ruff format (no writes)
	$(UV_RUN) ruff format --check

reuse: sync ## Run reuse lint on the whole repo (REUSE.toml at root)
	$(UV) run --project $(ENGINE) --no-sync $(UV_NO_CFG) reuse lint

ci: sync lock-check lint format-check test reuse ## Full gate (matches CI)
