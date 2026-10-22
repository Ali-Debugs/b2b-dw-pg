-- DATA QUALITY: things that must be unique. Every bad_rows number must be 0, or the run fails.

SELECT 'dim_company: same CUIT on two current companies' AS check_name, count(*) AS bad_rows
FROM (SELECT cuit FROM dw.dim_company WHERE is_current GROUP BY cuit HAVING count(*) > 1) AS doubles

UNION ALL
SELECT 'dim_company: a company without exactly one current version', count(*)
FROM (SELECT company_id FROM dw.dim_company GROUP BY company_id
      HAVING count(*) FILTER (WHERE is_current) <> 1) AS wrong

UNION ALL
SELECT 'dim_product: a product without exactly one current version', count(*)
FROM (SELECT product_id FROM dw.dim_product GROUP BY product_id
      HAVING count(*) FILTER (WHERE is_current) <> 1) AS wrong

UNION ALL
SELECT 'dim_end_customer: an end customer without exactly one current version', count(*)
FROM (SELECT end_customer_id FROM dw.dim_end_customer GROUP BY end_customer_id
      HAVING count(*) FILTER (WHERE is_current) <> 1) AS wrong

UNION ALL
SELECT 'dim_end_customer: same document number on two current end customers', count(*)
FROM (SELECT document_number FROM dw.dim_end_customer WHERE is_current GROUP BY document_number HAVING count(*) > 1) AS doubles

UNION ALL
SELECT 'fact_sales: same order line twice', count(*)
FROM (SELECT order_id, line_number FROM dw.fact_sales GROUP BY order_id, line_number HAVING count(*) > 1) AS doubles;
