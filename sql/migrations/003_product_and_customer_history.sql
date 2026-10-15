-- MIGRATION 003: products and end customers now keep history too, and fact_sales points to their
-- versions with product_key and end_customer_key. A warehouse built by an older version has these
-- tables in the old shape, so they are dropped here. The same run rebuilds them (and the report views
-- that CASCADE removes with them); their history starts with that run. dim_company is not touched.
DROP TABLE IF EXISTS dw.fact_sales, dw.dim_product, dw.dim_end_customer CASCADE;

-- The order watermarks used to hold the highest order id. Now they hold a change id (CDC), so the
-- old values are removed: the next incremental run does a full load first and writes new ones.
DELETE FROM etl.watermark WHERE table_name IN ('raw_orders', 'raw_order_items');
