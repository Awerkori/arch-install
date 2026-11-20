#!/usr/bin/env bash
# Stage 10: CachyOS GPG verification, keyring, mirrorlists, Pacman fork, and znver4 repos.
set -Eeuo pipefail
source "${NOX_ROOT}/scripts/lib/common.sh"

CACHYOS_KEY_ID="F3B607488DB35A47"
CACHYOS_KEY_FP="882DCFE48E2051D48E2562ABF3B607488DB35A47"
CACHYOS_BASE_URL="https://mirror.cachyos.org/repo/x86_64/cachyos"

nox_assert_target_context
if $NOX_DRY_RUN; then
  nox_info "[DRY-RUN] 10-cachyos-repos: importaria chave ${CACHYOS_KEY_FP}, instalaria pacman fork e repos znver4."
  exit 0
fi

nox_wait_pacman_lock

# 1. Import and verify FULL fingerprint of CachyOS GPG key
if ! pacman-key --finger "$CACHYOS_KEY_ID" 2>/dev/null | tr -d ' ' | grep -qF "$CACHYOS_KEY_FP"; then
  nox_info "Importando chave GPG CachyOS (${CACHYOS_KEY_ID})..."
  pacman-key --recv-keys "$CACHYOS_KEY_ID" --keyserver hkps://keyserver.ubuntu.com \
    || pacman-key --recv-keys "$CACHYOS_KEY_ID" --keyserver hkps://keys.openpgp.org \
    || pacman-key --recv-keys "$CACHYOS_KEY_ID" --keyserver hkps://pgp.mit.edu \
    || nox_die "Falha ao importar chave GPG do CachyOS."
fi

ACTUAL_FP="$(pacman-key --finger "$CACHYOS_KEY_ID" 2>/dev/null | tr -d ' ' | grep -oE '[0-9A-F]{40}' | head -n1 || true)"
[[ "$ACTUAL_FP" == "$CACHYOS_KEY_FP" ]] || nox_die "Fingerprint GPG CachyOS divergente! Esperado=${CACHYOS_KEY_FP}, obtido=${ACTUAL_FP}"
pacman-key --lsign-key "$CACHYOS_KEY_ID"

# 2. Discover current keyring, mirrorlists, and pacman fork packages dynamically (IPv4 + cdn77 fallback)
INDEX_HTML=""
for base_candidate in "https://mirror.cachyos.org/repo/x86_64/cachyos" "https://cdn77.cachyos.org/repo/x86_64/cachyos"; do
  if INDEX_HTML="$(curl --proto '=https' --tlsv1.2 -fsSL --connect-timeout 8 --retry 3 --retry-delay 2 --max-time 25 "${base_candidate}/" 2>/dev/null)" \
     || INDEX_HTML="$(curl -4 --proto '=https' --tlsv1.2 -fsSL --connect-timeout 8 --retry 3 --retry-delay 2 --max-time 25 "${base_candidate}/" 2>/dev/null)"; then
    if [[ -n "$INDEX_HTML" ]]; then
      CACHYOS_BASE_URL="$base_candidate"
      break
    fi
  fi
done
[[ -n "$INDEX_HTML" ]] || nox_die "Falha ao consultar indice HTTPS dos repositorios CachyOS."
resolve_pkg_url() {
  local prefix="$1"
  local fname
  fname="$(printf '%s\n' "$INDEX_HTML" | grep -Eo "${prefix}-[0-9][^\"<> ]+\.pkg\.tar\.zst" | grep -v '\.sig$' | sort -V | tail -n1 || true)"
  [[ -n "$fname" ]] || nox_die "Pacote '${prefix}' nao encontrado em ${CACHYOS_BASE_URL}/"
  printf '%s/%s' "$CACHYOS_BASE_URL" "$fname"
}

KEYRING_URL="$(resolve_pkg_url "cachyos-keyring")"
MIRROR_URL="$(resolve_pkg_url "cachyos-mirrorlist")"
V4_MIRROR_URL="$(resolve_pkg_url "cachyos-v4-mirrorlist")"
PACMAN_URL="$(resolve_pkg_url "pacman")"

nox_info "Instalando keyring, mirrorlists e pacman fork do CachyOS..."
pacman -U --noconfirm "$KEYRING_URL" "$MIRROR_URL" "$V4_MIRROR_URL" "$PACMAN_URL"

