#!/usr/bin/env bash
# Stage 53: Dark mode (GTK3/4, Qt5/6), XDG Luciole directory association, fonts cache, user session unit.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 53-appearance: configuraria GTK/Qt dark mode, mimeapps Luciole e font cache."
  exit 0
fi

# 1. Verify Luciole desktop entry exists
LUCIOLE_DESKTOP=""
for f in /usr/share/applications/dev.noctalia.luciole.desktop /usr/share/applications/luciole.desktop; do
  if [[ -f "$f" ]]; then
    LUCIOLE_DESKTOP="$(basename "$f")"
    break
  fi
done
[[ -n "$LUCIOLE_DESKTOP" ]] || nox_die "Desktop entry do Luciole nao encontrado em /usr/share/applications/!"

# 2. Verify Qt darker palettes exist before referencing them
for v in 5 6; do
  [[ -f "/usr/share/qt${v}ct/colors/darker.conf" ]] \
    || nox_die "Paleta darker.conf do Qt${v} ausente!"
done

# 3. Install GTK3, GTK4, Qt5ct, Qt6ct, and XDG mimeapps in /etc/skel
nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/settings.ini" /etc/skel/.config/gtk-3.0/settings.ini
nox_atomic_install 0644 "${NOX_ROOT}/configs/gtk/settings.ini" /etc/skel/.config/gtk-4.0/settings.ini
nox_atomic_install 0644 "${NOX_ROOT}/configs/qt/qt5ct.conf" /etc/skel/.config/qt5ct/qt5ct.conf
nox_atomic_install 0644 "${NOX_ROOT}/configs/qt/qt6ct.conf" /etc/skel/.config/qt6ct/qt6ct.conf

mkdir -p /etc/skel/.config
cat > /etc/skel/.config/mimeapps.list <<EOF
[Default Applications]
inode/directory=${LUCIOLE_DESKTOP}

[Added Associations]
inode/directory=${LUCIOLE_DESKTOP};
EOF

# 4. Install user session unit globally for umbriel-session.target
nox_atomic_install 0644 "${NOX_ROOT}/configs/systemd/nox-session-setup.service" \
  /etc/systemd/user/nox-session-setup.service
mkdir -p /etc/systemd/user/umbriel-session.target.wants
ln -sf /etc/systemd/user/nox-session-setup.service \
  /etc/systemd/user/umbriel-session.target.wants/nox-session-setup.service

# 5. Apply to all existing human users
while IFS=: read -r uname uid gid uhome _shell; do
  [[ -n "$uname" && -d "$uhome" ]] || continue
  for rel in gtk-3.0/settings.ini gtk-4.0/settings.ini qt5ct/qt5ct.conf qt6ct/qt6ct.conf mimeapps.list; do
    install -d -m 0755 -o "$uid" -g "$gid" "${uhome}/.config/$(dirname "$rel")"
    nox_atomic_install 0644 "/etc/skel/.config/${rel}" "${uhome}/.config/${rel}"
    chown "${uid}:${gid}" "${uhome}/.config/${rel}"
  done
  su -s /usr/bin/bash "$uname" -c "HOME='${uhome}' XDG_CONFIG_HOME='${uhome}/.config' xdg-mime default '${LUCIOLE_DESKTOP}' inode/directory" >/dev/null 2>&1 || true
done < <(nox_list_human_users)

# 6. Rebuild font cache
fc-cache -f >/dev/null 2>&1 || fc-cache -f
nox_info "Tema escuro, Luciole XDG (${LUCIOLE_DESKTOP}), font cache e unit de sessao configurados."
