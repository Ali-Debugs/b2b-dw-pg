-- RAW: an exact copy of b2b.orders from the source database (all text).
CREATE TABLE IF NOT EXISTS raw.raw_orders (
  order_id        text,
  company_id      text,
  end_customer_id text,
  order_date      text
);
TRUNCATE raw.raw_orders;
