-- RAW: the lookup file sources/csv/ip_country.csv.
-- It says which country an IP address belongs to, using the first number of the address.
CREATE TABLE IF NOT EXISTS raw.raw_ip_country (
  ip_prefix    text,
  country_code text,
  country_name text
);
TRUNCATE raw.raw_ip_country;
