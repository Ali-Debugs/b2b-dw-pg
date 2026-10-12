-- RAW: the web server log, one row per log line that could be read.
-- Only the four fields in scope are kept: client IP, username, timestamp, user agent.
CREATE TABLE IF NOT EXISTS raw.raw_web_logs (
  ip         text,
  username   text,
  log_time   text,
  user_agent text
);
TRUNCATE raw.raw_web_logs;
