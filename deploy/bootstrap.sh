#!/bin/sh
# One-time deployment setup: check the host looks like a deployment, and seed
# the version pins.
#
# Idempotent — safe to re-run. Run from anywhere:
#     ./deploy/bootstrap.sh
#
# This does NOT record where the deployment lives. The deploy workflow gets
# that from the repository variable DEPLOY_DIR (.github/workflows/deploy.yml)
# and passes it to the script as COMPOSE_PROJECT_DIR; nothing reads it from
# .env. Set the variable to the directory this prints.
set -eu

# `pwd -P` resolves symlinks: the Docker daemon resolves bind-mount sources
# against the physical filesystem, so DEPLOY_DIR must be the physical path.
PROJECT_DIR=$(cd "$(dirname "$0")/.." && pwd -P)

# The same preflight the deploy script runs (infra/deploy/lib/common.sh,
# validate_startup), so a host that fails here fails now, not on first deploy.
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
# The deployment's real environment (CORS_ORIGIN, OSS_*, CADDY_PORT). Not
# created here: an empty one would make every recreate interpolate those to
# blank and look like an application bug.
[ -f "$PROJECT_DIR/.env" ] || {
    printf 'ERROR: no .env in %s — write the deployment environment first.\n' \
        "$PROJECT_DIR" >&2
    exit 1
}

# Seed the version pins. Never overwrite: after the first deployment this file
# is the deploy workflow's record of what is running.
if [ -f "$PROJECT_DIR/deploy/versions.env" ]; then
    printf 'deploy/versions.env already exists — left untouched.\n'
else
    cp "$PROJECT_DIR/deploy/versions.env.example" "$PROJECT_DIR/deploy/versions.env"
    printf 'Created deploy/versions.env from the template.\n'
fi

printf 'Bootstrap complete. Set the repository variable DEPLOY_DIR=%s\n' "$PROJECT_DIR"
