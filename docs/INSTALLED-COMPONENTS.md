# Inventário Completo — Nox Archinstall (`v1.0.0-rc9`)

> Documento de referência das instalações e configurações automatizadas pelo **Nox Archinstall** na pré-release **`v1.0.0-rc9`** (candidata final antes da publicação explícita da `v1.0.0`).
> Listagem completa e exata de todos os **651 pacotes** (explícitos e dependências) disponível em [`INSTALLED-PACKAGES.tsv`](INSTALLED-PACKAGES.tsv).

## Metadados da Revisão Documentada

- **Repositório:** `https://github.com/Awerkori/arch-install`
- **Pré-release validada:** `v1.0.0-rc9` (`https://github.com/Awerkori/arch-install/releases/tag/v1.0.0-rc9`)
- **Commit da revisão (`main`):** `dd6ad04e0736c78890b98d163d228dfb0054dbe2` (base `e7a94b4`)
- **SHA-256 do payload (`nox-archinstall-payload-v1.0.0-rc9.tar.gz`):** `cac833940ab868dfef32f319347f0e0c53b89301895e6262dae3165c529cacc5`
- **Base de comprovação:** Duas instalações limpas completas a partir da ISO oficial `archlinux-2026.11.01-x86_64.iso` (`ACCEPT-A` e `ACCEPT-B`), verificadas com `diff` nulo entre ambas.

### Contagem Total de Pacotes (`ACCEPT-A` e `ACCEPT-B`)

| Métrica | Quantidade | Observações |
|---|---:|---|
| **Total instalado** | **651** | Idêntico entre `ACCEPT-A` e `ACCEPT-B` (0 diferenças) |
| **Instalados explicitamente (`pacman -Qqe`)** | **93** | Base `archinstall` + módulos do Nox + `makedepends` AUR |
| **Instalados como dependências (`pacman -Qd`)** | **558** | Bibliotecas, toolchains, codecs e dependências transitivas |
| **Origem `cachyos-extra-znver4`** | 294 | Otimizados Zen 4 (`x86-64-v4`) |
| **Origem `cachyos-core-znver4`** | 117 | Núcleo otimizado Zen 4 |
| **Origem `extra` (Arch)** | 69 | Repositório oficial Arch |
| **Origem `multilib` (Arch 32-bit)** | 55 | Suporte 32 bits (`lib32-*`) |
| **Origem `cachyos-znver4`** | 48 | Pacotes específicos Zen 4 (`linux-cachyos`, `firefox-pure`, Mesa) |
| **Origem `core` (Arch)** | 35 | Base Arch |
| **Origem `cachyos`** | 32 | Keyring, mirrorlists, `paru`, `limine*`, `umbriel*`, `cachyos-settings` |
| **Origem `AUR/foreign`** | 1 | `luciole-git` (compilado em sandbox não-privileged `noxbuild`) |

---

## 1. Sistema Base, Kernel, Firmware e Microcode

| Componente | Função | Pacote | Origem | Classificação |
|---|---|---|---|---|
| Sistema Base | Conjunto mínimo Arch Linux | `base` (`3-3`) | Arch (`core`) | **Obrigatório** |
| Kernel Otimizado | Kernel CachyOS Zen 4 (com `BORE`/otimizações) | `linux-cachyos` (`7.3.5-1`) | `cachyos-znver4` | **Obrigatório** |
| Kernel Headers | Cabeçalhos para módulos/ferramentas de kernel | `linux-cachyos-headers` (`7.3.5-1`) | `cachyos-znver4` | **Obrigatório** |
| Initramfs | Gerador de initramfs (`zstd`, hook `sd-btrfs-overlayfs`) | `mkinitcpio` (`42.2-1`) | Arch (`core`) | **Obrigatório** |
| Firmware Linux | Blobs de firmware Wi-Fi/GPU/rede/periféricos | `linux-firmware` (`1:20261019-1`) | `cachyos` | **Obrigatório** |
| Microcode AMD | Atualizações de microcode para CPUs AMD | `amd-ucode` (`1:20261019-1`) | `cachyos` | **Obrigatório** |
| Compilação Base | Toolchain GCC/Make para pacotes e AUR | `base-devel` (`1-2`), `git` (`2.56.1-1.1`), `python` (`3.14.10-2`) | `core` / `cachyos-extra-znver4` / `cachyos-znver4` | **Obrigatório** |
| Privilégios | Elevação via grupo `wheel` com senha (sem `NOPASSWD`) | `sudo` (`1.9.17.p2-7.1`) | `cachyos-core-znver4` | **Obrigatório** |

