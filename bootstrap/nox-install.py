#!/usr/bin/env python3
"""Interactive simplified installer wrapper for Project Nox on the official Arch Linux ISO.

Collects strictly the personal inputs required from the owner (target SSD,
explicit wipe confirmation, username, and password) and generates the exact
Archinstall silent JSON configuration matching the validated Project Nox layout
(GPT + 4 GiB FAT32 /boot + Btrfs compress=zstd with @, @home, @log, @pkg,
@.snapshots; @swap + ZRAM + CachyOS + Limine + Umbriel + Noctalia via target-offline).
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_URL = "https://raw.githubusercontent.com/Awerkori/arch-install/main/user_configuration.json"
LEGACY_RC_TAG = "v1.0.0-rc10"
HOMOLOGATED_ARCHINSTALL_SERIES = "4.5"
REQUIRED_ARCHINSTALL_FLAGS = ("--silent", "--config", "--creds", "--skip-version-check", "--skip-wifi-check")
MIN_DISK_BYTES = 20 * 1024 * 1024 * 1024  # 20 GiB safety floor
ESP_SIZE_MIB = 4096
ESP_START_MIB = 1
BTRFS_START_MIB = ESP_START_MIB + ESP_SIZE_MIB

RESERVED_USERS = {
    "root",
    "daemon",
    "bin",
    "sys",
    "sync",
    "games",
    "man",
    "lp",
    "mail",
    "news",
    "uucp",
    "proxy",
    "www-data",
    "backup",
    "list",
    "irc",
    "gnats",
    "nobody",
    "systemd-network",
    "systemd-resolve",
    "systemd-timesync",
    "systemd-oom",
    "messagebus",
    "dbus",
    "greeter",
    "noxbuild",
}
USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,31}$")


def ensure_interactive_tty() -> None:
    """Ensure stdin reads from the interactive controlling TTY even if invoked via pipe."""
    if sys.stdin.isatty():
        return
    try:
        tty_file = open("/dev/tty", "r", encoding="utf-8")
        sys.stdin = tty_file
    except OSError as exc:
        raise RuntimeError(
            "stdin nao e um terminal interativo e /dev/tty nao esta disponivel. "
            "Baixe o instalador para um arquivo temporario antes de executar com python3."
        ) from exc


def list_candidate_disks() -> list[dict[str, Any]]:
    """Query lsblk and return eligible disks (>= 20 GiB), excluding live archiso media."""
    raw = subprocess.check_output(
        ["lsblk", "-d", "-b", "-J", "-o", "NAME,PATH,SIZE,MODEL,SERIAL,TRAN,TYPE,RM,MOUNTPOINTS"],
        text=True,
    )
    data = json.loads(raw)
    disks: list[dict[str, Any]] = []
    by_id_map: dict[str, str] = {}
    by_id_dir = Path("/dev/disk/by-id")
    if by_id_dir.is_dir():
        for entry in sorted(by_id_dir.iterdir()):
            if entry.name.startswith(("dm-", "wwn-", "nvme-eui.")) or "-part" in entry.name:
                continue
            try:
                resolved = str(entry.resolve())
                by_id_map.setdefault(resolved, str(entry))
            except OSError:
                continue

    for dev in data.get("blockdevices", []):
        if dev.get("type") != "disk":
            continue
        path = str(dev.get("path") or "")
        size = int(dev.get("size") or 0)
        if not path or size < MIN_DISK_BYTES:
            continue
        children_raw = subprocess.run(
            ["lsblk", "-nr", "-o", "MOUNTPOINT", path],
            capture_output=True,
            text=True,
            check=False,
        )
        mounts = sorted({m.strip() for m in children_raw.stdout.splitlines() if m.strip()})
        if any(m.startswith("/run/archiso") for m in mounts):
            continue
        rm_raw = dev.get("rm")
        is_removable = bool(rm_raw) and str(rm_raw).lower() not in {"0", "false"}
        tran = (dev.get("tran") or "disk").strip().lower()
        disks.append(
            {
                "name": str(dev.get("name") or Path(path).name),
                "path": path,
                "size_bytes": size,
                "size_gib": size / (1024**3),
                "model": (dev.get("model") or "Desconhecido").strip(),
                "serial": (dev.get("serial") or "").strip(),
                "tran": tran,
                "removable": is_removable or tran == "usb",
                "mounts": mounts,
                "by_id": by_id_map.get(path, ""),
            }
        )
    return disks


def verify_disk_safe_to_wipe(disk: dict[str, Any]) -> None:
    """Re-verify selected device path, persistent by-id target, and absence of active mounts."""
    disk_path = Path(disk["path"])
    if not disk_path.exists():
        raise RuntimeError(f"Disco selecionado '{disk['path']}' nao esta mais presente.")
    if disk.get("by_id"):
        by_id_path = Path(disk["by_id"])
        if not by_id_path.exists() or str(by_id_path.resolve()) != str(disk_path.resolve()):
            raise RuntimeError(
                f"Identificador persistente '{disk['by_id']}' nao aponta mais para '{disk['path']}'. Abortando."
            )
    mounts_out = subprocess.run(
        ["lsblk", "-nr", "-o", "MOUNTPOINT", str(disk_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    active_mounts = [m.strip() for m in mounts_out.stdout.splitlines() if m.strip()]
    if active_mounts:
        raise RuntimeError(
            f"O disco '{disk['path']}' possui pontos montados ativos ({', '.join(active_mounts)}). "
            "Desmonte-os manualmente antes de prosseguir."
        )


def validate_username(name: str) -> tuple[bool, str]:
    cleaned = name.strip()
    if not cleaned:
        return False, "O nome de usuario nao pode ficar vazio."
    if cleaned in RESERVED_USERS:
        return False, f"O nome '{cleaned}' e reservado pelo sistema."
    if not USERNAME_RE.match(cleaned):
        return (
            False,
            "Use apenas letras minusculas, digitos, '_' ou '-', comecando por letra ou '_' (max. 32 caracteres).",
        )
    return True, cleaned


def build_disk_config(disk_path: str, size_bytes: int, sector_size: int = 512) -> dict[str, Any]:
    """Build deterministic GPT + 4GiB ESP + Btrfs compress=zstd disk_config for the chosen disk."""
    total_mib = size_bytes // (1024 * 1024)
    # Reserve 2 MiB at end for GPT backup header alignment
    btrfs_mib = total_mib - BTRFS_START_MIB - 2
    if btrfs_mib < 16384:
        raise ValueError(f"Disco '{disk_path}' menor que o minimo necessario apos /boot de 4 GiB.")
    return {
        "config_type": "default_layout",
        "btrfs_options": {
            "snapshot_config": {
                "type": "Snapper",
            }
        },
        "device_modifications": [
            {
                "device": disk_path,
                "wipe": True,
                "partitions": [
                    {
                        "btrfs": [],
                        "dev_path": None,
                        "flags": ["boot", "esp"],
                        "fs_type": "fat32",
                        "mount_options": [],
                        "mountpoint": "/boot",
                        "obj_id": "11111111-1111-4111-8111-111111111101",
                        "size": {
                            "sector_size": {"unit": "B", "value": sector_size},
                            "unit": "MiB",
                            "value": ESP_SIZE_MIB,
                        },
                        "start": {
                            "sector_size": {"unit": "B", "value": sector_size},
                            "unit": "MiB",
                            "value": ESP_START_MIB,
                        },
                        "status": "create",
                        "type": "primary",
                    },
                    {
                        "btrfs": [
                            {"mountpoint": "/", "name": "@"},
                            {"mountpoint": "/home", "name": "@home"},
                            {"mountpoint": "/var/log", "name": "@log"},
                            {"mountpoint": "/var/cache/pacman/pkg", "name": "@pkg"},
                            {"mountpoint": "/.snapshots", "name": "@.snapshots"},
                        ],
                        "dev_path": None,
                        "flags": [],
                        "fs_type": "btrfs",
                        "mount_options": ["compress=zstd"],
                        "mountpoint": None,
                        "obj_id": "11111111-1111-4111-8111-111111111102",
                        "size": {
                            "sector_size": {"unit": "B", "value": sector_size},
                            "unit": "MiB",
                            "value": btrfs_mib,
                        },
                        "start": {
                            "sector_size": {"unit": "B", "value": sector_size},
                            "unit": "MiB",
                            "value": BTRFS_START_MIB,
                        },
                        "status": "create",
                        "type": "primary",
                    },
                ],
            }
        ],
    }


def hash_password_sha512(password: str) -> str:
    return subprocess.check_output(
        ["openssl", "passwd", "-6", "-stdin"],
        input=password + "\n",
        text=True,
    ).strip()


def load_base_config(source: str, allow_insecure_http: bool = False) -> dict[str, Any]:
    if source.startswith("http://") and not allow_insecure_http:
        raise ValueError(f"URL insegura recusada (use https://): {source}")
    if source.startswith(("http://", "https://")):
        req = urllib.request.Request(source, headers={"User-Agent": "nox-install/1.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw_text = resp.read().decode("utf-8")
    else:
        raw_text = Path(source).read_text(encoding="utf-8")

    data = json.loads(raw_text)
    if not isinstance(data, dict) or not data.get("custom_commands"):
        raise ValueError("user_configuration.json invalido ou sem 'custom_commands'.")
    for req_key in ("bootloader_config", "locale_config", "network_config"):
        if req_key not in data:
            raise ValueError(f"user_configuration.json incompleto (ausente: '{req_key}').")
    return data


def override_payload_cmd(
    cfg: dict[str, Any],
    payload_url: str | None,
    payload_sha: str | None,
    allow_insecure_http: bool = False,
) -> None:
    if payload_url and payload_url.startswith("http://") and not allow_insecure_http:
        raise ValueError(f"Payload URL HTTP recusada sem --allow-insecure-http: {payload_url}")
    if payload_sha and not re.fullmatch(r"[0-9a-fA-F]{64}", payload_sha):
        raise ValueError(f"SHA-256 de payload invalido: {payload_sha}")
    if not payload_url and not payload_sha:
        return
    cmds = list(cfg.get("custom_commands") or [])
    new_cmds: list[str] = []
    for cmd in cmds:
        updated = cmd
        if payload_url:
            updated = re.sub(r'URL=\\?"[^"]+\\?"', f'URL="{payload_url}"', updated)
            if payload_url.startswith("http://") and allow_insecure_http:
                updated = updated.replace('--proto "=https" ', "")
        if payload_sha:
            updated = re.sub(r'SHA=\\?"[0-9a-fA-F]{64}\\?"', f'SHA="{payload_sha}"', updated)
        new_cmds.append(updated)
    cfg["custom_commands"] = new_cmds


def extract_payload_spec(cfg: dict[str, Any]) -> tuple[str, str]:
    joined = "\n".join(cfg.get("custom_commands") or [])
    m_url = re.search(r'URL="([^"]+)"', joined)
    m_sha = re.search(r'SHA="([0-9a-fA-F]{64})"', joined)
    return (m_url.group(1) if m_url else "", m_sha.group(1) if m_sha else "")


def validate_payload_spec(
    cfg: dict[str, Any],
    allow_insecure_http: bool = False,
    allow_legacy_rc: bool = False,
) -> tuple[str, str]:
    url, sha = extract_payload_spec(cfg)
    if not url or not sha:
        raise ValueError("Nao foi possivel extrair URL/SHA-256 validos do payload em custom_commands.")
    if url.startswith("http://") and not allow_insecure_http:
        raise ValueError(f"Payload deve usar HTTPS: {url}")
    if LEGACY_RC_TAG in url and not allow_legacy_rc:
        raise ValueError(
            f"Configuracao base aponta para o payload antigo '{LEGACY_RC_TAG}' ({url}). "
            "Atualize user_configuration.json antes da publicacao v1.0.0 ou passe --payload-url/--payload-sha256."
        )
    return url, sha


def detect_archinstall_version(allow_untested: bool = False) -> str:
    res = subprocess.run(["archinstall", "--version"], capture_output=True, text=True, check=False)
    combined = (res.stdout + "\n" + res.stderr).strip()
    m = re.search(r"(\d+\.\d+(?:\.\d+)?)", combined)
    if res.returncode != 0 or not m:
        raise RuntimeError(f"archinstall ausente ou versao ilegivel: {combined or res.returncode}")
    ver = m.group(1)
    if not (ver == HOMOLOGATED_ARCHINSTALL_SERIES or ver.startswith(HOMOLOGATED_ARCHINSTALL_SERIES + ".")):
        if not allow_untested:
            raise RuntimeError(
                f"Versao de archinstall '{ver}' nao homologada (homologado especificamente na serie {HOMOLOGATED_ARCHINSTALL_SERIES})."
            )
    help_res = subprocess.run(["archinstall", "--help"], capture_output=True, text=True, check=False)
    help_txt = (help_res.stdout or "") + "\n" + (help_res.stderr or "")
    for flag in REQUIRED_ARCHINSTALL_FLAGS:
        if flag not in help_txt:
            raise RuntimeError(f"Interface CLI do archinstall '{ver}' nao suporta a flag obrigatoria '{flag}'.")
    return ver


def select_tmpfs_dir() -> str:
    """Return a verified in-memory tmpfs directory (/dev/shm, /run, or /tmp) for temporary credentials."""
    mounts: dict[str, str] = {}
    try:
        for line in Path("/proc/mounts").read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if len(parts) >= 3:
                mounts[parts[1]] = parts[2]
    except OSError:
        pass
    for candidate in ("/dev/shm", "/tmp", "/run"):
        if mounts.get(candidate) == "tmpfs" and os.path.isdir(candidate) and os.access(candidate, os.W_OK | os.X_OK):
            return candidate
    raise RuntimeError("Nenhum filesystem temporario em RAM (tmpfs) disponivel para armazenar credenciais temporarias.")


def scrub_persisted_archinstall_credentials() -> None:
    """Ensure archinstall log directories never retain user_credentials.json or world-readable logs."""
    for log_dir in (Path("/var/log/archinstall"), Path("/mnt/var/log/archinstall")):
        if not log_dir.is_dir():
            continue
        try:
            os.chmod(log_dir, 0o700)
        except OSError:
            pass
        for cred_name in ("user_credentials.json", "nox_creds.json", "creds.json"):
            cand = log_dir / cred_name
            if cand.exists():
                try:
                    cand.unlink()
                except OSError:
                    pass


def verify_network_preflight(payload_url: str) -> None:
    for test_url in (payload_url, "https://archlinux.org"):
        req = urllib.request.Request(test_url, method="HEAD", headers={"User-Agent": "nox-install/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=12) as resp:
                if resp.status >= 400:
                    raise RuntimeError(f"Falha HTTP {resp.status} ao verificar {test_url}")
        except urllib.error.HTTPError as exc:
            if exc.code == 405:
                continue
            raise RuntimeError(f"Falha de rede/repositorio em {test_url}: HTTP {exc.code}") from exc
        except Exception as exc:
            raise RuntimeError(f"Sem conectividade ou falha HTTPS ao acessar {test_url}: {exc}") from exc


def build_final_configs(
    base_cfg: dict[str, Any],
    disk: dict[str, Any],
    username: str,
    enc_password: str,
    sector_size: int = 512,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cfg = json.loads(json.dumps(base_cfg))
    cfg.pop("auth_config", None)
    cfg["disk_config"] = build_disk_config(disk["path"], int(disk["size_bytes"]), sector_size=sector_size)
    # Policy: root locked (null), single wheel user whose password also authorizes sudo.
    creds: dict[str, Any] = {
        "root_enc_password": None,
        "users": [
            {
                "enc_password": enc_password,
                "groups": ["wheel"],
                "sudo": True,
                "username": username,
            }
        ],
    }
    return cfg, creds


def _read_disk_sector_size(path: str) -> int:
    try:
        out = subprocess.check_output(["blockdev", "--getss", path], text=True).strip()
        val = int(out)
        return val if val in (512, 4096) else 512
    except Exception:
        return 512


def interactive_main(args: argparse.Namespace) -> int:
    if sys.version_info < (3, 11):
        print("ERRO: Python 3.11+ necessario.", file=sys.stderr)
        return 1

    try:
        ensure_interactive_tty()
    except RuntimeError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    archinstall_ver = "dry-run"
    if not args.dry_run:
        if os.geteuid() != 0:
            print("ERRO: execute o instalador como root na ISO oficial do Arch Linux.", file=sys.stderr)
            return 1
        if not Path("/sys/firmware/efi").is_dir():
            print("ERRO: sistema nao inicializado em modo UEFI.", file=sys.stderr)
            return 1
        if not Path("/run/archiso").exists():
            print("ERRO: este instalador deve ser executado na ISO live oficial do Arch Linux (/run/archiso).", file=sys.stderr)
            return 1
        try:
            archinstall_ver = detect_archinstall_version()
        except RuntimeError as exc:
            print(f"ERRO: {exc}", file=sys.stderr)
            return 1

    try:
        base_cfg = load_base_config(args.config, allow_insecure_http=args.allow_insecure_http)
        override_payload_cmd(
            base_cfg,
            args.payload_url,
            args.payload_sha256,
            allow_insecure_http=args.allow_insecure_http,
        )
        payload_url, payload_sha = validate_payload_spec(
            base_cfg,
            allow_insecure_http=args.allow_insecure_http,
            allow_legacy_rc=args.allow_legacy_rc,
        )
        if not args.dry_run and not args.skip_net_check:
            verify_network_preflight(payload_url)
    except Exception as exc:
        print(f"ERRO DE PRE-VALIDACAO: {exc}", file=sys.stderr)
        return 1

    print("=" * 68)
    print("  PROJECT NOX ARCHINSTALL — Instalacao Guiada Simplificada")
    print("=" * 68)
    print("Configuracoes aplicadas automaticamente:")
    print("  * Particionamento : GPT | /boot 4 GiB FAT32 + Btrfs compress=zstd")
    print("  * Subvolumes      : @ (/), @home, @log, @pkg, @.snapshots, @swap")
    print("  * Kernel & Boot   : linux-cachyos + Limine (Project Nox + sbctl)")
    print("  * Desktop         : Umbriel (dwindle) + Noctalia + Obsidian Purple")
    print("  * Privilegios     : sudo via senha do proprio usuario (root bloqueado)")
    print(f"  * Payload         : {payload_url}")
    print(f"  * Payload SHA-256 : {payload_sha[:16]}...")
    print(f"  * Archinstall     : {archinstall_ver}")
    print("-" * 68)

    disks = list_candidate_disks()
    if not disks:
        print("ERRO: nenhum disco elegivel (>= 20 GiB) encontrado.", file=sys.stderr)
        return 1

    print("\n[1/4] Discos disponiveis:")
    for idx, d in enumerate(disks, 1):
        kind_tag = "USB/REMOVIVEL" if d["removable"] else "INTERNO"
        id_str = f" | ID: {d['by_id']}" if d["by_id"] else ""
        ser_str = f" | Serial: {d['serial']}" if d["serial"] else ""
        mnt_str = f" | MONTADO: {','.join(d['mounts'])}" if d["mounts"] else ""
        print(
            f"  [{idx}] [{kind_tag}] {d['path']} ({d['size_gib']:.1f} GiB) | "
            f"{d['model']} [{d['tran']}]{ser_str}{id_str}{mnt_str}"
        )

    chosen: dict[str, Any] | None = None
    while chosen is None:
        raw_choice = input("\nEscolha o numero do SSD de destino (ou 'q' para cancelar): ").strip()
        if raw_choice.lower() in {"q", "quit", "sair", "exit"}:
            print("Instalacao cancelada pelo usuario antes de modificar qualquer disco.")
            return 130
        if not raw_choice:
            print("Selecao obrigatoria. Nenhum disco e selecionado automaticamente.")
            continue
        if not raw_choice.isdigit():
            print("Selecao invalida. Informe o numero correspondente ao disco desejado.")
            continue
        num = int(raw_choice)
        if not (1 <= num <= len(disks)):
            print(f"Numero fora do intervalo (1..{len(disks)}).")
            continue
        chosen = disks[num - 1]
        if chosen["mounts"]:
            print(
                f"AVISO: '{chosen['path']}' possui particoes montadas ({', '.join(chosen['mounts'])}). "
                "Desmonte antes ou escolha outro disco."
            )
            chosen = None

    print("\n[2/4] CONFIRMACAO DE APAGAMENTO DESTRUTIVO:")
    print(f"  Disco selecionado : {chosen['path']} ({chosen['size_gib']:.1f} GiB)")
    print(f"  Tipo / Barra      : {'USB/REMOVIVEL' if chosen['removable'] else 'INTERNO'} | {chosen['model']} [{chosen['tran']}]")
    if chosen["by_id"]:
        print(f"  Identificador     : {chosen['by_id']}")
    print("  AVISO: TODAS as particoes e dados deste disco serao APAGADOS permanentemente!")
    confirm_name = input(
        f"Digite exatamente '{chosen['name']}' para confirmar a formatacao deste disco: "
    ).strip()
    if confirm_name != chosen["name"]:
        print("Confirmacao nao corresponde ao disco selecionado. Abortando sem modificacoes.")
        return 130

    username = ""
    while not username:
        raw_user = input("\n[3/4] Nome de usuario (minusculas, ex: awerkori): ")
        ok, res = validate_username(raw_user)
        if not ok:
            print(f"Nome invalido: {res}")
            continue
        username = res

    password = ""
    while not password:
        pw1 = getpass.getpass(f"\n[4/4] Senha para '{username}' (tambem usada pelo sudo): ")
        if not pw1:
            print("A senha nao pode ficar vazia.")
            continue
        pw2 = getpass.getpass("Confirme a senha: ")
        if pw1 != pw2:
            print("As senhas nao coincidem. Tente novamente.")
            continue
        password = pw1

    print("\n" + "=" * 68)
    print("  RESUMO FINAL ANTES DE FORMATAR")
    print("=" * 68)
    print(f"  Disco alvo        : {chosen['path']} ({chosen['model']}, {chosen['size_gib']:.1f} GiB)")
    print("  Acao no disco     : APAGAR TUDO e criar GPT (/boot 4 GiB + Btrfs)")
    print("  Compressao Btrfs  : zstd (compress=zstd, @/@home/@log/@pkg/@.snapshots)")
    print(f"  Usuario           : {username} (grupo wheel + sudo)")
    print(f"  Hostname          : {base_cfg.get('hostname', 'Nox-Device-PC')}")
    print("  Senha             : [definida - nao exibida]")
    print("  Conta root        : bloqueada (administracao via sudo)")
    print("=" * 68)
    final_ans = input("Confirmar e iniciar a instalacao agora? [s/N]: ").strip().lower()
    if final_ans not in {"s", "sim", "y", "yes"}:
        del password
        print("Instalacao cancelada pelo usuario antes da formatacao.")
        return 130

    enc_pw = hash_password_sha512(password)
    del password

    try:
        verify_disk_safe_to_wipe(chosen)
    except RuntimeError as exc:
        print(f"ERRO: {exc}", file=sys.stderr)
        return 1

    sector_sz = _read_disk_sector_size(chosen["path"])
    cfg, creds = build_final_configs(base_cfg, chosen, username, enc_pw, sector_size=sector_sz)

    tmp_root = select_tmpfs_dir()
    with tempfile.TemporaryDirectory(prefix="nox-install-", dir=tmp_root) as tmp_dir:
        os.chmod(tmp_dir, 0o700)
        tmp_path = Path(tmp_dir)
        cfg_file = tmp_path / "nox_cfg.json"
        creds_file = tmp_path / "nox_creds.json"
        cfg_file.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        creds_file.write_text(json.dumps(creds, indent=2) + "\n", encoding="utf-8")
        os.chmod(cfg_file, 0o600)
        os.chmod(creds_file, 0o600)

        cmd = [
            "archinstall",
            "--silent",
            "--config",
            str(cfg_file),
            "--creds",
            str(creds_file),
            "--skip-version-check",
            "--skip-wifi-check",
        ]
        if args.dry_run:
            cmd.append("--dry-run")
        print("\nIniciando archinstall com configuracao Project Nox automatica...")
        try:
            proc = subprocess.run(cmd, check=False)
            return proc.returncode
        finally:
            scrub_persisted_archinstall_credentials()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Project Nox simplified Arch ISO installer")
    parser.add_argument("--config", default=DEFAULT_CONFIG_URL, help="Path or URL to user_configuration.json")
    parser.add_argument("--payload-url", default=None, help="Optional override payload URL for lab testing")
    parser.add_argument("--payload-sha256", default=None, help="Optional override payload SHA-256")
    parser.add_argument("--allow-insecure-http", action="store_true", help="Allow http:// URLs for local lab HTTP servers")
    parser.add_argument("--allow-legacy-rc", action="store_true", help="Allow legacy v1.0.0-rc10 payload URL if unchanged")
    parser.add_argument("--skip-net-check", action="store_true", help="Skip preflight HEAD check")
    parser.add_argument("--dry-run", action="store_true", help="Pass --dry-run to archinstall")
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(interactive_main(parse_args()))
