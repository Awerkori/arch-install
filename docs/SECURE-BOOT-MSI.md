# Guia Especializado de Secure Boot — MSI PRO B650M-P (`MS-7E27`) + Radeon RX 9060 XT

Este documento é o manual técnico e didático preparado especificamente para o computador físico do proprietário do **Project Nox**:

- **Placa-mãe:** **MSI PRO B650M-P** (`MS-7E27`)
- **Versão de BIOS observada no host:** **`1.I2`** (`E7E27AMS.1I2`, data de build `20/03/2026`)
- **Processador:** **AMD Ryzen 5 7500F** (6 núcleos / 12 threads, Zen 4 — **sem vídeo integrado / sem iGPU**)
- **Placa de vídeo dedicada:** **ASRock AMD Radeon RX 9060 XT** (Navi 44 / RDNA 4, PCI ID `1002:7590`, Subsistema `1849:5408`, VBIOS `113-APM7842CL-102`)
- **Bootloader e Gerenciador de Chaves do Project Nox:** **Limine** (com verificação BLAKE2B de `/boot/limine.conf`) + **`sbctl`** (`nox-secureboot-enroll` / `nox-secureboot-verify` / `nox-limine-integrity`)

> **Leia antes de começar:** Se você ainda não leu a explicação dos conceitos básicos (`PK`, `KEK`, `db`, `dbx`, `Setup Mode`, `Option ROM`, `GOP` e hash `BLAKE2B` do Limine), leia primeiro as Seções 1 a 4 de **[`docs/SECURE-BOOT.md`](SECURE-BOOT.md)**. Este documento foca nas particularidades reais do firmware MSI AM5, na proteção de vídeo da RX 9060 XT e na correção do alerta crítico **`FQ0001`**.

---

## Sumário