> **Observação de estágio:** O kernel bootstrap `linux-zen` do `archinstall` é removido em `20-cachyos-kernel.sh` após a instalação de `linux-cachyos` + `linux-cachyos-headers`.

---

## 2. Gerenciadores de Pacotes e Repositórios

| Componente | Função | Pacote / Arquivo | Origem | Classificação |
|---|---|---|---|---|
| Pacman (fork CachyOS) | Gerenciador nativo com `Architecture = auto`, `Color`, `ParallelDownloads = 5` | `pacman` (dependência de `base`, fork `cachyos`) | `cachyos` | **Obrigatório** |
| Helper AUR | Assistente AUR oficial compilado pelo projeto CachyOS | `paru` (`2.2.0-2`) | `cachyos` | **Obrigatório** |
| Chaves & Mirrors | Chaves GPG CachyOS e listas padrão / Zen 4 | `cachyos-keyring`, `cachyos-mirrorlist`, `cachyos-v4-mirrorlist`, `cachyos-rate-mirrors` | `cachyos` | **Obrigatório** |

**Ordem de prioridade configurada em `/etc/pacman.conf`:**
1. `[cachyos-znver4]`
2. `[cachyos-core-znver4]`
3. `[cachyos-extra-znver4]`
4. `[cachyos]`
5. `[core]` → `[extra]` → `[multilib]`

> `paru-git`, `yay`, `hushmic-bin`, `htop`, `glances`, `neofetch`, `macchina`, `grub`, `grub-btrfs`, `os-prober`, `hyprland` e `sddm` são explicitamente proibidos na validação (`80-validation.sh`).

---

## 3. Interface Gráfica, Wayland e Sessão

| Componente | Função | Pacote | Origem | Classificação |
|---|---|---|---|---|
| Compositor Wayland | Compositor `wlroots` com layout padrão `dwindle` | `umbriel` (`0.1.0.r1569.88ba829-1`) | `cachyos` | **Obrigatório** |
| Shell Desktop | Barra, central de controle, notificações, tela de bloqueio, launcher (`sortByMostUsed`, `enableCategories: false`) e timeouts de inatividade desativados (`lock`/`screen-off`/`suspend`) | `noctalia` (`5.5.0-1.1`) | `cachyos-extra-znver4` | **Obrigatório** |
| Greeter & Display Manager | Tela de login (`greetd` na VT1) com tema escuro Noctalia | `greetd` (`0.10.3-2.1`), `noctalia-greeter` (`1.7.0-1.1`) | `cachyos-extra-znver4` | **Obrigatório** |
| Portais XDG | File picker, screencast e integração desktop Wayland/GTK | `xdg-desktop-portal`, `xdg-desktop-portal-umbriel`, `xdg-desktop-portal-gtk` | `cachyos-extra-znver4` / `cachyos` | **Obrigatório** |
| Polkit | Agente de autenticação gráfica de privilégios | `polkit`, `polkit-gnome` (`0.105-12.1`) | `cachyos-extra-znver4` | **Obrigatório** |
| Compatibilidade X11 | Camada XWayland para aplicativos legados | `xorg-xwayland` (`24.1.15-1.1`) | `cachyos-extra-znver4` | **Obrigatório** |

---

## 4. Aplicativos Instalados e Visibilidade no Launcher Noctalia

### 4.1 Aplicativos visíveis na listagem inicial (`All`)

| Aplicativo | Função | Pacote | Origem | Launcher (`All`) | Pesquisa | Classificação |
|---|---|---|---|---|---|---|
| **Firefox** (`Firefox Pure`) | Navegador web padrão (`http`/`https`/`html`, `MOZ_ENABLE_WAYLAND=1`) | `firefox-pure` (`160.0-1`) | `cachyos-znver4` | **Visível** | Visível | **Obrigatório** |
| **kitty** | Terminal padrão com `JetBrainsMono Nerd Font`, Bash e opacidade 0.94 | `kitty` (`0.50.0-1.1`) | `cachyos-extra-znver4` | **Visível** | Visível | **Obrigatório** |
| **Luciole** | Gerenciador de arquivos padrão (`inode/directory`, `Mod+E` / `Ctrl+E`) | `luciole-git` (`0.1.0.r363.g0b37f2cc7-1`) | AUR (`makepkg` `noxbuild`) | **Visível** | Visível | **Obrigatório** |

