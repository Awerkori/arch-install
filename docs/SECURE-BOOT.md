# Guia Geral e Didático de Secure Boot — Project Nox (`v1.0.0`)

Este documento explica, passo a passo e sem exigir conhecimento prévio de criptografia ou firmware, como o **UEFI Secure Boot** funciona no **Project Nox**, como ele se integra ao bootloader **Limine**, ao **`sbctl`** e ao **Snapper**, e como ativá-lo utilizando o **Método A (Procedimento Geral Simples)**.

> **Importante — Qual guia você deve seguir?**
> - **Se você utiliza a placa-mãe de referência do projeto (`MSI PRO B650M-P` / `MS-7E27` com `Ryzen 5 7500F` e `Radeon RX 9060 XT`):** leia a Seção 1 e a Seção 2 deste documento para entender os conceitos básicos e, em seguida, siga o procedimento especializado em **[`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md)**.
> - **Se você utiliza outra placa-mãe UEFI padrão sem o quirk `FQ0001` da MSI:** siga este guia até o final (**Método A**).

---

## Sumário

1. [Introdução: O que o Secure Boot faz (e o que ele NÃO faz)](#1-introdução-o-que-o-secure-boot-faz-e-o-que-ele-não-faz)
2. [Todos os conceitos explicados para iniciantes](#2-todos-os-conceitos-explicados-para-iniciantes)
3. [Tabela de decisão: Como interpretar o estado do seu computador](#3-tabela-de-decisão-como-interpretar-o-estado-do-seu-computador)
4. [Como o Project Nox integra Limine, BLAKE2B, `sbctl` e Snapper](#4-como-o-project-nox-integra-limine-blake2b-sbctl-e-snapper)
5. [Método A — Procedimento Geral Simples de Ativação](#5-método-a--procedimento-geral-simples-de-ativação)
6. [Comportamento nas atualizações do dia a dia](#6-comportamento-nas-atualizações-do-dia-a-dia)
7. [Recuperação básica](#7-recuperação-básica)

---

## 1. Introdução: O que o Secure Boot faz (e o que ele NÃO faz)

Quando você aperta o botão de ligar do computador, a placa-mãe precisa decidir se o programa inicial gravado no SSD (o bootloader, como o Limine ou o Windows Boot Manager) é legítimo ou se foi adulterado.

- **O que o Secure Boot faz:** ele funciona como um **porteiro criptográfico na inicialização**. Antes de entregar o controle do computador para qualquer arquivo `.efi` na partição de boot (`/boot`) ou para o firmware de uma placa conectada (como a placa de vídeo), a placa-mãe confere se aquele arquivo possui um selo digital válido emitido por uma chave que você cadastrou como confiável.
- **O que o Secure Boot NÃO faz:**
  - **Ele não criptografa o seu SSD nem os seus arquivos pessoais.** Se alguém remover fisicamente um SSD sem criptografia de disco (LUKS) e conectá-lo como disco secundário em outro computador, os arquivos de `/home` continuarão legíveis.
  - **Ele não substitui a senha do usuário nem o `sudo`.** Sua função específica é proteger a cadeia de inicialização (`firmware UEFI → bootloader Limine → configuração limine.conf → kernel linux-cachyos`).

---

## 2. Todos os conceitos explicados para iniciantes

Antes de executar qualquer comando, entenda o vocabulário que aparecerá na BIOS e no terminal:

### 2.1. UEFI (Unified Extensible Firmware Interface)
É o software moderno gravado no chip da placa-mãe (popularmente chamado de "BIOS") que inicializa o processador, a memória RAM, a placa de vídeo e procura o sistema operacional na partição **ESP** (*EFI System Partition*, montada em `/boot` no Project Nox).

### 2.2. Assinatura Digital, Chave Privada, Chave Pública e Certificado
Imagine um **carimbo de lacre** com segredo único:
- **Chave Privada (`.key`):** é o **carimbo físico** que aplica o selo nos arquivos. Ela fica guardada somente dentro do seu Linux em `/var/lib/sbctl/keys/` (com permissão restrita ao `root`) e **nunca sai do seu computador**.
- **Chave Pública / Certificado (`.pem` / `.cer`):** é a **ficha de conferência** que permite a qualquer pessoa verificar se um selo foi feito pelo seu carimbo, mas não permite fabricar novos selos. É essa ficha pública que cadastramos na memória da placa-mãe.

> **Diferença fundamental para não se confundir:**
> 1. **Assinar um arquivo (`sbctl sign`)** = carimbar os arquivos `/boot/EFI/limine/limine_x64.efi`, `/boot/EFI/BOOT/BOOTX64.EFI` e o kernel `vmlinuz` no seu SSD usando a chave privada do seu PC.
> 2. **Inscrever chaves (`sbctl enroll-keys` / *enrollment*)** = entregar a ficha de conferência (certificados públicos) para a placa-mãe guardar na memória dela (NVRAM), dizendo: *"confie nos arquivos carimbados por mim"*.

### 2.3. A Hierarquia das 4 Variáveis do Secure Boot (`PK`, `KEK`, `db`, `dbx`)
A placa-mãe organiza a confiança em quatro gavetas na sua memória interna (NVRAM):

| Sigla | Nome Completo | Papel Explicado de Forma Simples |
|---|---|---|
| **`PK`** | **Platform Key** (Chave da Plataforma) | É a **"chave do dono do prédio"**. Só existe uma `PK`. Quem controla a `PK` pode trocar as chaves `KEK`. Quando a `PK` está preenchida, a placa-mãe está em **User Mode**; quando a `PK` está vazia, a placa-mãe entra em **Setup Mode**. |
| **`KEK`** | **Key Exchange Key** (Chave de Troca) | É a **"chave da administração"**, autorizada pela `PK` a atualizar as listas de programas permitidos (`db`) e proibidos (`dbx`). |
| **`db`** | **Signature Database** (Base de Assinaturas Permitidas) | É a **"lista VIP de entrada"**. Todo certificado ou hash listado na `db` tem permissão para rodar durante o boot (por exemplo, a chave local do seu Project Nox e, opcionalmente, o certificado de hardware da Microsoft). |
| **`dbx`** | **Forbidden Signature Database** (Base de Revogação) | É a **"lista negra"**. Contém hashes ou certificados de bootloaders antigos que tiveram falhas de segurança descobertas e foram proibidos de iniciar, mesmo que possuam assinatura na `db`. |

### 2.4. Chaves Microsoft vs Chaves de Fábrica do Fabricante (OEM)
Quando você compra uma placa-mãe nova, ela já vem de fábrica com duas categorias de chaves gravadas:
- **Chaves de fábrica do fabricante (OEM — ex.: MSI):** a `PK` de fábrica costuma pertencer ao fabricante da placa-mãe, junto com certificados internos de recuperação/diagnóstico da própria marca.
- **Chaves Microsoft (`Microsoft Windows Production PCA` e `Microsoft Corporation UEFI CA`):**
  1. A chave *Windows Production* serve para iniciar o Windows.
  2. A chave **`Microsoft Corporation UEFI CA`** (frequentemente chamada de *Third-Party UEFI CA*) é usada por quase toda a indústria de hardware para assinar **firmwares internos de placas de vídeo (AMD/NVIDIA)**, placas de rede e controladoras NVMe.

### 2.5. Option ROM (`OpROM`) e GOP (`Graphics Output Protocol`) da Placa de Vídeo
Este é um dos conceitos mais importantes para quem usa computador desktop:
- Antes mesmo de o Linux ou o menu do Limine aparecerem na tela, a sua placa de vídeo dedicada (por exemplo, uma **AMD Radeon RX 9060 XT**) precisa carregar um pequeno driver gravado dentro do próprio chip da placa de vídeo para ligar o monitor e desenhar a tela da BIOS.
- Esse mini-programa interno da placa de vídeo chama-se **Option ROM** (ou driver **GOP** — *Graphics Output Protocol*).
- Quem assina digitalmente a Option ROM das placas de vídeo comerciais? A **Microsoft Corporation UEFI CA**.
- **Consequência prática:** se você ativar o Secure Boot e cadastrar na `db` **apenas** a sua chave pessoal do Linux — removendo o certificado `Microsoft Corporation UEFI CA` — a placa-mãe pode recusar o carregamento do driver GOP da sua placa de vídeo durante o POST. O computador liga, mas o monitor fica **sem sinal de vídeo (tela preta)** até na BIOS!
- **Como o Project Nox evita isso:** o helper `nox-secureboot-enroll` utiliza por padrão a flag **`--microsoft`** do `sbctl`, que cadastra a sua chave pessoal do Nox **junto** com os certificados Microsoft na `db`, mantendo a placa de vídeo 100% confiável para o firmware.

### 2.6. `Setup Mode` vs `User Mode` e `Standard` vs `Custom`
- **`User Mode` (`Setup Mode: Disabled`):** estado normal quando já existe uma `PK` cadastrada na placa-mãe. Nesse estado, programas comuns não conseguem substituir a `PK` livremente.
- **`Setup Mode` (`Setup Mode: Enabled`):** estado temporário de configuração que ocorre quando a `PK` atual é limpa/apagada na BIOS. Em `Setup Mode`, o Secure Boot fica temporariamente inativo e a placa-mãe aceita que o comando `sudo nox-secureboot-enroll` (ou `sbctl enroll-keys`) grave a nova `PK`, `KEK` e `db` a partir do Linux. Assim que a nova `PK` é gravada, a placa-mãe volta automaticamente para `User Mode`.
- **`Secure Boot Mode: Standard` vs `Custom` (na BIOS):**
  - `Standard`: usa apenas as chaves padrão de fábrica sem mostrar o menu avançado de chaves.
  - `Custom`: habilita na BIOS o menu de gerenciamento de chaves (*Key Management*) e de políticas de execução, permitindo entrar em `Setup Mode`.

### 2.7. `sbctl`, Assinatura EFI e o Hash BLAKE2B do Limine
No Project Nox, a proteção de boot possui **duas camadas complementares**:
1. **Camada 1 — `sbctl` (Assinatura PE/EFI):**
   O utilitário `sbctl` cria as chaves locais em `/var/lib/sbctl/keys/` e assina digitalmente três binários na partição `/boot`:
   - `/boot/EFI/limine/limine_x64.efi` (bootloader principal)
   - `/boot/EFI/BOOT/BOOTX64.EFI` (bootloader de fallback UEFI)
   - `/boot/<machine-id>/linux-cachyos/vmlinuz` (imagem do kernel Linux CachyOS)
2. **Camada 2 — Hash BLAKE2B do `/boot/limine.conf` inscrito no Limine:**
   Se apenas o arquivo `limine_x64.efi` fosse assinado, alguém poderia editar o arquivo texto `/boot/limine.conf` em `/boot` para passar parâmetros maliciosos ao kernel (como `init=/bin/sh`).
   Para impedir isso, o Project Nox ativa `ENABLE_VERIFICATION=yes` e `ENABLE_ENROLL_LIMINE_CONFIG=yes` em `/etc/default/limine`. Sempre que `/boot/limine.conf` é gerado ou atualizado, o comando `limine-enroll-config` calcula o hash criptográfico **BLAKE2B de 512 bits (128 caracteres hexadecimais)** do `limine.conf`, grava esse hash **dentro** do próprio binário `limine_x64.efi` (e `BOOTX64.EFI`) sob a marca `++CONFIG_B2SUM_SIGNATURE++` e, logo em seguida, assina o `.efi` com o `sbctl`.
   Assim, se uma única letra de `/boot/limine.conf` for alterada sem re-assinar o `.efi` com a chave privada do `/var/lib/sbctl/keys/`, o Limine recusa o arquivo de configuração!

### 2.8. Diferença entre "Secure Boot Ativo" e "Secure Boot Realmente Aplicado"
Ver `Secure Boot: Enabled` na BIOS ou no terminal **não garante sozinho** que a placa-mãe está bloqueando arquivos não assinados. Alguns firmwares (especialmente placas-mãe MSI com o alerta **`FQ0001`**) vêm configurados de fábrica com uma política permissiva (*Always Execute*) que tenta verificar a assinatura, mas permite que o arquivo rode mesmo se a verificação falhar. Só dizemos que o Secure Boot está **corretamente aplicado** quando:
1. Os arquivos de boot estão assinados e com hash BLAKE2B sincronizado;
2. As chaves estão inscritas na NVRAM e o Secure Boot está `Enabled`;
3. A política de execução do firmware está configurada para **bloquear** (`Deny Execute` / `Maximum Security`) violações de assinatura.

---

## 3. Tabela de decisão: Como interpretar o estado do seu computador

Ao abrir o terminal Kitty e rodar `sudo sbctl status` e `sudo nox-secureboot-verify`, use esta tabela para saber exatamente o que fazer:

| Situação Observada | O que significa na prática | Caminho Recomendado |
|---|---|---|
| `Installed: ✗ sbctl is not installed` (no host antigo antes de instalar o Nox) | O pacote `sbctl` está instalado, mas ainda não gerou nem inscreveu chaves próprias naquela instalação | No sistema instalado pelo Project Nox, as chaves locais já vêm criadas (`Installed: ✓`); falta apenas inscrevê-las na BIOS quando desejar |
| `Secure Boot: ✗ Disabled` e `Setup Mode: ✗ Disabled` | O sistema inicia normalmente sem exigir assinatura; a placa-mãe ainda guarda as chaves de fábrica (`PK` preenchida) | **Estado padrão logo após instalar o Nox.** Verifique as assinaturas (`sudo nox-secureboot-verify`), coloque a BIOS em `Setup Mode` e inscreva as chaves |
| `Secure Boot: ✗ Disabled` e `Setup Mode: ✓ Enabled` | A `PK` da placa-mãe foi limpa na BIOS; o firmware está pronto para receber as chaves do Nox | Execute `sudo nox-secureboot-enroll --yes-enroll-uefi-keys` no terminal e depois ative o Secure Boot na BIOS |
| `Vendor Keys: microsoft builtin-db ...` | Existem certificados Microsoft e/ou de fábrica na memória da placa-mãe | **Não é um erro.** Certificados Microsoft são usados para validar Option ROMs de placas de vídeo dedicadas |
| `FQ0001: Defaults to executing on Secure Boot policy violation (CRITICAL)` | Firmware MSI possui política padrão permissiva que pode deixar passar arquivos EFI sem assinatura válida | Siga obrigatoriamente a seção de `FQ0001` no guia especializado **[`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md)** (`Maximum Security` / `Image Execution Policy`) |
| `✗ /boot/... is not signed` em `sbctl verify` | Algum arquivo EFI na partição `/boot` perdeu a assinatura ou não foi assinado | **Não ative o Secure Boot na BIOS ainda.** Execute `sudo /usr/local/libexec/nox/nox-limine-integrity --force` e confirme `✓ is signed` nos 3 arquivos |
| `PANIC: CHECKSUM MISMATCH FOR CONFIG FILE` na tela do Limine | O arquivo `/boot/limine.conf` foi modificado sem atualizar o hash BLAKE2B embutido no `limine_x64.efi` | Inicie pela ISO oficial do Arch Linux, entre no `arch-chroot` e execute `/usr/local/libexec/nox/nox-limine-integrity --force` (veja [`docs/RECOVERY.md`](RECOVERY.md)) |

