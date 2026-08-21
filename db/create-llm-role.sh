#!/bin/sh
set -eu

: "${LLM_DB_PASSWORD:?LLM_DB_PASSWORD is required}"

psql --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
    --set=ON_ERROR_STOP=1 --set=llm_password="$LLM_DB_PASSWORD" <<'SQL'
CREATE ROLE llm_reader LOGIN PASSWORD :'llm_password';
REVOKE ALL ON SCHEMA public, private FROM llm_reader;
REVOKE ALL ON ALL TABLES IN SCHEMA public, private FROM llm_reader;
GRANT USAGE ON SCHEMA llm TO llm_reader;
GRANT EXECUTE ON FUNCTION private.mask_value(text, text) TO llm_reader;
GRANT EXECUTE ON FUNCTION private.mask_hospital_text(
    text, text, text, text, text, text, text, text
) TO llm_reader;
GRANT SELECT ON llm.hospital TO llm_reader;
ALTER ROLE llm_reader SET search_path = llm, pg_catalog;
ALTER ROLE llm_reader SET default_transaction_read_only = on;
ALTER ROLE llm_reader SET statement_timeout = '10s';
SQL
