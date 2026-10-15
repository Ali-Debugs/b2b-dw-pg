#!/bin/bash
# New orders arrive and old ones are edited or deleted: only the changes are loaded (CDC).
# Run it after a full load (that writes the watermarks).
set -eo pipefail
cd "$(dirname "$0")"
source ./demo_settings.sh

counts() {
  show "SELECT (SELECT count(DISTINCT order_id) FROM mart.mart_sales) AS orders, (SELECT count(*) FROM mart.mart_logins) AS logins"
}

echo "Before"
counts

$PY -m seed.add_new_data
$PY -m seed.change_old_orders
$PY run.py --incremental | grep -E "^Run|changed orders|new rows|FAILED"

echo "After"
counts
show "SELECT table_name, value FROM etl.watermark ORDER BY 1"
