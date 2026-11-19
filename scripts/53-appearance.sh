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

# 3. Install Project Nox Obsidian Purple identity assets, fonts, icons, wallpapers, greeter assets, bundled plugins, Firefox Pure dark defaults, GTK3/4, Qt5/6, btop, fastfetch & Noctalia configs
install -d -m 0755 \
  /usr/share/nox-archinstall/wallpapers \
  /usr/share/nox-archinstall/icons \
  /usr/share/nox-archinstall/greeter-assets \
  /usr/share/nox-archinstall/noctalia-plugins \
  /usr/share/nox-archinstall/firefox \
  /usr/share/nox-archinstall/qt \
  /usr/share/fonts/nox \
  /etc/skel/.config/gtk-3.0 \
  /etc/skel/.config/gtk-4.0 \
  /etc/skel/.config/qt5ct/colors \
  /etc/skel/.config/qt6ct/colors \
  /etc/skel/.config/kitty/themes \
  /etc/skel/.config/btop/themes \
  /etc/skel/.config/fastfetch \
  /etc/skel/.config/umbriel \
  /etc/skel/.config/topgrade.d \
  /etc/skel/.config/noctalia/palettes

# Wallpapers (static masters + animated runtime WebM loops)
for wp in \
  obsidian-purple.png \
  nox-g5.png \
  nox-g5-runtime.webm \
  nox-aoc.png \
  nox-aoc-runtime.webm \
  nox-lockscreen.png \
  nox-greeter.png \
  nox-limine.png; do
  if [[ -f "${NOX_ROOT}/configs/wallpapers/${wp}" ]]; then
    nox_atomic_install 0644 "${NOX_ROOT}/configs/wallpapers/${wp}" "/usr/share/nox-archinstall/wallpapers/${wp}"
  fi
done

# Emblems & animated lockscreen GIF sticker
for ic in \
  nox-emblem.png \
  nox-lockscreen-emblem.gif \
  emblema-mestre-1254.png; do
  if [[ -f "${NOX_ROOT}/configs/icons/${ic}" ]]; then
    nox_atomic_install 0644 "${NOX_ROOT}/configs/icons/${ic}" "/usr/share/nox-archinstall/icons/${ic}"
  fi
done

