#!/bin/bash
# A run fails and is continued, then fails again and is started over. It waits so you can show Metabase.
set -eo pipefail
cd "$(dirname "$0")/.."   # work from the project folder
source demo/settings.sh

echo "A run that fails on purpose"
$PY run.py --fail-at fact_sales | grep -E "^Run|FAILED" || true
read -p "Show the failed run in Metabase, then press Enter to run again: " pause

echo "Run again: it continues the same run"
$PY run.py | grep -E "^Run|FAILED"

echo "Fail again"
$PY run.py --fail-at fact_sales | grep -E "^Run|FAILED" || true
read -p "Show it in Metabase, then press Enter to start over with --fresh: " pause

echo "Start over"
$PY run.py --fresh | grep -E "^Run|FAILED"

show "SELECT run_id, load_type, status FROM etl.run_log ORDER BY run_id DESC LIMIT 5"
