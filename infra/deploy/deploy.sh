#!/bin/sh
# One-shot deploy executor. Invoked by .github/workflows/deploy.yml on a
# self-hosted runner that lives on the deploy host.
#
# SECURITY BOUNDARY: this talks to the Docker daemon, which is root-equivalent
# on the host. The privilege is no longer held permanently by a container with
# /var/run/docker.sock mounted — it exists for the seconds a deploy takes —
# but it has not vanished: anyone who can dispatch this workflow, or who can
# push to the files it runs, gets it. The runner is the trust boundary now.
#
# Inputs are two positional arguments. They arrive from workflow_dispatch, so
# they are attacker-controlled by anyone holding a token with actions:write,
# and are validated below before anything uses them.
#
# NO LOCK, NO STATE FILE, NO CRASH RECOVERY. The workflow's `concurrency:
# deploy` group already guarantees one job at a time, the Actions run page is
# the progress and failure report, and a job that dies is simply re-run —
# versions.env is written atomically, so there is no half-state to reconcile.
set -u

SCRIPT_DIR="${SCRIPT_DIR:-$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)}"

. "$SCRIPT_DIR"/lib/common.sh
. "$SCRIPT_DIR"/lib/artifact.sh
. "$SCRIPT_DIR"/lib/stack.sh

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-bndsphere}"

main() {
    _action=${1:-}
    _version=${2:-}

    valid_version "$_version" || die "invalid version: $_version"
    validate_startup

    # A cancelled job can leave a `compose run --rm` migration alive with no
    # client. Starting a second `alembic upgrade head` beside it is the one
    # thing we must not do, so refuse rather than deploy.
    reap_orphans || die "an orphaned one-off container is still present; refusing to start new work"

    log "deploy started (action=$_action version=$_version run=${GITHUB_RUN_ID:-local})"

    # The `*)` arm is the action validation: a `case` that silently fell
    # through would exit 0 having deployed nothing.
    case "$_action" in
        update)   run_update "$_version" ;;
        rollback) run_rollback "$_version" manual ;;
        *)        die "invalid action: $_action" ;;
    esac
}

# run_update and run_rollback live in lib/ and are sourced above — never
# redefine them here. A stub defined after the sourcing would shadow the real
# implementation and silently no-op the deploy.

# DEPLOY_NO_MAIN lets the self-check source this file for its functions
# without executing a deploy.
[ "${DEPLOY_NO_MAIN:-}" ] || main "$@"
