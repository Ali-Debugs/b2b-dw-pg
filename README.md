# B2B data warehouse (simple learning project)

A small ELT pipeline that loads a data warehouse for a B2B e-commerce platform from two sources:

1. the **B2B platform database** (companies, suppliers, end customers, products, catalogs, orders)
2. the **web server log** (Apache combined format)

Both the source and the warehouse are PostgreSQL databases in one Docker container. Python only moves
the data in; all cleaning and modelling is plain SQL, one small file per table.

## How to run it

You need Docker and Python 3.11 or newer.

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

docker compose up -d              # starts PostgreSQL (port 5432) and Metabase (port 3000)

python -m seed.seed_postgres      # 1. create and fill the B2B source database
python -m seed.seed_weblogs       # 2. write the web log file
python run.py                     # 3. load the DEV warehouse
python -m pytest -q               # 4. check the result
```

`python -m seed.reset` deletes the source, the warehouse and the log file so you can start again.

The made-up data is a small business so the numbers are easy to read: 30 companies, 60 products,
about 85 orders a month (roughly 30,000 in sales) and 3,000 website visits. The sizes are in
`config.yaml`; make them bigger to test volume.

## What is in each folder

| Path | What it holds |
|---|---|
| `config.yaml` | Connection settings and how much data to generate |
| `docker-compose.yml` | The PostgreSQL and Metabase containers |
| `run.py` | The main program: the ordered list of steps and the restart logic |
| `sources/postgres/` | `schema.sql` (the B2B tables), `connection.py`, `create_databases.sql` |
| `sources/csv/ip_country.csv` | Lookup: first number of an IP address -> country |
| `~/b2b_weblogs/access.log` | The generated web log. It is outside the project, like the log of a real web server |
| `.github/workflows/` | `ci.yml` (test on dev) and `deploy.yml` (load prod) |
| `seed/` | Scripts that generate the source data and the log; `change_company.py` makes one change to show the history; `add_new_data.py` adds new orders and visits for an incremental load |
| `sql/setup.sql` | Creates the schemas and the `etl` tables |
| `sql/migrations/` | One-time changes to tables that already exist; each file runs once per warehouse |
| `sql/raw/` | Empty copies of the source tables, every column as text |
| `sql/staging/` | Cleaning rules: good rows go on, bad rows go to `etl.rejected_rows` |
| `sql/dimensions/`, `sql/facts/` | The star schema (schema `dw`) |
| `sql/marts/` | Report-ready views (schema `mart`) |
| `dq/` | Data quality checks that must all return 0 |
| `pipeline/` | Small Python helpers: copy a table, parse the log, run a SQL file, write the run log, keep the watermarks |
| `tests/` | A few simple tests |

One rule makes the project easy to find your way in: **the file name is the step name and the table
name.** `sql/staging/stg_orders.sql` is step `stg_orders` and builds table `staging.stg_orders`.

## What happens in one run

```
source database ─┐
ip_country.csv  ─┼─> raw ──> staging ──> dw (dimensions + facts) ──> data quality checks ──> mart (views)
access.log      ─┘            │
                              └──> etl.rejected_rows (bad rows, with the reason)
