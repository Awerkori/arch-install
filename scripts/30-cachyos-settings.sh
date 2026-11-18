#!/usr/bin/env bash
# Stage 30: Paru (CachyOS), cachyos-settings, SCX LAVD, Ananicy, IRQBalance, GameMode, TRIM, Sudo.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 30-cachyos-settings: instalaria paru/cachyos-settings/scx/ananicy/irqbalance/gamemode e sudo seguro."
  exit 0
fi

nox_wait_pacman_lock

# 1. Install Paru strictly from [cachyos] repo + CachyOS optimization stack
nox_info "Instalando paru (CachyOS) e pacotes de otimizacao..."
pacman -S --needed --noconfirm \
  cachyos/paru \
  cachyos-settings \
  scx-scheds \
  scx-tools \
  ananicy-cpp \
  cachyos-ananicy-rules \
  irqbalance \
  gamemode \
  lib32-gamemode

# Verify paru provenance (must NOT be paru-git)
if pacman -Qq paru-git >/dev/null 2>&1; then
  nox_die "paru-git detectado no alvo; apenas paru estavel do CachyOS e permitido."
fi
paru --version

# 2. Configure scx_loader for scx_lavd in Gaming mode
nox_atomic_install 0644 "${NOX_ROOT}/configs/scx_loader/config.toml" /etc/scx_loader/config.toml

# 3. Enable system services & timers (no --now in chroot)
for unit in \
  scx_loader.service \
  ananicy-cpp.service \
  irqbalance.service \
  fstrim.timer \
  systemd-resolved.service \
  systemd-oomd.service
do
  systemctl enable "$unit"
done

# Ensure systemd-resolved stub symlink is created cleanly at early boot (preserving chroot DNS now)
mkdir -p /etc/tmpfiles.d
cat > /etc/tmpfiles.d/nox-resolv.conf <<'EOF'
L+ /etc/resolv.conf - - - - ../run/systemd/resolve/stub-resolv.conf
EOF

# 4. Sudo hardening & validation (wheel authenticated, zero NOPASSWD)
nox_atomic_install 0440 "${NOX_ROOT}/configs/sudoers/10-wheel" /etc/sudoers.d/10-wheel
visudo -cf /etc/sudoers >/dev/null || nox_die "Falha na validacao visudo de /etc/sudoers!"
visudo -cf /etc/sudoers.d/10-wheel >/dev/null || nox_die "Falha na validacao visudo de /etc/sudoers.d/10-wheel!"
if grep -rn 'NOPASSWD' /etc/sudoers /etc/sudoers.d/ 2>/dev/null; then
  nox_die "Detectado NOPASSWD nao autorizado em configuracao sudoers!"
fi

nox_info "Paru CachyOS, cachyos-settings, SCX LAVD, servicos e sudo validados."
