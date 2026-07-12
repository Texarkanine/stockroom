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

# Cursor local-plugin rsync destination (contributor enter path; not marketplace).
PLUGIN_LOCAL_DEST ?= $(HOME)/.cursor/plugins/local/stockroom

# Optional: make shim TAKEOVER=1 → passes --takeover (dead foreign bake only).
TAKEOVER ?=

.PHONY: help sync lock lock-check test test-js lint format format-check reuse ci torch localdev localdev-clean localdev-status plugin-local shim docs docs-build

# localdev: mirror skills/ into .cursor/skills/stockroom-local so a harness can
# load them "normally", without ever letting the mirror land in a commit.
LOCAL_SKILLS_DIR := .cursor/skills/stockroom-local
PRE_COMMIT_HOOK := .git/hooks/pre-commit
LOCALDEV_MARKER_BEGIN := \# BEGIN stockroom-local (managed by 'make localdev')
LOCALDEV_MARKER_END := \# END stockroom-local

help: ## List targets
	@printf "stockroom dev targets (engine: %s)\n\n" "$(ENGINE)"
	@grep -E '^[a-zA-Z0-9_.-]+:.*##' $(MAKEFILE_LIST) | sort \
		| awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

sync: ## Install deps from the committed lock (torch-free; re-run make torch after)
	$(UV_DIR) sync --frozen

torch: ## Install torch out-of-band (embed/semantic; stripped by make sync)
	$(UV_DIR) pip install torch --index $(TORCH_INDEX)
	PYTHONPATH=$(CURDIR)/$(ENGINE)/src $(UV_RUN) python -m stockroom torch freeze --index $(TORCH_INDEX)

lock: ## Regenerate uv.lock hermetically
	$(UV_DIR) lock

lock-check: ## Fail if uv.lock is stale vs pyproject.toml
	$(UV_DIR) lock --locked

test: sync test-js ## Run pytest and JavaScript unit tests
	$(UV_RUN) pytest

test-js: ## Run native dashboard tests under Node 22
	@command -v $(NODE) >/dev/null 2>&1 || { echo "Node 22 is required for dashboard tests"; exit 1; }
	@version="$$($(NODE) --version)"; case "$$version" in v22.*) ;; *) echo "Node 22 is required for dashboard tests (found $$version)"; exit 1;; esac
	cd $(ENGINE) && $(NODE) --test tests-js/*.test.mjs

lint: sync ## Run ruff check
	$(UV_RUN) ruff check

format: sync ## Apply ruff format
	$(UV_RUN) ruff format

format-check: sync ## Check ruff format (no writes)
	$(UV_RUN) ruff format --check

# Absolute paths are load-bearing: `uv --directory` moves the cwd into the
# engine dir, so relative PYTHONPATH/--app-dir values would resolve wrong.
shim: ## Install the on-path stockroom shim baking this checkout (owner: dev; TAKEOVER=1 for --takeover)
	PYTHONPATH=$(CURDIR)/$(ENGINE)/src $(UV_RUN) python -m stockroom shim install --owner dev --app-dir $(CURDIR)/$(ENGINE) $(if $(filter 1,$(TAKEOVER)),--takeover)

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

localdev: ## Symlink skills/* into .cursor/skills/stockroom-local for in-harness testing (kept out of commits)
	@mkdir -p $(LOCAL_SKILLS_DIR)
	@for link in $(LOCAL_SKILLS_DIR)/*; do \
		[ -L "$$link" ] || continue; \
		name=$$(basename "$$link"); \
		[ -d "skills/$$name" ] || rm -f "$$link"; \
	done
	@for d in skills/*/; do \
		name=$$(basename "$$d"); \
		ln -sfn "../../../skills/$$name" "$(LOCAL_SKILLS_DIR)/$$name"; \
	done
	@touch $(PRE_COMMIT_HOOK)
	@head -1 $(PRE_COMMIT_HOOK) 2>/dev/null | grep -q '^#!' || \
		{ printf '#!/bin/sh\n' | cat - $(PRE_COMMIT_HOOK) > $(PRE_COMMIT_HOOK).tmp && mv $(PRE_COMMIT_HOOK).tmp $(PRE_COMMIT_HOOK); }
	@awk -v b="$(LOCALDEV_MARKER_BEGIN)" -v e="$(LOCALDEV_MARKER_END)" \
		'$$0==b{skip=1} !skip{print} $$0==e{skip=0}' $(PRE_COMMIT_HOOK) > $(PRE_COMMIT_HOOK).tmp && \
		mv $(PRE_COMMIT_HOOK).tmp $(PRE_COMMIT_HOOK)
	@{ \
		echo "$(LOCALDEV_MARKER_BEGIN)"; \
		echo 'if git diff --cached --name-only -- $(LOCAL_SKILLS_DIR) | grep -q .; then git reset --quiet HEAD -- $(LOCAL_SKILLS_DIR); fi'; \
		echo "$(LOCALDEV_MARKER_END)"; \
	} >> $(PRE_COMMIT_HOOK)
	@chmod +x $(PRE_COMMIT_HOOK)
	@echo "localdev ready: $(LOCAL_SKILLS_DIR)/* -> skills/*, pre-commit hook installed at $(PRE_COMMIT_HOOK)"

