# Shared by the demo scripts (they read it; you do not run it). Set ENVIRONMENT to dev or prod and all
# of them follow. The dashboard you show the demo on must read the same warehouse.
ENVIRONMENT=dev

export B2B_ENV=$ENVIRONMENT
PY=.venv/bin/python
[ -x "$PY" ] || PY=python   # GitHub's CI machine has no .venv

# Print the result of one query on the warehouse (connection settings come from config.yaml).
show() { "$PY" -m demo.show "$1"; }
