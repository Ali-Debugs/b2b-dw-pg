# Entity relationship diagrams

Two diagrams: the source database the data comes from, and the warehouse it is loaded into.

How to view them: GitHub draws them automatically. In VS Code, install the extension
"Markdown Preview Mermaid Support" and open the Markdown preview. Or paste a diagram into
https://mermaid.live to export it as PNG or SVG.

## Source: B2B platform (database `b2b_source`, schema `b2b`)

Defined in `sources/postgres/schema.sql`.

```mermaid
erDiagram
    companies     ||--o| suppliers : "is a"
    companies     ||--o{ end_customers : serves
    companies     ||--o{ catalog_items : "price list"
    companies     ||--o{ orders : places
    companies     ||--o{ users : "has logins"
    suppliers     ||--o{ products : publishes
    products      ||--o{ catalog_items : "listed in"
    products      ||--o{ order_items : "sold as"
    end_customers ||--o{ orders : receives
    orders        ||--o{ order_items : contains

    companies {
        int company_id PK
        text cuit UK
        text name
        text country_code
    }
    suppliers {
        int company_id PK
        date supplier_since
    }
    end_customers {
        int end_customer_id PK
        int company_id FK
        text document_number UK
        text full_name
        date date_of_birth
    }
    products {
        int product_id PK
        int supplier_id FK
        text name
        numeric default_price
    }
    catalog_items {
        int company_id PK
        int product_id PK
        numeric price
    }
    orders {
        int order_id PK
        int company_id FK
        int end_customer_id FK
        timestamp order_date
    }
    order_items {
        int order_id PK
        int line_number PK
        int product_id FK
        int quantity
        numeric unit_price
    }
    users {
        text username PK
        int company_id FK
    }
```

## Warehouse: star schema (databases `b2b_warehouse_dev` and `b2b_warehouse_prod`, schema `dw`)

Defined in `sql/dimensions/` and `sql/facts/`. Two fact tables in the middle, six dimensions around them.

```mermaid
erDiagram
    dim_date         ||--o{ fact_sales : date_key
    dim_company      ||--o{ fact_sales : company_id
    dim_end_customer ||--o{ fact_sales : end_customer_id
    dim_product      ||--o{ fact_sales : product_id
    dim_date         ||--o{ fact_logins : date_key
    dim_company      ||--o{ fact_logins : company_id
    dim_device       ||--o{ fact_logins : device_key
    dim_country      ||--o{ fact_logins : country_code
    dim_country      ||--o{ dim_company : country_code

    dim_date {
        int date_key PK
        date full_date
        int year
        int month
        text month_name
        date month_start
    }
    dim_country {
        text country_code PK
        text country_name
    }
    dim_company {
        int company_id PK
        text cuit
        text company_name
        text country_code FK
        boolean is_supplier
    }
    dim_product {
        int product_id PK
        text product_name
        numeric default_price
        int supplier_id
        text supplier_name
    }
    dim_end_customer {
        int end_customer_id PK
        text document_number
        text full_name
        date date_of_birth
        int company_id
    }
    dim_device {
        int device_key PK
        text device_name
    }
    fact_sales {
        int order_id PK
        int line_number PK
        int date_key FK
        int company_id FK
        int end_customer_id FK
        int product_id FK
        int quantity
        numeric unit_price
        numeric amount
    }
    fact_logins {
        int date_key FK
        timestamptz login_time
        text username
        int company_id FK
        int device_key FK
        text country_code FK
    }
```

The lines in the warehouse diagram are logical links. The `dw` tables have primary keys but no
foreign-key constraints; `dq/referential_integrity.sql` checks on every run that each fact row points to
a dimension row that exists.
