# Troubleshooting

Two parts: errors while **building** the EFI (`scripts/make-efi.py`), and problems while **booting/running** it.

**Privacy when asking for help:** `smbios.local`, `dist/EFI/OC/config.plist`, OpenCore logs (`opencore-*.txt`),
SysReport folders and `ioreg`/ACPI dumps can contain your SMBIOS identity or other machine-specific data. Review and
redact them before posting; never post `smbios.local`.

## Part 1 - Build errors

Every error is printed as `error: ...` and the script exits with status 1. **A failed build leaves `dist/EFI` and
`smbios.local` untouched** (a new identity is saved only after the build has passed validation).
Run `python3 scripts/make-efi.py --check` to test dependencies and the template without changing anything.

### Dependencies and downloads

| Message | Cause / fix |
|---|---|
| `Python 3.8 or newer is required` | Use a newer Python 3 (`python3 --version`; on Windows `py -3 --version`). |
| `could not download <url>` | Network, proxy or TLS-certificate problem. On python.org Python for macOS run *Install Certificates.command*. The script falls back to `curl` if it is installed. Behind a corporate proxy set `HTTPS_PROXY`. |
| `SHA-256 mismatch for <url>` | The file does not match the hash pinned in the script and was deleted. Retry once; if it repeats, stop - do not edit the hash to "make it work". Report it. |
| `cannot run macserial` / `cannot run ocvalidate` | The OS refused to run the downloaded tool. Causes: an unsupported platform (OpenCore ships Linux tools for **x86-64 only**), a security product quarantining the file, or a `noexec` mount. Delete `build/deps/` and retry; on ARM Linux use an x86-64 emulator or build on another machine. |
| `unsupported operating system` | The script supports macOS, Linux and Windows. |
| `OpenCore only ships x86-64 Linux utilities...` | You are on ARM Linux, see above. |

### SMBIOS identity (`smbios.local`)

| Message | Cause / fix |
|---|---|
| `smbios.local is incomplete or invalid` | The lines listed are wrong, missing or unknown. Fix by hand (format in the README). **Nothing was replaced.** |
| `smbios.local was created for X but the EFI template uses Y` | The serial/MLB belong to a different Mac model. Use the template for that model, or `--regenerate-smbios`. |
| `--regenerate-smbios needs confirmation but there is no terminal` | Run it in a terminal, or add `--yes`. |
| `macserial could not generate an identity` | `macserial` failed for this model; the message shows its output. Do not hand-write a serial to get around it. |
| `unexpected output format from macserial` | Only happens if the OpenCore utilities change. The output is not echoed because it would be an identity. |
| warning: `smbios.local is readable by other users` | `chmod 600 smbios.local`. |
| warning: `could not confirm that the serial matches <model>` | macserial's decode output was unrecognised; the build continues. |

I want to keep my iMessage/iCloud setup - what do I do? Put your existing identity into `smbios.local` yourself
(README, "Bring your own identity"). The script never reads it from anywhere else.

### Template and configuration

| Message | Cause / fix |
|---|---|
| `template PlatformInfo/Generic/<key> is not the placeholder ...` | `EFI/OC/config.plist` was edited and contains a real value. Restore it: `git checkout -- EFI/OC/config.plist`. Your identity belongs in `smbios.local` only. **Do not commit that file.** |
| `identity-style keys found outside PlatformInfo/Generic` | A `SystemSerialNumber`/`MLB`/`SystemUUID`/`ROM` key exists elsewhere (for example in `NVRAM/Add`). The script only personalises `PlatformInfo/Generic`; remove or sanitise the extra keys. |
| `EFI/OC must contain exactly one configuration` | Another `*.plist` is next to `config.plist`. Move it out of the repository. |
| `unknown placeholder(s) in the template` | A `{{...}}` token other than the four SMBIOS placeholders. Remove it. |
| `template is incomplete: EFI/... is missing` | Required files are missing from `EFI/`. Re-clone or `git checkout -- EFI`. |
| `config.plist refers to files that are not in the EFI` | An enabled ACPI table, kext or driver named in the config is absent. Restore the listed files. |
| `ocvalidate rejected the generated config.plist` | `ocvalidate` printed the reason (for example an invalid option value). Fix the template's `config.plist`. |
| `generated config differs from the template in the wrong places` | A bug or a modified script - the build only may change the four identity fields. Please report it. |
| `unresolved placeholder` / `expected exactly one {{...}} ` | A placeholder is missing or duplicated in the template. Restore the template. |
| `the source EFI/ changed during the build` | Something (a sync client, antivirus, an editor) modified `EFI/` while the script ran. Re-run. |

