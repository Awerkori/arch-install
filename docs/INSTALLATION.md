# Guia de Instalação Passo a Passo — Project Nox (`v1.0.0`)

Este guia explica, do começo ao fim e sem exigir experiência avançada com o `archinstall`, como instalar o **Project Nox** a partir da mídia oficial do Arch Linux.

O fluxo completo resume-se a:

> **ISO oficial do Arch Linux → Conexão com a Internet → Comando do Project Nox → Escolha do SSD → Nome de Usuário → Senha → Instalação Automática → Reinicialização.**

---

## 1. Antes da instalação (Pré-requisitos e Preparação)

### 1.1. Faça backup dos seus arquivos pessoais
A instalação do Project Nox **formatará integralmente o SSD escolhido**, recriando a tabela de partições GPT (`/boot` de 4 GiB em FAT32 + partição raiz em Btrfs). Copie qualquer documento, chave, foto ou projeto importante para um disco externo ou nuvem antes de iniciar.

### 1.2. Requisitos mínimos do computador
- **Processador (CPU):** compatível com **`x86-64-v4`** (AMD Ryzen séries 7000/9000 — Zen 4 / Zen 5). O instalador verifica esse requisito automaticamente na etapa `00-preflight` porque utiliza os repositórios otimizados `cachyos-znver4`.
- **Modo de inicialização da placa-mãe:** **UEFI 64 bits** (modo CSM / Legacy BIOS desativado).
- **Espaço livre no SSD de destino:** mínimo técnico de **20 GiB** (recomendado **64 GiB ou mais**; em máquinas físicas com `>= 24 GiB` de RAM e disco amplo, o instalador dimensiona o swapfile Btrfs adequadamente).
- **Conexão ativa com a internet:** necessária durante toda a instalação para baixar os pacotes oficiais do Arch Linux, do CachyOS e o payload verificado da release `v1.0.0`.

### 1.3. ISO oficial homologada e versão do `archinstall`
- O Project Nox **não** possui ISO própria: você deve usar a **ISO oficial do Arch Linux**.
- Esta release (`v1.0.0`) foi homologada na ISO oficial **`archlinux-2026.11.01-x86_64.iso`**, que traz o **`archinstall 4.5`**.
- Por segurança, o assistente `nox-install.py` verifica automaticamente se está rodando dentro da ISO oficial (`/run/archiso`) e se a versão do `archinstall` pertence à série homologada **`4.5`** (`4.5` ou `4.5.*`).

### 1.4. Por que o Secure Boot deve estar desativado para iniciar a ISO oficial
Em configurações padrão de fábrica, a ISO oficial do Arch Linux pode ser bloqueada caso o **Secure Boot** esteja ativo na placa-mãe (ou caso a política de execução de mídia removível esteja restrita).

