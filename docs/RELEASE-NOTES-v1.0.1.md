# Release Notes — Nox Archinstall `v1.0.1` (Candidata em Homologação)

> **Estado:** Preparada no Pull Request #1 (`hardening/v1.0.1` → `main`). **Ainda não publicada como release/tag.**  
> A release estável [`v1.0.0`](https://github.com/Awerkori/arch-install/releases/tag/v1.0.0) e sua tag/artefatos permanecem integralmente preservados.

## 1. Resumo das Melhorias e Correções de Hardening (`v1.0.1`)

1. **Cadeia de confiança e determinismo (`i` → `bootstrap/nox-install.py` → `user_configuration.json` → payload):**
   - Pinagem acíclica completa com [`manifests/release.json`](../manifests/release.json) schema v2 e validação estrita via `./scripts/build-release.sh --verify-only` (`VERIFY_RELEASE_CHAIN=PASS`).
   - Construção determinística bit-a-bit do tarball de payload (`GZIP=-n`, `--format=gnu --sort=name --mtime='UTC 2026-01-01' --owner=0 --group=0 --numeric-owner`) reproduzida entre Arch Linux local e `ubuntu-latest`.
   - Isolamento de `umask 022` antes do `archinstall` e na extração em `bootstrap/nox-bootstrap.sh`, mantendo diretórios temporários em `0700`/`0600`.
   - Adição de `--no-same-permissions` ao `tar` em `custom_commands` (`user_configuration.json`).

2. **Confiabilidade fail-closed em disco, Limine, Snapper e Secure Boot:**
   - `list_candidate_disks` e `verify_disk_safe_to_wipe` falham fechados se `lsblk`/`findmnt`/`swapon` retornarem erro ou JSON malformado.
   - Remoção de mascaramento (`|| true`) em estágios críticos de boot (`scripts/20-cachyos-kernel.sh`, `scripts/60-snapshots.sh`, `configs/bin/nox-first-boot`) com validação `--verify` no estágio `80-validation.sh`.
   - Serialização por `flock` + diretório temporário isolado por execução em [`configs/boot-hooks/95-nox-sbctl-fallback`](../configs/boot-hooks/95-nox-sbctl-fallback) e lock exclusivo em [`configs/bin/nox-limine-integrity`](../configs/bin/nox-limine-integrity), eliminando colisão concorrente (`BOOTX64.EFI.nox.tmp` / `unrecognized PE machine`).
   - Correção crítica em [`configs/bin/nox-limine-snapper-restore`](../configs/bin/nox-limine-snapper-restore): encaminhamento real do TTY interativo via fd `3` (`3<&0`) até o prompt final `Reboot now? [Y/n]:`, preservação correta de `repair_rc`, e supressão de reparo concorrente pelo `limine-snapper-watcher` enquanto `/run/lock/limine-snapper-restore.lock` estiver ativo.
   - Diferimento de `snapper` e `snap-pac` para o estágio `60-snapshots.sh` com `SNAP_PAC_SKIP=y`, zerando erros `fatal library error, lookup self` no `pacstrap` (`0` ocorrências).

3. **Documentação e apresentação pública:**
   - Separação clara entre o comando estável da release publicada `v1.0.0` (com `mktemp -d`, `trap` e verificação SHA-256 antes da execução) e os artefatos da `v1.0.1` em homologação.
   - Correções em [`docs/INSTALLATION.md`](INSTALLATION.md), [`docs/RECOVERY.md`](RECOVERY.md), [`docs/SECURE-BOOT.md`](SECURE-BOOT.md), [`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md) (`--no-microsoft`, `/usr/local/bin/limine-snapper-restore`, 4 etapas numeradas + confirmação destrutiva final) e captura oficial do desktop real no [`README.md`](../README.md).

## 2. Cadeia Congelada Verificada (`manifests/release.json`)

| Artefato | Commit Imutável | SHA-256 |
|---|---|---|
| [`i`](../i) | `978c1f1892d19a42d3b1eb3bc0c2a9f1e9b093db` | `ebd6a6515dad718530486bb8a14d7ce4e3f45d25bd0c7b364ba5b16996f5ce31` |
| [`bootstrap/nox-install.py`](../bootstrap/nox-install.py) | `46d3835b05ab43252454ce1648dd054f110857d5` | `fa6c2a3b1ee86cd60976857555326bf6a63c341914e9c061f557a62a74e03b47` |
| [`user_configuration.json`](../user_configuration.json) | `83624813f3f32fd8608ee881b21b7ab6ec92cf3e` | `9cb32121cb9a87b54b7c07749a92d3b8cb6cffcf6e4dadc502f3fa9a3da3a867` |
| `nox-archinstall-payload-v1.0.1.tar.gz` | `83624813f3f32fd8608ee881b21b7ab6ec92cf3e` | `52008f9c454c8b39c91d6e51b3546f6a76546f021c3c6a0850dc7a55d5bf92b2` |
| `nox-archinstall-payload-v1.0.1.tar.gz.sha256` | `83624813f3f32fd8608ee881b3546f6a76546f021c3c6a0850dc7a55d5bf92b2` (arquivo `.sha256`: `c6d52792ff1e1038663c633ea81a4f96d9db953ef54139a221b00ee46373ccf0`) | `c6d52792ff1e1038663c633ea81a4f96d9db953ef54139a221b00ee46373ccf0` |

## 3. Roteiro Pós-Aprovação (Executar somente após aprovação do proprietário)

```bash
# 1. Conferir CI verde no PR #1 e revisar diff contra main
gh pr view 1 --web

# 2. Aprovar e fazer merge na branch main (sem force-push)
gh pr merge 1 --merge

# 3. Sincronizar main local, gerar os 4 assets exatos de dist/ e conferir digests
git checkout main && git pull --ff-only origin main
./scripts/build-release.sh --verify-only

# 4. Criar tag assinada/anotada v1.0.1 e publicar release com os 4 assets congelados
git tag -a v1.0.1 -m "Release v1.0.1 — Hardening, Limine/Snapper/Secure Boot reliability, and docs"
git push origin v1.0.1
gh release create v1.0.1 \
  dist/nox-archinstall-payload-v1.0.1.tar.gz \
  dist/nox-archinstall-payload-v1.0.1.tar.gz.sha256 \
  bootstrap/nox-install.py \
  user_configuration.json \
  --title "Nox Archinstall v1.0.1" \
  --notes-file docs/RELEASE-NOTES-v1.0.1.md

# 5. Após publicar v1.0.1, habilitar 'immutable releases' na UI web do GitHub (Settings -> General -> Releases)
#    e atualizar o bloco principal de README.md / docs/INSTALLATION.md em PR subsequente apontando para v1.0.1.
```

> **Pendências exclusivas de hardware físico (`PENDENTE-HARDWARE`):** validação presencial em GPU AMD Radeon RX 9060 XT, monitores DP-1 (`2560x1440@165Hz`) + HDMI-A-1 (`1920x1080@100Hz`), Intel AX210, headset Havit Fuxi H3, microfone P2, teclado AULA F75 e enrollment UEFI na MSI PRO B650M-P conforme [`docs/POST_INSTALL_CHECKS.md`](POST_INSTALL_CHECKS.md) e [`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md).
