-- MART sales: fact_sales with every name already joined in (one wide row per order item).
-- The dashboard filters on these columns: date, country, company, product, supplier.
-- Company name and country are the ones the company had on the day of the order.

CREATE OR REPLACE VIEW mart.mart_sales AS
SELECT f.order_id,
       f.line_number,
       d.full_date     AS order_date,
       d.month_start   AS order_month,
       c.company_name,
       k.country_name  AS country,
       f.product_id,
       p.product_name,
       p.supplier_name,
       e.full_name     AS end_customer_name,
       f.quantity,
       f.amount
FROM dw.fact_sales f
JOIN dw.dim_date d         ON d.date_key = f.date_key
JOIN dw.dim_company c      ON c.company_key = f.company_key
JOIN dw.dim_country k      ON k.country_code = c.country_code
JOIN dw.dim_product p      ON p.product_id = f.product_id
JOIN dw.dim_end_customer e ON e.end_customer_id = f.end_customer_id;
