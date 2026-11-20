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
        # List AOC first to verify EDID model matching beats enumeration order and sets G5 (DP-1) as primary
        out = self.run_profile(
            [
                {"name": "HDMI-A-1", "make": "AOC", "model": "24B35", "modes": ["1920x1080@100", "1920x1080@60"]},
                {"name": "DP-1", "make": "Samsung", "model": "Odyssey G5", "modes": ["2560x1440@165", "2560x1440@60"]},
            ]
        )
        self.assertIn('xwayland_primary_output = "DP-1"', out)
        self.assertIn('mode = "2560x1440@165"', out)
        self.assertIn('position = [0, 0]', out)
        self.assertIn('position = [2560, -350]', out)
        self.assertIn('transform = "90"', out)

    def test_sysfs_edid_identification_matches_g5_and_aoc(self) -> None:
        loader = importlib.machinery.SourceFileLoader(
            "nox_display_profile", str(REPO / "configs/bin/nox-display-profile")
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        def make_edid(name_txt: str) -> bytes:
            buf = bytearray(128)
            blk = b"\x00\x00\x00\xfc\x00" + name_txt.encode("ascii")[:13].ljust(13, b"\n")
            buf[54:72] = blk
            return bytes(buf)

        with tempfile.TemporaryDirectory() as td:
            drm = Path(td)
            for card_conn, mode, title in [
                ("card0-HDMI-A-1", "1920x1080", "24B35HM2"),
                ("card0-DP-1", "2560x1440", "Odyssey G5"),
            ]:
                d = drm / card_conn
                d.mkdir(parents=True)
                (d / "status").write_text("connected\n", encoding="utf-8")
                (d / "modes").write_text(mode + "\n", encoding="utf-8")
                (d / "edid").write_bytes(make_edid(title))
            outs = mod.load_outputs_from_sysfs(drm)
            cfg = json.loads((REPO / "profiles/hardware.json").read_text(encoding="utf-8"))
            self.assertEqual(cfg["displays"]["primary"]["preferred_connectors"][0], "DP-1")
            rendered = mod.render_outputs_toml(outs, cfg)
            self.assertIn('xwayland_primary_output = "DP-1"', rendered)
            self.assertIn('[output."HDMI-A-1"]', rendered)
            self.assertIn('transform = "90"', rendered)

    def test_secondary_disconnected_or_swapped_order(self) -> None:
        out = self.run_profile(
            [
                {"name": "DP-2", "model": "Samsung Odyssey G5", "modes": ["2560x1440@164.83"]},
            ]
        )
        self.assertIn('xwayland_primary_output = "DP-2"', out)
        self.assertIn('mode = "2560x1440@164.83"', out)
        self.assertNotIn("HDMI-A-1", out)

    def test_vm_virtual_output_fallback(self) -> None:
        out = self.run_profile(
            [
                {"name": "Virtual-1", "model": "QEMU Monitor", "modes": ["1920x1080@60"]},
            ]
        )
        self.assertIn('[output."Virtual-1"]', out)
        self.assertNotIn("DP-1", out)
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
            {"name": "HDMI-A-1", "make": "AOC", "model": "24B35", "width": 1920, "height": 1080},
            {"name": "DP-1", "make": "Samsung", "model": "Odyssey G5", "width": 2560, "height": 1440},
        ]
        assigns = mod.build_mpvpaper_assignments(outputs)["assignments"]
        self.assertTrue(assigns["DP-1"].endswith("nox-g5-runtime.webm"))
        self.assertTrue(assigns["HDMI-A-1"].endswith("nox-aoc-runtime.webm"))

        import tomllib
        ls = tomllib.loads(mod.build_lockscreen_widgets_toml(outputs))
        self.assertTrue(ls["lockscreen_widgets"]["enabled"])
        self.assertIn("lockscreen-login-box@DP-1", ls["lockscreen_widgets"]["widget"])
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


