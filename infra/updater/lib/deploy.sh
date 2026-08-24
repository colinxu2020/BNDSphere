#!/bin/sh
# Migration, recreation, health verification, and the shared rollback executor.

# HARDCODED. The request never supplies these (spec §5, §8). Postgres is
# deliberately absent and must stay absent (spec §3, §18.3).
MANAGED_SERVICES="backend caddy"
MIGRATION_SERVICE="alembic-migration"
HEALTH_TIMEOUT="${HEALTH_TIMEOUT:-120}"
HEALTH_INTERVAL=3

versions_env() { printf '%s/deploy/versions.env' "$COMPOSE_PROJECT_DIR"; }

compose() {
    # Every flag explicit. Bind-mount sources in docker-compose.yml are
    # resolved by the HOST daemon, so guessing the project directory silently
    # breaks secrets rather than failing loudly (spec §13).
    if [ "${COMPOSE_ECHO:-0}" = "1" ]; then
        printf 'docker compose --project-directory %s -f %s --env-file %s -p %s %s\n' \
            "$COMPOSE_PROJECT_DIR" "$COMPOSE_PROJECT_DIR/docker-compose.yml" \
            "$(versions_env)" "$COMPOSE_PROJECT_NAME" "$*"
        return 0
    fi
    docker compose \
        --project-directory "$COMPOSE_PROJECT_DIR" \
        -f "$COMPOSE_PROJECT_DIR/docker-compose.yml" \
        --env-file "$(versions_env)" \
        -p "$COMPOSE_PROJECT_NAME" \
        "$@"
}

write_version_pins() {
    mkdir -p "$COMPOSE_PROJECT_DIR/deploy"
    printf '%s\n%s\n' \
        "BACKEND_IMAGE=$1" \
        "CADDY_IMAGE=$2" \
        | atomic_write "$(versions_env)"
    log "pinned BACKEND_IMAGE=$1 CADDY_IMAGE=$2"
}

# Run the NEW image's migrations against the live database while the OLD
# application is still serving. Safe only because of the N-1 compatibility
# policy (spec §11). A non-zero exit MUST abort before anything is replaced.
run_migration() {
    _backend_ref=$1
    log "running migrations with $_backend_ref"
    # BACKEND_IMAGE is overridden in the environment because versions.env still
    # holds the OLD pins at this point — deliberately, so an abort here leaves
    # the durable pins on the running version. Compose ranks shell env above
    # --env-file. Reversed, this would run the OLD migrations and report success.
    BACKEND_IMAGE="$_backend_ref" compose run --rm "$MIGRATION_SERVICE"
}

recreate_services() {
    write_version_pins "$1" "$2"
    # shellcheck disable=SC2086 # MANAGED_SERVICES is a fixed internal literal.
    compose up -d $MANAGED_SERVICES
}

# `docker compose up` exiting 0 means "containers created", not "the
# application works". Committing a version on that basis is how a broken
# deploy gets recorded as a success (spec §10.6).
wait_healthy() {
    _deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))

    while [ "$(date +%s)" -lt "$_deadline" ]; do
        _all_healthy=1
        for _svc in $MANAGED_SERVICES; do
            _cid=$(compose ps -q "$_svc" 2>/dev/null)
            [ -n "$_cid" ] || { _all_healthy=0; break; }
            _status=$(docker inspect --format \
                '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
                "$_cid" 2>/dev/null)
            [ "$_status" = "healthy" ] || { _all_healthy=0; break; }
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

# Application-level readiness, beyond container health. Reached over
# backend-network; the updater still has no listener of its own (spec §10.6).
app_ready() {
    curl -fsS --max-time 5 -o /dev/null http://backend:8000/health || return 1
    curl -fsS --max-time 5 -o /dev/null http://caddy:8080/ || return 1
    return 0
}

run_update() {
    _version=$1

    _current=$(deployed_get current_version)
    if [ "$_version" = "$_current" ]; then
        state_terminal failed already_current "$_version is already deployed"
        return 1
    fi

    _manifest=$(acquire_images "$_version") || return 1

    _backend_ref=$(manifest_field "$_manifest" '.images.backend.ref')
    _caddy_ref=$(manifest_field "$_manifest" '.images.caddy.ref')
    _prev_backend=$(deployed_get current_backend_ref)
    _prev_caddy=$(deployed_get current_caddy_ref)

    state_set target_version "$_version" previous_version "$_current"
    # Recorded before any side effect so the crash probes in Task 7 can ask
    # "are the running containers the ones we intended?" after an interruption.
    deployed_set target_backend_ref "$_backend_ref" target_caddy_ref "$_caddy_ref"

    state_stage migrating
    if ! run_migration "$_backend_ref"; then
        # Aborting here means the old application is still running and serving.
        state_terminal failed migration_failed \
            "alembic exited non-zero; application containers were NOT replaced"
        return 1
    fi

    state_stage deploying
    if ! recreate_services "$_backend_ref" "$_caddy_ref"; then
        state_stage rolling_back
        run_rollback "$_current" automatic
        return 1
    fi

    state_stage health_checking
    if ! wait_healthy; then
        log "new version $_version failed its health check — rolling back"
        run_rollback "$_current" automatic
        return 1
    fi

    deployed_set \
        current_version "$_version" \
        current_backend_ref "$_backend_ref" \
        current_caddy_ref "$_caddy_ref" \
        previous_version "$_current" \
        previous_backend_ref "$_prev_backend" \
        previous_caddy_ref "$_prev_caddy"

    state_terminal success "" "updated to $_version"
    prune_superseded_images
    return 0
}
