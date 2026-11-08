# Maintaining the template

For the person who owns the public repository. End users do not need this page.

The golden rule: **the repository never contains a real SMBIOS identity.** Your own working EFI (with your own
identity) lives *outside* the repository as a private recovery baseline.

## Update the configuration from your working EFI

1. Keep your working `config.plist` outside the repository (for example `~/Hackintosh/private/EFI/OC/config.plist`).
2. Generate the public template from it:
   ```bash
   python3 scripts/make-efi.py --sanitize ~/Hackintosh/private/EFI/OC/config.plist
   ```
   This replaces `SystemSerialNumber`, `MLB`, `SystemUUID` and `ROM` with the placeholders, changes **nothing else**,
   prints no values, and aborts if any form of the old values would survive in the output or if identity-style keys
   exist anywhere else in the file.
3. Copy any changed kexts/ACPI/drivers into `EFI/` by hand. Leave out: `HfsPlus.efi` (downloaded at build time), any
   second `*.plist`, backups, zip files and `.DS_Store`.
4. Check: `python3 scripts/make-efi.py --check` (also runs `ocvalidate` on a trial build).
5. Review before committing:
   ```bash
   git status
   git diff --stat
   git ls-files | grep -iE "smbios|dist/|build/|config-"     # expect no output except EFI/OC/config.plist
   ```
6. Run the unit tests: `python3 -m unittest discover tests`.

### Keeping your own identity

Building from the repository produces a **new** identity unless `smbios.local` exists. To keep the identity your
working EFI already uses, create `smbios.local` yourself, in the documented format, from the values in your private
config **before** the first build. The tool never extracts identities for you - on purpose.

## Updating OpenCore

`ocvalidate` accepts only the OpenCore version it ships with, so the version in the script and the binaries in `EFI/`
must change together:

1. Replace `EFI/BOOT/BOOTx64.efi`, `EFI/OC/OpenCore.efi` and the drivers in `EFI/OC/Drivers/` with the new release
   (RELEASE or DEBUG - the current ones are 1.0.8 **DEBUG**).
2. In `scripts/make-efi.py` update `OC_VERSION` and the SHA-256 in `OC_ZIP` (use the digest published with the
   release, then confirm by downloading it yourself).
3. Migrate `config.plist` for the new version (see the OpenCore changelog), `--sanitize` it, run `--check`.
4. Update [Components](Components.md).

## Dependencies the script pins

| Item | Where | How to change |
|---|---|---|
| OpenCore release zip (`macserial`, `ocvalidate`, `macrecovery`) | `OC_ZIP` | New URL **and** SHA-256 |
| `HfsPlus.efi` | `HFSPLUS` (OcBinaryData commit + SHA-256) | New commit **and** SHA-256 |
| Recovery board id | `RECOVERY_BOARD_IDS` | Add the model if `SystemProductName` changes |

## If an identity was ever committed or pushed

Treat it as burned: simply deleting the file does not remove it from history, forks or caches.

1. Stop using that identity: rebuild with `--regenerate-smbios` and expect to re-register iMessage/FaceTime.
2. Remove it from the repository history (for example with `git filter-repo`) and force-push; then ask GitHub support
   to purge cached views/forks if the repository was public.
3. Assume anyone who copied it can use it.

## Release checklist

- [ ] `python3 -m unittest discover tests` passes
- [ ] `python3 scripts/make-efi.py --check` passes on a clean clone
- [ ] `git ls-files` contains no `smbios.local*`, `dist/`, `build/`, `*.zip`, logs, or extra `*.plist`
- [ ] `EFI/OC/config.plist` shows only placeholders for the four identity fields
- [ ] README status table still matches reality (do not claim more than has been verified)
- [ ] The repository URL in README/Installation is correct, and `NOTICE.md` still lists the kexts and changes accurately
