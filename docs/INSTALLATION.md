# Guia de Instalação Passo a Passo — Project Nox (`v1.0.0` / Hardening `v1.0.1`)

Este guia explica, do começo ao fim e sem exigir experiência avançada com o `archinstall`, como instalar o **Project Nox / Nox Archinstall** a partir da mídia oficial do Arch Linux mantendo verificação criptográfica de integridade em todos os estágios.

O fluxo completo resume-se a:

> **ISO oficial do Arch Linux → Conexão com a Internet → Comando Oficial Verificado (SHA-256) → Escolha do SSD → Confirmação Destrutiva do Dispositivo → Nome de Usuário → Senha e Confirmação → Confirmação Final → Instalação Automática → Reinicialização.**

---

## 1. Antes da instalação (Pré-requisitos e Preparação)

### 1.1. Faça backup dos seus arquivos pessoais
A instalação do Project Nox **formatará integralmente o SSD escolhido**, recriando a tabela de partições GPT (`/boot` de 4 GiB em FAT32 + partição raiz em Btrfs). Copie qualquer documento, chave, foto ou projeto importante para um disco externo ou nuvem antes de iniciar.

### 1.2. Requisitos mínimos do computador
- **Processador (CPU):** compatível com **`x86-64-v4`** (AMD Ryzen séries 7000/9000 — Zen 4 / Zen 5). O instalador verifica esse requisito automaticamente na etapa `00-preflight` porque utiliza os repositórios otimizados `cachyos-znver4`.
- **Modo de inicialização da placa-mãe:** **UEFI 64 bits** (modo CSM / Legacy BIOS desativado).
- **Espaço livre no SSD de destino:** mínimo técnico de **20 GiB** (recomendado **64 GiB ou mais**; em máquinas físicas com `>= 24 GiB` de RAM e disco amplo, o instalador dimensiona o swapfile Btrfs de 32 GiB automaticamente).
- **Conexão ativa com a internet:** necessária durante toda a instalação para baixar os pacotes oficiais do Arch Linux, do CachyOS e o payload verificado da versão.

### 1.3. ISO oficial homologada e versão do `archinstall`
- O Project Nox **não** possui ISO própria: você deve usar a **ISO oficial do Arch Linux**.
- O instalador foi homologado na ISO oficial **`archlinux-2026.11.01-x86_64.iso`**, que traz o **`archinstall 4.5`**.
- Por segurança, o assistente `nox-install.py` verifica automaticamente se está rodando como `root` em modo UEFI dentro da ISO oficial (`/run/archiso`) e se a versão do `archinstall` pertence à série homologada **`4.5`** (`4.5` ou `4.5.*`), bloqueando qualquer execução acidental no sistema hospedeiro.

### 1.4. Por que o Secure Boot deve estar desativado para iniciar a ISO oficial
Em configurações padrão de fábrica, a ISO oficial do Arch Linux pode ser bloqueada caso o **Secure Boot** esteja ativo na placa-mãe.

