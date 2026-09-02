#!/bin/sh
# Migration, recreation, health verification and update.
#
# THE VERSION RECORD is deploy/versions.env, and it is the only one. It holds
# two kinds of key, written at two different times:
#
#   BACKEND_IMAGE / CADDY_IMAGE are INPUT to Compose. `up` reads them to know
#   what to start, so they are necessarily on disk before it runs.
#
#   APP_VERSION is input to nothing -- no compose file interpolates it, it is
#   purely the record of what is deployed. So it is advanced only after
#   wait_healthy has confirmed the containers ARE the new refs and are
#   healthy. `compose up` exiting 0 means "containers created", not "the new
#   version is serving", and a job cancelled between the two must not leave
#   the record naming a version that never came up.
#
# docker-compose.yml comes from the release too, installed from the release's
# own copy of it. A version therefore describes the whole deployment: a
# release that adds a service or an environment variable deploys without an
# operator having to edit the host first.
#
# NO ROLLBACK. A failed deploy leaves the failure in place and reports it;
# recovery is an operator's job. Automatic rollback, its recorded target
# (versions.env.prev / docker-compose.yml.prev) and the image retention that
# keeps that target's images are a separate change.

# Replaced from the release's own compose file before any recreate (see
# set_managed_services). Seeded, never empty, so nothing can accidentally
# expand to "every service" -- `compose up -d --no-deps` with no service
# arguments starts EVERYTHING, postgres included.
MANAGED_SERVICES="backend caddy"
MIGRATION_SERVICE="alembic-migration"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
HEALTH_INTERVAL=3

versions_env() { printf '%s/deploy/versions.env' "$COMPOSE_PROJECT_DIR"; }
compose_file() { printf '%s/docker-compose.yml' "$COMPOSE_PROJECT_DIR"; }

# Which compose file the wrapper below uses. Empty means the installed one.
# run_update points it at the staged release copy for the migration, so the
# migration runs against the definitions it shipped with while the host still
# holds the old file.
COMPOSE_FILE="${COMPOSE_FILE:-}"

# Read one pin out of a versions.env-format file. Keys are fixed literals, so
# no regex escaping is needed. Last assignment wins, as Compose itself does.
pin_get() {
    [ -f "$1" ] || return 0
    sed -n "s/^$2=//p" "$1" | tail -n 1
}

compose() {
    # Every flag explicit. Bind-mount sources in docker-compose.yml are
    # resolved by the Docker daemon, so guessing the project directory
    # silently breaks secrets rather than failing loudly.
    #
    # BOTH env files, in this order. --env-file REPLACES the default .env, it
    # does not add to it: with only the pins, CORS_ORIGIN/OSS_* interpolate to
    # empty strings and CADDY_PORT falls back to its :-80 default, so every
    # recreate would silently blank the backend's config and remap the public
    # port. Passing .env first and the pins second keeps the deployment's real
    # environment and still lets the pins win on BACKEND_IMAGE/CADDY_IMAGE
    # (later --env-file takes precedence for overlapping keys).
    # --project-directory stays at the deployment root even when -f points
    # elsewhere, so bind-mount sources (./secrets/*) keep resolving against
    # the host deployment while a staged compose file is in use.
    _cf=${COMPOSE_FILE:-$(compose_file)}
    if [ "${COMPOSE_ECHO:-0}" = "1" ]; then
        printf 'docker compose --project-directory %s -f %s --env-file %s --env-file %s -p %s %s\n' \
            "$COMPOSE_PROJECT_DIR" "$_cf" \
            "$COMPOSE_PROJECT_DIR/.env" "$(versions_env)" "$COMPOSE_PROJECT_NAME" "$*"
        return 0
    fi
    docker compose \
        --project-directory "$COMPOSE_PROJECT_DIR" \
        -f "$_cf" \
        --env-file "$COMPOSE_PROJECT_DIR/.env" \
        --env-file "$(versions_env)" \
        -p "$COMPOSE_PROJECT_NAME" \
        "$@"
}

# The services a deploy may recreate, taken from the compose file that is
# about to be used. Hardcoding "backend caddy" meant a release that added a
# service shipped its compose file and then never started the service --
# `--no-deps` does not start linked services either, so being a dependency of
# backend would not have saved it.
#
# Excluded, always: postgres (the database is not the application's to
# restart) and the alembic-* one-offs (`up -d` would leave them running;
# run_migration invokes the migration itself, once, under `compose run`).
set_managed_services() {
    _svcs=$(compose config --services 2>/dev/null \
        | grep -vx 'postgres' \
        | grep -v '^alembic-' \
        | tr '\n' ' ')
    _svcs=${_svcs% }

    # Fail closed. An empty list here would become `compose up -d --no-deps`
    # with no arguments, which starts every service in the file.
    [ -n "$_svcs" ] || {
        log "could not determine the services to manage from the compose file"
        return 1
    }
    case " $_svcs " in
        *" postgres "*)
            log "refusing: postgres appeared in the managed service list"
            return 1
            ;;
    esac

    MANAGED_SERVICES=$_svcs
    log "managed services: $MANAGED_SERVICES"
    return 0
}

