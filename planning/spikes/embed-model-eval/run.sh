#!/usr/bin/env bash
# One-shot: export the dataset from the local warehouse, then benchmark.
# Runs entirely in one interpreter (no uv/project needed) — just torch +
# sentence-transformers + duckdb + numpy (see requirements-bench.txt).
#
#   ./run.sh <label> [warehouse_db_path]
#
# Examples:
#   ./run.sh macbook-m4
#   ./run.sh macbook-m4 ~/.stockroom/warehouse.duckdb
#
# Override the interpreter with PYTHON=/path/to/python ./run.sh ...
#
# PRIVACY: only results-<label>.json (metrics, no message text) is produced for
# sharing. The corpus/queries parquet (raw text) stays local and is gitignored.
set -euo pipefail
cd "$(dirname "$0")"

LABEL="${1:-$(hostname -s 2>/dev/null || echo run)}"
DB_ARG=()
if [[ $# -ge 2 ]]; then DB_ARG=(--db "$2"); fi
PYTHON="${PYTHON:-python3}"

echo ">> exporting dataset from warehouse..."
"$PYTHON" export_dataset.py "${DB_ARG[@]}"

echo ">> running benchmark (label=$LABEL)..."
"$PYTHON" benchmark.py --label "$LABEL"

echo ">> done. Share planning/spikes/embed-model-eval/results-$LABEL.json"
