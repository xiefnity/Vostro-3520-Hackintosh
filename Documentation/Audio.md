# Audio (Cirrus Logic CS8409 / CS42L42)

**Status (maintainer-reported):** a working audio configuration for the Vostro 3520's CS8409 HDA codec with the
CS42L42 headset codec. The **internal speakers** and the **internal microphone** work on the maintainer's unit.

> **The headphone jack is NOT confirmed working.** It has not been verified. Do not assume that plugging in
> headphones or a headset gives you sound or a microphone. The status of HDMI audio has not been documented.
>
> **Volume:** sound works, but avoid turning the volume all the way up - it can produce crackling noises.

## How it is wired

| Piece | Setting in `config.plist` | Notes |
|---|---|---|
| Audio controller | `DeviceProperties/Add/PciRoot(0x0)/Pci(0x1f,0x3)/layout-id` = `07000000` | Layout id **7**, stored as little-endian data |
| `AppleALC.kext` 1.9.9 | `Kernel/Add` #35, enabled | Comment: "controller patch. **No CS8409 layout exists**" - AppleALC is *not* providing a CS8409 codec layout here |
| `SimpleHDA.kext` 1.0.1 | `Kernel/Add` #36, enabled, Darwin 25.x only | Comment: "restores AppleHDA 600.2" |
| OpenCore audio (`UEFI/Audio`) | `AudioSupport` = `false` | No boot chime / picker audio |

So the working path is the combination **AppleALC (controller patch) + SimpleHDA + layout-id 7**. Changing any one
of them (or running a different macOS than Tahoe) may break audio.

## Please do not

- change `layout-id`, or add other `alcid=` / `alc-layout-id` style properties;
- disable either kext, or move `SimpleHDA` to other macOS versions without testing;
- treat this as a general-purpose CS8409 solution: it is the configuration that worked on one unit.

## If audio is silent or missing

1. Check that both kexts loaded: `kmutil showloaded | grep -i -E "AppleALC|SimpleHDA"`.
2. Make sure `dist/EFI/OC/config.plist` still has the `layout-id` property (it is part of the template and is never
   changed by the build).
3. Check *System Settings → Sound* for an output device, and that you are on macOS Tahoe (Darwin 25).

## Help wanted: headphone jack

If you test the headphone jack (output and microphone), please report the result with your BIOS version and codec
details in an issue, so this page can say something firmer. Strip your SMBIOS identity from anything you paste.
