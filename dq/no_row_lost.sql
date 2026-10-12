-- DATA QUALITY: no row may disappear between raw and staging.
-- For every table:  raw rows - good rows - rejected rows  must be 0.
-- (Web log lines with username '-' are visitors who are not logged in; they are left out on purpose.)

SELECT 'stg_companies: raw rows not all accounted for' AS check_name,
       abs((SELECT count(*) FROM raw.raw_companies)
         - (SELECT count(*) FROM staging.stg_companies)
         - (SELECT count(*) FROM etl.rejected_rows WHERE step_name = 'stg_companies')) AS bad_rows

UNION ALL
SELECT 'stg_suppliers: raw rows not all accounted for',
       abs((SELECT count(*) FROM raw.raw_suppliers)
         - (SELECT count(*) FROM staging.stg_suppliers)
         - (SELECT count(*) FROM etl.rejected_rows WHERE step_name = 'stg_suppliers'))

UNION ALL
SELECT 'stg_end_customers: raw rows not all accounted for',
       abs((SELECT count(*) FROM raw.raw_end_customers)
         - (SELECT count(*) FROM staging.stg_end_customers)
         - (SELECT count(*) FROM etl.rejected_rows WHERE step_name = 'stg_end_customers'))

UNION ALL
SELECT 'stg_products: raw rows not all accounted for',
       abs((SELECT count(*) FROM raw.raw_products)
         - (SELECT count(*) FROM staging.stg_products)
         - (SELECT count(*) FROM etl.rejected_rows WHERE step_name = 'stg_products'))

UNION ALL
SELECT 'stg_catalog_items: raw rows not all accounted for',
       abs((SELECT count(*) FROM raw.raw_catalog_items)
         - (SELECT count(*) FROM staging.stg_catalog_items)
         - (SELECT count(*) FROM etl.rejected_rows WHERE step_name = 'stg_catalog_items'))

UNION ALL
SELECT 'stg_orders: raw rows not all accounted for',
       abs((SELECT count(*) FROM raw.raw_orders)
         - (SELECT count(*) FROM staging.stg_orders)
         - (SELECT count(*) FROM etl.rejected_rows WHERE step_name = 'stg_orders'))

UNION ALL
SELECT 'stg_order_items: raw rows not all accounted for',
       abs((SELECT count(*) FROM raw.raw_order_items)
         - (SELECT count(*) FROM staging.stg_order_items)
         - (SELECT count(*) FROM etl.rejected_rows WHERE step_name = 'stg_order_items'))

UNION ALL
SELECT 'stg_web_logs: raw rows not all accounted for',
       abs((SELECT count(*) FROM raw.raw_web_logs WHERE username <> '-')
         - (SELECT count(*) FROM staging.stg_web_logs)
         - (SELECT count(*) FROM etl.rejected_rows WHERE step_name = 'stg_web_logs'));
