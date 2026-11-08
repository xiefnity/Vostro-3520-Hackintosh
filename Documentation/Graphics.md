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

WhateverXe's and WhateverXe-Graphics' READMEs both specify `csr-active-config` = `03080000` (`0x803`) and say that
full SIP is unsupported. Whether `SecureBootModel=Disabled` is required has not been determined. They are documented
here because they are part of the working state. Do not tighten them without testing.

## After installing macOS: the WhateverXe-Graphics package

**You might have to install the [WhateverXe-Graphics](https://github.com/b00t0x/WhateverXe-Graphics/releases) package
after installing macOS to get the GPU working.** The kext in this EFI is only half of the setup: WhateverXe's README
includes installing the latest Graphics package from within macOS, then restarting, in its installation steps. The
package carries signed graphics driver files; per its README it installs under `/Library`, rebuilds the auxiliary
kernel collection and does not change the EFI or SIP. It is **not part of this repository** and the build script does
not download it. How to install it: [Installation, step 6](Installation.md#6-gpu-acceleration-after-installing-macos).

What those two READMEs ask for, and what this EFI has (summarised from them; this project has not re-verified it):

| Requirement | In this EFI |
|---|---|
| macOS Tahoe **26.7 or newer** | Up to you: check *About This Mac*, update macOS if needed |
| OpenCore with Lilu, WhateverXe and **AMFIPass 1.4.1 Mod** (upstream AMFIPass is no substitute) | Lilu, WhateverXe and a modified AMFIPass 1.4.1 are included and enabled |
| `csr-active-config` = `03080000` (`0x803`) | Set as shipped |
| WhateverGreen must not be enabled together with WhateverXe | Disabled as shipped |

**Version pairing.** Both projects say to use the *latest* WhateverXe and WhateverXe-Graphics releases together. This
EFI ships **WhateverXe 0.7.0**; when this page was written (2026-11-08) the latest releases were WhateverXe 0.8.0 and
WhateverXe-Graphics 0.4.1. Which Graphics version the maintainer installed alongside 0.7.0 has not been recorded, and
this project has **not** upgraded the working 0.7.0. WhateverXe 0.7.0 and WhateverXe-Graphics 0.4.0 were published on
the same day (2026-11-02), so if the newest package misbehaves with this EFI, the pairing is the first thing to check.
WhateverXe 0.8.0 also adds changes this project has not tested (including experimental sleep/wake support); sleep/wake
remains unsupported here.

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
