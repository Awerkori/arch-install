# [HISTÓRICO] Relatório de Auditoria Técnica, Visual e de Atualizações — Nox Archinstall (`v1.0.0-rc10`)

> **Nota histórica:** Este documento preserva integralmente o registro de auditoria da pré-release **`v1.0.0-rc10`** (anterior à publicação da versão estável **`v1.0.0`** e da revisão de hardening **`v1.0.1`**). Para o relatório da versão estável publicada (`v1.0.0`), consulte [`FINAL-AUDIT-REPORT-v1.0.0.md`](FINAL-AUDIT-REPORT-v1.0.0.md). Para o relatório atual de engenharia e hardening (`v1.0.1`), consulte [`../FINAL-AUDIT-REPORT.md`](../FINAL-AUDIT-REPORT.md).

- **Projeto:** Nox Archinstall / Project Nox (`https://github.com/Awerkori/arch-install`)
- **Revisão histórica documentada:** `v1.0.0-rc10` (`--prerelease`)
- **Release Tag:** [`v1.0.0-rc10`](https://github.com/Awerkori/arch-install/releases/tag/v1.0.0-rc10)
- **Commit do payload (`main`):** `4f58011a820e6638b3e9f900f117cd03fabc4f7b` (metadata `d8900ba221230448820c8b99d6f2863188690c72`)
- **Payload SHA-256 (`nox-archinstall-payload-v1.0.0-rc10.tar.gz`):** `6463bc0d24ac78aaa6ae08f86d18d67da96995256105a16ab4c96ec1bd128650`
- **Inventários:** [`../INSTALLED-COMPONENTS.md`](../INSTALLED-COMPONENTS.md), [`../INSTALLED-PACKAGES.tsv`](../INSTALLED-PACKAGES.tsv) e [`../TOPGRADE-PROTON-INTEGRATION.md`](../TOPGRADE-PROTON-INTEGRATION.md)

---

## 1. Validação em Gêmeas Limpas (`ACCEPT-A` e `ACCEPT-B`)

Duas instalações limpas completas em UEFI/OVMF com Btrfs, a partir da ISO oficial `archlinux-2026.11.01-x86_64.iso`, utilizando exatamente o fluxo oficial do payload `v1.0.0-rc10`:

| VM | Resultado Instalação | Fim (UTC) | `pacman -Qq` | `pacman -Qqe` | AUR (`pacman -Qqm`) | Unidades Falhas |
|---|---|---|---|---|---|---|
| **`ACCEPT-A`** | `EXIT_CODE=0` | `2026-11-19T21:08:28Z` | **711** | **100** | `luciole-git`, `topgrade-bin` | **0** (system + user) |
| **`ACCEPT-B`** | `EXIT_CODE=0` | `2026-11-19T20:03:59Z` | **711** | **100** | `luciole-git`, `topgrade-bin` | **0** (system + user) |

- **Paridade `ACCEPT-A` vs `ACCEPT-B`:** `diff -u` sobre `pacman -Qq` e `pacman -Qqe` retornou **0 diferenças** (`ALL_PACKAGES_MATCH_100PCT` / `EXPLICIT_PACKAGES_MATCH_100PCT`).
- **Correções descobertas e aplicadas no próprio ciclo antes da aceitação final:**
  1. `scripts/80-validation.sh`: ajustado para não exigir `//Snapshots` quando há 0 snapshots pós-instalação limpa (proibindo sempre `//+Snapshots`), pois `limine-snapper-sync` omite seção vazia.
  2. `scripts/lib/aur.sh`: exportados `HOME` e `GIT_CONFIG_GLOBAL` para o usuário não-root `noxbuild` no `git clone`, com timeout de 45s (`-4`) e fallback oficial para tarball `.tar.gz` da AUR (`cgit`).

---

## 2. Identidade Visual **Obsidian Purple** (RC9 → RC10)

| Área | Implementação e Verificação em VM Limpa |
|---|---|
| **Limine** | `interface_branding: Project Nox`, `interface_branding_colour: fbbf24`, `wallpaper` com hash BLAKE2b válido, `[+] Snapshots` recolhido por padrão, entradas `///Ponto de Segurança` (PRE) e `///Estado Atualizado` (POST) diretamente bootáveis |
| **Noctalia Greeter** | `NOCTALIA_GREETER_ASSETS_DIR=/usr/share/nox-archinstall/greeter-assets` (`noctalia.svg` + `fonts/`), `theme_mode = "dark"`, erro `pam_authenticate: AUTH_ERR` legível sem distorção |
| **Noctalia Lockscreen** | Sticker animado `nox-lockscreen-emblem.gif` ativo em 2 quadros distintos, relógio `Outfit`, `login_box` centralizado sem media strip |
| **Wallpapers & Multi-Monitor** | `nox-noctalia-layout --init-once` no `autostart` do Umbriel (0 Setup Wizard); `mpvpaper` executando `nox-g5-runtime.webm` em `Virtual-1`; perfil dual monitor (`DP-1` + `HDMI-A-1` vertical `90°` com `nox-aoc-runtime.webm`) validado por contrato/unit test |
| **Noctalia Config & Fontes** | `noctalia config validate ~/.config/noctalia` retornou `✓ Config is valid` (`0` avisos) nas duas VMs; `setup_wizard_enabled = false`; fontes OFL `Outfit` e `Plus Jakarta Sans` instaladas em `/usr/share/fonts/nox/` |
| **Fastfetch & Kitty** | Logo Braille de largura fixa 28 colunas (`nox-logo.txt`) e dashboard Obsidian Purple em tela cheia e metade Dwindle 50/50 |
| **Firefox Pure & Launcher** | `firefox-pure` (`160.0-1`) com `userChrome.css`/`userContent.css` escuros Obsidian Purple; launcher exibe **estritamente 4 aplicativos** (`Firefox`, `kitty`, `Luciole`, `ProtonPlus`) |

---

## 3. Correções Técnicas, Áudio, Entrada e Inatividade

- **Pilha gráfica (`80-validation.sh` / `50-desktop.sh`):** `vulkan-tools` (`1.4.363.0-1.1`) e `mesa-utils` (`9.0.0-7.1`) instalados com Mesa/RADV/VA-API 64/32 bits; `libva-utils` ausente conforme esperado. Na VM sem passthrough GPU, `glxinfo` operou em `llvmpipe` e `vulkaninfo` falhou por ausência de GPU física (hardware RDNA marcado `PENDENTE-HARDWARE`).
- **Energia / Anti-Inatividade:** `IdleAction=ignore`, `IdleActionSec=0` (`/etc/systemd/logind.conf.d/99-nox-no-idle.conf`), `swayidle`/`hypridle` ausentes e `nox-power.toml` com `lock`/`screen_off`/`lock_and_suspend` desativados. Comprovado empiricamente em `ACCEPT-B` com sessão gráfica aberta por **36 minutos ininterruptos sem interação** mantendo tela ativa sem bloqueio/suspensão.
- **Teclado ANSI `us(intl)` e Acentuação:** Umbriel configurado com `layout = "us"`, `variant = "intl"`, `track_layout = "global"`, `repeat_rate = 25`, `repeat_delay = 600` e `~/.XCompose` com `<dead_acute> <c> : "ç" ccedilla`. Sintoma físico de chattering/tecla `M` no AULA F75 permanece `PENDENTE-HARDWARE`.
- **Havit Fuxi H3 (`nox-fuxi-h3-fix`):** Regra udev `85-nox-fuxi-h3.rules` e unit `nox-fuxi-h3.path`/`service` atualizados para varredura multi-índice ALSA `Mic Capture Switch` + unmute PipeWire `alsa_input.*(fuxi|xiisound)` preservando mute intencional.

---

## 4. Bateria de Atualizações, ProtonPlus e Snapshots

| Teste | Escopo Verificado | Resultado Observado |
|---|---|---|
| **1 — `pacman` normal** | `pacman -S --noconfirm tree` + `-Rns tree` | `snap-pac` criou `PRE/POST`; política `root` manteve apenas par mais recente (`#3/#4`) + hashes BLAKE2b 100% íntegros |
| **2 — `paru` AUR** | `paru -S --noconfirm --rebuild topgrade-bin` | Build e instalação via `paru` geraram `#5/#6`; cleanup manteve `2` snapshots |
| **3 — Snapshot manual + `pacman`** | Snapshot manual `#7` (`manual-keep-test`) + transação `jq` (`#8/#9`) | Snapshot manual `#7` preservado; política removeu pares automáticos antigos (`#5/#6`), mantendo `#7` + `#8/#9` |
| **4 — `topgrade` real multi-transação (`Repo + AUR`)** | Downgrade temporário local de `mesa-utils` (`9.0.0-0`) + `topgrade-bin` (`17.17.0-0`), seguido de `/usr/local/bin/topgrade --yes` | `nox-snapper-cleanup` consolidou para **exatamente 1 par**: `PRE=#15` (Estado A) e `POST=#19` (`pre-number=15`, Estado C). `/boot/limine.conf` exibiu `///Ponto de Segurança` (`#15`) e `///Estado Atualizado` (`#19`), todos com BLAKE2b válidos |
| **5 — `topgrade` no-op** | `/usr/local/bin/topgrade --yes` sem pendências | Nenhum snapshot novo criado |
| **6 — `PRE` órfão (transação interrompida)** | Criação de `PRE=#12` (`interrupted-test`) + `nox-snapper-cleanup` | Preservaram-se snapshots existentes sem apagar ponto de recuperação válido |
| **7 — `ProtonPlus` + falha simulada** | `protonplus list`, `protonplus update all` e wrapper mock retornando `exit 1` | `protonplus update all` → `Already up to date` e falha isolada sem corromper snapshots |
| **8 — Kernel / `limine-update`** | `sudo limine-update` completo (mkinitcpio + `sbctl` + hooks pre/post) | Regenerou initramfs (`7.3.5-1-cachyos`), executou hooks `05`/`85`/`95`, e verificou `ALL_LIMINE_BLAKE2_HASHES_MATCH=True` (`7/7`) |
| **9 — Boot em Snapshot + Restore real (`--restore`)** | Boot direto via menu Limine em **`///Ponto de Segurança` (`#15`)** → `sudo limine-snapper-sync --restore` → reboot → `topgrade --yes` | Subvolume `/@` restaurado ao Estado A em Btrfs gravável (`subvolid=284`) e atualizado de volta para `9.0.0-7.1` + `17.17.0-1` (`#21/#25`) |
| **10 — Par `POST`/`PRE` final e limpeza** | Limpeza do snapshot `#20` (`backup before restore #15`) | Snapper `root` finalizado com exatamente o par `#21` (`pre`) e `#25` (`post`) |
| **11 — `topgrade --dry-run`** | Execução via `/usr/local/bin/topgrade --dry-run` em `ACCEPT-A` e `ACCEPT-B` | `System update: OK`, `config-update: OK`, `ProtonPlus: OK` |
| **12 — GUI ProtonPlus + Proton-CachyOS SLR** | Abertura do ProtonPlus e checagem `/usr/share/steam/compatibilitytools.d/` | `protonplus` (`0.6.8-2`) visível no launcher e funcional; `proton-cachyos-slr` (`1:11.0.20261015-1`) pré-instalado |
