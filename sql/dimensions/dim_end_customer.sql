-- DIMENSION end customer: one row per person who receives goods.

CREATE TABLE IF NOT EXISTS dw.dim_end_customer (
  end_customer_id integer PRIMARY KEY,
  document_number text NOT NULL,
  full_name       text NOT NULL,
  date_of_birth   date,
  company_id      integer NOT NULL
);
TRUNCATE dw.dim_end_customer;

INSERT INTO dw.dim_end_customer
SELECT end_customer_id, document_number, full_name, date_of_birth, company_id
FROM staging.stg_end_customers;
