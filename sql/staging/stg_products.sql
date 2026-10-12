-- STAGING products.
-- Rules: the default price must be above zero, and the supplier must have been accepted.

CREATE TABLE IF NOT EXISTS staging.stg_products (
  product_id    integer PRIMARY KEY,
  supplier_id   integer NOT NULL,
  name          text NOT NULL,
  default_price numeric(12,2) NOT NULL
);
TRUNCATE staging.stg_products;
DELETE FROM etl.rejected_rows WHERE step_name = 'stg_products';

CREATE TEMP TABLE checked ON COMMIT DROP AS
SELECT r.*,
       CASE WHEN r.default_price IS NULL THEN 'default price is missing'
            WHEN r.default_price::numeric <= 0 THEN 'default price is not above zero'
            WHEN s.company_id IS NULL THEN 'supplier was rejected'
       END AS reject_reason
FROM raw.raw_products r
LEFT JOIN staging.stg_suppliers s ON s.company_id = r.supplier_id::integer;

INSERT INTO etl.rejected_rows (step_name, reason, row_data)
SELECT 'stg_products', reject_reason, to_json(c)::text
FROM checked c
WHERE reject_reason IS NOT NULL;

INSERT INTO staging.stg_products
SELECT product_id::integer, supplier_id::integer, trim(name), default_price::numeric
FROM checked
WHERE reject_reason IS NULL;