- **Recomendação obrigatória para a instalação:** antes de dar boot pelo pendrive da ISO do Arch Linux, entre na BIOS/UEFI (tecla `Del` na MSI PRO B650M-P) e confirme que **Secure Boot** está como **`Disabled`**.
- **Não apague nem altere as chaves do firmware antes de instalar o sistema.** Toda a preparação criptográfica do Secure Boot será feita automaticamente durante a instalação e a ativação no firmware será realizada depois, com o sistema já instalado e funcionando, seguindo [`docs/SECURE-BOOT.md`](SECURE-BOOT.md) ou [`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md).

### 1.5. Como confirmar que a ISO iniciou em modo UEFI
Assim que o pendrive carregar e você cair no prompt `root@archiso ~ #`, pode confirmar que o sistema iniciou em modo UEFI executando:

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
  - Verifique se o relógio do sistema na BIOS está com data coerente: `timedatectl status` (certificados HTTPS falham se o ano da BIOS estiver muito atrasado; ative a sincronização com `timedatectl set-ntp true`).
  - Confira se a interface recebeu endereço IP: `ip addr show`.

---

## 3. Comando Definitivo de Instalação (`Download-Then-Execute`)

O instalador utiliza o método **baixar e executar** (`download-then-execute`), salvando `nox-install.py` em `/tmp/nox-install.py` (em memória RAM da ISO) antes de iniciá-lo. Isso garante que o script só seja executado se o download HTTPS terminar com sucesso e preserva o terminal interativo (`stdin`/`/dev/tty`) para as perguntas do assistente.

### Opção 1 — Comando único (recomendado para copiar ou digitar)

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/Awerkori/arch-install/main/bootstrap/nox-install.py -o /tmp/nox-install.py && python3 /tmp/nox-install.py
```

### Opção 2 — Em duas etapas (útil caso queira conferir o arquivo antes de iniciar)

```bash
curl --proto '=https' --tlsv1.2 -fsSL https://raw.githubusercontent.com/Awerkori/arch-install/main/bootstrap/nox-install.py -o /tmp/nox-install.py
python3 /tmp/nox-install.py
```

### O que esse comando faz automaticamente antes de tocar no disco
1. Verifica que você está em um terminal interativo dentro da ISO oficial do Arch Linux (`/run/archiso`) com **`archinstall 4.5`**.
2. Baixa via HTTPS a configuração base pública (`user_configuration.json`) do repositório oficial.
3. Valida a URL e o hash **SHA-256** do pacote da release (`nox-archinstall-payload-v1.0.0.tar.gz`) e testa a conectividade HTTPS com o GitHub Releases e com `https://archlinux.org`.
4. Lista os discos disponíveis no computador para que você escolha o SSD com segurança.

---

## 4. Escolha do SSD e Aviso Destrutivo

> **AVISO CRÍTICO:** O disco selecionado na etapa `[1/4]` terá **todas as suas partições e dados apagados permanentemente**. Nunca tente adivinhar qual disco escolher.

### 4.1. Como identificar o SSD correto na lista
O assistente exibe cada disco elegível com quatro informações claras:
1. **Tipo e barramento:** `[INTERNO]` vs `[USB/REMOVIVEL]` e o protocolo (`[nvme]`, `[sata]`, `[usb]`). O pendrive da própria ISO do Arch Linux já é filtrado automaticamente para não aparecer como destino.
2. **Caminho do dispositivo:** por exemplo, `/dev/nvme0n1` ou `/dev/sda`.
3. **Capacidade total em GiB:** por exemplo, `(931.5 GiB)` para um SSD de 1 TB ou `(465.8 GiB)` para um SSD de 500 GB.
4. **Modelo físico gravado no hardware:** por exemplo, `Kingston KC3000`, `WD Black SN770`, `Samsung SSD 980`, etc.

Se você tiver mais de um SSD instalado no PC e quiser conferir as partições atuais antes de rodar o assistente, execute `lsblk -o NAME,SIZE,MODEL,TRAN,FSTYPE,MOUNTPOINTS`.

### 4.2. Dupla confirmação de segurança
Para evitar qualquer formatação acidental por erro de digitação:
1. **Etapa `[1/4]`:** você digita o **número** correspondente ao SSD na lista (por exemplo, `1`) — nenhum disco é pré-selecionado automaticamente se você apenas apertar `Enter`.
2. **Etapa `[2/4]`:** o assistente mostra o resumo completo do disco escolhido e exige que você **digite exatamente o nome curto do dispositivo** (por exemplo, `nvme0n1` ou `vda`). Se o texto digitado não coincidir, a instalação é cancelada imediatamente sem alterar nada.

### 4.3. Como cancelar a qualquer momento antes da formatação
- Na escolha do disco (`[1/4]`), digite `q` e pressione `Enter`.
- Ou pressione `Ctrl + C` em qualquer etapa antes da confirmação final (`Confirmar e iniciar a instalacao agora? [s/N]:`). Nenhuma alteração em disco é feita até você responder `s` nessa última pergunta.

---

## 5. Usuário, Senha e Privilégios (`sudo`)

Nas etapas `[3/4]` e `[4/4]`:

1. **Nome de usuário (`[3/4]`):**
   - Digite o nome do seu usuário principal em letras minúsculas (por exemplo, `awerkori`).
   - O nome deve começar com letra minúscula e conter apenas letras minúsculas, números, `_` ou `-` (máximo de 32 caracteres). O nome `root` não é permitido como usuário comum.
2. **Senha (`[4/4]`):**
   - Digite sua senha e pressione `Enter`; em seguida, digite a mesma senha novamente para confirmar.
   - **Normal:** por segurança, **nenhum caractere ou asterisco aparece na tela** enquanto você digita a senha.
3. **Como funcionam o `sudo` e a conta `root` no Project Nox:**
   - Seu usuário é adicionado automaticamente ao grupo `wheel`.
   - Sempre que precisar executar comandos administrativos (`sudo ...`), você utilizará **a sua própria senha de usuário**.
   - Não existe senha separada para `root`: a conta `root` permanece **bloqueada para login direto** (`passwd -S root` -> `L`), seguindo as boas práticas de segurança do projeto.

Após confirmar o resumo final com `s`, o instalador executará o particionamento Btrfs, a instalação dos pacotes base, o download e verificação SHA-256 do payload da release `v1.0.0` e todas as 13 etapas de configuração até exibir a conclusão.

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
   - `Super` (tecla Windows sozinha) ou `Super + R`: abre o **Launcher minimalista** do Noctalia (`Firefox`, `kitty`, `Luciole`, `ProtonPlus`, ou digite `/tools` para ferramentas técnicas).
   - `Super + Q` ou `Super + T`: abre o terminal **Kitty** (exibindo o painel `nox-fastfetch`).
   - `Super + E`: abre o gerenciador de arquivos **Luciole**.
   - `Super + B`: abre o navegador **Firefox**.
   - `Super + L`: bloqueia a sessão com a **Noctalia Lock Screen**.
   - Consulte todos os atalhos em [`docs/KEYBINDS_MIGRATION.md`](KEYBINDS_MIGRATION.md).

5. **Verificação rápida pós-instalação:**
   Abra o terminal Kitty (`Super + Q`) e confirme que o status da instalação registrou sucesso e que nenhuma unidade do sistema falhou:
   ```bash
   cat /var/lib/nox-archinstall/status.json
   systemctl --failed
   ```
   Para verificações adicionais de hardware físico (GPU, áudio Fuxi H3, Wi-Fi AX210, Topgrade) e ativação futura do Secure Boot, consulte [`docs/POST_INSTALL_CHECKS.md`](POST_INSTALL_CHECKS.md) e [`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md).