# 3. Configure /etc/pacman.conf idempotently with znver4 order before [core]
if [[ ! -f /etc/pacman.conf.nox.bak ]]; then
  cp -a /etc/pacman.conf /etc/pacman.conf.nox.bak
fi

python3 - /etc/pacman.conf "$NOX_PROFILE" <<'PY'
import sys, re, os
conf_path, profile = sys.argv[1], sys.argv[2]
with open(conf_path, "r", encoding="utf-8") as f:
    text = f.read()

# Remove any previously managed CachyOS repo blocks to ensure idempotency without duplicates
cachy_sections = [
    "cachyos-znver4", "cachyos-core-znver4", "cachyos-extra-znver4",
    "cachyos-v4", "cachyos-core-v4", "cachyos-extra-v4",
    "cachyos-v3", "cachyos-core-v3", "cachyos-extra-v3",
    "cachyos",
]
for sec in cachy_sections:
    text = re.sub(rf'(?ms)^\[{re.escape(sec)}\]\n(?:(?!^\[).*\n)*', '', text)

# Ensure Architecture = auto, Color, ParallelDownloads = 5
text = re.sub(r'(?m)^#?\s*Architecture\s*=.*$', 'Architecture = auto', text)
text = re.sub(r'(?m)^#?\s*Color\s*$', 'Color', text)
if not re.search(r'(?m)^ParallelDownloads\s*=', text):
    text = re.sub(r'(?m)^#?\s*ParallelDownloads\s*=.*$', 'ParallelDownloads = 5', text)

# Ensure [multilib] is enabled
text = re.sub(r'(?ms)^#\[multilib\]\n#\s*(Include\s*=\s*/etc/pacman\.d/mirrorlist)', r'[multilib]\n\1', text)

if profile == "zen4":
    block = (
        "[cachyos-znver4]\nInclude = /etc/pacman.d/cachyos-v4-mirrorlist\n\n"
        "[cachyos-core-znver4]\nInclude = /etc/pacman.d/cachyos-v4-mirrorlist\n\n"
        "[cachyos-extra-znver4]\nInclude = /etc/pacman.d/cachyos-v4-mirrorlist\n\n"
        "[cachyos]\nInclude = /etc/pacman.d/cachyos-mirrorlist\n\n"
    )
else:
    block = (
        "[cachyos-v4]\nInclude = /etc/pacman.d/cachyos-v4-mirrorlist\n\n"
        "[cachyos-core-v4]\nInclude = /etc/pacman.d/cachyos-v4-mirrorlist\n\n"
        "[cachyos-extra-v4]\nInclude = /etc/pacman.d/cachyos-v4-mirrorlist\n\n"
        "[cachyos]\nInclude = /etc/pacman.d/cachyos-mirrorlist\n\n"
    )

m = re.search(r'(?m)^\[core\]\s*$', text)
if not m:
    raise SystemExit("Secao [core] nao encontrada em /etc/pacman.conf")
new_text = text[:m.start()] + block + text[m.start():]
new_text = re.sub(r'\n{3,}', '\n\n', new_text).strip() + '\n'

tmp = conf_path + ".nox.tmp"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(new_text)
os.replace(tmp, conf_path)
PY

pacman-conf --repo-list | grep -q 'cachyos-znver4\|cachyos-v4' || nox_die "Repositorios CachyOS ausentes apos edicao de pacman.conf."

# 4. Full coherent upgrade (-Syyu) including cachyos/pacman sync registration before installing rate-mirrors
nox_info "Executando atualizacao coerente completa (pacman -Syyu)..."
pacman -Syyu --noconfirm cachyos/pacman
if pacman -Syu --needed --noconfirm cachyos-rate-mirrors >/dev/null 2>&1; then
  nox_info "Classificando mirrors com cachyos-rate-mirrors..."
  timeout 120 cachyos-rate-mirrors >/dev/null 2>&1 || nox_warn "cachyos-rate-mirrors falhou/timeout; mantendo mirrorlists existentes."
  pacman -Syyu --noconfirm
fi
pacman -S --needed --noconfirm cachyos/pacman >/dev/null 2>&1 || true

# Verify pacman fork provenance
pacman -Qi pacman | grep -E 'Version|Installed From|Architecture'
nox_info "Repositorios CachyOS e Pacman fork configurados com sucesso."
