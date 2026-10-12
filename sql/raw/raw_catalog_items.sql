-- RAW: an exact copy of b2b.catalog_items from the source database (all text).
CREATE TABLE IF NOT EXISTS raw.raw_catalog_items (
  company_id text,
  product_id text,
  price      text
);
TRUNCATE raw.raw_catalog_items;
