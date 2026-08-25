#!/usr/bin/env bash
set -Eeuo pipefail

# Resolve the custom secret files as root before handing off to the stock
# postgres entrypoint.
#
# The stock entrypoint only resolves POSTGRES_PASSWORD_FILE (via its
# `file_env` helper) before it drops privileges with `gosu postgres`. Our
# init-db.sh additionally needs the app/migration passwords, but it is sourced
# only after that switch — as uid 999 — where the compose `secrets:` bind
# mounts (host-owned, 0600) are unreadable. Carry those values through as
# exported environment variables instead, mirroring how POSTGRES_PASSWORD
# survives the `gosu postgres` re-exec.

if [[ -n "${APP_DB_PASSWORD_FILE:-}" ]]; then
    export APP_DB_PASSWORD="$(cat "${APP_DB_PASSWORD_FILE}")"
    unset APP_DB_PASSWORD_FILE
fi

if [[ -n "${MIGRATION_DB_PASSWORD_FILE:-}" ]]; then
    export MIGRATION_DB_PASSWORD="$(cat "${MIGRATION_DB_PASSWORD_FILE}")"
    unset MIGRATION_DB_PASSWORD_FILE
fi

exec /usr/local/bin/docker-entrypoint.sh "$@"
