-- RAW: an exact copy of b2b.users from the source database (all text).
CREATE TABLE IF NOT EXISTS raw.raw_users (
  username   text,
  company_id text
);
TRUNCATE raw.raw_users;
