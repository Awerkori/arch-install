# Matriz de Migração de Atalhos: Hyprland + Ambxst -> Umbriel + Noctalia

Origem auditada (somente leitura): `~/.config/hypr/hyprland.lua`, `~/.local/share/ambxst/hyprland.lua` e `hyprctl binds` (170 binds ativos no host, incluindo overrides de precedência).
No Umbriel, definir `[keybinds]` substitui integralmente o conjunto built-in do compositor; por isso não existem atalhos inventados (`Mod+Return` ou `Mod+K` para terminal não são definidos).

## 1. Atalhos Migrados com Equivalente Nativo

| Atalho Hyprland/Ambxst | Origem Efetiva | Ação Original | Equivalente Umbriel / Noctalia |
|---|---|---|---|
| `SUPER + Q` | `hyprland.lua` | `kitty` | `"Mod+Q" = { action = "spawn kitty", repeat = false }` |
| `SUPER + E` | `hyprland.lua` (pós-Ambxst) | `luciole` | `"Mod+E" = { action = "spawn luciole", repeat = false }` |
| `CTRL + E` | `hyprland.lua` (pós-Ambxst) | `luciole` | `"Ctrl+E" = { action = "spawn luciole", repeat = false }` |
| `SUPER` (tap release) | `ambxst` | `ambxst run launcher` | `"Mod" = "spawn noctalia msg panel-toggle launcher"` |
| `SUPER + R` | `hyprland.lua` | `hyprlauncher` | `"Mod+R" = { action = "spawn noctalia msg panel-toggle launcher", repeat = false }` |
| `SUPER + C` | `hyprland.lua` + `ambxst` | `window.close` | `"Mod+C" = { action = "window-close", repeat = false }` |
| `SUPER + M` | `hyprland.lua` | `hyprshutdown` / `exit` | `"Mod+M" = { action = "session-quit", repeat = false }` |
| `SUPER + ESCAPE` | `ambxst` | `ambxst run powermenu` | `"Mod+Escape" = { action = "spawn noctalia msg panel-toggle session", repeat = false }` |
| `SUPER + L` | `ambxst` | `loginctl lock-session` | `"Mod+L" = { action = "spawn noctalia msg session lock", repeat = false }` |
| `SUPER + D` | `ambxst` | `ambxst run dashboard` | `"Mod+D" = { action = "spawn noctalia msg panel-toggle control-center", repeat = false }` |
| `SUPER + V` | `ambxst` (override float) | `ambxst run clipboard` | `"Mod+V" = { action = "spawn noctalia msg panel-toggle clipboard", repeat = false }` |
| `SUPER + PERIOD` | `ambxst` | `ambxst run emoji` | `"Mod+Period" = { action = "spawn noctalia msg panel-toggle launcher /emo", repeat = false }` |
| `SUPER + COMMA` | `ambxst` | `ambxst run wallpapers` | `"Mod+Comma" = { action = "spawn noctalia msg panel-toggle wallpaper", repeat = false }` |
| `SUPER + TAB` | `ambxst` | `ambxst run overview` | `"Mod+Tab" = { action = "overview-toggle", repeat = false }` |
| `SUPER + SHIFT + C` | `ambxst` | `ambxst run config` | `"Mod+Shift+C" = { action = "spawn noctalia msg settings-toggle", repeat = false }` |
| `SUPER + SHIFT + S` | `ambxst` (override special) | `ambxst run screenshot` | `"Mod+Shift+S" = { action = "spawn noctalia msg screenshot-region", repeat = false }` |
| `SUPER + SHIFT + A` | `ambxst` | `ambxst run lens` | `"Mod+Shift+A" = { action = "spawn noctalia msg screenshot-annotate", repeat = false }` |
| `SUPER + SHIFT + B` | `ambxst` | `ambxst toggle bar` | `"Mod+Shift+B" = { action = "spawn noctalia msg bar-toggle", repeat = false }` |
| `SUPER + ALT + B` | `ambxst` | `ambxst reload` | `"Mod+Alt+B" = { action = "spawn sh -c 'umbriel msg config-reload && noctalia msg config-reload'", repeat = false }` |
| `SUPER + SPACE` | `ambxst` | `window.float toggle` | `"Mod+Space" = { action = "window-toggle-floating", repeat = false }` |
| `SUPER + F` | `ambxst` | `window.fullscreen` | `"Mod+F" = { action = "window-toggle-fullscreen", repeat = false }` |
| `SUPER + SHIFT + F` | `ambxst` | `fullscreen maximized` | `"Mod+Shift+F" = { action = "window-toggle-maximize-to-edges", repeat = false }` |
| `SUPER + CTRL + F` | `ambxst` | `fullscreen_state client=2` | `"Mod+Ctrl+F" = { action = "window-toggle-maximize", repeat = false }` |
| `SUPER + J` | `hyprland.lua` | `togglesplit` (dwindle) | `"Mod+J" = { action = "layout-toggle-split", repeat = false }` |
| `SUPER + CTRL + SPACE` | `ambxst` | `center` | `"Mod+Ctrl+Space" = { action = "window-center", repeat = false }` |
| `SUPER + SHIFT + V` | `ambxst` | `toggle_special` | `"Mod+Shift+V" = { action = "scratchpad-toggle", repeat = false }` |
| `SUPER + ALT + V` | `ambxst` | `move special` | `"Mod+Alt+V" = { action = "window-move-to-scratchpad", repeat = false }` |
| `SUPER + Left/Right/Up/Down` (+ `CTRL+h/j/k/l/z/x`) | `ambxst` | foco direcional Dwindle | `"Mod+Left/Right/Up/Down"`, `"Mod+Ctrl+H/J/K/L/Z/X"` -> `window-focus-*` |
| `SUPER + SHIFT + Left/Right/Up/Down` (+ `h/j/k/l`) | `ambxst` | mover janela Dwindle | `"Mod+Shift+Left/Right/Up/Down"`, `"Mod+Shift+H/J/K/L"` -> `window-move-*` |
| `SUPER + ALT + Left/Right/Up/Down` (+ `h/j/k/l`) | `ambxst` | redimensionar janela (`50px`) | `"Mod+Alt+..."` -> `window-modify-primary/secondary-extent +-0.05` |
| `SUPER + 1..9, 0` | `hyprland.lua` + `ambxst` | trocar workspace `1..10` | `"Mod+1".."Mod+0"` -> `workspace-switch 1..10` |
| `SUPER + SHIFT + 1..9, 0` e `SUPER + ALT + 1..9, 0` | `hyprland.lua` + `ambxst` | mover janela p/ workspace `1..10` | `"Mod+Shift+1..0"` e `"Mod+Alt+1..0"` -> `window-move-to-workspace 1..10` |
| `SUPER + Z / X` e `SUPER + SHIFT + Z / X` | `ambxst` | workspace anterior/próximo | `"Mod+Z/Shift+Z"` -> `workspace-previous`; `"Mod+X/Shift+X"` -> `workspace-next` |
| `SUPER + mouse_down / mouse_up` | `ambxst` (override base) | `e-1` / `e+1` | `"Mod+WheelDown"` -> `workspace-previous`; `"Mod+WheelUp"` -> `workspace-next` |
| `SUPER + LMB` / `SUPER + RMB` | `hyprland.lua` + `ambxst` | mover / redimensionar com mouse | Comportamento nativo do Umbriel (`mod_key = "Super"` + arrasto LMB/RMB) |
| `XF86Audio*`, `XF86MonBrightness*` | `hyprland.lua` + `ambxst` | volume 10%, mic mute, media, brilho | `"XF86*"` via `noctalia msg` com `allow_when_locked = true` |

