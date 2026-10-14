-- Runs at the start of every pipeline run. Safe to run again: it only creates what is missing.

-- One schema per layer of the warehouse.
CREATE SCHEMA IF NOT EXISTS raw;      -- exact copies of the sources, everything as text
CREATE SCHEMA IF NOT EXISTS staging;  -- cleaned and checked rows
CREATE SCHEMA IF NOT EXISTS dw;       -- the star schema: dimensions and facts
CREATE SCHEMA IF NOT EXISTS mart;     -- report-ready views
CREATE SCHEMA IF NOT EXISTS etl;      -- what the pipeline writes about itself

-- One row per pipeline run: when it started, when it ended, how it ended.
CREATE TABLE IF NOT EXISTS etl.run_log (
  run_id      serial PRIMARY KEY,
  started_at  timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  status      text NOT NULL                 -- running / success / failed / abandoned
);

-- One row per step per attempt. A restart reads this to know which steps are already done.
CREATE TABLE IF NOT EXISTS etl.step_log (
  step_log_id   serial PRIMARY KEY,
  run_id        integer NOT NULL REFERENCES etl.run_log,
  step_name     text NOT NULL,
  started_at    timestamptz NOT NULL DEFAULT now(),
  finished_at   timestamptz,
  status        text NOT NULL,              -- running / success / failed
  row_count     bigint,                     -- rows in the table the step built (for a quality step: the number of checks)
  error_message text
);

-- Which files of sql/migrations/ were already applied to this warehouse (each one runs only once).
CREATE TABLE IF NOT EXISTS etl.migrations (
  file_name  text PRIMARY KEY,
  applied_at timestamptz NOT NULL DEFAULT now()
);

-- Every row the pipeline refused, with the reason, so nothing disappears silently.
CREATE TABLE IF NOT EXISTS etl.rejected_rows (
  step_name   text NOT NULL,
  reason      text NOT NULL,
  row_data    text,
  rejected_at timestamptz NOT NULL DEFAULT now()
);

-- --- Incremental load ---
-- How far each growing table has been loaded: the highest order id, or the latest log time.
-- An incremental run reads this, fetches only what is newer, and moves it forward.
CREATE TABLE IF NOT EXISTS etl.watermark (
  table_name text PRIMARY KEY,
  value      text NOT NULL,
  updated_at timestamptz NOT NULL DEFAULT now()
);
