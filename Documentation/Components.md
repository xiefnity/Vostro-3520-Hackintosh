# Components

Every third-party file shipped in `EFI/`, with the version read from the file itself and its state in
`EFI/OC/config.plist`. These binaries belong to their authors and keep their own licenses (see [NOTICE.md](../NOTICE.md)); the repository's
own files - script, tests, documentation and config template - are under the Thou Shalt Not Profit License 1.0
([LICENSE](../LICENSE)).

Versions come from each kext's `Info.plist` / the OpenCore release; "State" and "Kernel range" come from
`config.plist`. Kexts load in the order shown (order matters: Lilu first, WhateverXe after Lilu).

## OpenCore

| File | Version | Notes |
|---|---|---|
| `EFI/BOOT/BOOTx64.efi` | 1.0.8 **DEBUG** | Byte-identical to the official `OpenCore-1.0.8-DEBUG` release |
| `EFI/OC/OpenCore.efi` | 1.0.8 **DEBUG** | Same. `Misc/Debug/Target` is `0`, so no log is produced |
| `EFI/OC/Drivers/OpenRuntime.efi` | 1.0.8 **DEBUG** | Same |
| `EFI/OC/Drivers/ResetNvramEntry.efi` | not identified | Matches neither the 1.0.8 RELEASE/DEBUG builds nor the 1.0.6/1.0.7 DEBUG builds; its origin was not recorded |
| `EFI/OC/Drivers/HfsPlus.efi` | OcBinaryData commit `c2a98980` | **Not in this repository.** Apple's driver; downloaded by the script and checked against a pinned SHA-256 |
| `EFI/OC/Resources/` | - | Standard OpenCore fonts/images/labels (unused while the picker is hidden) |

`ocvalidate` only accepts the OpenCore version it was built with, so the script pins **OpenCore 1.0.8**
(`OC_VERSION` in `scripts/make-efi.py`). Change the OpenCore binaries and that pin together - see
[Maintaining](Maintaining.md).

## Kexts (`config.plist` → `Kernel/Add`)

