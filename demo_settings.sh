# Shared by the demo_*.sh scripts. Set ENVIRONMENT to prod or dev and all of them follow.
ENVIRONMENT=dev

export B2B_ENV=$ENVIRONMENT
PY=.venv/bin/python

# Run one query in the warehouse.
show() { docker exec b2b-postgres psql -U b2b -d "b2b_warehouse_$B2B_ENV" -c "$1"; }
