#!/bin/sh
# Artifact acquisition. Two delivery paths, both verified.
#
# Nothing downloaded is ever executed unverified: the GHCR path pulls by
# immutable digest (self-verifying), and the tarball path checks SHA256SUMS
# BEFORE docker load, then re-checks the loaded config digests (spec §6.3).

GITHUB_REPO="${GITHUB_REPO:-colinxu2020/BNDSphere}"
WORK_DIR="${WORK_DIR:-/tmp/updater}"

ASSET_TARBALL="bndsphere-images-amd64.tar.gz"
ASSET_MANIFEST="release-manifest.json"
ASSET_SUMS="SHA256SUMS"

asset_url() {
    printf 'https://github.com/%s/releases/download/%s/%s' \
        "$GITHUB_REPO" "$1" "$2"
}

# Download to a temp name and rename only on success, so an interrupted
# transfer can never be mistaken for a complete file (spec §19.3).
download_asset() {
    _version=$1; _name=$2; _dest="$WORK_DIR/$_name"
    rm -f "$_dest" "$_dest.part"
    curl -fsSL --retry 3 --retry-delay 2 --max-time 1800 \
        -o "$_dest.part" "$(asset_url "$_version" "$_name")" || {
            rm -f "$_dest.part"
            return 1
        }
    mv -f "$_dest.part" "$_dest"
}

verify_checksum() {
    _dir=$1; _name=$2
    [ -f "$_dir/$ASSET_SUMS" ] || return 1
    [ -f "$_dir/$_name" ] || return 1
    # Check only the entry we care about; SHA256SUMS also covers the manifest,
    # which may not have been downloaded into this directory.
    ( cd "$_dir" && grep " [ *]\{0,1\}$_name\$" "$ASSET_SUMS" | sha256sum -c - ) \
        >/dev/null 2>&1
}

fetch_manifest() {
    _version=$1
    mkdir -p "$WORK_DIR"
    # SHA256SUMS must land before the manifest is validated: the manifest is
    # the root of trust for the digest checks on BOTH delivery paths (a GHCR
    # pull trusts the registry_digest it read from this file just as much as
    # the tarball path trusts config_digest), so it gets the same
    # verify-before-use treatment as the tarball itself. This buys integrity
    # against truncation/corruption -- not authenticity, since the manifest
    # and SHA256SUMS both arrive over the same unauthenticated channel.
    # Signing is the intended follow-up (design spec) and is out of scope here.
    download_asset "$_version" "$ASSET_SUMS" || return 1
    download_asset "$_version" "$ASSET_MANIFEST" || return 1
    verify_checksum "$WORK_DIR" "$ASSET_MANIFEST" || {
        rm -f "$WORK_DIR/$ASSET_MANIFEST"
        log "checksum mismatch for $ASSET_MANIFEST — refusing to trust it"
        return 1
    }
    jq -e . "$WORK_DIR/$ASSET_MANIFEST" >/dev/null 2>&1 || return 1
    printf '%s/%s' "$WORK_DIR" "$ASSET_MANIFEST"
}

manifest_field() {
    jq -r "$2 // empty" "$1"
}

pull_from_ghcr() {
    _manifest=$1
    for _component in backend caddy; do
        _ref=$(manifest_field "$_manifest" ".images.${_component}.ref")
        _digest=$(manifest_field "$_manifest" ".images.${_component}.registry_digest")
        [ -n "$_ref" ] && [ -n "$_digest" ] || return 1

        # Pull by digest, never by tag: a tag is mutable and a mutable
        # reference defeats the point of recording a digest at release time.
        _repo=${_ref%%:*}
        case "$_ref" in *:*/*) _repo=${_ref%:*} ;; *) _repo=${_ref%:*} ;; esac

        log "pulling ${_repo}@${_digest}"
        docker pull "${_repo}@${_digest}" >/dev/null 2>&1 || return 1
        # Re-tag to the human-readable ref so Compose pins stay readable.
        docker tag "${_repo}@${_digest}" "$_ref" || return 1
    done
    return 0
}

fetch_and_load_tarball() {
    _version=$1; _manifest=$2

    download_asset "$_version" "$ASSET_SUMS" || return 1
    download_asset "$_version" "$ASSET_TARBALL" || return 1

    # THE gate. Verify before load, never after.
    verify_checksum "$WORK_DIR" "$ASSET_TARBALL" || {
        rm -f "$WORK_DIR/$ASSET_TARBALL"
        log "checksum mismatch for $ASSET_TARBALL — refusing to load"
        return 2
    }

    docker load -i "$WORK_DIR/$ASSET_TARBALL" >/dev/null 2>&1 || return 3

    # A correct checksum proves the bytes arrived intact; this proves they
    # contain the images the manifest claims.
    for _component in backend caddy; do
        _ref=$(manifest_field "$_manifest" ".images.${_component}.ref")
        _want=$(manifest_field "$_manifest" ".images.${_component}.config_digest")
        _got=$(docker image inspect --format '{{.Id}}' "$_ref" 2>/dev/null)
        # Both sides must be non-empty before comparing: an absent
        # config_digest (or ref) must never compare "" = "" and pass
        # vacuously -- a manifest with missing/renamed image fields is a
        # digest mismatch, not a pass.
        [ -n "$_want" ] && [ -n "$_got" ] && [ "$_want" = "$_got" ] || {
            log "config digest mismatch for $_component: want '$_want' got '$_got'"
            return 4
        }
    done
    return 0
}

acquire_images() {
    _version=$1
    rm -rf "$WORK_DIR"; mkdir -p "$WORK_DIR"

    state_stage checking
    _manifest=$(fetch_manifest "$_version") || {
        state_terminal failed download_failed "could not fetch $ASSET_MANIFEST for $_version"
        return 1
    }

    state_stage downloading
    if pull_from_ghcr "$_manifest"; then
        state_set delivery_path ghcr
        state_stage verifying
        log "images acquired from GHCR by digest (self-verifying)"
        printf '%s' "$_manifest"
        return 0
    fi

    log "GHCR unavailable, falling back to the release tarball"
    state_set delivery_path tarball

    fetch_and_load_tarball "$_version" "$_manifest"
    case $? in
        0) ;;
        2) state_terminal failed checksum_mismatch "SHA256SUMS did not match $ASSET_TARBALL"; return 1 ;;
        3) state_terminal failed load_failed "docker load failed"; return 1 ;;
        4) state_terminal failed digest_mismatch "loaded image digest did not match the manifest"; return 1 ;;
        *) state_terminal failed download_failed "could not download release assets"; return 1 ;;
    esac

    state_stage verifying
    printf '%s' "$_manifest"
    return 0
}
