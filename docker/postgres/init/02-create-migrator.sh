#!/bin/bash
set -euo pipefail

if [[ -z "${MIGRATOR_DB_USER:-}" || -z "${MIGRATOR_DB_PASSWORD:-}" ]]; then
    echo "MIGRATOR_DB_USER and MIGRATOR_DB_PASSWORD must be set for migrator database bootstrap"
    exit 1
fi

if [[ -z "${DB_USER:-}" ]]; then
    echo "DB_USER must be set so migrator default privileges can be configured"
    exit 1
fi

psql -v ON_ERROR_STOP=1 \
    --username "${POSTGRES_USER:-postgres}" \
    --dbname "${POSTGRES_DB}" \
    <<-EOSQL
DO \$\$
BEGIN
  IF NOT EXISTS (
    SELECT
    FROM pg_catalog.pg_roles
    WHERE rolname = '${MIGRATOR_DB_USER}'
  ) THEN
    CREATE ROLE ${MIGRATOR_DB_USER}
      LOGIN
      PASSWORD '${MIGRATOR_DB_PASSWORD}';
  END IF;
END
\$\$;

GRANT CONNECT ON DATABASE ${POSTGRES_DB}
TO ${MIGRATOR_DB_USER};

GRANT USAGE, CREATE ON SCHEMA public
TO ${MIGRATOR_DB_USER};

ALTER DEFAULT PRIVILEGES
FOR ROLE ${MIGRATOR_DB_USER}
IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES
TO ${DB_USER};

ALTER DEFAULT PRIVILEGES
FOR ROLE ${MIGRATOR_DB_USER}
IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES
TO ${DB_USER};
EOSQL