# OFL Fonts (Outfit + Plus Jakarta Sans)
if [[ -d "${NOX_ROOT}/configs/fonts" ]]; then
  for ff in "${NOX_ROOT}/configs/fonts"/*; do
    [[ -f "$ff" ]] || continue
    nox_atomic_install 0644 "$ff" "/usr/share/fonts/nox/$(basename "$ff")"
  done
fi

# Custom Greeter assets bundle (emblem SVG + fonts)
if [[ -f "${NOX_ROOT}/configs/greeter/assets/noctalia.svg" ]]; then
  nox_atomic_install 0644 "${NOX_ROOT}/configs/greeter/assets/noctalia.svg" /usr/share/nox-archinstall/greeter-assets/noctalia.svg
fi
if [[ -d /usr/share/noctalia-greeter/assets/fonts ]]; then
  ln -sfn /usr/share/noctalia-greeter/assets/fonts /usr/share/nox-archinstall/greeter-assets/fonts
fi

# Bundled official Noctalia plugins (offline-ready mpvpaper)
if [[ -d "${NOX_ROOT}/configs/noctalia/plugins/mpvpaper" ]]; then
  rm -rf /usr/share/nox-archinstall/noctalia-plugins/mpvpaper
  cp -a "${NOX_ROOT}/configs/noctalia/plugins/mpvpaper" /usr/share/nox-archinstall/noctalia-plugins/mpvpaper
  chmod -R a+rX /usr/share/nox-archinstall/noctalia-plugins/mpvpaper
fi

# Firefox Pure dark defaults + userChrome/userContent Obsidian Purple CSS
if [[ -d /usr/lib/firefox/browser/defaults/preferences ]]; then
  nox_atomic_install 0644 "${NOX_ROOT}/configs/firefox/nox-theme.js" /usr/lib/firefox/browser/defaults/preferences/nox-theme.js
fi
nox_atomic_install 0644 "${NOX_ROOT}/configs/firefox/userChrome.css" /usr/share/nox-archinstall/firefox/userChrome.css
nox_atomic_install 0644 "${NOX_ROOT}/configs/firefox/userContent.css" /usr/share/nox-archinstall/firefox/userContent.css

nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/settings.ini" /etc/skel/.config/gtk-3.0/settings.ini
nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/settings.ini" /etc/skel/.config/gtk-4.0/settings.ini
nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/gtk.css" /etc/skel/.config/gtk-3.0/gtk.css
nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/gtk.css" /etc/skel/.config/gtk-4.0/gtk.css
nox_atomic_install 0644 "${NOX_ROOT}/configs/qt/qt5ct.conf" /etc/skel/.config/qt5ct/qt5ct.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/qt/qt6ct.conf" /etc/skel/.config/qt6ct/qt6ct.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/btop/btop.conf" /etc/skel/.config/btop/btop.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/fastfetch/config.jsonc" /etc/skel/.config/fastfetch/config.jsonc
if [[ -f "${NOX_ROOT}/configs/fastfetch/nox-logo.txt" ]]; then
  nox_atomic_install 0644 "${NOX_ROOT}/configs/fastfetch/nox-logo.txt" /etc/skel/.config/fastfetch/nox-logo.txt
fi
nox_atomic_install 0644 "${NOX_ROOT}/configs/noctalia/nox-launcher.toml" /etc/skel/.config/noctalia/nox-launcher.toml
nox_atomic_install 0644 "${NOX_ROOT}/configs/noctalia/nox-power.toml" /etc/skel/.config/noctalia/nox-power.toml
nox_atomic_install 0644 "${NOX_ROOT}/configs/noctalia/nox-theme.toml" /etc/skel/.config/noctalia/nox-theme.toml
nox_atomic_install 0644 "${NOX_ROOT}/configs/noctalia/palettes/ObsidianPurple.json" /etc/skel/.config/noctalia/palettes/ObsidianPurple.json
for tgcfg in 50-nox-arch.toml 98-disable-self-update.toml 99-disable-containers.toml; do
  if [[ -f "${NOX_ROOT}/configs/topgrade/${tgcfg}" ]]; then
    nox_atomic_install 0644 "${NOX_ROOT}/configs/topgrade/${tgcfg}" "/etc/skel/.config/topgrade.d/${tgcfg}"
  fi
done
if [[ -f "${NOX_ROOT}/configs/bin/nox-topgrade" ]]; then
  nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-topgrade" /usr/local/bin/topgrade
fi
if [[ -x "${NOX_LIBEXEC_DIR}/nox-noctalia-layout" ]]; then
  "${NOX_LIBEXEC_DIR}/nox-noctalia-layout" \
    --lockscreen-out /etc/skel/.config/noctalia/nox-lockscreen-widgets.toml \
    --mpvpaper-out none >/dev/null 2>&1 || true
fi
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
    fastfetch/nox-logo.txt \
    umbriel/noctalia.toml \
    noctalia/nox-launcher.toml \
    noctalia/nox-power.toml \
    noctalia/nox-theme.toml \
    noctalia/nox-lockscreen-widgets.toml \
    noctalia/palettes/ObsidianPurple.json \
    mimeapps.list; do
    [[ -f "/etc/skel/.config/${rel}" ]] || continue
    install -d -m 0755 -o "$uid" -g "$gid" "${uhome}/.config/$(dirname "$rel")"
    nox_atomic_install 0644 "/etc/skel/.config/${rel}" "${uhome}/.config/${rel}"
    chown "${uid}:${gid}" "${uhome}/.config/${rel}"
  done
  install -d -m 0755 -o "$uid" -g "$gid" "${uhome}/.config/topgrade.d"
  for tgcfg in 50-nox-arch.toml 98-disable-self-update.toml 99-disable-containers.toml; do
    if [[ -f "/etc/skel/.config/topgrade.d/${tgcfg}" && ! -f "${uhome}/.config/topgrade.d/${tgcfg}" ]]; then
      nox_atomic_install 0644 "/etc/skel/.config/topgrade.d/${tgcfg}" "${uhome}/.config/topgrade.d/${tgcfg}"
      chown "${uid}:${gid}" "${uhome}/.config/topgrade.d/${tgcfg}"
    fi
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
