#!/usr/bin/env bash
# Stage 51: Keyboard (us/intl + vconsole), Umbriel config, displays, Kitty, and Noctalia Greeter.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 51-input-displays: configuraria us/intl, Umbriel TOML, Kitty e Noctalia Greeter."
  exit 0
fi

# 1. Install helper tools
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-display-profile" "${NOX_LIBEXEC_DIR}/nox-display-profile"
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-first-boot" "${NOX_LIBEXEC_DIR}/nox-first-boot"
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-session-init" "${NOX_LIBEXEC_DIR}/nox-session-init"
ln -sf "${NOX_LIBEXEC_DIR}/nox-display-profile" /usr/local/bin/nox-display-profile

# 2. System locale = en_US.UTF-8, Timezone = America/Sao_Paulo, Keyboard = us/intl + Cedilla (.XCompose)
if [[ -f /etc/locale.gen ]]; then
  sed -i 's/^#[[:space:]]*\(en_US\.UTF-8 UTF-8\)/\1/' /etc/locale.gen
  if ! grep -Eq '^[[:space:]]*en_US\.UTF-8[[:space:]]+UTF-8' /etc/locale.gen; then
    printf 'en_US.UTF-8 UTF-8\n' >> /etc/locale.gen
  fi
fi
if ! locale -a 2>/dev/null | grep -qiE '^en_US\.utf-?8$'; then
  locale-gen
fi
cat > /etc/locale.conf <<'EOF'
LANG=en_US.UTF-8
LC_MESSAGES=en_US.UTF-8
EOF
chmod 0644 /etc/locale.conf

if [[ -f /usr/share/zoneinfo/America/Sao_Paulo ]]; then
  ln -sf /usr/share/zoneinfo/America/Sao_Paulo /etc/localtime
fi

# System-wide session environment (language + RADV + Qt theme + large shader cache)
touch /etc/environment
python3 - /etc/environment <<'PY'
import os, re, sys
p = sys.argv[1]
desired = {
    "LANG": "en_US.UTF-8",
    "LC_MESSAGES": "en_US.UTF-8",
    "QT_QPA_PLATFORMTHEME": "qt5ct:qt6ct",
    "AMD_VULKAN_ICD": "RADV",
    "MESA_SHADER_CACHE_MAX_SIZE": "12G",
}
lines = open(p, "r", encoding="utf-8").read().splitlines()
out, seen = [], set()
for line in lines:
    m = re.match(r'^\s*([A-Z0-9_]+)\s*=', line)
    if m and m.group(1) in desired:
        k = m.group(1)
        if k not in seen:
            out.append(f"{k}={desired[k]}")
            seen.add(k)
    else:
        out.append(line)
for k, v in desired.items():
    if k not in seen:
        out.append(f"{k}={v}")
tmp = p + ".nox.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
os.replace(tmp, p)
PY

# Console keymap (valid kbd map for US International) & localectl X11 keymap
cat > /etc/vconsole.conf <<'EOF'
KEYMAP=us-acentos
FONT=default8x16
EOF

# Cedilla support (' + c -> ç) for en_US.UTF-8 with US International dead keys
cat > /etc/skel/.XCompose <<'EOF'
include "%L"
<dead_acute> <C> : "Ç" Ccedilla
<dead_acute> <c> : "ç" ccedilla
EOF
chmod 0644 /etc/skel/.XCompose

mkdir -p /etc/X11/xorg.conf.d
cat > /etc/X11/xorg.conf.d/00-keyboard.conf <<'EOF'
Section "InputClass"
        Identifier "system-keyboard"
        MatchIsKeyboard "on"
        Option "XkbLayout" "us"
        Option "XkbVariant" "intl"
EndSection
EOF

# 3. Kitty config + xdg-terminals.list
mkdir -p /etc/skel/.config/kitty
cat > /etc/skel/.config/kitty/kitty.conf <<'EOF'
font_family      JetBrainsMono Nerd Font
bold_font        auto
italic_font      auto
bold_italic_font auto
font_size        11.0
shell            /usr/bin/bash
confirm_os_window_close 0
background_opacity 0.94
EOF

printf 'kitty.desktop\n' > /etc/skel/.config/xdg-terminals.list

