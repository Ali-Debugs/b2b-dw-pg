"""Reads the web server log and loads it into raw.raw_web_logs.

Only four things are kept from each line: client IP, username, timestamp and user agent.
"""

import re
from datetime import datetime

from sources.postgres.connection import CONFIG, ROOT

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
    with open(ROOT / CONFIG["log_file"], errors="replace") as log_file:
        with cur.copy(f"COPY raw.{step_name} FROM STDIN") as copy_in:
            for line in log_file:
                parsed = parse_line(line)
                if parsed:
                    copy_in.write_row(parsed)
                else:
                    broken_lines.append((step_name, "line is not in Apache combined format", line.strip()))

    cur.executemany("INSERT INTO etl.rejected_rows (step_name, reason, row_data) VALUES (%s, %s, %s)", broken_lines)
