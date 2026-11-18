#!/usr/bin/env bash
# Stage 50: Umbriel, Noctalia Shell, Noctalia Greeter, Kitty, Bash, Mesa/RADV, Noto fonts, Luciole.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"
source "${NOX_ROOT}/scripts/lib/aur.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 50-desktop: instalaria Umbriel, Noctalia, Greeter, Kitty, Mesa, fontes e Luciole."
  exit 0
fi

nox_wait_pacman_lock

# Ensure forbidden environments are never requested
PKGS=(
  # Graphics & Mesa/RADV/XWayland
  mesa
  lib32-mesa
  vulkan-radeon
  lib32-vulkan-radeon
  libva-mesa-driver
  xorg-xwayland
  # Umbriel + Portals + Polkit + DBus
  umbriel
  xdg-desktop-portal
  xdg-desktop-portal-umbriel
  xdg-desktop-portal-gtk
  polkit
  polkit-gnome
  # Noctalia Shell + Greeter + Terminal + Fonts + File helpers
  noctalia
  noctalia-greeter
  greetd
  kitty
  bash
  bash-completion
  xdg-utils
  xdg-user-dirs
  gvfs
  ffmpegthumbnailer
  poppler
  7zip
  # Dark mode & theming tools
  adw-gtk-theme
  gnome-themes-extra
  nwg-look
  qt5ct
  qt6ct
  # Fonts (Latin, CJK, Emoji + monospace for Kitty)
  noto-fonts
  noto-fonts-cjk
  noto-fonts-emoji
  ttf-jetbrains-mono-nerd
  # Clipboard & Wayland utilities
  wl-clipboard
  jq
)

nox_info "Instalando stack desktop oficial (Umbriel + Noctalia + Greeter + Kitty + Mesa)..."
pacman -S --needed --noconfirm "${PKGS[@]}"

# Build & install Luciole from AUR as unprivileged user (noctalia-dev/luciole)
nox_aur_install_pkg "luciole-git"
nox_aur_cleanup_user

# Verify bash is login shell for all human accounts and valid in /etc/shells
grep -qxF '/bin/bash' /etc/shells || printf '/bin/bash\n' >> /etc/shells
grep -qxF '/usr/bin/bash' /etc/shells || printf '/usr/bin/bash\n' >> /etc/shells
while IFS=: read -r uname _uid _gid _home ushell; do
  [[ -n "$uname" ]] || continue
  if [[ "$ushell" != "/bin/bash" && "$ushell" != "/usr/bin/bash" ]]; then
    nox_info "Ajustando shell de login de '$uname' para /usr/bin/bash..."
    chsh -s /usr/bin/bash "$uname"
  fi
done < <(nox_list_human_users)

# Verify no forbidden desktops/display managers/file managers crept in
for forbidden in hyprland sddm nemo plasma-desktop gnome-shell firefox chromium steam discord; do
  if pacman -Qq "$forbidden" >/dev/null 2>&1; then
    nox_die "Pacote proibido detectado no alvo: $forbidden"
  fi
done

nox_info "Stack desktop base instalado e auditado com sucesso."
