#!/bin/bash
# Look inside the warehouse. Only reads.
set -eo pipefail
cd "$(dirname "$0")/.."   # work from the project folder
source demo/settings.sh

echo "Orders: raw = staging + rejected"
show "SELECT 'raw' AS layer, count(*) FROM raw.raw_orders
      UNION ALL SELECT 'staging', count(*) FROM staging.stg_orders
      UNION ALL SELECT 'rejected', count(*) FROM etl.rejected_rows WHERE step_name = 'stg_orders'"

echo "Why rows were rejected"
show "SELECT step_name, reason, count(*) FROM etl.rejected_rows GROUP BY 1, 2 ORDER BY 3 DESC LIMIT 5"

echo "The three reports"
show "SELECT * FROM mart.mart_top_devices"
show "SELECT * FROM mart.mart_top_products_top_country"
show "SELECT * FROM mart.mart_monthly_sales"
