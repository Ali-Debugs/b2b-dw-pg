-- STAGING catalog items (each company's own price list).
-- Rules: the price must be above zero, and both the company and the product must have been accepted.

CREATE TABLE IF NOT EXISTS staging.stg_catalog_items (
  company_id integer NOT NULL,
  product_id integer NOT NULL,
  price      numeric(12,2) NOT NULL,
  PRIMARY KEY (company_id, product_id)
);
TRUNCATE staging.stg_catalog_items;
DELETE FROM etl.rejected_rows WHERE step_name = 'stg_catalog_items';

CREATE TEMP TABLE checked ON COMMIT DROP AS
SELECT r.*,
       CASE WHEN r.price IS NULL OR r.price::numeric <= 0 THEN 'price is not above zero'
            WHEN c.company_id IS NULL THEN 'company was rejected'
            WHEN p.product_id IS NULL THEN 'product was rejected'
       END AS reject_reason
FROM raw.raw_catalog_items r
LEFT JOIN staging.stg_companies c ON c.company_id = r.company_id::integer
LEFT JOIN staging.stg_products p ON p.product_id = r.product_id::integer;

INSERT INTO etl.rejected_rows (step_name, reason, row_data)
SELECT 'stg_catalog_items', reject_reason, to_json(c)::text
FROM checked c
WHERE reject_reason IS NOT NULL;

INSERT INTO staging.stg_catalog_items
SELECT company_id::integer, product_id::integer, price::numeric
FROM checked
WHERE reject_reason IS NULL;
