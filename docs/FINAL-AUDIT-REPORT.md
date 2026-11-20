# Relatório Final de Auditoria de Engenharia, Hardening de Segurança e Homologação — Nox Archinstall (`v1.0.1`)

> **Histórico de versões anteriores:**
> - Pré-release [`v1.0.0-rc10`](https://github.com/Awerkori/arch-install/releases/tag/v1.0.0-rc10): preservada integralmente em [`docs/history/FINAL-AUDIT-REPORT-v1.0.0-rc10.md`](history/FINAL-AUDIT-REPORT-v1.0.0-rc10.md).
> - Release estável publicada [`v1.0.0`](https://github.com/Awerkori/arch-install/releases/tag/v1.0.0): documentada em [`docs/history/FINAL-AUDIT-REPORT-v1.0.0.md`](history/FINAL-AUDIT-REPORT-v1.0.0.md) (artefatos e hashes originais preservados sem alteração retroativa).

---

## 1. Identificação da Revisão Analisada (`v1.0.1` — Branch `hardening/v1.0.1`)

- **Projeto:** Nox Archinstall / Project Nox (`https://github.com/Awerkori/arch-install`)
- **Versão analisada:** `v1.0.1` (revisão de hardening sobre a release estável `v1.0.0`)
- **Branch de engenharia:** `hardening/v1.0.1`
- **ISO oficial homologada:** `archlinux-2026.11.01-x86_64.iso` (`archinstall 4.5`)
- **Manifesto de integridade:** [`manifests/release.json`](../manifests/release.json) (schema v2)

### Cadeia Acíclica de Commits Imutáveis e Hashes SHA-256 (`v1.0.1`)

| Estágio | Artefato | Commit de Origem Imutável | SHA-256 |
|---|---|---|---|
| **Estágio 1 (Iniciador)** | [`i`](../i) | `16f858e924a4565fca85bb36a75c873eeeba3778` | `dd439e6364a5d97e970d1c8ed62224fea2e7c9c38018724c1216eae1f4ca50de` |
| **Estágio 2 (Bootstrap)** | [`bootstrap/nox-install.py`](../bootstrap/nox-install.py) | `5e1128cba9796a88c0d62e22963c67bd18ccd79a` | `bee5edb22d802fe82fa4727377172694f4b53fd81839c5774e9ebcd6eb39ab80` |
| **Estágio 3 (Configuração)** | [`user_configuration.json`](../user_configuration.json) | `e2e84418d045b8856157265dd4f74f9172211e4e` | `aef4bdeb5268d1bbbebb42ad8de00cf7d98b71b687332bfab1f259cadb8311f9` |
| **Estágio 4 (Payload)** | `nox-archinstall-payload-v1.0.1.tar.gz` | `16f858e924a4565fca85bb36a75c873eeeba3778` | `660d6caa4a418a17a6a4138f2a1d61f10673718aeca775adca6bcf3fdbdd1ec3` |
| **Arquivo `.sha256`** | `nox-archinstall-payload-v1.0.1.tar.gz.sha256` | `16f858e924a4565fca85bb36a75c873eeeba3778` | `8c1c1fb06a9ab2e66fbd9f83e81a83721fc520e17caf70a13d39ce788ab87596` |

---

## 2. Hardening da Cadeia de Confiança e Segurança

### 2.1. Eliminação de referências mutáveis (`main`) e execução não verificada
1. **Estágio 1 (`i`):**
   - Documentado exclusivamente com download prévio para arquivo temporário sob `umask 077`, `trap` de limpeza em `EXIT INT TERM`, HTTPS estrito (`--proto "=https" --proto-redir "=https" --tlsv1.2`) a partir do commit imutável `16f858e924a4565fca85bb36a75c873eeeba3778` e verificação `sha256sum -c -` **antes** da invocação do `sh`.
   - O próprio script `i` baixa `bootstrap/nox-install.py` do commit imutável `5e1128cba9796a88c0d62e22963c67bd18ccd79a`, recusa URLs HTTP, valida o formato e o valor do hash SHA-256 (`bee5edb22d802fe82fa4727377172694f4b53fd81839c5774e9ebcd6eb39ab80`) antes de iniciar o `python3` e reconecta `/dev/tty`.
2. **Estágio 2 (`bootstrap/nox-install.py`):**
   - `DEFAULT_CONFIG_URL` aponta para o commit imutável `e2e84418d045b8856157265dd4f74f9172211e4e` (recusando URLs de branches mutáveis `main`/`master` sem `--config-sha256`).
   - `verify_sha256_bytes()` verifica o hash SHA-256 independente da configuração oficial (`OFFICIAL_CONFIG_SHA256 = aef4bdeb5268d1bbbebb42ad8de00cf7d98b71b687332bfab1f259cadb8311f9`) **antes** de decodificar UTF-8 ou executar `json.loads()`.
   - `SafeHTTPSRedirectHandler` bloqueia qualquer tentativa de downgrade de HTTPS para HTTP durante redirecionamentos HTTP `301`/`302`/`307`/`308`.
   - `_fetch_url_bytes()` valida `Content-Length` contra o tamanho efetivamente recebido para detectar downloads truncados/incompletos e rejeita respostas vazias.
   - `validate_payload_spec(..., enforce_official_payload=True)` garante que a configuração oficial autenticada só aceite o payload e o hash SHA-256 exatos da versão correspondente (`v1.0.1`), enquanto preserva o modo explícito de configuração personalizada do operador (`--config` / `--config-sha256` / `--payload-url` / `--payload-sha256`).
3. **Proteção do sistema hospedeiro (`Host Safety`):**
   - `ensure_arch_iso_environment()` em `bootstrap/nox-install.py` exige `EUID == 0`, `/sys/firmware/efi` e `/run/archiso`.
   - `nox_assert_target_context()` em `scripts/lib/common.sh` e `is_target_chroot()` em `bootstrap/nox-bootstrap.sh` bloqueiam qualquer execução fora do `arch-chroot` ou alvo autorizado.

---

## 3. Auditoria de Btrfs, Snapper, Limine e Secure Boot

1. **Btrfs e Swapfile NOCOW (`scripts/60-snapshots.sh`, `scripts/70-memory.sh`):**
   - Subvolumes `@`, `@home`, `@log`, `@pkg`, `@.snapshots` e `@swap` montados com `compress=zstd:3,noatime,discard=async,space_cache=v2`.
   - Adicionados `trap` de desmontagem e limpeza automática para montagens temporárias `subvolid=5` (`TOP_MNT`) e `/nox-swap`.
   - `/nox-swap/swapfile` confirmado com atributo `+C` (`NOCOW`) e prioridade `10` abaixo da ZRAM (`zstd`, prioridade `100`).
2. **Snapper (`configs/bin/nox-snapper-cleanup`):**
   - Adicionado bloqueio exclusivo de concorrência via `fcntl.flock` (`_cleanup_lock`) para serializar invocações simultâneas de hooks e timers.
   - Adicionada limpeza automática de estado residual (`update-session.json`) ao executar transações simples fora de sessões `topgrade`/`paru`.
   - Adicionado fallback de segurança durante consolidação multi-transação: caso `snapper create --type post` falhe após remover o `POST` anterior da âncora, o par intermediário íntegro (`fallback_pre`/`fallback_post`) é preservado tanto no disco quanto no arquivo de estado.
3. **Limine e 5 Estágios do Secure Boot (`configs/bin/nox-secureboot-verify`, `configs/bin/nox-limine-integrity`, `configs/boot-hooks/95-nox-sbctl-fallback`):**
   - `nox-secureboot-verify` valida e reporta separadamente os 5 estágios:
     1. **Estágio 1 (Preparação das chaves):** presença das chaves privadas locais em `/var/lib/sbctl/keys/`.
     2. **Estágio 2 (Assinatura dos binários):** verificação PE/EFI via `sbctl verify` de `limine_x64.efi`, `BOOTX64.EFI` e de todas as imagens `vmlinuz*` presentes na ESP.
     3. **Estágio 3 (Configuração e BLAKE2B do Limine):** ausência de marcador de transação interrompida (`/run/nox-limine-tx.dirty`), conferência real do `b2sum` de cada arquivo `boot():/<caminho>#<hash>` referenciado em `/boot/limine.conf` contra o arquivo no disco, e verificação da inscrição do `b2sum /boot/limine.conf` dentro de `limine_x64.efi` e `BOOTX64.EFI`.
     4. **Estágio 4 (Enrollment na NVRAM UEFI):** distinção explícita entre `Setup Mode` e `User Mode`.
     5. **Estágio 5 (Enforcement ativo na UEFI):** verificação do estado real de `Secure Boot` no firmware (`--require-active`).

---

## 4. Testes Automatizados e Qualidade de Código (CI/CD)

- **Workflow GitHub Actions (`.github/workflows/ci.yml`):**
  - Atualizado `actions/checkout` para `actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1` (`v7.0.1`, runtime nativo **Node.js 24**).
  - Descoberta automática e auditoria de **todos os 31 scripts shell** do repositório (incluindo executáveis sem extensão `.sh` em `i`, `configs/bin/*` e `configs/boot-hooks/*`):
    - `bash -n` em todos os 31 scripts e `sh -n` nos scripts POSIX (`i` e `configs/bin/nox-greeter-session`): **PASS (31/31)**.
    - `shellcheck -x -P .`: **PASS (31/31, 0 avisos/erros)**.
    - `shfmt -i 2 -ci -d`: **PASS (31/31, 0 diferenças)**.
  - Validação sintática JSON (`jq empty`) em `user_configuration.json`, `manifests/release.json`, `profiles/hardware.json` e `configs/noctalia/palettes/ObsidianPurple.json`: **PASS (4/4)**.
  - Suite expandida de testes unitários, de contrato, segurança e documentação (`python3 -B -m unittest discover -s tests/unit -p 'test_*.py' -v`): **PASS (42/42 testes aprovados, 0 falhas, 0 ignorados)**.

---

## 5. Validação Real em Máquinas Virtuais (`ACCEPT-A` e `ACCEPT-B`)

As duas máquinas virtuais independentes QEMU/KVM (`nox-archinstall-lab-acceptA` e `nox-archinstall-lab-acceptB`, 6 vCPUs AMD Zen 4 `host-passthrough`, 8 GiB RAM, UEFI/OVMF Secure Boot capable, discos virtuais independentes) foram inicializadas e validadas com o payload determinístico `nox-archinstall-payload-v1.0.1.tar.gz` (`660d6caa4a418a17a6a4138f2a1d61f10673718aeca775adca6bcf3fdbdd1ec3`):

| Item Verificado (Seção 11) | `ACCEPT-A` | `ACCEPT-B` | Status |
|---|---|---|---|
| 1. Instalação e validação `80-validation.sh` | `status: SUCCESS` (`55/55` checks) | `status: SUCCESS` (`55/55` checks) | **PASS** |
| 2. Boot pelo Limine (`timeout: 5`, `Arch Linux/Project Nox`) | Validado (`01-limine-boot.png`) | Validado | **PASS** |
| 3. Primeiro login via Noctalia Greeter (`greetd`) | Validado (`02-noctalia-greeter.png`) | Validado | **PASS** |
| 4. Inicialização do Umbriel (`mode = "dwindle"`) | Ativo (`✓ Configuration is valid`) | Ativo (`✓ Configuration is valid`) | **PASS** |
| 5. Inicialização do Noctalia Shell | Ativo (`✓ Config is valid`) | Ativo (`✓ Config is valid`) | **PASS** |
| 6. Tema Obsidian Purple + `mpvpaper` animado | Ativo (`03-desktop-initial.png`) | Ativo (`nox-g5-runtime.webm`) | **PASS** |
| 7. Inicialização do Firefox Pure (`firefox-pure`) | Instalado e validado | Validado em execução (`09-firefox-luciole-desktop.png`) | **PASS** |
| 8. Funcionamento do Luciole (`luciole-git`) | Instalado e validado | Validado em execução (`09-firefox-luciole-desktop.png`) | **PASS** |
| 9. Funcionamento do Kitty + Fastfetch | Validado (`04-noctalia-launcher.png`) | Validado (`06-fastfetch-kitty.png`) | **PASS** |
| 10. Unidades systemd com falha (`system` e `user`) | **0 falhas** (`0 loaded units listed`) | **0 falhas** (`0 loaded units listed`) | **PASS** |
| 11. Kernel final único (`linux-cachyos`) | `7.3.5-1-cachyos` (único kernel) | `7.3.5-1-cachyos` (único kernel) | **PASS** |
| 12. Subvolumes Btrfs + ZRAM + Swapfile NOCOW | `@`, `@home`, `@log`, `@pkg`, `@.snapshots`, `@swap` (`+C`) | `@`, `@home`, `@log`, `@pkg`, `@.snapshots`, `@swap` (`+C`) | **PASS** |
| 13. Snapper (`root`, `NUMBER_LIMIT=2`, `TIMELINE_CREATE=no`) | Configurado e ativo | Configurado e ativo | **PASS** |
| 14. Snapshots `PRE`/`POST` | Política validada | Par ativo `#21` (`pre`) + `#25` (`post`, `pre-number=21`) (`07-snapshots-state.png`) | **PASS** |
| 15. Sincronização de snapshots com Limine | `//Project Nox` + BLAKE2B verificados | `///Ponto de Segurança` + `///Estado Atualizado` (`07-snapshots-state.png`) | **PASS** |
| 16. Verificações de Secure Boot (`nox-secureboot-verify`) | Estágios 1–3 `PASS` (Setup Mode pré-enrollment) | Estágios 1–5 `PASS` (`--require-active` com Secure Boot ativo na OVMF, `08-integrity-verification.png`) | **PASS** |
| 17. Integridade dos arquivos de configuração | `umbriel`, `noctalia`, `visudo`, `limine.conf` `PASS` | `umbriel`, `noctalia`, `visudo`, `limine.conf` `PASS` | **PASS** |

### Comparação de Pacotes (`pacman -Qq` e `pacman -Qqe`)

- **Pacotes explícitos (`pacman -Qqe`):** **`100` em `ACCEPT-A` vs `100` em `ACCEPT-B`** — `diff -u` retornou **0 diferenças (`100% idênticos`)**.
- **Todos os pacotes (`pacman -Qq`):**
  - Na instalação limpa inicial: **`711` em `ACCEPT-A` vs `711` em `ACCEPT-B` (0 diferenças)**.
  - Após a bateria de atualização real com `topgrade --yes` em `ACCEPT-B`: `ACCEPT-B` possui `712` pacotes porque o repositório `multilib` substituiu `lib32-zlib` por `lib32-zlib-ng` + `lib32-zlib-ng-compat` (+1 pacote de dependência transitiva). Todas as demais 710 entradas são idênticas.

---

## 6. Evidências Visuais Reais e Manifesto SHA-256 (`v1.0.1`)

As capturas de tela reais produzidas nas VMs `ACCEPT-A` e `ACCEPT-B` durante esta auditoria estão organizadas em `/home/awerkori/.local/share/antigravity/Nox-Workspace/laboratorios/nox-archinstall-lab/evidence/v1.0.1/` (acompanhadas de `MANIFEST.sha256` e dos logs completos em `logs/`):

1. `screenshots/01-limine-boot.png` — Menu de boot Limine (`Project Nox`, kernel `7.3.5-1-cachyos`, auto-boot 5s).
2. `screenshots/02-noctalia-greeter.png` — Noctalia Greeter (`greetd`, sessão `Umbriel`, tema Obsidian Purple).
3. `screenshots/03-desktop-initial.png` — Desktop inicial Umbriel + Noctalia Shell + wallpaper animado `mpvpaper`.
4. `screenshots/04-noctalia-launcher.png` — Launcher minimalista do Noctalia exibindo os 4 aplicativos principais (`Firefox`, `kitty`, `Luciole`, `ProtonPlus`).
5. `screenshots/05-noctalia-lockscreen.png` — Noctalia Lock Screen com emblema animado, relógio `Outfit` e caixa de desbloqueio centralizada.
6. `screenshots/06-fastfetch-kitty.png` — Painel `nox-fastfetch` no terminal Kitty com logo Braille e 4 quadros alinhados.
7. `screenshots/07-snapshots-state.png` — Estado dos snapshots Snapper (`PRE`/`POST`), entradas `Ponto de Segurança` / `Estado Atualizado` no `/boot/limine.conf`, subvolumes Btrfs e swapfile NOCOW (`+C`).
8. `screenshots/08-integrity-verification.png` — Execução real de `sudo nox-secureboot-verify --require-active` (todos os 5 estágios `PASS`), `systemctl --failed` (`0` falhas) e `/var/lib/nox-archinstall/status.json`.
9. `screenshots/09-firefox-luciole-desktop.png` — Firefox Pure (com tema escuro Obsidian Purple) e gerenciador de arquivos Luciole em execução no Umbriel (`dwindle`).

---

## 7. Limitações Conhecidas e Itens Pendentes de Validação Física (`PENDENTE-HARDWARE`)

### 7.1. Limitações Arquiteturais Documentadas
1. **Pinagem de hashes SHA-256 sem chave pública offline pré-instalada na ISO:** A ISO oficial do Arch Linux não inclui chaves públicas do proprietário do Project Nox. Por isso, a cadeia de confiança utiliza referências imutáveis de commit no GitHub sobre HTTPS/TLSv1.2+ combinadas à verificação explícita de hash SHA-256 em cada estágio.
2. **Releases imutáveis do GitHub (`immutable_releases`):** A proteção da branch `main` (exigindo CI `validate`, bloqueando force-push e deleção) e o ruleset de proteção de tags `refs/tags/v*` (bloqueando deleção e force-push de tags de release) já estão ativos via API do GitHub. A chave adicional *Enable release immutability* na interface web do GitHub (`Settings → General → Releases`) só pode ser ativada pelo proprietário no navegador.

### 7.2. Checklist de Validação Física (`PENDENTE-HARDWARE`)
Os itens abaixo dependem exclusivamente do hardware físico de referência e permanecem identificados como pendentes até o teste na máquina real (procedimento detalhado em [`docs/POST_INSTALL_CHECKS.md`](POST_INSTALL_CHECKS.md)):

- [ ] **GPU ASRock AMD Radeon RX 9060 XT:** aceleração Vulkan/RADV real (`vulkaninfo`, `rocm-smi-lib`, `btop` GPU meter) e preservação de vídeo da Option ROM/GOP no POST com Secure Boot ativo.
- [ ] **Monitor principal Samsung Odyssey G5 (`DP-1`, `2560x1440@165Hz`) e monitor secundário AOC 24B35 (`HDMI-A-1`, `1920x1080@100Hz` vertical `90°`):** alinhamento físico `[2560, -350]` e travessia contínua do feixe luminoso entre os dois monitores reais.
- [ ] **Placa Wi-Fi / Bluetooth Intel AX210 (`iwlwifi` + `iwd`):** conexão Wi-Fi real, `regdomain BR` e pareamento de áudio Bluetooth A2DP.
- [ ] **Headset HAVIT Fuxi H3:** ciclo real de conexão USB/2.4GHz validando `nox-fuxi-h3-fix` (`PCM Playback Volume` = 100 e unmute de captura).
- [ ] **Microfone analógico P2:** seleção de fonte padrão no WirePlumber sem dispositivo virtual residual.
- [ ] **Teclado AULA F75:** digitação física com layout `us(intl)` e cedilha (`' + c → ç`) sem chattering.
- [ ] **Secure Boot efetivamente ativo na UEFI da MSI PRO B650M-P (`MS-7E27`, BIOS `1.I2`):** execução presencial das Fases A a E de [`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md), correção da política `FQ0001` (`Maximum Security` / `Deny Execute`) e teste físico de rejeição do pendrive não assinado.