## 2. Conflitos / Precedências Resolvidas

- `SUPER + V`: `hyprland.lua` (`float`) sobrescrito por `ambxst` (`clipboard`); `float` fica em `SUPER + SPACE` (conforme `ambxst`).
- `SUPER + S` e `SUPER + SHIFT + S`: `hyprland.lua` (`special:magic`) sobrescrito por `ambxst` (`screenshot` em `SUPER+SHIFT+S`).
- `SUPER + mouse_down/up`: `hyprland.lua` (`e+1`/`e-1`) invertido por `ambxst` (`e-1`/`e+1`); mantido o comportamento ativo de `ambxst`.
- `SUPER + Q` vs padrão do Umbriel (`window-close`): `SUPER + Q` abre `kitty` e `SUPER + C` fecha janelas.

## 3. Funcionalidades Sem Equivalente Direto (Documentadas)

- `SUPER + P` (`pseudo` do Hyprland Dwindle): Umbriel Dwindle não possui modo pseudo-tiling dedicado (não foi substituído por outro atalho para não inventar combinações).
- `SUPER + A` (`ambxst assistant`): assistentes de IA são explicitamente excluídos do sistema instalado.
- `SUPER + N` (`ambxst notes`), `SUPER + T` (`ambxst tmux`), `SUPER + S` (`ambxst tools`), `SUPER + SHIFT + R` (`ambxst screenrecord`), `SUPER + CTRL + ALT + B` (`ambxst quit`): widgets exclusivos do Ambxst sem equivalente nativo built-in equivalente no Noctalia base.
- `SUPER + ALT + SPACE`, `SUPER + SHIFT + SPACE`, `SUPER + CTRL + ALT + Arrows/1..0`: eram no-ops condicionados a `layout == "scrolling"` no `ambxst/hyprland.lua`; inativos no layout padrão Dwindle.
- `switch:Lid Switch`: evento exclusivo de notebook (host é desktop sem tampa).
