# Wi-Fi and Bluetooth

**Status (maintainer-reported):** both work on the maintainer's unit. The Wi-Fi and Bluetooth modules fitted to
other Vostro 3520 units can differ; the exact module model of the maintainer's unit is not recorded here, so
**check that your card is supported before relying on this**.

## Wi-Fi - `AirportItlwm`

| | |
|---|---|
| Kext | `AirportItlwm.kext` 2.4.0 - the laobamac fork of itlwm, commit `7204c69` (config comment: "Tahoe only") |
| Limited to | Darwin **25.0.0 - 25.99.99** (`MinKernel` / `MaxKernel` in `config.plist`), i.e. macOS Tahoe only |
| Hardware | Intel Wi-Fi cards supported by the [OpenIntelWireless itlwm](https://github.com/OpenIntelWireless/itlwm) family |

`AirportItlwm` presents the card to macOS as a native Wi-Fi interface. Because the kext is restricted to Darwin 25,
**it will not load on any other macOS version**; those would need a different build and a different `config.plist`
entry. Major macOS updates can also break this kext - expect to wait for a new build.

Wi-Fi inside the macOS **installer/recovery** environment has not been verified. For installation, a wired
connection (the EFI includes `RealtekRTL8111`) or a phone tethered over USB (`HoRNDIS`) is the safer assumption.

## Bluetooth

| Kext | Version | Role |
|---|---|---|
| `IntelBluetoothFirmware.kext` | 2.5.3 | Uploads firmware to the Intel controller (config comment: USB ID **8087:0AAA**) |
| `IntelBTPatcher.kext` | 2.5.3 | Bluetooth LE event fixes |
| `BlueToolFixup.kext` | 2.7.2 | `bluetoothd` patches (from BrcmPatchRAM 2.7.2) required on current macOS for third-party controllers |

All three are enabled and must stay enabled together. The Bluetooth controller is a USB device, so it depends on
`UTBMap.kext` (the USB map): if you ever remap USB ports, keep the Bluetooth port mapped as an internal device or
Bluetooth will disappear.

`NVRAM/Add` sets `bluetoothInternalControllerInfo` and `bluetoothExternalDongleFailed` to neutral defaults on every
boot (both names are also listed in `NVRAM/Delete`, so stale values are replaced). They are shipped unchanged.

## If it does not work on your unit

- Wi-Fi: confirm your card is an Intel model supported by itlwm and that you are on Tahoe.
- Bluetooth: confirm that your controller's USB ID is `8087:0AAA` (the firmware loader in this EFI is for that
  device); another ID needs different firmware handling and is not covered here.
- Include your card/controller model and macOS version when you open an issue.
