-- STAGING orders.
-- Rules: the order date must be filled in and not in the future,
--        and both the company and the end customer must have been accepted.

CREATE TABLE IF NOT EXISTS staging.stg_orders (
  order_id        integer PRIMARY KEY,
  company_id      integer NOT NULL,
  end_customer_id integer NOT NULL,
  order_date      timestamp NOT NULL
);
TRUNCATE staging.stg_orders;
DELETE FROM etl.rejected_rows WHERE step_name = 'stg_orders';

CREATE TEMP TABLE checked ON COMMIT DROP AS
SELECT r.*,
       CASE WHEN r.order_date IS NULL THEN 'order date is missing'
            WHEN r.order_date::timestamp > now() THEN 'order date is in the future'
            WHEN c.company_id IS NULL THEN 'company was rejected'
            WHEN e.end_customer_id IS NULL THEN 'end customer was rejected'
       END AS reject_reason
FROM raw.raw_orders r
LEFT JOIN staging.stg_companies c ON c.company_id = r.company_id::integer
LEFT JOIN staging.stg_end_customers e ON e.end_customer_id = r.end_customer_id::integer;

INSERT INTO etl.rejected_rows (step_name, reason, row_data)
SELECT 'stg_orders', reject_reason, to_json(c)::text
FROM checked c
WHERE reject_reason IS NOT NULL;

INSERT INTO staging.stg_orders
SELECT order_id::integer, company_id::integer, end_customer_id::integer, order_date::timestamp
FROM checked
WHERE reject_reason IS NULL;
