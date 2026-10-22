"""Copies source data into the RAW tables of the warehouse, unchanged."""

from pipeline import watermark
from sources.postgres.connection import CONFIG, ROOT, connect_source


def copy_table(warehouse, step_name):
    """Copy one whole table from the source database, e.g. step raw_orders copies b2b.orders.

    COPY streams the rows in small chunks straight from one database to the other, so the table
    never has to fit in memory. That is what lets it handle large tables.
    """
    table = step_name.removeprefix("raw_")
    with connect_source() as source:
        with source.cursor().copy(f"COPY b2b.{table} TO STDOUT") as copy_out:
            with warehouse.cursor().copy(f"COPY raw.{step_name} FROM STDIN") as copy_in:
                for chunk in copy_out:
                    copy_in.write(chunk)


def copy_csv(warehouse, step_name):
    """Load the small IP-prefix -> country file."""
    copy_sql = f"COPY raw.{step_name} FROM STDIN WITH (FORMAT csv, HEADER true)"
    with open(ROOT / CONFIG["ip_country_file"]) as csv_file:
        with warehouse.cursor().copy(copy_sql) as copy_in:
            copy_in.write(csv_file.read())


# --- Incremental load (CDC) ---
# The source writes every change to an order or an order item into b2b.changes (a trigger does it, see
# sources/postgres/schema.sql). change_id goes up by one with every change, so "how far am I loaded" is
# simply the last change id the warehouse has applied: that is the watermark of these two tables.


def copy_table_and_save_change_id(warehouse, step_name):
    """Full load of orders or order items: copy the whole table, and remember the last change id.

    The change id is read BEFORE the copy. A change made during the copy is then applied again by the
    next incremental run, which is harmless: applying a change twice gives the same rows.
    """
    with connect_source() as source:
        last_change = source.execute("SELECT coalesce(max(change_id), 0) FROM b2b.changes").fetchone()[0]
    copy_table(warehouse, step_name)
    watermark.save(warehouse, step_name, last_change)


def apply_changes(warehouse, step_name):
    """Incremental load of orders or order items: apply only what changed since the last run.

    Every order with a change is deleted from raw and copied again from the source, as it is now.
    So a new order is added, an edited order gets its new values, and a deleted order stays gone.
    """
    table = step_name.removeprefix("raw_")
    last_change = int(watermark.read(warehouse, step_name))
    with connect_source() as source:
        newest_change = source.execute("SELECT coalesce(max(change_id), 0) FROM b2b.changes").fetchone()[0]
        changed_orders = [
            row[0]
            for row in source.execute(
                "SELECT DISTINCT order_id FROM b2b.changes WHERE table_name = %s AND change_id > %s AND change_id <= %s",
                [table, last_change, newest_change],
            )
        ]
        warehouse.execute(f"DELETE FROM raw.{step_name} WHERE order_id::integer = ANY(%s)", [changed_orders])
        with source.cursor().copy(f"COPY (SELECT * FROM b2b.{table} WHERE order_id = ANY(%s)) TO STDOUT", [changed_orders]) as copy_out:
            with warehouse.cursor().copy(f"COPY raw.{step_name} FROM STDIN") as copy_in:
                for chunk in copy_out:
                    copy_in.write(chunk)
    watermark.save(warehouse, step_name, newest_change)
    print(f"    {step_name}: {len(changed_orders)} changed orders applied (changes up to id {newest_change})")
