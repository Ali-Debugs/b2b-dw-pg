-- DATA QUALITY: a few rejected rows are normal, but if a step rejects more than 20% of its rows
-- the source is probably broken, and the run must fail instead of loading a half-empty warehouse.
-- bad_rows is the number of rejected rows when a step is over the limit, otherwise 0.

WITH raw_counts (step_name, raw_rows) AS (
            SELECT 'stg_companies',     count(*) FROM raw.raw_companies
  UNION ALL SELECT 'stg_suppliers',     count(*) FROM raw.raw_suppliers
  UNION ALL SELECT 'stg_end_customers', count(*) FROM raw.raw_end_customers
  UNION ALL SELECT 'stg_products',      count(*) FROM raw.raw_products
  UNION ALL SELECT 'stg_catalog_items', count(*) FROM raw.raw_catalog_items
  UNION ALL SELECT 'stg_orders',        count(*) FROM raw.raw_orders
  UNION ALL SELECT 'stg_order_items',   count(*) FROM raw.raw_order_items
  UNION ALL SELECT 'stg_web_logs',      count(*) FROM raw.raw_web_logs WHERE username <> '-'
),
rejected_counts AS (
  SELECT step_name, count(*) AS rejected_rows
  FROM etl.rejected_rows
  GROUP BY step_name
)
SELECT r.step_name || ': more than 20% of the rows were rejected' AS check_name,
       CASE WHEN coalesce(j.rejected_rows, 0) > 0.20 * r.raw_rows THEN j.rejected_rows ELSE 0 END AS bad_rows
FROM raw_counts r
LEFT JOIN rejected_counts j ON j.step_name = r.step_name;
