-- REPORT 1: the top 5 most-used devices among B2B clients.

CREATE OR REPLACE VIEW mart.mart_top_devices AS
SELECT device, count(*) AS logins
FROM mart.mart_logins
GROUP BY device
ORDER BY logins DESC
LIMIT 5;