# 4. Umbriel main configuration + safe outputs.toml baseline + optional local override template
nox_atomic_install 0644 "${NOX_ROOT}/configs/umbriel/config.toml" /etc/skel/.config/umbriel/config.toml
cat > /etc/skel/.config/umbriel/outputs.local.toml <<'EOF'
# Optional manual monitor overrides (loaded after outputs.toml, preserved across updates/logins).
# Uncomment and adjust if you need a fine vertical offset on physical hardware:
# [output."HDMI-A-1"]
# position = [2560, -350]
EOF
chmod 0644 /etc/skel/.config/umbriel/outputs.local.toml
"${NOX_LIBEXEC_DIR}/nox-display-profile" \
  --profile "${NOX_CFG_DIR}/hardware.json" \
  --output /etc/skel/.config/umbriel/outputs.toml || true

# Validate Umbriel TOML config directly with umbriel binary
if command -v umbriel >/dev/null 2>&1; then
  umbriel config validate -c /etc/skel/.config/umbriel/config.toml \
    || nox_die "Falha na validacao sintatica do config.toml do Umbriel!"
fi

# Deploy configs to existing human users without overwriting unrelated files
while IFS=: read -r uname uid gid uhome _shell; do
  [[ -n "$uname" && -d "$uhome" ]] || continue
  install -d -m 0755 -o "$uid" -g "$gid" "${uhome}/.config/umbriel" "${uhome}/.config/kitty"
  nox_atomic_install 0644 "${NOX_ROOT}/configs/umbriel/config.toml" "${uhome}/.config/umbriel/config.toml"
  chown "${uid}:${gid}" "${uhome}/.config/umbriel/config.toml"
  if [[ -f /etc/skel/.config/umbriel/outputs.toml ]]; then
    nox_atomic_install 0644 /etc/skel/.config/umbriel/outputs.toml "${uhome}/.config/umbriel/outputs.toml"
    chown "${uid}:${gid}" "${uhome}/.config/umbriel/outputs.toml"
  fi
  if [[ ! -f "${uhome}/.config/umbriel/outputs.local.toml" ]]; then
    nox_atomic_install 0644 /etc/skel/.config/umbriel/outputs.local.toml "${uhome}/.config/umbriel/outputs.local.toml"
    chown "${uid}:${gid}" "${uhome}/.config/umbriel/outputs.local.toml"
  fi
  if [[ ! -f "${uhome}/.config/kitty/kitty.conf" ]]; then
    nox_atomic_install 0644 /etc/skel/.config/kitty/kitty.conf "${uhome}/.config/kitty/kitty.conf"
    chown "${uid}:${gid}" "${uhome}/.config/kitty/kitty.conf"
  fi
  nox_atomic_install 0644 /etc/skel/.config/xdg-terminals.list "${uhome}/.config/xdg-terminals.list"
  chown "${uid}:${gid}" "${uhome}/.config/xdg-terminals.list"
  nox_atomic_install 0644 /etc/skel/.XCompose "${uhome}/.XCompose"
  chown "${uid}:${gid}" "${uhome}/.XCompose"
done < <(nox_list_human_users)

# 5. Configure greetd + Noctalia Greeter (SDDM excluded)
for dm in sddm gdm lightdm lxdm; do
  if systemctl is-enabled "${dm}.service" >/dev/null 2>&1; then
    systemctl disable "${dm}.service" || true
  fi
done

id -u greeter >/dev/null 2>&1 || nox_die "Usuario de sistema 'greeter' nao encontrado."
grep -q '^Exec=start-umbriel' /usr/share/wayland-sessions/umbriel.desktop \
  || nox_die "Session file /usr/share/wayland-sessions/umbriel.desktop invalido ou ausente."

cat > /etc/greetd/config.toml <<'EOF'
[terminal]
vt = 1

[default_session]
command = "/usr/bin/noctalia-greeter-session"
user = "greeter"
EOF
chmod 0644 /etc/greetd/config.toml

mkdir -p /etc/tmpfiles.d
cat > /etc/tmpfiles.d/noctalia-greeter.conf <<'EOF'
d /var/lib/noctalia-greeter 0750 greeter greeter -
EOF
systemd-tmpfiles --create /etc/tmpfiles.d/noctalia-greeter.conf || true

if command -v noctalia-greeter-apply-appearance >/dev/null 2>&1; then
  GREETER_USER=greeter noctalia-greeter-apply-appearance --setup-system || true
fi

nox_atomic_install 0644 "${NOX_ROOT}/configs/greeter/greeter.toml" /var/lib/noctalia-greeter/greeter.toml
chown -R greeter:greeter /var/lib/noctalia-greeter
chmod 0750 /var/lib/noctalia-greeter

systemctl enable greetd.service
nox_info "Teclado us/intl, Umbriel, Kitty e Noctalia Greeter configurados."
