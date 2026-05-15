#!/usr/bin/env bash
set -Eeuo pipefail

APP_DB_PASSWORD_VALUE="$(cat "$APP_DB_PASSWORD_FILE")"
MIGRATION_DB_PASSWORD_VALUE="$(cat "$MIGRATION_DB_PASSWORD_FILE")"

echo "[initdb] configuring roles, schemas, and privileges for database: ${POSTGRES_DB}"

psql \
  -X \
  -v ON_ERROR_STOP=1 \
  -v db_name="$POSTGRES_DB" \
  -v app_password="$APP_DB_PASSWORD_VALUE" \
  -v migration_password="$MIGRATION_DB_PASSWORD_VALUE" \
  --username "$POSTGRES_USER" \
  --dbname "$POSTGRES_DB" <<'SQL'
CREATE ROLE app_owner NOLOGIN;
CREATE ROLE migration_user LOGIN;
CREATE ROLE app_user LOGIN;


ALTER ROLE app_owner
  WITH NOLOGIN
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOREPLICATION;

ALTER ROLE migration_user
  WITH LOGIN
  PASSWORD :'migration_password'
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOREPLICATION;

ALTER ROLE app_user
  WITH LOGIN
  PASSWORD :'app_password'
  NOSUPERUSER
  NOCREATEDB
  NOCREATEROLE
  NOREPLICATION;


GRANT app_owner TO migration_user;

REVOKE ALL ON DATABASE :"db_name" FROM PUBLIC;

GRANT CONNECT ON DATABASE :"db_name" TO app_user;
GRANT CONNECT ON DATABASE :"db_name" TO migration_user;

GRANT CONNECT, CREATE ON DATABASE :"db_name" TO app_owner;


CREATE SCHEMA IF NOT EXISTS app AUTHORIZATION app_owner;
CREATE SCHEMA IF NOT EXISTS extensions AUTHORIZATION app_owner;

ALTER SCHEMA app OWNER TO app_owner;
ALTER SCHEMA extensions OWNER TO app_owner;


REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM app_user;
REVOKE ALL ON SCHEMA public FROM migration_user;


GRANT USAGE ON SCHEMA app TO app_user;
GRANT USAGE ON SCHEMA extensions TO app_user;

ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;

ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app
GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO app_user;

ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA app
GRANT EXECUTE ON FUNCTIONS TO app_user;

ALTER DEFAULT PRIVILEGES FOR ROLE app_owner IN SCHEMA extensions
GRANT EXECUTE ON FUNCTIONS TO app_user;

ALTER ROLE migration_user IN DATABASE :"db_name"
SET search_path = app, extensions, public;

ALTER ROLE app_user IN DATABASE :"db_name"
SET search_path = app, extensions, public;
SQL

echo "[initdb] roles, schemas, and privileges configured"
