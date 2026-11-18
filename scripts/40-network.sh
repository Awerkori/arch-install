#!/usr/bin/env bash
# Stage 40: NetworkManager + iwd backend, iwd roaming config, BBR+fq, and iwlwifi-only link rule.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 40-network: configuraria NM+iwd, BBR+fq e Match Driver=iwlwifi."
  exit 0
fi

nox_wait_pacman_lock

pacman -S --needed --noconfirm networkmanager iwd iw ethtool

# Ensure only NetworkManager manages Wi-Fi via iwd backend (do not enable standalone iwd.service)
systemctl enable NetworkManager.service
systemctl disable iwd.service >/dev/null 2>&1 || true

nox_atomic_install 0644 "${NOX_ROOT}/configs/network/wifi_backend.conf" /etc/NetworkManager/conf.d/wifi_backend.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/network/wifi-powersave-off.conf" /etc/NetworkManager/conf.d/wifi-powersave-off.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/network/iwd-main.conf" /etc/iwd/main.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/network/10-iwlwifi.link" /etc/systemd/network/10-iwlwifi.link
nox_atomic_install 0644 "${NOX_ROOT}/configs/network/iwlwifi-ax210.conf" /etc/modprobe.d/iwlwifi-ax210.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/sysctl/99-bbr.conf" /etc/sysctl.d/99-bbr.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/sysctl/modules-bbr.conf" /etc/modules-load.d/bbr.conf

nox_info "Rede NM+iwd, BBR/fq e match restrito iwlwifi configurados."
