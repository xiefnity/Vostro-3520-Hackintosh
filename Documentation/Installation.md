# Installation

> **Read this first.** The EFI itself is the maintainer's working configuration. The *steps* on this page are the
> standard OpenCore procedure; items marked **(general practice)** are widely used but have **not** been verified on
> the maintainer's Vostro 3520, and the maintainer has not recorded exact BIOS menu names. Back up your data and
> work with a spare drive if you can. Nothing in this project writes to a disk for you - you copy files yourself.

## 1. Build your EFI

```bash
git clone https://github.com/xiefnity/Vostro-3520-Hackintosh.git
cd Vostro-3520-Hackintosh
python3 scripts/make-efi.py --installer    # dist/installer/EFI - for the install USB (shows the OpenCore picker)
python3 scripts/make-efi.py                # dist/EFI - for the internal drive after the install (fast boot)
python3 scripts/make-efi.py --recovery     # --recovery only if you will install from Windows/Linux (about 1 GB)
```

You get **two** EFI folders with the **same** SMBIOS identity (`smbios.local` is shared):

| Folder | Use it for | OpenCore picker |
|---|---|---|
| `dist/installer/EFI` | the install USB | **shown**, 5 s timeout, so you can choose the installer |
| `dist/EFI` | the internal drive once macOS is installed | hidden, no timeout (fast boot) |

They differ in exactly two config values (`Misc/Boot/ShowPicker` and `Timeout`); the script verifies that. With
`--recovery` you also get `dist/com.apple.recovery.boot`. Never copy the repository's own `EFI/` folder: it holds
placeholders and lacks `HfsPlus.efi`. Back up `smbios.local` somewhere private.

## 2. BIOS settings (general practice)

Typical requirements for OpenCore on Intel laptops; check the equivalent options in the Vostro 3520 BIOS (press
**F2** at power-on):

- **Secure Boot: off.**
- **UEFI boot mode** (no legacy / CSM).
- **Storage mode: AHCI** rather than RAID / Intel RST, otherwise macOS cannot see the NVMe drive.
- Leave other options at their defaults unless you have a reason; if you find a setting that is required on this
  laptop, please contribute it.

`config.plist` enables `AppleXcpmCfgLock`, so no CFG-Lock BIOS change is needed.

## 3. Prepare the USB drive

Use a USB drive you can erase, with a **GPT** partition table.

### Option A - on a Mac (installer from Apple)

1. Download *Install macOS Tahoe* from the App Store.
2. In Disk Utility, partition the USB drive into two partitions: a small one (about 1 GB) formatted
   **MS-DOS (FAT)** named `OPENCORE`, and a second one (about 16 GB or more) formatted *Mac OS Extended (Journaled)*
   named `INSTALL`.
3. Make the installer on the second partition:
   ```bash
   sudo /Applications/Install\ macOS\ Tahoe.app/Contents/Resources/createinstallmedia --volume /Volumes/INSTALL
   ```
4. Copy the **`dist/installer/EFI`** folder (the installer build) to the root of `OPENCORE`.

### Option B - on Windows or Linux (recovery image)

1. You built with `--recovery`, so `dist/com.apple.recovery.boot` exists.
2. Format the USB drive as **GPT** with one **FAT32** partition.
3. Copy `dist/installer/EFI` (the installer build) **and** `dist/com.apple.recovery.boot` to the root of that
   partition. It should look like:
   ```
   EFI/BOOT/BOOTx64.efi
   EFI/OC/...
   com.apple.recovery.boot/BaseSystem.dmg
   ```
4. This installs macOS online from Apple's servers, so you need a network connection during installation (see
   [Wi-Fi & Bluetooth](WiFi-Bluetooth.md): Wi-Fi in the installer is not verified; wired is the safer choice).

## 4. Boot the installer

1. Plug in the USB drive, power on and press **F12** (Dell one-time boot menu) and choose the USB drive's **UEFI**
   entry.
2. OpenCore shows its **boot picker** (this is the `--installer` build; if you used the normal `dist/EFI` instead,
   the picker is hidden and the default entry boots straight away - then power off and, immediately after powering
   on, **hold Esc**, OpenCore's standard hotkey; `Option`/`Alt` is the other one. That hotkey behaviour is
   **(general practice)**; it has not been recorded as tested on this unit).
