# Manual Completo de Recuperação — Nox Archinstall (`v1.0.0` / `v1.0.1`)

Este manual descreve, passo a passo, como recuperar o sistema **Project Nox** nos **10 cenários reais de falha ou manutenção** sem precisar formatar o SSD e sem perder seus arquivos pessoais em `/home`.

> **Duas regras fundamentais de recuperação:**
> 1. **Nunca use formatação como primeira opção de recuperação.** No layout Btrfs do Project Nox, seus dados pessoais ficam isolados no subvolume `@home`, as chaves de Secure Boot ficam em `/var/lib/sbctl/keys/` (dentro de `@`) e os snapshots ficam em `@.snapshots`. Quase qualquer problema de boot, kernel ou pacote pode ser resolvido em poucos minutos pelo menu de snapshots do Limine ou por `arch-chroot` a partir do pendrive da ISO oficial do Arch Linux.
> 2. **Não apague as chaves do Secure Boot na BIOS indiscriminadamente para qualquer erro de boot.** Primeiro identifique na tabela abaixo qual é o sintoma exato e siga o procedimento específico.

---

## Sumário Rápido dos 10 Cenários

- [Procedimento Base: Como iniciar pela ISO oficial do Arch Linux e entrar no `arch-chroot`](#procedimento-base-como-iniciar-pela-iso-oficial-do-arch-linux-e-entrar-no-arch-chroot)
- [Cenário 1 — O menu do Limine não aparece (cai direto na BIOS ou não encontra dispositivo de boot)](#cenário-1--o-menu-do-limine-não-aparece-cai-direto-na-bios-ou-não-encontra-dispositivo-de-boot)
- [Cenário 2 — Arquivo EFI perdeu a assinatura (`Secure Boot Violation` ao atualizar ou iniciar)](#cenário-2--arquivo-efi-perdeu-a-assinatura-secure-boot-violation-ao-atualizar-ou-iniciar)
- [Cenário 3 — Hash BLAKE2B não corresponde (`PANIC: CHECKSUM MISMATCH FOR CONFIG FILE`)](#cenário-3--hash-blake2b-não-corresponde-panic-checksum-mismatch-for-config-file)
- [Cenário 4 — Atualização de kernel (`linux-cachyos`) foi interrompida e deixou o boot inconsistente](#cenário-4--atualização-de-kernel-linux-cachyos-foi-interrompida-e-deixou-o-boot-inconsistente)
- [Cenário 5 — Restaurar um snapshot Btrfs/Snapper anterior (pelo sistema ou via ISO)](#cenário-5--restaurar-um-snapshot-btrfssnapper-anterior-pelo-sistema-ou-via-iso)
- [Cenário 6 — Secure Boot foi ativado na BIOS antes das assinaturas estarem prontas](#cenário-6--secure-boot-foi-ativado-na-bios-antes-das-assinaturas-estarem-prontas)
- [Cenário 7 — As chaves cadastradas na NVRAM não coincidem com as chaves do sistema](#cenário-7--as-chaves-cadastradas-na-nvram-não-coincidem-com-as-chaves-do-sistema)
- [Cenário 8 — A BIOS MSI está bloqueando uma imagem EFI específica após ativar `Maximum Security`](#cenário-8--a-bios-msi-está-bloqueando-uma-imagem-efi-específica-após-ativar-maximum-security)
- [Cenário 9 — A GPU (Radeon RX 9060 XT) não apresenta imagem após mudança de política de Option ROM](#cenário-9--a-gpu-radeon-rx-9060-xt-não-apresenta-imagem-após-mudança-de-política-de-option-rom)
- [Cenário 10 — O pendrive da ISO oficial do Arch Linux não inicia porque o Secure Boot está ativo](#cenário-10--o-pendrive-da-iso-oficial-do-arch-linux-não-inicia-porque-o-secure-boot-está-ativo)

---

## Procedimento Base: Como iniciar pela ISO oficial do Arch Linux e entrar no `arch-chroot`

Vários cenários abaixo utilizam o ambiente de recuperação da ISO oficial do Arch Linux (`archlinux-2026.11.01-x86_64.iso`). Sempre que um cenário pedir para **"montar o sistema e entrar no `arch-chroot`"**, execute exatamente estes passos:

### Passo 1 — Iniciar pelo pendrive da ISO oficial
1. Conecte o pendrive com a ISO oficial do Arch Linux.
2. Se o **Secure Boot** estiver ativo na BIOS, pressione **`Del`** ao ligar o computador, vá em **`Settings → Security → Secure Boot`**, mude **Secure Boot** temporariamente para **`Disabled`** e pressione **`F10`** para salvar (veja o [Cenário 10](#cenário-10--o-pendrive-da-iso-oficial-do-arch-linux-não-inicia-porque-o-secure-boot-está-ativo)).
3. Pressione **`F11`** para abrir o menu de boot e escolha a entrada **`UEFI: <seu pendrive>`**.

### Passo 2 — Identificar as partições do seu SSD por UUID e tipo (`lsblk -f`)
No terminal `root@archiso ~ #`, liste os discos e sistemas de arquivos sem formatar nada:

```bash
lsblk -f
```

No particionamento padrão criado pelo Project Nox, o seu SSD terá **duas partições**:
- **Partição 1 (`vfat` / `FAT32`, tamanho `4G`):** é a partição **ESP** (`/boot`), por exemplo `/dev/nvme0n1p1`.
- **Partição 2 (`btrfs`, restante do disco):** é a partição que contém todos os subvolumes Btrfs (`@`, `@home`, `@log`, `@pkg`, `@.snapshots`, `@swap`), por exemplo `/dev/nvme0n1p2`.

Para não errar o nome do dispositivo mesmo que haja mais de um disco conectado, defina duas variáveis no terminal usando os caminhos conferidos no `lsblk -f` (ou seus `UUID=`):

```bash
ESP_PART="/dev/nvme0n1p1"     # Substitua pela sua partição FAT32 de 4 GiB
BTRFS_PART="/dev/nvme0n1p2"   # Substitua pela sua partição Btrfs principal
```

### Passo 3 — Conferir e montar os subvolumes Btrfs e a ESP (`/boot`)
Monte o subvolume raiz `@` em `/mnt`, os demais subvolumes nos seus pontos corretos e a partição EFI em `/mnt/boot`:

```bash
mount -o subvol=@,compress=zstd:3 "$BTRFS_PART" /mnt
mount -o subvol=@home,compress=zstd:3 "$BTRFS_PART" /mnt/home
mount -o subvol=@log,compress=zstd:3 "$BTRFS_PART" /mnt/var/log
mount -o subvol=@pkg,compress=zstd:3 "$BTRFS_PART" /mnt/var/cache/pacman/pkg
mount -o subvol=@.snapshots,compress=zstd:3 "$BTRFS_PART" /mnt/.snapshots
mount -o subvol=@swap,compress=zstd:3 "$BTRFS_PART" /mnt/nox-swap
mount "$ESP_PART" /mnt/boot
```

Confirme com `findmnt -R /mnt` que `/mnt`, `/mnt/boot`, `/mnt/home`, `/mnt/var/log` e `/mnt/.snapshots` estão montados.

### Passo 4 — Entrar no `arch-chroot`
```bash
arch-chroot /mnt
```
Agora você está executando comandos diretamente dentro do seu sistema Project Nox instalado!

---

## Cenário 1 — O menu do Limine não aparece (cai direto na BIOS ou não encontra dispositivo de boot)

- **Causa comum:** atualização de BIOS limpou a lista de entradas NVRAM de boot (`efibootmgr`), ou o arquivo `/boot/EFI/BOOT/BOOTX64.EFI` / `/boot/EFI/limine/limine_x64.efi` foi removido da ESP.
- **Como resolver:**
  1. Siga o **[Procedimento Base](#procedimento-base-como-iniciar-pela-iso-oficial-do-arch-linux-e-entrar-no-arch-chroot)** para montar o sistema e entrar no `arch-chroot /mnt`.
  2. Dentro do `arch-chroot`, reinstale os binários EFI do Limine (incluindo o caminho padrão de fallback `/boot/EFI/BOOT/BOOTX64.EFI`, que qualquer placa-mãe UEFI reconhece automaticamente mesmo se a NVRAM de boot tiver sido limpa) e sincronize a integridade:
     ```bash
     limine-install --fallback
     limine-update
     limine-snapper-sync || true
     /usr/local/libexec/nox/nox-limine-integrity --force
     nox-secureboot-verify
     ```
  3. Saia do chroot e reinicie:
     ```bash
     exit
     umount -R /mnt
     reboot
     ```

---

## Cenário 2 — Arquivo EFI perdeu a assinatura (`Secure Boot Violation` ao atualizar ou iniciar)

- **Causa comum:** algum binário em `/boot` (`limine_x64.efi`, `BOOTX64.EFI` ou `vmlinuz`) foi substituído sem que o hook final do `sbctl` terminasse de rodar.
- **Como resolver sem apagar chaves:**
  1. Entre na BIOS (`Del`), mude **Secure Boot** temporariamente para **`Disabled`** e pressione **`F10`**.
  2. Como o sistema está íntegro, o Project Nox iniciará normalmente pelo SSD!
  3. Faça login no seu usuário, abra o terminal Kitty (`Super + Q`) e execute:
     ```bash
     sudo /usr/local/libexec/nox/nox-limine-integrity --force
     sudo sbctl sign-all
     sudo nox-secureboot-verify
     ```
  4. Confirme que os 3 arquivos exibem `✓ is signed`.
  5. Reinicie na BIOS (`systemctl reboot --firmware-setup`), volte **Secure Boot** para **`Enabled`** e salve com `F10`.

---

## Cenário 3 — Hash BLAKE2B não corresponde (`PANIC: CHECKSUM MISMATCH FOR CONFIG FILE`)

- **Sintoma:** a placa-mãe passa pelo POST, carrega o Limine, mas o Limine para em uma tela de erro exibindo:
  `PANIC: CHECKSUM MISMATCH FOR CONFIG FILE`
- **Causa:** o arquivo texto `/boot/limine.conf` foi modificado (ou uma restauração de snapshot foi interrompida por queda de energia) antes que o comando `limine-enroll-config` gravasse o novo hash BLAKE2B de `/boot/limine.conf` dentro de `limine_x64.efi` e `BOOTX64.EFI`.
- **Observação importante:** desativar o Secure Boot na BIOS **não** pula essa verificação, porque quem verifica o hash BLAKE2B do `limine.conf` é o próprio binário `limine_x64.efi` (`ENABLE_VERIFICATION=yes`).
- **Como resolver em 1 minuto:**
  1. Siga o **[Procedimento Base](#procedimento-base-como-iniciar-pela-iso-oficial-do-arch-linux-e-entrar-no-arch-chroot)** para iniciar pelo pendrive da ISO oficial do Arch Linux, montar os subvolumes e `/mnt/boot`, e entrar no `arch-chroot /mnt`.
  2. Dentro do `arch-chroot`, execute o helper de integridade do Project Nox em modo forçado:
     ```bash
     /usr/local/libexec/nox/nox-limine-integrity --force
     nox-secureboot-verify
     ```
     *(Esse comando normaliza `/boot/limine.conf`, calcula o novo hash BLAKE2B, grava-o em `limine_x64.efi` e `BOOTX64.EFI` e re-assina tudo com as chaves de `/var/lib/sbctl/keys/`).*
  3. Saia do chroot, desmonte `/mnt` e reinicie:
     ```bash
     exit
     umount -R /mnt
     reboot
     ```
  4. Se você havia desativado o Secure Boot na BIOS apenas para iniciar o pendrive da ISO, pode reativá-lo agora na BIOS (`F10`).

---

## Cenário 4 — Atualização de kernel (`linux-cachyos`) foi interrompida e deixou o boot inconsistente

- **Sintoma:** o computador caiu de energia ou foi desligado no meio de um `pacman -Syu` / `topgrade` enquanto o `mkinitcpio` estava gerando o `initramfs` do `linux-cachyos`, resultando em falha ao montar o rootfs ou kernel ausente em `/boot`.
- **Caminho A (Mais rápido — direto pelo menu do Limine, sem pendrive):**
  1. Ligue o computador e, no menu do **Limine**, selecione **`Arch Linux → Snapshots`**.
  2. Escolha o snapshot **`Ponto de Segurança`** (`pre`) mais recente anterior à atualização interrompida e inicie por ele.
  3. Assim que entrar no desktop, abra o terminal Kitty ou o utilitário **Limine Snapshot Restore** e restaure o snapshot conforme o [Cenário 5](#cenário-5--restaurar-um-snapshot-btrfssnapper-anterior-pelo-sistema-ou-via-iso).
- **Caminho B (Via pendrive da ISO oficial + `arch-chroot`):**
  1. Conecte-se à internet na ISO oficial, siga o **[Procedimento Base](#procedimento-base-como-iniciar-pela-iso-oficial-do-arch-linux-e-entrar-no-arch-chroot)** e entre em `arch-chroot /mnt`.
  2. Reinstale o kernel `linux-cachyos` e regenere toda a cadeia de boot:
     ```bash
     pgrep -a pacman || rm -f /var/lib/pacman/db.lck
     pacman -Syyu --noconfirm linux-cachyos linux-cachyos-headers
     limine-update
     limine-snapper-sync || true
     /usr/local/libexec/nox/nox-limine-integrity --force
     nox-secureboot-verify
     exit
     umount -R /mnt
     reboot
     ```

---

## Cenário 5 — Restaurar um snapshot Btrfs/Snapper anterior (pelo sistema ou via ISO)

O Project Nox mantém snapshots automáticos do subvolume raiz `@` em `/.snapshots` (preservando seus arquivos pessoais em `@home` separados, para que você não perca documentos ao voltar o sistema a um estado anterior).

### Método 5.1 — Restauração assistida pelo menu do Limine (Recomendado)
1. Ao ligar o computador, no menu do **Limine**, desça até **`[-] Arch Linux → Snapshots`** e escolha o snapshot desejado (por exemplo, `Ponto de Segurança`).
2. O sistema iniciará normalmente usando `btrfs-overlayfs` sobre aquele snapshot.
3. Faça login no desktop, abra o terminal Kitty (`Super + Q`) — ou pesquise por **`Limine Snapshot Restore`** via `/tools` no launcher — e execute:
   ```bash
   sudo /usr/local/bin/limine-snapper-restore
   ```
4. O assistente `/usr/local/bin/limine-snapper-restore` exibirá a tabela de snapshots disponíveis (`limine-snapper-list`), pedirá que você informe o ID a restaurar, restaurará o subvolume `@` e o kernel correspondente em `/boot` e executará automaticamente `/usr/local/libexec/nox/nox-limine-integrity --force` para atualizar o hash BLAKE2B e re-assinar os binários EFI com `sbctl`.
5. Reinicie o computador ao concluir.

### Método 5.2 — Restauração manual de `@` via ISO oficial (Caso o sistema nem inicie e houve queda de energia)
Se uma queda de energia interrompeu uma restauração no meio ou você precisa trocar o subvolume `@` diretamente pela ISO oficial:
1. Inicie pelo pendrive da ISO oficial do Arch Linux e identifique suas partições com `lsblk -f` (`ESP_PART="/dev/nvme0n1p1"` e `BTRFS_PART="/dev/nvme0n1p2"`).
2. Monte o topo da árvore Btrfs (`subvolid=5`) em `/mnt/btrfs-top`:
   ```bash
   mkdir -p /mnt/btrfs-top
   mount -o subvolid=5 "$BTRFS_PART" /mnt/btrfs-top
   ```
3. Liste os snapshots disponíveis e seus metadados (`info.xml`):
   ```bash
   ls -la /mnt/btrfs-top/@.snapshots/
   grep -H -E '<(type|date|description)>' /mnt/btrfs-top/@.snapshots/*/info.xml
   ```
4. Substitua `N` abaixo pelo número do snapshot desejado (por exemplo, `1`): mova o `@` atual para um backup `@.broken` e crie um novo subvolume `@` gravável a partir do snapshot `N`:
   ```bash
   SNAP_ID="1"   # Substitua pelo número do snapshot escolhido
   mv /mnt/btrfs-top/@ "/mnt/btrfs-top/@.broken.$(date +%Y%m%d-%H%M%S)"
   btrfs subvolume snapshot "/mnt/btrfs-top/@.snapshots/${SNAP_ID}/snapshot" /mnt/btrfs-top/@
   umount /mnt/btrfs-top
   ```
5. Agora siga os Passos 3 e 4 do **[Procedimento Base](#procedimento-base-como-iniciar-pela-iso-oficial-do-arch-linux-e-entrar-no-arch-chroot)** para montar o novo `@` e `/mnt/boot`, entre em `arch-chroot /mnt` e ressincronize o kernel e o Limine com `/boot`:
   ```bash
   arch-chroot /mnt
   pacman -S --noconfirm linux-cachyos linux-cachyos-headers
   limine-update
   limine-snapper-sync || true
   /usr/local/libexec/nox/nox-limine-integrity --force
   nox-secureboot-verify
   exit
   umount -R /mnt
   reboot
   ```
6. Após confirmar que o sistema iniciou perfeitamente, você pode remover o subvolume antigo `@.broken.*` montando `subvolid=5` e rodando `sudo btrfs subvolume delete /mnt/btrfs-top/@.broken.*`.

---

## Cenário 6 — Secure Boot foi ativado na BIOS antes das assinaturas estarem prontas

- **Sintoma:** você ativou `Secure Boot = Enabled` na BIOS, mas ainda não havia executado `sudo nox-secureboot-enroll --yes-enroll-uefi-keys` ou algum binário em `/boot` não estava assinado, recebendo `Secure Boot Violation`.
- **Como resolver:**
  1. Reinicie, pressione **`Del`** para entrar na BIOS e mude **`Secure Boot`** de volta para **`Disabled`**.
  2. Pressione **`F10`** para salvar e iniciar o Project Nox normalmente.
  3. No terminal Kitty, siga as **Fases A, B e C** do guia **[`docs/SECURE-BOOT-MSI.md`](SECURE-BOOT-MSI.md)** (ou o **Método A** de **[`docs/SECURE-BOOT.md`](SECURE-BOOT.md)**) na ordem exata, ativando o Secure Boot somente depois que `sudo nox-secureboot-verify` retornar `OK`.

---

## Cenário 7 — As chaves cadastradas na NVRAM não coincidem com as chaves do sistema

- **Sintoma:** você reinstalou o sistema (o que gerou um novo par de chaves em `/var/lib/sbctl/keys/`), mas a memória NVRAM da placa-mãe ainda guarda as chaves da instalação anterior. Ao ativar o Secure Boot, a placa-mãe rejeita os binários assinados pela chave nova.
- **Como resolver:**
  1. Entre na BIOS (`Del`), vá em **`Settings → Security → Secure Boot`**.
  2. Mude **`Secure Boot`** para **`Disabled`** e **`Secure Boot Mode`** para **`Custom`**.
  3. Entre em **`Key Management`** e escolha **`Delete all Secure Boot variables`** (para colocar a placa novamente em **`Setup Mode`**).
  4. Pressione **`F10`**, inicie o novo Project Nox e execute no terminal Kitty:
     ```bash
     sudo sbctl status   # Confirme Setup Mode: ✓ Enabled
     sudo nox-secureboot-enroll --yes-enroll-uefi-keys
     sudo nox-secureboot-verify
     ```
  5. Reinicie na BIOS e reative **`Secure Boot = Enabled`**.

---

## Cenário 8 — A BIOS MSI está bloqueando uma imagem EFI específica após ativar `Maximum Security`

- **Sintoma:** após ativar `Secure Boot Preset → Maximum Security` (ou `Image Execution Policy → Deny Execute`), algum utilitário EFI externo ou ferramenta de diagnóstico na partição `/boot` é bloqueado pela BIOS.
- **Como resolver:**
  - **Se o arquivo `.efi` faz parte do seu sistema em `/boot` e você confia nele:** desative o Secure Boot temporariamente na BIOS, inicie o Project Nox e assine o arquivo `.efi` com a sua chave do `sbctl`:
    ```bash
    sudo sbctl sign -s /boot/caminho/do/arquivo.efi
    sudo sbctl verify
    ```
  - **Se o arquivo `.efi` é uma mídia externa temporária (como o pendrive da ISO oficial do Arch Linux):** veja o [Cenário 10](#cenário-10--o-pendrive-da-iso-oficial-do-arch-linux-não-inicia-porque-o-secure-boot-está-ativo).

---

## Cenário 9 — A GPU (Radeon RX 9060 XT) não apresenta imagem após mudança de política de Option ROM

- **Sintoma:** em um PC com processador sem vídeo integrado (**Ryzen 5 7500F**) e GPU dedicada (**Radeon RX 9060 XT**), a política de `Option ROM` foi colocada em `Deny Execute` sem que o certificado `Microsoft Corporation UEFI CA` (`--microsoft`) estivesse inscrito na variável `db`, resultando em tela preta logo ao ligar o computador.
- **Como resolver fisicamente (Reset de CMOS via jumper `JBAT1`):**
  1. Desligue o computador e **retire o cabo de energia da fonte** da tomada.
  2. Aguarde 15 segundos.
  3. Na placa-mãe **MSI PRO B650M-P**, localize o par de pinos **`JBAT1`** (Clear CMOS) e encoste uma chave de fenda metálica conectando os dois pinos por **10 segundos**.
  4. Retire a chave de fenda, reconecte o cabo de energia e ligue o computador.
  5. O reset de CMOS restaura as configurações da BIOS para o padrão de fábrica (`Secure Boot = Disabled`, política padrão), devolvendo imediatamente a imagem da Radeon RX 9060 XT.
  6. Ao entrar no Linux, refaça a inscrição das chaves utilizando o comando padrão `sudo nox-secureboot-enroll --yes-enroll-uefi-keys` (que sempre inclui `--microsoft`).

---

## Cenário 10 — O pendrive da ISO oficial do Arch Linux não inicia porque o Secure Boot está ativo

- **Por que isso acontece:** com o Secure Boot ativo e o quirk `FQ0001` corrigido (`Maximum Security` / `Removable Media = Deny Execute`), a sua placa-mãe MSI bloqueia corretamente qualquer pendrive cujo bootloader EFI não tenha sido assinado pela sua chave privada de `/var/lib/sbctl/keys/`. Como a ISO oficial do Arch Linux não vem assinada pela sua chave privada pessoal, a placa-mãe exibe `Secure Boot Violation` ao tentar dar boot pelo pendrive.
- **Como iniciar a ISO oficial quando precisar fazer manutenção ou reinstalar:**
  1. Reinicie o computador e pressione **`Del`** para entrar na BIOS da MSI.
  2. Vá em **`Settings → Security → Secure Boot`** e mude **`Secure Boot`** de `Enabled` para **`Disabled`**.
     *(Nota: você **não** precisa apagar suas chaves de `Key Management` para isso! Basta mudar a chave geral `Secure Boot` para `Disabled`; suas chaves `PK`, `KEK` e `db` continuam guardadas na NVRAM).*
  3. Pressione **`F10`** para salvar, pressione **`F11`** para abrir o menu de boot e inicie normalmente pelo pendrive da ISO oficial do Arch Linux.
  4. Quando terminar a manutenção (ou se estiver apenas usando a ISO para reparo via `arch-chroot`), basta voltar na BIOS e mudar **`Secure Boot`** novamente para **`Enabled`** — suas chaves continuarão lá!
