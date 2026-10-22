-- MIGRATION 004: fact_logins now has a primary key (username, login_time), like fact_sales has
-- (order_id, line_number). CREATE TABLE IF NOT EXISTS does not change a table that already exists,
-- so the old table is dropped here. fact_logins is rebuilt from staging on every run, so nothing is
-- lost: the same run creates it again with the key (and the report views that CASCADE removes with it).
DROP TABLE IF EXISTS dw.fact_logins CASCADE;
