#!/bin/bash
set -euo pipefail

if [[ -z "${DB_USER:-}" || -z "${DB_PASSWORD:-}" ]]; then
  echo "DB_USER and DB_PASSWORD must be set for API database bootstrap"
  exit 1
fi

psql -v ON_ERROR_STOP=1 \
  --username "${POSTGRES_USER:-postgres}" \
  --dbname "${POSTGRES_DB}" \
  <<-EOSQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;

GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${DB_USER};
EOSQL

psql -v ON_ERROR_STOP=1 \
  --username "${POSTGRES_USER:-postgres}" \
  --dbname "${POSTGRES_DB}" \
  <<-EOSQL
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO ${DB_USER};
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO ${DB_USER};
EOSQL
