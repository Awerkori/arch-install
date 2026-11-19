# Integração Topgrade + Paru + ProtonPlus + Protons (Project Nox)

> Documentação arquitetural e operacional da camada de atualização centralizada e compatibilidade gaming no **Nox Archinstall / Project Nox**.

---

## 1. Instalação do Topgrade

O Topgrade é instalado nativamente pelo estágio `scripts/50-desktop.sh` a partir do pacote AUR **`topgrade-bin`** (compilado de forma não privilegiada via usuário temporário `noxbuild`, sem dependência de toolchain `cargo`/Rust em runtime), pois não há pacote oficial `topgrade` nos repositórios `cachyos*` ou `extra`.

- Binário oficial: `/usr/bin/topgrade`
- Wrapper de concorrência (`flock`): `/usr/local/bin/topgrade` (precede `/usr/bin` no `PATH` e executa `/usr/bin/topgrade` diretamente sem recursão, rejeitando execuções simultâneas que possam misturar transações Snapper)
- Execução esperada: usuário comum (`topgrade`), solicitando `sudo` apenas quando o gerenciador do sistema precisa gravar alterações. Não há serviços ou timers automáticos em segundo plano.

## 2. Por que `containers` está desativado

O arquivo `/etc/skel/.config/topgrade.d/99-disable-containers.toml` (propagado a `~/.config/topgrade.d/`) define:

```toml
[misc]
disable = ["containers"]
```

Isso impede falhas de permissão recorrentes nessa etapa em instalações Arch sem alterar permissões de socket, grupos de usuário, Docker ou Podman caso o usuário os instale depois.

## 3. Por que a autoatualização interna está desativada

O arquivo `/etc/skel/.config/topgrade.d/98-disable-self-update.toml` define:

```toml
[misc]
no_self_update = true
```

Evita que o binário tente baixar releases do GitHub por conta própria (sujeito a erros HTTP 403/rate-limit) e mantém o ciclo de versão sob controle exclusivo do gerenciador de pacotes (`paru`/`pacman`).

## 4. Gerenciador Arch utilizado (`paru`)

O arquivo `/etc/skel/.config/topgrade.d/50-nox-arch.toml` define:

```toml
[linux]
arch_package_manager = "paru"
```

Dessa forma, o Topgrade utiliza exclusivamente o `paru` (pacote oficial `cachyos/paru`) para atualizar pacotes dos repositórios Arch/CachyOS Zen 4 e pacotes AUR em uma única etapa de sistema, sem duplicar chamadas com outro helper.

## 5. Instalação do ProtonPlus

O pacote **`protonplus`** é instalado nativamente via Pacman a partir do repositório **`cachyos`** (`scripts/50-desktop.sh`), sem duplicata Flatpak. Atualizações automáticas em segundo plano e no boot permanecem desativadas por padrão no esquema GSettings (`background-updates = false`, `check-updates-on-launch = false`, `check-updates-on-boot = false`).

## 6. Visibilidade do ProtonPlus no launcher Noctalia

Por definição explícita do projeto, o arquivo `com.vysp3r.ProtonPlus.desktop` **não** recebe `NoDisplay=true` nos overlays do usuário (`scripts/lib/common.sh` e `scripts/80-validation.sh`). A listagem inicial (`All`) do Noctalia exibe exatamente os **4 aplicativos principais**:

1. **Firefox** (`firefox-pure`)
2. **kitty**
3. **Luciole** (`luciole-git`)
4. **ProtonPlus** (`protonplus`)

## 7. Gerenciamento das três variantes Proton

| Variante | Origem / Provedor | Estado após instalação limpa | Como é atualizada |
|---|---|---|---|
| **Proton-CachyOS SLR** | `cachyos/proton-cachyos-slr` (Pacman) | **Instalado nativamente** na base do sistema (sem variant duplicate não-SLR) | `topgrade` → `paru` → `pacman` |
| **GE-Proton** | `GloriousEggroll/proton-ge-custom` via `protonplus` | **Suportado nativamente no ProtonPlus**, mas **não pré-baixado sem launcher** (ver limitação abaixo) | `topgrade` → `protonplus update all` (após launcher instalado) |
| **DWProton** | `dawn-winery/dwproton-mirror` via `protonplus` | **Suportado nativamente no ProtonPlus**, mas **não pré-baixado sem launcher** (ver limitação abaixo) | `topgrade` → `protonplus update all` (após launcher instalado) |

