"""Prints the result of one SELECT on the warehouse (DEV or PROD, chosen by B2B_ENV). Used by the demo scripts.

    python -m demo.show "SELECT * FROM mart.mart_top_devices"
"""

import sys

from sources.postgres.connection import connect_warehouse

with connect_warehouse() as warehouse:
    cursor = warehouse.execute(sys.argv[1])
    rows = cursor.fetchall()
    names = [column.name for column in cursor.description]

# every column as wide as its longest value
widths = [max(len(str(value)) for value in [name] + [row[i] for row in rows]) for i, name in enumerate(names)]
print(" | ".join(name.ljust(width) for name, width in zip(names, widths)))
print("-+-".join("-" * width for width in widths))
for row in rows:
    print(" | ".join(str(value).ljust(width) for value, width in zip(row, widths)))
print(f"({len(rows)} rows)\n")
