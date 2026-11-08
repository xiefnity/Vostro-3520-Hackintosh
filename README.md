# Dell Vostro 3520 - OpenCore EFI for macOS Tahoe (Intel Iris Xe)

An OpenCore EFI for the **Dell Vostro 3520** (Intel Core i5-1235U, Iris Xe graphics) running **macOS Tahoe**,
plus a build script that gives **every user their own, freshly generated SMBIOS identity**.

> **Based on:** the EFI in this repository is built on
> [henriquejsza/Hackintosh-Vostro3520-IrisXe-Tahoe](https://github.com/henriquejsza/Hackintosh-Vostro3520-IrisXe-Tahoe)
> (which, according to its own README, is in turn based on
> [JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe](https://github.com/JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe)).
> Many thanks to both authors - see [Third-party components and license](#third-party-components-and-license).

```bash
git clone https://github.com/xiefnity/Vostro-3520-Hackintosh.git
cd Vostro-3520-Hackintosh
python3 scripts/make-efi.py          # Windows: py -3 scripts\make-efi.py
# -> dist/EFI: your personalised, validated fast-boot EFI (to install macOS first, add --installer - see below)
```

New here? Follow the [Quick start](#quick-start-after-cloning) - it walks through the whole install, including the
extra [GPU package](#gpu-acceleration-after-installing-macos) you might need after installing macOS.

> **Use at your own risk.** This is community work, provided as-is (see [LICENSE](LICENSE)). Apple's license
> restricts macOS to Apple-branded hardware; you are responsible for complying with it. Keep a backup of your
> disk before changing anything, and read [Known limitations](#known-limitations) first.

## Contents

- [Quick start (after cloning)](#quick-start-after-cloning)
- [What this project does](#what-this-project-does)
- [Project status](#project-status)
- [Build your EFI](#build-your-efi)
- [SMBIOS identity](#smbios-identity)
- [Why `smbios.local` must stay private](#why-smbioslocal-must-stay-private)
- [Install the generated EFI](#install-the-generated-efi)
- [GPU acceleration after installing macOS](#gpu-acceleration-after-installing-macos)
- [Known limitations](#known-limitations)
- [Development status](#development-status)
- [Troubleshooting build errors](#troubleshooting-build-errors)
- [Repository layout](#repository-layout)
- [Third-party components and license](#third-party-components-and-license)

## Quick start (after cloning)

**You need:** a Dell Vostro 3520 (this configuration is for that machine), an erasable USB drive, a computer to build
on (macOS, Windows or Linux) with **Git** and **Python 3.8+**, and an internet connection for the first run. Nothing
in this project writes to a drive for you - you copy the folders yourself.

1. **Clone and enter the folder** (skip this if you already have it):

   ```bash
   git clone https://github.com/xiefnity/Vostro-3520-Hackintosh.git
   cd Vostro-3520-Hackintosh
   ```

2. **Build the EFI for the install USB.** The first run creates your own private SMBIOS identity in `smbios.local`:

   ```bash
   python3 scripts/make-efi.py --installer      # Windows: py -3 scripts\make-efi.py --installer
   ```

   Add `--recovery` if you will install from Windows or Linux (it also downloads macOS, about 1 GB). To test your setup
   first, run `python3 scripts/make-efi.py --check`. The result is **`dist/installer/EFI`**.
   **Back up `smbios.local`, and never share it or anything in `dist/`.**
3. **Put it on a USB drive.** Use a GPT drive with a FAT32 partition and copy the `dist/installer/EFI` folder to its
   root (plus `dist/com.apple.recovery.boot` if you used `--recovery`). On a Mac you can instead make the installer
   from Apple's app - both ways are in [Installation](Documentation/Installation.md). In the laptop's BIOS, turn
   Secure Boot off and set the storage mode to AHCI.
4. **Boot the USB drive.** Press F12 at power-on, choose the drive's UEFI entry, pick the macOS installer in
   OpenCore's picker and install macOS Tahoe.
5. **Install the GPU package** if the GPU is not accelerated after installing:
   [WhateverXe-Graphics](#gpu-acceleration-after-installing-macos).
6. **Switch to the fast-boot EFI.** Build the normal EFI (your identity is reused) and copy `dist/EFI` to the internal
   drive's EFI partition, as described in
   [Installation, step 5](Documentation/Installation.md#5-after-installing-macos---install-opencore-on-the-internal-drive):

   ```bash
   python3 scripts/make-efi.py                  # builds dist/EFI
   ```

7. **Later:** run `git pull` and build again. `smbios.local` is reused, so your Mac keeps the same identity.

If a build stops with an error, see [Troubleshooting build errors](#troubleshooting-build-errors).

## What this project does

The repository contains a **sanitized template** of a working OpenCore EFI. The template has *placeholders*
instead of an SMBIOS identity (serial number, MLB, UUID, ROM), so nothing in this repository identifies any real
machine. `scripts/make-efi.py` turns the template into **your** EFI:

1. downloads the official OpenCore utilities (`macserial`, `ocvalidate`) and checks their SHA-256,
2. loads your identity from `smbios.local`, or generates a new one with `macserial` and saves it,
3. copies `EFI/` to a staging folder (the template itself is never modified),
4. fetches Apple's `HfsPlus.efi` from [OcBinaryData](https://github.com/acidanthera/OcBinaryData) (SHA-256 checked),
5. fills in the placeholders and verifies the result (types, values, nothing else changed, no placeholder left),
6. runs `ocvalidate` and stops if it reports anything,
7. only then writes `dist/EFI` - an existing `dist/EFI` is moved to `dist/backups/`, never deleted.

There is exactly **one** configuration, `EFI/OC/config.plist`. The script refuses to build if it finds a second
one next to it, or if the template contains anything other than placeholders.

## Project status

**macOS Tahoe on the Dell Vostro 3520**

This project is currently functional, with several hardware components working through custom OpenCore
configuration and additional kernel extensions.

### Target machine

Built and used on one specific machine. **Other Vostro 3520 units can differ** (CPU, Wi-Fi/Bluetooth module,
display panel, audio codec revision, BIOS version), so do not assume every configuration behaves identically.

| | |
|---|---|
| Laptop | Dell Vostro 3520 |
| CPU | Intel Core i5-1235U (12th gen, Alder Lake-U) |
| Graphics | Intel Iris Xe, internal eDP panel |
| OS | macOS Tahoe (Darwin 25); some kexts are limited to it |
| Boot loader | OpenCore 1.0.8 (DEBUG build, logging off), SMBIOS model `MacBookPro16,2` |

### Hardware compatibility

The status below is what the maintainer reported for their own unit; the build script can only check that the EFI
is well-formed, not that your hardware behaves the same.

| Component | Status | Notes |
|---|---|---|
| Intel Core i5-1235U | ✅ Working | 12th-generation Intel processor |
| Intel Iris Xe Graphics | ✅ Working | Hardware acceleration using WhateverXe 0.7.0 (you might also need the [WhateverXe-Graphics package](#gpu-acceleration-after-installing-macos) in macOS) - [Graphics](Documentation/Graphics.md) |
| Internal eDP Display | ✅ Working | Graphics acceleration and internal display output |
| Wi-Fi | ✅ Working | AirportItlwm, Tahoe only - [Wi-Fi & Bluetooth](Documentation/WiFi-Bluetooth.md) |
| Bluetooth | ✅ Working | IntelBluetoothFirmware, IntelBTPatcher and BlueToolFixup |
| Internal Speakers | ✅ Working | AppleALC and SimpleHDA - [Audio](Documentation/Audio.md) |
| Internal Microphone | ✅ Working | Internal microphone input |
| Headphone Jack | ⚠️ Unconfirmed | Not yet confirmed working |
| Sleep / Wake | ⚠️ Unreliable | Just disable sleep from macOS, otherwise it will freeze. This project does not attempt to fix it |
| Lid-close behaviour | ⚠️ Unverified | Requires further testing |
| Display sleep / wake | ⚠️ Untested | Requires further testing |
| Boot time | About 10 seconds | Picker hidden, no timeout, logging off, non-verbose boot |
| Keyboard, trackpad, USB, Ethernet, battery, brightness keys, NVMe | Included, **not individually verified** | See [Components](Documentation/Components.md) |

**Important:** This configuration is developed for the Dell Vostro 3520 with an Intel Core i5-1235U. Compatibility
with other hardware configurations and laptop revisions is not guaranteed.

## Build your EFI

**Requirements:** Python 3.8 or newer, an internet connection for the first run, about 200 MB of free disk
space. No `pip install` is needed ([requirements.txt](requirements.txt) lists nothing on purpose).

```bash
python3 scripts/make-efi.py                      # build dist/EFI (fast boot: the OpenCore picker is hidden)
python3 scripts/make-efi.py --installer          # build dist/installer/EFI (picker shown) - for the install USB
python3 scripts/make-efi.py --check              # check dependencies + template, trial-build, keep nothing
python3 scripts/make-efi.py --recovery           # also download the macOS recovery image (~1 GB)
python3 scripts/make-efi.py --regenerate-smbios  # NEW identity - read the warning below first
```

| Option | Meaning |
|---|---|
| *(none)* | Build `dist/EFI`. Creates `smbios.local` on the first run, reuses it afterwards. |
| `--installer` | Build `dist/installer/EFI` instead: the same EFI with the OpenCore picker **shown** (`ShowPicker=true`, `Timeout=5`) so you can choose the macOS installer. Those are the only two values that change, and the script checks that. Use it on the install USB. `dist/EFI` stays the fast-boot build and is never touched by this option. |
| `--check` | Verifies Python/OS support, downloads and verifies the OpenCore tools, validates the template and any existing `smbios.local`, then does trial builds (normal and `--installer`) with a throw-away identity. Writes nothing to `dist/` or `smbios.local`. |
| `--recovery` | Also downloads the latest macOS recovery from Apple to `dist/com.apple.recovery.boot` (for installing from Windows/Linux). Uses an all-zero MLB - your identity is not involved. |
| `--regenerate-smbios` | Replaces your identity with a new one after a confirmation (`--yes` skips the prompt). The old file is kept as `smbios.local.bak-<time>`. |
| `--sanitize FILE` | *Maintainers only:* writes the template `EFI/OC/config.plist` from a working config. See [Maintaining](Documentation/Maintaining.md). |

**Platforms.** The script picks the right OpenCore utilities for the operating system: macOS (Intel and Apple
silicon - the tools are universal binaries), Linux (x86-64 only) and Windows. It has been run by the maintainer
on **macOS only**; the Linux and Windows paths select the `.linux` / `.exe` tools from the same official release
but are untested - please report problems.

**Output.** `dist/installer/EFI` is the folder for the install USB and `dist/EFI` is the one for the internal drive
afterwards. Both are ordinary `EFI` folders, so you copy them as they are. The build never writes to any drive itself.

## SMBIOS identity

macOS and Apple's online services identify a Mac by its **SMBIOS identity**. OpenCore must present one:

| Field | Where it goes | How it is created |
|---|---|---|
| `SystemSerialNumber` | `PlatformInfo/Generic` (string) | `macserial -m <model> -g` - the serial is decoded again to confirm it belongs to the same model |
| `MLB` (board serial) | `PlatformInfo/Generic` (string) | same `macserial` call |
| `SystemUUID` | `PlatformInfo/Generic` (string) | Python `uuid.uuid4()`, upper-case |
| `ROM` | `PlatformInfo/Generic` (**data, exactly 6 bytes**) | 6 random bytes from Python `secrets`, marked as a locally administered unicast address |
| `SystemProductName` | not generated | stays as in the template: `MacBookPro16,2` |

**How it behaves**

- **First run:** the identity is generated, built and validated; only after the build succeeds is it saved to
  `smbios.local` (permissions `600` where the OS supports it).
- **Later runs:** `smbios.local` is read and **reused**, so you get the same identity every time.
- **Incomplete or invalid `smbios.local`:** the script stops with a list of what is wrong. It never quietly
  generates a replacement.
- **Model mismatch:** if `smbios.local` was made for a different `SystemProductName` than the template uses, the
  script stops - serials are model-specific.
- **`--regenerate-smbios`:** the only way to get a new identity. A failed build keeps your old one.
- **Nothing is transmitted.** The only network traffic is downloading public files (OpenCore release, `HfsPlus.efi`,
  and with `--recovery` Apple's recovery servers, using a zero MLB).

> **Warning - changing the identity affects Apple services.** iCloud, iMessage, FaceTime, App Store and Find My
> associate your Mac with its serial/MLB/UUID/ROM. A new identity looks like a different Mac: you may have to sign
> out and in again and re-register iMessage/FaceTime. Only regenerate if you mean to.

**`smbios.local` format** (plain text, one `KEY=VALUE` per line, `#` for comments; ROM is 12 hex digits):

```
SystemProductName=MacBookPro16,2
SystemSerialNumber=<12 letters/digits>
MLB=<17 letters/digits>
SystemUUID=<8-4-4-4-12 hex digits>
ROM=<12 hex digits>
```

**Bring your own identity.** If you already run macOS with an identity you want to keep (to preserve your iMessage
registration, say), create `smbios.local` yourself in this format *before* the first build; the script validates
and reuses it. The tool never reads identities from other files.

**Generated serials.** `macserial` produces serials that *look* real, so it is good practice to check your serial
yourself on Apple's *Check Coverage* page and make sure it is **not** registered to a real Mac (if Apple shows
purchase or coverage information for it, run `--regenerate-smbios`). That check is optional and manual: typing the
serial into Apple's site is your own decision - the script never sends it anywhere.

## Why `smbios.local` must stay private

- It is **your Mac's identity**. Anyone who has it can configure another machine with the same serial, MLB, UUID and
  ROM; two machines claiming one identity confuse Apple's services and can break iMessage/FaceTime for you.
- Once pushed to a public repository it is effectively permanent (forks, clones, caches, search indexes), even if you
  delete the commit later.
- It is why this project has a template at all: **no real identity may ever appear in the repository.**

`.gitignore` already excludes `smbios.local*`, `dist/`, `build/`, logs, archives, diagnostics, extra `*.plist`
variants and backup folders. Your personalised `dist/EFI/OC/config.plist` also contains the identity: treat the
whole of `dist/` as private, and **never paste `smbios.local`, `dist/` contents, OpenCore logs or SysReport output
into issues** without checking them first.

Do not copy `EFI/` straight from the repository to a drive: the template deliberately contains placeholders
and is missing `HfsPlus.efi`. Always use the output of the script.

## Install the generated EFI

The short version: build with **`--installer`** and put the resulting **`dist/installer/EFI`** folder at the root of a
FAT32 partition on a GPT-formatted USB drive; boot it, install macOS, then build normally and copy **`dist/EFI`**
to the internal EFI partition.
The full walk-through - installer USB on macOS or via `--recovery` on Windows/Linux, BIOS settings, post-install
steps - is in **[Documentation/Installation.md](Documentation/Installation.md)**.

Why two builds: the normal EFI is tuned for a fast boot - the OpenCore boot picker is **hidden** and the timeout is
**0**, so it boots its default entry at once. That is what you want day to day, but not while installing, when you
must be able to choose the installer. `--installer` shows the picker (5 s timeout) and changes nothing else. With the
normal EFI you can still reach the picker by holding a key such as **Esc** right after powering on (OpenCore's
standard hotkey; the window is short and not tested on this laptop). The default boot is also **not verbose**.

## GPU acceleration after installing macOS

**You might have to install the [WhateverXe-Graphics](https://github.com/b00t0x/WhateverXe-Graphics/releases)
package after installing macOS to get the GPU working.**

Graphics acceleration has two parts that belong together: the `WhateverXe` kext, which is already inside this EFI, and
the WhateverXe-Graphics package, which is installed *inside macOS* (under `/Library`) and is **not** part of this
repository. WhateverXe's own installation steps include it: you install the latest Graphics package from within macOS
and then restart. In short:

1. Install macOS and boot it with this EFI. The package needs **macOS Tahoe 26.7 or newer**.
2. Download `WhateverXe-Graphics-<version>.pkg` (and `SHA256SUMS`) from the
   [Releases page](https://github.com/b00t0x/WhateverXe-Graphics/releases) and open the package. Its README says it is
   unsigned and not notarized, so macOS will warn before opening it. Restart once the installation succeeds.
3. To remove it again, run `sudo bash uninstall.sh` (the script from the same project) and restart.

The steps, the checksum check and the requirements are in
[Installation, step 6](Documentation/Installation.md#6-gpu-acceleration-after-installing-macos). One thing to know: this
EFI ships WhateverXe 0.7.0 while newer releases exist - see the version note in
[Graphics](Documentation/Graphics.md#after-installing-macos-the-whateverxe-graphics-package).

## Known limitations

- **Sleep/wake is unreliable - disable sleep in macOS as a workaround**, otherwise the machine freezes. Not fixed,
  not attempted here.
- **Headphone jack not confirmed working.** The internal speakers and internal microphone are the maintainer-reported
  working cases.
- **Opening the App Store sometimes freezes the device**, for reasons not yet understood (maintainer-reported).
- **Do not turn the volume all the way up.** Sound works, but maximum volume can produce crackling noises
  (maintainer-reported).
- **Lid-close behaviour and display sleep/wake are untested.**
- **Tahoe only.** `AirportItlwm` and `SimpleHDA` are restricted to Darwin 25.x in `config.plist`; other macOS
  versions need different builds and are unsupported.
- **Graphics depends on WhateverXe 0.7.0**, a third-party Lilu plug-in, and on a modified AMFIPass (the config
  comments say WhateverXe requires it). The EFI also runs with a reduced SIP setting (`csr-active-config`
  `0x0803`, which WhateverXe's own README calls for) and `SecureBootModel=Disabled`. After installing macOS you may
  also need the separate [WhateverXe-Graphics package](#gpu-acceleration-after-installing-macos). See
  [Graphics](Documentation/Graphics.md).
- **One tested unit.** Different Wi-Fi/Bluetooth modules, panels, BIOS versions or codec revisions may behave
  differently or not work.
- **Untested here:** Linux and Windows builds, Apple-silicon Macs as the build machine, and the features marked
  "not individually verified" in the table above.
- **No dual-boot guidance.** The normal EFI hides the picker (build with `--installer` to get one, or hold Esc at
  power-on); see Installation.
- **Debug OpenCore binaries.** The shipped OpenCore files are the official 1.0.8 DEBUG build with logging turned off.

## Development status

The working EFI configuration has been established, and the sanitized template and build script are published in
this repository.

Done:

- Sanitized the EFI configuration and removed personal identifiers (the template holds placeholders instead of an
  SMBIOS identity).
- Automated Python EFI build script (`scripts/make-efi.py`).
- Unique SMBIOS values are generated locally for each user.
- Installation instructions and hardware documentation (`Documentation/`).

Still to do:

- **Boot-test a freshly generated EFI on real hardware.** A generated EFI passes `ocvalidate` and was compared file
  by file with the maintainer's working EFI (only the four SMBIOS values differ), but booting a generated build has
  not been tested yet.
- Test the build script on Linux and Windows.

## Troubleshooting build errors

| Message (shortened) | Meaning and fix |
|---|---|
| `Python 3.8 or newer is required` | Install a current Python 3 from python.org or your package manager. |
| `could not download ...` | No network, proxy, or certificate problem. On python.org Python for macOS run *Install Certificates.command*. The script retries with `curl` automatically if it exists. |
| `SHA-256 mismatch for ...` | The download did not match the pinned hash and was **discarded**. Retry; if it persists do not continue - report it. |
| `cannot run macserial / ocvalidate` | Unsupported platform (for example ARM Linux) or a security tool blocking the binary. See [Troubleshooting](Documentation/Troubleshooting.md). |
| `smbios.local is incomplete or invalid` | The listed lines are wrong. Fix them by hand. Nothing was changed. Only use `--regenerate-smbios` if you want a brand-new identity. |
| `smbios.local was created for <model> but the EFI template uses <model>` | The identity belongs to another Mac model. Use the matching template or `--regenerate-smbios`. |
| `template PlatformInfo/Generic/... is not the placeholder` | `EFI/OC/config.plist` was edited and now holds real values. Restore it with `git checkout -- EFI/OC/config.plist`. |
| `EFI/OC must contain exactly one configuration` | Another `*.plist` sits next to `config.plist`. Move it out of the repository. |
| `config.plist refers to files that are not in the EFI` | A kext/driver/table the config enables is missing from `EFI/`. Restore it. |
| `ocvalidate rejected the generated config.plist` | The printed lines say what is wrong. Nothing in `dist/` was replaced. |
| `the source EFI/ changed during the build` | Something modified `EFI/` while the script ran. Re-run; if it repeats, report it. |

More cases, and boot-time problems, are in **[Documentation/Troubleshooting.md](Documentation/Troubleshooting.md)**.

## Repository layout

```
Vostro-3520-Hackintosh/
├── EFI/                      sanitized template (placeholders instead of an identity)
│   ├── BOOT/BOOTx64.efi
│   └── OC/
│       ├── ACPI/             SSDTs
│       ├── Drivers/          OpenRuntime, ResetNvramEntry (HfsPlus.efi is added at build time)
│       ├── Kexts/
│       ├── Resources/
│       ├── OpenCore.efi
│       └── config.plist      the only configuration
├── scripts/make-efi.py       the build script
├── tests/                    offline unit tests (python3 -m unittest discover tests)
├── Documentation/            Installation, Graphics, Audio, WiFi-Bluetooth, Components, Troubleshooting, Maintaining
├── LICENSE  NOTICE.md  licenses/   TSNPL 1.0, attribution notices, GPL texts for bundled GPL kexts
├── .gitignore  .gitattributes  requirements.txt  README.md
├── smbios.local              (you, local, git-ignored)
├── dist/                     (output, git-ignored)
└── build/                    (downloads and staging, git-ignored)
```

## Third-party components and license

**License.** This repository is licensed under the **[Thou Shalt Not Profit License 1.0](LICENSE)**, the license of
the EFI it is built on: free to use, study, modify and share, **for non-profit purposes only**. Anyone who distributes
this repository or a modified version must keep that license, keep the notices in [NOTICE.md](NOTICE.md) and mark
their own changes (section 6). Sections 17 and 18 also tie distribution to a non-profit declaration - read the
[license](LICENSE) before redistributing.

The binaries in `EFI/` (OpenCore, drivers, kexts, ACPI tables) belong to their respective authors and keep their own
licenses (some are GPL - see [NOTICE.md](NOTICE.md) and [licenses/](licenses/));
[Documentation/Components.md](Documentation/Components.md) lists every component with its version.
`HfsPlus.efi` is Apple's driver, fetched from OcBinaryData at build time and not redistributed here.

**Origin.** The EFI is built on
[henriquejsza/Hackintosh-Vostro3520-IrisXe-Tahoe](https://github.com/henriquejsza/Hackintosh-Vostro3520-IrisXe-Tahoe),
which according to its own README is based on
[JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe](https://github.com/JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe).
What this repository changed compared with it is listed in [NOTICE.md](NOTICE.md).

Thanks to the Acidanthera team (OpenCore, Lilu, VirtualSMC, AppleALC, ...), the OpenIntelWireless project, and the
authors of WhateverXe, AMFIPass and the other kexts this EFI depends on.
