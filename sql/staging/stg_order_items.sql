-- STAGING order items.
-- Rules: quantity and unit price must be above zero,
--        and both the order and the product must have been accepted.

CREATE TABLE IF NOT EXISTS staging.stg_order_items (
  order_id    integer NOT NULL,
  line_number integer NOT NULL,
  product_id  integer NOT NULL,
  quantity    integer NOT NULL,
  unit_price  numeric(12,2) NOT NULL,
  PRIMARY KEY (order_id, line_number)
);
TRUNCATE staging.stg_order_items;
DELETE FROM etl.rejected_rows WHERE step_name = 'stg_order_items';

CREATE TEMP TABLE checked ON COMMIT DROP AS
SELECT r.*,
       CASE WHEN r.quantity IS NULL OR r.quantity::integer <= 0 THEN 'quantity is not above zero'
            WHEN r.unit_price IS NULL OR r.unit_price::numeric <= 0 THEN 'unit price is not above zero'
            WHEN o.order_id IS NULL THEN 'order was rejected'
            WHEN p.product_id IS NULL THEN 'product was rejected'
       END AS reject_reason
FROM raw.raw_order_items r
LEFT JOIN staging.stg_orders o ON o.order_id = r.order_id::integer
LEFT JOIN staging.stg_products p ON p.product_id = r.product_id::integer;

INSERT INTO etl.rejected_rows (step_name, reason, row_data)
SELECT 'stg_order_items', reject_reason, to_json(c)::text
FROM checked c
WHERE reject_reason IS NOT NULL;

INSERT INTO staging.stg_order_items
SELECT order_id::integer, line_number::integer, product_id::integer, quantity::integer, unit_price::numeric
FROM checked
WHERE reject_reason IS NULL;
