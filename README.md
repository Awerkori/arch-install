# Nox Archinstall

**Minha instalação pessoal do Arch Linux**

O **Nox Archinstall** é meu projeto pessoal de instalação automatizada do Arch Linux. Criei este repositório para conseguir reinstalar meu sistema com os aplicativos, configurações, aparência e otimizações que utilizo no dia a dia.

O projeto foi desenvolvido especificamente para o meu computador e é executado a partir da ISO oficial do Arch Linux. Deixei o código disponível para quem quiser estudar, adaptar ou reproduzir essa instalação, mas ele não foi testado em outras configurações de hardware.

[Sobre o Nox Archinstall](#sobre-o-nox-archinstall) · [Hardware utilizado](#hardware-utilizado) · [O que vem instalado](#o-que-vem-instalado) · [Instalação](#instalação) · [Capturas de tela](#capturas-de-tela) · [Secure Boot](#secure-boot) · [Créditos e licença](#créditos-e-licença)

---

## Sobre o Nox Archinstall

Em vez de distribuir uma imagem ISO modificada ou exigir dezenas de etapas manuais após formatar o PC, o Nox Archinstall funciona diretamente sobre a mídia oficial do Arch Linux.

Um assistente simples no terminal conduz as três únicas escolhas necessárias — o SSD de destino, o nome de usuário e a senha — e aplica automaticamente o particionamento Btrfs, o kernel e os repositórios otimizados, a interface gráfica e os aplicativos. Ao reiniciar, o ambiente já abre pronto para uso no primeiro login.

---

## Hardware utilizado

**O Nox Archinstall foi desenvolvido para o computador pessoal abaixo. Seu funcionamento em outras configurações de hardware ainda não foi comprovado.**

| Componente | Modelo |
|---|---|
| Processador | AMD Ryzen 5 7500F |
| Placa-mãe | MSI PRO B650M-P |
| Placa de vídeo | Radeon RX 9060 XT |
| Wi-Fi / Bluetooth | Intel AX210 |
| Monitor principal | Samsung Odyssey G5 |
| Monitor secundário | AOC 24B35 |
| Headset | Havit Fuxi H3 |
| Teclado | AULA F75 |

**O projeto foi configurado e testado em máquinas virtuais, utilizando o hardware acima como referência de configuração. Não há garantia de compatibilidade com outros computadores.**

---

## O que vem instalado

### Sistema
- Arch Linux oficial
- Kernel `linux-cachyos`
- Repositórios CachyOS Zen 4
- Otimizações de desempenho aprovadas (`scx_lavd`, `ananicy-cpp`, `irqbalance`, `GameMode`, `TCP BBR` e drivers AMD Mesa/RADV 64 e 32 bits)

### Interface
- Umbriel (layout `dwindle`)
- Noctalia Shell
- Noctalia Greeter e Lock Screen
- Tema Obsidian Purple
- Wallpapers animados via `mpvpaper`

### Aplicativos
- Firefox Pure (exibido como Firefox)
- Kitty
- Luciole
- Fastfetch
- btop
- Topgrade
- ProtonPlus (com `proton-cachyos-slr`)

### Armazenamento e inicialização
- Btrfs com compressão ZSTD
- Snapper (snapshots automáticos antes e depois de atualizações)
- Limine (com verificação de integridade BLAKE2B)
- ZRAM
- Swapfile
- Preparação para Secure Boot (`sbctl`)

---

## Instalação

> **Atenção:** O disco selecionado durante a instalação será totalmente formatado e todos os dados existentes nele serão apagados. Faça backup dos seus arquivos pessoais antes de começar.

1. Baixe a ISO oficial do Arch Linux compatível (`archlinux-2026.11.01-x86_64.iso`, com `archinstall 4.5`).
2. Inicie o computador pelo pendrive em modo UEFI (com o Secure Boot desativado na BIOS).
3. Conecte-se à internet (via cabo de rede ou Wi-Fi com `iwctl`).
4. Execute o comando abaixo para baixar e iniciar o instalador:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/Awerkori/arch-install/main/bootstrap/nox-install.py -o /tmp/nox-install.py && python3 /tmp/nox-install.py
```

5. Selecione o SSD de destino, escolha seu nome de usuário e senha e confirme a formatação.
6. Aguarde a conclusão da instalação automática e reinicie o computador.

Para instruções detalhadas sobre preparação do pendrive, conexão Wi-Fi, requisitos de arquitetura e primeiro boot, consulte o **[Guia de Instalação Passo a Passo](docs/INSTALLATION.md)**.

---

## Capturas de tela

**Desktop principal — Umbriel + Noctalia Shell (`Obsidian Purple`)**

![Desktop Umbriel e Noctalia Shell](docs/screenshots/03-desktop-first-login.png)

| Menu de inicialização (Limine) | Tela de login (Noctalia Greeter) |
|---|---|
| ![Limine Boot Menu](docs/screenshots/01-limine-boot.png) | ![Noctalia Greeter](docs/screenshots/02-noctalia-greeter.png) |

| Launcher de aplicativos | Tela de bloqueio (Lock Screen) |
|---|---|
| ![Noctalia Launcher](docs/screenshots/04-noctalia-launcher.png) | ![Noctalia Lock Screen](docs/screenshots/05-noctalia-lockscreen.png) |

---

## Secure Boot

O Nox Archinstall já prepara a cadeia de inicialização com o **Limine** e o **`sbctl`**, gerando chaves locais exclusivas em cada instalação e assinando automaticamente o bootloader e o kernel. A ativação final do Secure Boot exige uma etapa posterior na BIOS/UEFI da placa-mãe.

- **Método geral — configuração mais simples:** [`docs/SECURE-BOOT.md`](docs/SECURE-BOOT.md)
- **Método MSI — PRO B650M-P, chaves Microsoft/OEM e FQ0001:** [`docs/SECURE-BOOT-MSI.md`](docs/SECURE-BOOT-MSI.md)
- **Manual de recuperação (ISO, Chroot, Snapshots e CMOS):** [`docs/RECOVERY.md`](docs/RECOVERY.md)

Outros guias úteis:
- **Verificações pós-instalação no hardware físico:** [`docs/POST_INSTALL_CHECKS.md`](docs/POST_INSTALL_CHECKS.md)
- **Referência de atalhos de teclado:** [`docs/KEYBINDS_MIGRATION.md`](docs/KEYBINDS_MIGRATION.md)

---

## Créditos e licença

Este projeto integra e configura ferramentas desenvolvidas pelas comunidades do **Arch Linux**, **CachyOS**, **Limine**, **`sbctl`**, **Snapper**, **Umbriel**, **Noctalia**, **Luciole**, **Kitty**, **Firefox**, **`mpvpaper`**, **Topgrade** e **ProtonPlus**. A lista completa de atribuições e licenças de terceiros está disponível em [`docs/CREDITS-AND-LICENSES.md`](docs/CREDITS-AND-LICENSES.md).

Os scripts e configurações próprios deste repositório são disponibilizados sob a licença **[GNU AGPLv3](LICENSE)**. Por se tratar de um projeto pessoal feito sob medida para o meu ambiente, o uso em outros computadores é por sua conta e risco e pode exigir adaptações.
