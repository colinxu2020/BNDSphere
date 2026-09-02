#!/bin/sh
# Migration, recreation, health verification, update and rollback.
#
# THE VERSION RECORD is deploy/versions.env, and it is the only one. It holds
# what Compose will start, so it cannot drift from what is running the way a
# separate deployed.json could. Rollback reads versions.env.prev, which is a
# byte copy of that file taken immediately before a forward deploy overwrote
# it -- not a set of fields that can partially desync from it.
#
# docker-compose.yml is rotated the same way, from the release's own copy of
# it. A version therefore describes the whole deployment: a release that adds
# a service or an environment variable deploys without an operator having to
# edit the host first, and rollback restores the file that matched the version
# it restores.

# Replaced from the release's own compose file before any recreate (see
# set_managed_services). Seeded, never empty, so nothing can accidentally
# expand to "every service" -- `compose up -d --no-deps` with no service
# arguments starts EVERYTHING, postgres included.
MANAGED_SERVICES="backend caddy"
MIGRATION_SERVICE="alembic-migration"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
HEALTH_INTERVAL=3

versions_env()      { printf '%s/deploy/versions.env' "$COMPOSE_PROJECT_DIR"; }
versions_env_prev() { printf '%s/deploy/versions.env.prev' "$COMPOSE_PROJECT_DIR"; }
compose_file()      { printf '%s/docker-compose.yml' "$COMPOSE_PROJECT_DIR"; }
compose_file_prev() { printf '%s/docker-compose.yml.prev' "$COMPOSE_PROJECT_DIR"; }

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

recreate_services() {
    # A failed pin write must never be followed by `compose up`: with the OLD
    # pins still on disk, `up` would recreate nothing, exit 0, and the OLD
    # (genuinely healthy) containers would sail through wait_healthy --
    # reporting success while still running the old version.
    write_pins "$1" "$2" "$3" || {
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
    # simply fail to become healthy and wait_healthy rolls the deploy back,
    # so that wait was never load-bearing here.
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

# Only two versions are ever reachable: the one in versions.env and the one in
# versions.env.prev. Everything else is unreachable disk, and a deploy host
# accumulates a full image pair per release.
#
# `docker image rm` WITHOUT -f, deliberately: the daemon refuses to remove an
# image that a container still uses, which makes "never delete something in
# use" the daemon's invariant rather than this function's arithmetic.
prune_superseded() {
    _keep_ids=""
    _repos=""
    for _ref in "$@"; do
        [ -n "$_ref" ] || continue
        _id=$(docker image inspect --format '{{.Id}}' "$_ref" 2>/dev/null) || continue
        _keep_ids="$_keep_ids $_id"
        # Confine the sweep to the repositories we actually deploy, so an
        # unrelated image on the host is never a candidate.
        _repo=${_ref%@*}; _repo=${_repo%:*}
        case " $_repos " in *" $_repo "*) ;; *) _repos="$_repos $_repo" ;; esac
    done
    [ -n "$_keep_ids" ] || return 0

    for _repo in $_repos; do
        # --no-trunc so these are sha256:... ids, comparable with inspect's.
        for _id in $(docker image ls -q --no-trunc \
                        --filter "reference=$_repo" 2>/dev/null | sort -u); do
            case " $_keep_ids " in *" $_id "*) continue ;; esac
            if docker image rm "$_id" >/dev/null 2>&1; then
                log "pruned superseded image $_id"
            fi
        done
    done
    return 0
}

