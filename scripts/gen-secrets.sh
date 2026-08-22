#!/usr/bin/env bash
set -Eeuo pipefail

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
  # shellcheck disable=SC2312
  openssl rand -hex "${SECRETS[${name}]}" > "${file}"
  echo "[gen-secrets] wrote ${file}"
done

# Enforce 600 on all secret files (including any pre-existing ones).
chmod 600 "${SECRETS_DIR}"/*.txt 2>/dev/null || true

echo "[gen-secrets] done"
