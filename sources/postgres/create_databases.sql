-- Runs once when the PostgreSQL container is created.
-- b2b_source already exists (docker-compose.yml creates it); this adds the two warehouse databases.
CREATE DATABASE b2b_warehouse_dev;   -- DEV: for trying and testing changes
CREATE DATABASE b2b_warehouse_prod;  -- PROD: the live warehouse behind the dashboard

-- The warehouses work in Buenos Aires time, so "today" and every date mean the local business day.
ALTER DATABASE b2b_warehouse_dev SET timezone TO 'America/Argentina/Buenos_Aires';
ALTER DATABASE b2b_warehouse_prod SET timezone TO 'America/Argentina/Buenos_Aires';
