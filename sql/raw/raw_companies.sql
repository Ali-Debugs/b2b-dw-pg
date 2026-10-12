-- RAW: an exact copy of b2b.companies from the source database.
-- Every column is text, so a bad value can never stop the copy. The checking happens in staging.
CREATE TABLE IF NOT EXISTS raw.raw_companies (
  company_id   text,
  cuit         text,
  name         text,
  country_code text
);
TRUNCATE raw.raw_companies;  -- empty it: every run reloads the whole table
