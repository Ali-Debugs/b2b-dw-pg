"""Copies source data into the RAW tables of the warehouse, unchanged."""

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
