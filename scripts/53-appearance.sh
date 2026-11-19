#!/usr/bin/env bash
# Stage 53: Dark mode (GTK3/4, Qt5/6), XDG defaults (Luciole + Firefox Pure), minimalist Noctalia launcher, btop/fastfetch configs, fonts cache, user session unit.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 53-appearance: configuraria GTK/Qt dark mode, mimeapps Luciole/Firefox, launcher minimalista, btop/fastfetch e font cache."
  exit 0
fi

# 1. Verify Luciole and Firefox Pure desktop entries exist
LUCIOLE_DESKTOP=""
for f in /usr/share/applications/dev.noctalia.luciole.desktop /usr/share/applications/luciole.desktop; do
  if [[ -f "$f" ]]; then
    LUCIOLE_DESKTOP="$(basename "$f")"
    break
  fi
done
[[ -n "$LUCIOLE_DESKTOP" ]] || nox_die "Desktop entry do Luciole nao encontrado em /usr/share/applications/!"

FIREFOX_DESKTOP="firefox.desktop"
[[ -f "/usr/share/applications/${FIREFOX_DESKTOP}" ]] || nox_die "Desktop entry do Firefox Pure (/usr/share/applications/${FIREFOX_DESKTOP}) nao encontrado!"

# 2. Verify Qt darker palettes exist before referencing them
for v in 5 6; do
  [[ -f "/usr/share/qt${v}ct/colors/darker.conf" ]] \
    || nox_die "Paleta darker.conf do Qt${v} ausente!"
done

# 3. Install Project Nox Obsidian Purple identity assets, Firefox Pure dark defaults, GTK3/4, Qt5/6, btop, fastfetch & Noctalia configs
install -d -m 0755 \
  /usr/share/nox-archinstall/wallpapers \
  /usr/share/nox-archinstall/qt \
  /etc/skel/.config/gtk-3.0 \
  /etc/skel/.config/gtk-4.0 \
  /etc/skel/.config/qt5ct/colors \
  /etc/skel/.config/qt6ct/colors \
  /etc/skel/.config/kitty/themes \
  /etc/skel/.config/btop/themes \
  /etc/skel/.config/fastfetch \
  /etc/skel/.config/umbriel \
  /etc/skel/.config/noctalia/palettes

nox_atomic_install 0644 "${NOX_ROOT}/configs/wallpapers/obsidian-purple.png" /usr/share/nox-archinstall/wallpapers/obsidian-purple.png
if [[ -d /usr/lib/firefox/browser/defaults/preferences ]]; then
  nox_atomic_install 0644 "${NOX_ROOT}/configs/firefox/nox-theme.js" /usr/lib/firefox/browser/defaults/preferences/nox-theme.js
fi

nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/settings.ini" /etc/skel/.config/gtk-3.0/settings.ini
nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/settings.ini" /etc/skel/.config/gtk-4.0/settings.ini
nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/gtk.css" /etc/skel/.config/gtk-3.0/gtk.css
nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/gtk.css" /etc/skel/.config/gtk-4.0/gtk.css
nox_atomic_install 0644 "${NOX_ROOT}/configs/qt/qt5ct.conf" /etc/skel/.config/qt5ct/qt5ct.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/qt/qt6ct.conf" /etc/skel/.config/qt6ct/qt6ct.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/btop/btop.conf" /etc/skel/.config/btop/btop.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/fastfetch/config.jsonc" /etc/skel/.config/fastfetch/config.jsonc
nox_atomic_install 0644 "${NOX_ROOT}/configs/noctalia/nox-launcher.toml" /etc/skel/.config/noctalia/nox-launcher.toml
nox_atomic_install 0644 "${NOX_ROOT}/configs/noctalia/nox-power.toml" /etc/skel/.config/noctalia/nox-power.toml
nox_atomic_install 0644 "${NOX_ROOT}/configs/noctalia/nox-theme.toml" /etc/skel/.config/noctalia/nox-theme.toml
nox_atomic_install 0644 "${NOX_ROOT}/configs/noctalia/palettes/ObsidianPurple.json" /etc/skel/.config/noctalia/palettes/ObsidianPurple.json
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-system-tools-list" "${NOX_LIBEXEC_DIR}/nox-system-tools-list"
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-system-tools-launch" "${NOX_LIBEXEC_DIR}/nox-system-tools-launch"

# Pre-render Noctalia builtin Obsidian Purple templates into /etc/skel + shared Qt fallback
install -d -m 0755 \
  /etc/skel/.config/qt5ct/colors \
  /etc/skel/.config/qt6ct/colors \
  /etc/skel/.config/kitty/themes \
  /etc/skel/.config/btop/themes \
  /etc/skel/.config/umbriel \
  /usr/share/nox-archinstall/qt

if command -v noctalia >/dev/null 2>&1; then
  noctalia theme --theme-json /etc/skel/.config/noctalia/palettes/ObsidianPurple.json --dark \
    -r /usr/share/noctalia/assets/templates/gtk/gtk3.css:/etc/skel/.config/gtk-3.0/noctalia.css \
    -r /usr/share/noctalia/assets/templates/gtk/gtk4.css:/etc/skel/.config/gtk-4.0/noctalia.css \
    -r /usr/share/noctalia/assets/templates/qt/qtct.conf:/etc/skel/.config/qt5ct/colors/noctalia.conf \
    -r /usr/share/noctalia/assets/templates/qt/qtct.conf:/etc/skel/.config/qt6ct/colors/noctalia.conf \
    -r /usr/share/noctalia/assets/templates/kitty/kitty.conf:/etc/skel/.config/kitty/themes/noctalia.conf \
    -r /usr/share/noctalia/assets/templates/btop/btop.theme:/etc/skel/.config/btop/themes/noctalia.theme \
    -r /usr/share/noctalia/assets/templates/umbriel/umbriel.toml:/etc/skel/.config/umbriel/noctalia.toml
  nox_atomic_install 0644 /etc/skel/.config/qt6ct/colors/noctalia.conf /usr/share/nox-archinstall/qt/obsidian-purple.conf
