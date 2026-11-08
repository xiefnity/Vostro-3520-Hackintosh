"""Offline unit tests for scripts/make-efi.py (no network, nothing written outside temporary folders).

    python3 -m unittest discover tests

All identities used here are made-up test values.
"""
import base64
import hashlib
import importlib.util
import os
import plistlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "make-efi.py"

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
\t<key>Misc</key>
\t<dict>
\t\t<key>Boot</key>
\t\t<dict>
\t\t\t<key>Timeout</key>
\t\t\t<integer>0</integer>
\t\t</dict>
\t</dict>
\t<key>PlatformInfo</key>
\t<dict>
\t\t<key>Generic</key>
\t\t<dict>
\t\t\t<key>MLB</key>
\t\t\t<string>{{SMBIOS_MLB}}</string>
\t\t\t<key>ROM</key>
\t\t\t<string>{{SMBIOS_ROM}}</string>
\t\t\t<key>SystemProductName</key>
\t\t\t<string>MacBookPro16,2</string>
\t\t\t<key>SystemSerialNumber</key>
\t\t\t<string>{{SMBIOS_SERIAL_NUMBER}}</string>
\t\t\t<key>SystemUUID</key>
\t\t\t<string>{{SMBIOS_UUID}}</string>
\t\t</dict>
\t</dict>
</dict>
</plist>
"""

IDENTITY = {
    "SystemProductName": "MacBookPro16,2",
    "SystemSerialNumber": "C02TESTAAAA1",
    "MLB": "C02TESTMLB0000001",
    "SystemUUID": "11111111-2222-3333-4444-555555555555",
    "ROM": bytes.fromhex("0a1b2c3d4e5f"),
}


def load_module():
    spec = importlib.util.spec_from_file_location("make_efi", str(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Base(unittest.TestCase):
    def setUp(self):
        self.m = load_module()
        self.tmp = Path(tempfile.mkdtemp(prefix="make-efi-test-"))
        self.addCleanup(shutil.rmtree, str(self.tmp), True)
        # redirect every location the script uses into the temporary folder
        m = self.m
        m.ROOT = self.tmp
        m.SRC_EFI = self.tmp / "EFI"
        m.SRC_CONFIG = m.SRC_EFI / "OC" / "config.plist"
        m.BUILD_DIR = self.tmp / "build"
        m.DEPS_DIR = m.BUILD_DIR / "deps"
        m.STAGING_DIR = m.BUILD_DIR / "staging"
        m.DIST_DIR = self.tmp / "dist"
        m.DIST_EFI = m.DIST_DIR / "EFI"
        m.BACKUP_DIR = m.DIST_DIR / "backups"
        m.SMBIOS_FILE = self.tmp / "smbios.local"

    def write_template(self, text=TEMPLATE, extra_files=()):
        for rel in ("BOOT/BOOTx64.efi", "OC/OpenCore.efi") + tuple(extra_files):
            path = self.m.SRC_EFI / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b"binary")
        self.m.SRC_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        self.m.SRC_CONFIG.write_text(text, encoding="utf-8")

    def assertBuildError(self, func, *args, **kwargs):
        with self.assertRaises(self.m.BuildError) as ctx:
            func(*args, **kwargs)
        return str(ctx.exception)


class SmbiosFileTests(Base):
    def test_roundtrip(self):
        parsed = self.m.parse_smbios_text(self.m.format_smbios_file(IDENTITY))
        self.assertEqual(parsed, IDENTITY)
        self.assertIs(type(parsed["ROM"]), bytes)
        self.assertEqual(len(parsed["ROM"]), 6)

    def test_comments_blank_lines_and_case_are_tolerated(self):
        text = "# c\n\nSystemProductName=MacBookPro16,2\nSystemSerialNumber=c02testaaaa1\nMLB=c02testmlb0000001\n" \
               "SystemUUID=11111111-2222-3333-4444-555555555555\nROM=0A1B2C3D4E5F\n"
        parsed = self.m.parse_smbios_text(text)
        self.assertEqual(parsed["SystemSerialNumber"], "C02TESTAAAA1")
        self.assertEqual(parsed["ROM"], IDENTITY["ROM"])

    def mutate(self, **changes):
        lines = {k: (v.hex() if k == "ROM" else v) for k, v in IDENTITY.items()}
        lines.update(changes)
        return "".join("%s=%s\n" % (k, v) for k, v in lines.items() if v is not None)

    def test_invalid_files_stop_with_an_explanation(self):
        cases = {
            "missing MLB": self.mutate(MLB=None),
            "empty value": self.mutate(MLB=""),
            "short ROM": self.mutate(ROM="0a1b2c3d4e"),
            "long ROM": self.mutate(ROM="0a1b2c3d4e5f60"),
            "non-hex ROM": self.mutate(ROM="zz1b2c3d4e5f"),
            "zero ROM": self.mutate(ROM="000000000000"),
            "bad UUID": self.mutate(SystemUUID="not-a-uuid"),
            "nil UUID": self.mutate(SystemUUID="00000000-0000-0000-0000-000000000000"),
            "bad serial": self.mutate(SystemSerialNumber="abc"),
            "placeholder value": self.mutate(MLB="{{SMBIOS_MLB}}"),
            "unknown key": self.mutate() + "Extra=1\n",
            "duplicate key": self.mutate() + "MLB=C02TESTMLB0000002\n",
            "no equals sign": self.mutate() + "garbage\n",
            "empty file": "",
        }
        for name, text in cases.items():
            with self.subTest(name):
                message = self.assertBuildError(self.m.parse_smbios_text, text)
                self.assertIn("--regenerate-smbios", message)

    def test_generated_rom_is_unicast_and_locally_administered(self):
        for _ in range(200):
            rom = self.m.generate_rom()
            self.assertEqual(len(rom), 6)
            self.assertEqual(rom[0] & 0x03, 0x02)

    def test_file_is_private_and_never_overwritten_by_a_failed_write(self):
        path = self.m.SMBIOS_FILE
        self.m.write_smbios_file(path, IDENTITY)
        if os.name == "posix":
            self.assertEqual(path.stat().st_mode & 0o077, 0)
        self.assertEqual(self.m.read_smbios_file(path, "MacBookPro16,2"), IDENTITY)
        self.assertFalse(path.with_name(path.name + ".tmp").exists())

    def test_model_mismatch(self):
        self.m.write_smbios_file(self.m.SMBIOS_FILE, IDENTITY)
        message = self.assertBuildError(self.m.read_smbios_file, self.m.SMBIOS_FILE, "MacBookPro16,1")
        self.assertIn("MacBookPro16,2", message)


class PersonaliseTests(Base):
    def personalised(self):
        return self.m.personalise(TEMPLATE.encode(), IDENTITY)

    def test_values_and_types(self):
        config = plistlib.loads(self.personalised())["PlatformInfo"]["Generic"]
        for key in ("SystemSerialNumber", "MLB", "SystemUUID"):
            self.assertIs(type(config[key]), str)
            self.assertEqual(config[key], IDENTITY[key])
        self.assertIs(type(config["ROM"]), bytes)
        self.assertEqual(config["ROM"], IDENTITY["ROM"])
        self.assertEqual(len(config["ROM"]), 6)
        self.assertEqual(config["SystemProductName"], "MacBookPro16,2")

    def test_no_placeholder_remains_and_only_identity_changed(self):
        out = self.personalised()
        self.assertNotIn(b"{{", out)
        self.m.verify_personalised(out, plistlib.loads(TEMPLATE.encode()), IDENTITY)

    def test_each_placeholder_must_appear_exactly_once(self):
        doubled = TEMPLATE.replace("<key>Misc</key>", "<key>X</key><string>{{SMBIOS_MLB}}</string><key>Misc</key>")
        self.assertBuildError(self.m.personalise, doubled.encode(), IDENTITY)
        self.assertBuildError(self.m.personalise, TEMPLATE.replace("{{SMBIOS_UUID}}", "x").encode(), IDENTITY)

    def test_verify_rejects_collateral_changes(self):
        template = plistlib.loads(TEMPLATE.encode())
        tampered = self.personalised().replace(b"<integer>0</integer>", b"<integer>5</integer>")
        message = self.assertBuildError(self.m.verify_personalised, tampered, template, IDENTITY)
        self.assertIn("wrong places", message)

    def test_verify_rejects_rom_stored_as_text_or_wrong_size(self):
        template = plistlib.loads(TEMPLATE.encode())
        good = base64.b64encode(IDENTITY["ROM"])
        out = self.personalised()
        self.assertIn(b"<data>" + good + b"</data>", out)  # ROM really is a <data> element
        as_text = out.replace(b"<data>" + good + b"</data>", b"<string>0a1b2c3d4e5f</string>")
        self.assertBuildError(self.m.verify_personalised, as_text, template, IDENTITY)
        short = out.replace(good, base64.b64encode(IDENTITY["ROM"][:5]))
        self.assertBuildError(self.m.verify_personalised, short, template, IDENTITY)


class TemplateTests(Base):
    def test_valid_template(self):
        self.write_template()
        raw, config, model = self.m.load_template()
        self.assertEqual(model, "MacBookPro16,2")
        self.assertEqual(config["PlatformInfo"]["Generic"]["MLB"], "{{SMBIOS_MLB}}")

    def test_template_with_a_real_value_is_refused(self):
        self.write_template(TEMPLATE.replace("{{SMBIOS_SERIAL_NUMBER}}", "C02REALSERIAL"))
        message = self.assertBuildError(self.m.load_template)
        self.assertIn("placeholder", message)
        self.assertNotIn("C02REALSERIAL", message)  # never echo a value

    def test_second_configuration_is_refused(self):
        self.write_template()
        (self.m.SRC_EFI / "OC" / "config-old.plist").write_text("<plist/>")
        self.assertIn("config-old.plist", self.assertBuildError(self.m.load_template))

    def test_identity_key_elsewhere_is_refused(self):
        text = TEMPLATE.replace("<key>Misc</key>", "<key>NVRAM</key><dict><key>MLB</key><string>x</string></dict><key>Misc</key>")
        self.write_template(text)
        self.assertIn("NVRAM/MLB", self.assertBuildError(self.m.load_template))

    def test_unknown_token_and_missing_files(self):
        self.write_template(TEMPLATE.replace("<key>Misc</key>", "<key>A</key><string>{{OTHER}}</string><key>Misc</key>"))
        self.assertIn("{{OTHER}}", self.assertBuildError(self.m.load_template))
        shutil.rmtree(str(self.m.SRC_EFI))
        self.write_template()
        (self.m.SRC_EFI / "OC" / "OpenCore.efi").unlink()
        self.assertIn("OpenCore.efi", self.assertBuildError(self.m.load_template))

    def test_referenced_files_must_exist(self):
        efi = self.tmp / "efi"
        (efi / "OC" / "Kexts" / "A.kext" / "Contents" / "MacOS").mkdir(parents=True)
        (efi / "OC" / "ACPI").mkdir(parents=True)
        (efi / "OC" / "Drivers").mkdir(parents=True)
        (efi / "OC" / "ACPI" / "S.aml").write_bytes(b"x")
        (efi / "OC" / "Drivers" / "D.efi").write_bytes(b"x")
        config = {
            "ACPI": {"Add": [{"Enabled": True, "Path": "S.aml"}, {"Enabled": False, "Path": "gone.aml"}]},
            "Kernel": {"Add": [{"Enabled": True, "BundlePath": "A.kext", "ExecutablePath": "Contents/MacOS/A",
                                "PlistPath": "Contents/Info.plist"}]},
            "UEFI": {"Drivers": [{"Enabled": True, "Path": "D.efi"}, "Missing.efi"]},
        }
        message = self.assertBuildError(self.m.check_referenced_files, efi, config)
        self.assertIn("A.kext/Contents/MacOS/A", message)
        self.assertIn("Missing.efi", message)
        self.assertNotIn("gone.aml", message)  # disabled entries are not required


class SanitizeTests(Base):
    REAL = TEMPLATE.replace("{{SMBIOS_MLB}}", "C02REALMLB000000X").replace("{{SMBIOS_UUID}}", "AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE") \
        .replace("{{SMBIOS_SERIAL_NUMBER}}", "C02REALSER01").replace("<string>{{SMBIOS_ROM}}</string>", "<data>\n\t\t\t\tCxssPU5f\n\t\t\t</data>")

    def test_replaces_only_the_identity(self):
        source = self.tmp / "working.plist"
        source.write_text(self.REAL, encoding="utf-8")
        self.m.sanitize_template(source)
        out = self.m.SRC_CONFIG.read_bytes()
        for leaked in (b"C02REALMLB000000X", b"AAAAAAAA-BBBB", b"C02REALSER01", b"CxssPU5f"):
            self.assertNotIn(leaked, out)
        sanitized = plistlib.loads(out)
        self.assertEqual(set(self.m.diff_paths(plistlib.loads(self.REAL.encode()), sanitized)), self.m.IDENTITY_PATHS)
        self.assertEqual(sanitized["PlatformInfo"]["Generic"]["SystemProductName"], "MacBookPro16,2")
        self.assertEqual(sanitized["Misc"]["Boot"]["Timeout"], 0)

    def test_refuses_identity_keys_elsewhere_and_same_file(self):
        source = self.tmp / "working.plist"
        source.write_text(self.REAL.replace("<key>Misc</key>", "<key>NVRAM</key><dict><key>ROM</key><data>AAAA</data></dict><key>Misc</key>"))
        self.assertBuildError(self.m.sanitize_template, source)
        self.write_template()
        self.assertBuildError(self.m.sanitize_template, self.m.SRC_CONFIG)

    def test_output_is_accepted_by_the_template_check(self):
        source = self.tmp / "working.plist"
        source.write_text(self.REAL, encoding="utf-8")
        self.write_template()
        self.m.sanitize_template(source)
        self.assertEqual(self.m.load_template()[2], "MacBookPro16,2")


class IdentityLifecycleTests(Base):
    def test_valid_file_is_reused_and_nothing_is_generated(self):
        self.m.write_smbios_file(self.m.SMBIOS_FILE, IDENTITY)
        before = self.m.SMBIOS_FILE.read_bytes()
        with mock.patch.object(self.m, "generate_identity", side_effect=AssertionError("must not generate")):
            identity, is_new = self.m.obtain_identity("MacBookPro16,2", False, False)
        self.assertEqual(identity, IDENTITY)
        self.assertFalse(is_new)
        self.assertEqual(self.m.SMBIOS_FILE.read_bytes(), before)

    def test_invalid_file_never_triggers_generation(self):
        self.m.SMBIOS_FILE.write_text("SystemProductName=MacBookPro16,2\n")
        before = self.m.SMBIOS_FILE.read_bytes()
        with mock.patch.object(self.m, "generate_identity", side_effect=AssertionError("must not generate")):
            self.assertBuildError(self.m.obtain_identity, "MacBookPro16,2", False, False)
        self.assertEqual(self.m.SMBIOS_FILE.read_bytes(), before)
        self.assertEqual([p.name for p in self.tmp.glob("smbios.local*")], ["smbios.local"])

    def test_first_run_generates_in_memory_and_saves_only_on_request(self):
        with mock.patch.object(self.m, "generate_identity", return_value=IDENTITY) as gen:
            identity, is_new = self.m.obtain_identity("MacBookPro16,2", False, False)
        gen.assert_called_once_with("MacBookPro16,2")
        self.assertTrue(is_new)
        self.assertFalse(self.m.SMBIOS_FILE.exists())  # not written until the build has validated
        self.m.save_new_identity(identity)
        self.assertEqual(self.m.read_smbios_file(self.m.SMBIOS_FILE, "MacBookPro16,2"), IDENTITY)

    def test_regenerate_needs_confirmation_and_changes_nothing_without_it(self):
        self.m.write_smbios_file(self.m.SMBIOS_FILE, IDENTITY)
        before = self.m.SMBIOS_FILE.read_bytes()
        with mock.patch.object(self.m, "generate_identity", side_effect=AssertionError("must not generate")), \
                mock.patch.object(sys.stdin, "isatty", return_value=False), mock.patch("builtins.print"), \
                mock.patch("builtins.input", side_effect=AssertionError("must not prompt without a terminal")):
            self.assertBuildError(self.m.obtain_identity, "MacBookPro16,2", True, False)
        self.assertEqual(self.m.SMBIOS_FILE.read_bytes(), before)
        self.assertEqual([p.name for p in self.tmp.glob("smbios.local*")], ["smbios.local"])

    def test_regenerate_with_yes_keeps_a_backup_of_the_old_identity(self):
        self.m.write_smbios_file(self.m.SMBIOS_FILE, IDENTITY)
        old = self.m.SMBIOS_FILE.read_bytes()
        new = dict(IDENTITY, MLB="C02TESTMLB0000009")
        with mock.patch.object(self.m, "generate_identity", return_value=new), mock.patch("builtins.print"):
            identity, is_new = self.m.obtain_identity("MacBookPro16,2", True, True)
            self.assertTrue(is_new)
            self.assertEqual(self.m.SMBIOS_FILE.read_bytes(), old)  # still the old one until saved
            self.m.save_new_identity(identity)
        backups = list(self.tmp.glob("smbios.local.bak-*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_bytes(), old)
        self.assertEqual(self.m.read_smbios_file(self.m.SMBIOS_FILE, "MacBookPro16,2")["MLB"], "C02TESTMLB0000009")


class PublishTests(Base):
    def staged(self, content):
        staged = self.m.STAGING_DIR / "EFI"
        if staged.exists():
            shutil.rmtree(str(staged))
        (staged / "OC").mkdir(parents=True)
        (staged / "OC" / "config.plist").write_text(content)
        return staged

    def test_publish_backup_and_idempotence(self):
        with mock.patch("builtins.print"):
            self.assertTrue(self.m.publish(self.staged("one")))
            self.assertEqual((self.m.DIST_EFI / "OC" / "config.plist").read_text(), "one")
            self.assertFalse(self.m.BACKUP_DIR.exists())
            self.assertFalse(self.m.publish(self.staged("one")))  # identical: left alone, no backup
            self.assertFalse(self.m.BACKUP_DIR.exists())
            self.assertTrue(self.m.publish(self.staged("two")))
        self.assertEqual((self.m.DIST_EFI / "OC" / "config.plist").read_text(), "two")
        backups = list(self.m.BACKUP_DIR.iterdir())
        self.assertEqual(len(backups), 1)
        self.assertEqual((backups[0] / "OC" / "config.plist").read_text(), "one")

    def test_os_junk_does_not_force_a_new_backup(self):
        with mock.patch("builtins.print"):
            self.m.publish(self.staged("one"))
            (self.m.DIST_EFI / ".DS_Store").write_bytes(b"finder")
            self.assertFalse(self.m.publish(self.staged("one")))

    def test_failed_publish_restores_the_previous_build(self):
        with mock.patch("builtins.print"):
            self.m.publish(self.staged("one"))
            staged = self.staged("two")
            real_move = shutil.move

            def flaky(src, dst, *args, **kwargs):
                if Path(src) == staged:
                    raise OSError("disk full")
                return real_move(src, dst, *args, **kwargs)

            with mock.patch.object(self.m.shutil, "move", side_effect=flaky), self.assertRaises(OSError):
                self.m.publish(staged)
        self.assertEqual((self.m.DIST_EFI / "OC" / "config.plist").read_text(), "one")


class FetchTests(Base):
    def test_hash_is_enforced(self):
        payload = self.tmp / "payload.bin"
        payload.write_bytes(b"hello")
        url = payload.as_uri()
        good = hashlib.sha256(b"hello").hexdigest()
        dest = self.tmp / "cache" / "out.bin"
        with mock.patch("builtins.print"):
            self.assertEqual(self.m.fetch(url, good, dest), dest)
            self.assertEqual(dest.read_bytes(), b"hello")
            bad_dest = self.tmp / "cache" / "bad.bin"
            message = self.assertBuildError(self.m.fetch, url, "0" * 64, bad_dest)
        self.assertIn("SHA-256 mismatch", message)
        self.assertFalse(bad_dest.exists())
        self.assertFalse(bad_dest.with_name("bad.bin.part").exists())

    def test_pinned_hashes_look_like_sha256(self):
        for pinned in (self.m.OC_ZIP[1], self.m.HFSPLUS[1]):
            self.assertRegex(pinned, r"^[0-9a-f]{64}$")
        self.assertIn(self.m.OC_VERSION, self.m.OC_ZIP[0])


class RepositoryHygieneTests(unittest.TestCase):
    """The checked-in template must hold placeholders only."""

    def test_checked_in_template_is_sanitized(self):
        m = load_module()
        raw = (SCRIPT.parent.parent / "EFI" / "OC" / "config.plist").read_bytes()
        generic = plistlib.loads(raw)["PlatformInfo"]["Generic"]
        for key, token in m.PLACEHOLDERS.items():
            self.assertEqual(generic[key], token)
        self.assertEqual(generic["SystemProductName"], "MacBookPro16,2")

    def test_gitignore_protects_private_files(self):
        text = (SCRIPT.parent.parent / ".gitignore").read_text()
        lines = {line.strip() for line in text.splitlines()}
        for required in ("smbios.local", "dist/", "build/", "*.log", "*.tmp", "__pycache__/"):
            self.assertIn(required, lines)


if __name__ == "__main__":
    unittest.main()
