#!/bin/sh
set -eu

query() {
    docker compose exec -T \
        -e PGPASSWORD="${LLM_DB_PASSWORD:-llm-readonly-local}" \
        postgres psql -X -qAt -v ON_ERROR_STOP=1 -U llm_reader -d medical -c "$1"
}

test "$(query "SELECT count(*) FROM hospital")" = 272
test "$(query "SELECT bool_and(
    patient_name LIKE 'NAME_%'
    AND mrn LIKE 'MRN_%'
    AND birth_date LIKE 'BIRTH_DATE_%'
    AND phone LIKE 'PHONE_%'
    AND accession_no LIKE 'ACCESSION_%'
) FROM hospital")" = t

! query "SELECT count(*) FROM public.hospital" >/dev/null 2>&1
! query "SELECT secret FROM private.masking_secret" >/dev/null 2>&1

printf 'LLM access is limited to the masked view.\n'