fi

# 3b. XDG mimeapps.list: Luciole (directories) + Firefox Pure (HTTP/HTTPS/HTML)
mkdir -p /etc/skel/.config
cat > /etc/skel/.config/mimeapps.list <<EOF
[Default Applications]
inode/directory=${LUCIOLE_DESKTOP}
x-scheme-handler/http=${FIREFOX_DESKTOP}
x-scheme-handler/https=${FIREFOX_DESKTOP}
x-scheme-handler/about=${FIREFOX_DESKTOP}
x-scheme-handler/unknown=${FIREFOX_DESKTOP}
text/html=${FIREFOX_DESKTOP}
application/xhtml+xml=${FIREFOX_DESKTOP}

[Added Associations]
inode/directory=${LUCIOLE_DESKTOP};
x-scheme-handler/http=${FIREFOX_DESKTOP};
x-scheme-handler/https=${FIREFOX_DESKTOP};
text/html=${FIREFOX_DESKTOP};
application/xhtml+xml=${FIREFOX_DESKTOP};
EOF

# 3c. Ensure Firefox Pure displays visually as "Firefox" if upstream desktop Name differs
install -d -m 0755 /etc/skel/.local /etc/skel/.local/share /etc/skel/.local/share/applications
ff_name="$(grep -m1 '^Name=' "/usr/share/applications/${FIREFOX_DESKTOP}" | cut -d= -f2- || true)"
if [[ -n "$ff_name" && "$ff_name" != "Firefox" ]]; then
  cp -f "/usr/share/applications/${FIREFOX_DESKTOP}" "/etc/skel/.local/share/applications/${FIREFOX_DESKTOP}"
  sed -i 's/^Name=.*/Name=Firefox/' "/etc/skel/.local/share/applications/${FIREFOX_DESKTOP}"
  chmod 0644 "/etc/skel/.local/share/applications/${FIREFOX_DESKTOP}"
else
  rm -f "/etc/skel/.local/share/applications/${FIREFOX_DESKTOP}"
fi

# 4. Install user session unit globally for umbriel-session.target
nox_atomic_install 0644 "${NOX_ROOT}/configs/systemd/nox-session-setup.service" \
  /etc/systemd/user/nox-session-setup.service
mkdir -p /etc/systemd/user/umbriel-session.target.wants
ln -sf /etc/systemd/user/nox-session-setup.service \
  /etc/systemd/user/umbriel-session.target.wants/nox-session-setup.service

# 5. Apply to all existing human users
while IFS=: read -r uname uid gid uhome _shell; do
  [[ -n "$uname" && -d "$uhome" ]] || continue
  install -d -m 0755 -o "$uid" -g "$gid" "${uhome}/.config"
  for rel in \
    gtk-3.0/settings.ini \
    gtk-3.0/gtk.css \
    gtk-3.0/noctalia.css \
    gtk-4.0/settings.ini \
    gtk-4.0/gtk.css \
    gtk-4.0/noctalia.css \
    qt5ct/qt5ct.conf \
    qt5ct/colors/noctalia.conf \
    qt6ct/qt6ct.conf \
    qt6ct/colors/noctalia.conf \
    kitty/themes/noctalia.conf \
    btop/btop.conf \
    btop/themes/noctalia.theme \
    fastfetch/config.jsonc \
    umbriel/noctalia.toml \
    noctalia/nox-launcher.toml \
    noctalia/nox-power.toml \
    noctalia/nox-theme.toml \
    noctalia/palettes/ObsidianPurple.json \
    mimeapps.list; do
    [[ -f "/etc/skel/.config/${rel}" ]] || continue
    install -d -m 0755 -o "$uid" -g "$gid" "${uhome}/.config/$(dirname "$rel")"
    nox_atomic_install 0644 "/etc/skel/.config/${rel}" "${uhome}/.config/${rel}"
    chown "${uid}:${gid}" "${uhome}/.config/${rel}"
  done
  for qtver in 5 6; do
    if [[ -f "${uhome}/.config/qt${qtver}ct/colors/noctalia.conf" && -f "${uhome}/.config/qt${qtver}ct/qt${qtver}ct.conf" ]]; then
      sed -i "s|^color_scheme_path=.*|color_scheme_path=${uhome}/.config/qt${qtver}ct/colors/noctalia.conf|" "${uhome}/.config/qt${qtver}ct/qt${qtver}ct.conf"
      chown "${uid}:${gid}" "${uhome}/.config/qt${qtver}ct/qt${qtver}ct.conf"
    fi
  done

  su -s /usr/bin/bash "$uname" -c "HOME='${uhome}' XDG_CONFIG_HOME='${uhome}/.config' xdg-mime default '${LUCIOLE_DESKTOP}' inode/directory && HOME='${uhome}' XDG_CONFIG_HOME='${uhome}/.config' xdg-mime default '${FIREFOX_DESKTOP}' x-scheme-handler/http x-scheme-handler/https text/html application/xhtml+xml" >/dev/null 2>&1 || true
done < <(nox_list_human_users)

# 5b. Sync minimalist Noctalia launcher XDG user overlays (called again in 60-snapshots after limine-snapper-sync install)
nox_sync_hidden_tech_desktops

# 6. Rebuild font cache
fc-cache -f >/dev/null 2>&1 || fc-cache -f
nox_info "Tema escuro, Luciole + Firefox Pure XDG, launcher minimalista Noctalia, btop/fastfetch e font cache configurados."