> Novos aplicativos pessoais instalados posteriormente pelo usuário (sem `NoDisplay=true`) aparecem automaticamente na listagem inicial `All`.

### 4.2 Ferramentas padrão CLI e aplicativos técnicos ocultos da listagem inicial

As entradas `.desktop` técnicas são ocultadas apenas via overlays XDG do usuário em `~/.local/share/applications/*.desktop` (`NoDisplay=true`), permanecendo intactas em `/usr/share/applications/` e acessíveis pela pesquisa global do Noctalia (ou prefixo `/tools`):

| Aplicativo / Ferramenta | Função | Pacote | Origem | Launcher Inicial | Pesquisa (`system-tools` / `/tools`) | Classificação |
|---|---|---|---|---|---|---|
| **btop** (`btop++`) | Monitor de recursos padrão no Kitty (`CPU/RAM/Swap/Disks/Net/Proc` + AMD GPU) | `btop` (`1.4.8-1.1`) + `rocm-smi-lib` (`10.1-1.1`) | `cachyos-extra-znver4` | Oculto | Pesquisável (`btop++`) e CLI (`btop`) | **Obrigatório** |
| **fastfetch** | Informações do sistema no Kitty (logo Arch Linux personalizável) | `fastfetch` (`2.71.0-1.1`) | `cachyos-extra-znver4` | Sem `.desktop` | CLI manual (`fastfetch`) | **Obrigatório** |
| **Noctalia** | Painel de configurações do shell Noctalia (`noctalia msg settings-open`) | `noctalia` (`5.5.0-1.1`) | `cachyos-extra-znver4` | Oculto | Pesquisável (`Noctalia`) | **Obrigatório** |
| **Limine-snapper-restore** | Utilitário gráfico de restauração de snapshots Btrfs | `limine-snapper-sync` (`1.32.1-1`) | `cachyos` | Oculto | Pesquisável (`Limine-snapper-restore`) | **Obrigatório** |
| **Qt5 Settings** / **Qt6 Settings** | Temas e plugins de plataforma Qt5/Qt6 (`darker` + `Fusion`) | `qt5ct` (`1.9-2.1`), `qt6ct` (`0.11-9.1`) | `cachyos-extra-znver4` | Oculto | Pesquisável (`Qt5`/`Qt6 Settings`) | **Obrigatório** |
| **GTK Settings** | Editor visual de tema GTK3 (`Adwaita-dark`) | `nwg-look` (`1.2.1-1.1`) | `cachyos-extra-znver4` | Oculto | Pesquisável (`GTK Settings`) | **Opcional visual** (ferramenta técnica mantida) |
| **Volume Control** | Controle gráfico de entradas/saídas PulseAudio/PipeWire | `pavucontrol` (`1:6.2-2.1`) | `cachyos-extra-znver4` | Oculto | Pesquisável (`Volume Control`) | **Opcional visual** (útil em diagnósticos) |
| **Qt V4L2 test / video capture** | Utilitários do pacote `v4l-utils` | `v4l-utils` (`1.32.0-2.1`, dep. de `ffmpeg`) | `cachyos-extra-znver4` | Oculto | Pesquisável | **Dependência** (`ffmpeg`) |

---

## 5. Aparência, Temas e Fontes