3. Choose the macOS installer / recovery entry. If you do nothing, the picker boots its default entry after 5 s.
4. In the installer, open *Disk Utility*, erase the target internal drive as **APFS / GUID Partition Map**, then run
   *Install macOS*. The machine restarts several times; each time, boot from the USB drive again and choose the
   installer or the new macOS disk entry as OpenCore shows it.

## 5. After installing macOS - install OpenCore on the internal drive

Boot macOS from the USB drive once, then copy `dist/EFI` (the normal, fast-boot build - **not** `dist/installer/EFI`)
to the internal drive's EFI partition so the USB drive is no longer needed:

```bash
diskutil list                              # find the internal disk's "EFI" partition, e.g. disk0s1
sudo diskutil mount /dev/disk0s1           # use YOUR identifier from the list above
cp -R /path/to/Vostro-3520-Hackintosh/dist/EFI /Volumes/EFI/    # the folder must end up as /Volumes/EFI/EFI
```

Double-check you picked the **internal** disk's EFI partition before copying. Then set the BIOS boot order to put
the internal UEFI drive first **(general practice)**. `Misc/Boot/LauncherOption` is `Disabled`, so OpenCore does not
add itself to the firmware boot menu; the firmware has to boot the fallback `EFI/BOOT/BOOTx64.efi`.

Afterwards you should see the expected quick boot (about 10 seconds on the maintainer's unit).

## 6. GPU acceleration after installing macOS

**You might have to install the [WhateverXe-Graphics](https://github.com/b00t0x/WhateverXe-Graphics/releases) package
after installing macOS to get the GPU working.** The `WhateverXe` kext in this EFI is only half of the graphics
setup; the package supplies the signed graphics driver files that macOS itself needs. The steps below are that
project's own (from its README) - this repository does not ship, download or verify the package.

1. **Be on macOS Tahoe 26.7 or newer** (the package's stated minimum) and boot with this EFI. Either build works:
   both contain WhateverXe, the modified AMFIPass and the SIP setting `csr-active-config` = `0x803` that the package
   requires. Update macOS first if your installer was older.
2. **Download** `WhateverXe-Graphics-<version>.pkg` and `SHA256SUMS` from the latest release on the
   [Releases page](https://github.com/b00t0x/WhateverXe-Graphics/releases).
3. **Check the download** (sensible, optional): the hash from this command must match the line for the `.pkg` in
   `SHA256SUMS`:
   ```bash
   shasum -a 256 ~/Downloads/WhateverXe-Graphics-*.pkg
   ```
4. **Open the package.** Its README says it is unsigned and not notarized, so macOS will warn before opening it; you
   have to allow it yourself (usually *System Settings → Privacy & Security → Open Anyway* **(general macOS
   behaviour)**). If the installer reports an error, resolve it before restarting.
5. **Restart** once the installation succeeds. Afterwards you can look at *System Report → Graphics/Displays* to see
   whether the GPU is listed with Metal support **(general macOS behaviour; what it shows on this GPU has not been
   recorded here)**.
6. **To remove it again:** download the project's `uninstall.sh`, run `sudo bash uninstall.sh` and restart. It
   removes the package's graphics files and leaves the EFI alone.

The project also describes an experimental *AutoPkg* way to apply the package during a fresh install. It needs an
extra OpenCore kext (AutoPkgInstaller) that this EFI does not include, and it has not been tried here.

More about the requirements and a note on version pairing: [Graphics](Graphics.md#after-installing-macos-the-whateverxe-graphics-package).

## 7. Known state after install

- **Sleep/wake is unreliable and disabled; it is not supported by this project.** Choose your own power settings
  with care. Settings that keep the machine from sleeping are the safe choice; the maintainer has not published a
  recommended set.
- **Headphone jack: not confirmed.**
- Check the [status table](../README.md#project-status) for everything else.
- To confirm your own identity is active, *About This Mac → System Report* shows the serial number from
  `smbios.local`.

## 8. Updating later

- Pull new repository changes and run `python3 scripts/make-efi.py` again: your `smbios.local` is reused, so the
  identity stays the same. The previous `dist/EFI` is moved to `dist/backups/`.
- Copy the new `dist/EFI` over the EFI on your internal drive (keep the old one until the new one boots).
- Do **not** use `--regenerate-smbios` just to "refresh" things; it changes your Mac's identity for Apple's services.

## Emergency recovery

If a new EFI will not boot, boot macOS from your USB drive (which still holds the previous working EFI), or restore
the previous EFI from `dist/backups/` or your own backup. Keep a known-good copy of your internal EFI before every
change.
