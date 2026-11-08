# Graphics (Intel Iris Xe, internal eDP display)

**Status (maintainer-reported):** graphics acceleration and the internal eDP display work on the maintainer's
Vostro 3520. This repository treats that configuration as a known-good unit: it is shipped **exactly as it was
working**, and the build script never touches it.

## What provides graphics

| Piece | Where | Notes |
|---|---|---|
| **WhateverXe 0.7.0** (`org.b00t0x.WhateverXe`) | `Kernel/Add` #2, enabled | Iris Xe (Alder Lake) acceleration. Needs Lilu (it declares Lilu ≥ 1.2.0; the EFI has 1.7.3) and must load **after** Lilu. |
| **AMFIPass 1.4.1 (modified build)** | `Kernel/Add` #3, enabled | The config comment says WhateverXe requires this build - do not replace it with upstream AMFIPass. |
| `WhateverGreen`, `NootedGreen` | `Kernel/Add` #26, #27, **disabled** | Present in the folder but off. The config comments say they must **never** load together with WhateverXe. |
| Backlight | `SSDT-PNLF.aml` + `BrightnessKeys.kext` | PNLF device under `GFX0`; brightness hot-keys. |
| Boot arguments | `NVRAM/Add/7C436110-…/boot-args` | See below. |

There are **no GPU entries in `DeviceProperties`** (no `AAPL,ig-platform-id`, no framebuffer patches): the only
device property in the whole config is the audio `layout-id`. The display setup is handled inside WhateverXe.

### Boot arguments (as shipped)

```
keepsyms=1 -vi2c-force-polling -allow3d -disablegfxfirmware -wexdbg
```

| Argument | Belongs to | Note |
|---|---|---|
| `-allow3d`, `-disablegfxfirmware`, `-wexdbg` | WhateverXe (these strings are in its binary) | Their exact meaning is defined by WhateverXe's author; this project does not reinterpret them. |
| `-vi2c-force-polling` | VoodooI2C | Makes the I2C-HID stack poll instead of using interrupts. |
| `keepsyms=1` | macOS kernel | Keeps kernel symbols in panic reports. |

There is **no `-v`**: boot is deliberately non-verbose. To see verbose output while debugging, add `-v` to the
`boot-args` string in the *template* `EFI/OC/config.plist`, rebuild, and remove it again afterwards (it slows boot).
Do not edit `dist/EFI/OC/config.plist` by hand - the next build replaces it.

### Related security settings

The EFI runs with a reduced SIP configuration and no secure boot model:

- `NVRAM … csr-active-config` = `03080000` → `0x00000803` = `CSR_ALLOW_UNTRUSTED_KEXTS` (0x1) +
  `CSR_ALLOW_UNRESTRICTED_FS` (0x2) + `CSR_ALLOW_UNAUTHENTICATED_ROOT` (0x800).
- `Misc/Security/SecureBootModel` = `Disabled`, `Vault` = `Optional`.

Whether each of these is *required* for graphics has not been determined; they are documented here because they
are part of the working state. Do not tighten them without testing.

## Please do not

- enable `WhateverGreen` or `NootedGreen`, or add framebuffer / `AAPL,ig-platform-id` properties;
- reorder the kexts (Lilu → WhateverXe → AMFIPass …);
- swap AMFIPass for another build;
- remove `SSDT-PNLF` or `BrightnessKeys` if you want working brightness.

## If graphics do not work on your unit

1. Make sure you booted the **generated** EFI from `dist/`, not the template, and that the OpenCore log/boot-args
   are what you expect.
2. Confirm you are on macOS Tahoe. This EFI and its Wi-Fi/audio kexts target Darwin 25.x.
3. Unit-to-unit differences (different display panel, resolution, BIOS version) are possible and are **not covered**
   by this project. When reporting a problem, include the panel model, BIOS version and what you see - but strip
   your identity first (see [Troubleshooting](Troubleshooting.md)).
