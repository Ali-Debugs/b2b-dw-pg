"""Makes one change in the source database, to show how the warehouse keeps history.

Run from the project folder:   python -m seed.change_company
Then load the warehouse:       python run.py

What it does to company 10:
  1. renames it (adds the word "Group" to the name, or removes it again on the next run)
  2. adds three new orders for it, placed right now

After the load, dw.dim_company holds two versions of company 10. The old sales stay under the old
name, and the three new orders are under the new name.
"""

from sources.postgres.connection import connect_source

COMPANY_ID = 10


def main():
    with connect_source() as source:
        # 1. rename the company
        old_name = source.execute("SELECT name FROM b2b.companies WHERE company_id = %s", [COMPANY_ID]).fetchone()[0]
        if " Group S.A." in old_name:
            new_name = old_name.replace(" Group S.A.", " S.A.")
        else:
            new_name = old_name.replace(" S.A.", " Group S.A.")
        source.execute("UPDATE b2b.companies SET name = %s WHERE company_id = %s", [new_name, COMPANY_ID])
        print(f"Company {COMPANY_ID} renamed: {old_name}  ->  {new_name}")

        # 2. three new orders, one product each, from the company's own price list
        customer_id = source.execute(
            "SELECT min(end_customer_id) FROM b2b.end_customers WHERE company_id = %s AND document_number IS NOT NULL",
            [COMPANY_ID],
        ).fetchone()[0]
        products = source.execute(
            "SELECT c.product_id, c.price FROM b2b.catalog_items c JOIN b2b.products p USING (product_id)"
            " WHERE c.company_id = %s AND c.price > 0 AND p.default_price > 0 ORDER BY c.product_id LIMIT 3",
            [COMPANY_ID],
        ).fetchall()
        order_id = source.execute("SELECT max(order_id) FROM b2b.orders").fetchone()[0]
        for product_id, price in products:
            order_id += 1
            # the order time is "now" in Buenos Aires, the time zone the warehouse works in
            source.execute(
                "INSERT INTO b2b.orders VALUES (%s, %s, %s, now() AT TIME ZONE 'America/Argentina/Buenos_Aires')",
                [order_id, COMPANY_ID, customer_id],
            )
            source.execute("INSERT INTO b2b.order_items VALUES (%s, 1, %s, 5, %s)", [order_id, product_id, price])
        print(f"Added {len(products)} new orders for company {COMPANY_ID}")


if __name__ == "__main__":
    main()
