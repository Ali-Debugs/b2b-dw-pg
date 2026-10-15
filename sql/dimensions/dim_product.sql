-- DIMENSION product, WITH HISTORY (a "slowly changing dimension, type 2"), built like dim_company.
-- When a product's name, default price or supplier changes, the old row is kept and a new row is added.
--
--   product_key  the warehouse's own key, one per version. fact_sales points to this.
--   valid_from   first day the version is valid
--   valid_to     the day it stopped being valid (9999-12-31 while it is the current version)
--
-- This table is NOT emptied on each run: the old versions are the history.

CREATE TABLE IF NOT EXISTS dw.dim_product (
  product_key   integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  product_id    integer NOT NULL,
  product_name  text NOT NULL,
  default_price numeric(12,2) NOT NULL,
  supplier_id   integer NOT NULL,
  supplier_name text NOT NULL,
  valid_from    date NOT NULL,
  valid_to      date NOT NULL,
  is_current    boolean NOT NULL
);

-- The products as they are in the source right now, with the name of the supplier filled in.
CREATE TEMP TABLE source_products ON COMMIT DROP AS
SELECT p.product_id, p.name AS product_name, p.default_price, p.supplier_id, c.name AS supplier_name
FROM staging.stg_products p
JOIN staging.stg_companies c ON c.company_id = p.supplier_id;

-- Step 1: a product changed -> close its current version (it was valid until today).
UPDATE dw.dim_product d
SET valid_to = current_date,
    is_current = false
FROM source_products s
WHERE d.product_id = s.product_id
  AND d.is_current
  AND (d.product_name, d.default_price, d.supplier_id, d.supplier_name)
      IS DISTINCT FROM (s.product_name, s.default_price, s.supplier_id, s.supplier_name);

-- Step 2: add a current version for every product that has none.
-- That is a brand-new product, or one whose version was just closed in step 1.
-- The very first version of a product starts in 1900, so it also covers all its old orders.
INSERT INTO dw.dim_product (product_id, product_name, default_price, supplier_id, supplier_name, valid_from, valid_to, is_current)
SELECT s.product_id, s.product_name, s.default_price, s.supplier_id, s.supplier_name,
       CASE WHEN EXISTS (SELECT 1 FROM dw.dim_product old WHERE old.product_id = s.product_id)
            THEN current_date
            ELSE DATE '1900-01-01'
       END,
       DATE '9999-12-31',
       true
FROM source_products s
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_product d WHERE d.product_id = s.product_id AND d.is_current);
