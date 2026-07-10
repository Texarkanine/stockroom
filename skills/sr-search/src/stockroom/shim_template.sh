#!/bin/sh
# stockroom — generated on-path launcher. Do not edit: regenerate via
# `stockroom shim install` (harness owners: sr-initialize; dev: make shim).
# STOCKROOM_OWNER={{OWNER}}
# STOCKROOM_APP_DIR={{APP_DIR}}
# STOCKROOM_GENERATOR_VERSION={{VERSION}}
#
# Baked-only, succeed-or-refuse: this shim never scans, ranks, or guesses.
# It execs the baked engine through the torch-safe contract, or refuses
# with a one-line remedy.

APP_DIR={{APP_DIR_SH}}

command -v uv >/dev/null 2>&1 || {
	echo "stockroom: uv not found — see sr-initialize prerequisites" >&2
	exit 127
}

[ -f "$APP_DIR/pyproject.toml" ] || {
	echo "stockroom: baked engine dir $APP_DIR is missing or invalid — {{REMEDY}}" >&2
	exit 1
}

# Refuse before `uv run --no-sync` when locked deps are missing. That flag
# otherwise creates an empty .venv and fails mid-import; session hooks heal
# via `shim rectify` → ensure_engine_env.
"$APP_DIR/.venv/bin/python" -c "import duckdb" >/dev/null 2>&1 || {
	echo "stockroom: engine env at $APP_DIR is not ready — {{REMEDY}}" >&2
	exit 1
}

PYTHONPATH="$APP_DIR/src" exec uv run --project "$APP_DIR" --no-sync --no-config python -m stockroom "$@"
