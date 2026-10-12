-- STAGING web logs: one clean row per log line of a logged-in user (one page the user opened).
-- (fact_logins later groups the lines of one visit into one login.)
--   * lines with username '-' are visitors who are not logged in: they are simply left out
--   * a username that does not exist in the platform is bad data: the line is rejected
--   * device  = worked out from the user agent text
--   * country = looked up from the first number of the IP address ('XX' when it is not in the file)

CREATE TABLE IF NOT EXISTS staging.stg_web_logs (
  login_time   timestamptz NOT NULL,
  username     text NOT NULL,
  company_id   integer NOT NULL,
  ip           text NOT NULL,
  device       text NOT NULL,
  country_code text NOT NULL
);
TRUNCATE staging.stg_web_logs;
DELETE FROM etl.rejected_rows WHERE step_name = 'stg_web_logs';

CREATE TEMP TABLE checked ON COMMIT DROP AS
SELECT r.*,
       u.company_id,
       coalesce(i.country_code, 'XX') AS country_code,
       CASE WHEN r.user_agent LIKE '%iPhone%' THEN 'iPhone'
            WHEN r.user_agent LIKE '%iPad%' THEN 'iPad'
            WHEN r.user_agent LIKE '%Android%' AND r.user_agent LIKE '%Mobile%' THEN 'Android Phone'
            WHEN r.user_agent LIKE '%Android%' THEN 'Android Tablet'
            WHEN r.user_agent LIKE '%Windows%' THEN 'Windows PC'
            WHEN r.user_agent LIKE '%Macintosh%' THEN 'Mac'
            WHEN r.user_agent LIKE '%Linux%' THEN 'Linux PC'
            ELSE 'Other'
       END AS device,
       CASE WHEN u.username IS NULL THEN 'username does not exist'
            WHEN c.company_id IS NULL THEN 'company was rejected'
       END AS reject_reason
FROM raw.raw_web_logs r
LEFT JOIN raw.raw_users u ON u.username = r.username
LEFT JOIN staging.stg_companies c ON c.company_id = u.company_id::integer
LEFT JOIN raw.raw_ip_country i ON i.ip_prefix = split_part(r.ip, '.', 1)
WHERE r.username <> '-';

INSERT INTO etl.rejected_rows (step_name, reason, row_data)
SELECT 'stg_web_logs', reject_reason, to_json(c)::text
FROM checked c
WHERE reject_reason IS NOT NULL;

INSERT INTO staging.stg_web_logs
SELECT log_time::timestamptz, username, company_id::integer, ip, device, country_code
FROM checked
WHERE reject_reason IS NULL;
