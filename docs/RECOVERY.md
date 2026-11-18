# Guia de Recuperação (ISO Oficial + Chroot + Snapshots Btrfs)

## 1. Retomar instalação interrompida antes do reboot
Se o `archinstall` ou alguma etapa de `custom_commands` falhar antes de reiniciar:
1. Consulte o log em `/mnt/var/log/nox-archinstall/install.log` e `/mnt/var/lib/nox-archinstall/status.json`.
2. **Não formate nem reparticionamento o disco.**
3. Entre no alvo e retome a partir das etapas pendentes:
   ```bash
   arch-chroot /mnt /var/lib/nox-archinstall/payload/install.sh --stage target-offline --resume
   ```

## 2. Recuperar boot pela ISO oficial do Arch Linux
Caso o sistema não inicialize após uma falha de atualização (lembrando que apenas `linux-cachyos` permanece instalado):
1. Inicie pelo pendrive com a ISO oficial do Arch Linux e conecte a rede (`iwctl`).
2. Identifique as partições do seu SSD sem formatar nada:
   ```bash
   lsblk -f
   ```
3. Monte os subvolumes Btrfs e a ESP (`/boot`) exatamente como no layout instalado (substitua `/dev/nvme0n1p2` e `/dev/nvme0n1p1` pelos dispositivos reais conferidos):
   ```bash
   mount -o subvol=@ /dev/nvme0n1p2 /mnt
   mount -o subvol=@home /dev/nvme0n1p2 /mnt/home
   mount -o subvol=@log /dev/nvme0n1p2 /mnt/var/log
   mount -o subvol=@pkg /dev/nvme0n1p2 /mnt/var/cache/pacman/pkg
   mount -o subvol=@.snapshots /dev/nvme0n1p2 /mnt/.snapshots
   mount /dev/nvme0n1p1 /mnt/boot
   ```
4. Entre no chroot e repare o kernel/initramfs/Limine/Secure Boot:
   ```bash
   arch-chroot /mnt
   pacman -S --noconfirm linux-cachyos linux-cachyos-headers
   limine-install --fallback
   limine-update
   limine-snapper-sync
   limine-enroll-config
   /etc/boot/hooks/post.d/95-nox-sbctl-fallback
   nox-secureboot-verify
   exit
   umount -R /mnt
   reboot
   ```

## 3. Rollback de snapshot Btrfs (preservando `/home`, chaves `sbctl` e coerência com `/boot`)
- **Importante:** As chaves privadas do Secure Boot em `/var/lib/sbctl/keys/` acompanham o subvolume `@` (e jamais vão para o GitHub). Ao realizar rollback de `@`, re-sincronize a ESP e o hash inscrito no Limine antes de reiniciar com Secure Boot ativo:
  1. Pelo Limine, escolha a entrada de snapshot desejado em `Snapshots` e, após iniciar, execute `sudo limine-snapper-restore` (método configurado: `RESTORE_METHOD=replace`) e reinicie (`limine-enroll-config` e o hook de fallback re-assinam automaticamente).
  2. Ou manualmente via `subvolid=5` (preservando `@home` intacto; substitua `N` pelo ID do snapshot `PRE`):
     ```bash
     ROOT_DEV=$(findmnt -no SOURCE / | sed 's/\[.*//')
     sudo mkdir -p /mnt/btrfs-top
     sudo mount -o subvolid=5 "$ROOT_DEV" /mnt/btrfs-top
     sudo mv /mnt/btrfs-top/@ /mnt/btrfs-top/@.broken.$(date +%Y%m%d-%H%M%S)
     sudo btrfs subvolume snapshot /mnt/btrfs-top/@.snapshots/N/snapshot /mnt/btrfs-top/@
     ```
  3. Se o kernel tiver mudado entre o `PRE` e o estado quebrado, reentre via `arch-chroot` no novo `@` (com `/boot` montado) e execute `pacman -S --noconfirm linux-cachyos linux-cachyos-headers && limine-update && limine-snapper-sync && limine-enroll-config && /etc/boot/hooks/post.d/95-nox-sbctl-fallback` antes de reiniciar.
  4. Após bootar normalmente no sistema restaurado e validar, remova o `@.broken.*` antigo com `sudo btrfs subvolume delete /mnt/btrfs-top/@.broken.*`.