class TestVisualPolishDefinitiva(unittest.TestCase):
    def test_greeter_and_lockscreen_unification_contracts(self) -> None:
        import tomllib

        greeter = tomllib.loads((REPO / "configs/greeter/greeter.toml").read_text(encoding="utf-8"))
        sync_cfg = tomllib.loads((REPO / "configs/greeter/sync.toml").read_text(encoding="utf-8"))
        theme_cfg = tomllib.loads((REPO / "configs/noctalia/nox-theme.toml").read_text(encoding="utf-8"))
        self.assertTrue(greeter["appearance"]["hide_logo"])
        self.assertEqual(greeter["appearance"]["corner_radius_scale"], 1.05)
        self.assertEqual(sync_cfg["appearance"]["corner_radius_scale"], 1.05)
        self.assertEqual(greeter["appearance"]["palette"]["outline"], "#5b21b6")
        self.assertEqual(sync_cfg["appearance"]["palette"]["outline"], "#5b21b6")
        self.assertIn("shadow", greeter["appearance"]["palette"])
        self.assertIn("shadow", sync_cfg["appearance"]["palette"])
        self.assertEqual(sync_cfg["appearance"]["scheme"], "Synced")
        self.assertEqual(greeter["appearance"]["wallpaper"]["tint"], 0.0)
        self.assertEqual(greeter["appearance"]["wallpaper"]["blur"], 0.0)
        self.assertEqual(theme_cfg["lockscreen"]["blur_intensity"], 0.0)
        self.assertEqual(theme_cfg["lockscreen"]["tint_intensity"], 0.0)
        self.assertNotIn("avatar_path", theme_cfg["shell"])
        self.assertTrue(theme_cfg["plugin_settings"]["noctalia/mpvpaper"]["dual_sync"])
        actions = {a["action"]: a for a in theme_cfg["shell"]["session"]["actions"]}
        self.assertEqual(actions["shutdown"]["variant"], "outline")
        self.assertEqual(actions["lock_and_suspend"]["variant"], "outline")
        self.assertTrue(greeter["appearance"]["wallpaper"]["path"].endswith("nox-greeter.png"))

        loader = importlib.machinery.SourceFileLoader(
            "nox_noctalia_layout", str(REPO / "configs/bin/nox-noctalia-layout")
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ls = tomllib.loads(
            mod.build_lockscreen_widgets_toml(
                [{"name": "DP-1", "model": "Odyssey G5", "width": 2560, "height": 1440}]
            )
        )
        emblem = ls["lockscreen_widgets"]["widget"]["lockscreen-widget-emblem-DP-1"]
        date_w = ls["lockscreen_widgets"]["widget"]["lockscreen-widget-date-DP-1"]
        login_w = ls["lockscreen_widgets"]["widget"]["lockscreen-login-box@DP-1"]
        self.assertEqual(emblem["box_width"], 160.0)
        self.assertEqual(emblem["box_height"], 160.0)
        self.assertTrue(emblem["settings"]["image_path"].endswith("nox-lockscreen-emblem.gif"))
        self.assertEqual(date_w["type"], "clock")
        self.assertFalse(login_w["settings"]["show_unlock_hint"])
        self.assertTrue(login_w["settings"]["show_session_buttons"])
        self.assertNotIn("background_padding", login_w["settings"])

    def test_dual_monitor_shared_trajectory_and_ipc_sync_contracts(self) -> None:
        import math
        import tomllib

        loader = importlib.machinery.SourceFileLoader(
            "generate_nox_visuals", str(REPO / "tools/generate_nox_visuals.py")
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec and spec.loader
        gen_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(gen_mod)

        self.assertIsNone(gen_mod._compute_dual_sweep_global(0.02))
        self.assertIsNone(gen_mod._compute_dual_sweep_global(0.85))
        xs = [gen_mod._compute_dual_sweep_global(p)[0] for p in [i / 40.0 for i in range(4, 30)]]
        self.assertTrue(all(xs[i] < xs[i + 1] for i in range(len(xs) - 1)), "Dual sweep must move forward monotonically")
        self.assertLess(xs[0], 0.0)
        self.assertGreater(xs[-1], 3640.0)

        # Verify bezel continuity formula at x_global = 2560 across y in [0, 1440]
        tilt = math.tan(math.radians(-20.0))
        bx_g5 = 2560.0 + (0.0 * tilt) - 0.0
        bx_aoc = 2560.0 + (-350.0 * tilt) - 2560.0
        # At y_virtual = 720 -> y_g5 = 720, y_aoc = 720 - (-350) = 1070
        x_g5_at_y720 = bx_g5 + 720.0 * tilt
        x_aoc_at_y720 = bx_aoc + 1070.0 * tilt
        self.assertAlmostEqual(x_g5_at_y720 - 2560.0, x_aoc_at_y720, places=6)

        plug = tomllib.loads((REPO / "configs/noctalia/plugins/mpvpaper/plugin.toml").read_text(encoding="utf-8"))
        dual_settings = [s for s in plug["setting"] if s["key"] == "dual_sync"]
        self.assertEqual(len(dual_settings), 1)
        self.assertTrue(dual_settings[0]["default"])

        lua = (REPO / "configs/noctalia/plugins/mpvpaper/mpvpaper_service.luau").read_text(encoding="utf-8")
        for needle in ("dualSyncEnabled", "orderedDualConnectors", "syncPairPhase", "resetDualPairZero", "DUAL_CYCLE_SECONDS = 14.0"):
            self.assertIn(needle, lua)

    def test_nox_fastfetch_panel_alignment_and_sections(self) -> None:
        loader = importlib.machinery.SourceFileLoader(
            "nox_fastfetch", str(REPO / "configs/bin/nox-fastfetch")
        )
        spec = importlib.util.spec_from_loader(loader.name, loader)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        sample_raw = [
            "\x1b[m\x1b[?7lawerkori@nox-arch",
            "-----------------",
            "✦ SYSTEM",
            "\x1b[1m├─ OS        \x1b[38;2;168;85;247m│ \x1b[m\x1b[13G\x1b[38;2;245;242;255mArch Linux x86_64",
            "├─ Host      │ \x1b[13GKVM/QEMU Standard PC",
            "├─ Kernel    │ \x1b[13G6.14.0-cachyos",
            "└─ Packages  │ \x1b[13G742 (pacman)",
            "✦ SESSION",
            "├─ DE/WM     │ \x1b[13GUmbriel (Wayland)",
            "└─ Terminal  │ \x1b[13Gkitty 0.41.0",
            "✦ HARDWARE",
            "├─ CPU       │ \x1b[13GAMD Ryzen 9 7950X",
            "└─ Memory    │ \x1b[13G1.24 GiB / 7.75 GiB (\x1b[32m16%\x1b[m)",
            "✦ DISPLAY & STORAGE",
            "├─ Display   │ \x1b[13G1280x800 in 14\" [External]",
            "└─ Disk (/)  │ \x1b[13G8.4 GiB / 60.0 GiB (\x1b[32m14%\x1b[m) - btrfs",
            "● ● ● ● ● ● ● ●",
            "\x1b[?7h",
        ]
        parsed = mod.parse_fastfetch_lines(sample_raw)
        self.assertEqual([s["title"] for s in parsed["sections"]], list(mod.EXPECTED_SECTIONS))
        logo_lines = (REPO / "configs/fastfetch/nox-logo.txt").read_text(encoding="utf-8").splitlines()
        for cols in (120, 90, 62):
            rendered = mod.render_dashboard(parsed, logo_lines, cols)
            self.assertNotIn("\x1b[13G", rendered)
            self.assertNotIn("\x1b[?7l", rendered)
            plain_lines = [mod.strip_ansi(l) for l in rendered.splitlines()]
            sep_cols = {l.find("│") for l in plain_lines if "├─" in l or "└─" in l}
            self.assertEqual(len(sep_cols), 1, f"Misaligned │ separators at cols={cols}: {sep_cols}")
            border_widths = {
                mod.vis_len(l[l.find("╭") :]) for l in plain_lines if "╭─ ✦ " in l
            } | {
                mod.vis_len(l[l.find("╰") :]) for l in plain_lines if "╰─" in l
            }
            self.assertEqual(len(border_widths), 1, f"Mismatched border widths at cols={cols}: {border_widths}")


class TestCorrectiveAuditAdditions(unittest.TestCase):
    def test_nox_install_builds_btrfs_and_locked_root_equivalently(self) -> None:
        import importlib.util

        spec = importlib.util.spec_from_file_location("nox_install", REPO / "bootstrap/nox-install.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        self.assertFalse(mod.validate_username("root")[0])
        self.assertFalse(mod.validate_username("BadUser")[0])
        self.assertTrue(mod.validate_username("awerkori")[0])

        base_cfg = json.loads((REPO / "user_configuration.json").read_text(encoding="utf-8"))
        disk = {"name": "nvme0n1", "path": "/dev/nvme0n1", "size_bytes": 1000 * 1024**3}
        cfg, creds = mod.build_final_configs(base_cfg, disk, "awerkori", "$6$salt$hash", sector_size=512)

        self.assertNotIn("auth_config", cfg)
        self.assertIsNone(creds["root_enc_password"])
        self.assertEqual(len(creds["users"]), 1)
        self.assertEqual(creds["users"][0]["username"], "awerkori")
        self.assertTrue(creds["users"][0]["sudo"])
        self.assertEqual(creds["users"][0]["groups"], ["wheel"])

        dc = cfg["disk_config"]
        self.assertEqual(dc["btrfs_options"]["snapshot_config"]["type"], "Snapper")
        parts = dc["device_modifications"][0]["partitions"]
        self.assertEqual(parts[0]["fs_type"], "fat32")
        self.assertEqual(parts[0]["size"]["value"], 4096)
        self.assertEqual(parts[1]["fs_type"], "btrfs")
        self.assertEqual(parts[1]["mount_options"], ["compress=zstd"])
        subvols = [(s["name"], s["mountpoint"]) for s in parts[1]["btrfs"]]
        self.assertEqual(
            subvols,
            [
                ("@", "/"),
                ("@home", "/home"),
                ("@log", "/var/log"),
                ("@pkg", "/var/cache/pacman/pkg"),
                ("@.snapshots", "/.snapshots"),
            ],
        )

    def test_limine_interrupted_restore_guards_present(self) -> None:
        for rel in (
            "configs/bin/nox-limine-integrity",
            "configs/bin/nox-limine-snapper-restore",
            "configs/systemd/nox-limine-integrity-shutdown.service",
        ):
            self.assertTrue((REPO / rel).is_file(), f"Missing {rel}")
        pre_hook = (REPO / "configs/boot-hooks/05-nox-limine-naming-pre").read_text(encoding="utf-8")
        fb_hook = (REPO / "configs/boot-hooks/95-nox-sbctl-fallback").read_text(encoding="utf-8")
        k_script = (REPO / "scripts/20-cachyos-kernel.sh").read_text(encoding="utf-8")
        self.assertIn("/run/nox-limine-tx.dirty", pre_hook)
        self.assertIn("/run/nox-limine-tx.dirty", fb_hook)
        self.assertIn("nox-limine-integrity-shutdown.service", k_script)
        self.assertIn("/usr/local/bin/limine-snapper-restore", k_script)

        # Ensure P1/P2/P4/P5 corrective invariants remain intact
        nox_inst = (REPO / "bootstrap/nox-install.py").read_text(encoding="utf-8")
        self.assertIn("ensure_interactive_tty", nox_inst)
        self.assertIn("verify_disk_safe_to_wipe", nox_inst)
        self.assertIn("validate_payload_spec", nox_inst)
        self.assertIn('HOMOLOGATED_ARCHINSTALL_SERIES = "4.5"', nox_inst)
        self.assertIn("select_tmpfs_dir", nox_inst)
        self.assertIn("scrub_persisted_archinstall_credentials", nox_inst)
        repo_stage = (REPO / "scripts/10-cachyos-repos.sh").read_text(encoding="utf-8")
        self.assertNotIn("pacman -Sy --noconfirm", repo_stage)
        desktop_stage = (REPO / "scripts/50-desktop.sh").read_text(encoding="utf-8")
        self.assertIn("nox_log_missing_lib_diagnostics", desktop_stage)
        self.assertIn("pacman -Syyu --noconfirm", desktop_stage)
        self.assertNotIn("_nox_lagging", desktop_stage)
        limine_integ = (REPO / "configs/bin/nox-limine-integrity").read_text(encoding="utf-8")
        self.assertIn('CONF_B2="$(b2sum "$CONF"', limine_integ)
        self.assertIn('grep -qaiF "$CONF_B2" "$LIMINE_EFI"', limine_integ)
        mem_stage = (REPO / "scripts/70-memory.sh").read_text(encoding="utf-8")
        self.assertNotIn("nodatacow", mem_stage)
        wrap = (REPO / "configs/bin/nox-limine-snapper-restore").read_text(encoding="utf-8")
        self.assertIn("/usr/bin/limine-snapper-list", wrap)


class TestTrustChainHardening(unittest.TestCase):
    @staticmethod
    def _load_nox_install():
        spec = importlib.util.spec_from_file_location("nox_install", REPO / "bootstrap/nox-install.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_stage1_launcher_rejects_tampered_bootstrap_and_http(self) -> None:
        import hashlib

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fake_boot = tmp / "nox-install.py"
            fake_boot.write_text("import sys\nprint('EXECUTED_UNVERIFIED')\nsys.exit(0)\n", encoding="utf-8")
            wrong_sha = "a" * 64

            # 1. Override without NOX_ALLOW_CUSTOM_BOOTSTRAP=1 must fail
            env_no_flag = os.environ.copy()
            env_no_flag["NOX_BOOTSTRAP_URL"] = "https://example.invalid/nox-install.py"
            res_no_flag = subprocess.run(
                ["sh", str(REPO / "i")],
                env=env_no_flag,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_no_flag.returncode, 2)
            self.assertIn("NOX_ALLOW_CUSTOM_BOOTSTRAP=1", res_no_flag.stderr)

            # 2. HTTP URL must be rejected even with NOX_ALLOW_CUSTOM_BOOTSTRAP=1
            env_http = os.environ.copy()
            env_http["NOX_ALLOW_CUSTOM_BOOTSTRAP"] = "1"
            env_http["NOX_BOOTSTRAP_URL"] = "http://127.0.0.1:9999/nox-install.py"
            env_http["NOX_BOOTSTRAP_SHA256"] = wrong_sha
            res_http = subprocess.run(
                ["sh", str(REPO / "i")],
                env=env_http,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_http.returncode, 2)
            self.assertIn("HTTPS estrito", res_http.stderr)

            # 3. Invalid SHA-256 format must be rejected
            env_bad_sha = os.environ.copy()
            env_bad_sha["NOX_ALLOW_CUSTOM_BOOTSTRAP"] = "1"
            env_bad_sha["NOX_BOOTSTRAP_URL"] = "https://example.invalid/nox-install.py"
            env_bad_sha["NOX_BOOTSTRAP_SHA256"] = "not-a-sha256"
            res_bad_sha = subprocess.run(
                ["sh", str(REPO / "i")],
                env=env_bad_sha,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_bad_sha.returncode, 2)
            self.assertIn("formato SHA-256", res_bad_sha.stderr)

            # 4. Tampered bootstrap content must fail SHA-256 verification before python3 executes
            mock_bin = tmp / "bin"
            mock_bin.mkdir()
            mock_curl = mock_bin / "curl"
            mock_curl.write_text(
                "#!/usr/bin/env sh\n"
                "while [ $# -gt 0 ]; do\n"
                "  if [ \"$1\" = \"-o\" ]; then cp '" + str(fake_boot) + "' \"$2\"; exit 0; fi\n"
                "  shift\n"
                "done\n"
                "exit 1\n",
                encoding="utf-8",
            )
            mock_curl.chmod(0o755)

            env_tamper = os.environ.copy()
            env_tamper["PATH"] = f"{mock_bin}:{env_tamper.get('PATH', '')}"
            env_tamper["NOX_ALLOW_CUSTOM_BOOTSTRAP"] = "1"
            env_tamper["NOX_BOOTSTRAP_URL"] = "https://raw.githubusercontent.com/Awerkori/arch-install/0000000/bootstrap/nox-install.py"
            env_tamper["NOX_BOOTSTRAP_SHA256"] = wrong_sha
            res_tamper = subprocess.run(
                ["sh", str(REPO / "i")],
                env=env_tamper,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res_tamper.returncode, 0)
            self.assertIn("falha na verificacao SHA-256", res_tamper.stderr)
            self.assertNotIn("EXECUTED_UNVERIFIED", res_tamper.stdout)

            # 5. Matching SHA-256 executes cleanly
            good_sha = hashlib.sha256(fake_boot.read_bytes()).hexdigest()
            env_good = env_tamper.copy()
            env_good["NOX_BOOTSTRAP_SHA256"] = good_sha
            res_good = subprocess.run(
                ["sh", str(REPO / "i")],
                env=env_good,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(res_good.returncode, 0)
            self.assertIn("EXECUTED_UNVERIFIED", res_good.stdout)

    def test_config_integrity_verified_before_json_parse_and_http_rejected(self) -> None:
        import hashlib

        mod = self._load_nox_install()
        raw_cfg = (REPO / "user_configuration.json").read_bytes()
        real_sha = hashlib.sha256(raw_cfg).hexdigest()

        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            cfg_file = tmp / "user_configuration.json"
            cfg_file.write_bytes(raw_cfg)

            # Valid hash succeeds
            loaded = mod.load_base_config(str(cfg_file), expected_sha256=real_sha)
            self.assertEqual(loaded["bootloader_config"]["bootloader"], "Limine")

            # Tampered config with mismatched SHA-256 fails before JSON interpretation
            tampered = tmp / "tampered.json"
            tampered.write_text("NOT EVEN JSON", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                mod.load_base_config(str(tampered), expected_sha256=real_sha)
            self.assertIn("Falha na verificacao SHA-256", str(ctx.exception))

            # Invalid SHA-256 format is rejected
            with self.assertRaises(ValueError) as ctx2:
                mod.load_base_config(str(cfg_file), expected_sha256="12345")
            self.assertIn("Formato de SHA-256", str(ctx2.exception))

            # HTTP URL rejected without allow_insecure_http
            with self.assertRaises(ValueError) as ctx3:
                mod.load_base_config("http://127.0.0.1:8080/user_configuration.json", allow_insecure_http=False)
            self.assertIn("URL insegura recusada", str(ctx3.exception))

            # Mutable branch URL rejected without explicit expected_sha256
            with self.assertRaises(ValueError) as ctx4:
                mod.load_base_config(
                    "https://raw.githubusercontent.com/Awerkori/arch-install/main/user_configuration.json",
                    allow_insecure_http=False,
                    expected_sha256=None,
                )
            self.assertIn("branch mutavel", str(ctx4.exception))

    def test_redirect_downgrade_and_incomplete_download_rejected(self) -> None:
        import http.server
        import threading

        mod = self._load_nox_install()

        class TestHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:  # noqa: A002
                pass

            def do_GET(self) -> None:
                if self.path == "/redirect-http":
                    self.send_response(302)
                    self.send_header("Location", "http://example.com/user_configuration.json")
                    self.end_headers()
                elif self.path == "/truncated":
                    self.send_response(200)
                    self.send_header("Content-Length", "500")
                    self.end_headers()
                    self.wfile.write(b'{"partial": true}')
                elif self.path == "/empty":
                    self.send_response(200)
                    self.send_header("Content-Length", "0")
                    self.end_headers()

        server = http.server.HTTPServer(("127.0.0.1", 0), TestHandler)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            # 1. SafeHTTPSRedirectHandler refuses redirect to http:// when allow_insecure_http=False
            handler = mod.SafeHTTPSRedirectHandler(allow_insecure_http=False)
            req = mod.urllib.request.Request("https://github.com/Awerkori/arch-install/raw/v1.0.1/user_configuration.json")
            with self.assertRaises(ValueError) as r_ctx:
                handler.redirect_request(req, None, 302, "Found", {}, "http://evil.example.com/cfg.json")
            self.assertIn("downgrade HTTPS->HTTP", str(r_ctx.exception))

            # 2. Truncated download (Content-Length mismatch) raises RuntimeError
            with self.assertRaises(RuntimeError) as t_ctx:
                mod._fetch_url_bytes(f"http://127.0.0.1:{port}/truncated", allow_insecure_http=True)
            self.assertIn("incompleto", str(t_ctx.exception).lower())

            # 3. Empty response raises ValueError
            with self.assertRaises(ValueError) as e_ctx:
                mod._fetch_url_bytes(f"http://127.0.0.1:{port}/empty", allow_insecure_http=True)
            self.assertIn("Resposta vazia", str(e_ctx.exception))
        finally:
            server.shutdown()
            server.server_close()

    def test_payload_validation_rejects_other_version_and_tampered_tarball(self) -> None:
        import http.server
        import tarfile
        import threading

        mod = self._load_nox_install()
        base_cfg = json.loads((REPO / "user_configuration.json").read_text(encoding="utf-8"))

        # 1. Config pointing to another version or wrong payload hash fails when enforce_official_payload=True
        wrong_ver_cfg = json.loads(json.dumps(base_cfg))
        mod.override_payload_cmd(
            wrong_ver_cfg,
            "https://github.com/Awerkori/arch-install/releases/download/v0.9.0/nox-archinstall-payload-v0.9.0.tar.gz",
            "b" * 64,
        )
        with self.assertRaises(ValueError) as v_ctx:
            mod.validate_payload_spec(wrong_ver_cfg, enforce_official_payload=True)
        self.assertIn("incompativel com esta versao do bootstrap", str(v_ctx.exception))

        # 2. Legacy RC payload URL rejected by default
        rc_cfg = json.loads(json.dumps(base_cfg))
        mod.override_payload_cmd(
            rc_cfg,
            "https://github.com/Awerkori/arch-install/releases/download/v1.0.0-rc10/nox-archinstall-payload-v1.0.0-rc10.tar.gz",
            "c" * 64,
        )
        with self.assertRaises(ValueError) as rc_ctx:
            mod.validate_payload_spec(rc_cfg, allow_legacy_rc=False)
        self.assertIn("RC legado", str(rc_ctx.exception))

        # 3. Tampered payload tarball is rejected by nox-bootstrap.sh before extraction
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            pkg_dir = tmp / "pkg"
            pkg_dir.mkdir()
            (pkg_dir / "install.sh").write_text("#!/usr/bin/env bash\necho PWNED\n", encoding="utf-8")
            tar_file = tmp / "payload.tar.gz"
            with tarfile.open(tar_file, "w:gz") as tf:
                tf.add(pkg_dir / "install.sh", arcname="root/install.sh")

            class TarHandler(http.server.BaseHTTPRequestHandler):
                def log_message(self, format: str, *args) -> None:  # noqa: A002
                    pass

                def do_GET(self) -> None:
                    data = tar_file.read_bytes()
                    self.send_response(200)
                    self.send_header("Content-Length", str(len(data)))
                    self.end_headers()
                    self.wfile.write(data)

            srv = http.server.HTTPServer(("127.0.0.1", 0), TarHandler)
            port = srv.server_port
            th = threading.Thread(target=srv.serve_forever, daemon=True)
            th.start()
            try:
                dest_dir = tmp / "dest"
                env = os.environ.copy()
                env["NOX_ALLOW_INSECURE_HTTP"] = "1"
                env["NOX_ALLOW_TARGET_EXEC"] = "1"
                env["NOX_PAYLOAD_DEST_DIR"] = str(dest_dir)
                res = subprocess.run(
                    [
                        "bash",
                        str(REPO / "bootstrap/nox-bootstrap.sh"),
                        f"http://127.0.0.1:{port}/payload.tar.gz",
                        "d" * 64,
                    ],
                    env=env,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertNotEqual(res.returncode, 0)
                self.assertIn("Checksum SHA-256 divergente", res.stderr)
                self.assertFalse(dest_dir.exists(), "Tampered payload must never be extracted")
            finally:
                srv.shutdown()
                srv.server_close()


class TestBootstrapAndHostSafetyHardening(unittest.TestCase):
    @staticmethod
    def _load_nox_install():
        spec = importlib.util.spec_from_file_location("nox_install", REPO / "bootstrap/nox-install.py")
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_host_safety_guards_reject_execution_outside_iso_and_chroot(self) -> None:
        mod = self._load_nox_install()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            efi_dir = tmp / "efi"
            efi_dir.mkdir()
            missing_archiso = tmp / "no-archiso"

            # 1. Non-root rejected
            with self.assertRaises(RuntimeError) as e1:
                mod.ensure_arch_iso_environment(euid=1000, efi_dir=efi_dir, archiso_dir=efi_dir)
            self.assertIn("root", str(e1.exception))

            # 2. Non-UEFI rejected
            with self.assertRaises(RuntimeError) as e2:
                mod.ensure_arch_iso_environment(euid=0, efi_dir=missing_archiso, archiso_dir=efi_dir)
            self.assertIn("UEFI", str(e2.exception))

            # 3. Missing /run/archiso rejected
            with self.assertRaises(RuntimeError) as e3:
                mod.ensure_arch_iso_environment(euid=0, efi_dir=efi_dir, archiso_dir=missing_archiso)
            self.assertIn("/run/archiso", str(e3.exception))

            # 4. nox-bootstrap.sh refuses execution on host when NOX_ALLOW_TARGET_EXEC is not set
            env = os.environ.copy()
            env.pop("NOX_ALLOW_TARGET_EXEC", None)
            res = subprocess.run(
                [
                    "bash",
                    str(REPO / "bootstrap/nox-bootstrap.sh"),
                    "https://example.com/payload.tar.gz",
                    "e" * 64,
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("BLOQUEIO DE SEGURANCA", res.stderr)

    def test_tmpfs_selection_and_credential_scrubbing(self) -> None:
        mod = self._load_nox_install()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            no_tmpfs_mounts = tmp / "mounts_no_tmpfs"
            no_tmpfs_mounts.write_text("/dev/sda1 / ext4 rw 0 0\n", encoding="utf-8")
            with self.assertRaises(RuntimeError) as ctx:
                mod.select_tmpfs_dir(mounts_file=no_tmpfs_mounts)
            self.assertIn("tmpfs", str(ctx.exception))

            log1 = tmp / "var_log_archinstall"
            log2 = tmp / "mnt_var_log_archinstall"
            log1.mkdir(mode=0o755)
            log2.mkdir(mode=0o755)
            for d in (log1, log2):
                (d / "user_credentials.json").write_text('{"secret": 1}', encoding="utf-8")
                (d / "nox_creds.json").write_text('{"secret": 2}', encoding="utf-8")
                (d / "creds.json").write_text('{"secret": 3}', encoding="utf-8")
                (d / "install.log").write_text("normal log\n", encoding="utf-8")

            mod.scrub_persisted_archinstall_credentials(log_dirs=(log1, log2))
            for d in (log1, log2):
                self.assertFalse((d / "user_credentials.json").exists())
                self.assertFalse((d / "nox_creds.json").exists())
                self.assertFalse((d / "creds.json").exists())
                self.assertTrue((d / "install.log").exists())
                self.assertEqual( d.stat().st_mode & 0o777, 0o700)

    def test_verify_disk_safe_to_wipe_rejects_missing_or_mounted_or_broken_by_id(self) -> None:
        from unittest import mock

        mod = self._load_nox_install()
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fake_disk = tmp / "nvme0n1"
            fake_disk.write_text("", encoding="utf-8")
            other_disk = tmp / "sda"
            other_disk.write_text("", encoding="utf-8")
            bad_symlink = tmp / "by-id-nvme"
            bad_symlink.symlink_to(other_disk)

            # 1. Missing disk rejected
            with self.assertRaises(RuntimeError) as m_ctx:
                mod.verify_disk_safe_to_wipe({"path": str(tmp / "nonexistent"), "by_id": ""})
            self.assertIn("nao esta mais presente", str(m_ctx.exception))

            # 2. Broken/redirected by-id symlink rejected
            with self.assertRaises(RuntimeError) as id_ctx:
                mod.verify_disk_safe_to_wipe({"path": str(fake_disk), "by_id": str(bad_symlink)})
            self.assertIn("Identificador persistente", str(id_ctx.exception))

            # 3. Active mounts rejected
            fake_proc = subprocess.CompletedProcess(args=["lsblk"], returncode=0, stdout="/mnt\n", stderr="")
            with mock.patch.object(mod.subprocess, "run", return_value=fake_proc):
                with self.assertRaises(RuntimeError) as mnt_ctx:
                    mod.verify_disk_safe_to_wipe({"path": str(fake_disk), "by_id": ""})
                self.assertIn("pontos montados ativos", str(mnt_ctx.exception))

    def test_interactive_tty_and_accidental_wipe_abort_guards(self) -> None:
        from unittest import mock

        mod = self._load_nox_install()

        # 1. ensure_interactive_tty fails cleanly when stdin is not a TTY and /dev/tty is unavailable
        with (
            mock.patch.object(mod.sys.stdin, "isatty", return_value=False),
            mock.patch("builtins.open", side_effect=OSError("no controlling tty")),
        ):
            with self.assertRaises(RuntimeError) as tty_ctx:
                mod.ensure_interactive_tty()
            self.assertIn("/dev/tty", str(tty_ctx.exception))

        # 2. Mismatched disk name in [2/4] aborts with rc=130 without hashing password or running archinstall
        fake_disks = [
            {
                "name": "nvme0n1",
                "path": "/dev/nvme0n1",
                "size_bytes": 100 * (1024**3),
                "size_gib": 100.0,
                "model": "Test NVMe",
                "serial": "SN123",
                "tran": "nvme",
                "removable": False,
                "mounts": [],
                "by_id": "",
            }
        ]
        args = mod.parse_args(["--config", str(REPO / "user_configuration.json"), "--dry-run", "--skip-net-check"])
        with (
            mock.patch.object(mod, "ensure_interactive_tty"),
            mock.patch.object(mod, "list_candidate_disks", return_value=fake_disks),
            mock.patch("builtins.input", side_effect=["1", "wrongdisk"]),
            mock.patch.object(mod.subprocess, "run") as mock_run,
        ):
            rc = mod.interactive_main(args)
            self.assertEqual(rc, 130)
            mock_run.assert_not_called()

        # 3. Declining final confirmation [s/N] aborts with rc=130 without calling archinstall
        with (
            mock.patch.object(mod, "ensure_interactive_tty"),
            mock.patch.object(mod, "list_candidate_disks", return_value=fake_disks),
            mock.patch("builtins.input", side_effect=["1", "nvme0n1", "awerkori", "n"]),
            mock.patch.object(mod.getpass, "getpass", side_effect=["SecretPass123!", "SecretPass123!"]),
            mock.patch.object(mod.subprocess, "run") as mock_run2,
        ):
            rc2 = mod.interactive_main(args)
            self.assertEqual(rc2, 130)
            mock_run2.assert_not_called()


class TestSnapperConcurrencyAndEdgeCases(unittest.TestCase):
    def test_concurrent_cleanup_invocations_are_serialized_by_flock(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            lock_file = root / "cleanup.lock"
            state_file = root / "state.json"
            trace_file = root / "trace.log"
            entries = [
                {"number": 0, "type": "single", "cleanup": ""},
                {"number": 1, "type": "pre", "cleanup": "number"},
                {"number": 2, "type": "post", "pre-number": 1, "cleanup": "number"},
                {"number": 3, "type": "pre", "cleanup": "number"},
                {"number": 4, "type": "post", "pre-number": 3, "cleanup": "number"},
            ]
            in_json = root / "entries.json"
            in_json.write_text(json.dumps({"root": entries}), encoding="utf-8")

            mock_snapper = root / "mock-snapper"
            mock_snapper.write_text(
                "#!/usr/bin/env bash\n"
                f"echo \"START $$ $(date +%s%N)\" >> '{trace_file}'\n"
                "sleep 0.35\n"
                f"echo \"END $$ $(date +%s%N)\" >> '{trace_file}'\n",
                encoding="utf-8",
            )
            mock_snapper.chmod(0o755)

            cmd = [
                "python3",
                str(REPO / "configs/bin/nox-snapper-cleanup"),
                "--input-json",
                str(in_json),
                "--session-id",
                "",
                "--state-file",
                str(state_file),
                "--lock-file",
                str(lock_file),
                "--snapper-bin",
                str(mock_snapper),
            ]
            p1 = subprocess.Popen(cmd)
            p2 = subprocess.Popen(cmd)
            self.assertEqual(p1.wait(timeout=10), 0)
            self.assertEqual(p2.wait(timeout=10), 0)

            events = [line.split()[0] for line in trace_file.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(events, ["START", "END", "START", "END"])

    def test_failed_consolidate_create_preserves_intermediate_pair_and_important_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            state_file = root / "session.json"
            state_file.write_text(
                json.dumps({"session_id": "topgrade:99:1", "anchor_pre": 7, "latest_post": 8}),
                encoding="utf-8",
            )
            log_file = root / "snapper.log"
            entries = [
                {"number": 0, "type": "single", "cleanup": ""},
                {"number": 4, "type": "single", "cleanup": "number", "userdata": {"important": "yes"}},
                {"number": 7, "type": "pre", "cleanup": "number"},
                {"number": 8, "type": "post", "pre-number": 7, "cleanup": "number"},
                {"number": 9, "type": "pre", "cleanup": "number"},
                {"number": 10, "type": "post", "pre-number": 9, "cleanup": "number"},
            ]
            in_json = root / "in.json"
            in_json.write_text(json.dumps({"root": entries}), encoding="utf-8")

            # Mock snapper that succeeds on deleting old post 8, but FAILS on creating consolidated post
            mock_snapper = root / "mock-snapper"
            mock_snapper.write_text(
                "#!/usr/bin/env bash\n"
                f"echo \"$*\" >> '{log_file}'\n"
                "if [[ \"$*\" == *\"create\"* ]]; then\n"
                "  echo 'simulated create failure' >&2\n"
                "  exit 1\n"
                "fi\n",
                encoding="utf-8",
            )
            mock_snapper.chmod(0o755)

            subprocess.run(
                [
                    "python3",
                    str(REPO / "configs/bin/nox-snapper-cleanup"),
                    "--input-json",
                    str(in_json),
                    "--session-id",
                    "topgrade:99:1",
                    "--state-file",
                    str(state_file),
                    "--snapper-bin",
                    str(mock_snapper),
                ],
                check=True,
            )
            ops = log_file.read_text(encoding="utf-8").splitlines()
            # Must NOT delete 9 and 10 when create fails, and must never touch important=yes snapshot #4
            self.assertEqual(len(ops), 2)
            self.assertFalse(any("9 10" in op for op in ops))
            self.assertFalse(any(" 4" in op for op in ops))
            saved = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual((saved["anchor_pre"], saved["latest_post"]), (9, 10))


class TestLimineAndSecureBootHardening(unittest.TestCase):
    def test_secureboot_verify_and_limine_integrity_detect_and_repair_failures(self) -> None:
        import hashlib

        def b2(data: bytes) -> str:
            return hashlib.blake2b(data, digest_size=64).hexdigest()

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            esp = root / "boot"
            (esp / "EFI/limine").mkdir(parents=True)
            (esp / "EFI/BOOT").mkdir(parents=True)
            (esp / "abc123/linux-cachyos").mkdir(parents=True)

            wp_bytes = b"nox-wallpaper-bytes"
            kern_bytes = b"nox-kernel-vmlinuz-bytes"
            init_bytes = b"nox-initramfs-bytes"
            (esp / "nox-limine-wallpaper.png").write_bytes(wp_bytes)
            (esp / "abc123/linux-cachyos/vmlinuz").write_bytes(kern_bytes)
            (esp / "abc123/linux-cachyos/initramfs-linux-cachyos.img").write_bytes(init_bytes)

            conf_path = esp / "limine.conf"
            conf_text = (
                "timeout: 5\n"
                "default_entry: Arch Linux/Project Nox\n"
                "remember_last_entry: no\n"
                f"wallpaper: boot():/nox-limine-wallpaper.png#{b2(wp_bytes)}\n"
                "wallpaper_style: stretched\n"
                "/+Arch Linux\n"
                "  //Project Nox\n"
                "  comment: kernel-id=linux-cachyos\n"
                "  protocol: linux\n"
                f"  path: boot():/abc123/linux-cachyos/vmlinuz#{b2(kern_bytes)}\n"
                f"  module_path: boot():/abc123/linux-cachyos/initramfs-linux-cachyos.img#{b2(init_bytes)}\n"
            )
            conf_path.write_text(conf_text, encoding="utf-8")
            conf_hash = b2(conf_path.read_bytes())

            limine_efi = esp / "EFI/limine/limine_x64.efi"
            fallback_efi = esp / "EFI/BOOT/BOOTX64.EFI"
            src_efi = root / "BOOTX64.EFI.src"
            src_efi.write_bytes(b"MZ-FAKE-EFI-BINARY-" + (b"0" * 128))
            limine_efi.write_bytes(b"MZ-FAKE-EFI-" + conf_hash.encode("ascii") + b"-SIGNED\n")
            fallback_efi.write_bytes(b"MZ-FAKE-EFI-" + conf_hash.encode("ascii") + b"-SIGNED\n")
            (esp / "abc123/linux-cachyos/vmlinuz").write_bytes(kern_bytes)

            limine_default = root / "default-limine"
            limine_default.write_text(
                "ENABLE_VERIFICATION=yes\nENABLE_ENROLL_LIMINE_CONFIG=yes\n",
                encoding="utf-8",
            )
            dirty_marker = root / "nox-limine-tx.dirty"
            unsigned_list = root / "unsigned.txt"
            unsigned_list.write_text("", encoding="utf-8")

            bin_dir = root / "bin"
            bin_dir.mkdir()
            mock_sbctl = bin_dir / "sbctl"
            mock_sbctl.write_text(
                "#!/usr/bin/env bash\n"
                "case \"$1\" in\n"
                "  setup) echo '{\"installed\": true}' ;;\n"
                "  status) echo '{\"installed\": true, \"setup_mode\": false, \"secure_boot\": false}' ;;\n"
                "  verify)\n"
                f"    if grep -qxF \"$2\" '{unsigned_list}' 2>/dev/null; then\n"
                "      echo \"✗ $2 is not signed\"\n"
                "      exit 1\n"
                "    fi\n"
                "    echo \"✓ $2 is signed\"\n"
                "    ;;\n"
                "  sign)\n"
                "    target=\"${@: -1}\"\n"
                "    real_target=\"${target%.nox.tmp}\"\n"
                f"    sed -i \"\\|^${{real_target}}$|d\" '{unsigned_list}' 2>/dev/null || true\n"
                "    echo \"✓ Signed $target\"\n"
                "    ;;\n"
                "esac\n",
                encoding="utf-8",
            )
            mock_sbctl.chmod(0o755)

            mock_limine = bin_dir / "limine"
            mock_limine.write_text(
                "#!/usr/bin/env bash\n"
                "if [[ \"$1\" == \"enroll-config\" ]]; then\n"
                "  printf 'MZ-FAKE-EFI-%s-SIGNED\\n' \"$3\" > \"$2\"\n"
                "fi\n",
                encoding="utf-8",
            )
            mock_limine.chmod(0o755)

            mock_enroll_cfg = bin_dir / "limine-enroll-config"
            mock_enroll_cfg.write_text(
                "#!/usr/bin/env bash\n"
                f"h=\"$(b2sum '{conf_path}' | awk '{{print $1}}')\"\n"
                f"printf 'MZ-FAKE-EFI-%s-SIGNED\\n' \"$h\" > '{limine_efi}'\n"
                f"'{mock_sbctl}' sign '{limine_efi}' >/dev/null\n",
                encoding="utf-8",
            )
            mock_enroll_cfg.chmod(0o755)

            def run_verify(*extra: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [
                        "bash",
                        str(REPO / "configs/bin/nox-secureboot-verify"),
                        "--esp-path",
                        str(esp),
                        "--limine-default",
                        str(limine_default),
                        "--dirty-marker",
                        str(dirty_marker),
                        "--sbctl-bin",
                        str(mock_sbctl),
                        *extra,
                    ],
                    capture_output=True,
                    text=True,
                    check=False,
                )

            # 1. Clean state passes all offline checks
            ok_res = run_verify()
            self.assertEqual(ok_res.returncode, 0, ok_res.stderr + ok_res.stdout)
            self.assertIn("[NOX SECUREBOOT] OK", ok_res.stdout)

            # 2. --require-active fails when UEFI Secure Boot is disabled in firmware
            req_res = run_verify("--require-active")
            self.assertNotEqual(req_res.returncode, 0)
            self.assertIn("UEFI Secure Boot is NOT active", req_res.stderr)

            # 3. Partially updated config (dirty marker present) fails verification
            dirty_marker.write_text("", encoding="utf-8")
            dirty_res = run_verify()
            self.assertNotEqual(dirty_res.returncode, 0)
            self.assertIn("partially updated/interrupted", dirty_res.stderr)
            dirty_marker.unlink()

            # 4. Unsigned EFI binary fails verification
            unsigned_list.write_text(f"{limine_efi}\n", encoding="utf-8")
            unsig_res = run_verify()
            self.assertNotEqual(unsig_res.returncode, 0)
            self.assertIn("unsigned or missing EFI binary", unsig_res.stderr)
            unsigned_list.write_text("", encoding="utf-8")

            # 5. Missing EFI binary fails verification
            fallback_efi.unlink()
            miss_res = run_verify()
            self.assertNotEqual(miss_res.returncode, 0)
            self.assertIn("unsigned or missing EFI binary", miss_res.stderr)

            # 6. Incorrect asset BLAKE2B hash in limine.conf fails verification
            fallback_efi.write_bytes(b"MZ-FAKE-EFI-" + conf_hash.encode("ascii") + b"-SIGNED\n")
            (esp / "abc123/linux-cachyos/vmlinuz").write_bytes(b"TAMPERED-KERNEL-BYTES")
            bad_k_res = run_verify()
            self.assertNotEqual(bad_k_res.returncode, 0)
            self.assertIn("BLAKE2B mismatch", bad_k_res.stderr)
            (esp / "abc123/linux-cachyos/vmlinuz").write_bytes(kern_bytes)

            # 7. Adulterated limine.conf (mismatched config BLAKE2B in EFI + unnormalized //linux-cachyos)
            #    fails nox-secureboot-verify, and is automatically repaired by nox-limine-integrity!
            adulterated = conf_text.replace("  //Project Nox\n", "  //linux-cachyos\n")
            conf_path.write_text(adulterated, encoding="utf-8")
            dirty_marker.write_text("", encoding="utf-8")
            unsigned_list.write_text(f"{limine_efi}\n{fallback_efi}\n", encoding="utf-8")

            adult_res = run_verify()
            self.assertNotEqual(adult_res.returncode, 0)
            self.assertIn("NOT enrolled or mismatched", adult_res.stderr)

            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
            env["ESP_PATH"] = str(esp)
            env["NOX_DIRTY_MARKER"] = str(dirty_marker)
            env["NOX_LIMINE_DEFAULT"] = str(limine_default)
            env["NOX_NORMALIZE_BIN"] = str(REPO / "configs/bin/nox-limine-normalize")
            env["NOX_FALLBACK_HOOK"] = str(REPO / "configs/boot-hooks/95-nox-sbctl-fallback")
            env["NOX_LIMINE_SRC_EFI"] = str(src_efi)
            env["NOX_SBCTL_BIN"] = str(mock_sbctl)
            env["NOX_ALLOW_NONROOT_TEST"] = "1"
            env["NOX_FORCE_EFI_HOOK"] = "1"

            rep_res = subprocess.run(
                ["bash", str(REPO / "configs/bin/nox-limine-integrity"), "--repair-if-dirty"],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(rep_res.returncode, 0, rep_res.stderr)
            self.assertFalse(dirty_marker.exists())
            self.assertIn("  //Project Nox\n", conf_path.read_text(encoding="utf-8"))

            post_rep_verify = run_verify()
            self.assertEqual(post_rep_verify.returncode, 0, post_rep_verify.stderr + post_rep_verify.stdout)


class TestDocumentationAndManifestIntegrity(unittest.TestCase):
    def test_all_markdown_relative_links_exist(self) -> None:
        import re
        import urllib.parse

        link_re = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
        md_files = [REPO / "README.md", *sorted((REPO / "docs").rglob("*.md"))]
        for md in md_files:
            text = md.read_text(encoding="utf-8")
            for raw_target in link_re.findall(text):
                target = raw_target.strip().split()[0]
                if target.startswith(("http://", "https://", "mailto:", "#")):
                    continue
                rel_path = urllib.parse.unquote(target.split("#", 1)[0])
                if not rel_path:
                    continue
                resolved = (md.parent / rel_path).resolve()
                self.assertTrue(
                    resolved.exists(),
                    f"Broken link in {md.relative_to(REPO)}: {raw_target!r} -> {resolved} does not exist",
                )

    def test_release_manifest_and_config_payload_consistency(self) -> None:
        manifest = json.loads((REPO / "manifests/release.json").read_text(encoding="utf-8"))
        cfg = json.loads((REPO / "user_configuration.json").read_text(encoding="utf-8"))
        for req in ("version", "payload_commit", "payload_url", "payload_sha256"):
            self.assertIn(req, manifest)
            self.assertTrue(manifest[req])
        joined_cmd = "\n".join(cfg.get("custom_commands") or [])
        self.assertIn(manifest["payload_url"], joined_cmd)
        self.assertIn(manifest["payload_sha256"], joined_cmd)

    def test_documentation_has_no_unverified_mutable_install_commands(self) -> None:
        import hashlib

        launcher_sha = hashlib.sha256((REPO / "i").read_bytes()).hexdigest()
        boot_sha = hashlib.sha256((REPO / "bootstrap/nox-install.py").read_bytes()).hexdigest()
        cfg_sha = hashlib.sha256((REPO / "user_configuration.json").read_bytes()).hexdigest()

        i_text = (REPO / "i").read_text(encoding="utf-8")
        self.assertIn(f'DEFAULT_BOOTSTRAP_SHA256="{boot_sha}"', i_text)
        self.assertNotIn("/main/", i_text)

        boot_text = (REPO / "bootstrap/nox-install.py").read_text(encoding="utf-8")
        self.assertIn(f'OFFICIAL_CONFIG_SHA256 = "{cfg_sha}"', boot_text)
        self.assertNotIn("raw.githubusercontent.com/Awerkori/arch-install/main/", boot_text)

        for doc_rel in ("README.md", "docs/INSTALLATION.md"):
            doc_text = (REPO / doc_rel).read_text(encoding="utf-8")
            self.assertNotIn("/raw/main/i", doc_text)
            self.assertNotIn("raw.githubusercontent.com/Awerkori/arch-install/main/", doc_text)
            self.assertIn(launcher_sha, doc_text)
            self.assertIn("sha256sum -c -", doc_text)



