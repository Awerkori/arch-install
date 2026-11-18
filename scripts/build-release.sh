#!/usr/bin/env bash
# Build deterministic release tarball + SHA-256 and optionally update user_configuration.json.
set -Eeuo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${REPO_ROOT}/dist"
mkdir -p "$DIST_DIR"

VERSION="${1:-v1.0.0}"
BASE_URL="${2:-}"
COMMIT_SHA="$(git -C "$REPO_ROOT" rev-parse HEAD)"
TAR_NAME="nox-archinstall-payload-${VERSION}.tar.gz"
TAR_PATH="${DIST_DIR}/${TAR_NAME}"

# Deterministic archive from git HEAD (or working tree via temp index)
git -C "$REPO_ROOT" archive --format=tar.gz --prefix="nox-archinstall/" -o "$TAR_PATH" HEAD
SHA256="$(sha256sum "$TAR_PATH" | awk '{print $1}')"
printf '%s  %s\n' "$SHA256" "$TAR_NAME" > "${TAR_PATH}.sha256"

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
    "curl --proto \"=https\" --tlsv1.2 -fsSL --retry 3 --max-time 60 \"$URL\" -o \"$TMP/p.tar.gz\"; "
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
  python3 - "${REPO_ROOT}/manifests/release.json" "$VERSION" "$COMMIT_SHA" "$PAYLOAD_URL" "$SHA256" <<'PY'
import json, sys
out, ver, commit, url, sha = sys.argv[1:]
with open(out, "w", encoding="utf-8") as f:
    json.dump({
        "version": ver,
        "payload_commit": commit,
        "payload_url": url,
        "payload_sha256": sha,
    }, f, indent=2)
    f.write("\n")
PY
fi
