-- DATA QUALITY: every fact row must point to a dimension row that exists.
-- Every bad_rows number must be 0, or the run fails.

SELECT 'fact_sales: date not in dim_date' AS check_name, count(*) AS bad_rows
FROM dw.fact_sales f
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_date d WHERE d.date_key = f.date_key)

UNION ALL
SELECT 'fact_sales: company not in dim_company', count(*)
FROM dw.fact_sales f
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_company c WHERE c.company_id = f.company_id)

UNION ALL
SELECT 'fact_sales: product not in dim_product', count(*)
FROM dw.fact_sales f
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_product p WHERE p.product_id = f.product_id)

UNION ALL
SELECT 'fact_sales: end customer not in dim_end_customer', count(*)
FROM dw.fact_sales f
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_end_customer e WHERE e.end_customer_id = f.end_customer_id)

UNION ALL
SELECT 'fact_logins: date not in dim_date', count(*)
FROM dw.fact_logins f
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_date d WHERE d.date_key = f.date_key)

UNION ALL
SELECT 'fact_logins: company not in dim_company', count(*)
FROM dw.fact_logins f
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_company c WHERE c.company_id = f.company_id)

UNION ALL
SELECT 'fact_logins: device not in dim_device', count(*)
FROM dw.fact_logins f
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_device v WHERE v.device_key = f.device_key)

UNION ALL
SELECT 'fact_logins: country not in dim_country', count(*)
FROM dw.fact_logins f
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_country k WHERE k.country_code = f.country_code)

UNION ALL
SELECT 'dim_company: country not in dim_country', count(*)
FROM dw.dim_company c
WHERE NOT EXISTS (SELECT 1 FROM dw.dim_country k WHERE k.country_code = c.country_code);
