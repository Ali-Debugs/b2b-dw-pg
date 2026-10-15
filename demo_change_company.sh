#!/bin/bash
# A company is renamed in the source: the warehouse keeps the old version. Run it once per rebuild.
set -eo pipefail
cd "$(dirname "$0")"
source ./demo_settings.sh

versions() {
  show "SELECT company_name, valid_from, valid_to, is_current FROM dw.dim_company WHERE company_id = 10 ORDER BY company_key"
}

echo "Company 10 before"
versions

$PY -m seed.change_company
$PY run.py | grep -E "^Run|FAILED"

echo "Company 10 after"
versions

echo "Sales per version"
show "SELECT c.company_name, count(*) AS items, round(sum(f.amount), 2) AS amount
      FROM dw.fact_sales f JOIN dw.dim_company c USING (company_key)
      WHERE c.company_id = 10 GROUP BY c.company_key, c.company_name ORDER BY c.company_key"
