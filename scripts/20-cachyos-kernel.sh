#!/usr/bin/env bash
# Stage 20: Install linux-cachyos (+ headers), remove bootstrap kernel, configure GRUB console menu.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 20-cachyos-kernel: instalaria linux-cachyos + headers, removeria linux-zen e regeneraria GRUB."
  exit 0
fi

nox_wait_pacman_lock

# 1. Install linux-cachyos, headers, amd-ucode, linux-firmware
nox_info "Instalando linux-cachyos e linux-cachyos-headers..."
pacman -S --needed --noconfirm linux-cachyos linux-cachyos-headers amd-ucode linux-firmware

# 2. Verify target kernel and initramfs files exist and are non-empty before removing bootstrap kernel
for f in /boot/vmlinuz-linux-cachyos /boot/initramfs-linux-cachyos.img /boot/amd-ucode.img; do
  [[ -s "$f" ]] || nox_die "Arquivo de boot obrigatorio ausente ou vazio: $f"
done

# 3. Cleanly remove temporary bootstrap kernels (linux-zen / linux) if present
for old_k in linux-zen linux-zen-headers linux linux-headers linux-lts linux-lts-headers; do
  if pacman -Qq "$old_k" >/dev/null 2>&1; then
    nox_info "Removendo kernel temporario '$old_k' via pacman -Rns..."
    pacman -Rns --noconfirm "$old_k"
  fi
done

# Clean up stale mkinitcpio presets belonging to removed kernels only
for p in /etc/mkinitcpio.d/*.preset; do
  [[ -e "$p" ]] || continue
  base="$(basename "$p" .preset)"
  if [[ "$base" != "linux-cachyos" ]] && ! pacman -Qq "$base" >/dev/null 2>&1; then
    nox_info "Removendo preset orfao: $p"
    rm -f "$p"
  fi
done

# 4. Configure GRUB robustly (visible 5s menu, console output to avoid multi-monitor blank screen)
if [[ -f /etc/default/grub ]]; then
  python3 - /etc/default/grub <<'PY'
import sys, re, os
p = sys.argv[1]
lines = open(p, "r", encoding="utf-8").read().splitlines()
desired = {
    "GRUB_TIMEOUT": "5",
    "GRUB_TIMEOUT_STYLE": "menu",
    "GRUB_TERMINAL_OUTPUT": "console",
}
out = []
seen = set()
for line in lines:
    m = re.match(r'^\s*#?\s*([A-Z0-9_]+)\s*=', line)
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
fi

# 5. Reinstall GRUB EFI if /sys/firmware/efi is present (or EFI dir exists) and regenerate grub.cfg
EFI_DIR=""
if findmnt /boot >/dev/null 2>&1 && [[ -d /boot/EFI ]]; then
  EFI_DIR="/boot"
elif findmnt /efi >/dev/null 2>&1 && [[ -d /efi/EFI ]]; then
  EFI_DIR="/efi"
fi

if [[ -n "$EFI_DIR" ]] && [[ -d /sys/firmware/efi ]]; then
  nox_info "Atualizando binario EFI do GRUB em ${EFI_DIR}..."
  grub-install --target=x86_64-efi --efi-directory="$EFI_DIR" --bootloader-id=GRUB
fi

nox_info "Gerando /boot/grub/grub.cfg..."
grub-mkconfig -o /boot/grub/grub.cfg

grep -q 'vmlinuz-linux-cachyos' /boot/grub/grub.cfg || nox_die "grub.cfg nao contem entrada para linux-cachyos!"
if grep -q 'vmlinuz-linux-zen' /boot/grub/grub.cfg; then
  nox_die "grub.cfg ainda contem entrada residual de linux-zen!"
fi

nox_info "Kernel unico linux-cachyos e GRUB validados."
