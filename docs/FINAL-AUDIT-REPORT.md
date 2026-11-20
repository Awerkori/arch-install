# Relatório Final de Auditoria Técnica, Visual e de Atualizações — Nox Archinstall (`v1.0.0-rc10`)

- **Projeto:** Nox Archinstall / Project Nox (`https://github.com/Awerkori/arch-install`)
- **Revisão entregue:** `v1.0.0-rc10` (`--prerelease`; **`v1.0.0` não publicada — aguarda aprovação humana explícita**)
- **Release Tag:** [`v1.0.0-rc10`](https://github.com/Awerkori/arch-install/releases/tag/v1.0.0-rc10)
- **Commit do payload (`main`):** `4f58011a820e6638b3e9f900f117cd03fabc4f7b` (metadata `d8900ba221230448820c8b99d6f2863188690c72`)
- **Payload SHA-256 (`nox-archinstall-payload-v1.0.0-rc10.tar.gz`):** `6463bc0d24ac78aaa6ae08f86d18d67da96995256105a16ab4c96ec1bd128650`
- **Pacote visual de evidências:** `/home/awerkori/Downloads/Aprovacao-Visual-Nox-Archinstall/PROXIMA-RC/` (`42` artefatos listados com SHA-256 em `MANIFEST.md`)
- **Inventários:** [`INSTALLED-COMPONENTS.md`](INSTALLED-COMPONENTS.md), [`INSTALLED-PACKAGES.tsv`](INSTALLED-PACKAGES.tsv) e [`TOPGRADE-PROTON-INTEGRATION.md`](TOPGRADE-PROTON-INTEGRATION.md)

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

| Área | Implementação e Verificação em VM Limpa | Evidências (`PROXIMA-RC/`) |
|---|---|---|
| **Limine** | `interface_branding: Project Nox`, `interface_branding_colour: fbbf24`, `wallpaper` com hash BLAKE2b válido, `[+] Snapshots` recolhido por padrão, entradas `///Ponto de Segurança` (PRE) e `///Estado Atualizado` (POST) diretamente bootáveis | `01-Limine/limine-main-collapsed-vm.png`, `01-Limine/limine-snapshots-expanded-vm.png` |
| **Noctalia Greeter** | `NOCTALIA_GREETER_ASSETS_DIR=/usr/share/nox-archinstall/greeter-assets` (`noctalia.svg` + `fonts/`), `theme_mode = "dark"`, erro `pam_authenticate: AUTH_ERR` legível sem distorção | `02-Noctalia-Greeter/greeter-live-vm.png`, `02-Noctalia-Greeter/greeter-error-vm.png` |
| **Noctalia Lockscreen** | Sticker animado `nox-lockscreen-emblem.gif` ativo em 2 quadros distintos, relógio `Outfit`, `login_box` centralizado sem media strip | `03-Noctalia-Lockscreen/lockscreen-live-vm.png`, `03-Noctalia-Lockscreen/lockscreen-live-vm-frame2.png` |
| **Wallpapers & Multi-Monitor** | `nox-noctalia-layout --init-once` no `autostart` do Umbriel (0 Setup Wizard); `mpvpaper` executando `nox-g5-runtime.webm` em `Virtual-1` (2 frames distintos comprovam animação contínua); perfil dual monitor (`DP-1` + `HDMI-A-1` vertical `90°` com `nox-aoc-runtime.webm`) validado por contrato/unit test | `04-Wallpapers-G5/desktop-frame1-vm.png`, `04-Wallpapers-G5/desktop-frame2-vm.png`, `05-Wallpapers-AOC/*` |
| **Noctalia Config & Fontes** | `noctalia config validate ~/.config/noctalia` retornou `✓ Config is valid` (`0` avisos) nas duas VMs; `setup_wizard_enabled = false`; fontes OFL `Outfit` e `Plus Jakarta Sans` instaladas em `/usr/share/fonts/nox/` | `07-Evidencias-Tecnicas/acceptA-audit.txt`, `acceptB-audit.txt` |
| **Fastfetch & Kitty** | Logo Braille de largura fixa 28 colunas (`nox-logo.txt`) e dashboard Obsidian Purple em tela cheia e metade Dwindle 50/50 | `06-Fastfetch/fastfetch-full-vm.png`, `06-Fastfetch/fastfetch-half-vm.png` |
| **Firefox Pure & Launcher** | `firefox-pure` (`160.0-1`) com `userChrome.css`/`userContent.css` escuros Obsidian Purple; launcher exibe **estritamente 4 aplicativos** (`Firefox`, `kitty`, `Luciole`, `ProtonPlus`) | `07-Evidencias-Tecnicas/firefox-pure-obsidian-vm.png`, `08-Topgrade-Proton/launcher-4-apps-vm.png` |

---

## 3. Correções Técnicas, Áudio, Entrada e Inatividade

- **Pilha gráfica (`80-validation.sh` / `50-desktop.sh`):** `vulkan-tools` (`1.4.363.0-1.1`) e `mesa-utils` (`9.0.0-7.1`) instalados com Mesa/RADV/VA-API 64/32 bits; `libva-utils` ausente conforme esperado. Na VM sem passthrough GPU, `glxinfo` operou em `llvmpipe` e `vulkaninfo` falhou por ausência de GPU física (hardware RDNA marcado `PENDENTE-HARDWARE`).
- **Energia / Anti-Inatividade:** `IdleAction=ignore`, `IdleActionSec=0` (`/etc/systemd/logind.conf.d/99-nox-no-idle.conf`), `swayidle`/`hypridle` ausentes e `nox-power.toml` com `lock`/`screen_off`/`lock_and_suspend` desativados. Comprovado empiricamente em `ACCEPT-B` com sessão gráfica aberta por **36 minutos ininterruptos sem interação** (`17:33` → `18:09`, `desktop-idle-live-vm.png`) mantendo tela ativa sem bloqueio/suspensão.
- **Teclado ANSI `us(intl)` e Acentuação:** Umbriel configurado com `layout = "us"`, `variant = "intl"`, `track_layout = "global"`, `repeat_rate = 25`, `repeat_delay = 600` e `~/.XCompose` com `<dead_acute> <c> : "ç" ccedilla`. Sintoma físico de chattering/tecla `M` no AULA F75 permanece `PENDENTE-HARDWARE` (não reproduzível em teclado virtual KVM).
- **Havit Fuxi H3 (`nox-fuxi-h3-fix`):** Regra udev `85-nox-fuxi-h3.rules` e unit `nox-fuxi-h3.path`/`service` atualizados para varredura multi-índice ALSA `Mic Capture Switch` + unmute PipeWire `alsa_input.*(fuxi|xiisound)` preservando mute intencional em `/var/lib/nox-archinstall/` (`PENDENTE-HARDWARE` para ciclo real de energia no headset).

---

## 4. Bateria de Atualizações, ProtonPlus e Snapshots (Seção 12.1)

Todas as provas abaixo foram executadas e registradas na VM limpa `ACCEPT-B` (`08-Topgrade-Proton/acceptB-battery-clean.log`, `acceptB-test4-multi-txn.log`, `acceptB-limine-snapshots-post-test4.txt`, `acceptB-post-restore.log`):

| Teste | Escopo Verificado | Resultado Observado |
|---|---|---|
| **1 — `pacman` normal** | `pacman -S --noconfirm tree` + `-Rns tree` | `snap-pac` criou `PRE/POST`; política `root` manteve apenas par mais recente (`#3/#4`) + hashes BLAKE2b 100% íntegros |
| **2 — `paru` AUR** | `paru -S --noconfirm --rebuild topgrade-bin` | Build e instalação via `paru` geraram `#5/#6`; cleanup manteve `2` snapshots |
| **3 — Snapshot manual + `pacman`** | Snapshot manual `#7` (`manual-keep-test`) + transação `jq` (`#8/#9`) | Snapshot manual `#7` preservado; política removeu pares automáticos antigos (`#5/#6`), mantendo `#7` + `#8/#9` |
| **4 — `topgrade` real multi-transação (`Repo + AUR`)** | Downgrade temporário local de `mesa-utils` (`9.0.0-0`) + `topgrade-bin` (`17.17.0-0`), seguido de **uma execução real** `/usr/local/bin/topgrade --yes` | `paru` atualizou `mesa-utils` (`9.0.0-0 → 9.0.0-7.1`, `#15/#16`) **e** compilou/atualizou `topgrade-bin` (`17.17.0-0 → 17.17.0-1`, `#17/#18`). `nox-snapper-cleanup` consolidou para **exatamente 1 par**: `PRE=#15` (Estado A) e `POST=#19` (`pre-number=15`, Estado C). `/boot/limine.conf` exibiu `///Ponto de Segurança` (`#15`) e `///Estado Atualizado` (`#19`), todos com BLAKE2b válidos |
| **5 — `topgrade` no-op** | `/usr/local/bin/topgrade --yes` sem pendências | Nenhum snapshot novo criado |
| **6 — `PRE` órfão (transação interrompida)** | Criação de `PRE=#12` (`interrupted-test`) + `nox-snapper-cleanup` | Preservaram-se snapshots existentes sem apagar ponto de recuperação válido |
| **7 — `ProtonPlus` + falha simulada** | `protonplus list`, `protonplus update all` e wrapper mock retornando `exit 1` | `protonplus update all` → `Already up to date` (real) e `topgrade --only protonplus` falhou isoladamente com `SIM_FAIL_RC=1` sem corromper snapshots |
| **8 — Kernel / `limine-update`** | `sudo limine-update` completo (mkinitcpio + `sbctl` + hooks pre/post) | Regenerou initramfs (`7.3.5-1-cachyos`), executou hooks `05`/`85`/`95`, e verificou `ALL_LIMINE_BLAKE2_HASHES_MATCH=True` (`7/7`) |
| **9 — Boot em Snapshot + Restore real (`--restore`)** | Boot direto via menu Limine em **`///Ponto de Segurança` (`#15`)** → verificação em `overlay` (`mesa-utils 9.0.0-0`, `topgrade-bin 17.17.0-0`) → `sudo limine-snapper-sync --restore` (`r` + Enter) → reboot → pós-reexecução `topgrade --yes` | Subvolume `/@` restaurado ao Estado A em Btrfs gravável (`subvolid=284`, `mesa-utils 9.0.0-0` e `topgrade-bin 17.17.0-0` confirmados após reboot), e em seguida atualizado novamente de volta para `9.0.0-7.1` + `17.17.0-1` (`#21/#25`) |
| **10 — Par `POST`/`PRE` final e limpeza** | Limpeza do snapshot `#20` (`backup before restore #15`) | Snapper `root` finalizado com exatamente o par `#21` (`pre`) e `#25` (`post`), zero restos temporários |
| **11 — `topgrade --dry-run`** | Execução via `/usr/local/bin/topgrade --dry-run` em `ACCEPT-A` e `ACCEPT-B` | `System update: OK`, `config-update: OK`, `ProtonPlus: OK` + notificação Noctalia (`topgrade-dryrun-kitty-vm.png`) |
| **12 — GUI ProtonPlus + Proton-CachyOS SLR** | Abertura do ProtonPlus e checagem `/usr/share/steam/compatibilitytools.d/` | `protonplus` (`0.6.8-2`) visível no launcher e funcional; `proton-cachyos-slr` (`1:11.0.20261015-1`) pré-instalado. Download automático de `GE-Proton` / `DWProton` documentado como dependente de instalação futura de um launcher de jogos (`Steam`/`Heroic`/`Lutris`/`Bottles`/`Faugus`) |

---

## 5. Secure Boot e Itens `PENDENTE-HARDWARE`

### 5.1 Estado do Secure Boot
- **Na instalação/VM:** `nox-secureboot-verify` passou `5/5` verificações em `ACCEPT-A` e `ACCEPT-B` (chaves privadas `sbctl` geradas, `/etc/default/limine` configurado, `/boot/EFI/limine/limine_x64.efi` e `/boot/EFI/BOOT/BOOTX64.EFI` assinados, 100% dos caminhos no `/boot/limine.conf` com hash BLAKE2b).
- **Enrolamento NVRAM OVMF (`ACCEPT-B`):** `sudo nox-secureboot-enroll --yes-enroll-uefi-keys --ignore-immutable` gravou chaves PK/KEK/db com certificados Microsoft no OVMF (`Setup Mode: Disabled`). A ativação final do bit `Secure Boot: Enabled` no menu UEFI da placa-mãe física (`nox-secureboot-verify --require-active` 6/6) é etapa de firmware pós-instalação no equipamento físico.

### 5.2 Itens `PENDENTE-HARDWARE` (Não Reproduzíveis Integralmente em KVM)
1. **Monitor físico dual (`DP-1` 2560×1440@165 Hz + `HDMI-A-1` 1920×1080@100 Hz rotação 90°)** com vídeo animado `nox-g5-runtime.webm` + `nox-aoc-runtime.webm` simultâneos.
2. **GPU AMD RX 9060 XT (RDNA) + `vulkaninfo` / `rocm-smi-lib` / `btop`** com aceleração de hardware real.
3. **Teclado AULA F75 físico** (verificação de ausência de chattering / múltiplas ocorrências da tecla `M` fora de hardware KVM).
4. **Headset Havit Fuxi H3 físico** (teste real de power-cycle / dongle + Bluetooth validando `nox-fuxi-h3-fix`).
5. **Placa Wi-Fi Intel AX210 + `iwlwifi`** e ativação do Secure Boot no UEFI BIOS físico (`nox-secureboot-verify --require-active` 6/6).
6. **ProtonPlus com launcher de jogos real instalado** (`Steam` / `Heroic` / `Lutris` / `Bottles` / `Faugus`) para download e detecção ativa de `GE-Proton` e `DWProton` via `protonplus update all`.

---

## 6. Recomendações ao Operador (`v1.0.0-rc10` → `v1.0.0`)

1. Inspecionar os artefatos visuais e logs em `/home/awerkori/Downloads/Aprovacao-Visual-Nox-Archinstall/REFINAMENTO-FINAL/` (`01-Referencias/` a `07-Relatorio/` e `MANIFEST.md`), além de `REVISAO-VISUAL-DEFINITIVA/` (Fastfetch e Limine aprovados).
2. Após testar em hardware físico (ou aprovar explicitamente o pacote visual/técnico da RC10), autorizar a publicação da release estável **`v1.0.0`**.
3. Até lá, **`v1.0.0-rc10`** permanece exclusivamente como pré-release no repositório `Awerkori/arch-install`.

---

## 8. Refinamento Visual Final (`REFINAMENTO-FINAL` — Feixe Global, Greeter & Lock Screen)

- **Feixe solar global (`tools/generate_nox_visuals.py`):** Corrigida a implementação anterior restrita à máscara metálica do ouro; implementada camada `draw_global_light_sweep` baseada em `Awerkori/Awerkori/assets/profile/hero.svg`, `ProjectNox-org/.github` e `banner-engine.mjs` (`sweepBeam` inclinado `-20°` atravessando fundo esquerdo, emblema, fundo direito e saída fora da tela em loop contínuo de `10.0s` para G5 `2560×1440` e AOC `1080×1920`).
- **Greeter Obsidian Purple real (`configs/greeter/sync.toml`, `greeter.toml`, `scripts/51-input-displays.sh`):** Adicionada a 16ª chave `shadow` e `sync.toml` com `scheme = "Synced"` para aplicar o cartão escuro `#140c24`, bordas `#6d28d9` e ação `#9333ea` (em substituição ao fallback azul/amarelo), sem chaves não reconhecidas no relógio.
- **Lock Screen unificada (`configs/noctalia/nox-theme.toml`, `configs/bin/nox-noctalia-layout`):** `blur_intensity = 0.0` e `tint_intensity = 0.0` para nitidez da neve cósmica, remoção da caixa redundante `show_unlock_hint = false`, adição do subtítulo de data alinhado ao Greeter e unificação tipográfica (`Outfit` + `Plus Jakarta Sans`). Validada ao vivo na VM `ACCEPT-B` (`mpvpaper` G5 em movimento, login no Greeter e Lock Screen animada com `LOCKSCREEN_ANIM_CHANGED_PIXELS=2867`).

---

## 7. Revisão Visual Definitiva (`v1.0.0-rc10` — Obsidian Purple & Ouro)

- **Pacote organizado para aprovação:** `/home/awerkori/Downloads/Aprovacao-Visual-Nox-Archinstall/REVISAO-VISUAL-DEFINITIVA/` (`01-Fastfetch/` a `08-Relatorio/` + `MANIFEST.md` com 36 arquivos e hashes SHA-256).
- **Mudanças visuais aplicadas:**
  - Substituição global de partículas amarelas/roxas de fundo pela `neveCosmica` oficial (`snowWhite`, `snowSilver`, `snowLilac` desfocadas) em `tools/generate_nox_visuals.py` para G5, AOC, Greeter, Lock Screen e Limine.
  - Feixe metálico diagonal oficial (`feixeLuminoso`) restrito à máscara dourada do emblema nos loops WebM/GIF (`nox-g5*`, `nox-aoc*`, `nox-lockscreen-emblem.gif`).
  - Remoção de geometria inventada: linha horizontal no G5, elipses gigantes e eixo vertical no AOC, oval gigante/divisor no Greeter (`hide_logo = true`, emblema superior integrado, relógio e cartão Obsidian Purple refinados) e colchetes/divisor no fundo do Lock Screen (layout unificado em `configs/bin/nox-noctalia-layout`).
  - Reprodução fiel do painel `Fastfetch` (`configs/bin/nox-fastfetch` + `tools/generate_braille_logo.py`), eliminando `\x1b[13G`, alinhando colunas `│` e bordas dos 4 quadros em modos cheio e split Dwindle, e preservando Lambda violeta sólido.
- **Validação em VM existente (`ACCEPT-B`):** boot pelo Limine atualizado (`limine-live-vm.png`), captura de Greeter e erro/login, `mpvpaper` G5 em movimento (`desktop-frame-1.png` vs `desktop-frame-2.png`), Lock Screen animado (`LOCKSCREEN_ANIM_CHANGED_PIXELS=1416`) com desbloqueio real e Fastfetch no Kitty cheio e em split (`fastfetch-kitty-full.png`, `fastfetch-kitty-split.png`), além de `24/24` testes unitários OK (`python3 -m unittest discover -s tests/unit -v`).

---

## 9. Rodada Final Dual-Monitor (`REFINAMENTO-DUAL-MONITOR` — G5 → AOC, Greeter, Lock Screen & Avatar)

- **Pacote entregue para aprovação:** `/home/awerkori/Downloads/Aprovacao-Visual-Nox-Archinstall/REFINAMENTO-DUAL-MONITOR/` (`01-Referencias/` a `08-Relatorio/` + `MANIFEST.md` e `RELATORIO-DUAL-MONITOR.md`).
- **Animação contínua G5 → AOC (`tools/generate_nox_visuals.py` + `configs/noctalia/plugins/mpvpaper/`):**
  - Timeline global única de `14.0 s` (`840` quadros a `60 fps` em WebM; `280` quadros a `20 fps` em GIF) calculada em espaço virtual contínuo (`Odyssey G5 [0,0]` `2560×1440` → `AOC 24B35 [2560,-350]` `1080×1920`), sem feixe duplicado e sem ping-pong.
  - Sincronizador leve por IPC Unix JSON via `socat` (`dual_sync = true`, checagem de drift a cada `3 s` em módulo `14.0 s` com `seek absolute+exact`, pausa/retomada coordenada em `session_locked`/`session_unlocked` e alinhamento automático em `onOutputsChanged`), com `nox-bundled` como última `[[plugins.source]]` em `nox-theme.toml`.
  - **Evidência:** prévia composta sintética `04-Animacao-Conjunta/preview-dual-monitor.webm`, teste live na VM `ACCEPT-B` (`mpvpaper` G5 em `Virtual-1`, `seek` exato via `socat`, `STAT=T<l` no Lock Screen e teste empírico com dois processos `mpv --vo=null` corrigindo `5.0 s` de desvio para `Δ = 0.016 s`). Travessia simultânea nas duas saídas físicas (`DP-*` + `HDMI-A-*`) permanece **`PENDENTE-HARDWARE`**.
- **Greeter, Lock Screen e Avatar:**
  - Greeter refinado com `corner_radius_scale = 1.05`, borda `#5b21b6`, superfície `#120a21` e ajuste de altura/diâmetro do emblema em `nox-greeter.png` (documentando ausência de `card_width` configurável no binário).
  - Lock Screen refinada sem `background_padding` (0 warnings em `noctalia config validate`), botões `[[shell.session.actions]]` em `variant = "outline"` eliminando o destaque coral sólido do `Shut Down`, GIF `360×360` animado e desbloqueio preservado.
  - Removida imposição de `nox-emblem.png` como `[shell].avatar_path` e documentada a ausência de `accountsservice` na RC10 (avatar customizado funciona no Noctalia Shell via Settings → Shell; compartilhamento com Greeter depende de instalação futura de `accountsservice`).
- **Testes unitários após alterações finais:** `25/25` OK em `tests/unit/test_nox.py`.

---

## 10. Adendo `DP-1` (Odyssey G5) e Revisão Plug-and-Play

- **Atualização de porta e EDID (`profiles/hardware.json`, `configs/bin/nox-display-profile`, `configs/bin/nox-noctalia-layout`, `configs/bin/nox-session-init`):**
  - `preferred_connectors` do monitor primário atualizado para `["DP-1", "DP-2"]` (G5 à esquerda em `[0, 0]`, `2560×1440@165`; AOC em `[2560, -350]`, `transform = "90"`, `1920×1080@100`).
  - Identificação em duas etapas estritas priorizando modelo/EDID (`Odyssey G5`/`Samsung` e `24B35`/`AOC`, incluindo leitura dos blocos descritores em `/sys/class/drm/card*-*/edid`) antes da ordem de conectores, evitando inversão de monitor primário ou troca de wallpapers por ordem de enumeração.
  - `nox-session-init` atualiza automaticamente `outputs.toml` e revalida `assignments.json` (`nox_mpv_layout_stale`) se os conectores ativos divergirem entre boots, preservando operação plug-and-play no primeiro login (`scripts/50-desktop.sh`, `51-input-displays.sh`, `53-appearance.sh`).
- **Limitação honesta:** conectores físicos reais (`DP-1` + `HDMI-A-*`) permanecem **`PENDENTE-HARDWARE`** até execução no computador físico (VM KVM expõe apenas `Virtual-1`).
