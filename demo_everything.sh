#!/bin/bash
# The whole demo, one script after the other. Press Enter between them to talk and show Metabase.
set -e
cd "$(dirname "$0")"

for script in rebuild_everything.sh demo_show_database.sh demo_change_company.sh demo_incremental_load.sh demo_failure_and_restart.sh; do
  echo "=== $script"
  ./$script
  read -p "Press Enter for the next one: " pause
done
