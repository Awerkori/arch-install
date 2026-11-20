# [HISTÓRICO] Relatório de Auditoria e Homologação da Release Estável — Nox Archinstall (`v1.0.0`)

> **Nota histórica:** Este documento registra a homologação final e publicação oficial da primeira release estável **`v1.0.0`** (candidato técnico consolidado `final-v4`). Os artefatos e hashes da `v1.0.0` permanecem imutáveis na release publicada no GitHub. Para o relatório atual da revisão de hardening **`v1.0.1`**, consulte [`../FINAL-AUDIT-REPORT.md`](../FINAL-AUDIT-REPORT.md).

- **Projeto:** Nox Archinstall / Project Nox (`https://github.com/Awerkori/arch-install`)
- **Versão estável publicada:** [`v1.0.0`](https://github.com/Awerkori/arch-install/releases/tag/v1.0.0)
- **Commit da tag `v1.0.0`:** `32c074ca3819d261a774b92ee4c7359411b963d5` (payload commit `2651e5a622bf5c2a0e56c5ee510a1d481a237438`)
- **Hash SHA-256 do Payload (`nox-archinstall-payload-v1.0.0.tar.gz`):** `08fbf62a2325b2a3a4b30a3d7ec4b986bc17f412970ba25f83839624444d6fd9`
- **Hash SHA-256 do arquivo `.sha256` (`nox-archinstall-payload-v1.0.0.tar.gz.sha256`):** `4c25fd721effd4e6f7a807821755154591f3e9876572c95a53d79c882e6e7be7`
- **Hash SHA-256 do Bootstrap (`bootstrap/nox-install.py` em `v1.0.0`):** `fce3f9a83e2b8c13666cf583f143096de37b8dd312e59dd8c6af4acbabb82f10`
- **Hash SHA-256 da Configuração (`user_configuration.json` em `v1.0.0`):** `6754aefcdfb659e1abdfb5036c158a609d1672f945186a1e692edeab2e104e4c`
- **ISO Oficial Homologada:** `archlinux-2026.11.01-x86_64.iso` (`archinstall 4.5`)

---

## 1. Correções Consolidadas antes da Publicação `v1.0.0` (`final-v4`)

1. **Isolamento e limpeza de credenciais do `archinstall 4.5` (`bootstrap/nox-install.py`):**
   - `select_tmpfs_dir()` garante criação de `nox_cfg.json` (`0600`) e `nox_creds.json` (`0600`) exclusivamente em `tmpfs` em RAM (`/dev/shm/nox-install-*`, `0700`) com hash SHA-512 (`$6$...`).
   - `scrub_persisted_archinstall_credentials()` executado em bloco `finally:` restringe `/var/log/archinstall` e `/mnt/var/log/archinstall` a `0700` e remove qualquer arquivo de credenciais residual.
2. **Eliminação de promoção seletiva de pacotes (`scripts/50-desktop.sh`):**
   - Removida promoção parcial de pacotes; implementada auditoria completa de SONAME/ABI (`nox_log_missing_lib_diagnostics`), atualização coerente completa (`pacman -Syyu --noconfirm`) e verificação funcional de execução (`mpvpaper --help`, `mpv --version`, `ffmpeg -version`).
3. **Verificação BLAKE2B real em `configs/bin/nox-limine-integrity`:**
   - Comparação direta do `b2sum /boot/limine.conf` contra o hash inscrito nos binários `/boot/EFI/limine/limine_x64.efi` e `/boot/EFI/BOOT/BOOTX64.EFI`.

---

## 2. Validação Limpa Ponta a Ponta (`v1.0.0` / `final-v4`)

- **Instalação limpa a partir de `archlinux-2026.11.01-x86_64.iso` em UEFI/OVMF:**
  - Todas as 13 etapas (`00-preflight` a `90-first-boot`) concluídas com `status: "SUCCESS"` (`55/55` verificações offline em `80-validation.sh`).
  - Primeiro boot via Limine (`Arch Linux -> Project Nox`, kernel `7.3.5-1-cachyos`), Noctalia Greeter e primeiro login no Umbriel + Noctalia Shell com **zero correções manuais**.
  - `systemctl --failed` e `systemctl --user --failed`: **0 unidades com falha**.
  - `28/28` testes unitários e de contrato aprovados no GitHub Actions CI da `v1.0.0`.
