-- REPORT 2: the most popular products in the country that generates the most logins.
-- Step 1: find the one country with the most logins (the country comes from the IP address).
-- Step 2: add up what was sold to the companies of that country and keep the 5 best-selling products.
-- "Popular" means the highest total quantity sold.

CREATE OR REPLACE VIEW mart.mart_top_products_top_country AS
WITH top_country AS (
  SELECT country, count(*) AS logins
  FROM mart.mart_logins
  WHERE country <> 'Unknown'
  GROUP BY country
  ORDER BY logins DESC
  LIMIT 1
)
SELECT t.country,
       t.logins          AS country_logins,
       s.product_name,
       sum(s.quantity)   AS total_quantity,
       sum(s.amount)     AS total_amount
FROM mart.mart_sales s
JOIN top_country t ON t.country = s.country
GROUP BY t.country, t.logins, s.product_id, s.product_name
ORDER BY total_quantity DESC
LIMIT 5;