- **Recomendação obrigatória para a instalação:** antes de dar boot pelo pendrive da ISO do Arch Linux, entre na BIOS/UEFI (tecla `Del` na MSI PRO B650M-P) e confirme que **Secure Boot** está como **`Disabled`**.
- **Não apague nem altere as chaves do firmware antes de instalar o sistema.** As etapas 1, 2 e 3 do Secure Boot (geração das chaves locais `sbctl`, assinatura dos binários EFI/kernel e inscrição do hash BLAKE2B em `/boot/limine.conf`) são preparadas automaticamente durante a instalação. As etapas 4 e 5 (inscrição das chaves na NVRAM e ativação do Secure Boot na BIOS) serão realizadas depois, com o sistema já instalado e funcionando, seguindo [`docs/SECURE-BOOT.md`](SECURE-BOOT.md) ou [`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md).

### 1.5. Como confirmar que a ISO iniciou em modo UEFI
Assim que o pendrive carregar e você cair no prompt `root@archiso ~ #`, confirme que o sistema iniciou em modo UEFI executando:

```bash
ls /sys/firmware/efi/efivars
```

- **Resultado esperado:** uma lista de variáveis EFI é exibida na tela. (Se o diretório não existir, a placa-mãe iniciou o pendrive em modo Legacy/CSM; reinicie na BIOS e selecione a entrada `UEFI: <seu pendrive>`).

---

## 2. Conexão à Internet na ISO Oficial

### 2.1. Conexão via cabo de rede (Ethernet)
Se o computador estiver conectado por cabo Ethernet ao roteador, a ISO oficial do Arch Linux obtém endereço IP automaticamente via DHCP (`systemd-networkd`). Pule para a [Seção 2.3](#23-como-confirmar-a-conectividade).

### 2.2. Conexão via Wi-Fi (`iwctl`)
Se for instalar usando Wi-Fi (como a placa **Intel AX210**), utilize o utilitário nativo `iwctl` da ISO do Arch Linux:

1. Liste sua interface Wi-Fi (geralmente `wlan0`):
   ```bash
   iwctl device list
   ```
2. Faça a varredura e liste as redes disponíveis:
   ```bash
   iwctl station wlan0 scan
   iwctl station wlan0 get-networks
   ```
3. Conecte-se à sua rede Wi-Fi (substitua `NOME_DA_REDE` pelo SSID exato; a senha será solicitada a seguir):
   ```bash
   iwctl station wlan0 connect "NOME_DA_REDE"
   ```
4. Aguarde cerca de 5 segundos para a atribuição de IP.

### 2.3. Como confirmar a conectividade
Execute no terminal da ISO:

```bash
curl -I https://archlinux.org
```

- **Resultado esperado:** resposta contendo `HTTP/2 200` (ou `HTTP/1.1 200 OK`).
- **Se DNS ou HTTPS falhar:**
  - Verifique se o relógio do sistema na BIOS está com data coerente: `timedatectl status` (ative a sincronização com `timedatectl set-ntp true`).
  - Confira se a interface recebeu endereço IP: `ip addr show`.

---

## 3. Cadeia de Confiança e Comando Oficial de Instalação

O Project Nox utiliza uma **única cadeia oficial de instalação** baseada em **referências imutáveis de commit** e **verificação SHA-256 independente em todos os estágios**, sem executar código remoto não verificado e sem depender de arquivos mutáveis da branch `main`:

| Estágio | Artefato | Referência Imutável (`v1.0.1`) | SHA-256 Verificado antes do uso |
|---|---|---|---|
| **1. Iniciador** | [`i`](../i) | Commit `9504584cd8a01936e0588a900c8c2dba88b90d7c` | `9a752b29f43f5f68224e5693375f849ec818d182150d571861e596ca7ef67c75` |
| **2. Bootstrap** | [`bootstrap/nox-install.py`](../bootstrap/nox-install.py) | Commit `5f01eaaed8744fc1049e9e97e8d953f638361e24` | `0963baf3832952591874853bf715c9fe059672cc33af9ed0d9b19635ed792a38` |
| **3. Configuração** | [`user_configuration.json`](../user_configuration.json) | Commit `48ef35686a2fb948ad9b1b96621019ba7d47611e` | `d815b8577d268ded529da1a45ba753861ce75b333ff331b6058967ad9625404a` |
| **4. Payload** | `nox-archinstall-payload-v1.0.1.tar.gz` | Candidato `v1.0.1` (`hardening/v1.0.1`) | `7dcc5acea5feab877ab18c4677656eae9b85358dddccd550e43f8d09c36d52c8` |

> **Nota sobre o modelo de segurança e suas limitações:** Como o projeto não utiliza infraestrutura externa de chaves de assinatura digital pré-instaladas na ISO oficial do Arch Linux, a autenticidade da cadeia é estabelecida pela pinagem criptográfica de hashes SHA-256 combinada a URLs imutáveis por commit SHA sobre HTTPS/TLSv1.2+ (com bloqueio de downgrade HTTP em redirecionamentos). A raiz de confiança parte do comando e hash SHA-256 do Estágio 1 copiados pelo operador a partir desta documentação.

### Opção 1 — Comando oficial verificado em linha única (Recomendado)

```bash
sh -c 'set -eu; umask 077; f=$(mktemp /tmp/nox-i.XXXXXX); trap "rm -f \"$f\"" EXIT INT TERM; curl --proto "=https" --proto-redir "=https" --tlsv1.2 -fsSL https://raw.githubusercontent.com/Awerkori/arch-install/9504584cd8a01936e0588a900c8c2dba88b90d7c/i -o "$f"; printf "%s  %s\n" "9a752b29f43f5f68224e5693375f849ec818d182150d571861e596ca7ef67c75" "$f" | sha256sum -c -; sh "$f"'
```

### Opção 2 — Download, verificação SHA-256 e inspeção manual passo a passo

Se desejar inspecionar o iniciador antes de executá-lo, execute os passos abaixo na ordem exata (o arquivo nunca é executado antes da verificação `sha256sum -c -`):

```bash
umask 077
curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/Awerkori/arch-install/9504584cd8a01936e0588a900c8c2dba88b90d7c/i -o /tmp/nox-i
printf '%s  /tmp/nox-i\n' '9a752b29f43f5f68224e5693375f849ec818d182150d571861e596ca7ef67c75' | sha256sum -c -
less /tmp/nox-i
sh /tmp/nox-i
rm -f /tmp/nox-i
```

### Referência da release estável publicada `v1.0.0` (Imutável)

Caso deseje executar especificamente os artefatos congelados da release estável [`v1.0.0`](https://github.com/Awerkori/arch-install/releases/tag/v1.0.0), utilize a verificação explícita dos hashes publicados da `v1.0.0`:

```bash
umask 077
curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fsSL https://github.com/Awerkori/arch-install/releases/download/v1.0.0/nox-install.py -o /tmp/nox-install.py
printf '%s  /tmp/nox-install.py\n' '9a752b29f43f5f68224e5693375f849ec818d182150d571861e596ca7ef67c75' | sha256sum -c -
curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/Awerkori/arch-install/32c074ca3819d261a774b92ee4c7359411b963d5/user_configuration.json -o /tmp/nox-cfg.json
printf '%s  /tmp/nox-cfg.json\n' '9a752b29f43f5f68224e5693375f849ec818d182150d571861e596ca7ef67c75' | sha256sum -c -
python3 /tmp/nox-install.py --config /tmp/nox-cfg.json
rm -f /tmp/nox-install.py /tmp/nox-cfg.json
```

### O que o assistente verifica automaticamente antes de tocar no disco
1. Confirma que você está em um terminal interativo dentro da ISO oficial do Arch Linux (`/run/archiso`) em modo UEFI com **`archinstall 4.5`**.
2. Baixa via HTTPS a configuração base oficial de commit imutável e **valida o SHA-256 dos bytes brutos antes de interpretar o JSON**.
3. Valida o formato, esquema HTTPS e hash **SHA-256** do payload da versão e testa a conectividade HTTPS sem permitir downgrade para HTTP.
4. Lista os discos elegíveis (`>= 20 GiB`, excluindo a mídia da ISO) para que você escolha o SSD com segurança.

---

## 4. As 5 Etapas Interativas do Assistente e Aviso Destrutivo

> **AVISO CRÍTICO:** O disco selecionado na etapa `[1/4]` terá **todas as suas partições e dados apagados permanentemente**. Nunca tente adivinhar qual disco escolher.

### 4.1. Como identificar o SSD correto na lista (`[1/4]`)
O assistente exibe cada disco elegível com quatro informações claras:
1. **Tipo e barramento:** `[INTERNO]` vs `[USB/REMOVIVEL]` e o protocolo (`[nvme]`, `[sata]`, `[usb]`). O pendrive da própria ISO do Arch Linux já é filtrado automaticamente para não aparecer como destino.
2. **Caminho do dispositivo:** por exemplo, `/dev/nvme0n1` ou `/dev/sda`.
3. **Capacidade total em GiB:** por exemplo, `(931.5 GiB)` para um SSD de 1 TB ou `(465.8 GiB)` para um SSD de 500 GB.
4. **Modelo físico e identificador persistente (`by-id`):** por exemplo, `Kingston KC3000`, `WD Black SN770`, `Samsung SSD 980`.

### 4.2. Dupla confirmação de segurança (`[1/4]`, `[2/4]` e confirmação final)
Para evitar qualquer formatação acidental por erro de digitação:
1. **Escolha do SSD (`[1/4]`):** digite o **número** correspondente ao SSD na lista (por exemplo, `1`) — nenhum disco é selecionado automaticamente se você apenas apertar `Enter`.
2. **Confirmação destrutiva do dispositivo (`[2/4]`):** o assistente mostra o resumo do disco escolhido e exige que você **digite exatamente o nome curto do dispositivo** (por exemplo, `nvme0n1` ou `vda`). Se o texto digitado não coincidir, a instalação é cancelada imediatamente sem alterar nada.
3. **Confirmação final antes de formatar:** após informar usuário e senha, o assistente apresenta o quadro **`RESUMO FINAL ANTES DE FORMATAR`** e pergunta `Confirmar e iniciar a instalacao agora? [s/N]:`. Nenhuma partição é tocada antes de você responder `s` nessa última confirmação.

---

## 5. Usuário, Senha e Privilégios (`sudo`)

Nas etapas `[3/4]` e `[4/4]`:

1. **Nome de usuário (`[3/4]`):**
   - Digite o nome do seu usuário principal em letras minúsculas (por exemplo, `awerkori`).
   - O nome deve começar com letra minúscula ou `_` e conter apenas letras minúsculas, números, `_` ou `-` (máximo de 32 caracteres). Contas reservadas como `root`, `greeter` ou `noxbuild` são recusadas.
2. **Definição e confirmação da senha (`[4/4]`):**
   - Digite sua senha e pressione `Enter`; em seguida, digite a mesma senha novamente para confirmar.
   - Por segurança, **nenhum caractere ou asterisco aparece na tela** enquanto você digita a senha, e a senha em texto puro é convertida imediatamente em hash SHA-512 (`$6$`) dentro de `tmpfs` em RAM (`/dev/shm`, permissão `0700`/`0600`), sendo removida dos diretórios de log ao final da execução.
3. **Como funcionam o `sudo` e a conta `root` no Project Nox:**
   - Seu usuário é adicionado automaticamente ao grupo `wheel`.
   - Sempre que precisar executar comandos administrativos (`sudo ...`), você utilizará **a sua própria senha de usuário** (sem regras `NOPASSWD`).
   - A conta `root` permanece **bloqueada para login direto** (`passwd -S root` → `L`).

Quando o processo terminar e voltar ao prompt da ISO, reinicie o computador e remova o pendrive:

```bash
reboot
```

---

## 6. Depois da instalação (Primeiro Boot e Primeiro Login)

Nenhuma configuração manual é necessária após reiniciar:

1. **Menu de Boot Limine:**
   - Você verá o menu do **Limine** com o tema escuro **Project Nox** e o emblema roxo/dourado no canto superior direito.
   - A entrada padrão **`Arch Linux → Project Nox`** (`linux-cachyos`) inicia automaticamente após **5 segundos** (ou imediatamente se você pressionar `Enter`).
2. **Tela de Login (Noctalia Greeter):**
   - O **Noctalia Greeter** será exibido com o relógio centralizado, seu nome de usuário já selecionado e a sessão **`Umbriel`** ativa.
   - Digite sua senha e pressione `Enter`.
3. **Primeiro Login no Desktop (Umbriel + Noctalia Shell):**
   - O compositor **Umbriel** (em layout `dwindle`) e a barra superior do **Noctalia Shell** carregam automaticamente.
   - O wallpaper animado entra em execução via `mpvpaper`.
   - Se os dois monitores de referência (Samsung Odyssey G5 em `DP-1` e AOC vertical em `HDMI-A-1`) estiverem conectados, o `nox-display-profile` aplica automaticamente as resoluções (`2560x1440@165Hz` e `1920x1080@100Hz` rotacionado a 90°) e sincroniza a animação entre ambos.
4. **Atalhos principais para começar a usar:**
   - `Super` ou `Super + R`: abre o **Launcher minimalista** do Noctalia (`Firefox`, `kitty`, `Luciole`, `ProtonPlus`, ou digite `/tools` para ferramentas técnicas).
   - `Super + Q`: abre o terminal **Kitty** (exibindo o painel `nox-fastfetch`).
   - `Super + E` ou `Ctrl + E`: abre o gerenciador de arquivos **Luciole**.
   - `Super + C`: fecha a janela focada.
   - `Super + L`: bloqueia a sessão com a **Noctalia Lock Screen**.
   - Consulte todos os atalhos em [`docs/KEYBINDS_MIGRATION.md`](KEYBINDS_MIGRATION.md).
5. **Verificação rápida pós-instalação:**
   Abra o terminal Kitty (`Super + Q`) e confirme o status da instalação, a integridade criptográfica do boot e a ausência de unidades com falha:
   ```bash
   cat /var/lib/nox-archinstall/status.json
   sudo nox-secureboot-verify
   systemctl --failed
   systemctl --user --failed
   ```
   Para verificações adicionais de hardware físico (GPU, áudio Fuxi H3, Wi-Fi AX210, Topgrade) e ativação futura do Secure Boot, consulte [`docs/POST_INSTALL_CHECKS.md`](POST_INSTALL_CHECKS.md) e [`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md).