### Limitação comprovada (sem Steam/Heroic pré-instalados)

Em inspeção experimental direta na versão instalada (`protonplus 0.6.8-2`), `protonplus list` retorna `Detected launchers:` vazio e `protonplus install <launcher> ...` exige explicitamente um launcher suportado existente (`Steam`, `Heroic`, `Lutris`, `Bottles` ou `Faugus Launcher`). Conforme diretriz do projeto de não instalar Steam/Heroic nem criar instalações falsas/metadados sintéticos, **apenas o `Proton-CachyOS SLR` fica fisicamente pré-instalado fora da caixa**. Assim que o usuário instalar Steam (ou outro launcher compatível) e instalar `GE-Proton` e `DWProton` pela interface gráfica do **ProtonPlus** ou CLI (`protonplus install steam ...`), o `topgrade` passa a atualizá-los automaticamente via `protonplus update all`.

## 8. Onde os Protons ficam instalados

- **`Proton-CachyOS SLR` (sistema):** `/usr/share/steam/compatibilitytools.d/proton-cachyos-slr/` (gerenciado por Pacman dentro do subvolume raiz `@` protegido pelo Snapper).
- **`GE-Proton` e `DWProton` (usuário):** diretório `compatibilitytools.d/` do launcher escolhido em `$HOME` (por exemplo `~/.local/share/Steam/compatibilitytools.d/`).

## 9. Como o Topgrade chama o ProtonPlus

Quando o executável `protonplus` está presente no `PATH`, a etapa `ProtonPlus` do Topgrade executa nativamente:

```bash
/usr/bin/protonplus update all
```

Sem abrir janelas gráficas, reportando sucesso (`Already up to date` / atualizações aplicadas) ou falhas de rede no resumo final.

## 10. O que NÃO é protegido pelo snapshot Btrfs de raiz (`/`)

A política do Project Nox cria snapshots exclusivamente para o subvolume raiz **`@`** (`/` → `/.snapshots`), sem snapshots automáticos de `/home`:

- **Protegido por PRE/POST:** pacotes do sistema (`linux-cachyos`, bibliotecas, Mesa, `proton-cachyos-slr`, `topgrade-bin`, `protonplus`), `/etc/`, `/usr/`.
- **Fora do snapshot Btrfs da raiz:**
  - Protons baixados pelo usuário na pasta pessoal (`~/.local/share/Steam/compatibilitytools.d/`).
  - Caches/ferramentas de usuário (`~/.npm`, `~/.cargo`, instalações Flatpak por usuário).
  - Artefatos na partição EFI `/boot` (`vmlinuz`, `initramfs`, `limine.conf`), que são sincronizados com segurança via `limine_history` pelo `limine-snapper-sync` e assinados/enrolados por `sbctl`/`limine-enroll-config`.

## 11. Como funciona PRE/POST no Pacman direto

Em transações normais (`sudo pacman -Syu`, `pacman -S ...`):

1. Hook pre-transação (`05-snap-pac-pre.hook`) cria snapshot `PRE`.
2. `pacman` aplica alterações no sistema.
3. Hook pós-transação (`zz-snap-pac-post.hook`) cria snapshot `POST` vinculado (`pre-number = PRE`).
4. Hook final (`zzz-99-nox-snapper-cleanup.hook`) executa `/usr/local/libexec/nox/nox-snapper-cleanup`, removendo pares antigos e preservando apenas o par `PRE+POST` mais recente.
5. `limine-snapper-sync` + `nox-limine-normalize --post` + `limine-enroll-config` atualizam `/boot/limine.conf` com `Ponto de Segurança` (PRE) e `Estado Atualizado` (POST).

## 12–13. Como funciona PRE/POST no Topgrade e em múltiplas transações

