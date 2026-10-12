-- DIMENSION company: one row per company. is_supplier says whether the company also sells products.

CREATE TABLE IF NOT EXISTS dw.dim_company (
  company_id   integer PRIMARY KEY,
  cuit         text NOT NULL,
  company_name text NOT NULL,
  country_code text NOT NULL,
  is_supplier  boolean NOT NULL
);
TRUNCATE dw.dim_company;

INSERT INTO dw.dim_company
SELECT c.company_id, c.cuit, c.name, c.country_code, s.company_id IS NOT NULL
FROM staging.stg_companies c
LEFT JOIN staging.stg_suppliers s ON s.company_id = c.company_id;
