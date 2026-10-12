-- FACT sales: one row per order item (one product on one order).
-- amount = quantity x unit price. The other columns point to the dimensions.

CREATE TABLE IF NOT EXISTS dw.fact_sales (
  order_id        integer NOT NULL,
  line_number     integer NOT NULL,
  date_key        integer NOT NULL,
  company_id      integer NOT NULL,
  end_customer_id integer NOT NULL,
  product_id      integer NOT NULL,
  quantity        integer NOT NULL,
  unit_price      numeric(12,2) NOT NULL,
  amount          numeric(14,2) NOT NULL,
  PRIMARY KEY (order_id, line_number)
);
CREATE INDEX IF NOT EXISTS fact_sales_date ON dw.fact_sales (date_key);
TRUNCATE dw.fact_sales;

INSERT INTO dw.fact_sales
SELECT i.order_id,
       i.line_number,
       to_char(o.order_date, 'YYYYMMDD')::integer,
       o.company_id,
       o.end_customer_id,
       i.product_id,
       i.quantity,
       i.unit_price,
       i.quantity * i.unit_price
FROM staging.stg_order_items i
JOIN staging.stg_orders o ON o.order_id = i.order_id;
