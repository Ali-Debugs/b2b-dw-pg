-- MIGRATION 002 (incremental load): the run log now also says which kind of load a run was,
-- 'full' or 'incremental'. Runs from before this change keep an empty value.

ALTER TABLE etl.run_log ADD COLUMN IF NOT EXISTS load_type text;
