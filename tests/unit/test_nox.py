"""Unit and contract tests for Nox Archinstall."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


class TestUserConfigurationContract(unittest.TestCase):
    def test_public_config_has_no_disk_or_credentials(self) -> None:
        cfg = json.loads((REPO / "user_configuration.json").read_text(encoding="utf-8"))
        self.assertNotIn("disk_config", cfg)
        self.assertNotIn("auth_config", cfg)
        self.assertNotIn("users", cfg)
        self.assertNotIn("root_enc_password", cfg)
        self.assertNotIn("encryption_password", cfg)
        self.assertEqual(cfg["bootloader_config"]["bootloader"], "Limine")
        self.assertEqual(cfg["archinstall_language"], "English")
        self.assertNotIn("grub-btrfs", cfg["packages"])
        self.assertNotIn("grub", cfg["packages"])
        self.assertEqual(cfg["network_config"]["type"], "nm_iwd")
        self.assertEqual(cfg["locale_config"]["kb_layout"], "us-acentos")
        self.assertEqual(cfg["locale_config"]["sys_lang"], "en_CA.UTF-8")
        self.assertEqual(cfg["timezone"], "America/Sao_Paulo")
        self.assertEqual(cfg["swap"]["enabled"], False)
        self.assertEqual(cfg["kernels"], ["linux-zen"])

    def test_umbriel_default_layout_is_dwindle(self) -> None:
        toml_text = (REPO / "configs/umbriel/config.toml").read_text(encoding="utf-8")
        import tomllib
        parsed = tomllib.loads(toml_text)
        self.assertEqual(parsed["layout"]["mode"], "dwindle")
        self.assertIn("dwindle", parsed["layout"])
        self.assertNotIn("scrolling", parsed["layout"])
        self.assertEqual(parsed["environment"]["LANG"], "en_CA.UTF-8")
        self.assertEqual(parsed["environment"]["LANGUAGE"], "en_CA:en_US:en")
        self.assertEqual(parsed["environment"]["AMD_VULKAN_ICD"], "RADV")
        kb = parsed["keybinds"]
        self.assertIn("kitty", str(kb["Mod+Q"]))
        self.assertIn("luciole", str(kb["Mod+E"]))
        self.assertIn("luciole", str(kb["Ctrl+E"]))
        self.assertIn("window-close", str(kb["Mod+C"]))
        self.assertIn("layout-toggle-split", str(kb["Mod+J"]))
        self.assertNotIn("Mod+Return", kb)
        self.assertNotIn("Mod+K", kb)
        self.assertNotIn("Mod+MouseLeft", kb)
        self.assertNotIn("Mod+MouseRight", kb)
        self.assertTrue((REPO / "configs/sysctl/99-nox-performance.conf").is_file())
        self.assertTrue((REPO / "configs/gamemode/gamemode.ini").is_file())
        self.assertTrue((REPO / "configs/boot-hooks/95-nox-sbctl-fallback").is_file())
        self.assertTrue((REPO / "configs/bin/nox-secureboot-enroll").is_file())
        self.assertTrue((REPO / "configs/bin/nox-secureboot-verify").is_file())
        self.assertTrue((REPO / "docs/KEYBINDS_MIGRATION.md").is_file())

    def test_secureboot_enroll_refuses_non_root_without_confirm(self) -> None:
        if os.geteuid() == 0:
            return
        res = subprocess.run(
            ["bash", str(REPO / "configs/bin/nox-secureboot-enroll")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(res.returncode, 0)


class TestHostSafetyGuard(unittest.TestCase):
    def test_install_blocks_unarmed_non_chroot_execution(self) -> None:
        env = os.environ.copy()
        env.pop("NOX_ALLOW_TARGET_EXEC", None)
        res = subprocess.run(
            ["bash", str(REPO / "install.sh"), "--check-only"],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(res.returncode, 0)

    def test_install_dry_run_succeeds_safely(self) -> None:
        res = subprocess.run(
            ["bash", str(REPO / "install.sh"), "--dry-run"],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(res.returncode, 0, res.stderr)


class TestDisplayProfile(unittest.TestCase):
    def run_profile(self, outputs: list[dict]) -> str:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(outputs, tf)
            tpath = Path(tf.name)
        try:
            res = subprocess.run(
                [
                    "python3",
                    str(REPO / "configs/bin/nox-display-profile"),
                    "--profile",
                    str(REPO / "profiles/hardware.json"),
                    "--input-json",
                    str(tpath),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return res.stdout
        finally:
            tpath.unlink(missing_ok=True)

    def test_physical_dual_monitors(self) -> None:
        out = self.run_profile(
            [
                {"name": "DP-2", "model": "Odyssey G5", "modes": ["2560x1440@165", "2560x1440@60"]},
                {"name": "HDMI-A-1", "model": "24B35HM2", "modes": ["1920x1080@100", "1920x1080@60"]},
            ]
        )
        self.assertIn('xwayland_primary_output = "DP-2"', out)
        self.assertIn('mode = "2560x1440@165"', out)
        self.assertIn('position = [2560, -350]', out)
        self.assertIn('transform = "90"', out)

    def test_secondary_disconnected_or_swapped_order(self) -> None:
        out = self.run_profile(
            [
                {"name": "DP-1", "model": "Samsung Odyssey G5", "modes": ["2560x1440@164.83"]},
            ]
        )
        self.assertIn('xwayland_primary_output = "DP-1"', out)
        self.assertIn('mode = "2560x1440@164.83"', out)
        self.assertNotIn("HDMI-A-1", out)

    def test_vm_virtual_output_fallback(self) -> None:
        out = self.run_profile(
            [
                {"name": "Virtual-1", "model": "QEMU Monitor", "modes": ["1920x1080@60"]},
            ]
        )
        self.assertIn('[output."Virtual-1"]', out)
        self.assertNotIn("DP-2", out)


class TestFuxiH3Fix(unittest.TestCase):
    def test_dynamic_suffix_and_numid(self) -> None:
        cards_txt = (
            "Card #42\n"
            "  Name: alsa_card.usb-XiiSound_Technology_Corporation_Fuxi-H3-01\n"
            "  Profiles:\n"
            "    output:iec958-stereo+input:mono-fallback: Digital\n"
            "  Active Profile: output:analog-stereo+input:mono-fallback\n"
        )
        amixer_txt = (
            "numid=4,iface=MIXER,name='Mic Capture Volume'\n"
            "numid=14,iface=MIXER,name='PCM Playback Volume',index=1\n"
        )
        with tempfile.NamedTemporaryFile("w", delete=False) as cf, tempfile.NamedTemporaryFile("w", delete=False) as af:
            cf.write(cards_txt)
            af.write(amixer_txt)
            cpath, apath = Path(cf.name), Path(af.name)
        try:
            res = subprocess.run(
                [
                    "bash",
                    str(REPO / "configs/bin/nox-fuxi-h3-fix"),
                    "--pactl-cards",
                    str(cpath),
                    "--amixer-contents",
                    str(apath),
                    "--alsa-cards",
                    "/dev/null",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Fuxi-H3-01", res.stdout)
            self.assertIn("CHOSEN_PROFILE=output:iec958-stereo+input:mono-fallback", res.stdout)
            self.assertIn("NUMID=14", res.stdout)
        finally:
            cpath.unlink(missing_ok=True)
            apath.unlink(missing_ok=True)

    def test_absent_headset_skips_cleanly(self) -> None:
        with tempfile.NamedTemporaryFile("w", delete=False) as cf:
            cf.write("Card #1\n  Name: alsa_card.pci-0000_00_1b.0\n")
            cpath = Path(cf.name)
        try:
            res = subprocess.run(
                [
                    "bash",
                    str(REPO / "configs/bin/nox-fuxi-h3-fix"),
                    "--pactl-cards",
                    str(cpath),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("SKIP-HARDWARE", res.stdout)
        finally:
            cpath.unlink(missing_ok=True)


class TestLimineNormalize(unittest.TestCase):
    def test_roundtrip_pre_and_post_preserves_kernel_id_and_snapshots(self) -> None:
        sample = """timeout: 5
