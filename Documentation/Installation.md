# Installation

> **Read this first.** The EFI itself is the maintainer's working configuration. The *steps* on this page are the
> standard OpenCore procedure; items marked **(general practice)** are widely used but have **not** been verified on
> the maintainer's Vostro 3520, and the maintainer has not recorded exact BIOS menu names. Back up your data and
> work with a spare drive if you can. Nothing in this project writes to a disk for you - you copy files yourself.

## 1. Build your EFI

```bash
git clone https://github.com/xiefnity/Vostro-3520-Hackintosh.git
cd Vostro-3520-Hackintosh
python3 scripts/make-efi.py --recovery     # --recovery only if you will install from Windows/Linux (about 1 GB)
```

Result: `dist/EFI` (and `dist/com.apple.recovery.boot` with `--recovery`). Never copy the repository's own `EFI/`
folder: it holds placeholders and lacks `HfsPlus.efi`. Back up `smbios.local` somewhere private.

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
4. Copy the **`EFI` folder inside `dist/`** to the root of `OPENCORE`.

### Option B - on Windows or Linux (recovery image)

1. You built with `--recovery`, so `dist/com.apple.recovery.boot` exists.
2. Format the USB drive as **GPT** with one **FAT32** partition.
3. Copy `dist/EFI` **and** `dist/com.apple.recovery.boot` to the root of that partition. It should look like:
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
2. This EFI **hides the OpenCore picker and has no timeout**, so it boots its default entry straight away. If
   it boots something you did not want (for example Windows), power off and, immediately after powering on, **hold
   Esc** (OpenCore's standard hotkey; `Option`/`Alt` is the other one). Only a short window is available:
   `TakeoffDelay` is 0.5 s. This hotkey behaviour is **(general practice)**; it has not been recorded as tested on
   this unit.
3. Choose the macOS installer / recovery entry.
4. In the installer, open *Disk Utility*, erase the target internal drive as **APFS / GUID Partition Map**, then run
   *Install macOS*. The machine restarts several times; each time, boot from the USB drive again and choose the
   installer or the new macOS disk entry as OpenCore shows it.

## 5. After installing macOS - install OpenCore on the internal drive

Boot macOS from the USB drive once, then copy `dist/EFI` to the internal drive's EFI partition so the USB drive is
no longer needed:

```bash
diskutil list                              # find the internal disk's "EFI" partition, e.g. disk0s1
sudo diskutil mount /dev/disk0s1           # use YOUR identifier from the list above
cp -R /path/to/Vostro-3520-Hackintosh/dist/EFI /Volumes/EFI/    # the folder must end up as /Volumes/EFI/EFI
```

Double-check you picked the **internal** disk's EFI partition before copying. Then set the BIOS boot order to put
the internal UEFI drive first **(general practice)**. `Misc/Boot/LauncherOption` is `Disabled`, so OpenCore does not
add itself to the firmware boot menu; the firmware has to boot the fallback `EFI/BOOT/BOOTx64.efi`.

Afterwards you should see the expected quick boot (about 10 seconds on the maintainer's unit).

## 6. Known state after install

- **Sleep/wake is unreliable and disabled; it is not supported by this project.** Choose your own power settings
  with care. Settings that keep the machine from sleeping are the safe choice; the maintainer has not published a
  recommended set.
- **Headphone jack: not confirmed.**
- Check the [status table](../README.md#project-status) for everything else.
- To confirm your own identity is active, *About This Mac → System Report* shows the serial number from
  `smbios.local`.

## 7. Updating later

- Pull new repository changes and run `python3 scripts/make-efi.py` again: your `smbios.local` is reused, so the
  identity stays the same. The previous `dist/EFI` is moved to `dist/backups/`.
- Copy the new `dist/EFI` over the EFI on your internal drive (keep the old one until the new one boots).
- Do **not** use `--regenerate-smbios` just to "refresh" things; it changes your Mac's identity for Apple's services.

## Emergency recovery

If a new EFI will not boot, boot macOS from your USB drive (which still holds the previous working EFI), or restore
the previous EFI from `dist/backups/` or your own backup. Keep a known-good copy of your internal EFI before every
change.
