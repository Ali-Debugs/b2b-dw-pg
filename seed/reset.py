"""Deletes everything so you can start from zero: the source tables, the warehouse and the log file.

Run from the project folder:   python -m seed.reset
"""

from sources.postgres.connection import CONFIG, ROOT, connect_source, connect_warehouse


def main():
    with connect_source() as source:
        source.execute("DROP SCHEMA IF EXISTS b2b CASCADE")

    with connect_warehouse() as warehouse:
        for schema in ["raw", "staging", "dw", "mart", "etl"]:
            warehouse.execute(f"DROP SCHEMA IF EXISTS {schema} CASCADE")

    (ROOT / CONFIG["log_file"]).unlink(missing_ok=True)
    print("Source, warehouse and log file removed.")


if __name__ == "__main__":
    main()
