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
    def test_dynamic_suffix_and_numid_and_capture(self) -> None:
        cards_txt = (
            "Card #42\n"
            "  Name: alsa_card.usb-XiiSound_Technology_Corporation_Fuxi-H3-01\n"
            "  Profiles:\n"
            "    output:iec958-stereo+input:mono-fallback: Digital\n"
            "  Active Profile: output:analog-stereo+input:mono-fallback\n"
        )
        sources_txt = (
            "Source #1\n"
            "  Name: alsa_input.pci-0000_00_1f.3.analog-stereo\n"
            "  Mute: yes\n"
            "Source #9\n"
            "  Name: alsa_input.usb-XiiSound_Technology_Corporation_Fuxi-H3-01.mono-fallback\n"
            "  Mute: yes\n"
        )
        amixer_txt = (
            "numid=3,iface=MIXER,name='Mic Capture Switch'\n"
            "numid=4,iface=MIXER,name='Mic Capture Switch',index=1\n"
            "numid=14,iface=MIXER,name='PCM Playback Volume',index=1\n"
        )
        with (
            tempfile.NamedTemporaryFile("w", delete=False) as cf,
            tempfile.NamedTemporaryFile("w", delete=False) as sf,
            tempfile.NamedTemporaryFile("w", delete=False) as af,
            tempfile.NamedTemporaryFile("w", delete=False) as stf,
        ):
            cf.write(cards_txt)
            sf.write(sources_txt)
            af.write(amixer_txt)
            cpath, spath, apath, stpath = Path(cf.name), Path(sf.name), Path(af.name), Path(stf.name)
        stpath.unlink(missing_ok=True)
        try:
            res = subprocess.run(
                [
                    "bash",
                    str(REPO / "configs/bin/nox-fuxi-h3-fix"),
                    "--pactl-cards",
                    str(cpath),
                    "--pactl-sources",
                    str(spath),
                    "--amixer-contents",
                    str(apath),
                    "--alsa-cards",
                    "/dev/null",
                    "--state-file",
                    str(stpath),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("Fuxi-H3-01", res.stdout)
            self.assertIn("CHOSEN_PROFILE=output:iec958-stereo+input:mono-fallback", res.stdout)
            self.assertIn("NUMID=14", res.stdout)
            self.assertIn("MIC_SWITCH_NUMIDS=3,4", res.stdout)
            self.assertIn("SOURCE_NAME=alsa_input.usb-XiiSound_Technology_Corporation_Fuxi-H3-01.mono-fallback", res.stdout)
            self.assertIn("SHOULD_UNMUTE_CAPTURE=true", res.stdout)
        finally:
            cpath.unlink(missing_ok=True)
            spath.unlink(missing_ok=True)
            apath.unlink(missing_ok=True)
            stpath.unlink(missing_ok=True)

    def test_preserves_user_intentional_mute_across_hotplug(self) -> None:
        cards_txt = (
            "Card #42\n"
            "  Name: alsa_card.usb-XiiSound_Technology_Corporation_Fuxi-H3-01\n"
            "  Profiles:\n"
            "    output:iec958-stereo+input:mono-fallback: Digital\n"
            "  Active Profile: output:iec958-stereo+input:mono-fallback\n"
        )
        with (
            tempfile.NamedTemporaryFile("w", delete=False) as cf,
            tempfile.NamedTemporaryFile("w", delete=False) as stf,
        ):
            cf.write(cards_txt)
            stf.write("PRESENT=0\nSOURCE=\nUSER_MUTED=1\n")
            cpath, stpath = Path(cf.name), Path(stf.name)
        try:
            res = subprocess.run(
                [
                    "bash",
                    str(REPO / "configs/bin/nox-fuxi-h3-fix"),
                    "--pactl-cards",
                    str(cpath),
                    "--pactl-sources",
                    "/dev/null",
                    "--amixer-contents",
                    "/dev/null",
                    "--alsa-cards",
                    "/dev/null",
                    "--state-file",
                    str(stpath),
                    "--hotplug",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn("SHOULD_UNMUTE_CAPTURE=false", res.stdout)
        finally:
            cpath.unlink(missing_ok=True)
            stpath.unlink(missing_ok=True)

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
    @staticmethod
    def _load_mod():
        loader = importlib.machinery.SourceFileLoader(
            "nox_limine_normalize", str(REPO / "configs/bin/nox-limine-normalize")
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_roundtrip_pre_and_post_normalizes_theme_and_snapshots(self) -> None:
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

  //+Snapshots
  comment: 2 snapshots
  ///2 │ 2026-11-19 14:53:22
  comment: pacman -S foo bar
  ////linux-cachyos
  comment: kernel-id=linux-cachyos
  protocol: linux
  path: boot():/abc123/limine_history/vmlinuz#222
  cmdline: rootflags=subvol=/@.snapshots/2/snapshot
  ///1 │ 2026-11-19 14:53:22
  comment: pre update
  ////linux-cachyos
  comment: kernel-id=linux-cachyos
  protocol: linux
  path: boot():/abc123/limine_history/vmlinuz#111
  cmdline: rootflags=subvol=/@.snapshots/1/snapshot
"""
        mod = self._load_mod()
        with tempfile.TemporaryDirectory() as td:
            esp = Path(td)
            (esp / "nox-limine-wallpaper.png").write_bytes(b"fake-limine-wp")
            meta = {
                1: {"type": "pre", "pre_number": None},
                2: {"type": "post", "pre_number": 1},
            }
            post = mod.transform(sample, "post", esp_dir=esp, snapper_meta=meta)
            self.assertIn("timeout: 5\ndefault_entry: Arch Linux/Project Nox\nremember_last_entry: no\n", post)
            self.assertIn("wallpaper: boot():/nox-limine-wallpaper.png#", post)
            self.assertIn("interface_branding: Project Nox\n", post)
            self.assertIn("  //Project Nox\n", post)
            self.assertNotIn("  //linux-cachyos\n", post)
            self.assertIn("  //Snapshots\n", post)
            self.assertNotIn("//+Snapshots", post)
            self.assertIn("  ///Ponto de Segurança\n", post)
            self.assertIn("  ///Estado Atualizado\n", post)
            self.assertLess(post.index("///Ponto de Segurança"), post.index("///Estado Atualizado"))
            self.assertNotIn("pacman -S", post)
            self.assertNotIn("2026-11-19", post)
            self.assertNotIn("////linux-cachyos", post)

            pre = mod.transform(post, "pre", esp_dir=esp, snapper_meta=meta)
            self.assertIn("  //linux-cachyos\n", pre)
            self.assertNotIn("  //Project Nox\n", pre)
            self.assertIn("  ////linux-cachyos\n", pre)

    def test_snapshot_edge_cases_unpaired_and_empty(self) -> None:
        mod = self._load_mod()
        base_header = "/+Arch Linux\n  //linux-cachyos\n  comment: kernel-id=linux-cachyos\n  //Snapshots\n"
        out_empty = mod.transform(base_header, "post", snapper_meta={})
        self.assertIn("  //Snapshots\n", out_empty)
        self.assertNotIn("Ponto de Segurança", out_empty)

        only_pre = (
            base_header
            + "  ///5 │ 2026-11-19\n  ////linux-cachyos\n  protocol: linux\n  cmdline: rootflags=subvol=/@.snapshots/5/snapshot\n"
        )
        out_pre = mod.transform(only_pre, "post", snapper_meta={5: {"type": "pre", "pre_number": None}})
        self.assertIn("///Ponto de Segurança\n", out_pre)
        self.assertNotIn("Estado Atualizado", out_pre)


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
        for mode in ("dark", "light"):
            term = palette[mode]["terminal"]
            for req in ("foreground", "background", "selection_fg", "selection_bg", "cursor", "cursor_text", "normal", "bright"):
                self.assertIn(req, term)
        session_init = (REPO / "configs/bin/nox-session-init").read_text(encoding="utf-8")
        self.assertNotIn(") >/dev/null 2>&1 &", session_init)
        self.assertIn("noctalia msg wallpaper-get", session_init)
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

        power_toml = tomllib.loads((REPO / "configs/noctalia/nox-power.toml").read_text(encoding="utf-8"))
        for key in ("lock", "screen-off", "lock-and-suspend"):
            self.assertEqual(power_toml["idle"]["behavior"][key]["enabled"], False)
            self.assertEqual(power_toml["idle"]["behavior"][key]["timeout"], 0.0)

        logind_idle = (REPO / "configs/systemd/99-nox-no-idle.conf").read_text(encoding="utf-8")
        self.assertIn("IdleAction=ignore", logind_idle)
        self.assertIn("IdleActionSec=0", logind_idle)

        umbriel_toml = tomllib.loads((REPO / "configs/umbriel/config.toml").read_text(encoding="utf-8"))
        kb_cfg = umbriel_toml["input"]["keyboard"]
        self.assertEqual(kb_cfg["layout"], "us")
        self.assertEqual(kb_cfg["variant"], "intl")
        self.assertEqual(kb_cfg["repeat_rate"], 25)
        self.assertEqual(kb_cfg["repeat_delay"], 600)

        gtk_ini = (REPO / "configs/gtk/settings.ini").read_text(encoding="utf-8")
        self.assertIn("gtk-theme-name=adw-gtk3-dark", gtk_ini)
        self.assertIn("gtk-application-prefer-dark-theme=1", gtk_ini)

        desktop_sh = (REPO / "scripts/50-desktop.sh").read_text(encoding="utf-8")
        self.assertNotIn("  libva-utils\n", desktop_sh)
        for kept in ("mesa", "vulkan-radeon", "vulkan-tools", "mesa-utils", "mpvpaper", "socat", "libva"):
            self.assertIn(f"  {kept}\n", desktop_sh)

        for asset in (
            REPO / "configs/fastfetch/nox-logo.txt",
            REPO / "configs/firefox/userChrome.css",
            REPO / "configs/firefox/userContent.css",
            REPO / "configs/greeter/assets/noctalia.svg",
            REPO / "configs/fonts/outfit-latin.ttf",
            REPO / "configs/fonts/plus-jakarta-sans-latin.ttf",
            REPO / "configs/icons/nox-emblem.png",
            REPO / "configs/icons/nox-lockscreen-emblem.gif",
            REPO / "configs/wallpapers/nox-g5-runtime.webm",
            REPO / "configs/wallpapers/nox-aoc-runtime.webm",
            REPO / "configs/wallpapers/nox-lockscreen.png",
            REPO / "configs/wallpapers/nox-greeter.png",
            REPO / "configs/wallpapers/nox-limine.png",
            REPO / "configs/noctalia/plugins/mpvpaper/plugin.toml",
        ):
            self.assertTrue(asset.is_file(), f"Missing asset: {asset}")


class TestNoctaliaLayout(unittest.TestCase):
    def test_landscape_and_portrait_layout_and_mpvpaper_assignment(self) -> None:
        loader = importlib.machinery.SourceFileLoader(
            "nox_noctalia_layout", str(REPO / "configs/bin/nox-noctalia-layout")
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        outputs = [
            {"name": "DP-2", "model": "Odyssey G5", "width": 2560, "height": 1440},
            {"name": "HDMI-A-1", "model": "24B35HM2", "width": 1920, "height": 1080, "transform": "90"},
        ]
        assigns = mod.build_mpvpaper_assignments(outputs)["assignments"]
        self.assertTrue(assigns["DP-2"].endswith("nox-g5-runtime.webm"))
        self.assertTrue(assigns["HDMI-A-1"].endswith("nox-aoc-runtime.webm"))

        import tomllib
        ls = tomllib.loads(mod.build_lockscreen_widgets_toml(outputs))
        self.assertTrue(ls["lockscreen_widgets"]["enabled"])
        self.assertIn("lockscreen-login-box@DP-2", ls["lockscreen_widgets"]["widget"])
        self.assertIn("lockscreen-login-box@HDMI-A-1", ls["lockscreen_widgets"]["widget"])
        self.assertEqual(ls["lockscreen_widgets"]["widget"]["lockscreen-widget-emblem-HDMI-A-1"]["cx"], 540.0)


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
                    "--session-id",
                    "",
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


class TestTopgradeAndSnapperSession(unittest.TestCase):
    def test_topgrade_configs_and_proton_visibility_contracts(self) -> None:
        import tomllib

        arch_cfg = tomllib.loads((REPO / "configs/topgrade/50-nox-arch.toml").read_text(encoding="utf-8"))
        self.assertEqual(arch_cfg["linux"]["arch_package_manager"], "paru")

        self_cfg = tomllib.loads((REPO / "configs/topgrade/98-disable-self-update.toml").read_text(encoding="utf-8"))
        self.assertEqual(self_cfg["misc"]["no_self_update"], True)

        ctr_cfg = tomllib.loads((REPO / "configs/topgrade/99-disable-containers.toml").read_text(encoding="utf-8"))
        self.assertIn("containers", ctr_cfg["misc"]["disable"])

        desktop_sh = (REPO / "scripts/50-desktop.sh").read_text(encoding="utf-8")
        self.assertIn("  protonplus\n", desktop_sh)
        self.assertIn("  proton-cachyos-slr\n", desktop_sh)
        self.assertIn('nox_aur_install_pkg "topgrade-bin"', desktop_sh)
        self.assertNotIn("  steam\n", desktop_sh)
        self.assertNotIn("  proton-cachyos\n", desktop_sh)

        common_sh = (REPO / "scripts/lib/common.sh").read_text(encoding="utf-8")
        self.assertNotIn("ProtonPlus", common_sh)
        self.assertTrue((REPO / "configs/bin/nox-topgrade").is_file())

    def test_multi_transaction_session_consolidates_onto_anchor_pre(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_file = root / "session.json"
            log_file = root / "snapper.log"
            entries_t1 = [
                {"number": 0, "type": "single", "cleanup": ""},
                {"number": 5, "type": "pre", "cleanup": "number"},
                {"number": 6, "type": "post", "pre-number": 5, "cleanup": "number"},
                {"number": 7, "type": "pre", "cleanup": "number"},
                {"number": 8, "type": "post", "pre-number": 7, "cleanup": "number"},
            ]
            t1_json = root / "t1.json"
            t1_json.write_text(json.dumps({"root": entries_t1}), encoding="utf-8")

            mock_snapper = root / "mock-snapper"
            mock_snapper.write_text(
                "#!/usr/bin/env bash\n"
                f"echo \"$*\" >> '{log_file}'\n"
                "if [[ \"$*\" == *\"create\"* && \"$*\" == *\"--print-number\"* ]]; then\n"
                "  echo 11\n"
                "fi\n",
                encoding="utf-8",
            )
            mock_snapper.chmod(0o755)

            # Txn 1 inside topgrade session: initializes anchor_pre=7 and deletes prior 5,6
            subprocess.run(
                [
                    "python3",
                    str(REPO / "configs/bin/nox-snapper-cleanup"),
                    "--input-json",
                    str(t1_json),
                    "--session-id",
                    "topgrade:4242:100",
                    "--state-file",
                    str(state_file),
                    "--snapper-bin",
                    str(mock_snapper),
                ],
                check=True,
            )
            saved = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(saved["anchor_pre"], 7)
            self.assertEqual(saved["latest_post"], 8)

            # Txn 2 inside SAME topgrade session: deletes old post 8, creates post 11 -> pre 7, deletes 9,10
            entries_t2 = [
                {"number": 0, "type": "single", "cleanup": ""},
                {"number": 7, "type": "pre", "cleanup": "number"},
                {"number": 8, "type": "post", "pre-number": 7, "cleanup": "number"},
                {"number": 9, "type": "pre", "cleanup": "number"},
                {"number": 10, "type": "post", "pre-number": 9, "cleanup": "number"},
            ]
            t2_json = root / "t2.json"
            t2_json.write_text(json.dumps({"root": entries_t2}), encoding="utf-8")
            subprocess.run(
                [
                    "python3",
                    str(REPO / "configs/bin/nox-snapper-cleanup"),
                    "--input-json",
                    str(t2_json),
                    "--session-id",
                    "topgrade:4242:100",
                    "--state-file",
                    str(state_file),
                    "--snapper-bin",
                    str(mock_snapper),
                ],
                check=True,
            )
            saved2 = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(saved2["anchor_pre"], 7)
            self.assertEqual(saved2["latest_post"], 11)
            ops = log_file.read_text(encoding="utf-8").splitlines()
            self.assertIn("--no-dbus -c root delete --sync 5 6", ops[0])
            self.assertIn("--no-dbus -c root delete --sync 8", ops[1])
            self.assertIn("--no-dbus -c root create --type post --pre-number 7 --cleanup-algorithm number", ops[2])
            self.assertIn("--no-dbus -c root delete --sync 9 10", ops[3])

            # Interrupted Txn 3 with unpaired PRE 12 preserves everything cleanly
            entries_t3 = entries_t2 + [{"number": 12, "type": "pre", "cleanup": "number"}]
            t3_json = root / "t3.json"
            t3_json.write_text(json.dumps({"root": entries_t3}), encoding="utf-8")
            res_dry = subprocess.run(
                [
                    "python3",
                    str(REPO / "configs/bin/nox-snapper-cleanup"),
                    "--input-json",
                    str(t3_json),
                    "--session-id",
                    "topgrade:4242:100",
                    "--state-file",
                    str(state_file),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertEqual(json.loads(res_dry.stdout)["action"], "noop")


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