| Componente | Função | Pacote | Origem | Classificação |
|---|---|---|---|---|
| Tema & Paleta Nox | Identidade visual própria **Obsidian Purple** (preto cósmico, roxo profundo/vibrante, acento dourado discreto) via paleta Noctalia v2 + wallpaper exclusivo (`obsidian-purple.png`) + template Qt6/GTK3/GTK4/Kitty/Btop | Configs Nox (`ObsidianPurple.json` + templates) | Projeto | **Obrigatório** |
| Tema GTK Escuro | Tema `Adwaita-dark` em GTK3/GTK4 (`gtk-application-prefer-dark-theme=1`) | `adw-gtk-theme` (`6.5-1`), `gnome-themes-extra` (`1:3.28-1`) | Arch (`extra`) | **Obrigatório** |
| Configuração GTK/Qt | Ferramentas de esquema escuro (`darker` + `Fusion` + `QT_QPA_PLATFORMTHEME`) | `nwg-look`, `qt5ct`, `qt6ct` | `cachyos-extra-znver4` | **Obrigatório** (plugins Qt) |
| Fontes do Sistema | Suporte completo Latim, CJK, Emojis e fonte monoespaçada Nerd no Kitty | `noto-fonts`, `noto-fonts-cjk`, `noto-fonts-emoji`, `ttf-jetbrains-mono-nerd` | Arch (`extra`) | **Obrigatório** |
| Miniaturas / PDF / Arquivos | Suporte para Luciole (`gvfs`, PDFs, thumbnails de vídeo e compactação) | `gvfs`, `ffmpegthumbnailer`, `poppler`, `7zip` | Arch (`extra`) / `cachyos-extra-znver4` | **Obrigatório** (`7zip`/`gvfs`/preview) |
| Builddeps do Luciole | Instalados pelo `makepkg` durante o build do `luciole-git` | `meson`, `ninja`, `nlohmann-json`, `stb` | Arch (`extra`) / `cachyos-extra-znver4` | **Dependência de build** |

---

## 6. Boot, Secure Boot, Btrfs e Snapshots

| Componente | Função | Pacote | Origem | Classificação |
|---|---|---|---|---|
| Bootloader Limine | Menu gráfico UEFI (`[-] Arch Linux` → `Project Nox` + `[+] Snapshots`) | `limine` (`12.10.0-1`), `efibootmgr` (`18-4.1`) | `cachyos` / `cachyos-core-znver4` | **Obrigatório** |
| Integração Kernel & Snapshots | Hooks `mkinitcpio`/Limine, sync automático com Snapper e verificação BLAKE2 | `limine-mkinitcpio-hook` (`1.40.0-1`), `limine-snapper-sync` (`1.32.1-1`), `xxhash` | `cachyos` / `extra` | **Obrigatório** |
| Secure Boot | Gerenciamento de chaves UEFI exclusivas por máquina e assinatura EFI | `sbctl` (`0.18-2.1`) | `cachyos-extra-znver4` | **Obrigatório** |
| Snapshots Btrfs | Ferramentas Btrfs, Snapper (`root`), hooks `pacman` `PRE`/`POST` e watcher inotify | `btrfs-progs`, `snapper`, `snap-pac`, `inotify-tools` | `core` / `extra` / `cachyos-extra-znver4` | **Obrigatório** |

---

## 7. Rede, Áudio e Periféricos

| Componente | Função | Pacote | Origem | Classificação |
|---|---|---|---|---|
| Gerenciamento de Rede | NetworkManager + backend `iwd` (`wifi_backend.conf`, roaming, Wi-Fi powersave off) | `networkmanager` (`1.58.1-3`), `iwd` (`3.12-2.1`), `iw`, `ethtool` | `extra` / `cachyos-core-znver4` / `cachyos-extra-znver4` | **Obrigatório** |
| Áudio PipeWire | Servidor PipeWire + compatibilidade Pulse/ALSA/JACK/GStreamer e políticas WirePlumber | `pipewire`, `pipewire-pulse`, `pipewire-alsa`, `pipewire-jack`, `gst-plugin-pipewire`, `wireplumber`, `alsa-utils`, `libpulse` | `extra` / `cachyos-extra-znver4` | **Obrigatório** |
| Bluetooth | Pilha BlueZ (`FastConnectable = true`, `AutoEnable = true`, `ReconnectAttempts = 7`) | `bluez`, `bluez-utils` (`5.88-1.1`) | `cachyos-extra-znver4` | **Obrigatório** |
| Fix Headset Fuxi H3 | Regra udev + watcher + script dinâmico para microfone/perfil Bluetooth/dongle (`nox-fuxi-h3-fix`) | Configs Nox (`/etc/udev/rules.d/85-nox-fuxi-h3.rules` + user unit) | Script próprio do projeto | **Opcional** (só atua se hardware Havit Fuxi H3 presente) |
| Teclado ANSI (`us-intl`) & Energia | Umbriel `layout = "us"`, `variant = "intl"`, `repeat_rate = 25`, `repeat_delay = 600` + `~/.XCompose` (`' + c → ç`) e `logind` (`IdleAction=ignore`) | `configs/umbriel/config.toml`, `99-nox-no-idle.conf`, `.XCompose` | Projeto | **Obrigatório** |

