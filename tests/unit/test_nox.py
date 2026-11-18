"""Unit and contract tests for Nox Archinstall."""

from __future__ import annotations

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
        self.assertEqual(cfg["locale_config"]["sys_lang"], "pt_BR.UTF-8")
        self.assertEqual(cfg["swap"]["enabled"], False)
        self.assertEqual(cfg["kernels"], ["linux-zen"])

    def test_umbriel_default_layout_is_dwindle(self) -> None:
        toml_text = (REPO / "configs/umbriel/config.toml").read_text(encoding="utf-8")
        import tomllib
        parsed = tomllib.loads(toml_text)
        self.assertEqual(parsed["layout"]["mode"], "dwindle")
        self.assertIn("dwindle", parsed["layout"])
        self.assertNotIn("scrolling", parsed["layout"])


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
        self.assertIn('position = [2560, -400]', out)
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


class TestHushMicSetup(unittest.TestCase):
    def test_excludes_monitor_hdmi_navi_and_picks_analog(self) -> None:
        devs = [
            {"name": "alsa_output.pci-navi.hdmi.monitor", "description": "Monitor of Navi HDMI"},
            {"name": "alsa_input.hushmic", "description": "HushMic Virtual Microphone"},
            {"name": "alsa_input.pci-0000_12_00.6.analog-stereo", "description": "Ryzen HD Audio Realtek ALC1220 Analog"},
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as tf:
            json.dump(devs, tf)
            tpath = Path(tf.name)
        try:
            res = subprocess.run(
                [
                    "python3",
                    str(REPO / "configs/bin/nox-hushmic-setup"),
                    "--devices-json",
                    str(tpath),
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            out = json.loads(res.stdout)
            self.assertEqual(out["selected_mic"], "alsa_input.pci-0000_12_00.6.analog-stereo")
        finally:
            tpath.unlink(missing_ok=True)


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
