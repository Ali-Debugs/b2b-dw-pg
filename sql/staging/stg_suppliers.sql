-- STAGING suppliers: a supplier is only kept if its company was accepted.

CREATE TABLE IF NOT EXISTS staging.stg_suppliers (
  company_id     integer PRIMARY KEY,
  supplier_since date NOT NULL
);
TRUNCATE staging.stg_suppliers;
DELETE FROM etl.rejected_rows WHERE step_name = 'stg_suppliers';

CREATE TEMP TABLE checked ON COMMIT DROP AS
SELECT r.*,
       CASE WHEN c.company_id IS NULL THEN 'company was rejected'
       END AS reject_reason
FROM raw.raw_suppliers r
LEFT JOIN staging.stg_companies c ON c.company_id = r.company_id::integer;

INSERT INTO etl.rejected_rows (step_name, reason, row_data)
SELECT 'stg_suppliers', reject_reason, to_json(c)::text
FROM checked c
WHERE reject_reason IS NOT NULL;

INSERT INTO staging.stg_suppliers
SELECT company_id::integer, supplier_since::date
FROM checked
WHERE reject_reason IS NULL;
