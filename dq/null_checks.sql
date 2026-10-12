-- DATA QUALITY: values the reports cannot work without. Every bad_rows number must be 0, or the run fails.

SELECT 'fact_sales: amount missing or not above zero' AS check_name, count(*) AS bad_rows
FROM dw.fact_sales
WHERE amount IS NULL OR amount <= 0

UNION ALL
SELECT 'fact_logins: username missing', count(*)
FROM dw.fact_logins
WHERE username IS NULL OR username = ''

UNION ALL
SELECT 'dim_company: name missing', count(*)
FROM dw.dim_company
WHERE company_name IS NULL OR company_name = ''

UNION ALL
SELECT 'dim_product: name missing', count(*)
FROM dw.dim_product
WHERE product_name IS NULL OR product_name = '';
