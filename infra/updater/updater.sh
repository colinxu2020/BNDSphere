#!/bin/sh
# One-shot deploy executor. Invoked by .github/workflows/deploy.yml on a
# self-hosted runner that lives on the deploy host.
#
# SECURITY BOUNDARY: this talks to the Docker daemon, which is root-equivalent
# on the host. The privilege is no longer held permanently by a container with
# /var/run/docker.sock mounted — it exists for the seconds a deploy takes — but
# it has not vanished: anyone who can dispatch this workflow, or who can push
# to the files it runs, gets it. The runner is the trust boundary now.
#
# Inputs are two positional arguments, both validated below. They arrive from
# workflow_dispatch, so they are attacker-controlled by anyone holding a token
# with actions:write.
set -u

UPDATER_DIR="${UPDATER_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"

. "$UPDATER_DIR"/lib/state.sh
. "$UPDATER_DIR"/lib/validate.sh
. "$UPDATER_DIR"/lib/artifact.sh
. "$UPDATER_DIR"/lib/deploy.sh
. "$UPDATER_DIR"/lib/recover.sh

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-bndsphere}"

main() {
    _action=${1:-}
    _version=${2:-}

    valid_action "$_action"   || die "invalid action: $_action"
    valid_version "$_version" || die "invalid version: $_version"

    validate_startup
    state_init

    # One job runs at a time (the workflow's `concurrency:` group), so a lock
    # directory found at startup was left by a process that no longer exists.
    # Clearing it unconditionally before recovery is correct here; judging
    # staleness from a recorded pid is not, because pids get reused.
    release_lock

    # A cancelled job or a dead runner leaves state.json non-terminal, which
    # the panel would read as "busy" forever. Mark it interrupted first. This
    # calls release_lock itself, hence its position before acquire_lock.
    # Non-zero here means recovery found something it could not reconcile --
    # in practice an orphaned one-off that would not die, possibly a migration
    # still writing to the database. It has already recorded a terminal failed
    # state; starting a deploy beside it is the one thing we must not do.
    recover_if_interrupted || die "recovery could not reconcile the previous run"

    acquire_lock || die "another deploy already holds the lock"
    trap release_lock EXIT

    log "deploy started (action=$_action version=$_version run=${GITHUB_RUN_ID:-local})"

    # request_id is the Actions run id: it is what the panel's log line and an
    # operator both need to find this deploy in the workflow history.
    state_set request_id "${GITHUB_RUN_ID:-local}" \
        last_processed_request_id "${GITHUB_RUN_ID:-local}" \
        action "$_action" requested_version "$_version" \
        started_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
        error_code "" error_message ""

    case "$_action" in
        update)   run_update "$_version" ;;
        rollback) run_rollback "$_version" manual ;;
    esac
}

# run_update, run_rollback and recover_if_interrupted live in lib/ and are
# sourced above — never redefine them here. A stub defined after the sourcing
# would shadow the real implementation and silently no-op the deploy.

# UPDATER_NO_MAIN lets the self-check source this file for its functions
# without executing a deploy.
[ "${UPDATER_NO_MAIN:-}" ] || main "$@"
