#!/usr/bin/env bash
set -Eeuo pipefail

# `declare -A` requires Bash 4+ (macOS ships /bin/bash 3.2 by default).
if (( BASH_VERSINFO[0] < 4 )); then
  echo "[gen-secrets] ERROR: Bash 4+ required (found ${BASH_VERSION})" >&2
  exit 2
fi

# Generate local development/test secrets under secrets/ (one file per secret).
#
# These files are consumed by docker compose's top-level `secrets:` block and
# mounted into the postgres / backend / test containers as /run/secrets/*.
# They are gitignored — never commit real values. Safe to run repeatedly:
# existing files are left untouched unless --force is passed.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SECRETS_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)/secrets"

FORCE=0
if [[ "${1:-}" == "--force" ]]; then
  FORCE=1
fi

mkdir -p "${SECRETS_DIR}"

# Secrets must not be world-readable: directory 700, files 600.
# The directory stays owned by the invoking user (it is never chowned below), so
# this chmod keeps working on every repeat run.
chmod 700 "${SECRETS_DIR}"

# name -> byte length (openssl rand -hex emits 2 hex chars per byte).
declare -A SECRETS=(
  [postgres_password]=32
  [app_db_password]=32
  [migration_db_password]=32
  [app_secret_key]=32
  [oss_access_key_id]=16
  [oss_access_key]=32
)

for name in "${!SECRETS[@]}"; do
  file="${SECRETS_DIR}/${name}.txt"
  if [[ -f "${file}" && "${FORCE}" -ne 1 ]]; then
    echo "[gen-secrets] ${file} already exists — skipping (use --force to regenerate)"
    continue
  fi
  # An earlier run may have chowned this file to uid 1000, leaving it unwritable
  # for the invoking user. We own the 700 directory, so replacing the entry works
  # regardless of the file's owner (directory write permission governs unlink).
  rm -f "${file}"
  # umask 077 creates the file 600 from the start — no world-readable window, and
  # no post-hoc chmod that would fail on a foreign-owned file.
  # shellcheck disable=SC2312
  (umask 077 && openssl rand -hex "${SECRETS[${name}]}" > "${file}")
  echo "[gen-secrets] wrote ${file}"
done

# Enforce 600 on pre-existing files we skipped above. Best-effort: a file already
# chowned to uid 1000 by an earlier run cannot be chmod'ed by a non-root invoker,
# but such a file was written 600 by this script in the first place.
chmod 600 "${SECRETS_DIR}"/*.txt 2>/dev/null || true

# Align secret *file* ownership to uid 1000 (the container `appuser`, see
# backend/Dockerfile). file-type compose secrets are bind mounts that preserve
# the host uid/mode: the CI runner runs as uid 1001, so 600 files owned by 1001
# are unreadable once the container drops to appuser (uid 1000) — pydantic then
# fails to read postgres_password and the smoke test crashes at import time.
#
# Only the files are chowned, never the directory: the invoking user must keep
# ownership of secrets/ so later runs can still chmod it and rotate entries
# (`--force`). Local dev already runs as uid 1000, where this is a no-op.
if [[ "$(id -u)" -eq 0 ]]; then
  # root: chown directly.
  chown 1000:1000 "${SECRETS_DIR}"/*.txt
elif [[ "$(id -u)" -ne 1000 ]]; then
  # Non-1000 non-root (e.g. GitHub runner uid 1001): prefer passwordless sudo.
  if sudo -n true 2>/dev/null; then
    sudo chown 1000:1000 "${SECRETS_DIR}"/*.txt
  else
    echo "[gen-secrets] WARNING: cannot chown secrets to 1000:1000 (no passwordless sudo);" >&2
    echo "[gen-secrets]   container user (uid 1000) may be unable to read these files." >&2
  fi
fi
# uid == 1000 (appuser, local dev): already correct owner, nothing to do.

echo "[gen-secrets] done"
