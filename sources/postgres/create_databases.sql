-- Runs once when the PostgreSQL container is created.
-- b2b_source already exists (docker-compose.yml creates it); this adds the warehouse database.
CREATE DATABASE b2b_warehouse;

-- The warehouse works in Buenos Aires time, so "today" and every date mean the local business day.
ALTER DATABASE b2b_warehouse SET timezone TO 'America/Argentina/Buenos_Aires';
