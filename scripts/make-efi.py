#!/usr/bin/env python3
"""Build a personalised OpenCore EFI for the Dell Vostro 3520 (Iris Xe, macOS Tahoe).

    python3 scripts/make-efi.py                      build dist/EFI (creates smbios.local on first run)
    python3 scripts/make-efi.py --check              check dependencies + template, do a throw-away trial build
    python3 scripts/make-efi.py --regenerate-smbios  deliberately replace your SMBIOS identity (read the warning)
    python3 scripts/make-efi.py --recovery           also download the macOS recovery image (~1 GB)

The repository holds a *template*: EFI/OC/config.plist contains placeholders instead of an SMBIOS
identity.  This script

  1. downloads the official OpenCore utilities and checks their SHA-256,
  2. loads your identity from smbios.local - or generates one with OpenCore's macserial and saves it,
  3. copies EFI/ to build/staging/ (the source is never modified),
  4. fetches Apple's HfsPlus.efi from acidanthera/OcBinaryData (SHA-256 checked),
  5. replaces the placeholders in the staged config.plist and verifies the result,
  6. runs ocvalidate on it, and only then
  7. moves it to dist/EFI (an existing dist/EFI is moved to dist/backups/, never deleted).

Privacy: the identity (SystemSerialNumber, MLB, SystemUUID, ROM) is generated and used locally.
Nothing in this script sends it anywhere; the only network traffic is downloading public files.
smbios.local and dist/ are listed in .gitignore - never publish them.

Only the Python standard library is needed (Python 3.8+).
"""
import argparse
import base64
import datetime
import fnmatch
import hashlib
import http.client
import os
import platform
import plistlib
import re
import secrets
import shutil
import subprocess
import sys
import urllib.request
import uuid
import zipfile
from pathlib import Path

if sys.version_info < (3, 8):
    sys.exit("error: Python 3.8 or newer is required (this is Python %d.%d)." % sys.version_info[:2])

# ----------------------------------------------------------------------------- locations
ROOT = Path(__file__).resolve().parent.parent
SRC_EFI = ROOT / "EFI"                       # the sanitized template; never modified by a build
SRC_CONFIG = SRC_EFI / "OC" / "config.plist"  # the ONLY configuration in this project
BUILD_DIR = ROOT / "build"                   # scratch space, git-ignored
DEPS_DIR = BUILD_DIR / "deps"
STAGING_DIR = BUILD_DIR / "staging"
DIST_DIR = ROOT / "dist"                     # output, git-ignored
DIST_EFI = DIST_DIR / "EFI"
BACKUP_DIR = DIST_DIR / "backups"
SMBIOS_FILE = ROOT / "smbios.local"          # your private identity, git-ignored

# ----------------------------------------------------------------------------- pinned downloads
OC_VERSION = "1.0.8"  # must match the OpenCore binaries in EFI/ (ocvalidate only accepts its own version)
OC_ZIP = (
    "https://github.com/acidanthera/OpenCorePkg/releases/download/%s/OpenCore-%s-RELEASE.zip"
    % (OC_VERSION, OC_VERSION),
    "2011e8b7216ecb2645d97ea710df965947edd406846e92050b9bc4190be6d27b",
)
# Apple's HFS+ driver is not redistributed in this repository; it is fetched from OcBinaryData instead.
HFSPLUS = (
    "https://raw.githubusercontent.com/acidanthera/OcBinaryData/"
    "c2a98980d30e39a571a2843ab26aa8d2b9188094/Drivers/HfsPlus.efi",
    "a55b5fff36578864ba6792c4c6369c71f6f35b61dd5a853ddf8583cd36c31d8f",
)
# Official macOS board identifiers, needed only for --recovery.
RECOVERY_BOARD_IDS = {"MacBookPro16,2": "Mac-5F9802EFE386AA28"}

TOOL_SUFFIX = {"Darwin": "", "Linux": ".linux", "Windows": ".exe"}  # names inside the OpenCore release zip

# ----------------------------------------------------------------------------- SMBIOS identity
# placeholder in the template  ->  key in PlatformInfo/Generic
PLACEHOLDERS = {
    "SystemSerialNumber": "{{SMBIOS_SERIAL_NUMBER}}",
    "MLB": "{{SMBIOS_MLB}}",
    "SystemUUID": "{{SMBIOS_UUID}}",
    "ROM": "{{SMBIOS_ROM}}",
}
IDENTITY_KEYS = tuple(PLACEHOLDERS)
IDENTITY_PATHS = {("PlatformInfo", "Generic", key) for key in IDENTITY_KEYS}
SMBIOS_FILE_KEYS = ("SystemProductName",) + IDENTITY_KEYS

