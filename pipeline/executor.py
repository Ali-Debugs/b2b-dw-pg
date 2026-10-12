"""Runs .sql files in the warehouse."""

from sources.postgres.connection import ROOT


def run_sql_file(warehouse, path):
    """Run every statement in one .sql file."""
    warehouse.execute((ROOT / path).read_text())


def run_migrations(warehouse):
    """Apply the files in sql/migrations/ that this warehouse has not had yet, in name order.

    A migration changes tables that already exist (for example drops one that got a new shape).
    Each file runs once per warehouse; etl.migrations remembers which ones are done. That is how a
    change to a table reaches prod automatically when the new code is deployed.
    """
    done = {row[0] for row in warehouse.execute("SELECT file_name FROM etl.migrations")}
    for path in sorted((ROOT / "sql/migrations").glob("*.sql")):
        if path.name in done:
            continue
        warehouse.execute(path.read_text())
        warehouse.execute("INSERT INTO etl.migrations (file_name) VALUES (%s)", [path.name])
        # tables changed, so a half-finished run cannot be continued: the next run starts from step 1
        warehouse.execute("UPDATE etl.run_log SET status = 'abandoned' WHERE status <> 'success'")
        warehouse.commit()
        print(f"Migration applied: {path.name}")


def query_sql_file(warehouse, path):
    """Run a .sql file that holds one SELECT and return its rows."""
    return warehouse.execute((ROOT / path).read_text()).fetchall()
