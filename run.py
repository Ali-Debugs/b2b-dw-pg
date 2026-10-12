"""The main program: loads the warehouse, one step after the other.

    python run.py                         run the pipeline (or continue the run that failed)
    B2B_ENV=prod python run.py            the same, but load the PROD warehouse instead of DEV
    python run.py --fail-at fact_sales    stop on purpose at that step, to show the restart
    python run.py --incremental           fetch only the new orders and log lines (see the bottom block)

Each step is one .sql file. The step name is the file name without ".sql", and it is also the
name of the table (or view) the file builds.
"""

import argparse
import sys
import time
from pathlib import Path

from pipeline import executor, extractor, log_parser, logger, watermark
from sources.postgres.connection import ENV, connect_warehouse

# The steps, in the order they run: (the SQL file, extra Python work to do after it).
STEPS = [
    # 1. RAW: create the empty table, then copy the source data into it unchanged
    ("sql/raw/raw_companies.sql", extractor.copy_table),
    ("sql/raw/raw_suppliers.sql", extractor.copy_table),
    ("sql/raw/raw_end_customers.sql", extractor.copy_table),
    ("sql/raw/raw_products.sql", extractor.copy_table),
    ("sql/raw/raw_catalog_items.sql", extractor.copy_table),
    ("sql/raw/raw_orders.sql", extractor.copy_table),
    ("sql/raw/raw_order_items.sql", extractor.copy_table),
    ("sql/raw/raw_users.sql", extractor.copy_table),
    ("sql/raw/raw_ip_country.sql", extractor.copy_csv),
    ("sql/raw/raw_web_logs.sql", log_parser.load_log_file),
    # 2. STAGING: clean the data and reject bad rows (a table comes after the tables it checks against)
    ("sql/staging/stg_companies.sql", None),
    ("sql/staging/stg_suppliers.sql", None),
    ("sql/staging/stg_end_customers.sql", None),
    ("sql/staging/stg_products.sql", None),
    ("sql/staging/stg_catalog_items.sql", None),
    ("sql/staging/stg_orders.sql", None),
    ("sql/staging/stg_order_items.sql", None),
    ("sql/staging/stg_web_logs.sql", None),
    # 3. DIMENSIONS: the "who / what / when / where" tables
    ("sql/dimensions/dim_date.sql", None),
    ("sql/dimensions/dim_country.sql", None),
    ("sql/dimensions/dim_company.sql", None),
    ("sql/dimensions/dim_product.sql", None),
    ("sql/dimensions/dim_end_customer.sql", None),
    ("sql/dimensions/dim_device.sql", None),
    # 4. FACTS: the "what happened" tables
    ("sql/facts/fact_sales.sql", None),
    ("sql/facts/fact_logins.sql", None),
    # 5. DATA QUALITY: each file returns (check name, number of bad rows); every number must be 0.
    #    It runs before the marts, so the reports are only rebuilt when the data passed the checks.
    ("dq/no_row_lost.sql", None),
    ("dq/reject_rate.sql", None),
    ("dq/duplicates.sql", None),
    ("dq/null_checks.sql", None),
    ("dq/referential_integrity.sql", None),
    # 6. MARTS: report-ready views
    ("sql/marts/mart_sales.sql", None),
    ("sql/marts/mart_logins.sql", None),
    ("sql/marts/mart_top_devices.sql", None),
    ("sql/marts/mart_top_products_top_country.sql", None),
    ("sql/marts/mart_monthly_sales.sql", None),
]

# Which warehouse schema the files of each folder build their table in.
SCHEMA_OF_FOLDER = {"raw": "raw", "staging": "staging", "dimensions": "dw", "facts": "dw", "marts": "mart"}

# --- Incremental load ---
# The three raw tables that keep growing. A full run empties and reloads them like every other table.
# An incremental run (python run.py --incremental) keeps their rows and only adds the new ones, using
# the function named here. Everything after raw (staging, dimensions, facts) is rebuilt as usual.
INCREMENTAL_WORK = {
    "raw_orders": extractor.copy_new_rows,
    "raw_order_items": extractor.copy_new_rows,
    "raw_web_logs": log_parser.load_new_log_lines,
}