run_update() {
    _version=$1
    _current=$(pin_get "$(versions_env)" APP_VERSION)

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
        # disk has changed: nothing was deployed, so there is nothing to roll
        # back and the .prev files must keep naming whatever a manual rollback
        # should actually restore.
        log "alembic exited non-zero; application containers were NOT replaced"
        return 1
    fi

    # Rotate AFTER migration succeeded and immediately before the first step a
    # rollback could need to follow. Earlier, it would survive a migration
    # abort and leave .prev naming the version that is still running.
    #
    # ONLY when the version actually changes. Redeploying the version the pins
    # already name -- which is exactly what an operator does after a cancelled
    # job, since versions.env is written before `compose up` finishes -- would
    # otherwise copy that version over the rollback target and discard the
    # real last-known-good one.
    if [ "$_current" != "$_version" ]; then
        # compose FIRST, versions.env.prev LAST: the two writes cannot be made
        # atomic together, so the second one is the commit marker. Interrupted
        # in between, versions.env.prev is absent and a rollback refuses --
        # rather than pairing one version's pins with another's compose file.
        # Nothing has been replaced at this point either way.
        #
        # Redirected, not `cat ... |`: in a pipeline the status is
        # atomic_write's, so a missing source would write an EMPTY rollback
        # target and report success. As a redirect, the open failure fails.
        atomic_write "$(compose_file_prev)" < "$(compose_file)" || {
            log "could not record the previous compose file; refusing to deploy"
            return 1
        }
        atomic_write "$(versions_env_prev)" < "$(versions_env)" || {
            log "could not record the rollback target; refusing to deploy"
            return 1
        }
    else
        log "redeploying $_version; keeping the existing rollback target"
    fi

    # The automatic rollback target is whatever .prev records, NOT $_current.
    # A cancelled job leaves versions.env already naming the version being
    # deployed, so on a retry $_current IS that version -- and run_rollback
    # would reject it as a two-hop target and skip the rollback entirely,
    # leaving the broken release running with a valid target on disk.
    _rollback_target=$(pin_get "$(versions_env_prev)" APP_VERSION)

    atomic_write "$(compose_file)" < "$_staged_compose" || {
        log "could not install the release's compose file; refusing to deploy"
        return 1
    }

    if ! recreate_services "$_version" "$_backend_ref" "$_caddy_ref"; then
        log "could not recreate services on $_version — rolling back"
        run_rollback "$_rollback_target" automatic
        return 1
    fi

    if ! wait_healthy "$_backend_ref" "$_caddy_ref"; then
        log "$_version failed its health check — rolling back"
        run_rollback "$_rollback_target" automatic
        return 1
    fi

    log "updated to $_version"
    # Keep exactly the two reachable versions: this one, and the one rollback
    # would restore.
    prune_superseded "$_backend_ref" "$_caddy_ref" \
        "$(pin_get "$(versions_env_prev)" BACKEND_IMAGE)" \
        "$(pin_get "$(versions_env_prev)" CADDY_IMAGE)"
    return 0
}

# THE rollback path. Both triggers land here; there is no second
# implementation. `_trigger` is logged and deliberately never used in a
# conditional.
run_rollback() {
    _target=$1
    _trigger=$2
    _prev=$(versions_env_prev)

    [ -f "$_prev" ] || {
        log "no rollback target recorded ($_prev does not exist)"
        return 1
    }

    _prev_version=$(pin_get "$_prev" APP_VERSION)
    _backend_ref=$(pin_get "$_prev" BACKEND_IMAGE)
    _caddy_ref=$(pin_get "$_prev" CADDY_IMAGE)
    [ -n "$_backend_ref" ] && [ -n "$_caddy_ref" ] || {
        log "recorded rollback target has no image refs"
        return 1
    }

    # An operator naming a version that is not the recorded previous one is
    # asking for a two-hop rollback: that would skip a schema generation and
    # walk straight through the N-1 compatibility boundary the whole design
    # rests on. Refuse. An automatic rollback resolves its own target, so this
    # can only reject operator error.
    if [ "$_prev_version" != "$_target" ]; then
        log "recorded previous version ($_prev_version) is not the requested target ($_target); refusing a possible two-hop rollback"
        return 1
    fi

    log "rollback to $_target (trigger=$_trigger)"

    # Verify rather than assume: discovering a missing image during an
    # incident is the worst possible time. Pruning keeps this pair, so a
    # miss here means someone reclaimed space by hand.
    for _ref in "$_backend_ref" "$_caddy_ref"; do
        docker image inspect "$_ref" >/dev/null 2>&1 || {
            log "previous image $_ref is no longer present locally"
            return 1
        }
    done

    # Restore the compose file that matched this version, before recreating
    # against it. Absent on a deployment that predates compose rotation, in
    # which case the installed file is already the one that version ran with.
    if [ -f "$(compose_file_prev)" ]; then
        atomic_write "$(compose_file)" < "$(compose_file_prev)" || {
            log "could not restore the previous compose file"
            return 1
        }
    else
        log "no previous compose file recorded; keeping the installed one"
    fi

    # No migration, forward or backward. The schema stays at N while the
    # application returns to N-1; the N-1 compatibility policy makes that safe.
    if ! recreate_services "$_prev_version" "$_backend_ref" "$_caddy_ref"; then
        log "could not recreate services on the previous version"
        return 1
    fi

    if ! wait_healthy "$_backend_ref" "$_caddy_ref"; then
        log "the previous version did not become healthy — manual intervention required"
        return 1
    fi

    # The target is DROPPED, not rotated -- both files. Kept, it would name
    # the version now running, so a second rollback would sail through the
    # target check having done nothing. And the rolled-back-FROM version is not a target either:
    # that is the release which just failed, and offering it would be a
    # roll-forward into a known-bad version. After a rollback there is nothing
    # further back to go.
    rm -f "$_prev" "$(compose_file_prev)"
    log "rolled back to $_target"
    return 0
}
