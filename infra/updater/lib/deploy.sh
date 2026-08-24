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
    # Capture atomic_write's status BEFORE calling log: log always succeeds,
    # so returning its status (as this function used to, implicitly) masked
    # every refused write behind an apparently-successful pin update -- the
    # same hazard state_stage/state_terminal were already fixed for.
    _rc=$?
    if [ "$_rc" -eq 0 ]; then
        log "pinned BACKEND_IMAGE=$1 CADDY_IMAGE=$2"
    else
        log "write_version_pins: atomic_write failed for $(versions_env), refusing"
    fi
    return "$_rc"
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
    # A failed pin write must never be followed by `compose up`: with the OLD
    # pins still on disk, `up` would recreate nothing, exit 0, and the OLD
    # (genuinely healthy) containers would sail through wait_healthy --
    # reporting success while still running the old version.
    write_version_pins "$1" "$2" || {
        log "recreate_services: aborting, version pins were not written"
        return 1
    }
    # --no-deps: `up -d backend caddy` would otherwise pull postgres in via
    # depends_on (starting a deliberately-stopped postgres) and re-run
    # alembic-migration a second time via backend's
    # service_completed_successfully dependency. The explicit migration step
    # in run_migration already runs under `compose run`, which waits for
    # postgres to be healthy on its own, so that dependency buys nothing
    # here. If postgres is genuinely down, backend/caddy will fail to become
    # healthy and wait_healthy rolls the deploy back -- the correct outcome
    # for a component with no business starting databases.
    # shellcheck disable=SC2086 # MANAGED_SERVICES is a fixed internal literal.
    compose up -d --no-deps $MANAGED_SERVICES
}

# `docker compose up` exiting 0 means "containers created", not "the
# application works". Committing a version on that basis is how a broken
# deploy gets recorded as a success (spec §10.6).
wait_healthy() {
    _deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
    # Recorded before recreate_services ran (spec: crash probes compare
    # against these). Reused here for the identity check below: container
    # health alone cannot distinguish the NEW version from the OLD one -- if
    # the pin write silently failed and nothing was actually recreated, the
    # OLD containers are genuinely healthy too and would otherwise pass.
    _target_backend=$(deployed_get target_backend_ref)
    _target_caddy=$(deployed_get target_caddy_ref)

    while [ "$(date +%s)" -lt "$_deadline" ]; do
        _all_healthy=1
        for _svc in $MANAGED_SERVICES; do
            _cid=$(compose ps -q "$_svc" 2>/dev/null)
            [ -n "$_cid" ] || { _all_healthy=0; break; }
            _status=$(docker inspect --format \
                '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
                "$_cid" 2>/dev/null)
            [ "$_status" = "healthy" ] || { _all_healthy=0; break; }

            case "$_svc" in
                backend) _want=$_target_backend ;;
                caddy)   _want=$_target_caddy ;;
                *)       _want= ;;
            esac
            _running=$(docker inspect --format '{{.Config.Image}}' "$_cid" 2>/dev/null)
            # Both sides must be non-empty before comparing, same discipline
            # as the artifact digest check: an absent target ref must never
            # compare "" = "" and pass vacuously.
            [ -n "$_want" ] && [ "$_want" = "$_running" ] || { _all_healthy=0; break; }
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

    # Every write below is checked: an unnoticed refusal here is exactly the
    # kind of silent failure state_set/deployed_set/state_stage/state_terminal
    # were made to return non-zero for. Each check below sits BEFORE the
    # side-effecting step it guards, so aborting on a refused write never
    # leaves an action half-applied.
    if ! state_set target_version "$_version" previous_version "$_current"; then
        state_terminal failed state_write_failed \
            "could not record target_version; refusing to proceed"
        return 1
    fi
    # Recorded before any side effect so the crash probes in Task 7 can ask
    # "are the running containers the ones we intended?" after an interruption
    # -- and so wait_healthy's image-identity check below has something to
    # compare against.
    if ! deployed_set target_backend_ref "$_backend_ref" target_caddy_ref "$_caddy_ref"; then
        state_terminal failed state_write_failed \
            "could not record target image refs; refusing to proceed"
        return 1
    fi

    if ! state_stage migrating; then
        state_terminal failed state_write_failed \
            "could not record migrating stage; refusing to proceed"
        return 1
    fi
    if ! run_migration "$_backend_ref"; then
        # Aborting here means the old application is still running and serving.
        state_terminal failed migration_failed \
            "alembic exited non-zero; application containers were NOT replaced"
        return 1
    fi

    if ! state_stage deploying; then
        state_terminal failed state_write_failed \
            "could not record deploying stage; refusing to proceed"
        return 1
    fi
    if ! recreate_services "$_backend_ref" "$_caddy_ref"; then
        state_stage rolling_back
        run_rollback "$_current" automatic
        return 1
    fi

    if ! state_stage health_checking; then
        state_terminal failed state_write_failed \
            "could not record health_checking stage; refusing to proceed"
        return 1
    fi
    if ! wait_healthy; then
        log "new version $_version failed its health check — rolling back"
        run_rollback "$_current" automatic
        return 1
    fi

    # The deploy itself succeeded at this point -- the new containers are up,
    # healthy, and running the intended images. A rollback here would tear
    # down a working deployment for a bookkeeping failure. Instead: refuse to
    # report success, so the stale deployed.json is visible as a failure
    # rather than a lie the next update (or a rollback) would trust.
    if ! deployed_set \
        current_version "$_version" \
        current_backend_ref "$_backend_ref" \
        current_caddy_ref "$_caddy_ref" \
        previous_version "$_current" \
        previous_backend_ref "$_prev_backend" \
        previous_caddy_ref "$_prev_caddy"; then
        state_terminal failed state_write_failed \
            "deployment succeeded but recording the new current version failed"
        return 1
    fi

    state_terminal success "" "updated to $_version"
    prune_superseded_images
    return 0
}
