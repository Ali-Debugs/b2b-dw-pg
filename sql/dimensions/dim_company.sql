-- DIMENSION company, WITH HISTORY (a "slowly changing dimension, type 2").
-- When a company changes its name, country, CUIT or supplier status, the old row is kept and a new
-- row is added. So one company can have several rows (versions), and exactly one is the current one.
--
--   company_key  the warehouse's own key, one per version. The fact tables point to this.
--                (This is a "surrogate key": company_id cannot be the key, it repeats per version.)
--   valid_from   first day the version is valid
--   valid_to     the day it stopped being valid (9999-12-31 while it is the current version)
--
-- This table is NOT emptied on each run: the old versions are the history.

CREATE TABLE IF NOT EXISTS dw.dim_company (
  company_key  integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  company_id   integer NOT NULL,
  cuit         text NOT NULL,
  company_name text NOT NULL,
  country_code text NOT NULL,
  is_supplier  boolean NOT NULL,
  valid_from   date NOT NULL,
  valid_to     date NOT NULL,
  is_current   boolean NOT NULL
);

-- The companies as they are in the source right now.
CREATE TEMP TABLE source_companies ON COMMIT DROP AS
SELECT c.company_id, c.cuit, c.name AS company_name, c.country_code, s.company_id IS NOT NULL AS is_supplier
FROM staging.stg_companies c
LEFT JOIN staging.stg_suppliers s ON s.company_id = c.company_id;

-- Step 1: a company changed -> close its current version (it was valid until today).
UPDATE dw.dim_company d
SET valid_to = current_date,
    is_current = false
FROM source_companies s
WHERE d.company_id = s.company_id
  AND d.is_current
  AND (d.cuit, d.company_name, d.country_code, d.is_supplier)
      IS DISTINCT FROM (s.cuit, s.company_name, s.country_code, s.is_supplier);

-- Step 2: add a current version for every company that has none.
-- That is a brand-new company, or one whose version was just closed in step 1.
-- The very first version of a company starts in 1900, so it also covers all its old orders.
INSERT INTO dw.dim_company (company_id, cuit, company_name, country_code, is_supplier, valid_from, valid_to, is_current)
SELECT s.company_id, s.cuit, s.company_name, s.country_code, s.is_supplier,
       CASE WHEN EXISTS (SELECT 1 FROM dw.dim_company old WHERE old.company_id = s.company_id)
            THEN current_date
            ELSE DATE '1900-01-01'
       END,
       DATE '9999-12-31',
       true
FROM source_companies s
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_company d WHERE d.company_id = s.company_id AND d.is_current);
