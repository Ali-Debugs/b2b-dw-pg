"""--- Incremental load ---

A watermark remembers how far a growing table has been loaded, so the next incremental run only has
to fetch what came after it. It is kept in the table etl.watermark, one row per table:

    raw_orders, raw_order_items   the last change id read from b2b.changes (CDC, see extractor.py)
    raw_web_logs                  the latest log time already loaded
"""

GROWING_TABLES = ["raw_orders", "raw_order_items", "raw_web_logs"]


def save(warehouse, table_name, value):
    """Store the new watermark of one table. It is saved in the same transaction as the rows it describes."""
    warehouse.execute(
        "INSERT INTO etl.watermark (table_name, value) VALUES (%s, %s)"
        " ON CONFLICT (table_name) DO UPDATE SET value = EXCLUDED.value, updated_at = now()",
        [table_name, str(value)],
    )


def read(warehouse, table_name):
    """Return the stored watermark as text."""
    return warehouse.execute("SELECT value FROM etl.watermark WHERE table_name = %s", [table_name]).fetchone()[0]


def all_saved(warehouse):
    """True when every growing table has a watermark (that is, a full load has been done before)."""
    saved = warehouse.execute("SELECT count(*) FROM etl.watermark").fetchone()[0]
    return saved == len(GROWING_TABLES)
