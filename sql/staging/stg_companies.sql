-- STAGING companies: check each raw row, keep the good ones, send the bad ones to etl.rejected_rows.
-- Rule: a CUIT must be exactly 11 digits once the dashes are removed.

CREATE TABLE IF NOT EXISTS staging.stg_companies (
  company_id   integer PRIMARY KEY,
  cuit         text NOT NULL,
  name         text NOT NULL,
  country_code text NOT NULL
);
TRUNCATE staging.stg_companies;
DELETE FROM etl.rejected_rows WHERE step_name = 'stg_companies';

-- Give every row a reject_reason. NULL means the row is good.
CREATE TEMP TABLE checked ON COMMIT DROP AS
SELECT r.*,
       CASE WHEN r.cuit IS NULL OR replace(r.cuit, '-', '') !~ '^[0-9]{11}$' THEN 'CUIT is not 11 digits'
       END AS reject_reason
FROM raw.raw_companies r;

INSERT INTO etl.rejected_rows (step_name, reason, row_data)
SELECT 'stg_companies', reject_reason, to_json(c)::text
FROM checked c
WHERE reject_reason IS NOT NULL;

INSERT INTO staging.stg_companies
SELECT company_id::integer, replace(cuit, '-', ''), trim(name), upper(country_code)
FROM checked
WHERE reject_reason IS NULL;
