-- STAGING end customers.
-- Rules: the document number must be filled in, and the company must have been accepted.

CREATE TABLE IF NOT EXISTS staging.stg_end_customers (
  end_customer_id integer PRIMARY KEY,
  company_id      integer NOT NULL,
  document_number text NOT NULL,
  full_name       text NOT NULL,
  date_of_birth   date
);
TRUNCATE staging.stg_end_customers;
DELETE FROM etl.rejected_rows WHERE step_name = 'stg_end_customers';

CREATE TEMP TABLE checked ON COMMIT DROP AS
SELECT r.*,
       CASE WHEN r.document_number IS NULL OR trim(r.document_number) = '' THEN 'document number is missing'
            WHEN c.company_id IS NULL THEN 'company was rejected'
       END AS reject_reason
FROM raw.raw_end_customers r
LEFT JOIN staging.stg_companies c ON c.company_id = r.company_id::integer;

INSERT INTO etl.rejected_rows (step_name, reason, row_data)
SELECT 'stg_end_customers', reject_reason, to_json(c)::text
FROM checked c
WHERE reject_reason IS NOT NULL;

INSERT INTO staging.stg_end_customers
SELECT end_customer_id::integer, company_id::integer, trim(document_number), trim(full_name), date_of_birth::date
FROM checked
WHERE reject_reason IS NULL;