### Output folder

| Situation | Behaviour |
|---|---|
| `dist/EFI` already exists and differs from the new build | It is **moved** (not deleted) to `dist/backups/EFI-<timestamp>/`. Delete old backups yourself when you no longer need them. |
| `dist/EFI` already equals the new build | Left untouched: `dist/EFI is already identical to this build`. |
| The same for `--installer` | `dist/installer/EFI` is handled independently (backups are named `EFI-installer-<timestamp>`); an installer build never touches `dist/EFI`, and vice versa. |
| Disk full / permission error mid-build | The previous `dist/EFI` is still in place; fix the problem and re-run. `build/staging/` is removed automatically. |

## Part 2 - Boot and run-time problems

The EFI is shipped as a working configuration; most boot problems come from differences between units or from
mistakes in copying. Start with the simple checks.

1. **Right EFI in the right place?** The drive must contain `EFI/BOOT/BOOTx64.efi` and `EFI/OC/...` at the root of a
   FAT32 partition. Use `dist/EFI`, not the repository's `EFI/`.
2. **Reach the picker.** In the normal `dist/EFI` the picker is hidden and the timeout is 0: hold **Esc** immediately
   after power-on **(general OpenCore behaviour; the window is only 0.5 s)**. If you cannot get there - or you are
   installing - build with `python3 scripts/make-efi.py --installer` and boot from `dist/installer/EFI`, which always
   shows the picker.
3. **See what is happening.** Add `-v` to `boot-args` in the *template* config (see [Graphics](Graphics.md)),
   rebuild, and boot from the new EFI. Remove `-v` afterwards.
4. **Get an OpenCore log (optional).** The shipped OpenCore binaries are the official 1.0.8 **DEBUG** build, so
   logging works once enabled: in the template, set `Misc/Debug/Target` to `67`, rebuild and boot. A file
   `opencore-<date>.txt` appears on the EFI partition. Set `Target` back to `0` afterwards - logging slows boot, and the
   log can contain machine details (review before sharing).
5. **Reset NVRAM.** `ResetNvramEntry.efi` is installed and `HideAuxiliary` is `false`, so the picker should list a
   *Reset NVRAM* entry; choose it, then boot again.
6. **Stuck after installing only on the internal drive?** Check the BIOS boot order and that the internal EFI
   partition contains `EFI/BOOT/BOOTx64.efi` (`LauncherOption` is `Disabled`, so OpenCore does not add its own
   firmware entry).

### Things that are known not to work

- **Sleep/wake** - unreliable; disabled; unsupported here.
- **Headphone jack** - not confirmed (see [Audio](Audio.md)).
- **Any macOS other than Tahoe** - `AirportItlwm` and `SimpleHDA` are restricted to Darwin 25.x.

### Graphics, audio, Wi-Fi, Bluetooth

See the dedicated pages: [Graphics](Graphics.md), [Audio](Audio.md), [Wi-Fi & Bluetooth](WiFi-Bluetooth.md).

## Reporting an issue

Include: what you ran, the exact `error:` text (build) or what you see (boot), macOS version, BIOS version, and your
hardware differences (Wi-Fi/Bluetooth module, display panel). **Do not include** `smbios.local`, serial numbers, MLB,
UUID, ROM, or unredacted logs.
