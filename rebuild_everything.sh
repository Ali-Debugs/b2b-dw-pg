#!/bin/bash
# Wipes everything and builds it again from zero: the sources, the DEV warehouse and the PROD warehouse.
#
# Run from the project folder:   ./rebuild_everything.sh
#
# Docker must be running. The Metabase dashboard is kept; its charts show errors while the
# warehouse is empty and work again when the script is finished.

set -e                 # stop at the first command that fails
cd "$(dirname "$0")"   # always work from the project folder
unset B2B_ENV          # the DEV steps below must not inherit a B2B_ENV=prod from your terminal
PY=.venv/bin/python

echo "This deletes ALL data: the source database, the web log, the DEV warehouse and the PROD warehouse."
read -p "Type yes to continue: " answer
if [ "$answer" != "yes" ]; then
  echo "Cancelled. Nothing was changed."
  exit 1
fi

echo
echo "== 1. Wipe everything =="
$PY -m seed.reset
B2B_ENV=prod $PY -m seed.reset

echo
echo "== 2. Generate the source data and the web log =="
$PY -m seed.seed_postgres
$PY -m seed.seed_weblogs

echo
echo "== 3. Load the DEV warehouse and test it =="
$PY run.py
$PY -m pytest -q

echo
echo "== 4. Load the PROD warehouse and test it =="
B2B_ENV=prod $PY run.py
B2B_ENV=prod $PY -m pytest -q

echo
echo "Done. Everything was rebuilt from zero. Refresh the Metabase dashboard."