1. [Diagnóstico linha por linha do estado inicial comprovado na MSI PRO B650M-P](#1-diagnóstico-linha-por-linha-do-estado-inicial-comprovado-na-msi-pro-b650m-p)
2. [Investigação da alternativa menos invasiva: É possível evitar o Setup Mode?](#2-investigação-da-alternativa-menos-invasiva-é-possível-evitar-o-setup-mode)
3. [Comparação profunda: `--microsoft` versus `--firmware-builtin` no `sbctl`](#3-comparação-profunda---microsoft-versus---firmware-builtin-no-sbctl)
4. [Proteção crítica de vídeo para a Radeon RX 9060 XT (Por que o Ryzen 5 7500F exige cuidado redobrado)](#4-proteção-crítica-de-vídeo-para-a-radeon-rx-9060-xt-por-que-o-ryzen-5-7500f-exige-cuidado-redobrado)
5. [Investigação e solução documentada do alerta `FQ0001` na MSI](#5-investigação-e-solução-documentada-do-alerta-fq0001-na-msi)
6. [Cenários técnicos documentados em placas MSI / AM5 (Upstream e Wikis Oficiais)](#6-cenários-técnicos-documentados-em-placas-msi--am5-upstream-e-wikis-oficiais)
7. [Preparação segura, backup e pontos de parada antes de modificar o firmware](#7-preparação-segura-backup-e-pontos-de-parada-antes-de-modificar-o-firmware)
8. [Procedimento físico passo a passo na MSI PRO B650M-P (Fases A a F)](#8-procedimento-físico-passo-a-passo-na-msi-pro-b650m-p-fases-a-a-f)

---

## 1. Diagnóstico linha por linha do estado inicial comprovado na MSI PRO B650M-P

Na inspeção somente-leitura realizada no computador físico antes da reinstalação, a saída de `sbctl status` registrou exatamente:

```text
Installed:   ✗ sbctl is not installed
Setup Mode:  Disabled
Secure Boot: Disabled
Vendor Keys: microsoft builtin-db builtin-KEK builtin-PK
Firmware:    ‼ Your firmware has known quirks
             - FQ0001: Defaults to executing on Secure Boot policy violation (CRITICAL)
               https://github.com/Foxboron/sbctl/wiki/FQ0001
```

Veja o que cada uma dessas cinco linhas significa tecnicamente (e por que **nenhuma delas significa que sua placa-mãe está defeituosa ou com certificados corrompidos**):

1. **`Installed: ✗ sbctl is not installed`**
   - **O que significa:** apesar da frase em inglês parecer dizer que o programa `sbctl` não está instalado, o pacote `sbctl` **já está instalado** (caso contrário o comando nem teria rodado!). Essa linha indica apenas que, no sistema onde o comando foi rodado, o `sbctl` ainda não possuía sua pasta local de chaves ativas vinculadas à NVRAM.
   - **Como fica após instalar o Project Nox:** durante a instalação limpa do Project Nox (etapa `20-cachyos-kernel.sh`), o instalador executa `sbctl create-keys` automaticamente, gerando chaves exclusivas da sua máquina em `/var/lib/sbctl/keys/`.
2. **`Setup Mode: Disabled`**
   - **O que significa:** a placa-mãe encontra-se atualmente em **`User Mode`**, ou seja, existe uma chave de plataforma (`PK`) de fábrica gravada na NVRAM. Enquanto `Setup Mode` estiver `Disabled`, o firmware bloqueia tentativas de programas no sistema operacional de substituir a `PK` diretamente.
3. **`Secure Boot: Disabled`**
   - **O que significa:** a verificação de assinaturas está desligada no boot atual. Qualquer bootloader EFI (assinado ou não, incluindo o pendrive da ISO oficial do Arch Linux) pode iniciar livremente.
4. **`Vendor Keys: microsoft builtin-db builtin-KEK builtin-PK`**
   - **O que significa:** o `sbctl` comparou as chaves atualmente gravadas na sua placa-mãe com o banco de certificados conhecidos e identificou que a NVRAM contém a hierarquia original de fábrica da MSI (`builtin-PK`, `builtin-KEK`, `builtin-db`) junto com os certificados oficiais da Microsoft (`microsoft`).
   - **Importante:** isso prova que as chaves de fábrica da sua MSI estão **íntegras**. Você **não** deve apagá-las impulsivamente sem antes ter o Project Nox instalado, testado e com pendrive de recuperação pronto.
5. **`FQ0001: Defaults to executing on Secure Boot policy violation (CRITICAL)`**
   - **O que significa:** não é uma chave corrompida nem um erro do Linux. Trata-se de um comportamento conhecido do firmware de placas-mãe MSI (catalogado pelo autor do `sbctl` como quirk `FQ0001`), em que a política padrão de execução de imagens EFI vem configurada de fábrica como **`Always Execute`** (Sempre Executar) em vez de **`Deny Execute`** (Negar Execução). Explicamos esse ponto em detalhes na [Seção 5](#5-investigação-e-solução-documentada-do-alerta-fq0001-na-msi).

---

## 2. Investigação da alternativa menos invasiva: É possível evitar o Setup Mode?

Antes de recomendar a limpeza da `PK` de fábrica da MSI para entrar em `Setup Mode`, avaliamos tecnicamente todas as alternativas possíveis para incluir a confiança do Project Nox:

| Método Avaliado | Como Funciona | O que acontece com as chaves de fábrica da MSI? | Compatível com `sbctl` e hooks automáticos do Project Nox? | Veredito para a MSI PRO B650M-P |
|---|---|---|---|---|
| **1. Operação `append` autenticada via Linux sem Setup Mode** | Tenta adicionar o certificado `db.pem` do usuário à variável `db` existente sem tocar na `PK` ou `KEK` | Mantém `PK` e `KEK` da MSI intactas | **Não.** Pelo padrão UEFI, em `User Mode` a variável `db` só aceita escrita autenticada assinada pela chave privada da **`KEK` atual**. Como a chave privada da `KEK` de fábrica pertence à MSI/Microsoft (e ninguém fora da MSI/Microsoft a possui), o Linux não pode assinar uma atualização da `db` em `User Mode`. | **Inviável via SO** |
| **2. Adição manual do arquivo `db.cer` via menu da BIOS MSI (`Key Management → Authorized Signatures (db) → Append`)** | Copiar o certificado público `/var/lib/sbctl/keys/db/db.der` para a partição `/boot` (FAT32) e usar o menu `Key Management` da BIOS MSI para fazer *Append* manual na `db` | Mantém `PK` e `KEK` de fábrica da MSI e apenas adiciona a chave `db` do Nox na BIOS | **Parcial / Limitado.** Embora algumas versões do Click BIOS 5 permitam fazer *Append* manual de um certificado `.cer`/`.der` na variável `db` pela interface da BIOS (que contorna a verificação porque você está fisicamente dentro do setup UEFI), o `sbctl` no Linux verificará que a `PK` e a `KEK` da NVRAM não pertencem ao `/var/lib/sbctl/keys/` e continuará reportando estado inconsistente ou falhando em futuras rotações de `db`/`dbx` via `sbctl`. | **Apenas paliativo manual; não recomendado como método principal** |
| **3. Enrollment padrão via `sbctl` em `Setup Mode` com `--microsoft` (`nox-secureboot-enroll`)** | Limpar a `PK` na BIOS (`Setup Mode: Enabled`) e rodar `sudo nox-secureboot-enroll --yes-enroll-uefi-keys`, que inscreve a `PK`, `KEK` e `db` do Nox + certificados Microsoft | Substitui a `PK`/`KEK`/`db` ativas na NVRAM pelas chaves do Nox + Microsoft; **porém as chaves originais de fábrica continuam salvas intactas na ROM da BIOS (`PKDefault`, `KEKDefault`, `dbDefault`)** e podem ser restauradas a qualquer momento com 1 clique em *Enroll all Factory Default keys*! | **100% Compatível.** É o fluxo oficial suportado pelo `sbctl`, pelo Arch Linux, pelo CachyOS e pelos helpers automáticos do Project Nox. | **Recomendado e Homologado** |

> **Fato técnico tranquilizador sobre as chaves de fábrica da MSI:**
> Limpar as chaves ativas na BIOS para entrar em `Setup Mode` **não apaga as chaves de fábrica da memória ROM da placa-mãe**. A especificação UEFI separa as variáveis ativas (`PK`, `KEK`, `db`, `dbx` na NVRAM) das variáveis padrão gravadas na imagem da BIOS (`PKDefault`, `KEKDefault`, `dbDefault`, `dbxDefault` na ROM). Se um dia você quiser voltar a placa-mãe exatamente ao estado original de fábrica da MSI (por exemplo, para vender a placa ou instalar apenas Windows), basta entrar em `Settings → Security → Secure Boot → Key Management` e clicar em **`Enroll all Factory Default keys`** (Restaurar chaves padrão de fábrica).

---

## 3. Comparação profunda: `--microsoft` versus `--firmware-builtin` no `sbctl`

O utilitário `sbctl enroll-keys` possui dois parâmetros frequentemente citados em tutoriais de Arch Linux e CachyOS: `--microsoft` e `--firmware-builtin`.

Abaixo está a análise técnica exata do que cada parâmetro faz nas variáveis UEFI e por que essa distinção é crítica:

| Aspecto Técnico | `sbctl enroll-keys --microsoft` *(Padrão do `nox-secureboot-enroll`)* | `sbctl enroll-keys --microsoft --firmware-builtin` | `sbctl enroll-keys` *(ou `nox-secureboot-enroll --no-microsoft`)* |
|---|---|---|---|
| **O que inscreve na `PK`** | Somente a chave pública `PK` local gerada pelo `sbctl` no seu PC (`/var/lib/sbctl/keys/PK/PK.pem`). | Somente a chave pública `PK` local gerada pelo `sbctl` (**não** mantém a `PK` original da MSI, pois só pode existir 1 `PK` no UEFI). | Somente a chave pública `PK` local gerada pelo `sbctl`. |
| **O que inscreve na `KEK`** | Chave `KEK` local do `sbctl` + certificado `Microsoft Corporation KEK CA`. | Chave `KEK` local do `sbctl` + certificado `Microsoft Corporation KEK CA` + cópia de todas as entradas presentes em `KEKDefault` do firmware. | Somente a chave `KEK` local do `sbctl`. |
| **O que inscreve na `db`** | Chave `db` local do `sbctl` + certificados `Microsoft Windows Production PCA` e **`Microsoft Corporation UEFI CA`** (Option ROMs). | Chave `db` local do `sbctl` + certificados Microsoft embutidos no `sbctl` **+** cópia bruta de `dbDefault` do firmware (que já contém os mesmos certificados Microsoft + certificados OEM MSI). | Somente a chave `db` local do `sbctl`. |
| **O que acontece com a `dbx`** | Preserva a `dbx` existente na NVRAM. | Copia `dbxDefault` / preserva entradas padrão do firmware. | Preserva a `dbx` existente. |
| **Risco de duplicidade de certificados na NVRAM** | **Zero.** O conjunto de certificados inscritos pelo `sbctl` é limpo, deduplicado e de tamanho previsível. | **Existente e documentado.** Como `dbDefault` e `KEKDefault` da placa-mãe já incluem os certificados da Microsoft, combinar `--microsoft` com `--firmware-builtin` em várias versões do `sbctl` ou firmwares (documentado oficialmente na Wiki do CachyOS para placas ASUS/Gigabyte e relatado em NVRAMs com limite estrito de tamanho de variável EFI) pode duplicar entradas `builtin-db`/`microsoft` ou exceder o buffer de escrita da variável `db` (`input/output error` / `Secure Boot Violation`). | **Zero**, mas remove a confiança em Option ROMs de terceiros. |
| **Compatibilidade com a Option ROM da GPU Radeon RX 9060 XT** | **Total.** As Option ROMs/GOP de GPUs comerciais AMD Radeon são assinadas pela **Microsoft Corporation UEFI CA**, que é incluída por `--microsoft`. | **Total**, porém com payload de variável EFI maior e redundante. | **Perigoso em PCs sem vídeo integrado (como o Ryzen 5 7500F):** o firmware pode bloquear o driver GOP da RX 9060 XT no POST, causando tela preta. |

### Conclusão técnica sobre o helper `nox-secureboot-enroll`
- **Não confunda `--firmware-builtin` com "manter a PK original da MSI":** ambos os métodos substituem a `PK` ativa pela `PK` local do `sbctl`. A diferença é apenas se o `sbctl` copia ou não o conteúdo bruto das variáveis `*Default` da ROM para dentro de `KEK`/`db`.
- Para o hardware do proprietário (**MSI PRO B650M-P + Ryzen 5 7500F + ASRock Radeon RX 9060 XT**), **`sbctl enroll-keys --microsoft`** (que já é o comportamento padrão de `sudo nox-secureboot-enroll --yes-enroll-uefi-keys`) é o caminho **mais limpo, seguro e determinístico**: ele inclui os certificados Microsoft necessários para a Option ROM da Radeon RX 9060 XT e para atualizações de `dbx`, sem correr o risco de duplicar certificados na NVRAM com `--firmware-builtin`.
- Por isso, **nenhuma alteração de código no helper `nox-secureboot-enroll` foi necessária**: ele já implementa a opção técnica mais segura.

---

## 4. Proteção crítica de vídeo para a Radeon RX 9060 XT (Por que o Ryzen 5 7500F exige cuidado redobrado)

Preste muita atenção a esta característica específica do seu computador físico:

1. **O processador AMD Ryzen 5 7500F não possui vídeo integrado (iGPU):**
   - Na nomenclatura da AMD para a linha Ryzen 7000 (AM5), o sufixo **`F`** significa que a GPU integrada nos conectores HDMI/VGA da placa-mãe está **fisicamente desativada no processador**.
   - Isso significa que **100% da imagem que você vê no monitor — inclusive a tela da BIOS da MSI e o menu do Limine — depende exclusivamente da placa de vídeo dedicada ASRock Radeon RX 9060 XT**.
2. **Como a RX 9060 XT exibe imagem antes do Linux carregar:**
   - Durante o POST (logo que você liga o PC), a BIOS da MSI PRO B650M-P lê o módulo **UEFI GOP (Option ROM)** gravado na memória flash VBIOS (`113-APM7842CL-102`) da sua RX 9060 XT.
   - Se o Secure Boot estiver ativo e com política restrita (`Deny Execute` para Option ROM), a BIOS da MSI verifica a assinatura digital desse driver GOP da RX 9060 XT contra a base **`db`** da placa-mãe.
   - Se o certificado **`Microsoft Corporation UEFI CA`** estiver presente na `db` (o que é garantido pelo padrão `--microsoft` do `nox-secureboot-enroll`), a assinatura da Option ROM da RX 9060 XT é validada com sucesso e o vídeo funciona normalmente desde o primeiro segundo do boot.
   - Se alguém executasse `nox-secureboot-enroll --no-microsoft` (sem `--microsoft`) **e** ativasse a verificação estrita de Option ROM, a placa-mãe recusaria o driver GOP da RX 9060 XT. Como o Ryzen 5 7500F não tem vídeo integrado de reserva na placa-mãe, o PC ligaria com **tela preta** (sem exibir nem a tela da BIOS!).

### Regras obrigatórias de segurança para a sua RX 9060 XT
1. **Sempre utilize o modo padrão do `nox-secureboot-enroll` (que inclui `--microsoft`).** Nunca use `--no-microsoft` nesta máquina.
2. **Nunca utilize flags do `sbctl` que tentem contornar ou desabilitar verificações de Option ROM de forma improvisada.**
3. **Saiba onde fica o jumper `JBAT1` (Clear CMOS) antes de ativar o Secure Boot:** caso qualquer configuração de BIOS deixe o PC sem vídeo durante um teste, desligar a fonte e fechar contato nos 2 pinos do jumper **`JBAT1`** da MSI PRO B650M-P por 5 a 10 segundos reseta as configurações da BIOS para o padrão de fábrica (desativando o Secure Boot imediatamente e devolvendo a imagem da RX 9060 XT no próximo boot).

---

## 5. Investigação e solução documentada do alerta `FQ0001` na MSI

### 5.1. O que é o alerta `FQ0001` em termos simples
O alerta **`FQ0001: Defaults to executing on Secure Boot policy violation (CRITICAL)`** (documentado em [`github.com/Foxboron/sbctl/wiki/FQ0001`](https://github.com/Foxboron/sbctl/wiki/FQ0001) e abordado na nota oficial da MSI sobre Secure Boot) foi descoberto quando pesquisadores e usuários de Linux notaram que diversas placas-mãe MSI vinham de fábrica com uma configuração curiosa na BIOS:

- Mesmo quando o usuário colocava **Secure Boot = Enabled**, a política interna de reação a falhas (*Image Execution Policy* ou *Secure Boot Preset*) vinha configurada em **`Always Execute`** (Sempre Executar) ou **`Hardware/OS Compatibility`** (Compatibilidade).
- Na prática, isso fazia a BIOS verificar a assinatura do arquivo `.efi`, perceber que a assinatura não batia, mas **deixar o arquivo iniciar mesmo assim** para evitar reclamações de usuários com pendrives ou placas antigas!
- Ou seja: o sistema operacional informava que o Secure Boot estava "Ativo", mas a placa-mãe não estava bloqueando nada.

### 5.2. As duas opções de correção na BIOS MSI (Dependendo da versão/menu da BIOS)

Na família **MSI Click BIOS 5** (utilizada na **MSI PRO B650M-P / MS-7E27**), existem duas formas pelas quais a MSI expõe essa política dentro de **`Settings → Security → Secure Boot`** (após mudar **Secure Boot Mode** para **`Custom`**):

#### Opção A — Menu com `Secure Boot Preset` (Presente em revisões recentes de BIOS MSI AM5)
Quando você muda **Secure Boot Mode** para **`Custom`**, aparece uma opção chamada **`Secure Boot Preset`**:
- O valor padrão de fábrica costuma ser `Hardware/OS Compatibility` (que permite executar imagens mesmo com violação de assinatura).
- **Ação correta:** altere **`Secure Boot Preset`** para **`Maximum Security`**.
- **Efeito:** a BIOS passa a bloquear efetivamente qualquer bootloader, kernel ou mídia cujo certificado não esteja na `db` (ou esteja revogado na `dbx`).

#### Opção B — Menu com `Image Execution Policy` (Presente em revisões de Click BIOS 5 que detalham por categoria)
Quando você muda **Secure Boot Mode** para **`Custom`**, aparece um submenu chamado **`Image Execution Policy`** com três itens internos:
1. **`Internal FV`** (Firmware Volume interno da placa-mãe — sempre mantido em `Always Execute`).
2. **`Option ROM`** (Firmware de placas PCIe, como a Radeon RX 9060 XT).
3. **`Removable Media`** (Pendrives USB e mídias externas).
4. **`Fixed Media`** (SSDs NVMe e discos SATA internos).

Na configuração permissiva que causa o `FQ0001`, `Removable Media` e `Fixed Media` (e às vezes `Option ROM`) vêm como **`Always Execute`**.
- **Ação correta na Opção B:**
  - Altere **`Removable Media`** de `Always Execute` para **`Deny Execute`**.
  - Altere **`Fixed Media`** de `Always Execute` para **`Deny Execute`**.
  - Para **`Option ROM`**: desde que você tenha inscrito as chaves com `--microsoft` (padrão do `nox-secureboot-enroll`), você pode alterar **`Option ROM`** para **`Deny Execute`** (ou, caso queira testar em duas etapas com máxima cautela na máquina sem iGPU, teste primeiro o boot com `Removable Media = Deny Execute` e `Fixed Media = Deny Execute`, confirme que o Linux iniciou normalmente e, em seguida, mude também `Option ROM = Deny Execute`).

### 5.3. Regra condicional para a sua BIOS física (`1.I2` ou superior)
Como a MSI pode alterar o nome exato do submenu entre revisões da BIOS `7E27v1x` (como a sua `1.I2` de 20/03/2026 ou versões posteriores):

> **Regra de decisão presencial na BIOS da MSI PRO B650M-P:**
> 1. Entre em **`Settings → Security → Secure Boot`** e mude **`Secure Boot Mode`** para **`Custom`**.
> 2. **Se a sua BIOS mostrar `Secure Boot Preset`:** selecione **`Maximum Security`** (Opção A).
> 3. **Se a sua BIOS mostrar `Image Execution Policy`:** entre nesse submenu e mude **`Removable Media`** e **`Fixed Media`** (e **`Option ROM`**, com `--microsoft` inscrito) de `Always Execute` para **`Deny Execute`** (Opção B).
> 4. **Se a sua BIOS mostrar AMBAS (`Secure Boot Preset` e `Image Execution Policy`):** ao selecionar `Secure Boot Preset → Maximum Security`, confira dentro de `Image Execution Policy` se `Removable Media` e `Fixed Media` mudaram automaticamente para `Deny Execute`.
> 5. **Se a sua BIOS não mostrar nenhuma das duas opções mesmo em modo `Custom`:** **PARE**, não apague as chaves e confira a versão do firmware na página oficial de suporte da MSI (`PRO B650M-P / MS-7E27`).

### 5.4. Como verificar de verdade se o `FQ0001` foi corrigido (Atenção ao comportamento do `sbctl status`)

Este é um detalhe técnico fundamental que confunde muitos usuários:

- **Como o `sbctl` detecta o `FQ0001`:** dependendo da versão do `sbctl` e de como a BIOS MSI expõe suas variáveis DMI/SMBIOS e variáveis proprietárias na NVRAM, o `sbctl` pode emitir o aviso `FQ0001` com base na assinatura/familia do firmware MSI (ou na presença de variáveis padrão da APTIO V), **mesmo depois** que você mudou a opção na BIOS para `Maximum Security` / `Deny Execute`! Em outras versões, o alerta desaparece assim que a variável de política da NVRAM muda.
- Portanto: **não confie apenas no sumiço ou permanência do texto `FQ0001` no `sbctl status` para declarar que a política de execução está funcionando.**

#### O Teste Definitivo e Controlado de Rejeição (Comprovação Real)
Para ter **100% de certeza física** de que a sua MSI PRO B650M-P está realmente aplicando o Secure Boot e bloqueando código não assinado:

1. Com o Secure Boot ativo e o Project Nox iniciando normalmente pelo SSD (porque o Limine do seu SSD está assinado pelas suas chaves), conecte o **pendrive com a ISO oficial do Arch Linux** (cujo bootloader **não** foi assinado pela sua chave privada local do `/var/lib/sbctl/keys/`).
2. Reinicie o computador, pressione **`F11`** para abrir o menu de boot da MSI e escolha iniciar pelo **pendrive USB da ISO do Arch Linux**.
3. **Resultado esperado quando o `FQ0001` foi corrigido com sucesso:**
   - A placa-mãe **recusa** o boot do pendrive e exibe uma caixa vermelha/mensagem na tela:
     **`Secure Boot Violation — Invalid signature detected. Check Secure Boot Policy in Setup.`**
   - Em seguida, ao remover o pendrive ou reiniciar normalmente pelo SSD interno, o **Project Nox (Limine)** inicia sem nenhum erro!
4. **O que significa esse teste:**
   - Se o pendrive não assinado pelas suas chaves foi **bloqueado** (`Secure Boot Violation`) e o seu SSD assinado pelas suas chaves **iniciou normalmente**, está **fisicamente comprovado** que o Secure Boot e a correção do `FQ0001` estão funcionando de verdade na sua MSI PRO B650M-P — independentemente de qualquer aviso estático de modelo no `sbctl status`!
5. **E se o pendrive não assinado iniciar normalmente mesmo com Secure Boot = Enabled?**
   - Isso significa que a política da BIOS ainda está em `Always Execute` / `Hardware/OS Compatibility`. Volte à BIOS em `Settings → Security → Secure Boot` e aplique `Maximum Security` / `Deny Execute` em `Removable Media` e `Fixed Media`.

---

## 6. Cenários técnicos documentados em placas MSI / AM5 (Upstream e Wikis Oficiais)

Para complementar a documentação oficial do `sbctl`, Arch Wiki, CachyOS Wiki e MSI, consolidamos seis cenários técnicos documentados nas referências oficiais upstream envolvendo placas MSI (incluindo B650/AM5), `sbctl`, `FQ0001` e GPUs AMD Radeon:

### Cenário Técnico 1 — Firmware MSI Desktop com `FQ0001` permitindo boot não assinado por padrão
1. **Plataforma documentada:** Placas desktop MSI UEFI Aptio V (séries Intel e AMD AM4/AM5, documentado originalmente por Morten Linderud / Foxboron).
2. **Versão da BIOS:** Múltiplas versões de fábrica lançadas com o padrão *Always Execute*.
3. **Distribuição:** Arch Linux.
4. **Estado inicial das chaves:** Chaves de fábrica MSI + Microsoft presentes; `Secure Boot = Enabled` ativado no firmware sem ajuste de política de execução.
5. **Comportamento documentado:** Mesmo com `Secure Boot: Enabled`, o firmware iniciava imagens EFI sem assinatura válida porque `Image Execution Policy` para `Removable Media` e `Fixed Media` vinha em `Always Execute`.
6. **Correção técnica documentada:** Mudança de `Secure Boot Mode` para `Custom`, ajuste de `Secure Boot Preset` para `Maximum Security` (ou `Image Execution Policy → Deny Execute` em `Option ROM`, `Removable Media` e `Fixed Media`), seguido de inscrição das chaves com `sbctl enroll-keys --microsoft`.
7. **Efeito esperado:** O firmware passa a bloquear binários EFI não assinados com `Secure Boot Violation`, mantendo o boot normal dos binários assinados pelo `sbctl`.
8. **Aplicação ao Nox Archinstall:** É a base direta da **Fase D** do procedimento físico deste guia para a MSI PRO B650M-P.
9. **Limitações da referência:** O nome do menu varia entre `Secure Boot Preset` e `Image Execution Policy` conforme a revisão da BIOS MSI.
10. **Referências upstream:** [Foxboron/sbctl Wiki — FQ0001](https://github.com/Foxboron/sbctl/wiki/FQ0001) · [MSI Official Statement on Secure Boot](https://us.msi.com/blog/statement-on-secure-boot)

### Cenário Técnico 2 — Auto-reprovisionamento de chaves de fábrica na MSI ao tentar entrar em Setup Mode
1. **Plataforma documentada:** Placas MSI B650 (Click BIOS 5, plataforma AM5).
2. **Versão da BIOS:** Revisões Click BIOS 5 AM5.
3. **Distribuição:** CachyOS / Arch Linux.
4. **Estado inicial das chaves:** `Setup Mode: Disabled`, `Secure Boot: Disabled`, chaves de fábrica MSI/Microsoft presentes.
5. **Comportamento documentado:** Ao apagar as chaves na BIOS para entrar em `Setup Mode`, se o firmware restaurar automaticamente as chaves padrão ao salvar/sair ou receber confirmação no prompt *"Enroll Factory Defaults?"*, o sistema retorna com `Setup Mode: Disabled`.
6. **Correção técnica documentada:** Em `Settings → Security → Secure Boot` (`Secure Boot Mode: Custom`), garantir que *Factory Default Key Provisioning* não permaneça ativo e, ao apagar todas as variáveis de Secure Boot (*Delete all Secure Boot variables*) e salvar com `F10`, responder **No / Cancel** caso o firmware pergunte se deseja recarregar as chaves de fábrica.
7. **Efeito esperado:** `sbctl status` passa a reportar `Setup Mode: Enabled`, permitindo executar `sbctl enroll-keys --microsoft`.
8. **Aplicação ao Nox Archinstall:** Documentado na **Fase B** deste guia para evitar ciclos de re-provisionamento automático antes da inscrição das chaves.
9. **Limitações da referência:** A redação exata do aviso (*"Enroll Factory Defaults?"* vs *"Initialize without keys"*) varia conforme a versão do Click BIOS 5.
10. **Referências upstream:** [CachyOS Wiki — Secure Boot Setup (MSI)](https://wiki.cachyos.org/configuration/secure_boot_setup/) · [Arch Wiki — Secure Boot: Putting firmware in Setup Mode](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot#Putting_firmware_in_%22Setup_Mode%22)

### Cenário Técnico 3 — Tela preta no POST com GPU dedicada AMD Radeon ao omitir `--microsoft`
1. **Plataforma documentada:** Placas desktop UEFI em plataformas sem vídeo integrado (GPU dedicada AMD Radeon).
2. **Versão da BIOS:** UEFI Aptio V com verificação de Option ROM ativa.
3. **Distribuição:** Arch Linux com `sbctl`.
4. **Estado inicial das chaves:** Firmware em `Setup Mode` com inscrição executada usando apenas chaves próprias (`sbctl enroll-keys` sem `--microsoft`).
5. **Comportamento documentado:** Ao reiniciar com Secure Boot e verificação de Option ROM ativos, o firmware rejeita o driver GOP da Option ROM da GPU AMD Radeon (assinado pela `Microsoft Corporation UEFI CA`), resultando em **tela preta** sem exibição do POST ou da BIOS.
6. **Correção técnica documentada:** Reset de CMOS via jumper (`JBAT1`) para desativar o Secure Boot e restaurar vídeo, limpeza para `Setup Mode` no Linux e nova inscrição com `sbctl enroll-keys --microsoft`.
7. **Efeito esperado:** Com `--microsoft` incluído na `db`, a Option ROM da GPU Radeon passa na validação do POST com Secure Boot ativo.
8. **Aplicação ao Nox Archinstall:** Fundamenta o uso padrão de `--microsoft` em `nox-secureboot-enroll` e a documentação preventiva do jumper `JBAT1` para o conjunto Ryzen 5 7500F (sem iGPU) + Radeon RX 9060 XT.
9. **Limitações da referência:** Quando `Option ROM` está em `Always Execute`, a omissão não bloqueia vídeo, mas o endurecimento completo de `FQ0001` (`Maximum Security` / `Deny Execute`) exige o certificado Microsoft UEFI CA na `db`.
10. **Referências upstream:** [Foxboron/sbctl Wiki — FAQ: Option ROMs](https://github.com/Foxboron/sbctl/wiki/FAQ#option-roms) · [Arch Wiki — Secure Boot: Microsoft Windows certificates / Option ROMs](https://wiki.archlinux.org/title/Unified_Extensible_Firmware_Interface/Secure_Boot#Microsoft_Windows)

### Cenário Técnico 4 — Duplicidade de chaves e `Secure Boot Violation` ao usar `--firmware-builtin`
1. **Plataforma documentada:** Placas desktop documentadas pela equipe do CachyOS (ASUS, Gigabyte e placas AM5).
2. **Versão da BIOS:** Firmwares UEFI com `dbDefault` contendo certificados Microsoft.
3. **Distribuição:** CachyOS.
4. **Estado inicial das chaves:** `Setup Mode: Enabled`.
5. **Comportamento documentado:** Ao executar `sbctl enroll-keys --microsoft --firmware-builtin`, entradas da variável `db` (`builtin-db` / certificados Microsoft já presentes em `dbDefault`) podem ser gravadas em duplicidade, provocando erro de NVRAM ou `Secure Boot Violation` ao ativar o Secure Boot.
6. **Correção técnica documentada:** Voltar ao `Setup Mode` na BIOS e executar exclusivamente `sbctl enroll-keys --microsoft` (sem `--firmware-builtin`).
7. **Efeito esperado:** Inscrição limpa da PK/KEK/`db` sem entradas duplicadas.
8. **Aplicação ao Nox Archinstall:** Confirma a decisão arquitetural da [Seção 3](#3-comparação-profunda---microsoft-versus---firmware-builtin-no-sbctl) de utilizar `sbctl enroll-keys --microsoft` em `nox-secureboot-enroll`.
9. **Limitações da referência:** O comportamento depende da implementação de `dbDefault` do fabricante UEFI, mas omitir `--firmware-builtin` em favor de `--microsoft` evita a falha sem perder suporte à Option ROM da GPU.
10. **Referência upstream:** [CachyOS Wiki — Configuração de Secure Boot (Aviso sobre `--firmware-builtin`)](https://wiki.cachyos.org/pt/configuration/secure_boot_setup/)

### Cenário Técnico 5 — `PANIC: CHECKSUM MISMATCH FOR CONFIG FILE` no Limine após alterar `limine.conf` ou restaurar snapshot
1. **Plataforma documentada:** Sistemas UEFI com Limine compilado com `ENABLE_ENROLL_LIMINE_CONFIG=yes`.
2. **Versão da BIOS:** Independente da BIOS (verificação realizada pelo próprio binário `limine_x64.efi`).
3. **Distribuição:** Arch Linux / CachyOS com `limine-mkinitcpio-hook` e `limine-snapper-sync`.
4. **Estado inicial das chaves:** Hash BLAKE2B inscrito em `limine_x64.efi` e assinado com `sbctl`.
5. **Comportamento documentado:** Se `/boot/limine.conf` for modificado sem atualização subsequente de `limine-enroll-config` e assinatura `sbctl`, o bootloader `limine_x64.efi` aborta a inicialização com `PANIC: CHECKSUM MISMATCH FOR CONFIG FILE`.
6. **Correção técnica documentada:** Iniciar pela ISO oficial do Arch Linux, montar a partição raiz e `/boot`, entrar em `arch-chroot` e executar `/usr/local/libexec/nox/nox-limine-integrity --force` (que normaliza `limine.conf`, atualiza `limine-enroll-config` e re-assina `BOOTX64.EFI` e `limine_x64.efi`).
7. **Efeito esperado:** Novo hash BLAKE2B inscrito e assinaturas UEFI sincronizadas.
8. **Aplicação ao Nox Archinstall:** Automatizado por `nox-limine-integrity` (modos `--repair-if-dirty`, `--force` e `--verify`, com preservação fail-closed do marcador `.dirty`) nos hooks e serviço `nox-limine-integrity-shutdown.service`.
9. **Limitações da referência:** Queda abrupta de energia durante a escrita na ESP continua coberta pelo fluxo de recuperação offline via ISO em [`docs/RECOVERY.md`](RECOVERY.md).
10. **Referências upstream:** [Arch Wiki — Limine: Configuration file verification (BLAKE2b)](https://wiki.archlinux.org/title/Limine#Configuration_file_verification) · [GitLab — Zesko/limine-mkinitcpio-hook (`limine-enroll-config`)](https://gitlab.com/Zesko/limine-mkinitcpio-hook)

### Cenário Técnico 6 — Travamentos de menu em revisões antigas da BIOS MSI PRO B650M-P e recuperação via Flash BIOS Button
1. **Plataforma documentada:** **MSI PRO B650M-P (`MS-7E27`)**.
2. **Versão da BIOS:** Revisões antigas da série `7E27v1x` anteriores às atualizações AGESA 2025/2026.
3. **Distribuição:** Independente de sistema operacional (interface UEFI Click BIOS 5).
4. **Estado inicial das chaves:** Padrão de fábrica.
5. **Comportamento documentado:** As notas de suporte e documentação de recuperação da placa preveem instabilidade ou configurações inválidas de NVRAM em revisões antigas, com recuperação prevista por **Clear CMOS (`JBAT1`)**, **M-Flash** ou botão físico traseiro **Flash BIOS Button** (`MSI.ROM` em pendrive FAT32).
6. **Correção técnica documentada:** Limpeza de CMOS em `JBAT1` para restaurar acesso ao firmware ou atualização via M-Flash / Flash BIOS Button para revisões recentes (`1.I2`, março de 2026 ou posterior).
7. **Efeito esperado:** Acesso estável à configuração de `Secure Boot Mode` e políticas UEFI sem travamentos de interface.
8. **Aplicação ao Nox Archinstall:** O ambiente físico de destino já utiliza revisão **`1.I2` (`20/03/2026`)**, mantendo `JBAT1` e **Flash BIOS Button** documentados como rede de segurança física caso uma configuração incorreta impeça o POST.
9. **Limitações da referência:** Atualizar a BIOS além da versão já instalada não é pré-requisito caso `Secure Boot Preset` ou `Image Execution Policy` já estejam disponíveis no menu atual.
10. **Referência upstream:** [Página Oficial de Suporte e BIOS — MSI PRO B650M-P](https://www.msi.com/Motherboard/PRO-B650M-P/support)

---

## 7. Preparação segura, backup e pontos de parada antes de modificar o firmware

Siga esta seção **depois** que o Project Nox já estiver instalado no seu SSD e iniciando normalmente no desktop (com o Secure Boot ainda desativado na BIOS).

### 7.1. Inventário e Backup das Chaves e Variáveis Atuais (`[LEITURA]` / `[MODIFICA O SISTEMA]`)

Abra o terminal Kitty (`Super + Q`) no seu Project Nox recém-instalado e execute os comandos abaixo para salvar uma cópia de segurança das suas chaves locais do `sbctl` e das variáveis públicas atuais da UEFI na sua pasta pessoal (`~/backup-secureboot-msi/`):

```bash
mkdir -p ~/backup-secureboot-msi/efivars-publicos
chmod 700 ~/backup-secureboot-msi

# 1. Registrar o estado inicial do sbctl, BIOS e assinaturas
sudo sbctl status > ~/backup-secureboot-msi/01-sbctl-status-inicial.txt
sudo nox-secureboot-verify > ~/backup-secureboot-msi/02-nox-verify-inicial.txt
cat /sys/class/dmi/id/board_vendor /sys/class/dmi/id/board_name /sys/class/dmi/id/bios_version /sys/class/dmi/id/bios_date > ~/backup-secureboot-msi/03-bios-info.txt

# 2. Copiar o conteúdo público das variáveis atuais PK, KEK, db e dbx da placa-mãe (somente leitura)
for var in PK KEK db dbx PKDefault KEKDefault dbDefault dbxDefault; do
  cp -a /sys/firmware/efi/efivars/${var}-* ~/backup-secureboot-msi/efivars-publicos/ 2>/dev/null || true
done

# 3. Fazer backup criptografado/protegido das chaves privadas geradas pelo Project Nox (/var/lib/sbctl/keys)
sudo tar -czf ~/backup-secureboot-msi/nox-sbctl-keys-backup.tar.gz -C /var/lib/sbctl keys
sudo chown "$USER:$USER" ~/backup-secureboot-msi/nox-sbctl-keys-backup.tar.gz
chmod 600 ~/backup-secureboot-msi/nox-sbctl-keys-backup.tar.gz
ls -la ~/backup-secureboot-msi/
```

> **O que esse backup contém (e o que ele NÃO contém):**
> - `nox-sbctl-keys-backup.tar.gz` guarda as **suas chaves privadas e públicas do Project Nox** (`/var/lib/sbctl/keys/`). **Nunca publique esse arquivo no GitHub ou na internet!** Se você quiser, pode copiá-lo para um pendrive pessoal seguro.
> - `efivars-publicos/` guarda uma cópia dos **certificados públicos** que estavam na NVRAM da MSI antes da mudança (`PK`, `KEK`, `db`, `dbx` e `*Default`). Lembre-se: nenhuma placa-mãe expõe as chaves *privadas* da MSI; para restaurar as chaves originais de fábrica da MSI na NVRAM a qualquer momento, usa-se a opção nativa da BIOS **`Enroll all Factory Default keys`** (que lê `PKDefault`, `KEKDefault` e `dbDefault` direto da ROM da placa-mãe).

### 7.2. Mídia de Recuperação Obrigatória
Mantenha ao seu lado o **pendrive USB com a ISO oficial do Arch Linux (`archlinux-2026.11.01-x86_64.iso`)** que você usou para instalar o sistema.
- Se precisar iniciar por esse pendrive no futuro enquanto o Secure Boot estiver ativo na MSI, basta entrar na BIOS (`Del`), mudar **Secure Boot** para **`Disabled`**, salvar (`F10`) e dar boot pelo pendrive (`F11`).
- Todo o passo a passo de montagem dos subvolumes Btrfs (`@`, `@home`, `@log`, `@pkg`, `@.snapshots`) e de `/boot` a partir do pendrive está documentado em **[`docs/RECOVERY.md`](RECOVERY.md)**.

### 7.3. Checklist Obrigatório de Ponto de Parada (Leia antes de ir para a Seção 8)

**Antes de continuar para a Fase B, confirme que todas as respostas abaixo são "SIM":**

- [ ] O Project Nox já foi instalado no SSD e iniciou normalmente até o desktop (Umbriel + Noctalia)?
- [ ] Tenho o pendrive com a ISO oficial do Arch Linux guardado e funcionando?
- [ ] Sei entrar na BIOS da MSI PRO B650M-P pressionando a tecla **`Del`** ao ligar o computador?
- [ ] Sei qual é o meu SSD do Project Nox (`lsblk -f`)?
- [ ] Sei diferenciar **`Setup Mode: Enabled`** (modo temporário para inscrever chaves) de **`Secure Boot: Disabled`** (verificação desligada)?
- [ ] Entendi que na minha máquina (**Ryzen 5 7500F sem vídeo integrado + Radeon RX 9060 XT**) devo usar o comando padrão `sudo nox-secureboot-enroll --yes-enroll-uefi-keys` (que inclui **`--microsoft`**) para preservar o vídeo da placa dedicada no POST?
- [ ] Sei onde fica o jumper **`JBAT1`** (Clear CMOS) na MSI PRO B650M-P caso precise resetar configurações da BIOS para o padrão de fábrica?

Se qualquer item acima não estiver claro, **pare aqui** e releia a seção correspondente antes de alterar a BIOS.

---

## 8. Procedimento físico passo a passo na MSI PRO B650M-P (Fases A a F)

Cada etapa abaixo indica explicitamente se a ação é de **`[LEITURA]`**, **`[MODIFICA O SISTEMA]`** ou **`[MODIFICA O FIRMWARE UEFI]`**.

---

### Fase A — Verificação prévia das assinaturas e do hash BLAKE2B no Linux (`[LEITURA]` / `[MODIFICA O SISTEMA]`)

- **Objetivo:** comprovar que as chaves locais em `/var/lib/sbctl/keys/` existem e que `/boot/EFI/limine/limine_x64.efi`, `/boot/EFI/BOOT/BOOTX64.EFI` e o kernel `vmlinuz` estão assinados e com o hash BLAKE2B de `/boot/limine.conf` sincronizado.
- **Por que:** garante que os arquivos do SSD já estão prontos para o Secure Boot antes mesmo de entrarmos na BIOS.
- **Antes de executar:** estar logado normalmente no desktop do Project Nox com Secure Boot ainda desativado.
- **Comandos no terminal Kitty:**
  ```bash
  sudo /usr/local/libexec/nox/nox-limine-integrity
  sudo nox-secureboot-verify
  sudo sbctl status
  ```
- **Resultado esperado:**
  - `nox-limine-integrity` não exibe erro (saída vazia quando tudo já está convergido).
  - `nox-secureboot-verify` exibe `✓ ... is signed` para os 3 arquivos (`vmlinuz`, `BOOTX64.EFI` e `limine_x64.efi`) e termina com:
    `[NOX SECUREBOOT] OK: /var/lib/sbctl/keys presente, Limine + kernel assinados e hash de limine.conf inscrito.`
- **Se der errado:** se algum arquivo não estiver assinado, execute `sudo /usr/local/libexec/nox/nox-limine-integrity --force` e repita `sudo nox-secureboot-verify`. **Não avance para a Fase B enquanto `nox-secureboot-verify` não exibir `OK`.**

---

### Fase B — Ativar o `Setup Mode` na BIOS da MSI PRO B650M-P (`[MODIFICA O FIRMWARE UEFI]`)

- **Objetivo:** colocar a MSI PRO B650M-P em **`Setup Mode`** (`PK` limpa) para permitir que o Linux inscreva as chaves do Project Nox + Microsoft na NVRAM.
- **Por que:** em `User Mode` (`Setup Mode: Disabled`), a NVRAM da MSI rejeita a gravação de uma nova `PK`.
- **Antes de executar:** a Fase A e o backup da Seção 7.1 devem estar concluídos.
- **Ação passo a passo na BIOS MSI:**
  1. No terminal do Project Nox, reinicie diretamente para a BIOS da MSI:
     ```bash
     systemctl reboot --firmware-setup
     ```
     *(Ou reinicie e pressione a tecla **`Del`** repetidamente até abrir o MSI Click BIOS 5).*
  2. Se a BIOS abrir no *EZ Mode* (modo simplificado), pressione **`F7`** para mudar para o **Advanced Mode**.
  3. Clique no bloco **`Settings`** (à esquerda) → **`Security`** → **`Secure Boot`**.
  4. Mantenha **`Secure Boot`** como **`Disabled`** por enquanto.
  5. Mude **`Secure Boot Mode`** de `Standard` para **`Custom`**.
  6. Clique em **`Key Management`** (Gerenciamento de Chaves):
     - Verifique se existe a opção **`Factory Default Key Provisioning`** (Auto-provisionamento de chaves de fábrica). Se existir e estiver `Enabled`, mude-a para **`Disabled`** (para que a placa não reinstale sozinha as chaves de fábrica ao reiniciar).
     - Selecione **`Delete all Secure Boot variables`** (ou entre em **`Platform Key (PK)` → `Delete`**).
     - Quando a BIOS perguntar se você confirma a exclusão das variáveis para entrar em *Setup Mode*, confirme (**`Yes`**).
     - **Atenção:** se logo em seguida aparecer uma segunda pergunta dizendo *"Do you want to enroll factory default keys?"* ou *"Reboot without saving / Restore defaults?"*, responda **`No`** para a restauração de fábrica (pois queremos justamente deixar a `PK` vazia em **Setup Mode**!).
     - Confirme na própria tela de `Key Management` que o estado passou a exibir **`System Mode: Setup`** (ou `PK: 0 / Not Installed`).
  7. Pressione **`F10`** (*Save Configuration and Reset*), confirme em **`Yes`** e deixe o computador iniciar normalmente no Project Nox.
- **Resultado esperado:** o computador inicia normalmente no menu do Limine e entra no desktop do Project Nox.
- **Se der errado:** se ao voltar para o Linux o comando `sudo sbctl status` ainda mostrar `Setup Mode: ✗ Disabled`, a BIOS re-provisionou as chaves de fábrica ao sair. Volte em `Settings → Security → Secure Boot → Key Management`, apague apenas a **`Platform Key (PK)`** (ou *Delete all Secure Boot variables* com *Factory Default Key Provisioning = Disabled*) e salve com `F10`.

---

### Fase C — Inscrever as chaves (`nox-secureboot-enroll`) e validar BLAKE2B no Linux (`[MODIFICA O FIRMWARE UEFI]` / `[MODIFICA O SISTEMA]`)

- **Objetivo:** inscrever a `PK`, `KEK` e `db` do Project Nox junto com os certificados Microsoft (`--microsoft`) na NVRAM da MSI PRO B650M-P e garantir que o Limine e o kernel estejam assinados e sincronizados.
- **Por que:** transfere a confiança criptográfica para a placa-mãe mantendo a Option ROM da Radeon RX 9060 XT confiável.
- **Antes de executar:** abra o terminal Kitty e confirme obrigatoriamente:
  ```bash
  sudo sbctl status
  ```
  A linha **`Setup Mode`** deve estar como **`✓ Enabled`**.
- **Comandos no terminal Kitty:**
  ```bash
  sudo nox-secureboot-enroll --yes-enroll-uefi-keys
  sudo nox-secureboot-verify
  sudo sbctl status
  ```
- **Resultado esperado:**
  1. `nox-secureboot-enroll` exibe:
     ```text
     Enrolling keys to EFI variables...
     With vendor keys from microsoft...✓
     Enrolled keys to the EFI variables!
     Config file BLAKE2B successfully enrolled.
     ✓ Signed /boot/EFI/limine/limine_x64.efi
     Config file BLAKE2B successfully enrolled.
     Verifying file database and EFI images in /boot...
     ✓ /boot/<machine-id>/linux-cachyos/vmlinuz is signed
     ✓ /boot/EFI/BOOT/BOOTX64.EFI is signed
     ✓ /boot/EFI/limine/limine_x64.efi is signed
     [NOX SECUREBOOT] Chaves inscritas e cadeia Limine re-assinada com sucesso.
     ```
  2. `sudo sbctl status` agora mostra **`Installed: ✓ sbctl is installed`** e **`Setup Mode: ✗ Disabled`** (porque a sua `PK` acabou de ser gravada, colocando a placa em `User Mode` sob o seu controle!).
- **Se der errado:** se o comando `sbctl enroll-keys` reportar qualquer erro, **não ative o Secure Boot na BIOS**. Leia a mensagem de erro no terminal e, se necessário, restaure as chaves de fábrica na BIOS (*Enroll all Factory Default keys*) mantendo `Secure Boot = Disabled`.

---

### Fase D — Endurecer a política contra o `FQ0001` e Ativar o Secure Boot na BIOS MSI (`[MODIFICA O FIRMWARE UEFI]`)

- **Objetivo:** corrigir a política permissiva `FQ0001` da MSI e ativar o **Secure Boot**.
- **Por que:** sem ajustar `Secure Boot Preset` ou `Image Execution Policy`, a placa MSI ativaria o Secure Boot mantendo a política `Always Execute` (`FQ0001`).
- **Antes de executar:** a Fase C deve ter concluído com `[NOX SECUREBOOT] Chaves inscritas e cadeia Limine re-assinada com sucesso.` e `sudo nox-secureboot-verify` deve ter retornado `OK`.
- **Ação passo a passo na BIOS MSI:**
  1. No terminal Kitty, reinicie para a BIOS:
     ```bash
     systemctl reboot --firmware-setup
     ```
  2. Pressione **`F7`** (Advanced Mode) e vá em **`Settings → Security → Secure Boot`**.
  3. Confirme que **`Secure Boot Mode`** está em **`Custom`**.
  4. Aplique a política de execução conforme o menu exibido pela sua BIOS (conforme explicamos na [Seção 5.3](#53-regra-condicional-para-a-sua-bios-física-1i2-ou-superior)):
     - **Caminho 1 (se aparecer `Secure Boot Preset`):** mude **`Secure Boot Preset`** para **`Maximum Security`**.
     - **Caminho 2 (se aparecer `Image Execution Policy`):** entre em **`Image Execution Policy`** e mude **`Removable Media`**, **`Fixed Media`** e **`Option ROM`** de `Always Execute` para **`Deny Execute`** *(lembrando que você inscreveu `--microsoft` na Fase C, portanto a Option ROM da RX 9060 XT possui certificado válido na `db`)* — ou, se preferir fazer em dois passos, mude primeiro `Removable Media` e `Fixed Media` para `Deny Execute`, teste o boot na Fase E e depois mude `Option ROM` para `Deny Execute`.
  5. Mude **`Secure Boot`** de `Disabled` para **`Enabled`**.
  6. Anote em um papel quais opções você alterou, pressione **`F10`** (*Save Configuration and Reset*) e confirme em **`Yes`**.
- **Resultado esperado:** a placa-mãe reinicia, a Radeon RX 9060 XT exibe imagem normalmente no monitor Samsung Odyssey G5 (`DP-1`), o menu do **Limine (`Project Nox`)** carrega e o sistema inicia até o **Noctalia Greeter**.

---

### Fase E — Validação Pós-Ativação noPrimeiro Boot com Secure Boot Ativo (`[LEITURA]`)

- **Objetivo:** comprovar dentro do Linux que o Secure Boot está ativo no firmware UEFI, que toda a cadeia Limine + BLAKE2B + `sbctl` está íntegra e (opcionalmente) realizar o teste físico de bloqueio de mídia não assinada.
- **Por que:** encerra o ciclo de ativação com evidência real do sistema em execução.
- **Comandos no terminal Kitty após fazer login:**
  ```bash
  sudo sbctl status
  sudo nox-secureboot-verify --require-active
  bootctl status 2>/dev/null | grep -i "Secure Boot" || od -An -t u1 /sys/firmware/efi/efivars/SecureBoot-*
  ```
- **Resultado esperado:**
  - `sudo nox-secureboot-verify --require-active` retorna:
    ```text
    ✓ /boot/<machine-id>/linux-cachyos/vmlinuz is signed
    ✓ /boot/EFI/BOOT/BOOTX64.EFI is signed
    ✓ /boot/EFI/limine/limine_x64.efi is signed
    [NOX SECUREBOOT] OK: /var/lib/sbctl/keys presente, Limine + kernel assinados e hash de limine.conf inscrito.
    ```
  - O último byte da variável EFI `/sys/firmware/efi/efivars/SecureBoot-*` é **`1`** (indicando `Secure Boot = Enabled` diretamente no kernel Linux).
  - Para confirmar fisicamente o bloqueio do `FQ0001`, você pode realizar o teste controlado do pendrive da ISO descrito na [Seção 5.4](#o-teste-definitivo-e-controlado-de-rejeição-comprovação-real).

---

### Fase F — Procedimentos de Recuperação Específicos da MSI PRO B650M-P

Caso qualquer comportamento inesperado ocorra após a Fase D, siga exatamente o cenário correspondente abaixo:

#### Cenário F.1 — A BIOS exibiu `Secure Boot Violation` ao tentar iniciar o SSD
1. Pressione `Enter` ou reinicie e pressione **`Del`** para entrar na BIOS da MSI.
2. Vá em **`Settings → Security → Secure Boot`** e mude **`Secure Boot`** para **`Disabled`**.
3. Pressione **`F10`** para salvar e inicie o Project Nox normalmente.
4. No terminal Kitty, repare e re-assine a cadeia de boot com um único comando:
   ```bash
   sudo /usr/local/libexec/nox/nox-limine-integrity --force
   sudo nox-secureboot-verify
   ```
5. Se `nox-secureboot-verify` confirmar os 3 arquivos assinados (`✓`), mas a BIOS ainda recusar o boot ao religar o Secure Boot, significa que as chaves na NVRAM não correspondem às chaves de `/var/lib/sbctl/keys/`: volte à **Fase B** (limpe as variáveis para `Setup Mode`) e repita a **Fase C** (`sudo nox-secureboot-enroll --yes-enroll-uefi-keys`).

#### Cenário F.2 — O Limine exibiu `PANIC: CHECKSUM MISMATCH FOR CONFIG FILE`
- Isso não é bloqueio da BIOS da MSI: a BIOS aceitou a assinatura do `limine_x64.efi`, mas o próprio Limine detectou que `/boot/limine.conf` foi alterado sem atualizar o hash BLAKE2B interno.
- Entre na BIOS (`Del`), desative o Secure Boot temporariamente se precisar dar boot pelo pendrive da ISO oficial do Arch Linux, monte o sistema em `/mnt` conforme **[`docs/RECOVERY.md`](RECOVERY.md)** e execute:
  ```bash
  arch-chroot /mnt /usr/local/libexec/nox/nox-limine-integrity --force
  ```

#### Cenário F.3 — O computador ligou sem imagem no monitor (Tela Preta após alterar Option ROM)
Como o Ryzen 5 7500F não possui vídeo integrado, se uma configuração incorreta de Option ROM impedir a inicialização visual da RX 9060 XT:
1. Desligue o computador e **desconecte o cabo de energia da fonte** da tomada (ou desligue a chave traseira `I/O` da fonte).
2. Aguarde 15 segundos para descarregar os capacitores.
3. Localize o conector de 2 pinos **`JBAT1`** na parte inferior da placa-mãe **MSI PRO B650M-P**.
4. Encoste a ponta metálica de uma chave de fenda limpa (ou um jumper) ligando os dois pinos do **`JBAT1`** durante **10 segundos**.
5. Retire a chave de fenda, reconecte o cabo de força e ligue o computador.
6. A BIOS será reiniciada com as configurações padrão de fábrica (com `Secure Boot = Disabled`), restaurando imediatamente o sinal de vídeo da Radeon RX 9060 XT no monitor!

#### Cenário F.4 — Como retornar a MSI PRO B650M-P às chaves originais de fábrica da MSI
Se em qualquer momento você desejar remover suas chaves personalizadas da placa-mãe e voltar exatamente às chaves de fábrica originais (`microsoft builtin-db builtin-KEK builtin-PK`):
1. Entre na BIOS (`Del` → `F7` Advanced Mode).
2. Vá em **`Settings → Security → Secure Boot`**.
3. Mude **`Secure Boot`** para **`Disabled`** e **`Secure Boot Mode`** para **`Custom`**.
4. Entre em **`Key Management`** e selecione **`Enroll all Factory Default keys`** (Inscrever todas as chaves padrão de fábrica) → confirme em **`Yes`**.
5. Pressione **`F10`** para salvar e reiniciar.
