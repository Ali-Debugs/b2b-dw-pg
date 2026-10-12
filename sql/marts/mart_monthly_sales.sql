-- REPORT 3: total B2B platform sales by month for the last year.
-- "Last year" = the last 12 complete months. The current month is left out because it is not
-- finished yet, and a half month would look like a drop in sales.

CREATE OR REPLACE VIEW mart.mart_monthly_sales AS
SELECT order_month              AS month,
       sum(amount)              AS total_sales,
       count(DISTINCT order_id) AS orders
FROM mart.mart_sales
WHERE order_month >= date_trunc('month', current_date) - INTERVAL '12 months'
  AND order_month <  date_trunc('month', current_date)
GROUP BY order_month
ORDER BY order_month;
