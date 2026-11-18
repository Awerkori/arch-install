#!/usr/bin/env bash
# Stage 60: Btrfs Snapper (root only, max 2 PRE+POST), snap-pac, limine-snapper-sync, immediate cleanup hook.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 60-snapshots: configuraria Snapper root (max 2), snap-pac e limine-snapper-sync."
  exit 0
fi

nox_wait_pacman_lock
pacman -S --needed --noconfirm snapper snap-pac limine-snapper-sync inotify-tools xxhash

BOOT_MP="/boot"
if ! findmnt /boot >/dev/null 2>&1 && findmnt /efi >/dev/null 2>&1; then
  BOOT_MP="/efi"
fi

ROOT_FSTYPE="$(findmnt -no FSTYPE / || true)"
[[ "$ROOT_FSTYPE" == "btrfs" ]] || nox_die "Sistema de arquivos raiz '/' nao e Btrfs (obtido: ${ROOT_FSTYPE})."

# 1. Ensure 'root' Snapper config exists without recreating over an existing one
if ! snapper --no-dbus -c root get-config >/dev/null 2>&1; then
  nox_info "Criando configuracao Snapper 'root'..."
  if [[ -d /.snapshots ]] && mountpoint -q /.snapshots; then
    umount /.snapshots
    rmdir /.snapshots 2>/dev/null || true
    snapper --no-dbus -c root create-config /
    btrfs subvolume delete /.snapshots >/dev/null 2>&1 || true
    mkdir -p /.snapshots
    mount /.snapshots || true
  else
    snapper --no-dbus -c root create-config /
  fi
fi

# 2. Enforce retention policy on root: max 2 number snapshots (PRE+POST), no timeline
snapper --no-dbus -c root set-config \
  NUMBER_CLEANUP=yes \
  NUMBER_MIN_AGE=0 \
  NUMBER_LIMIT=2 \
  NUMBER_LIMIT_IMPORTANT=0 \
  EMPTY_PRE_POST_CLEANUP=no \
  TIMELINE_CREATE=no \
  TIMELINE_CLEANUP=no

# 3. Disable home automatic snapshots if archinstall created 'home' config
if snapper --no-dbus -c home get-config >/dev/null 2>&1; then
  snapper --no-dbus -c home set-config \
    TIMELINE_CREATE=no \
    TIMELINE_CLEANUP=no \
    NUMBER_CLEANUP=yes \
    NUMBER_LIMIT=0 \
    NUMBER_LIMIT_IMPORTANT=0
  home_ids="$(snapper --no-dbus --jsonout -c home list | python3 -c 'import sys,json; d=json.load(sys.stdin); entries=d.get("home", d) if isinstance(d,dict) else d; print(" ".join(str(e["number"]) for e in entries if int(e.get("number",0))!=0))' || true)"
  if [[ -n "$home_ids" ]]; then
    # shellcheck disable=SC2086
    snapper --no-dbus -c home delete --sync $home_ids || true
  fi
fi

# 4. Disable timeline & boot timers; keep cleanup timer active
systemctl disable snapper-timeline.timer >/dev/null 2>&1 || true
systemctl mask snapper-timeline.timer >/dev/null 2>&1 || true
if systemctl list-unit-files snapper-boot.timer >/dev/null 2>&1; then
  systemctl disable snapper-boot.timer >/dev/null 2>&1 || true
  systemctl mask snapper-boot.timer >/dev/null 2>&1 || true
fi
systemctl enable snapper-cleanup.timer

# 5. Configure snap-pac exclusively for root
nox_atomic_install 0644 "${NOX_ROOT}/configs/snapper/snap-pac.ini" /etc/snap-pac.ini

# 6. Install immediate post-transaction cleanup helper & hook (runs after zz-snap-pac-post.hook)
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-snapper-cleanup" "${NOX_LIBEXEC_DIR}/nox-snapper-cleanup"
nox_atomic_install 0644 "${NOX_ROOT}/configs/pacman-hooks/zz-99-nox-snapper-cleanup.hook" \
  /etc/pacman.d/hooks/zz-99-nox-snapper-cleanup.hook

# 7. Enable limine-snapper-sync service (uses /etc/default/limine + 10-limine-snapper-sync snapper plugin)
systemctl enable limine-snapper-sync.service

# Ensure //Snapshots placeholder exists under OS block in limine.conf if not added yet
if [[ -f "${BOOT_MP}/limine.conf" ]] && ! grep -qE '^[[:space:]]*/+Snapshots' "${BOOT_MP}/limine.conf"; then
  printf '  //Snapshots\n' >> "${BOOT_MP}/limine.conf"
fi

# 8. Prune any excess initial snapshots left by base installation
"${NOX_LIBEXEC_DIR}/nox-snapper-cleanup" || true

# 9. Sync Limine snapshot entries cleanly offline/target
limine-snapper-sync || nox_warn "limine-snapper-sync retornou aviso na sincronizacao inicial (sem snapshots iniciais ainda)."

nox_info "Politica Snapper root (max 2), snap-pac e limine-snapper-sync configurados."
