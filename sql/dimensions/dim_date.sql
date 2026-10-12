-- DIMENSION date: one row per calendar day, so reports can group by month or year without date maths.
-- date_key is the day written as a number, e.g. 20251010.

CREATE TABLE IF NOT EXISTS dw.dim_date (
  date_key    integer PRIMARY KEY,
  full_date   date NOT NULL,
  year        integer NOT NULL,
  month       integer NOT NULL,
  month_name  text NOT NULL,
  month_start date NOT NULL        -- first day of the month, handy for "sales by month"
);
TRUNCATE dw.dim_date;

INSERT INTO dw.dim_date
SELECT to_char(d, 'YYYYMMDD')::integer,
       d::date,
       extract(year FROM d)::integer,
       extract(month FROM d)::integer,
       to_char(d, 'FMMonth'),
       date_trunc('month', d)::date
FROM generate_series(DATE '2020-01-01', DATE '2030-12-31', INTERVAL '1 day') AS d;
