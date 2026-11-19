#!/usr/bin/env bash
# Safe unprivileged AUR build & install helpers (never runs makepkg as root).

NOX_AUR_USER="noxbuild"
NOX_AUR_HOME="/var/tmp/noxbuild-home"

nox_aur_setup_user() {
  if ! id -u "$NOX_AUR_USER" >/dev/null 2>&1; then
    useradd --system --home-dir "$NOX_AUR_HOME" --create-home --shell /usr/bin/bash "$NOX_AUR_USER"
  fi
  mkdir -p "$NOX_AUR_HOME"
  chown -R "${NOX_AUR_USER}:${NOX_AUR_USER}" "$NOX_AUR_HOME"
  chmod 750 "$NOX_AUR_HOME"
}

nox_aur_cleanup_user() {
  if id -u "$NOX_AUR_USER" >/dev/null 2>&1; then
    userdel -r "$NOX_AUR_USER" >/dev/null 2>&1 || userdel "$NOX_AUR_USER" >/dev/null 2>&1 || true
  fi
  rm -rf "$NOX_AUR_HOME"
}

nox_aur_inspect_pkgbuild() {
  local pkgbuild="$1"
  [[ -f "$pkgbuild" ]] || nox_die "PKGBUILD ausente: $pkgbuild"
  # Reject suspicious constructs before running makepkg
  if grep -Eq 'curl\s+.*\|\s*(ba)?sh|wget\s+.*\|\s*(ba)?sh|--skipchecksums|--skippgpcheck' "$pkgbuild"; then
    nox_die "PKGBUILD reprovado na inspecao de seguranca: $pkgbuild"
  fi
  bash -n "$pkgbuild" || nox_die "Erro sintatico no PKGBUILD: $pkgbuild"
}

nox_aur_install_pkg() {
  local pkgname="$1"
  local workdir="${NOX_AUR_HOME}/${pkgname}"

  if pacman -Qq "$pkgname" >/dev/null 2>&1; then
    nox_info "Pacote AUR '$pkgname' ja instalado; pulando rebuild."
    return 0
  fi

  nox_aur_setup_user
  rm -rf "$workdir"
  mkdir -p "$workdir"
  cat > "${NOX_AUR_HOME}/.gitconfig" <<'EOF'
[http]
	version = HTTP/1.1
	lowSpeedLimit = 1024
	lowSpeedTime = 20
EOF
  chown -R "${NOX_AUR_USER}:${NOX_AUR_USER}" "$workdir" "${NOX_AUR_HOME}/.gitconfig"

  nox_info "Clonando AUR '$pkgname' como usuario nao-root '$NOX_AUR_USER'..."
  local clone_ok=false attempt
  for attempt in 1 2 3; do
    rm -rf "${workdir}/src"
    if su -s /usr/bin/bash "$NOX_AUR_USER" -c "
      export HOME='${NOX_AUR_HOME}' GIT_CONFIG_GLOBAL='${NOX_AUR_HOME}/.gitconfig'
      timeout 45 git clone --depth 1 -4 'https://aur.archlinux.org/${pkgname}.git' '${workdir}/src'
    "; then
      clone_ok=true
      break
    fi
    rm -rf "${workdir:?}/src" "${workdir:?}/${pkgname}"
    if su -s /usr/bin/bash "$NOX_AUR_USER" -c "
      set -euo pipefail
      curl -fsSL -4 --connect-timeout 15 --max-time 45 'https://aur.archlinux.org/cgit/aur.git/snapshot/${pkgname}.tar.gz' -o '${workdir}/${pkgname}.tar.gz'
      tar -xzf '${workdir}/${pkgname}.tar.gz' -C '${workdir}'
      mv '${workdir}/${pkgname}' '${workdir}/src'
      rm -f '${workdir}/${pkgname}.tar.gz'
    "; then
      clone_ok=true
      break
    fi
    nox_warn "Tentativa ${attempt}/3 de clonar AUR '${pkgname}' falhou; aguardando 3s..."
    sleep 3
  done
  $clone_ok || nox_die "Falha ao clonar repositorio AUR '${pkgname}' apos 3 tentativas."

  local pkgbuild="${workdir}/src/PKGBUILD"
  nox_aur_inspect_pkgbuild "$pkgbuild"

  # Resolve official repo dependencies as root first (never NOPASSWD sudo from makepkg)
  local deps_raw
  deps_raw="$(su -s /usr/bin/bash "$NOX_AUR_USER" -c "
    cd '${workdir}/src'
    python3 - <<'PY'
import subprocess, re
out = subprocess.check_output(['bash', '-c', 'source PKGBUILD; printf \"%s\\n\" \"\${depends[@]}\" \"\${makedepends[@]}\"'], text=True)
for line in out.splitlines():
    pkg = re.split(r'[<>=:]', line.strip())[0]
    if pkg:
        print(pkg)
PY
  ")"

  local repo_deps=()
  local aur_deps=()
  while IFS= read -r dep; do
    [[ -n "$dep" ]] || continue
    if pacman -Qq "$dep" >/dev/null 2>&1 || pacman -Sq --print "$dep" >/dev/null 2>&1; then
      repo_deps+=("$dep")
    else
      aur_deps+=("$dep")
    fi
  done <<< "$deps_raw"

  if (( ${#aur_deps[@]} > 0 )); then
    for adep in "${aur_deps[@]}"; do
      nox_info "Resolvendo dependencia AUR '$adep' para '$pkgname'..."
      nox_aur_install_pkg "$adep"
    done
  fi

  if (( ${#repo_deps[@]} > 0 )); then
    nox_wait_pacman_lock
    pacman -S --needed --noconfirm "${repo_deps[@]}"
  fi

  nox_info "Compilando '$pkgname' via makepkg sem root..."
  local build_ok=false b_attempt
  for b_attempt in 1 2 3; do
    if su -s /usr/bin/bash "$NOX_AUR_USER" -c "
      set -euo pipefail
      export HOME='${NOX_AUR_HOME}'
      export GIT_CONFIG_GLOBAL='${NOX_AUR_HOME}/.gitconfig'
      cd '${workdir}/src'
      makepkg --noconfirm --nodeps
    "; then
      build_ok=true
      break
    fi
    nox_warn "Tentativa ${b_attempt}/3 de makepkg para '${pkgname}' falhou; aguardando 4s..."
    sleep 4
  done
  $build_ok || nox_die "Falha em makepkg para '${pkgname}' apos 3 tentativas."

  local built_pkgs=()
  while IFS= read -r f; do
    built_pkgs+=("$f")
  done < <(find "${workdir}/src" -maxdepth 1 -type f -name '*.pkg.tar.*' ! -name '*.sig' ! -name '*-debug-*' | sort)

  if (( ${#built_pkgs[@]} == 0 )); then
    nox_die "Nenhum pacote compilado encontrado para '$pkgname'."
  fi

  nox_wait_pacman_lock
  pacman -U --noconfirm "${built_pkgs[@]}"
  rm -rf "$workdir"
  nox_info "Pacote AUR '$pkgname' compilado e instalado com sucesso."
}
