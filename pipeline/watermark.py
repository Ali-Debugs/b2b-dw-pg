"""--- Incremental load ---

A watermark remembers how far a growing table has been loaded, so the next incremental run only has
to fetch what is newer. It is kept in the table etl.watermark, one row per table:

    raw_orders, raw_order_items   the highest order id already loaded
    raw_web_logs                  the latest log time already loaded
"""

# For each growing raw table: how to work out "how far it is loaded" from the table itself.
WATERMARK_OF = {
    "raw_orders": "max(order_id::integer)",
    "raw_order_items": "max(order_id::integer)",
    "raw_web_logs": "max(log_time::timestamptz)",
}


def save(warehouse, table_name):
    """Look at what is in the raw table now and store the new watermark."""
    value = warehouse.execute(f"SELECT {WATERMARK_OF[table_name]} FROM raw.{table_name}").fetchone()[0]
    if value is None:  # the table is empty: nothing to remember
        return
    text = value.isoformat() if hasattr(value, "isoformat") else str(value)
    warehouse.execute(
        "INSERT INTO etl.watermark (table_name, value) VALUES (%s, %s)"
        " ON CONFLICT (table_name) DO UPDATE SET value = EXCLUDED.value, updated_at = now()",
        [table_name, text],
    )


def read(warehouse, table_name):
    """Return the stored watermark as text."""
    return warehouse.execute("SELECT value FROM etl.watermark WHERE table_name = %s", [table_name]).fetchone()[0]


def all_saved(warehouse):
    """True when every growing table has a watermark (that is, a full load has been done before)."""
    saved = warehouse.execute("SELECT count(*) FROM etl.watermark").fetchone()[0]
    return saved == len(WATERMARK_OF)
