"""A few simple checks. Run them after the pipeline has loaded the warehouse:

    python run.py
    python -m pytest -q
"""

from pipeline import executor
from pipeline.log_parser import parse_line
from sources.postgres.connection import connect_warehouse

GOOD_LINE = (
    '181.20.3.44 - user0007 [10/Oct/2025:13:55:36 -0300] "GET /catalog HTTP/1.1" 200 5123 "-" '
    '"Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X)"'
)


def query(sql):
    """Run one SELECT in the warehouse and return the rows."""
    with connect_warehouse() as warehouse:
        return warehouse.execute(sql).fetchall()


# --- the log parser (no database needed) ---------------------------------------------------------


def test_good_log_line_gives_the_four_fields():
    ip, username, log_time, user_agent = parse_line(GOOD_LINE)
    assert ip == "181.20.3.44"
    assert username == "user0007"
    assert log_time == "2025-10-10T13:55:36-03:00"
    assert "iPhone" in user_agent


def test_cut_off_log_line_is_refused():
    assert parse_line(GOOD_LINE[:40]) is None


def test_log_line_with_impossible_date_is_refused():
    assert parse_line(GOOD_LINE.replace("10/Oct/2025", "99/Oct/2025")) is None


# --- the loaded warehouse ------------------------------------------------------------------------


def test_last_run_finished_with_success():
    assert query("SELECT status FROM etl.run_log ORDER BY run_id DESC LIMIT 1") == [("success",)]


def test_report_1_has_five_devices_biggest_first():
    logins = [row[1] for row in query("SELECT device, logins FROM mart.mart_top_devices")]
    assert len(logins) == 5
    assert logins == sorted(logins, reverse=True)


def test_report_2_has_five_products_of_one_country_biggest_first():
    rows = query("SELECT country, total_quantity FROM mart.mart_top_products_top_country")
    assert len(rows) == 5
    assert len({row[0] for row in rows}) == 1
    quantities = [row[1] for row in rows]
    assert quantities == sorted(quantities, reverse=True)


def test_report_3_has_twelve_months():
    assert len(query("SELECT month FROM mart.mart_monthly_sales")) == 12


def test_no_row_is_lost_between_raw_and_staging():
    # every raw order is either accepted into staging or written to the rejected rows
    raw = query("SELECT count(*) FROM raw.raw_orders")[0][0]
    good = query("SELECT count(*) FROM staging.stg_orders")[0][0]
    rejected = query("SELECT count(*) FROM etl.rejected_rows WHERE step_name = 'stg_orders'")[0][0]
    assert raw == good + rejected
    assert rejected > 0


def test_a_visit_of_many_log_lines_counts_as_one_login():
    log_lines = query("SELECT count(*) FROM staging.stg_web_logs")[0][0]
    logins = query("SELECT count(*) FROM dw.fact_logins")[0][0]
    assert 0 < logins < log_lines
    # the same user never has two logins less than 30 minutes apart
    too_close = query("""
        SELECT count(*) FROM (
          SELECT login_time - lag(login_time) OVER (PARTITION BY username ORDER BY login_time) AS gap
          FROM dw.fact_logins) AS gaps
        WHERE gap <= INTERVAL '30 minutes'
    """)[0][0]
    assert too_close == 0


def test_every_data_quality_check_finds_zero_bad_rows():
    dq_files = [
        "dq/no_row_lost.sql",
        "dq/reject_rate.sql",
        "dq/duplicates.sql",
        "dq/null_checks.sql",
        "dq/referential_integrity.sql",
    ]
    with connect_warehouse() as warehouse:
        for sql_file in dq_files:
            for check_name, bad_rows in executor.query_sql_file(warehouse, sql_file):
                assert bad_rows == 0, check_name
