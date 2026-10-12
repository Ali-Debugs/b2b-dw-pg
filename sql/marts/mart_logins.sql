-- MART logins: fact_logins with every name already joined in (one wide row per login).
-- The dashboard filters on these columns: date, country, company, device.

CREATE OR REPLACE VIEW mart.mart_logins AS
SELECT f.login_time,
       d.full_date     AS login_date,
       d.month_start   AS login_month,
       f.username,
       c.company_name,
       v.device_name   AS device,
       k.country_name  AS country
FROM dw.fact_logins f
JOIN dw.dim_date d    ON d.date_key = f.date_key
JOIN dw.dim_company c ON c.company_key = f.company_key
JOIN dw.dim_device v  ON v.device_key = f.device_key
JOIN dw.dim_country k ON k.country_code = f.country_code;
