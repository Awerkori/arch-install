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
# Skip pre/post snap-pac hooks during initial installation before root snapper config and /etc/snap-pac.ini exist.
SNAP_PAC_SKIP=y pacman -S --needed --noconfirm snapper snap-pac limine-snapper-sync inotify-tools xxhash

BOOT_MP="/boot"
if ! findmnt /boot >/dev/null 2>&1 && findmnt /efi >/dev/null 2>&1; then
  BOOT_MP="/efi"
fi

ROOT_FSTYPE="$(findmnt -no FSTYPE / || true)"
[[ "$ROOT_FSTYPE" == "btrfs" ]] || nox_die "Sistema de arquivos raiz '/' nao e Btrfs (obtido: ${ROOT_FSTYPE})."

# 1. Ensure 'root' Snapper config exists and /.snapshots is mounted on top-level @.snapshots subvolume
if ! snapper --no-dbus -c root get-config >/dev/null 2>&1; then
  nox_info "Criando configuracao Snapper 'root'..."
  if [[ -d /.snapshots ]] && mountpoint -q /.snapshots; then
    SNAP_DEV="$(findmnt -no SOURCE /.snapshots | sed 's/\[.*\]//')"
    SNAP_SUBVOL="$(findmnt -no OPTIONS /.snapshots | tr ',' '\n' | sed -n 's/^subvol=//p' | head -n1)"
    SNAP_SUBVOL="${SNAP_SUBVOL:-/@.snapshots}"
    umount /.snapshots
    rmdir /.snapshots 2>/dev/null || true
    snapper --no-dbus -c root create-config /
    btrfs subvolume delete /.snapshots >/dev/null 2>&1 || true
    mkdir -p /.snapshots
    SNAP_UUID="$(blkid -s UUID -o value "$SNAP_DEV" 2>/dev/null || true)"
    if [[ "$SNAP_SUBVOL" =~ ^/?@\.snapshots$ ]] && [[ -n "$SNAP_UUID" ]] && ! awk '$2 == "/.snapshots" {found=1} END{exit !found}' /etc/fstab 2>/dev/null; then
      printf 'UUID=%s\t/.snapshots\tbtrfs\trw,noatime,compress=zstd:3,discard=async,space_cache=v2,subvol=/@.snapshots\t0 0\n' "$SNAP_UUID" >>/etc/fstab
    fi
    mount /.snapshots 2>/dev/null || mount -o "subvol=${SNAP_SUBVOL}" "$SNAP_DEV" /.snapshots
  else
    snapper --no-dbus -c root create-config /
    btrfs subvolume delete /.snapshots >/dev/null 2>&1 || mkdir -p /.snapshots
    mkdir -p /.snapshots
    ROOT_DEV="$(findmnt -no SOURCE / | sed 's/\[.*\]//')"
    ROOT_UUID="$(blkid -s UUID -o value "$ROOT_DEV" 2>/dev/null || true)"
    TOP_MNT="$(mktemp -d)"
    cleanup_top_mnt() {
      umount "$TOP_MNT" 2>/dev/null || true
      rmdir "$TOP_MNT" 2>/dev/null || true
    }
    trap cleanup_top_mnt EXIT INT TERM HUP
    if [[ -n "$ROOT_DEV" ]] && mount -o subvolid=5 "$ROOT_DEV" "$TOP_MNT" 2>/dev/null; then
      [[ -e "${TOP_MNT}/@.snapshots" ]] || btrfs subvolume create "${TOP_MNT}/@.snapshots"
      umount "$TOP_MNT"
    fi
    rmdir "$TOP_MNT" 2>/dev/null || true
    trap - EXIT INT TERM HUP
    if ! awk '$2 == "/.snapshots" {found=1} END{exit !found}' /etc/fstab 2>/dev/null && [[ -n "$ROOT_UUID" ]]; then
      printf 'UUID=%s\t/.snapshots\tbtrfs\trw,noatime,compress=zstd:3,ssd,discard=async,space_cache=v2,subvol=/@.snapshots\t0 0\n' "$ROOT_UUID" >>/etc/fstab
    fi
    mount /.snapshots 2>/dev/null || { [[ -n "$ROOT_DEV" ]] && mount -o "subvol=/@.snapshots" "$ROOT_DEV" /.snapshots; }
  fi
fi

# Inform limine-snapper-sync when /.snapshots is backed by top-level /@.snapshots
if findmnt -no OPTIONS /.snapshots 2>/dev/null | tr ',' '\n' | grep -qE '^subvol=/?@\.snapshots$'; then
  sed -i '/^ROOT_SNAPSHOTS_PATH=/d' /etc/default/limine
  printf 'ROOT_SNAPSHOTS_PATH="/@.snapshots"\n' >>/etc/default/limine
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

# 6. Install immediate post-transaction cleanup helper & hook (runs strictly AFTER zz-snap-pac-post.hook: zzz- > zz-)
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-snapper-cleanup" "${NOX_LIBEXEC_DIR}/nox-snapper-cleanup"
rm -f /etc/pacman.d/hooks/zz-99-nox-snapper-cleanup.hook
nox_atomic_install 0644 "${NOX_ROOT}/configs/pacman-hooks/zzz-99-nox-snapper-cleanup.hook" \
  /etc/pacman.d/hooks/zzz-99-nox-snapper-cleanup.hook

# 7. Enable limine-snapper-sync service (uses /etc/default/limine + 10-limine-snapper-sync snapper plugin)
systemctl enable limine-snapper-sync.service

# Ensure //Snapshots placeholder exists under OS block in limine.conf if not added yet
if [[ -f "${BOOT_MP}/limine.conf" ]] && ! grep -qE '^[[:space:]]*/+Snapshots' "${BOOT_MP}/limine.conf"; then
  printf '  //Snapshots\n' >>"${BOOT_MP}/limine.conf"
  command -v limine-enroll-config >/dev/null 2>&1 && limine-enroll-config >/dev/null 2>&1 || true
  [[ -x /etc/boot/hooks/post.d/95-nox-sbctl-fallback ]] && /etc/boot/hooks/post.d/95-nox-sbctl-fallback >/dev/null 2>&1 || true
fi

# 8. Prune any excess initial snapshots left by base installation
"${NOX_LIBEXEC_DIR}/nox-snapper-cleanup" || true

# 9. Sync Limine snapshot entries cleanly offline/target & keep config enrollment + EFI signatures updated
limine-snapper-sync || nox_warn "limine-snapper-sync retornou aviso na sincronizacao inicial (sem snapshots iniciais ainda)."
command -v limine-enroll-config >/dev/null 2>&1 && limine-enroll-config >/dev/null 2>&1 || true
[[ -x /etc/boot/hooks/post.d/95-nox-sbctl-fallback ]] && /etc/boot/hooks/post.d/95-nox-sbctl-fallback >/dev/null 2>&1 || true

# 10. Sync launcher XDG user overlays now that limine-snapper-restore.desktop is installed
nox_sync_hidden_tech_desktops

nox_info "Politica Snapper root (max 2), snap-pac e limine-snapper-sync configurados."
