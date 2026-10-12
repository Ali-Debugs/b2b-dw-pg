-- RAW: an exact copy of b2b.products from the source database (all text).
CREATE TABLE IF NOT EXISTS raw.raw_products (
  product_id    text,
  supplier_id   text,
  name          text,
  default_price text
);
TRUNCATE raw.raw_products;
