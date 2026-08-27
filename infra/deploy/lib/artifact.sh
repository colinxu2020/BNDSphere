#!/bin/sh
# Artifact acquisition. One delivery path (the GitHub Release tarball),
# verified at every step.
#
# Nothing downloaded is ever executed unverified: the tarball is checked
# against SHA256SUMS BEFORE docker load, then the loaded config digests are
# re-checked against the manifest.

GITHUB_REPO="${GITHUB_REPO:-colinxu2020/BNDSphere}"
WORK_DIR="${WORK_DIR:-/tmp/bndsphere-deploy}"

ASSET_TARBALL="bndsphere-images-amd64.tar.gz"
ASSET_MANIFEST="release-manifest.json"
ASSET_SUMS="SHA256SUMS"

asset_url() {
    printf 'https://github.com/%s/releases/download/%s/%s' \
        "$GITHUB_REPO" "$1" "$2"
}

# Download to a temp name and rename only on success, so an interrupted
# transfer can never be mistaken for a complete file.
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
    # the root of trust for the post-load config_digest check, so it gets the
    # same verify-before-use treatment as the tarball itself. This buys integrity
    # against truncation/corruption -- not authenticity, since the manifest
    # and SHA256SUMS both arrive over the same unauthenticated channel.
    # Signing is the intended follow-up and is out of scope here.
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

fetch_and_load_tarball() {
    _version=$1; _manifest=$2

    # SHA256SUMS is already in $WORK_DIR: fetch_manifest downloaded and
    # verified it before this ever runs (review round 2). Re-fetching it here
    # bought nothing but a wasted round trip, and it deleted the known-good
    # copy first -- a transient failure on the re-fetch would discard a good
    # file, and the manifest and tarball could in principle end up checked
    # against two different versions of the sums file.
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

    log "fetching release assets for $_version"
    _manifest=$(fetch_manifest "$_version") || {
        log "could not fetch $ASSET_MANIFEST for $_version"
        return 1
    }

    fetch_and_load_tarball "$_version" "$_manifest"
    case $? in
        0) ;;
        2) log "SHA256SUMS did not match $ASSET_TARBALL"; return 1 ;;
        3) log "docker load failed"; return 1 ;;
        4) log "loaded image digest did not match the manifest"; return 1 ;;
        *) log "could not download release assets"; return 1 ;;
    esac

    printf '%s' "$_manifest"
    return 0
}
