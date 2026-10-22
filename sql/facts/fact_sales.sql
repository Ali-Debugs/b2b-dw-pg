-- FACT sales: one row per order item (one product on one order).
-- amount = quantity x unit price. The other columns point to the dimensions.
-- company_key, end_customer_key and product_key point to the versions that were valid on the day of
-- the order, so an old sale keeps the names, country and price that were true at that time.

CREATE TABLE IF NOT EXISTS dw.fact_sales (
  order_id         integer NOT NULL,
  line_number      integer NOT NULL,
  date_key         integer NOT NULL,
  company_key      integer NOT NULL,
  end_customer_key integer NOT NULL,
  product_key      integer NOT NULL,
  quantity         integer NOT NULL,
  unit_price       numeric(12,2) NOT NULL,
  amount           numeric(14,2) NOT NULL,
  PRIMARY KEY (order_id, line_number)
);
CREATE INDEX IF NOT EXISTS fact_sales_date ON dw.fact_sales (date_key);
TRUNCATE dw.fact_sales;

INSERT INTO dw.fact_sales
SELECT i.order_id,
       i.line_number,
       to_char(o.order_date, 'YYYYMMDD')::integer,
       c.company_key,
       e.end_customer_key,
       p.product_key,
       i.quantity,
       i.unit_price,
       i.quantity * i.unit_price
FROM staging.stg_order_items i
JOIN staging.stg_orders o ON o.order_id = i.order_id
-- each dimension: the version that was valid on the day of the order
JOIN dw.dim_company c      ON c.company_id = o.company_id
                          AND o.order_date::date >= c.valid_from
                          AND o.order_date::date <  c.valid_to
JOIN dw.dim_end_customer e ON e.end_customer_id = o.end_customer_id
                          AND o.order_date::date >= e.valid_from
                          AND o.order_date::date <  e.valid_to
JOIN dw.dim_product p      ON p.product_id = i.product_id
                          AND o.order_date::date >= p.valid_from
                          AND o.order_date::date <  p.valid_to;
