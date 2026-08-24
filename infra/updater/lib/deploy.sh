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
    # Named _write_pins_rc (not the generic _rc some lib/state.sh functions
    # use) so this local can never collide with theirs on the critical path.
    _write_pins_rc=$?
    if [ "$_write_pins_rc" -eq 0 ]; then
        log "pinned BACKEND_IMAGE=$1 CADDY_IMAGE=$2"
    else
        log "write_version_pins: atomic_write failed for $(versions_env), refusing"
    fi
    return "$_write_pins_rc"
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
    # --no-deps: without it, `up -d backend caddy` pulls postgres in via
    # depends_on (starting a deliberately-stopped postgres) and re-runs
    # alembic-migration a SECOND time via backend's
    # service_completed_successfully dependency -- run_migration above
    # already ran it once against the new image, under `compose run`, which
    # waits for postgres to be healthy on its own. That duplicate run is the
    # actual reason for --no-deps (NOT that this updater has no business
    # starting databases -- it already started postgres two lines earlier,
    # for the migration). --no-deps also drops caddy's compose-level wait on
    # backend being healthy; if postgres is genuinely down, backend/caddy
    # will simply fail to become healthy and wait_healthy rolls the deploy
    # back, so that wait was never load-bearing here.
    # shellcheck disable=SC2086 # MANAGED_SERVICES is a fixed internal literal.
    compose up -d --no-deps $MANAGED_SERVICES
}

# `docker compose up` exiting 0 means "containers created", not "the
# application works". Committing a version on that basis is how a broken
# deploy gets recorded as a success (spec §10.6).
# $1/$2: expected backend/caddy image refs, defaulting to the recorded
# target_*_ref when not supplied. A forward deploy needs no arguments -- the
# refs it just wrote are the right comparison. Rollback (next task) MUST
# pass the restored OLD refs explicitly: the durable target_*_ref fields
# still name the version being rolled back FROM, and comparing rollback's
# restored containers against those would fail every single time, on the
# one path that only runs after something has already gone wrong.
wait_healthy() {
    _want_backend=${1:-$(deployed_get target_backend_ref)}
    _want_caddy=${2:-$(deployed_get target_caddy_ref)}
    _deadline=$(( $(date +%s) + HEALTH_TIMEOUT ))
    # Container health alone cannot distinguish the NEW version from the OLD
    # one -- if the pin write silently failed and nothing was actually
    # recreated, the OLD containers are genuinely healthy too and would
    # otherwise pass.

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
                backend) _want=$_want_backend ;;
                caddy)   _want=$_want_caddy ;;
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
        # Aborting here means the old application is still running and serving,
        # and previous_* must NOT have been touched by this attempt: the
        # design defines migration_failed as "nothing deployed, old app keeps
        # running", so previous_version must keep naming whatever a manual
        # rollback should actually restore -- not the version that is, right
        # now, still running.
        state_terminal failed migration_failed \
            "alembic exited non-zero; application containers were NOT replaced"
        return 1
    fi

    if ! state_stage deploying; then
        state_terminal failed state_write_failed \
            "could not record deploying stage; refusing to proceed"
        return 1
    fi
    # Committed here, immediately before recreate_services -- the first step
    # a rollback could ever need to follow -- and not any earlier. Writing it
    # right after target_backend_ref (before migration) would have it survive
    # a migration_failed abort too, overwriting previous_version with the
    # version that is still running: a later manual rollback to the genuine
    # previous version would then be refused as a "mismatch" (or worse,
    # silently "succeed" at restoring the version already running). Recorded
    # here, not only on final success below, so an automatic rollback
    # triggered further down in THIS attempt resolves the version it actually
    # started from -- not whatever an earlier successful deploy left behind.
    if ! deployed_set previous_version "$_current" \
        previous_backend_ref "$_prev_backend" previous_caddy_ref "$_prev_caddy"; then
        state_terminal failed state_write_failed \
            "could not record previous image refs; refusing to proceed"
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
        current_caddy_ref "$_caddy_ref"; then
        state_terminal failed state_write_failed \
            "deployment succeeded but recording the new current version failed"
        return 1
    fi
    # previous_version/previous_backend_ref/previous_caddy_ref were already
    # committed durably above -- after migration succeeded, immediately
    # before recreate_services -- re-writing the same values here would be
    # redundant.

    state_terminal success "" "updated to $_version"
    prune_superseded_images
    return 0
}