```

| Layer | Schema | What it does |
|---|---|---|
| Raw | `raw` | Exact copy of each source, all columns text, so nothing can fail to land |
| Staging | `staging` | Gives every row a `reject_reason`; NULL means good. Good rows get real types |
| Dimensions | `dw` | `dim_date`, `dim_country`, `dim_company` (keeps history), `dim_product`, `dim_end_customer`, `dim_device` |
| Facts | `dw` | `fact_sales` (one row per order item), `fact_logins` (one row per login) |
| Marts | `mart` | Two wide views for the dashboard and three views that answer the three reports |

Every run reloads every table (`TRUNCATE` then `INSERT`), except `dim_company`, which keeps its old
versions. Running a step twice gives the same result either way.

## The three reports

| Report | View |
|---|---|
| Top 5 most-used devices among B2B clients | `mart.mart_top_devices` |
| Most popular products in the country with the most logins | `mart.mart_top_products_top_country` |
| Total sales by month for the last year (the last 12 complete months) | `mart.mart_monthly_sales` |

```bash
docker exec b2b-postgres psql -U b2b -d b2b_warehouse_dev -c "SELECT * FROM mart.mart_top_devices"
```

Assumptions behind report 2 (the brief leaves these open):

- The country is the one with the highest number of logins. A login's country comes from its IP address.
- A sale belongs to the country of the company that placed the order.
- "Popular" means the highest total quantity sold.
- The view shows the top 5 products, over all the data that is loaded.

The entity relationship diagrams of the source and the warehouse are in [docs/erd.md](docs/erd.md).

## How each requirement is met

| Requirement | Where to look |
|---|---|
| Project infrastructure | Docker Compose, dev and prod warehouses, CI and CD in `.github/workflows/` |
| Source database, populated | `sources/postgres/schema.sql`, `seed/seed_postgres.py` |
| Web log generator | `seed/seed_weblogs.py` |
| Target store | Databases `b2b_warehouse_dev` and `b2b_warehouse_prod`, star schema in `sql/dimensions/` and `sql/facts/` |
| Handles large data volumes | Data is moved with `COPY`, streamed in chunks (`pipeline/extractor.py`); the log is read one line at a time (`pipeline/log_parser.py`); all transformations are set-based SQL |
| Restartable after a failed job or sub-job | Each step is its own transaction and is recorded in `etl.step_log`. After a failure, `python run.py` continues the same run and skips the finished steps (`pipeline/logger.py`, `run.py`) |
| Initial load | `python run.py` on an empty warehouse creates everything |
| Handles erroneous data | Staging rules in `sql/staging/`; refused rows are kept in `etl.rejected_rows` with a reason; `dq/` then checks that no row was lost, that no step rejected more than 20% of its rows, and that the star schema is consistent. The reports are only rebuilt when these checks pass |
| Tracks ETL metadata | `etl.run_log` and `etl.step_log`: start, end, status, row count, error message |
| Report-friendly format | Star schema plus the `mart` views |

### Try the restart

```bash
python run.py --fail-at fact_sales   # stops at that step on purpose
python run.py                        # continues the same run, skipping what is done
```

Then look at `SELECT * FROM etl.step_log ORDER BY step_log_id`: `fact_sales` appears once as `failed`
and once as `success`, under the same `run_id`.

### The bad data

The seed scripts put wrong rows in on purpose. After a run, `run.py` prints what was refused and why:

| Bad data | Rule that catches it |
|---|---|
| CUIT that is not 11 digits | `stg_companies.sql` |
| End customer with no document number | `stg_end_customers.sql` |
| Product with a missing or negative price | `stg_products.sql` |
| Catalog price of zero | `stg_catalog_items.sql` |
| Order with a missing or future date | `stg_orders.sql` |
| Order item with zero quantity or no price | `stg_order_items.sql` |
| Log line that is cut off | `pipeline/log_parser.py` |
| Log line with a username that does not exist | `stg_web_logs.sql` |

A row is also refused when the row it depends on was refused (for example the orders of a company with
a broken CUIT). In every staging step: raw rows = good rows + rejected rows.

## Company history (slowly changing dimension, type 2)

`dw.dim_company` remembers how a company looked in the past. When its name, country, CUIT or supplier
status changes in the source, the load does two things (`sql/dimensions/dim_company.sql`):

1. it closes the current row (`valid_to` = today, `is_current` = false)
2. it adds a new row with the new values (`valid_from` = today, `is_current` = true)

So one company can have several rows. Each row has its own `company_key`, a key made by the warehouse
(a surrogate key), because `company_id` repeats on every version. The fact tables store `company_key`,
picked by date: a sale points to the version that was valid on the day of the order. An old sale keeps
the name and country the company had then.

Try it:

```bash
python -m seed.change_company     # renames company 10 and adds three orders dated now
python run.py
docker exec b2b-postgres psql -U b2b -d b2b_warehouse_dev -c \
  "SELECT company_key, company_name, valid_from, valid_to, is_current FROM dw.dim_company WHERE company_id = 10"
