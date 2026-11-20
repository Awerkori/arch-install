#!/usr/bin/env bash
# Stage 20: Install linux-cachyos (+ headers), remove bootstrap kernel, configure Limine + limine-mkinitcpio-hook.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 20-cachyos-kernel: instalaria linux-cachyos + headers, removeria linux-zen e configuraria Limine."
  exit 0
fi

nox_wait_pacman_lock

BOOT_MP="/boot"
if ! findmnt /boot >/dev/null 2>&1 && findmnt /efi >/dev/null 2>&1; then
  BOOT_MP="/efi"
fi

# 1. Install linux-cachyos, headers, firmware, microcode, Limine and limine-mkinitcpio-hook
nox_info "Instalando linux-cachyos, headers, limine e limine-mkinitcpio-hook..."
pacman -S --needed --noconfirm \
  linux-cachyos linux-cachyos-headers amd-ucode linux-firmware \
  limine efibootmgr limine-mkinitcpio-hook sbctl xxhash

# Remove GRUB packages explicitly if somehow present
for gpkg in grub grub-btrfs os-prober; do
  if pacman -Qq "$gpkg" >/dev/null 2>&1; then
    pacman -Rns --noconfirm "$gpkg" || true
  fi
done

# 2. Ensure reproducible zstd initramfs and btrfs-overlayfs hook in /etc/mkinitcpio.conf
python3 - /etc/mkinitcpio.conf <<'PY'
import os, re, sys
p = sys.argv[1]
txt = open(p, "r", encoding="utf-8").read()
lines = txt.splitlines()
out = []
overlay_hook = "sd-btrfs-overlayfs"
hooks_seen = False
comp_seen = False

# Inspect HOOKS first to pick udev vs systemd variant
for line in lines:
    m = re.match(r'^\s*HOOKS=\((.*)\)\s*$', line)
    if m:
        tokens = m.group(1).split()
        overlay_hook = "sd-btrfs-overlayfs" if "systemd" in tokens else "btrfs-overlayfs"
        break

for line in lines:
    m_comp = re.match(r'^\s*#?\s*COMPRESSION=', line)
    if m_comp and not comp_seen:
        out.append('COMPRESSION="zstd"')
        comp_seen = True
        continue
    m_hooks = re.match(r'^(\s*HOOKS=\()(.*)(\)\s*)$', line)
    if m_hooks and not hooks_seen:
        tokens = m_hooks.group(2).split()
        tokens = [t for t in tokens if t not in ("btrfs-overlayfs", "sd-btrfs-overlayfs")]
        if "filesystems" in tokens:
            idx = tokens.index("filesystems") + 1
            tokens.insert(idx, overlay_hook)
        else:
            tokens.append(overlay_hook)
        out.append(f"{m_hooks.group(1)}{' '.join(tokens)}{m_hooks.group(3)}")
        hooks_seen = True
        continue
    out.append(line)

if not comp_seen:
    out.append('COMPRESSION="zstd"')

tmp = p + ".nox.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write("\n".join(out) + "\n")
os.replace(tmp, p)
PY

# 3. Clean up bootstrap kernels and Archinstall's legacy Limine artifacts
for old_k in linux-zen linux-zen-headers linux linux-headers linux-lts linux-lts-headers; do
  if pacman -Qq "$old_k" >/dev/null 2>&1; then
    nox_info "Removendo kernel temporario '$old_k' via pacman -Rns..."
    pacman -Rns --noconfirm "$old_k"
  fi
done

