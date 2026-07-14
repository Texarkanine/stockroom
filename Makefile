# stockroom — dev shortcuts (engine lives in skills/sr-search/)
#
# All lock/sync/run targets use --no-config so ambient ~/.config/uv/uv.toml
# cannot leak into resolution. Run targets use --no-sync so out-of-lock torch
# (provisioned later, per-machine) is never stripped by an exact sync.

ENGINE := skills/sr-search
UV := uv
NODE ?= node
UV_NO_CFG := --no-config
UV_DIR := $(UV) --directory $(ENGINE) $(UV_NO_CFG)
UV_RUN := $(UV_DIR) run --no-sync

# Per-machine torch wheel index + hashed freeze (--no-config bypasses the lock override).
# Override for CUDA, e.g.: make torch TORCH_INDEX=https://download.pytorch.org/whl/cu126
# CPU-only (default): https://download.pytorch.org/whl/cpu
# After install, freezes the accepted stack under stockroom home (see docs/user-guide/troubleshooting/torch.md).
TORCH_INDEX ?= https://download.pytorch.org/whl/cpu

# Optional: make shim TAKEOVER=1 → --takeover; FORCE=1 → --force (both for live foreign).
TAKEOVER ?=
FORCE ?=

# Harness-scoped localdev atoms require HARNESS=cursor|claude.
HARNESS ?=

SCRIPTS := scripts
LOCALDEV_SH := $(SCRIPTS)/localdev.sh

.PHONY: help sync lock lock-check test test-dashboard-js test-dashboard-py lint format format-check reuse ci torch \
	local-skills local-engine local-dashboard localdev localdev-clean localdev-status shim \
	docs docs-build require-harness

help: ## List targets
	@printf "stockroom dev targets (engine: %s)\n\n" "$(ENGINE)"
	@grep -E '^[a-zA-Z0-9_.-]+:.*##' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  %-22s %s\n", $$1, $$2}'

sync: ## Install deps from the committed lock (torch-free; re-run make torch after)
	$(UV_DIR) sync --frozen

torch: ## Install torch out-of-band (embed/semantic; stripped by make sync)
	$(UV_DIR) pip install torch --index $(TORCH_INDEX)
	PYTHONPATH=$(CURDIR)/$(ENGINE)/src $(UV_RUN) python -m stockroom torch freeze --index $(TORCH_INDEX)

lock: ## Regenerate uv.lock hermetically
	$(UV_DIR) lock

lock-check: ## Fail if uv.lock is stale vs pyproject.toml
	$(UV_DIR) lock --locked

test: sync test-dashboard-js ## Run pytest and JavaScript unit tests
	$(UV_RUN) pytest

test-dashboard-js: ## Dashboard ES-module tests (Node 22; no sync)
	@command -v $(NODE) >/dev/null 2>&1 || { echo "Node 22 is required for dashboard tests"; exit 1; }
	@version="$$($(NODE) --version)"; case "$$version" in v22.*) ;; *) echo "Node 22 is required for dashboard tests (found $$version)"; exit 1;; esac
	cd $(ENGINE) && $(NODE) --test tests-js/*.test.mjs

# No sync: preserves out-of-lock torch. Full gate remains `make test` / `make ci`.
test-dashboard-py: ## Dashboard pytest (tests/test_dashboard_*.py; torch-safe; no sync)
	cd $(ENGINE) && $(UV) run --no-sync $(UV_NO_CFG) pytest tests/test_dashboard_*.py

lint: sync ## Run ruff check
	$(UV_RUN) ruff check

format: sync ## Apply ruff format
	$(UV_RUN) ruff format

format-check: sync ## Check ruff format (no writes)
	$(UV_RUN) ruff format --check

# Absolute paths are load-bearing: `uv --directory` moves the cwd into the
# engine dir, so relative PYTHONPATH/--app-dir values would resolve wrong.
shim: ## Install on-path shim for this checkout (owner: dev; TAKEOVER=1 / FORCE=1 as needed)
	PYTHONPATH=$(CURDIR)/$(ENGINE)/src $(UV_RUN) python -m stockroom shim install --owner dev --app-dir $(CURDIR)/$(ENGINE) $(if $(filter 1,$(TAKEOVER)),--takeover) $(if $(filter 1,$(FORCE)),--force)

reuse: sync ## Run reuse lint on the whole repo (REUSE.toml at root)
	$(UV) run --project $(ENGINE) --no-sync $(UV_NO_CFG) reuse lint

ci: sync lock-check lint format-check test reuse ## Full gate (matches CI)

# Docs site (root pyproject.toml docs group — separate from the engine project).
# Requires uv: https://docs.astral.sh/uv/
docs: ## Local docs preview (properdocs serve)
	uv run properdocs serve

docs-build: ## Strict docs build (matches docs CI)
	uv sync --group docs --frozen
	uv run properdocs build --strict

require-harness:
	@case "$(HARNESS)" in \
		cursor|claude) ;; \
		*) echo "HARNESS must be set to 'cursor' or 'claude' (got: '$(HARNESS)')"; exit 1 ;; \
	esac

local-skills: require-harness ## Wire checkout skills for HARNESS=cursor|claude
	@$(LOCALDEV_SH) skills --harness "$(HARNESS)" --repo-root "$(CURDIR)"

local-engine: ## Claim shim (TAKEOVER+FORCE) + ensure-env for this checkout
	@$(MAKE) --no-print-directory shim TAKEOVER=1 FORCE=1
	@PYTHONPATH=$(CURDIR)/$(ENGINE)/src $(UV_RUN) python -m stockroom shim ensure-env --app-dir $(CURDIR)/$(ENGINE)
	@echo "local-engine: shim claimed (dev+takeover+force) and ensure-env run"

local-dashboard: ## Bounce stockroom dashboard (identity-aware replace)
	@PYTHONPATH=$(CURDIR)/$(ENGINE)/src $(UV_RUN) python -m stockroom dashboard
	@echo "local-dashboard: dashboard bounced"

localdev: require-harness ## Compose local-skills + local-engine + local-dashboard
	@$(MAKE) --no-print-directory local-skills HARNESS=$(HARNESS)
	@$(MAKE) --no-print-directory local-engine
	@$(MAKE) --no-print-directory local-dashboard
	@echo "localdev ready (HARNESS=$(HARNESS)): skills, engine, dashboard"

localdev-clean: require-harness ## Undo localdev bits + drop owner=dev shim (not warehouse)
	@$(LOCALDEV_SH) clean --harness "$(HARNESS)" --repo-root "$(CURDIR)"

localdev-status: ## Read-only: localdev-managed vs shim sections (no mutations)
	@$(LOCALDEV_SH) status --repo-root "$(CURDIR)"
