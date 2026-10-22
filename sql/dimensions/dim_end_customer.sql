-- DIMENSION end customer, WITH HISTORY (a "slowly changing dimension, type 2"), built like dim_company.
-- When a person's document number, name, date of birth or company changes, the old row is kept and a
-- new row is added.
--
--   end_customer_key  the warehouse's own key, one per version. fact_sales points to this.
--   valid_from        first day the version is valid
--   valid_to          the day it stopped being valid (9999-12-31 while it is the current version)
--
-- This table is NOT emptied on each run: the old versions are the history.

CREATE TABLE IF NOT EXISTS dw.dim_end_customer (
  end_customer_key integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  end_customer_id  integer NOT NULL,
  document_number  text NOT NULL,
  full_name        text NOT NULL,
  date_of_birth    date,
  company_id       integer NOT NULL,
  valid_from       date NOT NULL,
  valid_to         date NOT NULL,
  is_current       boolean NOT NULL
);

-- Step 1: a person changed -> close the current version (it was valid until today).
UPDATE dw.dim_end_customer d
SET valid_to = current_date,
    is_current = false
FROM staging.stg_end_customers s
WHERE d.end_customer_id = s.end_customer_id
  AND d.is_current
  AND (d.document_number, d.full_name, d.date_of_birth, d.company_id)
      IS DISTINCT FROM (s.document_number, s.full_name, s.date_of_birth, s.company_id);

-- Step 2: add a current version for every person that has none.
-- That is a new end customer, or one whose version was just closed in step 1.
-- The very first version starts in 1900, so it also covers all the old orders.
INSERT INTO dw.dim_end_customer (end_customer_id, document_number, full_name, date_of_birth, company_id, valid_from, valid_to, is_current)
SELECT s.end_customer_id, s.document_number, s.full_name, s.date_of_birth, s.company_id,
       CASE WHEN EXISTS (SELECT 1 FROM dw.dim_end_customer old WHERE old.end_customer_id = s.end_customer_id)
            THEN current_date
            ELSE DATE '1900-01-01'
       END,
       DATE '9999-12-31',
       true
FROM staging.stg_end_customers s
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_end_customer d WHERE d.end_customer_id = s.end_customer_id AND d.is_current);
