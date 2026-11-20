#!/usr/bin/env sh
# Iniciador curto oficial do Nox Archinstall (v1.0.0)
# Baixa o bootstrap oficial via HTTPS, valida o SHA-256 e executa com TTY interativo.
set -eu

BOOTSTRAP_URL="https://github.com/Awerkori/arch-install/releases/download/v1.0.0/nox-install.py"
BOOTSTRAP_SHA256="fce3f9a83e2b8c13666cf583f143096de37b8dd312e59dd8c6af4acbabb82f10"

TMP_DIR="$(mktemp -d /tmp/nox-boot.XXXXXX)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

chmod 700 "$TMP_DIR"
BOOTSTRAP_FILE="$TMP_DIR/nox-install.py"

curl --proto '=https' --tlsv1.2 -fsSL --retry 3 --max-time 30 "$BOOTSTRAP_URL" -o "$BOOTSTRAP_FILE"
printf '%s  %s\n' "$BOOTSTRAP_SHA256" "$BOOTSTRAP_FILE" | sha256sum -c - >/dev/null 2>&1 || {
  echo "ERRO: falha na verificacao SHA-256 do bootstrap nox-install.py." >&2
  exit 1
}

if ( : </dev/tty ) 2>/dev/null; then
  python3 "$BOOTSTRAP_FILE" "$@" </dev/tty
else
  python3 "$BOOTSTRAP_FILE" "$@"
fi