> **HushMic removido:** `hushmic-bin` não é instalado e quaisquer resquícios de configuração/serviço são limpos automaticamente.

---

## 8. Otimizações (CPU, GPU, RAM, ZRAM, Scheduler e Armazenamento)

| Componente | Função | Pacote / Arquivo | Origem | Classificação |
|---|---|---|---|---|
| Drivers GPU AMD 64 + 32 bits | Mesa + RADV Vulkan + VA-API (`AMD_VULKAN_ICD=RADV`, cache `12G`; pacotes extras `vulkan-tools`/`libva-utils`/`mesa-utils` omitidos por padrão) | `mesa`, `lib32-mesa`, `vulkan-radeon`, `lib32-vulkan-radeon`, `vulkan-icd-loader`, `lib32-vulkan-icd-loader`, `vulkan-mesa-layers`, `lib32-vulkan-mesa-layers`, `libva`, `lib32-libva` | `cachyos-znver4` / `cachyos-extra-znver4` / `multilib` | **Obrigatório** |
| Scheduler `sched_ext` | `scx_loader` configurado com `scx_lavd` (modo `Gaming`) | `scx-scheds` (`1.1.4-2`), `scx-tools` (`1.1.3-1.1`) | `extra` / `cachyos-extra-znver4` | **Obrigatório** |
| Prioridade & IRQ & Jogos | Regras de prioridade, balanceamento IRQ e GameMode (usuário no grupo `gamemode`) | `ananicy-cpp`, `cachyos-ananicy-rules`, `irqbalance`, `gamemode`, `lib32-gamemode` | `cachyos-extra-znver4` / `cachyos` / `extra` / `multilib` | **Obrigatório** |
| Configurações CachyOS + ZRAM | ZRAM unificada (`zram-size = ram`, `zstd`, prioridade 100) + sysctls base | `cachyos-settings` (`1:1.4.4-1`) + `zram-generator` (dep.) | `cachyos` / `cachyos-extra-znver4` | **Obrigatório** |
| Swapfile em Subvolume Btrfs | Subvolume `@swap` (`/nox-swap/swapfile`, `nodatacow`, prioridade 10): 32 GiB físico (`RAM >= 24 GiB` e `>= 64 GiB` livres) ou 2 GiB em disco restrito/VM | Provisionado por `70-memory.sh` via `btrfs-progs` | — | **Obrigatório** (adaptativo) |
| Proteção OOMD & TRIM | `systemd-oomd` nos slices de usuários humanos (`user-<uid>.slice.d`) e `fstrim.timer` | `systemd` (base) | Arch (`core`) | **Obrigatório** |
| Sysctl Rede & Performance | `TCP BBR + fq` (`/etc/sysctl.d/99-bbr.conf`), tuning memória/IO (`/etc/sysctl.d/99-nox-performance.conf`) | Configs Nox + `modules-bbr.conf` | Projeto | **Obrigatório** |

---

## 9. Serviços, Hooks, Autostarts e Scripts do Sistema

### Serviços de Sistema Habilitados (`systemctl list-unit-files --state=enabled`)
- **Núcleo & Sessão:** `greetd.service`, `getty@.service`, `systemd-resolved.service`, `systemd-timesyncd.service`, `systemd-oomd.service`, `systemd-userdbd.socket`, `remote-fs.target`.
- **Rede & Bluetooth:** `NetworkManager.service`, `NetworkManager-dispatcher.service` (`NetworkManager-wait-online.service` e `iwd.service` desabilitados), `bluetooth.service`, `cachyos-iw-set-regdomain.path`.
- **Otimização & Manutenção:** `scx_loader.service`, `ananicy-cpp.service`, `irqbalance.service`, `limine-snapper-sync.service`, `cachyos-rate-mirrors.timer`, `fstrim.timer`, `snapper-cleanup.timer` (`snapper-timeline.timer` e `snapper-boot.timer` mascarados).

