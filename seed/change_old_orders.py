"""--- Incremental load (CDC) ---

Edits and deletes some OLD orders in the source, so an incremental run has changes to catch that a
watermark on the order id would miss.

Run from the project folder:   python -m seed.change_old_orders
Then load only the changes:    python run.py --incremental

It adds 5 to the quantity of the first line of 3 old orders, and deletes 1 old order with its lines.
The trigger on the source tables writes each of these changes into b2b.changes.
"""

import random

from sources.postgres.connection import connect_source


def main():
    random.seed()  # different orders on every run
    with connect_source() as source:
        # old orders with a date in the past and a first line that has a good quantity and price
        old_orders = [
            row[0]
            for row in source.execute(
                "SELECT o.order_id FROM b2b.orders o"
                " JOIN b2b.order_items i ON i.order_id = o.order_id AND i.line_number = 1"
                " WHERE o.order_date < now() AND i.quantity > 0 AND i.unit_price > 0"
            )
        ]
        chosen = random.sample(old_orders, 4)

        for order_id in chosen[:3]:
            source.execute(
                "UPDATE b2b.order_items SET quantity = quantity + 5 WHERE order_id = %s AND line_number = 1", [order_id]
            )
            print(f"Order {order_id}: quantity of line 1 raised by 5")

        deleted = chosen[3]
        source.execute("DELETE FROM b2b.order_items WHERE order_id = %s", [deleted])  # the lines first (they point to the order)
        source.execute("DELETE FROM b2b.orders WHERE order_id = %s", [deleted])
        print(f"Order {deleted}: deleted, with its lines")


if __name__ == "__main__":
    main()