for p in /etc/mkinitcpio.d/*.preset; do
  [[ -e "$p" ]] || continue
  base="$(basename "$p" .preset)"
  if [[ "$base" != "linux-cachyos" ]] && ! pacman -Qq "$base" >/dev/null 2>&1; then
    nox_info "Removendo preset orfao: $p"
    rm -f "$p"
  fi
done

rm -f /etc/pacman.d/hooks/99-limine.hook
rm -rf "${BOOT_MP}/EFI/arch-limine"
rm -f "${BOOT_MP}/vmlinuz-linux-zen" "${BOOT_MP}"/initramfs-linux-zen*.img
rm -f \
  "${BOOT_MP}/EFI/limine/limine.conf" \
  "${BOOT_MP}/EFI/BOOT/limine.conf" \
  "${BOOT_MP}/boot/limine/limine.conf" \
  "${BOOT_MP}/boot/limine.conf" \
  "${BOOT_MP}/limine/limine.conf"

if [[ -d /sys/firmware/efi/efivars ]] && command -v efibootmgr >/dev/null 2>&1; then
  while IFS= read -r bnum; do
    [[ -n "$bnum" ]] || continue
    efibootmgr -b "$bnum" -B >/dev/null 2>&1 || true
  done < <(efibootmgr 2>/dev/null | sed -n 's/^Boot\([0-9A-Fa-f]\{4\}\)\**\s*Arch Linux Limine Bootloader.*/\1/p')
fi

# 4. Write /etc/kernel/cmdline and /etc/default/limine (single source of truth for Limine + Snapper sync)
ROOT_DEV="$(findmnt -no SOURCE / | sed 's/\[.*//')"
ROOT_UUID="$(blkid -s UUID -o value "$ROOT_DEV" || true)"
[[ -n "$ROOT_UUID" ]] || nox_die "Nao foi possivel obter UUID de '${ROOT_DEV}' para kernel cmdline do Limine."

CMDLINE_STR="root=UUID=${ROOT_UUID} rw rootflags=subvol=/@ rootfstype=btrfs quiet loglevel=3 systemd.show_status=auto rd.udev.log_level=3 amd_pstate=active amd_iommu=on iommu=pt zswap.enabled=0 nowatchdog"
install -d -m 0755 /etc/kernel /etc/default
printf '%s\n' "$CMDLINE_STR" >/etc/kernel/cmdline

cat >/etc/default/limine <<EOF
TARGET_OS_NAME="Arch Linux"
ESP_PATH="${BOOT_MP}"
FIND_BOOTLOADERS=no
BOOT_ORDER="*, *fallback, Snapshots"
ENABLE_SORT=no
ENABLE_VERIFICATION=yes
ENABLE_ENROLL_LIMINE_CONFIG=yes
SPACE_NUMBER=2
KERNEL_CMDLINE[default]=${CMDLINE_STR}

# limine-snapper-sync defaults
LIMIT_USAGE_PERCENT=85
MAX_SNAPSHOT_ENTRIES=auto
RESTORE_METHOD=replace
SET_SNAPSHOT_AS_DEFAULT=yes
SNAPSHOT_FORMAT_CHOICE=2
HASH_FUNCTION=xxhash
EOF
chmod 0644 /etc/default/limine

# 4b. Generate unique per-installation Secure Boot keys (never shipped in repo) & install boot/enroll hooks
if ! sbctl setup --print-state --json 2>/dev/null | grep -q '"installed": true'; then
  nox_info "Gerando chaves privadas individuais de Secure Boot (sbctl create-keys)..."
  sbctl create-keys
fi

install -d -m 0755 /etc/boot/hooks/pre.d /etc/boot/hooks/post.d
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-limine-normalize" "${NOX_LIBEXEC_DIR}/nox-limine-normalize"
nox_atomic_install 0755 "${NOX_ROOT}/configs/boot-hooks/05-nox-limine-naming-pre" /etc/boot/hooks/pre.d/05-nox-limine-naming-pre
[[ -e /etc/boot/hooks/pre.d/10-limine-reset-enroll ]] || ln -sf /usr/bin/limine-reset-enroll /etc/boot/hooks/pre.d/10-limine-reset-enroll
nox_atomic_install 0755 "${NOX_ROOT}/configs/boot-hooks/85-nox-limine-naming-post" /etc/boot/hooks/post.d/85-nox-limine-naming-post
[[ -e /etc/boot/hooks/post.d/90-limine-enroll-config ]] || ln -sf /usr/bin/limine-enroll-config /etc/boot/hooks/post.d/90-limine-enroll-config
nox_atomic_install 0755 "${NOX_ROOT}/configs/boot-hooks/95-nox-sbctl-fallback" /etc/boot/hooks/post.d/95-nox-sbctl-fallback
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-limine-integrity" "${NOX_LIBEXEC_DIR}/nox-limine-integrity"
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-limine-snapper-restore" /usr/local/bin/limine-snapper-restore
ln -sf /usr/local/bin/limine-snapper-restore /usr/local/bin/limine-snapper-sync
nox_atomic_install 0644 "${NOX_ROOT}/configs/systemd/nox-limine-integrity-shutdown.service" /etc/systemd/system/nox-limine-integrity-shutdown.service
systemctl enable nox-limine-integrity-shutdown.service
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-secureboot-enroll" /usr/local/bin/nox-secureboot-enroll
nox_atomic_install 0755 "${NOX_ROOT}/configs/bin/nox-secureboot-verify" /usr/local/bin/nox-secureboot-verify