---

## 4. Como o Project Nox integra Limine, BLAKE2B, `sbctl` e Snapper

Para evitar que o usuário precise decorar comandos complexos ou corra o risco de quebrar o boot ao atualizar o kernel ou criar snapshots, o Project Nox automatiza a ordem criptográfica correta em quatro camadas:

### 4.1. A Ordem Obrigatória das Operações
Sempre que o kernel `linux-cachyos`, o Limine ou a lista de snapshots Btrfs mudam, a ordem executada pelos scripts do Nox é rigorosamente esta:

```text
1. Gerar/atualizar entradas em /boot/limine.conf (limine-update / limine-snapper-sync)
        ↓
2. Normalizar títulos e tema Obsidian Purple em /boot/limine.conf (nox-limine-normalize --post)
        ↓
3. Calcular o hash BLAKE2B final de /boot/limine.conf e gravá-lo dentro de limine_x64.efi + assinar limine_x64.efi com sbctl (limine-enroll-config)
        ↓
4. Gravar o mesmo hash BLAKE2B no fallback BOOTX64.EFI e assinar BOOTX64.EFI + vmlinuz com sbctl (95-nox-sbctl-fallback)
```

> **Regra de ouro:** o hash BLAKE2B (`limine-enroll-config`) e a assinatura EFI (`sbctl sign`) são **sempre as últimas etapas**, depois que `/boot/limine.conf` já está em seu estado final. Editar `/boot/limine.conf` manualmente depois da etapa 3 invalidaria o hash BLAKE2B embutido no `.efi`.