Uma única execução do `topgrade` pode disparar **duas ou mais transações Pacman sequenciais** via `paru` (por exemplo: Transação 1 para pacotes dos repositórios oficiais `A → B` e Transação 2 para compilação/instalação AUR `B → C`). Sem coordenação de sessão, o cleanup na Transação 2 apagaria o `PRE` original de `A` e deixaria `PRE = B`.

Para resolver isso de forma determinística e sem `NOPASSWD`:

1. `/usr/local/libexec/nox/nox-snapper-cleanup` percorre a árvore de processos em `/proc` identificando o processo ancestral `/usr/bin/topgrade` (ou `/usr/bin/paru`) por `<pid>:<starttime>`.
2. Na **Transação 1 (`A → B`)**, registra `anchor_pre = PRE_1 (A)` em `/var/lib/nox-archinstall/update-session.json` e remove apenas pares de sessões anteriores.
3. Na **Transação 2 (`B → C`)** dentro da mesma invocação `topgrade`/`paru`:
   - Remove apenas o `POST_1 (B)` intermediário associado ao `anchor_pre`.
   - Cria um novo snapshot `POST_consolidado (C)` nativamente pareado via `--pre-number <anchor_pre>` (`A`).
   - Só após confirmar a criação bem-sucedida de `POST_consolidado`, remove `PRE_2 (B)` e `POST_2 (C)`.
4. Resultado final normal após qualquer execução concluída com alterações: **exatamente 2 snapshots (`anchor_pre` = estado A anterior ao `topgrade`, e `POST_consolidado` = estado C final)**.

## 14. Atualizações incompletas, zero pendências e concorrência

- **Zero atualizações pendentes ou `--dry-run`:** nenhuma transação ALPM é aberta; nenhum snapshot é criado nem removido.
- **Transação interrompida / falha após criação de `PRE`:** `nox-snapper-cleanup` detecta o `PRE` sem par (`unpaired-newer-pre-preserved`) e aborta qualquer remoção destrutiva, mantendo tanto o par íntegro anterior quanto o `PRE` de recuperação acessíveis.
- **Falha em etapa externa (ex.: ProtonPlus) após sucesso do Pacman/Paru:** o par do sistema (`PRE+POST`) já foi persistido com integridade e o Topgrade encerra reportando falha parcial da etapa externa.
- **Execuções simultâneas:** `/usr/local/bin/topgrade` adquire lock exclusivo (`flock -n`) em `${XDG_RUNTIME_DIR:-/tmp}/nox-topgrade-${UID}.lock`, bloqueando sobreposição de sessões sem tocar em `/var/lib/pacman/db.lck`.

## 15–16. Como testar snapshots e efetuar rollback

```bash
# 1. Conferir histórico atual (deve listar apenas o par PRE + POST em estado normal)
snapper -c root list

# 2. Simular inspeção do Topgrade sem modificar o sistema
topgrade --dry-run

# 3. Atualizar sistema e ferramentas interativamente (usuário comum)
topgrade
```

Para efetuar rollback caso uma atualização cause regressão:

1. Reinicie o computador.
2. No menu do **Limine**, navegue até **`Snapshots`**, pressione `Enter` e selecione **`Ponto de Segurança`** (pressione `Enter` para iniciar diretamente no estado `PRE`).
3. Após validar o sistema restaurado no snapshot, execute **`limine-snapper-sync --restore`** (ou via ferramenta `limine-snapper-restore`) como administrador para promover o snapshot restaurado a subvolume ativo `@`, atualize/reassine a configuração caso o kernel tenha mudado e reinicie.

## 17. Validações físicas pendentes (`PENDENTE-HARDWARE`)

- Execução real de `ProtonPlus` para baixar e atualizar **`GE-Proton`** e **`DWProton`** após a instalação de **Steam** (ou **Heroic** / **Lutris** / **Bottles**) pelo usuário final no hardware definitivo.
- Testes de jogos e compatibilidade específica (incluindo verificação de comportamento de anticheat em títulos gacha/HoYoverse no sistema físico).