# Ensure Limine Obsidian Purple wallpaper is present on ESP before limine-update / enroll
if [[ -f "${NOX_ROOT}/configs/wallpapers/nox-limine.png" ]]; then
  nox_atomic_install 0644 "${NOX_ROOT}/configs/wallpapers/nox-limine.png" "${BOOT_MP}/nox-limine-wallpaper.png"
fi

# Ensure /boot/limine.conf starts clean with 5s unattended auto-boot targeting Arch Linux/Project Nox
cat >"${BOOT_MP}/limine.conf" <<'EOF'
timeout: 5
default_entry: Arch Linux/Project Nox
remember_last_entry: no
EOF

# 5. Deploy Limine EFI binaries & register NVRAM + fallback
nox_info "Instalando Limine EFI em ${BOOT_MP} (com fallback BOOTX64.EFI)..."
if [[ -d /sys/firmware/efi ]]; then
  limine-install --fallback
else
  limine-install --skip-uefi
fi

# 6. Build initramfs with btrfs-overlayfs and register linux-cachyos in /boot/limine.conf (hooks normalize Project Nox + enroll + sign)
nox_info "Executando limine-update para gerar initramfs e entradas linux-cachyos..."
limine-update

# Enforce normalized header & Project Nox visual title idempotently, then re-enroll if needed
ESP_PATH="${BOOT_MP}" "${NOX_LIBEXEC_DIR}/nox-limine-normalize" --post
limine-enroll-config || true
/etc/boot/hooks/post.d/95-nox-sbctl-fallback || true

# Guarantee EFI binaries are enrolled + signed cleanly
if [[ -d /sys/firmware/efi ]]; then
  /usr/local/bin/nox-secureboot-verify || nox_die "Falha na verificacao de assinatura/checksum Limine+sbctl."
fi

# 7. Strict verification of Limine binaries & config
for f in "${BOOT_MP}/EFI/limine/limine_x64.efi" "${BOOT_MP}/EFI/BOOT/BOOTX64.EFI" "${BOOT_MP}/limine.conf"; do
  [[ -s "$f" ]] || nox_die "Arquivo obrigatorio Limine ausente ou vazio: $f"
done

grep -q 'kernel-id=linux-cachyos' "${BOOT_MP}/limine.conf" || nox_die "${BOOT_MP}/limine.conf nao contem kernel-id=linux-cachyos!"
grep -Eq '^[[:space:]]*//Project Nox$' "${BOOT_MP}/limine.conf" || nox_die "${BOOT_MP}/limine.conf nao contem entrada visual //Project Nox!"
grep -qx 'default_entry: Arch Linux/Project Nox' "${BOOT_MP}/limine.conf" || nox_die "${BOOT_MP}/limine.conf nao aponta default_entry para Arch Linux/Project Nox!"
grep -qx 'timeout: 5' "${BOOT_MP}/limine.conf" || nox_die "${BOOT_MP}/limine.conf nao define timeout: 5!"
grep -qx 'remember_last_entry: no' "${BOOT_MP}/limine.conf" || nox_die "${BOOT_MP}/limine.conf nao define remember_last_entry: no!"
if grep -q 'linux-zen' "${BOOT_MP}/limine.conf"; then
  nox_die "${BOOT_MP}/limine.conf ainda contem entrada residual de linux-zen!"
fi

nox_info "Kernel unico linux-cachyos e Limine EFI validados."
