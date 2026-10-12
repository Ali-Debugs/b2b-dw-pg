-- DIMENSION country: one row per country. Used for both the company's country and the login country.
-- 'XX' is for IP addresses that are not in the lookup file.

CREATE TABLE IF NOT EXISTS dw.dim_country (
  country_code text PRIMARY KEY,
  country_name text NOT NULL
);
TRUNCATE dw.dim_country;

INSERT INTO dw.dim_country
SELECT DISTINCT country_code, country_name FROM raw.raw_ip_country
UNION
SELECT 'XX', 'Unknown';
