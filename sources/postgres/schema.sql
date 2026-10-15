-- The B2B platform database (the OLTP source). Created by seed/seed_postgres.py.
-- Some columns are loose on purpose (prices and dates may be empty), like an old real system:
-- the warehouse has to check the data itself.
CREATE SCHEMA b2b;

-- A company is identified by its CUIT (tax number).
CREATE TABLE b2b.companies (
  company_id   integer PRIMARY KEY,
  cuit         text NOT NULL UNIQUE,
  name         text NOT NULL,
  country_code text NOT NULL
);

-- A supplier is a kind of company: same id, plus supplier-only facts.
CREATE TABLE b2b.suppliers (
  company_id     integer PRIMARY KEY REFERENCES b2b.companies,
  supplier_since date NOT NULL
);

-- The people who receive the goods. One company serves many end customers.
CREATE TABLE b2b.end_customers (
  end_customer_id integer PRIMARY KEY,
  company_id      integer NOT NULL REFERENCES b2b.companies,
  document_number text UNIQUE,
  full_name       text NOT NULL,
  date_of_birth   date
);

-- Each supplier publishes its products with a default price.
CREATE TABLE b2b.products (
  product_id    integer PRIMARY KEY,
  supplier_id   integer NOT NULL REFERENCES b2b.suppliers,
  name          text NOT NULL,
  default_price numeric(12,2)
);

-- A company's own price list: products picked from many suppliers, with the company's price.
CREATE TABLE b2b.catalog_items (
  company_id integer NOT NULL REFERENCES b2b.companies,
  product_id integer NOT NULL REFERENCES b2b.products,
  price      numeric(12,2),
  PRIMARY KEY (company_id, product_id)
);

-- An order is placed by a company and says which end customer receives the goods.
CREATE TABLE b2b.orders (
  order_id        integer PRIMARY KEY,
  company_id      integer NOT NULL REFERENCES b2b.companies,
  end_customer_id integer NOT NULL REFERENCES b2b.end_customers,
  order_date      timestamp
);

CREATE TABLE b2b.order_items (
  order_id    integer NOT NULL REFERENCES b2b.orders,
  line_number integer NOT NULL,
  product_id  integer NOT NULL REFERENCES b2b.products,
  quantity    integer,
  unit_price  numeric(12,2),
  PRIMARY KEY (order_id, line_number)
);

-- The logins of the website. The username is what shows up in the web server log.
CREATE TABLE b2b.users (
  username   text PRIMARY KEY,
  company_id integer NOT NULL REFERENCES b2b.companies
);

-- CDC (change data capture): every insert, update or delete of an order or an order item is written
-- into b2b.changes by a trigger. The warehouse remembers the last change_id it has applied, so its
-- incremental load also catches orders that were edited or deleted, not only new ones.
CREATE TABLE b2b.changes (
  change_id  bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,   -- goes up by one with every change
  table_name text NOT NULL,                                     -- 'orders' or 'order_items'
  operation  text NOT NULL,                                     -- 'INSERT', 'UPDATE' or 'DELETE'
  order_id   integer NOT NULL,                                  -- the order that changed
  changed_at timestamptz NOT NULL DEFAULT now()
);

-- Runs after every changed row. NEW is the row after the change; a DELETE has none, so OLD (the row
-- before) gives the order id.
CREATE FUNCTION b2b.record_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  INSERT INTO b2b.changes (table_name, operation, order_id)
  VALUES (TG_TABLE_NAME, TG_OP, coalesce(NEW.order_id, OLD.order_id));
  RETURN NULL;  -- an AFTER trigger does not change the row
END $$;

CREATE TRIGGER orders_changes AFTER INSERT OR UPDATE OR DELETE ON b2b.orders
  FOR EACH ROW EXECUTE FUNCTION b2b.record_change();
CREATE TRIGGER order_items_changes AFTER INSERT OR UPDATE OR DELETE ON b2b.order_items
  FOR EACH ROW EXECUTE FUNCTION b2b.record_change();
