-- DIMENSION product: one row per product, with the name of its supplier already filled in.

CREATE TABLE IF NOT EXISTS dw.dim_product (
  product_id    integer PRIMARY KEY,
  product_name  text NOT NULL,
  default_price numeric(12,2) NOT NULL,
  supplier_id   integer NOT NULL,
  supplier_name text NOT NULL
);
TRUNCATE dw.dim_product;

INSERT INTO dw.dim_product
SELECT p.product_id, p.name, p.default_price, p.supplier_id, c.name
FROM staging.stg_products p
JOIN staging.stg_companies c ON c.company_id = p.supplier_id;
