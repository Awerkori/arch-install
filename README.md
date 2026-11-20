<img src="configs/icons/nox-emblem.png" alt="Emblema Nox Archinstall" width="124" align="right" />

# Nox Archinstall

**Minha instalação pessoal do Arch Linux**

O **Nox Archinstall** é meu projeto pessoal de instalação automatizada do Arch Linux. Criei este repositório para conseguir reinstalar meu sistema com os aplicativos, configurações, aparência e otimizações que utilizo no dia a dia.

O projeto foi desenvolvido especificamente para o meu computador e é executado a partir da ISO oficial do Arch Linux. Deixei o código disponível para quem quiser estudar, adaptar ou reproduzir essa instalação, mas ele não foi testado em outras configurações de hardware.

[Sobre o Nox Archinstall](#sobre-o-nox-archinstall) · [Ambiente e funcionalidades](#ambiente-e-funcionalidades) · [Hardware utilizado](#hardware-utilizado) · [Instalação](#instalação) · [Capturas de tela](#capturas-de-tela) · [Secure Boot e recuperação](#secure-boot-e-recuperação) · [Créditos e licença](#créditos-e-licença)

---

## Sobre o Nox Archinstall

Reinstalar o Arch Linux manualmente sempre exigia repetir uma longa sequência de tarefas: particionar o SSD em Btrfs, criar subvolumes, configurar repositórios otimizados, instalar o bootloader, ajustar o ambiente Wayland, posicionar os dois monitores, corrigir detalhes de áudio e aplicar temas em cada aplicativo. O Nox Archinstall nasceu para automatizar todo esse processo de maneira reprodutível.

Em vez de distribuir uma imagem ISO própria, o projeto roda diretamente sobre a mídia oficial do Arch Linux. Um assistente interativo no terminal solicita apenas três informações — o SSD de destino, o nome de usuário e a senha — e conduz automaticamente toda a instalação e configuração do sistema. Ao reiniciar, o computador já inicia no menu personalizado do Limine, passa pelo Noctalia Greeter e abre a sessão gráfica pronta para uso no primeiro login.

---

## Ambiente e funcionalidades

### Sistema e desempenho

A base combina o **Arch Linux oficial** com o kernel e os repositórios do **CachyOS** compilados para a arquitetura **AMD Zen 4 (`x86-64-v4`)**, priorizando baixa latência, resposta rápida da interface e estabilidade em jogos e uso diário.

- **Kernel `linux-cachyos`:** único kernel final instalado no sistema, acompanhado de seus headers e ajustado para cargas interativas de desktop.
- **Repositórios CachyOS Zen 4:** pacotes otimizados para a microarquitetura Zen 4 configurados acima dos repositórios oficiais do Arch Linux, utilizando o `pacman` do CachyOS e o helper AUR `paru`.
- **Gráficos AMD Mesa/RADV:** pilha gráfica aberta completa em 64 e 32 bits (`mesa`, `lib32-mesa`, `vulkan-radeon`, `lib32-vulkan-radeon` e `rocm-smi-lib`) pronta para Wayland e Vulkan.
- **Escalonamento e gerenciamento de recursos:** integração do escalonador BPF `scx_lavd` (via `scx_loader`), `ananicy-cpp`, `irqbalance` e `GameMode` para manter a fluidez em aplicativos em primeiro plano.
- **Rede e conectividade:** `NetworkManager` com backend `iwd`, resolução DNS via `systemd-resolved`, controle de congestionamento TCP `BBR` com fila `fq` e ajustes para Wi-Fi e Bluetooth.

### Ambiente gráfico

A interface gráfica foi construída para funcionar como um ambiente Wayland coeso, e não como uma coleção de programas isolados. Toda a experiência visual segue a identidade **Obsidian Purple** — fundo escuro profundo combinado a acentos em roxo e dourado — desde a tela de boot até os aplicativos da sessão.

- **Umbriel (layout `dwindle`):** compositor Wayland responsável pelo gerenciamento dinâmico de janelas em layout `dwindle`, atalhos de teclado e configuração automática da topologia dual-monitor.
- **Noctalia Shell:** barra superior integrada com indicadores de sistema, notificações, controle de áudio/rede e um **launcher minimalista**, que exibe por padrão apenas os aplicativos principais do dia a dia (mantendo utilitários técnicos acessíveis via busca ou pelo comando `/tools`).
- **Noctalia Greeter e Lock Screen:** tela de login inicial (`greetd`) e tela de bloqueio de sessão alinhadas à mesma tipografia, paleta de cores e emblema do restante do desktop.
- **Wallpapers animados (`mpvpaper`):** reprodução fluida de planos de fundo em vídeo com sincronização contínua entre o monitor principal horizontal e o monitor secundário vertical.
- **Integração visual completa:** tema escuro Obsidian Purple aplicado de forma consistente no terminal Kitty, em aplicativos GTK3/GTK4 e Qt5/Qt6, cursores, ícones e no navegador.

### Aplicativos

O sistema já vem com um conjunto enxuto de aplicativos pré-configurados e integrados aos atalhos do teclado e ao launcher:

- **Navegação e produtividade:** **Firefox** (pacote `firefox-pure` do CachyOS, exibido como Firefox e definido como navegador padrão com tema escuro integrado), **Kitty** (terminal principal acelerado por GPU, configurado com `bash`) e **Luciole** (`luciole-git`, gerenciador de arquivos gráfico).
- **Monitoramento e manutenção:** **Fastfetch** (painel visual personalizado exibido ao abrir o terminal com resumo do sistema e hardware), **btop** (monitor de recursos em tempo real com tema Obsidian Purple) e **Topgrade** (ferramenta de atualização completa do sistema integrada automaticamente à criação de snapshots do Snapper e ao ProtonPlus).
- **Jogos:** **ProtonPlus** (gerenciador gráfico de camadas de compatibilidade disponível no launcher) acompanhado do **`proton-cachyos-slr`** pré-instalado.

### Armazenamento e recuperação

O armazenamento é estruturado em **Btrfs** para separar os arquivos do sistema operacional dos arquivos pessoais em `/home` e integrar snapshots diretamente ao menu de inicialização, facilitando o retorno a um estado anterior caso alguma atualização apresente problemas.

- **Btrfs com compressão ZSTD (`zstd:3`):** organização automática em subvolumes dedicados para raiz do sistema, `/home`, logs, cache de pacotes, snapshots e swap.
- **Snapper e snapshots `PRE`/`POST`:** criação automática de pontos de restauração antes e depois de atualizações de pacotes ou execuções do Topgrade, com política enxuta de retenção.
- **Bootloader Limine com verificação BLAKE2B:** menu de boot com acesso direto aos snapshots do Snapper e verificação criptográfica BLAKE2B do arquivo `limine.conf` inscrita no binário EFI.
- **ZRAM e Swapfile:** combinação de memória **ZRAM** comprimida com `zstd` (alta prioridade) e um **swapfile Btrfs NOCOW** dedicado em disco, acompanhados do `systemd-oomd`.
- **Preparação para Secure Boot (`sbctl`):** geração local de chaves exclusivas durante a instalação e assinatura automática do Limine e do kernel, deixando o sistema pronto para o cadastro das chaves na BIOS.

---

## Hardware utilizado

**O Nox Archinstall foi desenvolvido especificamente para o computador pessoal abaixo. A instalação foi testada em máquinas virtuais, mas seu funcionamento em outros computadores físicos ainda não foi comprovado.**

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

A instalação aplica ajustes feitos sob medida para esse conjunto — incluindo repositórios exigindo instruções `x86-64-v4` (Zen 4), pilha gráfica AMD RADV, posicionamento automático do monitor Samsung Odyssey G5 (`2560x1440@165Hz` em `DP-1`) ao lado do AOC vertical (`1920x1080@100Hz` rotacionado a 90° em `HDMI-A-1`), regra de áudio para o receptor USB do headset Havit Fuxi H3 e layout de teclado `us-intl` com suporte a `ç` para o AULA F75. Os pré-requisitos obrigatórios de instalação estão detalhados em [`docs/INSTALLATION.md`](docs/INSTALLATION.md).

---

## Instalação

> **Atenção: o disco selecionado será formatado e seus dados serão apagados. Faça backup antes de continuar.**

O assistente conduz a escolha do SSD, do nome de usuário e da senha (utilizada também pelo `sudo`, mantendo a conta `root` bloqueada por segurança e definindo o hostname padrão `Nox-Device-PC`), enquanto o particionamento e a configuração completa do ambiente ocorrem automaticamente.

1. Baixe a ISO oficial do Arch Linux compatível (`archlinux-2026.11.01-x86_64.iso`, com `archinstall 4.5`).
2. Inicie o computador pelo pendrive em modo **UEFI** (com o **Secure Boot desativado** na BIOS durante o boot da ISO).
3. Conecte-se à internet (via cabo de rede Ethernet ou Wi-Fi utilizando `iwctl`).
4. No terminal da ISO, execute o comando abaixo para baixar e iniciar o assistente:

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/Awerkori/arch-install/main/bootstrap/nox-install.py -o /tmp/nox-install.py && python3 /tmp/nox-install.py
```

5. Escolha o número correspondente ao SSD de destino na lista exibida.
6. Defina seu nome de usuário em letras minúsculas e digite sua senha duas vezes.
7. Confirme o nome do dispositivo e autorize a formatação para iniciar a instalação automática.
8. Aguarde a conclusão de todas as etapas, remova o pendrive e reinicie o computador.

Para instruções detalhadas sobre preparação da mídia, conexão Wi-Fi passo a passo e verificações de primeiro boot, consulte o **[Guia de Instalação Completo (`docs/INSTALLATION.md`)](docs/INSTALLATION.md)**.

---

## Capturas de tela

Capturas reais do ambiente instalado pelo Nox Archinstall:

### Desktop principal

Sessão Wayland com **Umbriel**, barra superior do **Noctalia Shell** e wallpaper animado reproduzido via `mpvpaper` no primeiro login:

![Desktop principal — Umbriel e Noctalia Shell](docs/screenshots/03-desktop-first-login.png)

### Galeria complementar

| Menu de inicialização (Limine) | Tela de login (Noctalia Greeter) |
|---|---|
| ![Menu Limine](docs/screenshots/01-limine-boot.png) | ![Noctalia Greeter](docs/screenshots/02-noctalia-greeter.png) |

| Launcher minimalista (Noctalia Shell) | Tela de bloqueio (Noctalia Lock Screen) |
|---|---|
| ![Launcher Noctalia](docs/screenshots/04-noctalia-launcher.png) | ![Noctalia Lock Screen](docs/screenshots/05-noctalia-lockscreen.png) |

---

## Secure Boot e recuperação

Durante a instalação, o Nox Archinstall configura o **Limine** com verificação BLAKE2B do arquivo `limine.conf` e utiliza o **`sbctl`** para gerar chaves criptográficas locais exclusivas da máquina e assinar o bootloader e o kernel. A ativação final do Secure Boot no firmware UEFI requer um procedimento consciente após o primeiro boot.

- **Guia geral de Secure Boot — [`docs/SECURE-BOOT.md`](docs/SECURE-BOOT.md)**  
  Explica de forma didática o funcionamento das chaves UEFI (`PK`, `KEK`, `db`, `dbx`, Setup Mode, Option ROM e BLAKE2B) e apresenta o procedimento geral simplificado usando os helpers do projeto.

- **Guia específico para MSI PRO B650M-P — [`docs/SECURE-BOOT-MSI.md`](docs/SECURE-BOOT-MSI.md)**  
  Documenta passo a passo o caso particular da placa-mãe MSI PRO B650M-P em conjunto com o Ryzen 5 7500F (sem vídeo integrado) e a Radeon RX 9060 XT, cobrindo chaves Microsoft/OEM, entrada em Setup Mode, proteção da Option ROM da GPU e correção do alerta `FQ0001`.

- **Guia de recuperação — [`docs/RECOVERY.md`](docs/RECOVERY.md)**  
  Reúne os procedimentos para recuperação de boot pela ISO oficial do Arch Linux, restauração de snapshots Btrfs/Snapper pelo Limine ou via `arch-chroot`, ressincronização de assinaturas EFI e reset de CMOS.

Documentação complementar:
- **Checklist pós-instalação no hardware físico:** [`docs/POST_INSTALL_CHECKS.md`](docs/POST_INSTALL_CHECKS.md)
- **Referência de atalhos de teclado:** [`docs/KEYBINDS_MIGRATION.md`](docs/KEYBINDS_MIGRATION.md)

---

## Créditos e licença

O Nox Archinstall reúne e configura softwares desenvolvidos pelas comunidades do **Arch Linux**, **`archinstall`**, **CachyOS**, **Limine**, **`sbctl`**, **Snapper**, **Umbriel**, **Noctalia**, **Luciole**, **Kitty**, **Firefox**, **`mpvpaper`**, **btop**, **Fastfetch**, **Topgrade** e **ProtonPlus**. As atribuições detalhadas e licenças dos componentes de terceiros estão documentadas em [`docs/CREDITS-AND-LICENSES.md`](docs/CREDITS-AND-LICENSES.md).

Os scripts, utilitários e configurações próprios deste repositório são distribuídos sob a licença **[GNU AGPLv3](LICENSE)**.
