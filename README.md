# Nox Archinstall (`Awerkori/arch-install`)

Instalador reprodutível e opinativo de **Arch Linux + CachyOS Zen 4** com:

- **Bootloader:** Limine (`limine` + `limine-mkinitcpio-hook` + `limine-snapper-sync`), hierarquia visual `Arch Linux → Project Nox` + `Snapshots` com boot automático desassistido em 5s (`default_entry: Arch Linux/Project Nox`, `remember_last_entry: no`)
- **Secure Boot:** `sbctl` (chaves privadas geradas individualmente por máquina) + proteção criptográfica do `limine.conf` (`ENABLE_VERIFICATION=yes`, `ENABLE_ENROLL_LIMINE_CONFIG=yes`) + assinatura automática de `/boot/EFI/limine/limine_x64.efi` e fallback `/boot/EFI/BOOT/BOOTX64.EFI`
- **Filesystem & Snapshots:** Btrfs (`@`, `@home`, `@log`, `@pkg`, `@.snapshots`, `@swap`) + Snapper (`root`, política máxima de 2 snapshots `PRE` + `POST` após limpeza) + `snap-pac` + `btrfs-overlayfs`
- **Kernel & Repositórios:** `linux-cachyos` + `linux-cachyos-headers`, prioridade oficial CachyOS (`cachyos-znver4`, `cachyos-core-znver4`, `cachyos-extra-znver4`, `cachyos`) antes de `core`, `extra`, `multilib` + `cachyos/paru`
- **Ambiente Gráfico & Aplicativos Padrão:** `Umbriel` (layout padrão `dwindle` em todos os monitores/workspaces) + `Noctalia Shell` + `Noctalia Greeter` (`greetd`) + `Luciole` + `Kitty` (`Bash`) + `Firefox Pure` (`cachyos-znver4`, navegador padrão XDG) + launcher minimalista (`Kitty`, `Luciole`, `Firefox` + busca global de ferramentas técnicas) + `btop` + `fastfetch`
- **Idioma, Teclado & Região:** `en_CA.UTF-8` (`en_US.UTF-8` fallback), teclado `us` (`intl` / `us-acentos`) com acentuação e `ç` (`.XCompose`), fuso `America/Sao_Paulo`, domínio wireless `BR`
- **Desempenho & Hardware:** `scx_loader` (`scx_lavd` Gaming), `ananicy-cpp`, `irqbalance`, `gamemode`, `ZRAM` (prioridade 100) + `@swap` 2 GiB (prioridade 10), `systemd-oomd`, `TCP BBR + fq`, tuning `iwlwifi` AX210 + Bluetooth SBC-XQ/mSBC, PipeWire + WirePlumber + fix dinâmico `Fuxi H3` e driver Mesa/RADV 64+32 bits (`AMD_VULKAN_ICD=RADV`)

## Instalação limpa pela ISO oficial do Arch Linux

1. Inicie pela ISO oficial mais recente do Arch Linux com acesso à rede (`iwctl` / cabo).
2. Execute o `archinstall` carregando a configuração pública do repositório:

```bash
archinstall --config-url https://raw.githubusercontent.com/Awerkori/arch-install/main/user_configuration.json
```

3. No menu interativo do `archinstall`:
   - Escolha seu disco e configure o layout Btrfs (`@`, `@home`, `@log`, `@pkg`, `@.snapshots`, `@swap`) com partição EFI (`/boot`) recomendada de **4 GiB** (mínimo técnico 2 GiB).
   - Defina hostname, usuário administrador (grupo `wheel`) e senhas.
   - Confirme a instalação. O estágio `target-offline` baixa o payload verificado por **SHA-256** e aplica todo o provisionamento dentro do sistema alvo.

## Ativação do Secure Boot (pós-instalação)

Chaves privadas de Secure Boot **nunca** são armazenadas neste repositório. Cada máquina gera suas próprias chaves em `/var/lib/sbctl/keys/` durante a instalação.

Após o primeiro boot com o firmware em **Setup Mode**:

```bash
sudo nox-secureboot-enroll --yes-enroll-uefi-keys
sudo systemctl reboot
```

Ative o **Secure Boot** na UEFI/BIOS caso ainda esteja desabilitado e valide a cadeia completa após reiniciar:

```bash
sudo nox-secureboot-verify --require-active
```

> **Nota para GPU AMD:** `nox-secureboot-enroll` preserva automaticamente os certificados `--microsoft` por padrão para manter compatibilidade com Option ROMs UEFI de GPUs AMD. Use `--no-microsoft` apenas se desejar remover explicitamente chaves de terceiros.

## Ajuste fino dos monitores

A configuração padrão define Samsung Odyssey G5 (`2560x1440@165` em `[0, 0]`) como primário e AOC vertical (`1920x1080@100`, `transform = "90"`) em `[2560, -350]` (escala `1.0`).

Para ajustar o alinhamento na máquina física sem editar o arquivo principal, edite `~/.config/umbriel/outputs.local.toml` e execute `umbriel config reload`.

## Recuperação e verificação

- Checklist pós-instalação: [`docs/POST_INSTALL_CHECKS.md`](docs/POST_INSTALL_CHECKS.md)
- Recuperação via snapshots Limine: [`docs/RECOVERY.md`](docs/RECOVERY.md)
- Paridade de atalhos Hyprland → Umbriel: [`docs/KEYBINDS_MIGRATION.md`](docs/KEYBINDS_MIGRATION.md)
