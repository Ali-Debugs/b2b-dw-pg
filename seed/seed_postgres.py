"""Creates the B2B source tables and fills them with made-up data for a small business.

Run from the project folder:   python -m seed.seed_postgres

Some rows are wrong on purpose (broken CUIT, missing document number, missing or negative price,
zero quantity, missing or future order date) so the pipeline has bad data to catch.
"""

import random
from datetime import date, timedelta

from sources.postgres.connection import CONFIG, ROOT, connect_source, local_now

SIZES = CONFIG["seed"]
random.seed(SIZES["random_seed"])  # same seed = same data every time

# How likely a company is to be in each country (Argentina is the biggest market).
COUNTRY_WEIGHTS = {"AR": 40, "BR": 20, "CL": 10, "MX": 8, "UY": 6, "CO": 5, "PE": 4, "US": 3, "PY": 2, "ES": 2}

COMPANY_WORDS = ["Andes", "Pampa", "Litoral", "Austral", "Norte", "Delta", "Cordillera", "Atlantico", "Sur", "Plata"]
COMPANY_TYPES = ["Trading", "Supplies", "Distribuidora", "Logistics", "Industrial", "Comercial"]
FIRST_NAMES = ["Juan", "Maria", "Carlos", "Lucia", "Pedro", "Sofia", "Diego", "Valentina", "Martin", "Camila"]
LAST_NAMES = ["Gomez", "Perez", "Rodriguez", "Fernandez", "Lopez", "Diaz", "Martinez", "Romero", "Silva", "Torres"]
PRODUCT_STYLES = ["Steel", "Heavy", "Light", "Pro", "Basic", "Industrial", "Compact", "Flexible"]
PRODUCT_KINDS = ["Bolt", "Glove", "Filter", "Cable", "Valve", "Pump", "Hose", "Tape", "Bearing", "Label"]


def unique_names(first_words, second_words, how_many):
    """Names made of two words, e.g. 'Steel Bolt', each used once. A number is added if the words run out."""
    names = [f"{first} {second}" for first in first_words for second in second_words]
    random.shuffle(names)
    return [names[i % len(names)] + ("" if i < len(names) else f" {i + 1}") for i in range(how_many)]


def insert_rows(cur, table, rows):
    """Bulk-load a list of rows into one source table. COPY is much faster than row-by-row INSERT."""
    with cur.copy(f"COPY b2b.{table} FROM STDIN") as copy:
        for row in rows:
            copy.write_row(row)
    print(f"  {table}: {len(rows)} rows")


def main():
    today = local_now().replace(tzinfo=None, microsecond=0)  # order dates are stored as local business time
    history_seconds = SIZES["months_of_history"] * 30 * 24 * 3600

    # --- companies: the last one gets a broken CUIT -----------------------------------------------
    companies = []
    company_names = unique_names(COMPANY_WORDS, COMPANY_TYPES, SIZES["companies"])
    for company_id in range(1, SIZES["companies"] + 1):
        cuit = f"30-{50000000 + company_id}-{random.randint(0, 9)}"
        if company_id == SIZES["companies"]:
            cuit = f"30-{company_id}-X"
        country = random.choices(list(COUNTRY_WEIGHTS), list(COUNTRY_WEIGHTS.values()))[0]
        companies.append((company_id, cuit, company_names[company_id - 1] + " S.A.", country))
    company_ids = [row[0] for row in companies]

    # --- suppliers: the first companies are also suppliers ----------------------------------------
    supplier_ids = company_ids[: SIZES["suppliers"]]
    suppliers = [(company_id, date(2015 + company_id % 8, 1, 1)) for company_id in supplier_ids]

    # --- end customers: shared out evenly over the companies; every 75th has no document number ---
    end_customers = []
    customers_of_company = {company_id: [] for company_id in company_ids}
    for customer_id in range(1, SIZES["end_customers"] + 1):
        company_id = company_ids[customer_id % len(company_ids)]
        document = None if customer_id % 75 == 0 else str(20000000 + customer_id)
        full_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        birth = date(1950, 1, 1) + timedelta(days=random.randint(0, 20000))
        end_customers.append((customer_id, company_id, document, full_name, birth))
        customers_of_company[company_id].append(customer_id)

    # --- products: prices from 2 to 50; every 40th has no price, another every 40th a negative one -
    products = []
    product_names = unique_names(PRODUCT_STYLES, PRODUCT_KINDS, SIZES["products"])
    for product_id in range(1, SIZES["products"] + 1):
        price = round(random.uniform(2, 50), 2)
        if product_id % 40 == 0:
            price = None
        if product_id % 40 == 20:
            price = -price
        products.append((product_id, random.choice(supplier_ids), product_names[product_id - 1], price))

    # --- catalog: each company picks 15 products and sets its own price (default price + a margin) -
    catalog_items = []
    catalog_of_company = {}
    for company_id in company_ids:
        catalog_of_company[company_id] = []
        for product in random.sample(products, 15):
            default_price = product[3] if product[3] and product[3] > 0 else 10
            price = round(default_price * random.uniform(1.05, 1.40), 2)
            if len(catalog_items) % 100 == 99:
                price = 0  # every 100th catalog price is zero
            catalog_items.append((company_id, product[0], price))
            catalog_of_company[company_id].append((product[0], price))

    # --- orders and their items -------------------------------------------------------------------
    orders = []
    order_items = []
    for order_id in range(1, SIZES["orders"] + 1):
        company_id = random.choice(company_ids)
        customer_id = random.choice(customers_of_company[company_id])
        order_date = today - timedelta(days=1, seconds=random.randint(0, history_seconds))
        if order_id % 100 == 0:
            order_date = None  # missing date
        if order_id % 100 == 50:
            order_date = today + timedelta(days=random.randint(30, 300))  # date in the future
        orders.append((order_id, company_id, customer_id, order_date))

        chosen = random.sample(catalog_of_company[company_id], random.randint(1, 4))
        for line_number, (product_id, price) in enumerate(chosen, start=1):
            quantity = random.randint(1, 10)
            if len(order_items) % 100 == 99:
                quantity = 0  # every 100th item has zero quantity
            if len(order_items) % 100 == 49:
                price = None  # and another every 100th has no price
            order_items.append((order_id, line_number, product_id, quantity, price))

    # --- users: two website logins per company ----------------------------------------------------
    users = []
    for company_id in company_ids:
        users.append((f"user{company_id * 2 - 1:03d}", company_id))
        users.append((f"user{company_id * 2:03d}", company_id))

    # --- write everything to the source database --------------------------------------------------
    with connect_source() as source:
        cur = source.cursor()
        cur.execute("DROP SCHEMA IF EXISTS b2b CASCADE")
        cur.execute((ROOT / "sources/postgres/schema.sql").read_text())
        print("Filling the source database:")
        insert_rows(cur, "companies", companies)
        insert_rows(cur, "suppliers", suppliers)
        insert_rows(cur, "end_customers", end_customers)
        insert_rows(cur, "products", products)
        insert_rows(cur, "catalog_items", catalog_items)
        insert_rows(cur, "orders", orders)
        insert_rows(cur, "order_items", order_items)
        insert_rows(cur, "users", users)


if __name__ == "__main__":
    main()
