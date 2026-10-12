-- FACT logins: one row per login (one visit of a logged-in user).
-- The web log has one line per page a user opens, so one visit is many lines.
-- Rule: a line starts a new login when it is the user's first line ever,
--       or when the user's line before it is more than 30 minutes older.
-- The login keeps the time, device and country of that first line.
-- company_key points to the version of the company that was valid on the day of the login.

CREATE TABLE IF NOT EXISTS dw.fact_logins (
  date_key     integer NOT NULL,
  login_time   timestamptz NOT NULL,
  username     text NOT NULL,
  company_key  integer NOT NULL,
  device_key   integer NOT NULL,
  country_code text NOT NULL
);
CREATE INDEX IF NOT EXISTS fact_logins_date ON dw.fact_logins (date_key);
TRUNCATE dw.fact_logins;

INSERT INTO dw.fact_logins
WITH log_lines AS (
  -- next to every line, put the time of the same user's line before it (NULL for the first one)
  SELECT w.*,
         lag(w.login_time) OVER (PARTITION BY w.username ORDER BY w.login_time) AS previous_time
  FROM staging.stg_web_logs w
)
SELECT to_char(l.login_time, 'YYYYMMDD')::integer,
       l.login_time,
       l.username,
       c.company_key,
       d.device_key,
       l.country_code
FROM log_lines l
JOIN dw.dim_device d  ON d.device_name = l.device
JOIN dw.dim_company c ON c.company_id = l.company_id
                     AND l.login_time::date >= c.valid_from
                     AND l.login_time::date <  c.valid_to
WHERE l.previous_time IS NULL
   OR l.login_time - l.previous_time > INTERVAL '30 minutes';
