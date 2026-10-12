-- DIMENSION device: one row per kind of device seen in the web logs (iPhone, Windows PC, ...).
-- The source has no id for a device, so device_key is simply a row number.

CREATE TABLE IF NOT EXISTS dw.dim_device (
  device_key  integer PRIMARY KEY,
  device_name text NOT NULL UNIQUE
);
TRUNCATE dw.dim_device;

INSERT INTO dw.dim_device
SELECT row_number() OVER (ORDER BY device), device
FROM (SELECT DISTINCT device FROM staging.stg_web_logs) AS devices;