```

The change is only noticed when the warehouse is loaded, so `valid_from` is the load date, not the
moment the source was edited. Only companies keep history; the other dimensions are overwritten.

**Migrations.** A table that already exists is not changed by `CREATE TABLE IF NOT EXISTS`. When a
table needs a new shape, a file in `sql/migrations/` does it. `run.py` applies each file once per
warehouse and records it in `etl.migrations`, so the change reaches prod by itself on the next deploy.

## Incremental load

`python run.py` is the full load: it re-reads everything from the sources. `python run.py --incremental`
fetches only what is new. It was added after the rest, so its code sits in clearly marked
`--- Incremental load ---` blocks at the bottom of the files.

Three raw tables keep growing: `raw_orders`, `raw_order_items` and `raw_web_logs`. For each one the
table `etl.watermark` remembers how far it is loaded (the highest order id, or the latest log time).
An incremental run:

1. does **not** empty these three tables
2. reads the watermark and copies only the newer source rows (`copy_new_rows` in
   `pipeline/extractor.py`, `load_new_log_lines` in `pipeline/log_parser.py`)
3. saves the new watermark in the same transaction, so a failed step changes nothing and can be retried

The small tables (companies, products, customers) are still copied in full, and everything after raw
is rebuilt as usual. `etl.run_log.load_type` shows whether a run was `full` or `incremental`.

Try it:

```bash
python run.py                   # full load; writes the watermarks
python -m seed.add_new_data     # 20 new orders and 30 new website visits
python run.py --incremental     # prints how many new rows each table got
```

What it does not do:

- **A changed old order is not noticed.** The watermark only sees new order ids.
- **The log file is still read from the start;** only the new lines are loaded.
- **Staging and the facts are still rebuilt** from raw. The saving is in not re-reading the sources.
- **A deploy always runs a full load.** With no watermark yet, `--incremental` also falls back to full.

## Dev, prod and CI/CD

There are two warehouses in the same PostgreSQL server, and two git branches.

| | DEV | PROD |
|---|---|---|
| Purpose | Try and test changes | The live warehouse behind the Metabase dashboard |
| Database | `b2b_warehouse_dev` | `b2b_warehouse_prod` |
| Git branch | `dev` | `main` |
| Loaded by | you, with `python run.py` | GitHub, after a merge to `main` |

The environment variable `B2B_ENV` chooses the warehouse (`sources/postgres/connection.py`). Without it
you are always on dev, so you cannot load prod by accident. `B2B_ENV=prod python run.py` loads prod by
hand. Both warehouses read the same source database and web log.

**The workflow, step by step**

1. Work on the `dev` branch. Run `python run.py` and `python -m pytest -q` on your computer.
2. `git push`. **CI** (`.github/workflows/ci.yml`) starts on GitHub: a fresh machine with its own
   empty PostgreSQL creates the databases, generates the data, loads the dev warehouse and runs the
   tests. A green tick means the project builds from zero.
3. Open a pull request from `dev` to `main`. CI runs again and its result is shown on the pull request.
4. Merge the pull request. This is the release decision.
5. **CD** (`.github/workflows/deploy.yml`) starts: it loads the prod warehouse with the new code and
   runs the tests against prod. Metabase now shows the result.

**Why the deploy runs on your own computer.** The prod database is in Docker on your machine, and
GitHub's servers cannot reach it. So the deploy job runs on a *self-hosted runner*: a small GitHub
program on your computer that waits for jobs. Set it up once on GitHub under
Settings -> Actions -> Runners -> New self-hosted runner (choose macOS), and start it with `./run.sh`.
Docker and the runner must be running for a deploy to happen; otherwise the job waits.

## Dashboard (Metabase)

Metabase is a ready-made dashboard tool, so there is no dashboard code in this project. You build the
dashboard once by clicking. Menu names can differ a little between Metabase versions.

**1. Connect (once)**

1. Open http://localhost:3000 (the first start takes about a minute) and create your admin user.
2. Add the database: type **PostgreSQL**, host `postgres`, port `5432`, database name `b2b_warehouse_prod`
   (the dashboard shows the live data),
   username `b2b`, password `b2b_local`. The host is `postgres` (the container name), not `localhost`.

**2. Make the four charts** (New -> Question, pick the table, then Summarize)

| Chart | Table | Summarize | Group by | Finish |
|---|---|---|---|---|
| Top 5 devices | Mart Logins | Count | Device | Sort by count descending, row limit 5, bar chart |
| Logins by country | Mart Logins | Count | Country | Bar chart |
| Top 10 products | Mart Sales | Sum of Quantity | Product Name | Sort descending, row limit 10, bar chart |
| Sales by month | Mart Sales | Sum of Amount | Order Date: Month | Line or bar chart |

Also save three plain questions that just show the tables **Mart Top Devices**,
**Mart Top Products Top Country** and **Mart Monthly Sales**: these are the fixed answers to the three
reports and do not change with the filters.

**3. Make the dashboard and add the filters** (New -> Dashboard, add the saved questions, then Edit ->
Add a filter)

| Filter | Type | Connect it to |
|---|---|---|
| Date range | Date picker | `Login Date` on the login charts, `Order Date` on the sales charts |
| Country | Text or Category | `Country` on all four charts |
| Company | Text or Category | `Company Name` on all four charts |
| Device | Text or Category | `Device` on the login charts |
| Product | Text or Category | `Product Name` on the sales charts |
| Supplier | Text or Category | `Supplier Name` on the sales charts |

Every time you change a filter, Metabase runs a new query against the `mart` views.

## Kept simple on purpose

- **Incremental only up to raw.** An incremental run fetches only new source rows, but staging and the
  facts are still rebuilt from raw on every run.
- **Only companies keep history.** The other dimensions are overwritten and use the source ids as keys.
- **A "login" is one visit of a logged-in user.** The request line is out of scope in the brief, so a
  login page cannot be recognised. Instead, the log lines of one user are grouped: a line starts a new
  login when the user's line before it is more than 30 minutes older (`sql/facts/fact_logins.sql`).
- **IP -> country uses a small made-up lookup file** on the first number of the address. A real project
  would use a GeoIP database.
- **Device comes from a few `LIKE` rules** on the user agent text (`stg_web_logs.sql`).
- **`suppliers` and `catalog_items` are loaded** into `raw` and `staging` (suppliers also show up as
  `dim_company.is_supplier` and `dim_product.supplier_name`). The three reports do not need them, so
  `catalog_items` has no fact table.
- **Two fact tables.** `fact_sales` has one row per order item, the finest level in the source.
  `fact_logins` has one row per login (visit); the single log lines stay in `staging.stg_web_logs`.
- **Passwords are in `config.yaml`.** They are local defaults for the Docker container only.
