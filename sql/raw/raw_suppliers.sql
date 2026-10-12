-- RAW: an exact copy of b2b.suppliers from the source database (all text).
CREATE TABLE IF NOT EXISTS raw.raw_suppliers (
  company_id     text,
  supplier_since text
);
TRUNCATE raw.raw_suppliers;