# THE rollback path. Both triggers land here; there is no second
# implementation (spec §12.1). `_trigger` is recorded for the panel and the
# audit log and is deliberately never used in a conditional.
run_rollback() {
    _target=$1
    _trigger=$2

    state_set stage rolling_back trigger "$_trigger" target_version "$_target"
    _stage_write_rc=$?
    if [ "$_stage_write_rc" -ne 0 ]; then
        state_terminal failed state_write_failed \
            "could not record rollback stage; refusing to proceed"
        return 1
    fi
    log "rollback to $_target (trigger=$_trigger)"

    _backend_ref=$(deployed_get previous_backend_ref)
    _caddy_ref=$(deployed_get previous_caddy_ref)

    if [ -z "$_backend_ref" ] || [ -z "$_caddy_ref" ]; then
        state_terminal failed rollback_unavailable \
            "no previous image references recorded"
        return 1
    fi

    # previous_backend_ref/previous_caddy_ref are only trustworthy alongside
    # the previous_version they were recorded with. A forward update whose
    # final durable write failed (or any other stale bookkeeping) can leave
    # previous_version naming a version older than the one this call was
    # asked to restore -- silently restoring it anyway would skip a version
    # entirely. Refuse with the same code as "no refs at all": to an operator
    # both mean rollback cannot safely proceed from here.
    _recorded_previous_version=$(deployed_get previous_version)
    if [ "$_recorded_previous_version" != "$_target" ]; then
        state_terminal failed rollback_unavailable \
            "recorded previous_version ($_recorded_previous_version) does not match rollback target ($_target); refusing a possible two-hop rollback"
        return 1
    fi

    # Retention guarantees these are present; verify rather than assume,
    # because discovering it during an incident is the worst possible time.
    for _ref in "$_backend_ref" "$_caddy_ref"; do
        docker image inspect "$_ref" >/dev/null 2>&1 || {
            state_terminal failed rollback_unavailable \
                "previous image $_ref is no longer present locally"
            return 1
        }
    done

    # No migration, forward or backward. The schema stays at N while the
    # application returns to N-1; the N-1 compatibility policy is what makes
    # that safe.
    if ! recreate_services "$_backend_ref" "$_caddy_ref"; then
        state_terminal failed rollback_failed \
            "could not recreate services on the previous version"
        return 1
    fi

    # The same health gate as a forward deploy, but explicitly against the
    # RESTORED refs: wait_healthy's own default (target_backend_ref /
    # target_caddy_ref) names the version being rolled back FROM, and would
    # fail every single time here.
    if ! wait_healthy "$_backend_ref" "$_caddy_ref"; then
        state_terminal failed rollback_failed \
            "the previous version did not become healthy — manual intervention required"
        return 1
    fi

    if ! deployed_set \
        current_version "$_target" \
        current_backend_ref "$_backend_ref" \
        current_caddy_ref "$_caddy_ref"; then
        # The application IS back on the previous version at this point --
        # only the bookkeeping failed. Recording a clean success here would
        # be exactly the lie the equivalent guard in run_update refuses to
        # tell. rollback_failed, not rollback_success: the highest-severity
        # terminal state is reserved for "the new version is unhealthy and
        # the old one would not come back" -- this is milder (the old
        # version DID come back), but it must not read as a clean win either.
        state_terminal failed state_write_failed \
            "rollback succeeded but recording the restored version failed"
        return 1
    fi

    state_terminal rollback_success "" "rolled back to $_target"
    return 0
}
