-- RAW: an exact copy of b2b.end_customers from the source database (all text).
CREATE TABLE IF NOT EXISTS raw.raw_end_customers (
  end_customer_id text,
  company_id      text,
  document_number text,
  full_name       text,
  date_of_birth   text
);
TRUNCATE raw.raw_end_customers;
