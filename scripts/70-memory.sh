#!/usr/bin/env bash
# Stage 70: Unified ZRAM (cachyos-settings), dedicated Btrfs @swap swapfile (pri=10), OOMD protection.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 70-memory: configuraria ZRAM unica, subvolume @swap e protecao OOMD."
  exit 0
fi

# 1. Remove Archinstall's capped /etc/systemd/zram-generator.conf if present so cachyos-settings (zram-size=ram, zstd, prio=100) owns ZRAM cleanly without duplication
if [[ -f /etc/systemd/zram-generator.conf ]]; then
  if grep -q 'zram-size' /etc/systemd/zram-generator.conf; then
    nox_info "Removendo /etc/systemd/zram-generator.conf legado do Archinstall para unificar com cachyos-settings."
    rm -f /etc/systemd/zram-generator.conf
  fi
fi

# 2. Calculate proportional or physical swapfile size in dedicated @swap subvolume (outside @ and @.snapshots)
RAM_KIB="$(awk '/^MemTotal:/ {print $2}' /proc/meminfo)"
RAM_GIB=$(( (RAM_KIB + 524288) / 1048576 ))
ROOT_AVAIL_GIB=$(( $(df -BG --output=avail / | awk 'NR==2 {gsub(/G/,""); print $1}') ))

SWAP_SIZE_G=0
if (( RAM_GIB >= 24 && ROOT_AVAIL_GIB >= 64 )); then
  SWAP_SIZE_G=32
elif (( ROOT_AVAIL_GIB >= 20 )); then
  # VM / constrained disk proportional swapfile (e.g. 2G-4G)
  SWAP_SIZE_G=2
fi

if (( SWAP_SIZE_G > 0 )); then
  ROOT_SRC="$(findmnt -no SOURCE /)"
  ROOT_DEV="${ROOT_SRC%%\[*}"
  TOP_MNT="/var/tmp/nox-btrfs-top.$$"
  mkdir -p "$TOP_MNT" /nox-swap
  chmod 700 /nox-swap

  mount -t btrfs -o subvolid=5 "$ROOT_DEV" "$TOP_MNT"
  if [[ ! -d "${TOP_MNT}/@swap" ]]; then
    nox_info "Criando subvolume Btrfs dedicado @swap..."
    btrfs subvolume create "${TOP_MNT}/@swap"
  fi
  umount "$TOP_MNT"
  rmdir "$TOP_MNT"

  if ! mountpoint -q /nox-swap; then
    mount -t btrfs -o subvol=@swap,noatime "$ROOT_DEV" /nox-swap
  fi
  chmod 700 /nox-swap

  if [[ ! -f /nox-swap/swapfile ]]; then
    nox_info "Criando swapfile Btrfs de ${SWAP_SIZE_G}G em /nox-swap/swapfile (btrfs filesystem mkswapfile)..."
    btrfs filesystem mkswapfile --size "${SWAP_SIZE_G}g" --uuid clear /nox-swap/swapfile
  fi

  # Ensure /etc/fstab has @swap subvolume mount + swapfile pri=10 (idempotent)
  # Note: Btrfs superblock mount options (compress=zstd:3) are filesystem-wide from first mount (/);
  # NOCOW and no-compression on /nox-swap/swapfile are enforced per-inode (+C) by btrfs filesystem mkswapfile.
  UUID="$(blkid -s UUID -o value "$ROOT_DEV")"
  touch /etc/fstab
  if ! grep -qE '[[:space:]]/nox-swap[[:space:]]' /etc/fstab; then
    printf 'UUID=%s /nox-swap btrfs rw,noatime,subvol=/@swap 0 0\n' "$UUID" >> /etc/fstab
  fi
  if ! grep -qF '/nox-swap/swapfile ' /etc/fstab; then
    printf '/nox-swap/swapfile none swap defaults,pri=10 0 0\n' >> /etc/fstab
  fi

  # Unmount temporary chroot mountpoint so post-command genfstab() will not emit duplicate /nox-swap lines
  umount /nox-swap || true
else
  nox_warn "Espaco insuficiente (${ROOT_AVAIL_GIB}G) para swapfile Btrfs; mantendo apenas ZRAM."
fi

# 3. systemd-oomd protection for real human user slices (without disabling systemd-oomd globally)
while IFS=: read -r uname uid _gid _home _shell; do
  [[ -n "$uname" ]] || continue
  slice_dir="/etc/systemd/system/user-${uid}.slice.d"
  mkdir -p "$slice_dir"
  cat > "${slice_dir}/90-oom-protection.conf" <<'EOF'
[Slice]
ManagedOOMSwap=auto
ManagedOOMMemoryPressure=auto
EOF
  chmod 0644 "${slice_dir}/90-oom-protection.conf"
done < <(nox_list_human_users)

nox_info "Memoria ZRAM (cachyos-settings), swapfile @swap (${SWAP_SIZE_G}G pri=10) e protecao OOMD configurados."
