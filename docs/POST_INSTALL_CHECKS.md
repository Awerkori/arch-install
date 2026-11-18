# Verificações Pós-Instalação em Hardware Físico (PENDENTE-HARDWARE)

Os itens abaixo dependem de periféricos e GPU físicos (Tipo C) e não podem ser homologados integralmente em VM virtualizada (`virtio-gpu` / rede NAT):

1. **GPU AMD (`amdgpu`) e Mesa/RADV/Vulkan:**
   ```bash
   lspci -nnk | grep -A3 -E 'VGA|Display|3D'
   vulkaninfo --summary 2>/dev/null || glxinfo -B 2>/dev/null
   journalctl -k -b --no-pager | grep -Ei 'amdgpu|drm.*error'
   ```

2. **Monitores Samsung Odyssey G5 (`DP-2`, 1440p@165) e AOC (`HDMI-A-1`, 1080p@100 vertical):**
   ```bash
   umbriel outputs
   umbriel workspaces
   # Conferir posicionamento sem sobreposição nem buracos e XWayland primary:
   xrandr --query | grep -E ' connected( primary)? '
   ```

3. **Teclado Aula F75 (`us`/`intl` com dead keys):**
   - Testar no Kitty e no Luciole: `' + e -> é`, `' + c -> ç`, `~ + a -> ã`, `^ + e -> ê`, `" + space -> "`.
   - Diagnosticar duplicação apenas se ocorrer: `sudo libinput debug-events`.

4. **Headset HAVIT Fuxi H3 (`FuxiH3`):**
   ```bash
   pactl list cards | grep -A15 -i fuxi
   amixer -c FuxiH3 contents | grep -A2 "PCM Playback Volume"
   paplay /usr/share/sounds/alsa/Front_Left.wav
   paplay /usr/share/sounds/alsa/Front_Right.wav
   ```

5. **Microfone analógico P2 + HushMic:**
   ```bash
   hushmic status
   hushmic devices --json
   wpctl status
   ```
   Confirmar que a fonte selecionada NÃO é `Monitor of`, `HDMI` ou `Navi`, e que `HushMic` é a fonte padrão.

6. **Caixa de som Bluetooth:**
   ```bash
   systemctl status bluetooth --no-pager
   bluetoothctl
   # parear/conectar dispositivo e validar sink A2DP:
   pactl list sinks short
   ```

7. **Wi-Fi Intel AX210 (`iwlwifi` + `iwd` + regdomain BR):**
   ```bash
   nmtui   # ou nmcli device wifi connect "<SSID>" password "<SENHA>"
   iw reg get
   systemctl --failed
   ethtool -k wlan0 | grep -E 'tcp-segmentation-offload|generic-segmentation-offload|generic-receive-offload'
   ```
   (Se desejar desativar power save na conexão específica: `nmcli connection modify "<CONEXAO>" 802-11-wireless.powersave 2`.)
