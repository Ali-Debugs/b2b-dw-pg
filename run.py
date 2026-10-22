"""The main program: loads the warehouse, one step after the other.

    python run.py                         run the pipeline (or continue the run that failed)
    B2B_ENV=prod python run.py            the same, but load the PROD warehouse instead of DEV
    python run.py --fail-at fact_sales    stop on purpose at that step, to show the restart
    python run.py --fresh                 give up a failed run and start again from step 1
    python run.py --incremental           fetch only what changed in the orders and the new log lines

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
    ("sql/raw/raw_orders.sql", extractor.copy_table_and_save_change_id),
    ("sql/raw/raw_order_items.sql", extractor.copy_table_and_save_change_id),
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

# The name of each layer as it is printed on the screen.
HEADING_OF_FOLDER = {
    "raw": "RAW",
    "staging": "STAGING",
    "dimensions": "DIMENSIONS",
    "facts": "FACTS",
    "dq": "CHECKS",
    "marts": "MARTS",
}

# --- Incremental load ---
# The three raw tables that keep growing. A full run empties and reloads them like every other table.
# An incremental run (python run.py --incremental) keeps their rows and only applies what is new, using
# the function named here: the changed orders (CDC) and the new log lines. Each function also saves its
# watermark. Everything after raw (staging, dimensions, facts) is rebuilt as usual.
INCREMENTAL_WORK = {
    "raw_orders": extractor.apply_changes,
    "raw_order_items": extractor.apply_changes,
    "raw_web_logs": log_parser.load_new_log_lines,
}


def run_step(warehouse, sql_file, extra_work, incremental=False):
    """Do the work of one step. Returns the number of rows in the table it built (for a check: how many checks)."""
    step_name = Path(sql_file).stem
    folder = Path(sql_file).parent.name

    if folder == "dq":
        checks = executor.query_sql_file(warehouse, sql_file)
        failed = [name for name, bad_rows in checks if bad_rows > 0]
        if failed:
            raise RuntimeError("data quality checks failed: " + "; ".join(failed))
        return len(checks)  # for a quality step, the number of checks (it is saved as the row count)

    if incremental and step_name in INCREMENTAL_WORK:
        INCREMENTAL_WORK[step_name](warehouse, step_name)  # --- Incremental load: apply only what is new
    else:
        executor.run_sql_file(warehouse, sql_file)
        if extra_work:
            extra_work(warehouse, step_name)
    table = f"{SCHEMA_OF_FOLDER[folder]}.{step_name}"
    return warehouse.execute(f"SELECT count(*) FROM {table}").fetchone()[0]


def print_layer(folder, ran, skipped, seconds, checks):
    """Print one line for a layer of the pipeline, after its last step."""
    heading = f"  {HEADING_OF_FOLDER[folder]:<11}"
    if ran == 0:
        print(f"{heading}{skipped:>2} steps   skipped")
    elif folder == "dq":
        print(f"{heading}{checks:>2} passed")
    else:
        also = f"  ({skipped} skipped)" if skipped else ""
        print(f"{heading}{ran:>2} steps   {seconds:.1f}s{also}")


def main():
    parser = argparse.ArgumentParser(description="Load the B2B data warehouse")
    # --fail-at is only for showing the restart: without it, nothing in the run changes
    parser.add_argument("--fail-at", metavar="STEP", help="fail on purpose at this step (to demo the restart)")
    parser.add_argument("--incremental", action="store_true", help="fetch only new orders and log lines")
    parser.add_argument("--fresh", action="store_true", help="do not continue a failed run: start again from step 1")
    args = parser.parse_args()

    warehouse = connect_warehouse()  # does the work: one transaction per step
    log = connect_warehouse()  # writes the run log: every line is saved at once
    log.autocommit = True

    executor.run_sql_file(log, "sql/setup.sql")
    executor.run_migrations(warehouse)
    run_id, steps_done = logger.start_run(log, args.fresh)

    # --- Incremental load ---
    # An incremental run needs watermarks, and those are first written by a full run.
    incremental = args.incremental
    no_watermarks = incremental and not watermark.all_saved(log)
    if no_watermarks:
        incremental = False
    load_type = "incremental" if incremental else "full"
    log.execute("UPDATE etl.run_log SET load_type = %s WHERE run_id = %s", [load_type, run_id])

    continuing = f" (continuing, {len(steps_done)} steps already done; --fresh starts over)" if steps_done else ""
    print(f"Run {run_id} on {ENV}: {load_type} load{continuing}")
    if no_watermarks:
        print("  (no watermarks yet, so this run is a full load)")
    print()

    run_started = time.time()
    steps_run = steps_skipped = 0
    layer = None  # the layer (folder) being run, and what it has done so far
    ran = skipped = checks = 0
    seconds = 0.0

    for sql_file, extra_work in STEPS:
        step_name = Path(sql_file).stem
        folder = Path(sql_file).parent.name
        if folder != layer:  # a new layer starts: first print the line of the one before
            if layer:
                print_layer(layer, ran, skipped, seconds, checks)
            layer = folder
            ran = skipped = checks = 0
            seconds = 0.0

        if step_name in steps_done:
            skipped += 1
            steps_skipped += 1
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
            print(f"  {HEADING_OF_FOLDER[folder]:<11}FAILED at {step_name}: {error}")
            print("\nFix the problem and run again: finished steps are skipped.")
            sys.exit(1)

        logger.end_step(log, step_log_id, "success", row_count)
        ran += 1
        steps_run += 1
        seconds += time.time() - started
        if folder == "dq":
            checks += row_count
    print_layer(layer, ran, skipped, seconds, checks)  # the line of the last layer

    logger.end_run(log, run_id, "success")
    rejected = log.execute(
        "SELECT step_name, count(*) FROM etl.rejected_rows GROUP BY step_name ORDER BY 2 DESC, 1"
    ).fetchall()
    total_rejected = sum(count for _, count in rejected)
    skipped_note = f" ({steps_skipped} skipped)" if steps_skipped else ""
    print(
        f"\nRun {run_id} finished: {steps_run} steps{skipped_note} in {time.time() - run_started:.1f}s, "
        f"{total_rejected:,} rows rejected"
    )
    for step_name, count in rejected[:5]:  # the five steps that rejected the most
        print(f"  {step_name:20} {count:>7,}")
    if len(rejected) > 5:
        print(f"  {'other steps':20} {sum(count for _, count in rejected[5:]):>7,}")
    if rejected:
        print("Reasons: SELECT step_name, reason, count(*) FROM etl.rejected_rows GROUP BY 1, 2")


if __name__ == "__main__":
    main()
