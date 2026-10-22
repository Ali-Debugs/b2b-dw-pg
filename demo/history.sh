#!/bin/bash
# A company, a product and an end customer change in the source: the warehouse keeps their old versions.
# Run it once per rebuild.
set -eo pipefail
cd "$(dirname "$0")/.."   # work from the project folder
source demo/settings.sh

versions() {
  show "SELECT company_name, valid_from, valid_to, is_current FROM dw.dim_company WHERE company_id = 10 ORDER BY company_key"
  show "SELECT product_name, default_price, valid_from, valid_to, is_current FROM dw.dim_product WHERE product_id = 1 ORDER BY product_key"
  show "SELECT full_name, valid_from, valid_to, is_current FROM dw.dim_end_customer WHERE end_customer_id = 1 ORDER BY end_customer_key"
}

echo "Before: company 10, product 1, end customer 1"
versions

$PY -m seed.change_company
$PY -m seed.change_product_and_customer
$PY run.py | grep -E "^Run|FAILED"

echo "After: each has an old and a new version"
versions

echo "Sales per version of company 10"
show "SELECT c.company_name, count(*) AS items, round(sum(f.amount), 2) AS amount
      FROM dw.fact_sales f JOIN dw.dim_company c USING (company_key)
      WHERE c.company_id = 10 GROUP BY c.company_key, c.company_name ORDER BY c.company_key"
