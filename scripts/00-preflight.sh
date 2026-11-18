#!/usr/bin/env bash
# Stage 00: Preflight checks (context, ISA, storage, clock, DNS/HTTPS, pacman lock).
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context

if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 00-preflight: verificando sintaxe e dependencias locais."
  exit 0
fi

# 1. Verify CPU ISA
if ! nox_check_isa_v4; then
  nox_die "CPU/loader nao suporta x86-64-v4 (/lib/ld-linux-x86-64.so.2). Abortando para evitar instalacao de binarios incompativeis."
fi

if [[ "$NOX_PROFILE" == "zen4" ]]; then
  if nox_check_zen4_or_5; then
    nox_info "CPU AMD Zen 4/5 confirmada com suporte x86-64-v4."
  else
    nox_die "Perfil 'zen4' exige CPU AMD Zen 4/5 com x86-64-v4. Use --profile generic-v4 se aplicavel."
  fi
else
  nox_info "Perfil '$NOX_PROFILE' ativo com x86-64-v4 suportado."
fi

# 2. Verify root and boot mounts & free space
findmnt / >/dev/null || nox_die "Raiz '/' nao montada."
BOOT_MP=""
if findmnt /boot >/dev/null 2>&1; then
  BOOT_MP="/boot"
elif findmnt /efi >/dev/null 2>&1; then
  BOOT_MP="/efi"
else
  nox_warn "/boot e /efi nao constam como mountpoints separados; verificando /boot."
  BOOT_MP="/boot"
fi
export NOX_BOOT_MP="$BOOT_MP"

ROOT_AVAIL_KB=$(df -Pk / | awk 'NR==2 {print $4}')
BOOT_TOTAL_KB=$(df -Pk "$BOOT_MP" | awk 'NR==2 {print $2}')
BOOT_AVAIL_KB=$(df -Pk "$BOOT_MP" | awk 'NR==2 {print $4}')
(( ROOT_AVAIL_KB >= 8 * 1024 * 1024 )) || nox_die "Espaco livre insuficiente em '/' (${ROOT_AVAIL_KB} KiB; minimo 8 GiB)."
(( BOOT_TOTAL_KB >= 1500 * 1024 )) || nox_die "Particao EFI '${BOOT_MP}' muito pequena para Limine+snapshots ($((BOOT_TOTAL_KB/1024)) MiB; minimo 2 GiB, recomendado 4 GiB)."
(( BOOT_AVAIL_KB >= 500 * 1024 )) || nox_die "Espaco livre insuficiente em '${BOOT_MP}' (${BOOT_AVAIL_KB} KiB; minimo 500 MiB)."
if (( BOOT_TOTAL_KB < 3800 * 1024 )); then
  nox_warn "ESP '${BOOT_MP}' com $((BOOT_TOTAL_KB/1024)) MiB (abaixo dos 4 GiB recomendados para Limine + limine-snapper-sync)."
fi
nox_info "Espaco livre OK: /=$((ROOT_AVAIL_KB/1024)) MiB, ${BOOT_MP}=$((BOOT_AVAIL_KB/1024))/$((BOOT_TOTAL_KB/1024)) MiB."

# 3. Verify pacman lock and HTTPS/DNS (dual-stack with IPv4 fallback)
nox_wait_pacman_lock
curl --proto '=https' --tlsv1.2 -fsSI --connect-timeout 8 --retry 3 --max-time 20 "https://mirror.cachyos.org/repo/x86_64/cachyos/" >/dev/null \
  || curl -4 --proto '=https' --tlsv1.2 -fsSI --connect-timeout 8 --retry 3 --max-time 20 "https://mirror.cachyos.org/repo/x86_64/cachyos/" >/dev/null \
  || nox_die "Sem conectividade HTTPS/DNS para mirror.cachyos.org."

# 4. Install hardware profile metadata
nox_atomic_install 0644 "${NOX_ROOT}/profiles/hardware.json" "${NOX_CFG_DIR}/hardware.json"
nox_info "Preflight concluido com sucesso."