| # | Kext | Version | State | Kernel range | Purpose |
|---|---|---|---|---|---|
| 1 | `Lilu.kext` | 1.7.3 | **on** | any | Patching framework required by most of the plug-ins below |
| 2 | `WhateverXe.kext` | 0.7.0 | **on** | any | Iris Xe (Alder Lake) graphics acceleration; must load after Lilu |
| 3 | `AMFIPass.kext` | 1.4.1 | **on** | any | AMFI bypass; modified build that WhateverXe requires (per config comment) |
| 4 | `BrightnessKeys.kext` | 1.0.4 | **on** | any | Brightness hot-keys |
| 5 | `CpuTopologyRebuild.kext` | 2.0.2 | off | any | Hybrid P/E-core topology fix |
| 6 | `NVMeFix.kext` | 1.1.4 | **on** | >= 18.0.0 | NVMe power-management / compatibility fixes |
| 7 | `RestrictEvents.kext` | 1.1.7 | **on** | any | Used here for the CPU name (NVRAM `revcpu`, `revcpuname`, `revpatch`) |
| 8 | `VirtualSMC.kext` | 1.3.9 | **on** | any | SMC emulation |
| 9 | `SMCBatteryManager.kext` | 1.3.9 | **on** | any | Battery status |
| 10 | `SMCDellSensors.kext` | 1.3.9 | off | any | Dell fan / sensor readout |
| 11 | `SMCLightSensor.kext` | 1.3.9 | off | any | Ambient light sensor |
| 12 | `SMCProcessor.kext` | 1.3.9 | **on** | any | CPU temperature / power sensors |
| 13 | `SMCSuperIO.kext` | 1.3.9 | off | any | Super-I/O sensors |
| 14 | `USBToolBox.kext` | 1.2.0 | **on** | any | USB mapping driver |
| 15 | `UTBMap.kext` | 1.1 | **on** | any | USB port map for this laptop (xHCI 8086:51ED) |
| 16 | `VoodooI2C.kext/…/VoodooI2CServices.kext` | 1.0 | **on** | any | VoodooI2C helper (I2C-HID stack) |
| 17 | `VoodooI2C.kext/…/VoodooGPIO.kext` | 1.2 | **on** | any | VoodooI2C helper (GPIO controller) |
| 18 | `VoodooI2C.kext` | 2.9.1 | **on** | any | I2C bus controller (I2C-HID devices) |
| 19 | `VoodooI2C.kext/…/VoodooInput.kext` | 1.1.7 | **on** | any | Multitouch input layer |
| 20 | `VoodooI2CHID.kext` | 1.0 | **on** | any | I2C-HID device driver (touchpad) |
| 21 | `VoodooPS2Controller.kext` | 2.3.8 | **on** | any | PS/2 controller (keyboard, trackpad) |
| 22 | `VoodooPS2Controller.kext/…/VoodooInput.kext` | 1.1.7 | off | any | Second copy of VoodooInput, disabled (the one inside VoodooI2C, #19, is loaded) |
| 23 | `VoodooPS2Controller.kext/…/VoodooPS2Keyboard.kext` | 2.3.8 | **on** | any | PS/2 keyboard |
| 24 | `VoodooPS2Controller.kext/…/VoodooPS2Mouse.kext` | 2.3.8 | **on** | any | PS/2 mouse |
| 25 | `VoodooPS2Controller.kext/…/VoodooPS2Trackpad.kext` | 2.3.8 | **on** | any | PS/2 trackpad |
| 26 | `WhateverGreen.kext` | 1.7.2 | off | any | Standard graphics patcher - **disabled; must never load together with WhateverXe** (config comment) |
| 27 | `NootedGreen.kext` | 1.0.0 | off | >= 25.0.0 | Alternative iGPU kext - **disabled; must never load together with WhateverXe** (config comment) |
| 28 | `XHCI-unsupported.kext` | 0.9.2 | **on** | any | Injector for the unsupported xHCI controller |
| 29 | `RealtekRTL8111.kext` | 3.0.0 | **on** | any | Ethernet (config comment: RTL8168) |
| 30 | `HoRNDIS.kext` | 9.2 | **on** | any | USB tethering from a phone (RNDIS) |
| 31 | `AirportItlwm.kext` | 2.4.0 | **on** | 25.0.0 - 25.99.99 | Intel Wi-Fi - itlwm fork by laobamac, commit `7204c69`; Tahoe only |
| 32 | `BlueToolFixup.kext` | 2.7.2 | **on** | any | bluetoothd patches (from BrcmPatchRAM 2.7.2) |
| 33 | `IntelBluetoothFirmware.kext` | 2.5.3 | **on** | any | Uploads firmware to the Intel Bluetooth controller (USB 8087:0AAA, per config comment) |
| 34 | `IntelBTPatcher.kext` | 2.5.3 | **on** | any | Bluetooth LE event fixes |
| 35 | `AppleALC.kext` | 1.9.9 | **on** | any | Audio: controller patch only - config comment: "No CS8409 layout exists" |
| 36 | `SimpleHDA.kext` | 1.0.1 | **on** | 25.0.0 - 25.99.99 | Audio: restores AppleHDA 600.2 behaviour (config comment); Tahoe only |

"Kernel range" is the Darwin version: 25.x is macOS Tahoe. Kexts that are present but **off** are intentionally
kept in the folder and do nothing; do not enable `WhateverGreen` or `NootedGreen` next to `WhateverXe`.

Upstream projects (only those the maintainers could confirm): [OpenCorePkg](https://github.com/acidanthera/OpenCorePkg),
[OcBinaryData](https://github.com/acidanthera/OcBinaryData), [Lilu](https://github.com/acidanthera/Lilu),
[VirtualSMC](https://github.com/acidanthera/VirtualSMC), [AppleALC](https://github.com/acidanthera/AppleALC),
[WhateverGreen](https://github.com/acidanthera/WhateverGreen),
[RestrictEvents](https://github.com/acidanthera/RestrictEvents), [NVMeFix](https://github.com/acidanthera/NVMeFix),
[BrightnessKeys](https://github.com/acidanthera/BrightnessKeys),
[VoodooPS2](https://github.com/acidanthera/VoodooPS2), [VoodooI2C](https://github.com/VoodooI2C/VoodooI2C),
[USBToolBox](https://github.com/USBToolBox/kext), [HoRNDIS](https://github.com/jwise/HoRNDIS),
[OpenIntelWireless](https://github.com/OpenIntelWireless). WhateverXe, the modified AMFIPass, SimpleHDA,
NootedGreen and the itlwm fork are third-party projects identified only by their bundle identifiers
(`org.b00t0x.WhateverXe`, `cn.laobamac.SimpleHDA`, ...); check their authors' pages for their licenses.

## ACPI (`EFI/OC/ACPI/`, all enabled)

| File | What it does (from the table's own AML) |
|---|---|
| `SSDT-ALS0.aml` | Ambient light sensor device (`ACPI0008`) |
| `SSDT-SBUS.aml` | SMBus device under `PC00` |
| `SSDT-EC.aml` | Embedded-controller device macOS expects (`ACID0001`) |
| `SSDT-MCHC.aml` | Memory-controller host device under `PC00` |
| `SSDT-PLUG-ALT.aml` | CPU power-management `plugin-type` for processors defined under `\_SB` |
| `SSDT-PNLF.aml` | Backlight device (`PNLF`) under `GFX0` |
| `SSDT-RTCAWAC.aml` | RTC / AWAC clock setting |
| `SSDT-USB-Reset.aml` | Hides the xHCI root hub (`RHUB`) - the config comment confirms this is its job |
| `SSDT-USBX.aml` | USB power properties |
| `SSDT-XOSI.aml` | `_OSI` shim; used together with the two ACPI patches below |

ACPI patches in `config.plist` (both enabled): `OSID` → `XSID`, then `_OSI` → `XOSI` (the order matters). One
`ACPI/Delete` entry exists but is disabled (the config comment says the Dell `xh_Dell_` SSDT is kept on purpose).