SERIAL_RE = re.compile(r"[A-Z0-9]{11,12}")
MLB_RE = re.compile(r"[A-Z0-9]{13,17}")
ROM_HEX_RE = re.compile(r"[0-9A-Fa-f]{12}")
MACSERIAL_LINE_RE = re.compile(r"\s*([A-Z0-9]{11,12})\s*\|\s*([A-Z0-9]{13,17})\s*")
MACSERIAL_MODEL_RE = re.compile(r"^\s*Model:\s*\S+\s*-\s*(.+?)\s*$", re.M)

JUNK_PATTERNS = (".DS_Store", "._*", "Thumbs.db", "desktop.ini", ".gitkeep", ".gitignore")
IGNORE_JUNK = shutil.ignore_patterns(*JUNK_PATTERNS)
REQUIRED_TEMPLATE_FILES = ("BOOT/BOOTx64.efi", "OC/OpenCore.efi", "OC/config.plist")

REGENERATE_WARNING = """
WARNING - you asked for a NEW SMBIOS identity.
  Apple services (iCloud, iMessage, FaceTime, App Store, Find My) tie your Mac to its
  serial number / MLB / UUID / ROM.  A new identity looks like a different Mac to Apple:
  you may have to sign out and back in, and iMessage/FaceTime can need re-registering.
  Your current smbios.local will be kept as a timestamped backup next to it
  (smbios.local.bak-*, also git-ignored).  Only continue if you really want this.
"""


class BuildError(Exception):
    """A problem we can explain to the user.  Anything else is a bug."""


def say(message=""):
    print(message, flush=True)


def warn(message):
    print("warning: " + message, file=sys.stderr, flush=True)


# ----------------------------------------------------------------------------- generic helpers
def sha256_file(path):
    digest = hashlib.sha256()
    with open(str(path), "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_junk(name):
    return any(fnmatch.fnmatch(name, pattern) for pattern in JUNK_PATTERNS)


def tree_digest(root):
    """One hash for a directory tree (relative names + file contents; OS junk files ignored)."""
    digest = hashlib.sha256()
    for dirpath, dirnames, filenames in os.walk(str(root)):
        dirnames.sort()
        for name in sorted(filenames):
            if is_junk(name):
                continue
            full = Path(dirpath) / name
            digest.update(full.relative_to(root).as_posix().encode("utf-8") + b"\0")
            digest.update(sha256_file(full).encode("ascii") + b"\n")
    return digest.hexdigest()


def run(cmd, **kwargs):
    """Run a command, capturing text output.  Missing/unsupported executables become BuildErrors."""
    try:
        return subprocess.run([str(part) for part in cmd], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding="utf-8", errors="replace", **kwargs)
    except OSError as exc:
        raise BuildError("cannot run %s: %s\n  (OpenCore's prebuilt utilities support macOS, Windows and x86-64 "
                         "Linux; see Documentation/Troubleshooting.md)" % (Path(str(cmd[0])).name, exc))


def timestamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def unique_path(path):
    candidate, counter = path, 1
    while candidate.exists():
        counter += 1
        candidate = path.with_name("%s-%d" % (path.name, counter))
    return candidate


def move_aside(path, destination):
    """Move `path` to a unique location; never delete anything."""
    destination = unique_path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(destination))
    return destination


def rel(path):
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