default_entry: 2
remember_last_entry: yes
/+Arch Linux
comment: Arch Linux
comment: machine-id=abc123 order-priority=50
  //linux-cachyos
  comment: Kernel version: 7.3.5-1-cachyos
  comment: kernel-id=linux-cachyos
  protocol: linux
  path: boot():/abc123/linux-cachyos/vmlinuz#deadbeef

  //Snapshots
  ///8 | 2026-11-19 00:00:02
  ////linux-cachyos
  comment: kernel-id=linux-cachyos
"""
        loader = importlib.machinery.SourceFileLoader(
            "nox_limine_normalize", str(REPO / "configs/bin/nox-limine-normalize")
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        post = mod.transform(sample, "post")
        self.assertIn("timeout: 5\ndefault_entry: Arch Linux/Project Nox\nremember_last_entry: no\n", post)
        self.assertIn("  //Project Nox\n", post)
        self.assertNotIn("  //linux-cachyos\n", post)
        self.assertIn("  comment: kernel-id=linux-cachyos\n", post)
        self.assertIn("  ////linux-cachyos\n", post)

        pre = mod.transform(post, "pre")
        self.assertIn("  //linux-cachyos\n", pre)
        self.assertNotIn("  //Project Nox\n", pre)


class TestSystemToolsLauncher(unittest.TestCase):
    def test_lists_and_resolves_only_hidden_overrides_without_touching_usr_share(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            sys_dir = root / "sys"
            usr_dir = root / "usr"
            sys_dir.mkdir()
            usr_dir.mkdir()

            (sys_dir / "kitty.desktop").write_text("[Desktop Entry]\nName=kitty\nExec=kitty\n", encoding="utf-8")
            (sys_dir / "qt6ct.desktop").write_text(
                "[Desktop Entry]\nName=Qt6 Settings\nComment=Qt6 Configuration Tool\nExec=qt6ct\nTerminal=false\n",
                encoding="utf-8",
            )
            (sys_dir / "btop.desktop").write_text(
                "[Desktop Entry]\nName=btop++\nComment=Resource monitor\nExec=btop\nTerminal=true\n",
                encoding="utf-8",
            )
            (usr_dir / "qt6ct.desktop").write_text("[Desktop Entry]\nType=Application\nName=Qt6 Settings\nNoDisplay=true\n", encoding="utf-8")
            (usr_dir / "btop.desktop").write_text("[Desktop Entry]\nType=Application\nName=btop++\nNoDisplay=true\n", encoding="utf-8")

            res = subprocess.run(
                [
                    "python3",
                    str(REPO / "configs/bin/nox-system-tools-list"),
                    "--user-dir",
                    str(usr_dir),
                    "--sys-dir",
                    str(sys_dir),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(
                res.stdout.splitlines(),
                ["btop++\tSystem resource monitor", "Qt6 Settings\tQt6 configuration utility"],
            )
            self.assertFalse(any("gtk" in line.lower() for line in res.stdout.splitlines() if "btop++" in line))

            launch = subprocess.run(
                [
                    "python3",
                    str(REPO / "configs/bin/nox-system-tools-launch"),
                    "--user-dir",
                    str(usr_dir),
                    "--sys-dir",
                    str(sys_dir),
                    "--dry-run",
                    "Qt6 Settings\tQt6 configuration utility",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(launch.stdout.strip(), "qt6ct")

    def test_snapshots_stage_resyncs_limine_restore_overlay_and_ownership(self) -> None:
        common_sh = (REPO / "scripts/lib/common.sh").read_text(encoding="utf-8")
        appearance_sh = (REPO / "scripts/53-appearance.sh").read_text(encoding="utf-8")
        snapshots_sh = (REPO / "scripts/60-snapshots.sh").read_text(encoding="utf-8")
        val_sh = (REPO / "scripts/80-validation.sh").read_text(encoding="utf-8")
        self.assertIn("nox_sync_hidden_tech_desktops()", common_sh)
        self.assertIn('install -d -m 0755 -o "$uid" -g "$gid"', common_sh)
        self.assertIn('"${uhome}/.local" "${uhome}/.local/share"', common_sh)
        self.assertIn("nox_sync_hidden_tech_desktops", appearance_sh)
        self.assertIn("nox_sync_hidden_tech_desktops", snapshots_sh)
        self.assertIn("limine-snapper-restore.desktop", val_sh)


class TestObsidianPurplePolish(unittest.TestCase):
    def test_obsidian_purple_assets_and_palette_contract(self) -> None:
        import tomllib

        palette = json.loads((REPO / "configs/noctalia/palettes/ObsidianPurple.json").read_text(encoding="utf-8"))
        self.assertEqual(palette["version"], 2)
        dark = palette["dark"]
        self.assertEqual(dark["surface"], "#090610")
        self.assertEqual(dark["primary"], "#9333ea")
        self.assertIn("normal", dark["terminal"])
        self.assertIn("bright", dark["terminal"])
        self.assertTrue((REPO / "configs/wallpapers/obsidian-purple.png").is_file())
        self.assertTrue((REPO / "configs/firefox/nox-theme.js").is_file())
        self.assertTrue((REPO / "configs/gtk/gtk.css").is_file())

        theme_toml = tomllib.loads((REPO / "configs/noctalia/nox-theme.toml").read_text(encoding="utf-8"))
        self.assertEqual(theme_toml["theme"]["source"], "custom")
        self.assertEqual(theme_toml["theme"]["custom_palette"], "ObsidianPurple")
        self.assertIn("umbriel", theme_toml["theme"]["templates"]["builtin_ids"])

        launcher_toml = tomllib.loads((REPO / "configs/noctalia/nox-launcher.toml").read_text(encoding="utf-8"))
        self.assertEqual(launcher_toml["shell"]["launcher"]["providers"]["calculator"]["global"], False)
        self.assertEqual(launcher_toml["shell"]["launcher"]["providers"]["calculator"]["prefix"], "calc")

        gtk_ini = (REPO / "configs/gtk/settings.ini").read_text(encoding="utf-8")
        self.assertIn("gtk-theme-name=adw-gtk3-dark", gtk_ini)
        self.assertIn("gtk-application-prefer-dark-theme=1", gtk_ini)

        desktop_sh = (REPO / "scripts/50-desktop.sh").read_text(encoding="utf-8")
        for pkg in ("vulkan-tools", "mesa-utils", "libva-utils"):
            self.assertNotIn(f"  {pkg}\n", desktop_sh)
        for kept in ("mesa", "vulkan-radeon", "libva"):
            self.assertIn(f"  {kept}\n", desktop_sh)


class TestSnapperCleanup(unittest.TestCase):
    def run_cleanup(self, entries: list[dict]) -> dict:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump({"root": entries}, tf)
            tpath = Path(tf.name)
        try:
            res = subprocess.run(
                [
                    "python3",
                    str(REPO / "configs/bin/nox-snapper-cleanup"),
                    "--input-json",
                    str(tpath),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(res.stdout)
        finally:
            tpath.unlink(missing_ok=True)

    def test_keeps_latest_pre_post_and_manual(self) -> None:
        entries = [
            {"number": 0, "type": "single", "cleanup": "", "active": True, "default": True},
            {"number": 1, "type": "pre", "cleanup": "number"},
            {"number": 2, "type": "post", "pre-number": 1, "cleanup": "number"},
            {"number": 3, "type": "single", "cleanup": ""},  # manual snapshot preserved
            {"number": 4, "type": "pre", "cleanup": "number"},
            {"number": 5, "type": "post", "pre-number": 4, "cleanup": "number"},
        ]
        out = self.run_cleanup(entries)
        self.assertEqual(out["delete"], [1, 2])

    def test_aborted_unpaired_pre_preserves_previous_pair(self) -> None:
        entries = [
            {"number": 0, "type": "single", "cleanup": ""},
            {"number": 1, "type": "pre", "cleanup": "number"},
            {"number": 2, "type": "post", "pre-number": 1, "cleanup": "number"},
            {"number": 3, "type": "pre", "cleanup": "number"},
        ]
        out = self.run_cleanup(entries)
        self.assertEqual(out["delete"], [])
        self.assertEqual(out["reason"], "unpaired-newer-pre-preserved")


class TestBootstrapVerification(unittest.TestCase):
    def test_rejects_mismatched_sha256(self) -> None:
        res = subprocess.run(
            [
                "bash",
                str(REPO / "bootstrap/nox-bootstrap.sh"),
                "https://example.invalid/payload.tar.gz",
                "0" * 64,
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(res.returncode, 0)
