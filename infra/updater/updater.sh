#!/bin/sh
# BNDSphere deployment updater.
#
# SECURITY BOUNDARY (spec §4): this process has /var/run/docker.sock. Docker
# socket access is equivalent to root on the host. If this process is
# compromised, assume the host is compromised. The hardening on this container
# reduces the attack surface; it does NOT remove the daemon privilege boundary.
#
# Consequently this process has no listener, no published port, and accepts no
# commands — only a validated version identifier from $REQUEST_DIR.
set -u

. /updater/lib/state.sh

COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-bndsphere}"
POLL_INTERVAL="${POLL_INTERVAL:-5}"

main() {
    validate_startup
    log "updater started (project=$COMPOSE_PROJECT_NAME dir=$COMPOSE_PROJECT_DIR)"

    while true; do
        # Request handling is added in Task 3.
        sleep "$POLL_INTERVAL"
    done
}

main "$@"
