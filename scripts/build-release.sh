#!/usr/bin/env bash
# Build deterministic release tarball + SHA-256 and optionally update user_configuration.json & manifests/release.json.
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
mkdir -p "$DIST_DIR"

VERSION="${1:-v1.0.1}"
BASE_URL="${2:-}"
COMMIT_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
TAR_NAME="nox-archinstall-payload-${VERSION}.tar.gz"
TAR_PATH="${DIST_DIR}/${TAR_NAME}"

# Deterministic archive excluding release-pointer & stage-1/2 wrapper files (user_configuration.json,
# manifests/release.json, i, bootstrap/nox-install.py, README.md, docs/*) so post-payload commit pinning
# never alters the deterministic payload tarball hash.
GZIP=-n tar --sort=name --mtime='UTC 2026-01-01' --owner=0 --group=0 --numeric-owner \
  --exclude='.git' --exclude='dist' --exclude='__pycache__' --exclude='*.pyc' --exclude='*.pyo' \
  --exclude='./user_configuration.json' --exclude='./manifests/release.json' \
  --exclude='./i' --exclude='./bootstrap/nox-install.py' \
  --exclude='./README.md' --exclude='./docs' --exclude='./tests' \
  -czf "$TAR_PATH" -C "$REPO_ROOT" .
SHA256="$(sha256sum "$TAR_PATH" | awk '{print $1}')"
printf '%s  %s\n' "$SHA256" "$TAR_NAME" >"${TAR_PATH}.sha256"

echo "Built: ${TAR_PATH}"
echo "Commit: ${COMMIT_SHA}"
echo "SHA256: ${SHA256}"

if [[ -n "$BASE_URL" ]]; then
  PAYLOAD_URL="${BASE_URL}/${TAR_NAME}"
  python3 - "${REPO_ROOT}/user_configuration.json" "$PAYLOAD_URL" "$SHA256" <<'PY'
import json, sys
cfg_path, url, sha = sys.argv[1:]
with open(cfg_path, "r", encoding="utf-8") as f:
    data = json.load(f)
cmd = (
    "bash -c 'set -Eeuo pipefail; "
    f"URL=\"{url}\"; SHA=\"{sha}\"; "
    "TMP=$(mktemp -d); trap \"rm -rf $TMP\" EXIT; "
    "curl --proto \"=https\" --proto-redir \"=https\" --tlsv1.2 -fsSL --retry 3 --max-time 60 \"$URL\" -o \"$TMP/p.tar.gz\"; "
    "printf \"%s  %s\\n\" \"$SHA\" \"$TMP/p.tar.gz\" | sha256sum -c -; "
    "rm -rf /var/lib/nox-archinstall/payload; mkdir -p /var/lib/nox-archinstall/payload; "
    "tar --no-same-owner -xzf \"$TMP/p.tar.gz\" --strip-components=1 -C /var/lib/nox-archinstall/payload; "
    "chmod +x /var/lib/nox-archinstall/payload/install.sh; "
    "exec /var/lib/nox-archinstall/payload/install.sh --stage target-offline'"
)
data["custom_commands"] = [cmd]
with open(cfg_path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY

  CONFIG_SHA256="$(sha256sum "${REPO_ROOT}/user_configuration.json" | awk '{print $1}')"
  BOOTSTRAP_SHA256="$(sha256sum "${REPO_ROOT}/bootstrap/nox-install.py" | awk '{print $1}')"
  LAUNCHER_SHA256="$(sha256sum "${REPO_ROOT}/i" | awk '{print $1}')"
  PAYLOAD_SHA_FILE_SHA256="$(sha256sum "${TAR_PATH}.sha256" | awk '{print $1}')"

  python3 - "${REPO_ROOT}/manifests/release.json" "$VERSION" "$COMMIT_SHA" "$PAYLOAD_URL" "$SHA256" "$CONFIG_SHA256" "$BOOTSTRAP_SHA256" "$LAUNCHER_SHA256" "$TAR_NAME" "$PAYLOAD_SHA_FILE_SHA256" <<'PY'
import datetime, json, sys
(
    out,
    ver,
    commit,
    url,
    payload_sha,
    cfg_sha,
    boot_sha,
    launcher_sha,
    tar_name,
    sha_file_sha,
) = sys.argv[1:]
manifest = {
    "schema_version": 2,
    "version": ver,
    "payload_commit": commit,
    "source_commit": commit,
    "generated_at_utc": "2026-11-20T00:00:00Z",
    "trust_model": "immutable-commit-and-sha256-pinning",
    "payload_url": url,
    "payload_sha256": payload_sha,
    "config_sha256": cfg_sha,
    "bootstrap_sha256": boot_sha,
    "launcher_sha256": launcher_sha,
    "artifacts": {
        "launcher": {
            "name": "i",
            "path": "i",
            "sha256": launcher_sha,
        },
        "bootstrap": {
            "name": "nox-install.py",
            "path": "bootstrap/nox-install.py",
            "sha256": boot_sha,
        },
        "config": {
            "name": "user_configuration.json",
            "path": "user_configuration.json",
            "sha256": cfg_sha,
        },
        "payload": {
            "name": tar_name,
            "url": url,
            "sha256": payload_sha,
        },
        "payload_checksum_file": {
            "name": f"{tar_name}.sha256",
            "sha256": sha_file_sha,
        },
    },
    "reproducibility": {
        "build_script": "scripts/build-release.sh",
        "tar_flags": "GZIP=-n tar --sort=name --mtime='UTC 2026-01-01' --owner=0 --group=0 --numeric-owner",
        "excluded_paths": [
            ".git",
            "dist",
            "__pycache__",
            "*.pyc",
            "*.pyo",
            "./user_configuration.json",
            "./manifests/release.json",
            "./i",
            "./bootstrap/nox-install.py",
            "./README.md",
            "./docs",
            "./tests",
        ],
    },
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2)
    f.write("\n")
PY
fi