### 4.2. O Guardião Automático (`nox-limine-integrity`)
O script `/usr/local/libexec/nox/nox-limine-integrity` verifica automaticamente se:
- Existe alguma transação de boot interrompida (`/run/nox-limine-tx.dirty`);
- O título `Project Nox` em `/boot/limine.conf` precisa de normalização;
- O hash BLAKE2B real de `/boot/limine.conf` (`b2sum /boot/limine.conf`) diverge do hash gravado dentro de `/boot/EFI/limine/limine_x64.efi` ou `/boot/EFI/BOOT/BOOTX64.EFI` (seja por hash zerado `0{128}` ou por hash antigo de uma transação interrompida);
- Algum dos binários (`limine_x64.efi` ou `BOOTX64.EFI`) está sem assinatura `sbctl` válida.

Se tudo já estiver sincronizado, o `nox-limine-integrity` termina imediatamente sem tocar no disco (no-op). Se detectar qualquer divergência, ele executa automaticamente as etapas 2, 3 e 4 acima para reparar a cadeia de boot antes que o computador desligue ou reinicie (`nox-limine-integrity-boot.service` e `nox-limine-integrity-shutdown.service`).

---

## 5. Método A — Procedimento Geral Simples de Ativação

Utilize este método se a sua placa-mãe possui um firmware UEFI padrão sem o alerta `FQ0001`. (Para a **MSI PRO B650M-P**, utilize **[`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md)**).

---

### Passo 1 — Conferir o estado inicial e as assinaturas no Linux

- **Objetivo:** confirmar que o Project Nox gerou as chaves locais, que o hash BLAKE2B do Limine está inscrito e que todos os binários EFI em `/boot` estão assinados antes de alterar qualquer opção na BIOS.
- **Por que isso é necessário:** ativar o Secure Boot antes de ter certeza de que `/boot/EFI/limine/limine_x64.efi`, `/boot/EFI/BOOT/BOOTX64.EFI` e o kernel `vmlinuz` estão assinados faria a placa-mãe bloquear a inicialização.
- **Antes de executar:** o sistema Project Nox deve estar instalado e iniciado normalmente no desktop, e você deve ter em mãos o pendrive com a ISO oficial do Arch Linux caso precise de recuperação.
- **Comandos:**
  ```bash
  sudo sbctl status
  sudo nox-secureboot-verify
  ```
- **Resultado esperado:**
  - `sbctl status` mostra `Installed: ✓ sbctl is installed` e `Secure Boot: ✗ Disabled`.
  - `nox-secureboot-verify` mostra:
    ```text
    ✓ /boot/<machine-id>/linux-cachyos/vmlinuz is signed
    ✓ /boot/EFI/BOOT/BOOTX64.EFI is signed
    ✓ /boot/EFI/limine/limine_x64.efi is signed
    [NOX SECUREBOOT] OK: /var/lib/sbctl/keys presente, Limine + kernel assinados e hash de limine.conf inscrito.
    ```
- **Se der errado:** se algum arquivo aparecer como `✗ is not signed`, execute `sudo /usr/local/libexec/nox/nox-limine-integrity --force` e rode `sudo nox-secureboot-verify` novamente até todos os itens exibirem `✓`.

---

### Passo 2 — Colocar a placa-mãe em `Setup Mode` na BIOS/UEFI

- **Objetivo:** limpar a Platform Key (`PK`) de fábrica para permitir que a placa-mãe aceite a inscrição das chaves geradas pelo seu Project Nox.
- **Por que isso é necessário:** enquanto a placa-mãe estiver em `User Mode` (`Setup Mode: Disabled`), a NVRAM rejeita a gravação de uma nova `PK` a partir do sistema operacional.
- **Antes de executar:** confirme que o Passo 1 terminou com `[NOX SECUREBOOT] OK`.
- **Ação:**
  1. Reinicie diretamente para a tela de configuração da BIOS/UEFI:
     ```bash
     systemctl reboot --firmware-setup
     ```
  2. Na BIOS, acesse a aba **Security** (ou **Boot**) → **Secure Boot**.
  3. Mude **Secure Boot Mode** de `Standard` para **`Custom`**.
  4. Entre em **Key Management** (Gerenciamento de Chaves) e escolha a opção de entrar em **Setup Mode** (em muitas placas chamada de *Clear Secure Boot Keys*, *Reset to Setup Mode* ou *Delete PK / Delete all Secure Boot variables*).
  5. Mantenha **Secure Boot** como **`Disabled`** por enquanto, salve as alterações (`F10`) e deixe o computador iniciar normalmente no Project Nox.
- **Resultado esperado:** o computador inicia normalmente no Limine e no desktop do Project Nox. Ao abrir o terminal e rodar `sudo sbctl status`, a linha `Setup Mode` agora exibe:
  ```text
  Setup Mode: ✓ Enabled
  ```
- **Se der errado:** se `Setup Mode` continuar como `✗ Disabled`, a BIOS não limpou a chave `PK` (ou re-provisionou as chaves de fábrica automaticamente). Verifique se a opção de auto-provisionamento de chaves de fábrica (*Factory Default Key Provisioning*) está desativada no menu `Key Management`.

---

### Passo 3 — Inscrever as chaves na UEFI usando `nox-secureboot-enroll`

- **Objetivo:** gravar as chaves públicas locais do seu Project Nox (junto com os certificados Microsoft UEFI CA para proteger a Option ROM da placa de vídeo) nas variáveis `PK`, `KEK` e `db` da placa-mãe, e re-verificar toda a cadeia do Limine.
- **Por que isso é necessário:** é este comando que transfere a confiança das chaves criadas em `/var/lib/sbctl/keys/` para a memória NVRAM da placa-mãe.
- **Antes de executar:** `sudo sbctl status` **deve** mostrar `Setup Mode: ✓ Enabled`.
- **Comando:**
  ```bash
  sudo nox-secureboot-enroll --yes-enroll-uefi-keys
  ```
- **O que o helper `nox-secureboot-enroll` faz internamente:**
  1. Confirma que `/var/lib/sbctl/keys/` existe e que a placa-mãe está em `Setup Mode`.
  2. Executa `sbctl enroll-keys --microsoft` (incluindo os certificados Microsoft na `db` para garantir que a Option ROM/GOP da placa de vídeo dedicada continue funcionando).
  3. Executa `limine-enroll-config` e o hook `/etc/boot/hooks/post.d/95-nox-sbctl-fallback` para garantir que `/boot/limine.conf`, `limine_x64.efi`, `BOOTX64.EFI` e o kernel `vmlinuz` estejam 100% sincronizados e assinados com as chaves recém-inscritas.
  4. Executa `sbctl verify` para confirmar todas as assinaturas.
- **Resultado esperado:**
  ```text
  Enrolling keys to EFI variables...
  With vendor keys from microsoft...✓
  Enrolled keys to the EFI variables!
  Config file BLAKE2B successfully enrolled.
  ✓ Signed /boot/EFI/limine/limine_x64.efi
  ...
  [NOX SECUREBOOT] Chaves inscritas e cadeia Limine re-assinada com sucesso.
  ```
- **Se der errado:** se ocorrer erro de variável EFI imutável ou falha de escrita na NVRAM, **não ative o Secure Boot na BIOS**. Consulte a seção de troubleshooting do guia [`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md) ou [`docs/RECOVERY.md`](RECOVERY.md).

---

### Passo 4 — Ativar o Secure Boot na BIOS e validar no sistema

- **Objetivo:** ligar a verificação obrigatória de assinaturas na placa-mãe e comprovar no Linux que o Secure Boot está ativo.
- **Por que isso é necessário:** após inscrever as chaves no Passo 3, a placa-mãe saiu de `Setup Mode` para `User Mode`, mas em muitos firmwares a chave geral `Secure Boot` ainda precisa ser mudada de `Disabled` para `Enabled` na BIOS.
- **Antes de executar:** confirme que o Passo 3 exibiu `[NOX SECUREBOOT] Chaves inscritas e cadeia Limine re-assinada com sucesso.` e que `sudo nox-secureboot-verify` não mostra nenhum erro.
- **Ação e Comandos:**
  1. Reinicie para a BIOS:
     ```bash
     systemctl reboot --firmware-setup
     ```
  2. Em **Security → Secure Boot**, mude **Secure Boot** para **`Enabled`**.
  3. Salve e reinicie (`F10`).
  4. Assim que entrar no desktop do Project Nox, abra o terminal Kitty e execute:
     ```bash
     sudo nox-secureboot-verify --require-active
     ```
- **Resultado esperado:**
  - `sbctl status` exibe `Installed: ✓`, `Setup Mode: ✗ Disabled` (correto, pois agora está em `User Mode` protegido pela sua `PK`) e **`Secure Boot: ✓ Enabled`**.
  - `sudo nox-secureboot-verify --require-active` termina com código `0` e exibe `[NOX SECUREBOOT] OK`.
- **Se der errado:** se a placa-mãe exibir `Secure Boot Violation` ao tentar iniciar, entre na BIOS (`Del`), mude **Secure Boot** de volta para **`Disabled`**, inicie o Project Nox normalmente e execute `sudo /usr/local/libexec/nox/nox-limine-integrity --force` antes de tentar novamente.

---

## 6. Comportamento nas atualizações do dia a dia

Depois que o Secure Boot estiver ativo, **você não precisa assinar arquivos manualmente a cada atualização**:

1. **Atualização do kernel (`linux-cachyos`) ou pacotes (`topgrade` / `pacman -Syu`):**
   - Os hooks do `mkinitcpio`, `limine-mkinitcpio-hook`, `sbctl` e `95-nox-sbctl-fallback` atualizam `/boot/limine.conf`, recalculam o hash BLAKE2B e re-assinam automaticamente `vmlinuz`, `limine_x64.efi` e `BOOTX64.EFI`.
2. **Criação automática de snapshots (`snap-pac` / `nox-topgrade`):**
   - O `limine-snapper-sync` adiciona o novo snapshot ao menu do Limine e os hooks de pós-execução normalizam o menu, inscrevem o novo hash BLAKE2B e re-assinam os binários EFI automaticamente.
3. **Restauração de um snapshot anterior (`nox-limine-snapper-restore`):**
   - Ao abrir `Limine Snapshot Restore` (via `/tools` no launcher ou `sudo /usr/local/bin/limine-snapper-restore` no Kitty), o wrapper exibe a lista de snapshots e só altera `/boot` após a sua confirmação, re-assinando toda a cadeia ao concluir.
   - **Nota sobre queda de energia durante restauração:** evite desligar o computador à força durante os poucos segundos em que o `limine-snapper-restore` estiver copiando o kernel do snapshot para `/boot`. Caso ocorra falta de luz exatamente nesse instante (~1,5s medidos em laboratório), basta seguir o reparo rápido via `arch-chroot` em [`docs/RECOVERY.md`](RECOVERY.md).

---

## 7. Recuperação básica

Se em qualquer momento o computador não iniciar após uma alteração de Secure Boot:

1. **Não formate o SSD e não apague suas chaves privadas em `/var/lib/sbctl/keys/`.**
2. Entre na BIOS (`Del`), mude **Secure Boot** para **`Disabled`**, salve (`F10`) e veja se o sistema inicia normalmente.
   - Se o sistema iniciar normalmente com Secure Boot desativado, o problema é apenas um arquivo `.efi` ou hash BLAKE2B desatualizado em `/boot`. Basta abrir o terminal no próprio sistema e rodar:
     ```bash
     sudo /usr/local/libexec/nox/nox-limine-integrity --force
     sudo nox-secureboot-verify
     ```
3. Para todos os demais cenários (incluindo reparo pelo pendrive da ISO oficial do Arch Linux, erro `PANIC: CHECKSUM MISMATCH FOR CONFIG FILE` ou tela preta de Option ROM), consulte o manual completo em **[`docs/RECOVERY.md`](RECOVERY.md)**.
