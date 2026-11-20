#!/usr/bin/env bash
# Stage 52: PipeWire, WirePlumber, Bluetooth, and dynamic Fuxi H3 helper.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 52-audio: configuraria PipeWire, WirePlumber, Bluetooth e Fuxi H3 fix."
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

# Ensure pulseaudio daemon and HushMic are not installed
if pacman -Qq pulseaudio >/dev/null 2>&1; then
  nox_die "PulseAudio conflitante detectado; apenas PipeWire e permitido."
fi
if pacman -Qq hushmic-bin >/dev/null 2>&1; then
  nox_info "Removendo hushmic-bin legado..."
  pacman -Rns --noconfirm hushmic-bin || true
fi

# Enable Bluetooth service & tune BlueZ reconnection/fast-connect cleanly
systemctl enable bluetooth.service
if [[ -f /etc/bluetooth/main.conf ]]; then
  python3 - /etc/bluetooth/main.conf <<'PY'
import os, re, sys
p = sys.argv[1]
lines = open(p, "r", encoding="utf-8").read().splitlines()
desired = {
    "FastConnectable": "true",
    "AutoEnable": "true",
    "ReconnectAttempts": "7",
}
out, seen = [], set()
for line in lines:
    m = re.match(r'^\s*#?\s*(FastConnectable|AutoEnable|ReconnectAttempts)\s*=', line)
    if m and m.group(1) in desired and m.group(1) not in seen:
        k = m.group(1)
        out.append(f"{k} = {desired[k]}")
        seen.add(k)
    else:
        out.append(line)
for k, v in desired.items():
    if k not in seen:
        out.append(f"{k} = {v}")
tmp = p + ".nox.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
os.replace(tmp, p)
PY
fi

# Enable PipeWire/WirePlumber user sockets globally (packaging default, ensured explicitly)
systemctl --global enable pipewire.socket pipewire-pulse.socket wireplumber.service || true

# Install WirePlumber 0.5+ Bluetooth priority/codec & Fuxi H3 profile fragments
nox_atomic_install 0644 "${NOX_ROOT}/configs/wireplumber/51-bluetooth-priority.conf" \
  /etc/xdg/wireplumber/wireplumber.conf.d/51-bluetooth-priority.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/wireplumber/52-fuxi-h3-profile.conf" \
  /etc/xdg/wireplumber/wireplumber.conf.d/52-fuxi-h3-profile.conf

# Install dynamic Fuxi H3 helper + udev hotplug path watcher
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-fuxi-h3-fix" "${NOX_LIBEXEC_DIR}/nox-fuxi-h3-fix"
ln -sf "${NOX_LIBEXEC_DIR}/nox-fuxi-h3-fix" /usr/local/bin/nox-fuxi-h3-fix
nox_atomic_install 0644 "${NOX_ROOT}/configs/udev/85-nox-fuxi-h3.rules" /etc/udev/rules.d/85-nox-fuxi-h3.rules
nox_atomic_install 0644 "${NOX_ROOT}/configs/systemd/nox-fuxi-h3.path" /etc/systemd/user/nox-fuxi-h3.path
nox_atomic_install 0644 "${NOX_ROOT}/configs/systemd/nox-fuxi-h3.service" /etc/systemd/user/nox-fuxi-h3.service
mkdir -p /etc/systemd/user/umbriel-session.target.wants
ln -sf /etc/systemd/user/nox-fuxi-h3.path /etc/systemd/user/umbriel-session.target.wants/nox-fuxi-h3.path

# Ensure any legacy HushMic state/autostart/process artifacts are cleanly absent
systemctl --global disable hushmic.service >/dev/null 2>&1 || true
pkill -f '/usr/bin/hushmic' >/dev/null 2>&1 || true
pkill -f 'hushmic/filter-chain\.conf' >/dev/null 2>&1 || true
rm -f "${NOX_LIBEXEC_DIR}/nox-hushmic-setup" /usr/local/bin/nox-hushmic-setup
rm -rf /etc/skel/.config/hushmic
rm -f /etc/skel/.config/autostart/hushmic*.desktop
while IFS=: read -r uname _uid _gid uhome _shell; do
  [[ -n "$uname" && -d "$uhome" ]] || continue
  rm -rf "${uhome}/.config/hushmic"
  rm -f "${uhome}/.config/autostart"/hushmic*.desktop
  if [[ -f "${uhome}/.local/state/wireplumber/default-nodes" ]] &&
    grep -q 'hushmic_source' "${uhome}/.local/state/wireplumber/default-nodes"; then
    sed -i '/hushmic_source/d' "${uhome}/.local/state/wireplumber/default-nodes"
  fi
done < <(nox_list_human_users)

nox_info "Audio PipeWire/WirePlumber, Bluetooth e Fuxi H3 fix configurados (sem HushMic)."
