#!/bin/bash
set -euo pipefail

if [[ -z "${DB_USER:-}" || -z "${DB_PASSWORD:-}" ]]; then
    echo "DB_USER and DB_PASSWORD must be set for API database bootstrap"
    exit 1
fi

# Initially give only Connection and usage grants to the API user.
# The API user will be granted additional privileges by the "migrator" user.
psql -v ON_ERROR_STOP=1 \
    --username "${POSTGRES_USER:-postgres}" \
    --dbname "${POSTGRES_DB}" \
    <<-EOSQL
DO \$\$
BEGIN
  IF NOT EXISTS (
    SELECT
    FROM pg_catalog.pg_roles
    WHERE rolname = '${DB_USER}'
  ) THEN
    CREATE ROLE ${DB_USER}
      LOGIN
      PASSWORD '${DB_PASSWORD}';
  END IF;
END
\$\$;

GRANT CONNECT ON DATABASE ${POSTGRES_DB}
TO ${DB_USER};

GRANT USAGE ON SCHEMA public
TO ${DB_USER};
EOSQL