localdev-clean: ## Undo make localdev (remove stockroom-local symlinks + managed pre-commit block)
	@if [ -d "$(LOCAL_SKILLS_DIR)" ]; then \
		for link in $(LOCAL_SKILLS_DIR)/*; do \
			[ -e "$$link" ] || [ -L "$$link" ] || continue; \
			[ -L "$$link" ] && rm -f "$$link"; \
		done; \
		rmdir "$(LOCAL_SKILLS_DIR)" 2>/dev/null || true; \
	fi
	@if [ -f "$(PRE_COMMIT_HOOK)" ]; then \
		awk -v b="$(LOCALDEV_MARKER_BEGIN)" -v e="$(LOCALDEV_MARKER_END)" \
			'$$0==b{skip=1} !skip{print} $$0==e{skip=0}' $(PRE_COMMIT_HOOK) > $(PRE_COMMIT_HOOK).tmp && \
			mv $(PRE_COMMIT_HOOK).tmp $(PRE_COMMIT_HOOK); \
		chmod +x $(PRE_COMMIT_HOOK); \
	fi
	@echo "localdev-clean: removed $(LOCAL_SKILLS_DIR) symlinks and managed pre-commit block (idempotent)"

plugin-local: ## Rsync this checkout into Cursor plugins/local (PLUGIN_LOCAL_DEST; not a symlink)
	@mkdir -p "$(PLUGIN_LOCAL_DEST)"
	rsync -a --delete \
		--exclude .git --exclude .venv --exclude '**/__pycache__' \
		--exclude .cursor/skills/stockroom-local \
		"$(CURDIR)/" "$(PLUGIN_LOCAL_DEST)/"
	@test -f "$(PLUGIN_LOCAL_DEST)/.cursor-plugin/plugin.json" || { \
		echo "plugin-local: missing $(PLUGIN_LOCAL_DEST)/.cursor-plugin/plugin.json"; exit 1; }
	@echo "plugin-local: synced to $(PLUGIN_LOCAL_DEST) (reload the window; does not touch marketplace installs)"

localdev-status: ## Read-only: skills-mirror / plugin-local / shim hints (no mutations)
	@echo "localdev-status (read-only)"
	@if [ -d "$(LOCAL_SKILLS_DIR)" ] && ls -A "$(LOCAL_SKILLS_DIR)" >/dev/null 2>&1; then \
		echo "  skills-mirror: PRESENT ($(LOCAL_SKILLS_DIR))"; \
		ls -la "$(LOCAL_SKILLS_DIR)" | sed 's/^/    /'; \
	else \
		echo "  skills-mirror: absent ($(LOCAL_SKILLS_DIR))"; \
	fi
	@if [ -f "$(PLUGIN_LOCAL_DEST)/.cursor-plugin/plugin.json" ]; then \
		echo "  plugin-local: PRESENT ($(PLUGIN_LOCAL_DEST)/.cursor-plugin/plugin.json)"; \
	else \
		echo "  plugin-local: absent ($(PLUGIN_LOCAL_DEST))"; \
	fi
	@if [ -f "$(PRE_COMMIT_HOOK)" ] && grep -qF "$(LOCALDEV_MARKER_BEGIN)" "$(PRE_COMMIT_HOOK)" 2>/dev/null; then \
		echo "  pre-commit managed block: PRESENT"; \
	else \
		echo "  pre-commit managed block: absent"; \
	fi
	@echo "  shim: run \`stockroom doctor\` (or \`stockroom shim --help\`) to inspect bake/owner; make does not mutate here"
