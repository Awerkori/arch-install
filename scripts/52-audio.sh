#!/usr/bin/env bash
# Stage 52: PipeWire, WirePlumber, Bluetooth, dynamic Fuxi H3 helper, and HushMic.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"
source "${NOX_ROOT}/scripts/lib/aur.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 52-audio: configuraria PipeWire, WirePlumber, Bluetooth, Fuxi H3 fix e HushMic."
  exit 0
fi

nox_wait_pacman_lock

pacman -S --needed --noconfirm \
  pipewire \
  pipewire-pulse \
  pipewire-alsa \
  wireplumber \
  alsa-utils \
  bluez \
  bluez-utils \
  pavucontrol

# Ensure pulseaudio daemon is not installed
if pacman -Qq pulseaudio >/dev/null 2>&1; then
  nox_die "PulseAudio conflitante detectado; apenas PipeWire e permitido."
fi

# Install HushMic (AUR prebuilt binary) as unprivileged user
nox_aur_install_pkg "hushmic-bin"
nox_aur_cleanup_user

# Enable Bluetooth service (safe even if no BT adapter in VM)
systemctl enable bluetooth.service

# Enable PipeWire/WirePlumber user sockets globally (packaging default, ensured explicitly)
systemctl --global enable pipewire.socket pipewire-pulse.socket wireplumber.service || true

# Install WirePlumber 0.5+ Bluetooth priority fragment system-wide & in skel
nox_atomic_install 0644 "${NOX_ROOT}/configs/wireplumber/51-bluetooth-priority.conf" \
  /etc/xdg/wireplumber/wireplumber.conf.d/51-bluetooth-priority.conf

# Install dynamic Fuxi H3 & HushMic helpers
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-fuxi-h3-fix" "${NOX_LIBEXEC_DIR}/nox-fuxi-h3-fix"
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-hushmic-setup" "${NOX_LIBEXEC_DIR}/nox-hushmic-setup"
ln -sf "${NOX_LIBEXEC_DIR}/nox-fuxi-h3-fix" /usr/local/bin/nox-fuxi-h3-fix
ln -sf "${NOX_LIBEXEC_DIR}/nox-hushmic-setup" /usr/local/bin/nox-hushmic-setup

# Do NOT enable hushmic.service alongside XDG autostart (--tray) to avoid duplicate lock race
systemctl --global disable hushmic.service >/dev/null 2>&1 || true

# Pre-seed hushmic autostart config for existing users & skel (without forcing invalid device names)
mkdir -p /etc/skel/.config/hushmic /etc/skel/.config/autostart
cat > /etc/skel/.config/hushmic/config.toml <<'EOF'
mic = "default"
set_default = true
autostart = true
EOF

while IFS=: read -r uname uid gid uhome _shell; do
  [[ -n "$uname" && -d "$uhome" ]] || continue
  install -d -m 0755 -o "$uid" -g "$gid" "${uhome}/.config/hushmic"
  if [[ ! -f "${uhome}/.config/hushmic/config.toml" ]]; then
    nox_atomic_install 0644 /etc/skel/.config/hushmic/config.toml "${uhome}/.config/hushmic/config.toml"
    chown "${uid}:${gid}" "${uhome}/.config/hushmic/config.toml"
  fi
  su -s /usr/bin/bash "$uname" -c "HOME='${uhome}' hushmic config set autostart true && HOME='${uhome}' hushmic config set set_default true" >/dev/null 2>&1 || true
done < <(nox_list_human_users)

nox_info "Audio PipeWire/WirePlumber, Bluetooth, Fuxi H3 fix e HushMic configurados."
