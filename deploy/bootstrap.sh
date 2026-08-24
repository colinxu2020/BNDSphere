#!/bin/sh
# One-time deployment setup: resolve and persist this deployment's absolute
# path, and seed the version pins.
#
# Idempotent — safe to re-run. Run from anywhere:
#     ./deploy/bootstrap.sh
set -eu

# The script's own location IS the evidence of where the deployment lives, so
# no searching is needed or wanted. `pwd -P` resolves symlinks: the host Docker
# daemon resolves bind-mount sources against the physical filesystem, and a
# logical path containing a symlink would resolve differently there than here.
PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd -P)

# Fail closed rather than persisting a value that cannot work.
[ -f "$PROJECT_DIR/docker-compose.yml" ] || {
    printf 'ERROR: no docker-compose.yml in %s\n' "$PROJECT_DIR" >&2
    printf 'Run this script from inside the deployment checkout.\n' >&2
    exit 1
}
[ -d "$PROJECT_DIR/secrets" ] || {
    printf 'ERROR: no secrets/ in %s — create it before bootstrapping.\n' \
        "$PROJECT_DIR" >&2
    exit 1
}

ENV_FILE="$PROJECT_DIR/.env"
touch "$ENV_FILE"

# Upsert, never blind-append: re-running must not leave two conflicting
# COMPOSE_PROJECT_DIR lines, where Compose silently takes the last one.
if grep -q '^COMPOSE_PROJECT_DIR=' "$ENV_FILE"; then
    EXISTING=$(grep '^COMPOSE_PROJECT_DIR=' "$ENV_FILE" | tail -n 1 | cut -d= -f2-)
    if [ "$EXISTING" = "$PROJECT_DIR" ]; then
        printf 'COMPOSE_PROJECT_DIR already correct: %s\n' "$PROJECT_DIR"
    else
        printf 'Updating COMPOSE_PROJECT_DIR: %s -> %s\n' "$EXISTING" "$PROJECT_DIR"
        # grep -v exits 1 when every line matches (nothing left to print) —
        # that is a valid outcome here (.env held only this line), not a
        # failure, so don't let it trip `set -e`.
        grep -v '^COMPOSE_PROJECT_DIR=' "$ENV_FILE" > "$ENV_FILE.tmp" || true
        printf 'COMPOSE_PROJECT_DIR=%s\n' "$PROJECT_DIR" >> "$ENV_FILE.tmp"
        mv -f "$ENV_FILE.tmp" "$ENV_FILE"
    fi
else
    printf 'COMPOSE_PROJECT_DIR=%s\n' "$PROJECT_DIR" >> "$ENV_FILE"
    printf 'Set COMPOSE_PROJECT_DIR=%s\n' "$PROJECT_DIR"
fi

# Seed the version pins. Never overwrite: after the first deployment this file
# is the updater's, and clobbering it would discard the rollback target.
if [ -f "$PROJECT_DIR/deploy/versions.env" ]; then
    printf 'deploy/versions.env already exists — left untouched.\n'
else
    cp "$PROJECT_DIR/deploy/versions.env.example" "$PROJECT_DIR/deploy/versions.env"
    printf 'Created deploy/versions.env from the template.\n'
fi

printf 'Bootstrap complete.\n'
