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
4. Entre no chroot e repare o kernel/initramfs/GRUB:
   ```bash
   arch-chroot /mnt
   pacman -S --noconfirm linux-cachyos linux-cachyos-headers
   mkinitcpio -P
   grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=GRUB
   grub-mkconfig -o /boot/grub/grub.cfg
   exit
   umount -R /mnt
   reboot
   ```

## 3. Rollback de snapshot Btrfs (preservando `/home` e coerência com `/boot`)
- **Importante:** A ESP (`/boot`, FAT32) fica fora dos snapshots Btrfs do `root`. Se a transação revertida atualizou o kernel `linux-cachyos`, após reverter `@` para o snapshot `PRE` (ou bootar pelo snapshot no GRUB), reinstale/regenere o kernel correspondente antes do reboot definitivo:
  1. Liste os snapshots existentes: `sudo snapper -c root list`
  2. Monte o topo do Btrfs (`subvolid=5`) em `/mnt/btrfs-top`:
     ```bash
     ROOT_DEV=$(findmnt -no SOURCE / | sed 's/\[.*//')
     sudo mkdir -p /mnt/btrfs-top
     sudo mount -o subvolid=5 "$ROOT_DEV" /mnt/btrfs-top
     ```
  3. Faça rollback do subvolume `@` preservando `@home` intacto (substitua `N` pelo ID do snapshot `PRE`):
     ```bash
     sudo mv /mnt/btrfs-top/@ /mnt/btrfs-top/@.broken.$(date +%Y%m%d-%H%M%S)
     sudo btrfs subvolume snapshot /mnt/btrfs-top/@.snapshots/N/snapshot /mnt/btrfs-top/@
     ```
  4. Se o kernel tiver mudado entre o `PRE` e o estado quebrado, reentre via `arch-chroot` no novo `@` (com `/boot` montado) e execute `pacman -S --noconfirm linux-cachyos linux-cachyos-headers` ou `mkinitcpio -P && grub-mkconfig -o /boot/grub/grub.cfg` antes de reiniciar.
  5. Após bootar normalmente no sistema restaurado e validar, remova o `@.broken.*` antigo com `sudo btrfs subvolume delete /mnt/btrfs-top/@.broken.*`.