### Serviços de Usuário Habilitados Globalmente (`systemctl --global`) e Autostarts
- **User units (`umbriel-session.target.wants` / socket activation):**
  - `nox-session-setup.service` → executa `/usr/local/libexec/nox/nox-session-init` (perfil de monitores `nox-display-profile`, idioma/locale, esquema escuro, XDG padrão `firefox.desktop` + `dev.noctalia.luciole.desktop`, ajuste de áudio sem HushMic).
  - `nox-fuxi-h3.path` / `nox-fuxi-h3.service` → reage ao hotplug do headset Havit Fuxi H3.
  - `pipewire.socket`, `pipewire-pulse.socket`, `wireplumber.service`, `xdg-user-dirs.service`, `p11-kit-server.socket`.
- **XDG Autostart (`/etc/xdg/autostart/`):** `at-spi-dbus-bus.desktop`, `limine-restore-notify.desktop`, `limine-snapper-notify.desktop`, `xdg-user-dirs.desktop`.

### Hooks e Utilitários Próprios (`Nox Archinstall`)
- **Boot hooks (`/etc/boot/hooks/{pre.d,post.d}`):**
  - `05-nox-limine-naming-pre` & `85-nox-limine-naming-post` → preservam `//Project Nox`, `timeout: 5`, `default_entry: Arch Linux/Project Nox` e `remember_last_entry: no` sem quebrar `kernel-id=linux-cachyos`.
  - `95-nox-sbctl-fallback` → garante assinatura de `/boot/EFI/BOOT/BOOTX64.EFI` + `/boot/EFI/limine/limine_x64.efi` após `90-limine-enroll-config`.
- **Pacman hooks (`/etc/pacman.d/hooks/`):**
  - `90-mkinitcpio-install.hook` (`limine-mkinitcpio-hook`)
  - `zzz-99-nox-snapper-cleanup.hook` → mantém somente o par `PRE`+`POST` mais recente de snapshots em `root` via `nox-snapper-cleanup`.
- **Binários/helpers em `/usr/local/bin/` e `/usr/local/libexec/nox/`:**
  `nox-secureboot-enroll`, `nox-secureboot-verify`, `nox-display-profile`, `nox-fuxi-h3-fix`, `nox-first-boot`, `nox-session-init`, `nox-limine-normalize`, `nox-snapper-cleanup`, `nox-system-tools-list`, `nox-system-tools-launch`.

---

## 10. Diferenças: Instalação Física vs. Laboratório Virtual (QEMU/VM)

| Aspecto | Instalação Física Alvo (Zen 4 + RDNA + AX210) | Laboratório Virtual (`ACCEPT-A` / `ACCEPT-B`) |
|---|---|---|
| **Saídas de vídeo (`nox-display-profile`)** | Detecta `DP-1` (`2560x1440@165`, `[0, 0]`) + `HDMI-A-1` (`1920x1080@100`, `[2560, -350]`, `transform = "90"`) | Detecta saída única `Virtual-1` (`[0, 0]`, `normal`), evitando referências quebradas |
| **Swapfile `@swap` (`70-memory.sh`)** | **32 GiB** quando `RAM >= 24 GiB` e `>= 64 GiB` livres em `/` | **2 GiB** proporcionais na VM de 8 GiB RAM / 75 GiB Btrfs |
| **Placa Wi-Fi & Fuxi H3** | `10-iwlwifi.link` (casamento restrito `Driver=iwlwifi`), `iwlwifi-ax210.conf` e regra `85-nox-fuxi-h3.rules` ativos no hardware real | Regras presentes e inócuas na VM (sem interface `iwlwifi` nem headset USB/BT conectado) |
| **Chaves Secure Boot (`sbctl`)** | Geradas e registradas localmente no firmware físico da placa-mãe | Geradas e registradas isoladamente no NVRAM OVMF de cada VM (`ACCEPT-A` e `ACCEPT-B` com `Owner GUID` distintos) |
| **GPU acelerada (`btop` / Vulkan)** | `rocm-smi-lib` + Mesa/RADV na GPU AMD Radeon | Mesa `llvmpipe` / Virtio GPU 1.0 na VM |
| **Componentes exclusivos do harness de lab** | **Não instalados no sistema alvo** | Scripts em `lab/` no host (`vm_exec.py`, `send_keys.py`, `serve_lab.py`) e disco sentinela `/dev/vdb` |
