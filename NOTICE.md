# Notices and attribution

This repository is licensed under the **Thou Shalt Not Profit License 1.0** ([LICENSE](LICENSE)). That license
requires derivative works to keep it, to retain the notices of the original work, and to carry a prominent notice
that the original work was modified (section 6). This file is that notice.

## Origin and modifications

The EFI in this repository is a **modified version** of
[henriquejsza/Hackintosh-Vostro3520-IrisXe-Tahoe](https://github.com/henriquejsza/Hackintosh-Vostro3520-IrisXe-Tahoe).
According to that repository's `NOTICE.md`, it is in turn a modified version of
[JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe](https://github.com/JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe)
(commit `6b5f049`), which derives from [NootedGreen](https://github.com/sgiammori/NootedGreen) by StezzaPilot. All of
them are distributed under the Thou Shalt Not Profit License 1.0.

Compared by file hash with the henriquejsza `EFI/` folder on 2026-11-08, **136 of the 154 files in this repository's
`EFI/` are byte-identical** to it. The differences are:

- **`EFI/OC/config.plist`** differs. It is the maintainer's working configuration, with Wi-Fi, Bluetooth, audio
  (AppleALC and SimpleHDA) and graphics acceleration through WhateverXe enabled, and with the SMBIOS identity replaced
  by placeholders that `scripts/make-efi.py` fills in. The two other configurations of the original (`config-accel.plist`,
  `config-install.plist`) are not included; this repository has exactly one configuration.
- **Kexts added** (not in the original): `AMFIPass`, `AirportItlwm`, `AppleALC`, `BlueToolFixup`, `IntelBTPatcher`,
  `IntelBluetoothFirmware`, `SimpleHDA` and `WhateverXe`.
- **Scripts, tests and documentation:** `scripts/make-efi.py` is a rewrite of the original `make-efi.py` (a new
  program with the same purpose, adapted from it), and the tests and the documentation in `Documentation/` were
  written for this repository.

## Third-party components

These statements about the components that came with the original EFI are taken from the original repository's
`NOTICE.md`. The binaries are shipped unmodified from their projects unless stated otherwise.

- **`EFI/OC/Kexts/NootedGreen.kext`** - the binary of the NootedGreen project at commit `6b5f049` of
  JulioNectar/Hackintosh-XPS13Plus-IrisXe-Tahoe, unmodified (TSNPL 1.0). Source: `src/NootedGreen` in that repository
  at that commit. It is shipped but **disabled** in `config.plist`.
- **`EFI/OC/Kexts/RealtekRTL8111.kext`** - release v3.0.0 of
  [Mieze/RTL8111_driver_for_OS_X](https://github.com/Mieze/RTL8111_driver_for_OS_X), unmodified, under the
  **GNU GPL v2 or later** ([licenses/GPL-2.0.txt](licenses/GPL-2.0.txt)). Source: tag `v3.0.0` of that repository.
- **`EFI/OC/Kexts/HoRNDIS.kext`** - release rel9.2 of [jwise/HoRNDIS](https://github.com/jwise/HoRNDIS) (extracted
  from `HoRNDIS-9.2.pkg`), unmodified, under the **GNU GPL v3** ([licenses/GPL-3.0.txt](licenses/GPL-3.0.txt)).
  Source: tag `rel9.2` of that repository.
- **`EFI/OC/Kexts/UTBMap.kext`** - the USB map of this laptop for USBToolBox, made for the original repository.
- **`EFI/OC/Kexts/XHCI-unsupported.kext`** - RehabMan, GNU GPL v2 ([licenses/GPL-2.0.txt](licenses/GPL-2.0.txt)).
- **All other components that came with the original EFI** keep their own licenses: OpenCore, Lilu, WhateverGreen,
  VirtualSMC and its SMC plug-ins, NVMeFix, RestrictEvents, BrightnessKeys and CpuTopologyRebuild (Acidanthera and
  contributors); VoodooI2C and VoodooPS2 (their authors); USBToolBox (dhinakg).
- **The kexts added in this repository** (`AMFIPass`, `AirportItlwm`, `AppleALC`, `BlueToolFixup`, `IntelBTPatcher`,
  `IntelBluetoothFirmware`, `SimpleHDA`, `WhateverXe`) are the work of their own authors and keep their own licenses,
  several of which are copyleft. This repository has not itemized their license texts or source locations: check each
  project's repository before redistributing them. [Documentation/Components.md](Documentation/Components.md) lists
  the version of each. The one source location known here: `WhateverXe` is
  [b00t0x/WhateverXe](https://github.com/b00t0x/WhateverXe) (BSD-3-Clause according to GitHub). Its companion macOS
  package [WhateverXe-Graphics](https://github.com/b00t0x/WhateverXe-Graphics) is **not** included in this repository.

## Not included

- **No Apple software is included.** `HfsPlus.efi` and the macOS recovery image are downloaded by
  `scripts/make-efi.py` on your own machine.
- Apple, macOS and Metal are trademarks of Apple Inc. This project is not affiliated with Apple, Intel or Dell.
