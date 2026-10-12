-- MIGRATION 001: the company dimension now keeps history, and the facts point to it with company_key.
-- A warehouse built by an older version has these tables in the old shape, so they are dropped here.
-- The same run rebuilds them (and the report views that CASCADE removes with them).
-- On a brand-new warehouse there is nothing to drop and this does nothing.

DROP TABLE IF EXISTS dw.fact_sales, dw.fact_logins, dw.dim_company CASCADE;
