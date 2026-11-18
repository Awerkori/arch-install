#!/usr/bin/env bash
# Stage 90: Install first-boot service (in chroot) or execute runtime first-boot tasks (booted).
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 90-first-boot: instalaria/executaria nox-first-boot.service."
  exit 0
fi

nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-first-boot" "${NOX_LIBEXEC_DIR}/nox-first-boot"
nox_atomic_install 0644 "${NOX_ROOT}/configs/systemd/nox-first-boot.service" \
  /etc/systemd/system/nox-first-boot.service
systemctl enable nox-first-boot.service

if ! nox_is_chroot && [[ -d /run/systemd/system ]]; then
  nox_info "Sistema bootado detectado; executando nox-first-boot agora..."
  "${NOX_LIBEXEC_DIR}/nox-first-boot"
fi
