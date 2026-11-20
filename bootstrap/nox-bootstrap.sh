#!/usr/bin/env bash
# Verified remote payload bootstrapper executed by Archinstall custom_commands inside target chroot.
set -Eeuo pipefail
umask 077

PAYLOAD_URL="${1:-}"
EXPECTED_SHA256="${2:-}"
INSTALL_ARGS=("${@:3}")

if [[ -z "$PAYLOAD_URL" || -z "$EXPECTED_SHA256" ]]; then
  echo "Uso: nox-bootstrap.sh <PAYLOAD_URL> <SHA256> [args_install...]" >&2
  exit 2
fi

if [[ ! "$EXPECTED_SHA256" =~ ^[0-9a-fA-F]{64}$ ]]; then
  echo "ERRO: SHA-256 esperado invalido: $EXPECTED_SHA256" >&2
  exit 2
fi

if [[ "$PAYLOAD_URL" != https://* && "${NOX_ALLOW_INSECURE_HTTP:-0}" != "1" ]]; then
  echo "ERRO: URL do payload deve usar HTTPS: $PAYLOAD_URL" >&2
  exit 2
fi

is_target_chroot() {
  if [[ -r /proc/1/root/. && -r /. ]]; then
    local root_dev init_dev
    root_dev="$(stat -Lc '%d:%i' / 2>/dev/null || true)"
    init_dev="$(stat -Lc '%d:%i' /proc/1/root 2>/dev/null || true)"
    if [[ -n "$root_dev" && -n "$init_dev" && "$root_dev" != "$init_dev" ]]; then
      return 0
    fi
  fi
  if command -v systemd-detect-virt >/dev/null 2>&1 && systemd-detect-virt -r >/dev/null 2>&1; then
    return 0
  fi
  return 1
}

if [[ "${NOX_ALLOW_TARGET_EXEC:-0}" != "1" ]] && ! is_target_chroot && [[ ! -f /var/lib/nox-archinstall/target-armed ]]; then
  echo "BLOQUEIO DE SEGURANCA: nox-bootstrap.sh recusado fora do chroot/alvo autorizado." >&2
  exit 1
fi

TMP_DIR="$(mktemp -d /var/tmp/nox-bootstrap.XXXXXX)"
cleanup() { rm -rf "$TMP_DIR"; }
trap cleanup EXIT INT TERM HUP

TAR_PATH="${TMP_DIR}/payload.tar.gz"
CURL_PROTO="=https"
if [[ "${NOX_ALLOW_INSECURE_HTTP:-0}" == "1" ]]; then
  CURL_PROTO="=http,https"
fi

echo "[nox-bootstrap] Baixando payload verificado: ${PAYLOAD_URL}"
curl --proto "$CURL_PROTO" --proto-redir "$CURL_PROTO" --tlsv1.2 -fsSL --retry 3 --retry-delay 2 --max-time 60 \
  "$PAYLOAD_URL" -o "$TAR_PATH"

if [[ ! -s "$TAR_PATH" ]]; then
  echo "ERRO CRITICO: Payload baixado esta vazio." >&2
  exit 1
fi

ACTUAL_SHA256="$(sha256sum "$TAR_PATH" | awk '{print $1}')"
if [[ "${ACTUAL_SHA256,,}" != "${EXPECTED_SHA256,,}" ]]; then
  echo "ERRO CRITICO: Checksum SHA-256 divergente! Esperado=${EXPECTED_SHA256} Obtido=${ACTUAL_SHA256}" >&2
  exit 1
fi

DEST_DIR="${NOX_PAYLOAD_DEST_DIR:-/var/lib/nox-archinstall/payload}"
STAGE_DIR="${TMP_DIR}/extracted"
mkdir -p "$STAGE_DIR" "$(dirname "$DEST_DIR")"
tar --no-same-owner --no-same-permissions -xzf "$TAR_PATH" --strip-components=1 -C "$STAGE_DIR"

[[ -x "${STAGE_DIR}/install.sh" ]] || chmod +x "${STAGE_DIR}/install.sh"
rm -rf "$DEST_DIR"
mv "$STAGE_DIR" "$DEST_DIR"

if ((${#INSTALL_ARGS[@]} == 0)); then
  INSTALL_ARGS=(--stage target-offline)
fi

exec "${DEST_DIR}/install.sh" "${INSTALL_ARGS[@]}"