# ----------------------------------------------------------------------------- downloads
def download(url, dest):
    request = urllib.request.Request(url, headers={"User-Agent": "vostro3520-make-efi"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response, open(str(dest), "wb") as out:
            shutil.copyfileobj(response, out)
        return
    except (OSError, http.client.HTTPException) as exc:  # URLError, SSL and timeout errors are OSErrors
        first_error = exc
    curl = shutil.which("curl")  # a second chance: curl uses the operating system's certificate store
    if curl:
        try:
            if subprocess.run([curl, "-fL", "--retry", "3", "-sS", "-o", str(dest), url]).returncode == 0:
                return
        except OSError:
            pass
    raise BuildError("could not download %s\n  %s\n  Check your internet connection (and, on python.org builds of "
                     "Python for macOS, run 'Install Certificates.command')." % (url, first_error))


def fetch(url, digest, dest):
    """Download `url` to `dest` (cached) and require its SHA-256 to equal `digest`."""
    dest = Path(dest)
    if dest.exists() and sha256_file(dest) == digest:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    say("  downloading %s" % dest.name)
    partial = dest.with_name(dest.name + ".part")
    download(url, partial)
    actual = sha256_file(partial)
    if actual != digest:
        partial.unlink()
        raise BuildError("SHA-256 mismatch for %s\n  expected %s\n  got      %s\n"
                         "  The file was discarded.  Do not continue unless you understand why." % (url, digest, actual))
    os.replace(str(partial), str(dest))
    return dest


# ----------------------------------------------------------------------------- OpenCore utilities
def tool_binary(utilities, name):
    system = platform.system()
    if system not in TOOL_SUFFIX:
        raise BuildError("unsupported operating system %r; use macOS, Linux (x86-64) or Windows." % system)
    if system == "Linux" and platform.machine().lower() not in ("x86_64", "amd64"):
        raise BuildError("OpenCore only ships x86-64 Linux utilities and this machine is %s.  Run the script on "
                         "macOS/Windows/x86-64 Linux, or under an x86-64 emulator." % platform.machine())
    return utilities / name / (name + TOOL_SUFFIX[system])


def oc_utilities():
    """Utilities/ from the official OpenCore release (downloaded once, verified, cached in build/deps)."""
    base = DEPS_DIR / ("OpenCore-" + OC_VERSION)
    utilities = base / "Utilities"
    wanted = (tool_binary(utilities, "macserial"), tool_binary(utilities, "ocvalidate"),
              utilities / "macrecovery" / "macrecovery.py")
    if not all(path.is_file() for path in wanted):
        archive = fetch(OC_ZIP[0], OC_ZIP[1], DEPS_DIR / ("OpenCore-%s-RELEASE.zip" % OC_VERSION))
        extracting = DEPS_DIR / ("OpenCore-%s.extracting" % OC_VERSION)
        if extracting.exists():
            shutil.rmtree(str(extracting))
        with zipfile.ZipFile(str(archive)) as zf:
            for member in zf.namelist():
                if member.startswith(("Utilities/macserial/", "Utilities/ocvalidate/", "Utilities/macrecovery/")):
                    zf.extract(member, str(extracting))
        if base.exists():
            shutil.rmtree(str(base))
        os.replace(str(extracting), str(base))
    return utilities


def oc_tool(name):
    path = tool_binary(oc_utilities(), name)
    if not path.is_file():
        raise BuildError("%s is missing from the OpenCore %s release; delete build/deps and retry." % (name, OC_VERSION))
    if platform.system() != "Windows":
        path.chmod(path.stat().st_mode | 0o111)  # zipfile does not keep the executable bit
    return path


# ----------------------------------------------------------------------------- the template
def diff_paths(a, b, path=()):
    """Paths at which two plist trees differ (values are never returned, so nothing sensitive leaks)."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = []
        for key in sorted(set(a) | set(b), key=str):
            if key not in a or key not in b:
                out.append(path + (key,))
            else:
                out.extend(diff_paths(a[key], b[key], path + (key,)))
        return out
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return [path]
        out = []
        for index, (x, y) in enumerate(zip(a, b)):
            out.extend(diff_paths(x, y, path + (index,)))
        return out
    return [] if (type(a) is type(b) and a == b) else [path]


def find_identity_keys(node, path=()):
    if isinstance(node, dict):
        for key, value in node.items():
            if key in IDENTITY_KEYS:
                yield path + (key,)
            yield from find_identity_keys(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from find_identity_keys(value, path + (index,))


def pretty(path):
    return "/".join(str(part) for part in path)


def load_template():
    """Find, parse and sanity-check the single configuration.  Returns (raw bytes, parsed plist, SMBIOS model)."""
    if not SRC_EFI.is_dir():
        raise BuildError("template folder %s not found - run the script from a full clone of the repository." % rel(SRC_EFI))
    oc_dir = SRC_CONFIG.parent
    extras = sorted(p.name for p in oc_dir.iterdir()
                    if p.is_file() and p.suffix.lower() == ".plist" and p.name != SRC_CONFIG.name)
    if extras:
        raise BuildError("EFI/OC must contain exactly one configuration (config.plist), but also has: %s\n"
                         "  Extra copies would be shipped in your EFI and may hold unsanitised data.  Move them "
                         "outside the repository." % ", ".join(extras))
    for required in REQUIRED_TEMPLATE_FILES:
        if not (SRC_EFI / required).is_file():
            raise BuildError("template is incomplete: EFI/%s is missing." % required)

    raw = SRC_CONFIG.read_bytes()
    try:
        config = plistlib.loads(raw)
    except Exception as exc:  # expat / plistlib raise several unrelated types
        raise BuildError("%s is not a valid property list: %s" % (rel(SRC_CONFIG), exc))

    try:
        generic = config["PlatformInfo"]["Generic"]
    except (KeyError, TypeError):
        raise BuildError("%s has no PlatformInfo/Generic section." % rel(SRC_CONFIG))
    for key, token in PLACEHOLDERS.items():
        if generic.get(key) != token:
            raise BuildError(
                "template PlatformInfo/Generic/%s is not the placeholder %s.\n"
                "  The public template must never contain a real identity.  If you edited EFI/OC/config.plist, "
                "restore it (git checkout -- EFI/OC/config.plist) - your identity belongs in smbios.local only."
                % (key, token))
    elsewhere = [p for p in find_identity_keys(config) if tuple(p) not in IDENTITY_PATHS]
    if elsewhere:
        raise BuildError("identity-style keys found outside PlatformInfo/Generic: %s\n  This script only personalises "
                         "PlatformInfo/Generic; remove or sanitise these first." % ", ".join(pretty(p) for p in elsewhere))
    known = set(PLACEHOLDERS.values())
    stray = sorted({m.decode("utf-8", "replace") for m in re.findall(rb"\{\{[^}]*\}\}", raw)} - known)
    if stray:
        raise BuildError("unknown placeholder(s) in the template: %s" % ", ".join(stray))

    model = generic.get("SystemProductName")
    if not isinstance(model, str) or not model:
        raise BuildError("template PlatformInfo/Generic/SystemProductName is missing.")
    return raw, config, model


# ----------------------------------------------------------------------------- SMBIOS identity file
def parse_smbios_text(text, source="smbios.local"):
    """Strictly parse an identity file into a dict (ROM becomes 6 bytes).  Raises BuildError."""
    values, problems = {}, []
    for number, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            problems.append("line %d: expected KEY=VALUE" % number)
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key not in SMBIOS_FILE_KEYS:
            problems.append("line %d: unknown key %r" % (number, key))
        elif key in values:
            problems.append("line %d: %s appears twice" % (number, key))
        else:
            values[key] = value
    for key in SMBIOS_FILE_KEYS:
        if not values.get(key):
            problems.append("%s is missing or empty" % key)

    if any("{{" in v or "}}" in v for v in values.values()):
        problems.append("a value still looks like a template placeholder")
    for key in ("SystemSerialNumber", "MLB"):  # case-insensitive input, stored upper-case like macserial prints it
        if values.get(key):
            values[key] = values[key].upper()
    if values.get("SystemSerialNumber") and not SERIAL_RE.fullmatch(values["SystemSerialNumber"]):
        problems.append("SystemSerialNumber is invalid (expected 11-12 letters/digits)")
    if values.get("MLB") and not MLB_RE.fullmatch(values["MLB"]):
        problems.append("MLB is invalid (expected 13-17 letters/digits)")
    if values.get("ROM"):
        if not ROM_HEX_RE.fullmatch(values["ROM"]):
            problems.append("ROM is invalid (expected exactly 12 hexadecimal digits = 6 bytes)")
        elif int(values["ROM"], 16) in (0, (1 << 48) - 1):
            problems.append("ROM is invalid (all zeros / all ones)")
    if values.get("SystemUUID"):
        try:
            parsed = uuid.UUID(values["SystemUUID"])
            if parsed.int == 0:
                raise ValueError
            values["SystemUUID"] = str(parsed).upper()
        except ValueError:
            problems.append("SystemUUID is invalid (expected a UUID such as 8-4-4-4-12 hex digits, not all zeros)")
    if problems:
        raise BuildError(
            "%s is incomplete or invalid:\n  - %s\n\n"
            "Nothing was changed and no replacement identity was generated.  Fix the file by hand (see "
            "README.md, 'smbios.local'), or - only if you really want a brand-new identity - run again "
            "with --regenerate-smbios." % (source, "\n  - ".join(problems)))
    values["ROM"] = bytes.fromhex(values["ROM"])
    return values


def format_smbios_file(identity):
    lines = [
        "# SMBIOS identity for the Dell Vostro 3520 EFI, created by scripts/make-efi.py",
        "# PRIVATE - never commit, upload or share this file, and keep a backup of it.",
        "# A different identity makes iCloud / iMessage / FaceTime see a different Mac.",
    ]
    for key in SMBIOS_FILE_KEYS:
        value = identity[key].hex() if key == "ROM" else identity[key]
        lines.append("%s=%s" % (key, value))
    return "\n".join(lines) + "\n"


def write_smbios_file(path, identity):
    """Write the identity file, readable by the owner only (where the OS supports it)."""
    temp = path.with_name(path.name + ".tmp")
    fd = os.open(str(temp), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(format_smbios_file(identity))
    os.replace(str(temp), str(path))


def generate_rom():
    """Six random bytes, flagged as a unicast, locally-administered MAC address (cannot clash with a real NIC)."""
    rom = bytearray(secrets.token_bytes(6))
    rom[0] = (rom[0] & 0xFC) | 0x02
    return bytes(rom)


def check_serial_model(macserial, serial, model, strict):
    """Ask macserial which Mac model a serial belongs to and compare it with the configured model."""
    result = run([macserial, "-i", serial])
    match = MACSERIAL_MODEL_RE.search(result.stdout) if result.returncode == 0 else None
    if not match:
        warn("could not confirm that the serial matches %s (unexpected macserial output)." % model)
        return
    if match.group(1) != model:
        message = "the serial decodes to model %s but the configuration uses %s" % (match.group(1), model)
        if strict:
            raise BuildError("macserial " + message + ".")
        warn("smbios.local: " + message + ".")


def generate_identity(model):
    macserial = oc_tool("macserial")
    result = run([macserial, "-m", model, "-g", "-n", "1"])
    if result.returncode != 0:
        raise BuildError("macserial could not generate an identity for model %r (exit code %d).\n  %s"
                         % (model, result.returncode, (result.stdout + result.stderr).strip()[:300]))
    serial = mlb = None
    for line in result.stdout.splitlines():
        match = MACSERIAL_LINE_RE.fullmatch(line)
        if match:
            serial, mlb = match.groups()
            break
    if serial is None:  # deliberately not echoing the output: it would be an identity
        raise BuildError("unexpected output format from macserial; refusing to guess.")
    check_serial_model(macserial, serial, model, strict=True)
    return {"SystemProductName": model, "SystemSerialNumber": serial, "MLB": mlb,
            "SystemUUID": str(uuid.uuid4()).upper(), "ROM": generate_rom()}


def read_smbios_file(path, model):
    if path.is_dir():
        raise BuildError("%s is a directory, expected a file." % rel(path))
    try:
        text = path.read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError) as exc:
        raise BuildError("cannot read %s: %s" % (rel(path), exc))
    identity = parse_smbios_text(text, rel(path))
    if identity["SystemProductName"] != model:
        raise BuildError(
            "smbios.local was created for %s but the EFI template uses %s.\n"
            "  Serial numbers and MLBs are model-specific, so they cannot be reused.  Restore the template that "
            "matches your identity, or run with --regenerate-smbios to create one for %s."
            % (identity["SystemProductName"], model, model))
    if os.name == "posix" and path.stat().st_mode & 0o077:
        warn("%s is readable by other users on this machine; run: chmod 600 %s" % (rel(path), rel(path)))
    return identity


def confirm_regeneration(assume_yes):
    say(REGENERATE_WARNING)
    if assume_yes:
        return
    if not sys.stdin.isatty():
        raise BuildError("--regenerate-smbios needs confirmation but there is no terminal; add --yes to confirm.")
    if input("Type REGENERATE to create a new identity, anything else cancels: ").strip() != "REGENERATE":
        raise BuildError("cancelled; smbios.local is unchanged.")


def obtain_identity(model, regenerate, assume_yes):
    """Reuse smbios.local when it is valid; otherwise make a new identity.  Returns (identity, is_new).

    A new identity only exists in memory here: it is written to disk by save_new_identity() *after* the
    build has been validated, so a failed build never costs you an existing smbios.local.
    """
    exists = SMBIOS_FILE.exists()
    if exists and not regenerate:
        identity = read_smbios_file(SMBIOS_FILE, model)
        say("  SMBIOS: reusing your existing identity from smbios.local (values are not displayed)")
        return identity, False
    if exists:
        confirm_regeneration(assume_yes)
    identity = generate_identity(model)
    say("  SMBIOS: generated a new identity for %s with macserial (it is saved once the build validates)" % model)
    return identity, True


def save_new_identity(identity):
    """Persist a freshly generated identity; an existing smbios.local is kept as a timestamped backup."""
    backup = None
    if SMBIOS_FILE.exists():
        backup = move_aside(SMBIOS_FILE, SMBIOS_FILE.with_name("smbios.local.bak-" + timestamp()))
        say("  previous identity kept as %s" % rel(backup))
    try:
        write_smbios_file(SMBIOS_FILE, identity)
    except BaseException:
        if backup is not None and not SMBIOS_FILE.exists():
            shutil.move(str(backup), str(SMBIOS_FILE))
        raise
    say("  new identity saved to smbios.local")
    say("  Back this file up and keep it private - it is what makes your Mac *your* Mac to Apple.")


# ----------------------------------------------------------------------------- personalising + verifying
def personalise(raw, identity):
    """Replace the four placeholders in the template text; ROM becomes a <data> element of six bytes."""
    text = raw.decode("utf-8")
    elements = {
        PLACEHOLDERS["SystemSerialNumber"]: "<string>%s</string>" % identity["SystemSerialNumber"],
        PLACEHOLDERS["MLB"]: "<string>%s</string>" % identity["MLB"],
        PLACEHOLDERS["SystemUUID"]: "<string>%s</string>" % identity["SystemUUID"],
        PLACEHOLDERS["ROM"]: "<data>%s</data>" % base64.b64encode(identity["ROM"]).decode("ascii"),
    }
    for token, element in elements.items():
        pattern = re.compile(r"<string>\s*" + re.escape(token) + r"\s*</string>")
        text, count = pattern.subn(lambda _match, element=element: element, text)
        if count != 1:
            raise BuildError("expected exactly one %s in the template but found %d." % (token, count))
    return text.encode("utf-8")


def verify_personalised(output, template, identity):
    """Fail unless the config holds exactly the intended identity (correct types) and differs from the
    template in nothing else."""
    for token in PLACEHOLDERS.values():
        if token.encode("ascii") in output:
            raise BuildError("unresolved placeholder %s remains in the generated config.plist." % token)
    if b"{{" in output or b"}}" in output:
        raise BuildError("template syntax ({{ }}) remains in the generated config.plist.")
    try:
        config = plistlib.loads(output)
        generic = config["PlatformInfo"]["Generic"]
    except Exception as exc:
        raise BuildError("generated config.plist cannot be parsed back: %s" % exc)
    for key in ("SystemProductName", "SystemSerialNumber", "MLB", "SystemUUID"):
        if type(generic.get(key)) is not str or generic[key] != identity[key]:
            raise BuildError("PlatformInfo/Generic/%s was not inserted correctly." % key)
    rom = generic.get("ROM")
    if type(rom) is not bytes or len(rom) != 6 or rom != identity["ROM"]:
        raise BuildError("PlatformInfo/Generic/ROM must be exactly six bytes (<data>) and was not inserted correctly.")
    changed = set(diff_paths(template, config))
    if changed != IDENTITY_PATHS:
        unexpected = sorted(pretty(p) for p in changed - IDENTITY_PATHS)
        missing = sorted(pretty(p) for p in IDENTITY_PATHS - changed)
        raise BuildError("generated config differs from the template in the wrong places (unexpected: %s; "
                         "unchanged identity fields: %s)." % (unexpected or "none", missing or "none"))


def scan_for_placeholders(efi):
    token = b"{{SMBIOS_"
    for dirpath, _dirs, filenames in os.walk(str(efi)):
        for name in filenames:
            full = Path(dirpath) / name
            with open(str(full), "rb") as handle:
                if token in handle.read():
                    raise BuildError("unresolved placeholder found in %s" % full.relative_to(efi).as_posix())


def check_referenced_files(efi, config):
    """Every enabled ACPI table, kext and driver named in config.plist must exist in the staged EFI."""
    oc = efi / "OC"
    missing = []

    def need(path):
        if not path.exists():
            missing.append(path.relative_to(efi).as_posix())

    for entry in config.get("ACPI", {}).get("Add", []):
        if entry.get("Enabled"):
            need(oc / "ACPI" / entry["Path"])
    for entry in config.get("Kernel", {}).get("Add", []):
        if entry.get("Enabled"):
            bundle = oc / "Kexts" / entry["BundlePath"]
            need(bundle)
            for field in ("ExecutablePath", "PlistPath"):
                if entry.get(field):
                    need(bundle / entry[field])
    for entry in config.get("UEFI", {}).get("Drivers", []):
        name, enabled = (entry.get("Path"), entry.get("Enabled", True)) if isinstance(entry, dict) else (entry, True)
        if enabled and name:
            need(oc / "Drivers" / name)
    for entry in config.get("Misc", {}).get("Tools", []):
        if entry.get("Enabled") and entry.get("Path"):
            need(oc / "Tools" / entry["Path"])
    if missing:
        raise BuildError("config.plist refers to files that are not in the EFI:\n  - %s" % "\n  - ".join(sorted(set(missing))))


def run_ocvalidate(config_path):
    result = run([oc_tool("ocvalidate"), config_path])
    if result.returncode != 0 or "No issues found" not in result.stdout:
        report = (result.stdout + result.stderr).strip()
        raise BuildError("ocvalidate rejected the generated config.plist:\n    " + report.replace("\n", "\n    "))
    say("  ocvalidate %s: No issues found" % OC_VERSION)


# ----------------------------------------------------------------------------- build pipeline
def stage_efi(identity, template_raw, template_config):
    """Create build/staging/EFI, personalised and validated.  The template itself is only ever read."""
    if STAGING_DIR.exists():
        shutil.rmtree(str(STAGING_DIR))
    efi = STAGING_DIR / "EFI"
    shutil.copytree(str(SRC_EFI), str(efi), ignore=IGNORE_JUNK)

    drivers = efi / "OC" / "Drivers"
    drivers.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(str(fetch(HFSPLUS[0], HFSPLUS[1], DEPS_DIR / "HfsPlus.efi")), str(drivers / "HfsPlus.efi"))

    config_path = efi / "OC" / "config.plist"
    output = personalise(template_raw, identity)
    verify_personalised(output, template_config, identity)
    config_path.write_bytes(output)
    verify_personalised(config_path.read_bytes(), template_config, identity)  # re-check what is really on disk
    say("  config.plist personalised: 4 SMBIOS fields set (ROM stored as 6 raw bytes), nothing else changed")

    scan_for_placeholders(efi)
    say("  no unresolved placeholders anywhere in the EFI")
    check_referenced_files(efi, plistlib.loads(output))
    say("  every enabled ACPI table, kext and driver named in config.plist is present")
    run_ocvalidate(config_path)
    return efi


def publish(staged_efi):
    """Move the staged EFI to dist/EFI, keeping any previous build in dist/backups/."""
    DIST_DIR.mkdir(exist_ok=True)
    if DIST_EFI.exists():
        if tree_digest(DIST_EFI) == tree_digest(staged_efi):
            say("  dist/EFI is already identical to this build - left untouched")
            shutil.rmtree(str(staged_efi))
            return False
        backup = move_aside(DIST_EFI, BACKUP_DIR / ("EFI-" + timestamp()))
        say("  previous dist/EFI moved to %s (delete it yourself once you no longer need it)" % rel(backup))
    else:
        backup = None
    try:
        shutil.move(str(staged_efi), str(DIST_EFI))
    except BaseException:
        if backup is not None:  # put the previous build back rather than leave dist/ without an EFI
            if DIST_EFI.exists():
                shutil.rmtree(str(DIST_EFI), ignore_errors=True)
            shutil.move(str(backup), str(DIST_EFI))
        raise
    return True


def download_recovery(model):
    board = RECOVERY_BOARD_IDS.get(model)
    if board is None:
        raise BuildError("no macOS board identifier is recorded for %s; add it to RECOVERY_BOARD_IDS." % model)
    out = DIST_DIR / "com.apple.recovery.boot"
    if (out / "BaseSystem.dmg").is_file():
        say("  recovery image already present in dist/com.apple.recovery.boot (delete the folder to fetch it again)")
        return out
    DIST_DIR.mkdir(exist_ok=True)
    part = DIST_DIR / "recovery.part"
    if part.exists():
        shutil.rmtree(str(part))
    macrecovery = oc_utilities() / "macrecovery"
    say("  asking Apple's recovery servers for the latest macOS for board %s (about 1 GB)..." % board)
    # '-m 000...0' is deliberate: the real MLB is never needed, never read and never sent.
    result = subprocess.run([sys.executable, "macrecovery.py", "-b", board, "-m", "00000000000000000",
                             "-os", "latest", "-o", str(part), "download"], cwd=str(macrecovery))
    if result.returncode != 0:
        raise BuildError("the recovery download failed (macrecovery checks the image against Apple's chunklist); "
                         "run again.")
    if out.exists():
        move_aside(out, BACKUP_DIR / ("com.apple.recovery.boot-" + timestamp()))
    os.replace(str(part), str(out))
    return out


# ----------------------------------------------------------------------------- maintainer tool
def sanitize_template(source):
    """Maintainers: turn a *working* config.plist into the public template (EFI/OC/config.plist).

    Replaces the four identity fields with placeholders, changes nothing else, never prints a value.
    """
    source = Path(source)
    if not source.is_file():
        raise BuildError("%s is not a file." % source)
    if SRC_CONFIG.exists() and source.resolve() == SRC_CONFIG.resolve():
        raise BuildError("source and destination are the same file; point --sanitize at your working config.plist.")
    raw = source.read_bytes()
    try:
        original = plistlib.loads(raw)
    except Exception as exc:
        raise BuildError("%s is not a valid property list: %s" % (source, exc))
    where = sorted(pretty(p) for p in find_identity_keys(original) if tuple(p) not in IDENTITY_PATHS)
    if where:
        raise BuildError("identity-style keys also appear in: %s - sanitise these by hand first." % ", ".join(where))

    out = raw
    for key, token in PLACEHOLDERS.items():
        pattern = re.compile(rb"(<key>" + key.encode() + rb"</key>\s*)<(string|data)>[^<]*</\2>")
        if len(pattern.findall(out)) != 1:
            raise BuildError("expected exactly one <%s> element in the config, found %d."
                             % (key, len(pattern.findall(out))))
        out = pattern.sub(lambda m, token=token: m.group(1) + b"<string>" + token.encode() + b"</string>", out)

    cleaned = plistlib.loads(out)
    if set(diff_paths(original, cleaned)) != IDENTITY_PATHS:
        raise BuildError("sanitising changed more than the four identity fields; aborting.")
    generic = original["PlatformInfo"]["Generic"]
    for key in IDENTITY_KEYS:  # belt and braces: no form of any old value may survive anywhere in the output
        value = generic[key]
        forms = ([value.hex().encode(), value.hex().upper().encode(), base64.b64encode(value)]
                 if isinstance(value, bytes) else [str(value).encode("utf-8")])
        if any(form and form in out for form in forms):
            raise BuildError("an original %s value still appears in the sanitised output; aborting." % key)

    SRC_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    SRC_CONFIG.write_bytes(out)
    say("Sanitised template written to %s" % rel(SRC_CONFIG))
    say("  4 identity fields replaced by placeholders, SystemProductName %s kept, no values printed."
        % generic.get("SystemProductName"))
    say("Next: run 'python3 scripts/make-efi.py --check', then review 'git diff' before committing.")


# ----------------------------------------------------------------------------- command line
def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Build a personalised OpenCore EFI for the Dell Vostro 3520 into dist/EFI.",
        epilog="Your identity lives in smbios.local.  It is created on the first build, reused afterwards, and "
               "never printed or transmitted.  Do not publish smbios.local or dist/.")
    parser.add_argument("--check", action="store_true",
                        help="verify dependencies and the template and run a throw-away trial build with a temporary "
                             "identity; writes nothing to dist/ or smbios.local")
    parser.add_argument("--regenerate-smbios", action="store_true",
                        help="replace smbios.local with a NEW identity (asks for confirmation; the old file is kept)")
    parser.add_argument("--yes", action="store_true", help="answer the --regenerate-smbios confirmation with yes")
    parser.add_argument("--recovery", action="store_true",
                        help="also download the latest macOS recovery image to dist/com.apple.recovery.boot")
    parser.add_argument("--sanitize", metavar="WORKING_CONFIG",
                        help="maintainers only: write the public template EFI/OC/config.plist from your working "
                             "config.plist (identity replaced by placeholders)")
    args = parser.parse_args(argv)
    if args.check and (args.regenerate_smbios or args.recovery or args.sanitize):
        parser.error("--check cannot be combined with other actions")
    if args.sanitize and (args.regenerate_smbios or args.recovery):
        parser.error("--sanitize cannot be combined with other actions")
    return args


def main(argv=None):
    args = parse_args(argv)
    if args.sanitize:
        sanitize_template(args.sanitize)
        return 0

    total = 4 if args.check else 5 + (1 if args.recovery else 0)
    step = [0]

    def heading(text):
        step[0] += 1
        say("\n[%d/%d] %s" % (step[0], total, text))

    heading("Checking the template")
    template_raw, template_config, model = load_template()
    say("  active configuration: %s (single config, SMBIOS model %s)" % (rel(SRC_CONFIG), model))
    say("  template holds only placeholders - no identity")
    source_digest = tree_digest(SRC_EFI)

    heading("Checking dependencies (Python %d.%d, %s)" % (sys.version_info[0], sys.version_info[1], platform.system()))
    oc_tool("macserial")
    oc_tool("ocvalidate")
    say("  OpenCore %s utilities ready (SHA-256 verified)" % OC_VERSION)

    if args.check:
        heading("Identity")
        if SMBIOS_FILE.exists():
            read_smbios_file(SMBIOS_FILE, model)
            say("  smbios.local is present and valid (it would be reused)")
        else:
            say("  no smbios.local yet - one will be generated on the first real build")
        heading("Trial build with a temporary identity (nothing is kept)")
        try:
            stage_efi(generate_identity(model), template_raw, template_config)
        finally:
            shutil.rmtree(str(STAGING_DIR), ignore_errors=True)
        if tree_digest(SRC_EFI) != source_digest:
            raise BuildError("the source EFI/ changed during the check - this must never happen; please report it.")
        say("\nAll checks passed.  Run again without --check to build dist/EFI.")
        return 0

    heading("SMBIOS identity")
    identity, is_new = obtain_identity(model, args.regenerate_smbios, args.yes)

    heading("Building and validating")
    try:
        staged = stage_efi(identity, template_raw, template_config)
        if tree_digest(SRC_EFI) != source_digest:
            raise BuildError("the source EFI/ changed during the build - this must never happen; please report it.")
        heading("Writing smbios.local and dist/EFI")
        if is_new:
            save_new_identity(identity)  # only now: the build validated, so the identity is worth keeping
        changed = publish(staged)
    finally:
        shutil.rmtree(str(STAGING_DIR), ignore_errors=True)  # holds a personalised config: never leave it behind

    recovery = None
    if args.recovery:
        heading("macOS recovery image")
        recovery = download_recovery(model)

    say("\nDone: %s%s" % (rel(DIST_EFI), "" if changed else " (unchanged)")
        + (" and %s" % rel(recovery) if recovery else ""))
    say("Copy the EFI folder to the root of a FAT32 partition (see Documentation/Installation.md).")
    say("Keep smbios.local and dist/ private: they contain your SMBIOS identity.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BuildError as error:
        print("\nerror: %s" % error, file=sys.stderr)
        print("The build did not complete.  Nothing in dist/ was replaced.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\ninterrupted.", file=sys.stderr)
        sys.exit(130)
