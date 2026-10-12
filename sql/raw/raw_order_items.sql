-- RAW: an exact copy of b2b.order_items from the source database (all text).
CREATE TABLE IF NOT EXISTS raw.raw_order_items (
  order_id    text,
  line_number text,
  product_id  text,
  quantity    text,
  unit_price  text
);
TRUNCATE raw.raw_order_items;