# Compose `run --rm` helpers can be orphaned when the job is cancelled.
#
# NO status filter, deliberately: a one-off that is still RUNNING is the
# dangerous case, not the dead one. `--rm` only removes the container when it
# exits, so a migration whose client disconnected keeps going, stays invisible
# to a `status=exited` filter, and is never reaped -- and the next deploy then
# starts a SECOND `alembic upgrade head` concurrently against the same
# database. `rm -f` covers running and exited alike.
oneoff_ids() {
    docker ps -aq \
        --filter "label=com.docker.compose.project=$COMPOSE_PROJECT_NAME" \
        --filter "label=com.docker.compose.oneoff=True" 2>/dev/null
}

reap_orphans() {
    _ids=$(oneoff_ids)
    [ -n "$_ids" ] || return 0
    # shellcheck disable=SC2086 # deliberate word splitting over an id list
    docker rm -f $_ids >/dev/null 2>&1 || true
    # Verify, never assume: a surviving one-off may be a migration still
    # writing to the database, and starting a deploy beside it is the one
    # thing we must not do.
    _left=$(oneoff_ids)
    if [ -n "$_left" ]; then
        log "orphaned one-off containers could not be removed: $_left"
        return 1
    fi
    log "reaped orphaned one-off containers"
}

write_pins() {
    mkdir -p "$COMPOSE_PROJECT_DIR/deploy"
    printf 'APP_VERSION=%s\nBACKEND_IMAGE=%s\nCADDY_IMAGE=%s\n' "$1" "$2" "$3" \
        | atomic_write "$(versions_env)"
    # Capture atomic_write's status BEFORE logging: log always succeeds, so
    # returning its status would mask a refused write behind an apparently
    # successful pin update.
    _wp_rc=$?
    if [ "$_wp_rc" -eq 0 ]; then
        log "pinned APP_VERSION=$1 BACKEND_IMAGE=$2 CADDY_IMAGE=$3"
    else
        log "write_pins: atomic_write failed for $(versions_env)"
    fi
    return "$_wp_rc"
}

# Run the NEW image's migrations against the live database while the OLD
# application is still serving. Safe only because of the N-1 compatibility
# policy (docs/architecture/database.md §6). Non-zero MUST abort before
# anything is replaced.
run_migration() {
    _backend_ref=$1
    log "running migrations with $_backend_ref"
    # BACKEND_IMAGE is overridden in the environment because versions.env
    # still holds the OLD pins at this point -- deliberately, so an abort here
    # leaves the durable pins on the running version. Compose ranks shell env
    # above --env-file. Reversed, this would run the OLD migrations and report
    # success.
    BACKEND_IMAGE="$_backend_ref" compose run --rm "$MIGRATION_SERVICE"
}

# $1/$2 are the backend/caddy refs to start. NOT the version: recreating is
# not what makes a version current, so APP_VERSION is carried over unchanged
# here and run_update advances it once the health check has passed. Carried
# over rather than dropped, so an interrupted deploy leaves the record naming
# the last version that actually worked, not nothing.
recreate_services() {
    # A failed pin write must never be followed by `compose up`: with the OLD
    # pins still on disk, `up` would recreate nothing, exit 0, and the OLD
    # (genuinely healthy) containers would sail through wait_healthy --
    # reporting success while still running the old version.
    write_pins "$(pin_get "$(versions_env)" APP_VERSION)" "$1" "$2" || {
        log "recreate_services: aborting, version pins were not written"
        return 1
    }
    # After the pins are written, so `compose config` interpolates the images
    # this deploy is actually about to start.
    set_managed_services || {
        log "recreate_services: aborting, managed service list is unusable"
        return 1
    }
    # --no-deps: without it, `up -d backend caddy` pulls postgres in via
    # depends_on and re-runs alembic-migration a SECOND time via backend's
    # service_completed_successfully dependency -- run_migration already ran
    # it once against the new image. --no-deps also drops caddy's wait on
    # backend being healthy; if postgres is genuinely down, backend/caddy
    # simply fail to become healthy and wait_healthy fails the deploy, so
    # that wait was never load-bearing here.
    # shellcheck disable=SC2086 # MANAGED_SERVICES is a fixed internal literal
    compose up -d --no-deps $MANAGED_SERVICES
}

