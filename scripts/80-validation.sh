#!/usr/bin/env bash
# Stage 80: Comprehensive offline/target validation before allowing success status.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 80-validation: validaria todos os requisitos no alvo."
  exit 0
fi

FAILS=0
check() {
  local name="$1"; shift
  if "$@"; then
    nox_info "[PASS] $name"
  else
    nox_error "[FAIL] $name"
    ((FAILS++)) || true
  fi
}

# 1. CachyOS repos & single kernel
check "repos cachyos configurados" bash -c "pacman-conf --repo-list | grep -q 'cachyos-znver4\|cachyos-v4'"
check "linux-cachyos e headers instalados" bash -c "pacman -Q linux-cachyos linux-cachyos-headers >/dev/null"
check "nenhum kernel concorrente instalado" bash -c "! pacman -Q linux linux-zen linux-lts linux-hardened >/dev/null 2>&1"
check "arquivos de boot cachyos presentes" bash -c "test -s /boot/vmlinuz-linux-cachyos && test -s /boot/initramfs-linux-cachyos.img && test -s /boot/amd-ucode.img"
check "grub.cfg contem linux-cachyos sem linux-zen" bash -c "grep -q vmlinuz-linux-cachyos /boot/grub/grub.cfg && ! grep -q vmlinuz-linux-zen /boot/grub/grub.cfg"

# 2. Pacman & Paru from CachyOS
check "pacman instalado do CachyOS" bash -c "pacman -Qi pacman | grep -qE 'Installed From[[:space:]]*:[[:space:]]*cachyos'"
check "paru estavel instalado do CachyOS" bash -c "pacman -Qi paru | grep -qE 'Installed From[[:space:]]*:[[:space:]]*cachyos' && ! pacman -Q paru-git >/dev/null 2>&1"

# 3. Forbidden packages absent
for p in hyprland sddm nemo plasma-desktop gnome-shell firefox chromium steam discord yay paru-git; do
  check "pacote proibido ausente: $p" bash -c "! pacman -Q '$p' >/dev/null 2>&1"
done

# 4. Desktop, Greeter, Kitty, Bash, Luciole, HushMic
check "umbriel, noctalia, noctalia-greeter, greetd, kitty instalados" bash -c "pacman -Q umbriel noctalia noctalia-greeter greetd kitty >/dev/null"
check "luciole-git instalado e .desktop presente" bash -c "pacman -Q luciole-git >/dev/null && test -f /usr/share/applications/dev.noctalia.luciole.desktop"
check "hushmic-bin instalado" bash -c "pacman -Q hushmic-bin >/dev/null && command -v hushmic >/dev/null"
check "greetd habilitado e apontando para noctalia-greeter-session" bash -c "systemctl is-enabled greetd.service >/dev/null && grep -q noctalia-greeter-session /etc/greetd/config.toml"
check "umbriel config validate OK" bash -c "umbriel config validate -c /etc/skel/.config/umbriel/config.toml"
check "umbriel layout padrao dwindle" bash -c "grep -Eq '^[[:space:]]*mode[[:space:]]*=[[:space:]]*\"dwindle\"' /etc/skel/.config/umbriel/config.toml && ! grep -Eq '^[[:space:]]*mode[[:space:]]*=[[:space:]]*\"(scrolling|master|stacking)\"' /etc/skel/.config/umbriel/config.toml"
check "visudo validado sem NOPASSWD" bash -c "visudo -cf /etc/sudoers >/dev/null && visudo -cf /etc/sudoers.d/10-wheel >/dev/null && ! grep -rq NOPASSWD /etc/sudoers /etc/sudoers.d/"

# 5. Services enabled
for s in NetworkManager.service scx_loader.service ananicy-cpp.service irqbalance.service bluetooth.service systemd-resolved.service systemd-oomd.service grub-btrfsd.service; do
  check "servico habilitado: $s" systemctl is-enabled "$s" >/dev/null
done
check "snapper-timeline.timer desabilitado" bash -c "! systemctl is-enabled snapper-timeline.timer >/dev/null 2>&1"

# 6. Human user login shell = bash & wheel membership
while IFS=: read -r uname _uid _gid _home ushell; do
  [[ -n "$uname" ]] || continue
  check "shell bash para $uname" bash -c "test '$ushell' = '/bin/bash' -o '$ushell' = '/usr/bin/bash'"
  check "grupo wheel para $uname" bash -c "id -nG '$uname' | grep -qw wheel"
done < <(nox_list_human_users)

if (( FAILS > 0 )); then
  nox_die "Validacao offline falhou com ${FAILS} erro(s)."
fi
nox_info "Todas as checagens offline de 80-validation passaram!"
