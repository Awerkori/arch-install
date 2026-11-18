#!/usr/bin/env bash
# Nox Archinstall — Main Orchestrator
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export NOX_ROOT="$SCRIPT_DIR"

# shellcheck source=scripts/lib/common.sh
source "${NOX_ROOT}/scripts/lib/common.sh"

STAGE="target-offline"
RESUME=false
FROM_STAGE=""
CHECK_ONLY=false

usage() {
  cat <<EOF
Uso: $0 [opcoes]
  --stage <target-offline|first-boot|all>   Estagio de execucao (padrao: target-offline)
  --profile <zen4|generic-v4>               Perfil de CPU (padrao: zen4)
  --resume                                  Retoma pulando etapas ja concluidas
  --from-stage <NN>                         Executa a partir da etapa NN (ex: 50)
  --dry-run                                 Valida contexto e mostra plano sem mutacoes
  --check-only                              Executa apenas preflight e validacao
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --stage) STAGE="$2"; shift 2 ;;
    --profile) export NOX_PROFILE="$2"; shift 2 ;;
    --resume) RESUME=true; shift ;;
    --from-stage) FROM_STAGE="$2"; shift 2 ;;
    --dry-run) export NOX_DRY_RUN=true; shift ;;
    --check-only) CHECK_ONLY=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Opcao desconhecida: $1" >&2; usage; exit 2 ;;
  esac
done

CURRENT_STAGE="init"
on_err() {
  local rc=$?
  nox_error "Falha na etapa '${CURRENT_STAGE}' (exit=${rc})."
  if ! $NOX_DRY_RUN; then
    nox_write_status "FAILED" "$CURRENT_STAGE" "exit_code=${rc}" || true
  fi
  cat >&2 <<EOF
====================================================================
[NOX ARCHINSTALL] ERRO CRITICO NA ETAPA: ${CURRENT_STAGE} (exit ${rc})
NAO REINICIE AINDA se estiver na instalacao inicial.
Logs: ${NOX_LOG_DIR}/install.log
Para retomar no chroot apos corrigir:
  arch-chroot /mnt ${NOX_ROOT}/install.sh --stage ${STAGE} --resume
====================================================================
EOF
  exit "$rc"
}
trap on_err ERR

nox_assert_target_context
if ! $NOX_DRY_RUN; then
  nox_init_dirs
  nox_write_status "RUNNING" "$STAGE" "started"
fi

TARGET_OFFLINE_SCRIPTS=(
  "00-preflight.sh"
  "10-cachyos-repos.sh"
  "20-cachyos-kernel.sh"
  "30-cachyos-settings.sh"
  "40-network.sh"
  "50-desktop.sh"
  "51-input-displays.sh"
  "52-audio.sh"
  "53-appearance.sh"
  "60-snapshots.sh"
  "70-memory.sh"
  "80-validation.sh"
  "90-first-boot.sh"
)

run_list=()
if $CHECK_ONLY; then
  run_list=("00-preflight.sh" "80-validation.sh")
elif [[ "$STAGE" == "target-offline" || "$STAGE" == "all" ]]; then
  run_list=("${TARGET_OFFLINE_SCRIPTS[@]}")
elif [[ "$STAGE" == "first-boot" ]]; then
  run_list=("90-first-boot.sh")
else
  nox_die "Estagio invalido: $STAGE"
fi

skip_until_reached=false
if [[ -n "$FROM_STAGE" ]]; then
  skip_until_reached=true
fi

for script_name in "${run_list[@]}"; do
  stage_id="${script_name%.sh}"
  if $skip_until_reached; then
    if [[ "$stage_id" == ${FROM_STAGE}* ]]; then
      skip_until_reached=false
    else
      nox_info "Pulando etapa anterior a --from-stage ${FROM_STAGE}: ${stage_id}"
      continue
    fi
  fi

  if $RESUME && nox_stage_done "$stage_id"; then
    nox_info "Etapa '${stage_id}' ja concluida (--resume); pulando."
    continue
  fi

  CURRENT_STAGE="$stage_id"
  script_path="${NOX_ROOT}/scripts/${script_name}"
  [[ -x "$script_path" ]] || chmod +x "$script_path"

  nox_info ">>> Executando etapa: ${stage_id}"
  start_s=$(date +%s)
  "$script_path"
  end_s=$(date +%s)
  nox_info "<<< Etapa '${stage_id}' concluida em $((end_s - start_s))s."

  if ! $NOX_DRY_RUN; then
    sha="$(sha256sum "$script_path" | awk '{print $1}')"
    nox_mark_stage_done "$stage_id" "$sha"
  fi
done

if ! $NOX_DRY_RUN; then
  nox_write_status "SUCCESS" "" "completed_${STAGE}"
fi

cat <<EOF
====================================================================
[NOX ARCHINSTALL] ESTAGIO '${STAGE}' CONCLUIDO COM SUCESSO!
Logs: ${NOX_LOG_DIR}/install.log
Status: ${NOX_STATE_DIR}/status.json
Pode finalizar e reiniciar normalmente.
====================================================================
EOF
