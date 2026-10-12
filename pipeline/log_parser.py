"""Reads the web server log and loads it into raw.raw_web_logs.

Only four things are kept from each line: client IP, username, timestamp and user agent.
"""

import re
from datetime import datetime

from pipeline import watermark
from sources.postgres.connection import LOG_FILE

# Apache combined format:  IP ident USER [TIME] "REQUEST" STATUS BYTES "REFERER" "USER-AGENT"
# The four (...) groups are the parts we keep.
LINE_PATTERN = re.compile(r'^(\S+) \S+ (\S+) \[([^\]]+)\] "[^"]*" \d{3} \S+ "[^"]*" "([^"]*)"$')


def parse_line(line):
    """Return (ip, username, log_time, user_agent), or None when the line is broken."""
    match = LINE_PATTERN.match(line.strip())
    if match is None:
        return None
    ip, username, stamp, user_agent = match.groups()
    try:
        log_time = datetime.strptime(stamp, "%d/%b/%Y:%H:%M:%S %z")  # e.g. 10/Oct/2025:13:55:36 -0300
    except ValueError:
        return None
    return ip, username, log_time.isoformat(), user_agent


def load_log_file(warehouse, step_name):
    """Read the log one line at a time (so a huge file is fine) and COPY the good lines in.

    Broken lines are not thrown away: they go to etl.rejected_rows.
    """
    cur = warehouse.cursor()
    cur.execute("DELETE FROM etl.rejected_rows WHERE step_name = %s", [step_name])

    broken_lines = []
    with open(LOG_FILE, errors="replace") as log_file:
        with cur.copy(f"COPY raw.{step_name} FROM STDIN") as copy_in:
            for line in log_file:
                parsed = parse_line(line)
                if parsed:
                    copy_in.write_row(parsed)
                else:
                    broken_lines.append((step_name, "line is not in Apache combined format", line.strip()))

    cur.executemany("INSERT INTO etl.rejected_rows (step_name, reason, row_data) VALUES (%s, %s, %s)", broken_lines)


# --- Incremental load ---


def load_new_log_lines(warehouse, step_name):
    """Add only the log lines that are newer than the watermark (the latest log time already loaded).

    The raw table is not emptied. The file is still read from the start, but lines that are already
    loaded are skipped. A broken line has no time to compare, so all broken lines are written to
    etl.rejected_rows again, replacing the earlier copy.
    """
    last_time = datetime.fromisoformat(watermark.read(warehouse, step_name))
    cur = warehouse.cursor()
    cur.execute("DELETE FROM etl.rejected_rows WHERE step_name = %s", [step_name])

    broken_lines = []
    new_lines = 0
    with open(LOG_FILE, errors="replace") as log_file:
        with cur.copy(f"COPY raw.{step_name} FROM STDIN") as copy_in:
            for line in log_file:
                parsed = parse_line(line)
                if parsed is None:
                    broken_lines.append((step_name, "line is not in Apache combined format", line.strip()))
                elif datetime.fromisoformat(parsed[2]) > last_time:
                    copy_in.write_row(parsed)
                    new_lines += 1

    cur.executemany("INSERT INTO etl.rejected_rows (step_name, reason, row_data) VALUES (%s, %s, %s)", broken_lines)
    print(f"    {step_name}: {new_lines} new rows (after {last_time})")