# `docker compose up` exiting 0 means "containers created", not "the
# application works". Committing a version on that basis is how a broken
# deploy gets recorded as a success.
#
# $1/$2 are the expected backend/caddy refs, always passed explicitly:
# container health alone cannot distinguish the NEW version from the OLD one,
# because if the pin write silently failed and nothing was recreated, the OLD
# containers are genuinely healthy too and would otherwise pass.
wait_healthy() {
    _want_backend=$1
    _want_caddy=$2
    _deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))

    while [ "$(date +%s)" -lt "$_deadline" ]; do
        _all_healthy=1
        for _svc in $MANAGED_SERVICES; do
            _cid=$(compose ps -q "$_svc" 2>/dev/null)
            [ -n "$_cid" ] || { _all_healthy=0; break; }
            _status=$(docker inspect --format \
                '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
                "$_cid" 2>/dev/null)

            case "$_svc" in
                backend|caddy)
                    # The two services this deploy pins. Both checks apply,
                    # and the expected ref must be non-empty: an absent ref
                    # must never compare "" = "" and pass vacuously, which is
                    # the whole reason this gate exists.
                    case "$_svc" in
                        backend) _want=$_want_backend ;;
                        caddy)   _want=$_want_caddy ;;
                    esac
                    [ "$_status" = "healthy" ] || { _all_healthy=0; break; }
                    _running=$(docker inspect --format '{{.Config.Image}}' \
                        "$_cid" 2>/dev/null)
                    [ -n "$_want" ] && [ "$_want" = "$_running" ] \
                        || { _all_healthy=0; break; }
                    ;;
                *)
                    # A service the release introduced. There is no pinned ref
                    # to compare it against, and it may declare no healthcheck
                    # at all -- demanding "healthy" would fail every deploy
                    # that adds one. Honour a healthcheck if it has one; its
                    # container existing is all this can otherwise assert.
                    [ "$_status" = "none" ] || [ "$_status" = "healthy" ] \
                        || { _all_healthy=0; break; }
                    ;;
            esac
        done

        if [ "$_all_healthy" -eq 1 ] && app_ready; then
            log "health check passed"
            return 0
        fi
        sleep "$HEALTH_INTERVAL"
    done

    log "health check timed out after ${HEALTH_TIMEOUT}s"
    return 1
}

# Application-level readiness, beyond container health.
#
# This runs on the deploy host, NOT inside backend-network -- the Compose DNS
# names `backend` and `caddy` do not resolve here. The published port is the
# right probe anyway: it is what a user actually reaches, and it is the one
# thing wait_healthy does not already cover (the in-network endpoints are
# exactly what the images' own HEALTHCHECKs hit, which it reads above).
app_ready() {
    # Ask the daemon for the mapping rather than reading CADDY_PORT: this is
    # authoritative, and it verifies the port publish itself.
    _hostport=$(compose port caddy 8080 2>/dev/null) || return 1
    [ -n "$_hostport" ] || return 1
    # "0.0.0.0:8443" or "[::]:8443" -> 8443. Connect over loopback explicitly;
    # curl to 0.0.0.0 is not portable.
    curl -fsS --max-time 5 -o /dev/null "http://127.0.0.1:${_hostport##*:}/"
}

run_update() {
    _version=$1

    _manifest=$(acquire_images "$_version") || return 1
    _backend_ref=$(manifest_field "$_manifest" '.images.backend.ref')
    _caddy_ref=$(manifest_field "$_manifest" '.images.caddy.ref')
    [ -n "$_backend_ref" ] && [ -n "$_caddy_ref" ] \
        || { log "manifest is missing an image ref"; return 1; }

    _staged_compose=$(fetch_compose "$_version") || {
        log "could not fetch the release's docker-compose.yml"
        return 1
    }

    # The migration runs against the RELEASE's compose file (its
    # alembic-migration service may differ from the installed one) with the
    # NEW image, while the installed file and pins are still untouched.
    COMPOSE_FILE=$_staged_compose
    run_migration "$_backend_ref"
    _mig_rc=$?
    COMPOSE_FILE=

    if [ "$_mig_rc" -ne 0 ]; then
        # The old application is still running and serving, and nothing on
        # disk has changed: nothing was deployed.
        log "alembic exited non-zero; application containers were NOT replaced"
        return 1
    fi

    atomic_write "$(compose_file)" < "$_staged_compose" || {
        log "could not install the release's compose file; refusing to deploy"
        return 1
    }

    # Both failures below leave the deployment BROKEN and say so. There is no
    # automatic recovery here, so the log line is the whole handover: the
    # compose file and the image pins already name $_version, the containers
    # are whatever the failed step left behind, and APP_VERSION still names
    # the last version that passed a health check.
    if ! recreate_services "$_backend_ref" "$_caddy_ref"; then
        log "could not recreate services on $_version; the deployment is broken"
        return 1
    fi

    if ! wait_healthy "$_backend_ref" "$_caddy_ref"; then
        log "$_version failed its health check; the deployment is broken"
        return 1
    fi

    # COMMIT. Everything above this line is reversible by redeploying; only
    # here is $_version known to be the version actually serving.
    write_pins "$_version" "$_backend_ref" "$_caddy_ref" || {
        log "$_version is serving but APP_VERSION was not advanced; the deploy directory needs a hand"
        return 1
    }

    log "updated to $_version"
    return 0
}
