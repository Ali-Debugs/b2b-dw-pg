"""Makes one change to a product and one to an end customer in the source, to show that the warehouse
keeps their history too (seed/change_company.py does the same for a company).

Run from the project folder:   python -m seed.change_product_and_customer
Then load the warehouse:       python run.py

Product 1 gets a default price 10% higher. End customer 1 gets " Jr." added to the name (or removed
again on the next run). After the load, dw.dim_product and dw.dim_end_customer hold two versions of them.
"""

from sources.postgres.connection import connect_source

PRODUCT_ID = 1
END_CUSTOMER_ID = 1


def main():
    with connect_source() as source:
        # 1. a new price for the product
        source.execute(
            "UPDATE b2b.products SET default_price = round(default_price * 1.10, 2) WHERE product_id = %s",
            [PRODUCT_ID],
        )
        price = source.execute("SELECT default_price FROM b2b.products WHERE product_id = %s", [PRODUCT_ID]).fetchone()[0]
        print(f"Product {PRODUCT_ID}: default price is now {price}")

        # 2. a new name for the end customer
        old_name = source.execute(
            "SELECT full_name FROM b2b.end_customers WHERE end_customer_id = %s", [END_CUSTOMER_ID]
        ).fetchone()[0]
        new_name = old_name.removesuffix(" Jr.") if old_name.endswith(" Jr.") else old_name + " Jr."
        source.execute(
            "UPDATE b2b.end_customers SET full_name = %s WHERE end_customer_id = %s", [new_name, END_CUSTOMER_ID]
        )
        print(f"End customer {END_CUSTOMER_ID} renamed: {old_name}  ->  {new_name}")


if __name__ == "__main__":
    main()