def run_step(warehouse, sql_file, extra_work, incremental=False):
    """Do the work of one step. Returns the number of rows in the table it built (None for a check)."""
    step_name = Path(sql_file).stem
    folder = Path(sql_file).parent.name

    if folder == "dq":
        failed = [name for name, bad_rows in executor.query_sql_file(warehouse, sql_file) if bad_rows > 0]
        if failed:
            raise RuntimeError("data quality checks failed: " + "; ".join(failed))
        return None

    if incremental and step_name in INCREMENTAL_WORK:
        INCREMENTAL_WORK[step_name](warehouse, step_name)  # --- Incremental load: add only the new rows
    else:
        executor.run_sql_file(warehouse, sql_file)
        if extra_work:
            extra_work(warehouse, step_name)
    if step_name in INCREMENTAL_WORK:
        watermark.save(warehouse, step_name)  # --- Incremental load: remember how far this table is loaded
    table = f"{SCHEMA_OF_FOLDER[folder]}.{step_name}"
    return warehouse.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def main():
    parser = argparse.ArgumentParser(description="Load the B2B data warehouse")
    parser.add_argument("--fail-at", metavar="STEP", help="fail on purpose at this step (to demo the restart)")
    parser.add_argument("--incremental", action="store_true", help="fetch only new orders and log lines")
    args = parser.parse_args()

    warehouse = connect_warehouse()  # does the work: one transaction per step
    log = connect_warehouse()  # writes the run log: every line is saved at once
    log.autocommit = True

    executor.run_sql_file(log, "sql/setup.sql")
    executor.run_migrations(warehouse)
    run_id, steps_done = logger.start_run(log)
    print(f"Environment: {ENV}")
    print(f"Run {run_id}" + (f" (continuing, {len(steps_done)} steps already done)" if steps_done else ""))

    # --- Incremental load ---
    # An incremental run needs watermarks, and those are first written by a full run.
    incremental = args.incremental
    if incremental and not watermark.all_saved(log):
        print("No watermarks yet, so this run is a full load.")
        incremental = False
    load_type = "incremental" if incremental else "full"
    log.execute("UPDATE etl.run_log SET load_type = %s WHERE run_id = %s", [load_type, run_id])
    print(f"Load type: {load_type}")

    for sql_file, extra_work in STEPS:
        step_name = Path(sql_file).stem
        if step_name in steps_done:
            print(f"  {step_name:32} skipped (already done)")
            continue

        step_log_id = logger.start_step(log, run_id, step_name)
        started = time.time()
        try:
            if step_name == args.fail_at:
                raise RuntimeError("failed on purpose with --fail-at")
            row_count = run_step(warehouse, sql_file, extra_work, incremental)
            warehouse.commit()  # keep what the step did
        except Exception as error:
            warehouse.rollback()  # undo what the step did
            logger.end_step(log, step_log_id, "failed", error_message=str(error))
            logger.end_run(log, run_id, "failed")
            print(f"  {step_name:32} FAILED: {error}")
            print("Fix the problem and run again: finished steps are skipped.")
            sys.exit(1)

        logger.end_step(log, step_log_id, "success", row_count)
        rows = "" if row_count is None else f"{row_count:>9,} rows"
        print(f"  {step_name:32} ok {rows}  ({time.time() - started:.1f}s)")

    logger.end_run(log, run_id, "success")
    print(f"Run {run_id} finished.")

    print("Rejected rows (see etl.rejected_rows):")
    rejected = log.execute(
        "SELECT step_name, reason, count(*) FROM etl.rejected_rows GROUP BY step_name, reason ORDER BY step_name, reason"
    )
    for step_name, reason, count in rejected:
        print(f"  {step_name:20} {reason:40} {count:>7,}")


if __name__ == "__main__":
    main()
