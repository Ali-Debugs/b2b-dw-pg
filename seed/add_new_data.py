"""--- Incremental load ---

Adds a little new data to the two sources, so an incremental run has something new to load.

Run from the project folder:   python -m seed.add_new_data
Then load only the new data:   python run.py --incremental

It adds 20 new orders (placed right now) to the B2B database and appends 30 new visits to the web log.
"""

import random
from datetime import timedelta

from seed.seed_weblogs import PAGES, USER_AGENTS
from sources.postgres.connection import LOG_FILE, connect_source, local_now

NEW_ORDERS = 20
NEW_VISITS = 30


def main():
    random.seed()  # different new data on every run
    with connect_source() as source:
        # --- new orders: a random company, its first end customer, 1 to 3 products from its price list
        customer_of_company = dict(
            source.execute(
                "SELECT company_id, min(end_customer_id) FROM b2b.end_customers"
                " WHERE document_number IS NOT NULL GROUP BY company_id"
            ).fetchall()
        )
        catalog_of_company = {}
        for company_id, product_id, price in source.execute(
            "SELECT company_id, product_id, price FROM b2b.catalog_items WHERE price > 0"
        ):
            catalog_of_company.setdefault(company_id, []).append((product_id, price))

        order_id = source.execute("SELECT max(order_id) FROM b2b.orders").fetchone()[0]
        for _ in range(NEW_ORDERS):
            order_id += 1
            company_id = random.choice(list(customer_of_company))
            # the order time is "now" in the business time zone
            source.execute(
                "INSERT INTO b2b.orders VALUES (%s, %s, %s, %s)",
                [order_id, company_id, customer_of_company[company_id], local_now().replace(tzinfo=None)],
            )
            chosen = random.sample(catalog_of_company[company_id], random.randint(1, 3))
            for line_number, (product_id, price) in enumerate(chosen, start=1):
                source.execute(
                    "INSERT INTO b2b.order_items VALUES (%s, %s, %s, %s, %s)",
                    [order_id, line_number, product_id, random.randint(1, 10), price],
                )
        print(f"Added {NEW_ORDERS} new orders to the source database")

        usernames = [row[0] for row in source.execute("SELECT username FROM b2b.users")]

    # --- new visits: appended to the end of the web log, like a web server does
    page_time = local_now()
    with open(LOG_FILE, "a") as log_file:
        for _ in range(NEW_VISITS):
            username = random.choice(usernames)
            ip = f"181.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            user_agent = random.choices(list(USER_AGENTS), list(USER_AGENTS.values()))[0]
            for _ in range(random.randint(1, 3)):
                page_time += timedelta(seconds=random.randint(1, 20))
                stamp = page_time.strftime("%d/%b/%Y:%H:%M:%S %z")
                page = random.choice(PAGES)
                log_file.write(f'{ip} - {username} [{stamp}] "GET {page} HTTP/1.1" 200 1000 "-" "{user_agent}"\n')
    print(f"Appended {NEW_VISITS} new visits to {LOG_FILE}")


if __name__ == "__main__":
    main()
