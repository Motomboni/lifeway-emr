-- Local PostgreSQL bootstrap for Modern EMR (Windows / dev only).
--
-- Run once as the postgres superuser, for example:
--   "C:\Program Files\PostgreSQL\18\bin\psql.exe" -U postgres -h localhost -f postgres_local_setup.sql
--
-- To use a different password: edit the PASSWORD line below and the same value in backend/.env (DB_PASSWORD).

DROP DATABASE IF EXISTS modern_emr_local WITH (FORCE);
DROP ROLE IF EXISTS modern_emr_local;

CREATE ROLE modern_emr_local WITH LOGIN PASSWORD 'modern_emr_local_dev';
CREATE DATABASE modern_emr_local OWNER modern_emr_local ENCODING 'UTF8' TEMPLATE template0;

\c modern_emr_local
ALTER SCHEMA public OWNER TO modern_emr_local;
